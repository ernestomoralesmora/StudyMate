"""Detectores: cara y manos con MediaPipe; móvil con YOLO o MediaPipe.

Analizador.analizar() devuelve una Observacion con las caras, las manos y
los dispositivos detectados. El móvil se busca en segundo plano alrededor
de las manos o, si no se ven, alrededor de la cara.
"""

import threading
import time

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python import vision as mpv

from . import config
from .modelos import ruta_modelo
from .aparcado import VigilanteMovil
from .observacion import Dispositivo, Observacion, Recuadro, marcar_cercania


def _opciones_base(nombre: str) -> BaseOptions:
    return BaseOptions(model_asset_path=ruta_modelo(nombre))


def _recuadro(bb) -> Recuadro:
    return (
        bb.origin_x,
        bb.origin_y,
        bb.origin_x + bb.width,
        bb.origin_y + bb.height,
    )


def recorte_mano(
    mano: Recuadro, ancho: int, alto: int
) -> tuple[int, int, int, int]:
    """Calcula un recorte cuadrado alrededor de la zona, dentro de la imagen."""
    x1, y1, x2, y2 = mano
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2

    lado = max(x2 - x1, y2 - y1) * (1 + 2 * config.MARGEN_RECORTE)
    lado = min(max(lado, config.LADO_MIN_RECORTE), ancho, alto)

    rx1 = int(min(max(cx - lado / 2, 0), ancho - lado))
    ry1 = int(min(max(cy - lado / 2, 0), alto - lado))
    return rx1, ry1, rx1 + int(lado), ry1 + int(lado)


class _MovilYolo:
    """YOLO26 (n o s) exportado a ONNX (herramientas/exportar_yolo.py)."""

    IDS_COCO = {"cell phone": 67}

    def __init__(self, nombre: str = "yolo"):
        import onnxruntime as ort

        opciones = ort.SessionOptions()
        opciones.intra_op_num_threads = config.HILOS_YOLO
        self._sesion = ort.InferenceSession(
            ruta_modelo(nombre),
            opciones,
            providers=["CPUExecutionProvider"],
        )
        entrada = self._sesion.get_inputs()[0]
        self._entrada = entrada.name
        self.LADO = entrada.shape[2]  # tamaño de entrada con el que se exportó
        self._clases = {self.IDS_COCO[c]: c for c in config.CLASES_DISPOSITIVO}

    def detectar(self, recorte_rgb):
        lado = recorte_rgb.shape[0]
        x = cv2.resize(recorte_rgb, (self.LADO, self.LADO))
        x = x.astype(np.float32) / 255
        entrada = x.transpose(2, 0, 1)[None]
        salida = self._sesion.run(None, {self._entrada: entrada})[0][0]

        # Salida (84, N): cx, cy, ancho, alto y 80 puntuaciones COCO.
        escala = lado / self.LADO
        resultado = []

        for id_coco, clase in self._clases.items():
            puntuaciones = salida[4 + id_coco]
            validos = np.flatnonzero(
                puntuaciones >= config.UMBRAL_MOVIL_DUDOSO
            )
            if validos.size == 0:
                continue

            cajas = [
                [
                    (cx - w / 2) * escala,
                    (cy - h / 2) * escala,
                    w * escala,
                    h * escala,
                ]
                for cx, cy, w, h in salida[:4, validos].T
            ]
            elegidos = cv2.dnn.NMSBoxes(
                cajas,
                puntuaciones[validos].tolist(),
                config.UMBRAL_MOVIL_DUDOSO,
                0.45,
            )

            for i in np.array(elegidos).flatten():
                x1, y1, w, h = cajas[i]
                resultado.append(
                    (
                        clase,
                        float(puntuaciones[validos[i]]),
                        (x1, y1, x1 + w, y1 + h),
                    )
                )

        return resultado

    def cerrar(self):
        pass


class _MovilMediapipe:
    """EfficientDet-Lite de MediaPipe («objetos» u «objetos_preciso»)."""

    def __init__(self, nombre: str):
        self._detector = mpv.ObjectDetector.create_from_options(
            mpv.ObjectDetectorOptions(
                base_options=_opciones_base(nombre),
                running_mode=mpv.RunningMode.IMAGE,
                category_allowlist=list(config.CLASES_DISPOSITIVO),
                score_threshold=config.UMBRAL_MOVIL_DUDOSO,
                max_results=3,
            )
        )

    def detectar(self, recorte_rgb):
        imagen = mp.Image(image_format=mp.ImageFormat.SRGB, data=recorte_rgb)
        return [
            (
                d.categories[0].category_name,
                d.categories[0].score,
                _recuadro(d.bounding_box),
            )
            for d in self._detector.detect(imagen).detections
        ]

    def cerrar(self):
        self._detector.close()


class DetectorDispositivos(threading.Thread):
    """Busca el móvil en las zonas indicadas sin bloquear la cámara."""

    def __init__(
        self,
        modelo: str = config.MODELO_OBJETOS,
        usar_clip: bool = False,
        movil_a_la_vista: bool = False,
    ):
        super().__init__(daemon=True, name="deteccion-movil")
        self.modelo = modelo
        # CLIP solo se carga si hace falta (tarda unos segundos y ocupa memoria).
        self._clip = None
        if usar_clip:
            from .clip import VerificadorClip
            self._clip = VerificadorClip()
        self._motor = (
            _MovilYolo(modelo)
            if modelo.startswith("yolo")
            else _MovilMediapipe(modelo)
        )
        self._cerrojo = threading.Lock()
        self._hay_trabajo = threading.Event()
        self._parar = threading.Event()
        self._peticion: tuple | None = None
        self._siguiente_zona = 0
        self._ultimo: tuple[float, list[Dispositivo]] = (-1e9, [])
        self.recorte_actual: tuple[int, int, int, int] | None = None
        # Vigila el sitio donde se dejó el móvil (usa el mismo detector).
        self.vigilante = VigilanteMovil(self._motor.detectar, activo=movil_a_la_vista)
        self._ultima_comprobacion = -1e9

    def enviar(self, frame_rgb, zonas: list[Recuadro], manos: list[Recuadro] | None = None) -> None:
        """Deja el fotograma más reciente para analizarlo en segundo plano.

        Aunque no haya zonas (manos o cara), el fotograma sirve para vigilar
        el móvil aparcado.
        """
        if not zonas and not self.vigilante.activo:
            return

        with self._cerrojo:
            self._peticion = (frame_rgb, list(zonas), list(manos or []))
            self._hay_trabajo.set()

    def resultado(self, ahora: float) -> list[Dispositivo]:
        """Devuelve las detecciones recientes."""
        with self._cerrojo:
            instante, dispositivos = self._ultimo
            if ahora - instante > config.MEMORIA_MOVIL_S:
                return []

            return [
                Dispositivo(d.clase, d.puntuacion, d.recuadro, prob_clip=d.prob_clip)
                for d in dispositivos
            ]

    def run(self) -> None:
        try:
            while not self._parar.is_set():
                if not self._hay_trabajo.wait(timeout=0.2):
                    continue

                with self._cerrojo:
                    peticion, self._peticion = self._peticion, None
                    self._hay_trabajo.clear()

                if peticion is not None:
                    self._procesar(*peticion)
        finally:
            self._motor.cerrar()

    def _procesar(self, frame_rgb, zonas: list[Recuadro], manos: list[Recuadro] | None = None) -> None:
        encontrados = self._buscar_en_zonas(frame_rgb, zonas) if zonas else []

        # Móvil aparcado: al empezar se sigue en la mano hasta que se deja en la
        # mesa (y, por si acaso, se busca en toda la imagen); después se
        # comprueba su sitio cada PERIODO_APARCADO_S.
        vigilante = self.vigilante
        ahora = time.monotonic()
        if vigilante.estado.value == "buscando":
            vigilante.seguir_en_mano(
                frame_rgb, [(d.puntuacion, d.recuadro) for d in encontrados], manos or []
            )
            # Buscar en toda la imagen es caro (6 cuadros): no en cada pasada,
            # para que el seguimiento en la mano vaya fluido.
            if ahora - self._ultima_comprobacion >= config.PERIODO_BUSQUEDA_APARCADO_S:
                vigilante.buscar(frame_rgb)
                self._ultima_comprobacion = ahora
        elif vigilante.vigilando and ahora - self._ultima_comprobacion >= config.PERIODO_APARCADO_S:
            vigilante.comprobar(frame_rgb)
            self._ultima_comprobacion = ahora

    def _buscar_en_zonas(self, frame_rgb, zonas: list[Recuadro]) -> list[Dispositivo]:
        alto, ancho = frame_rgb.shape[:2]
        zona = zonas[self._siguiente_zona % len(zonas)]
        self._siguiente_zona += 1

        x1, y1, x2, y2 = recorte_mano(zona, ancho, alto)
        self.recorte_actual = (x1, y1, x2, y2)
        recorte = np.ascontiguousarray(frame_rgb[y1:y2, x1:x2])

        # Convierte las coordenadas del recorte a las del fotograma completo.
        encontrados = [
            Dispositivo(
                clase,
                puntuacion,
                (bx1 + x1, by1 + y1, bx2 + x1, by2 + y1),
            )
            for clase, puntuacion, (bx1, by1, bx2, by2)
            in self._motor.detectar(recorte)
        ]

        # CLIP revisa cada candidato mirando el fotograma completo alrededor.
        if self._clip is not None:
            for d in encontrados:
                d.prob_clip = self._clip.prob_movil(frame_rgb, d.recuadro)

        with self._cerrojo:
            self._ultimo = (time.monotonic(), encontrados)
        return encontrados

    def detener(self) -> None:
        self._parar.set()


class Analizador:
    def __init__(
        self,
        modelo_movil: str = config.MODELO_OBJETOS,
        modo_verificacion: str = config.MODO_VERIFICACION,
        cargar_clip: bool | None = None,
        movil_a_la_vista: bool = False,
    ):
        """`cargar_clip`: None = solo si el modo lo usa; True = siempre (para comparar)."""
        self.modo_verificacion = modo_verificacion
        if cargar_clip is None:
            cargar_clip = "clip" in modo_verificacion
        modo = mpv.RunningMode.VIDEO

        self._caras = mpv.FaceDetector.create_from_options(
            mpv.FaceDetectorOptions(
                base_options=_opciones_base("cara"),
                running_mode=modo,
                min_detection_confidence=config.CONFIANZA_CARA,
            )
        )
        self._manos = mpv.HandLandmarker.create_from_options(
            mpv.HandLandmarkerOptions(
                base_options=_opciones_base("manos"),
                running_mode=modo,
                num_hands=config.MAX_MANOS,
                min_hand_detection_confidence=config.CONFIANZA_MANO,
            )
        )

        self.dispositivos = DetectorDispositivos(
            modelo_movil, usar_clip=cargar_clip, movil_a_la_vista=movil_a_la_vista
        )
        self.dispositivos.start()
        self._ultimo_ts = -1

    def analizar(self, frame_bgr, ts_ms: int) -> Observacion:
        """Analiza un fotograma BGR con un tiempo creciente en milisegundos."""
        ts_ms = max(ts_ms, self._ultimo_ts + 1)
        self._ultimo_ts = ts_ms

        alto, ancho = frame_bgr.shape[:2]
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        imagen = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        obs = Observacion()

        for d in self._caras.detect_for_video(imagen, ts_ms).detections:
            obs.caras.append(_recuadro(d.bounding_box))
            obs.confianza_caras.append(d.categories[0].score)

        for puntos in self._manos.detect_for_video(imagen, ts_ms).hand_landmarks:
            xs = [p.x * ancho for p in puntos]
            ys = [p.y * alto for p in puntos]
            obs.manos.append((min(xs), min(ys), max(xs), max(ys)))

            # Puntos de MediaPipe: 0 muñeca, 4 pulgar, 8 índice, 9 base del
            # dedo corazón, 20 meñique. La palma (0-9) sirve de escala.
            def dist(a: int, b: int) -> float:
                return float(np.hypot(xs[a] - xs[b], ys[a] - ys[b]))

            palma = dist(0, 9) or 1.0
            obs.pinza_manos.append(dist(4, 8) / palma)
            obs.apertura_manos.append(dist(8, 20) / palma)

        # Si no vemos ninguna mano, buscamos el móvil alrededor de la cara.
        zonas_busqueda = obs.manos + obs.caras[:1]
        self.dispositivos.enviar(rgb, zonas_busqueda, obs.manos)
        obs.sitio_movil = self.dispositivos.vigilante.estado

        obs.dispositivos = self.dispositivos.resultado(time.monotonic())
        marcar_cercania(obs, modo=self.modo_verificacion)
        return obs

    def cerrar(self) -> None:
        self.dispositivos.detener()
        self.dispositivos.join(timeout=2)
        self._caras.close()
        self._manos.close()