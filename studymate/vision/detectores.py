"""Detectores: cara y manos con MediaPipe; móvil con YOLO (o MediaPipe).

`Analizador.analizar(frame)` devuelve una Observacion con todo lo detectado
en el fotograma, ya con los móviles marcados como "cerca de una mano" o no.

La cara y las manos se detectan en cada fotograma. El móvil se busca en un hilo
aparte (DetectorDispositivos), en un recorte alrededor de cada mano, para que
no frene la cámara.
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
from .observacion import Dispositivo, Observacion, Recuadro, marcar_cercania


def _opciones_base(nombre: str) -> BaseOptions:
    # CPU: el MSI tiene gráfica AMD y el delegado GPU de MediaPipe no la usa en Windows.
    return BaseOptions(model_asset_path=ruta_modelo(nombre))


def _recuadro(bb) -> Recuadro:
    return (bb.origin_x, bb.origin_y, bb.origin_x + bb.width, bb.origin_y + bb.height)


def recorte_mano(mano: Recuadro, ancho: int, alto: int) -> tuple[int, int, int, int]:
    """Recorte cuadrado alrededor de una mano, dentro de los límites de la imagen."""
    x1, y1, x2, y2 = mano
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    lado = max(x2 - x1, y2 - y1) * (1 + 2 * config.MARGEN_RECORTE)
    lado = min(max(lado, config.LADO_MIN_RECORTE), ancho, alto)
    rx1 = int(min(max(cx - lado / 2, 0), ancho - lado))
    ry1 = int(min(max(cy - lado / 2, 0), alto - lado))
    return rx1, ry1, rx1 + int(lado), ry1 + int(lado)


# --- Motores para buscar el móvil en un recorte ------------------------------
# Los dos tienen detectar(recorte_rgb) -> [(clase, puntuación, recuadro)], con el
# recuadro en coordenadas del recorte.

class _MovilYolo:
    """YOLO26n exportado a ONNX (herramientas/exportar_yolo.py)."""

    LADO = 320  # tamaño de entrada con el que se exportó
    IDS_COCO = {"cell phone": 67}

    def __init__(self):
        import onnxruntime as ort

        opciones = ort.SessionOptions()
        opciones.intra_op_num_threads = config.HILOS_YOLO
        self._sesion = ort.InferenceSession(
            ruta_modelo("yolo"), opciones, providers=["CPUExecutionProvider"]
        )
        self._entrada = self._sesion.get_inputs()[0].name
        self._clases = {self.IDS_COCO[c]: c for c in config.CLASES_DISPOSITIVO}

    def detectar(self, recorte_rgb):
        lado = recorte_rgb.shape[0]  # el recorte es cuadrado
        x = cv2.resize(recorte_rgb, (self.LADO, self.LADO)).astype(np.float32) / 255
        salida = self._sesion.run(None, {self._entrada: x.transpose(2, 0, 1)[None]})[0][0]
        # salida: (84, N) -> por columna, cx, cy, ancho, alto y 80 puntuaciones COCO.
        escala = lado / self.LADO
        resultado = []
        for id_coco, clase in self._clases.items():
            puntuaciones = salida[4 + id_coco]
            validos = np.flatnonzero(puntuaciones >= config.UMBRAL_MOVIL_DUDOSO)
            if validos.size == 0:
                continue
            cajas = [
                [(cx - w / 2) * escala, (cy - h / 2) * escala, w * escala, h * escala]
                for cx, cy, w, h in salida[:4, validos].T
            ]
            elegidos = cv2.dnn.NMSBoxes(
                cajas, puntuaciones[validos].tolist(), config.UMBRAL_MOVIL_DUDOSO, 0.45
            )
            for i in np.array(elegidos).flatten():
                x1, y1, w, h = cajas[i]
                resultado.append((clase, float(puntuaciones[validos[i]]), (x1, y1, x1 + w, y1 + h)))
        return resultado

    def cerrar(self):
        pass


class _MovilMediapipe:
    """EfficientDet-Lite de MediaPipe ("objetos" u "objetos_preciso")."""

    def __init__(self, nombre: str):
        self._detector = mpv.ObjectDetector.create_from_options(mpv.ObjectDetectorOptions(
            base_options=_opciones_base(nombre),
            running_mode=mpv.RunningMode.IMAGE,  # cada recorte es independiente
            category_allowlist=list(config.CLASES_DISPOSITIVO),
            score_threshold=config.UMBRAL_MOVIL_DUDOSO,
            max_results=3,
        ))

    def detectar(self, recorte_rgb):
        imagen = mp.Image(image_format=mp.ImageFormat.SRGB, data=recorte_rgb)
        return [
            (d.categories[0].category_name, d.categories[0].score, _recuadro(d.bounding_box))
            for d in self._detector.detect(imagen).detections
        ]

    def cerrar(self):
        self._detector.close()


class DetectorDispositivos(threading.Thread):
    """Busca el móvil alrededor de las manos en segundo plano.

    `enviar()` deja el fotograma más reciente (los anteriores se descartan si
    el hilo va retrasado) y `resultado()` devuelve lo último detectado.
    """

    def __init__(self, modelo: str = config.MODELO_OBJETOS):
        super().__init__(daemon=True, name="deteccion-movil")
        self.modelo = modelo
        self._motor = _MovilYolo() if modelo == "yolo" else _MovilMediapipe(modelo)
        self._cerrojo = threading.Lock()
        self._hay_trabajo = threading.Event()
        self._parar = threading.Event()
        self._peticion: tuple | None = None
        self._siguiente_mano = 0  # con dos manos, se alternan
        self._ultimo: tuple[float, list[Dispositivo]] = (-1e9, [])
        self.recorte_actual: tuple[int, int, int, int] | None = None  # para depurar

    def enviar(self, frame_rgb, manos: list[Recuadro]) -> None:
        with self._cerrojo:
            self._peticion = (frame_rgb, list(manos))
        self._hay_trabajo.set()

    def resultado(self, ahora: float) -> list[Dispositivo]:
        """Lo detectado en el último análisis, si es de hace menos de MEMORIA_MOVIL_S."""
        with self._cerrojo:
            instante, dispositivos = self._ultimo
            if ahora - instante > config.MEMORIA_MOVIL_S:
                return []
            return [Dispositivo(d.clase, d.puntuacion, d.recuadro) for d in dispositivos]

    def run(self) -> None:
        try:
            while not self._parar.is_set():
                if not self._hay_trabajo.wait(timeout=0.2):
                    continue
                with self._cerrojo:
                    peticion, self._peticion = self._peticion, None
                    self._hay_trabajo.clear()
                if peticion is None:
                    continue
                self._procesar(*peticion)
        finally:
            self._motor.cerrar()

    def _procesar(self, frame_rgb, manos: list[Recuadro]) -> None:
        alto, ancho = frame_rgb.shape[:2]
        mano = manos[self._siguiente_mano % len(manos)]
        self._siguiente_mano += 1
        x1, y1, x2, y2 = recorte_mano(mano, ancho, alto)
        self.recorte_actual = (x1, y1, x2, y2)
        recorte = np.ascontiguousarray(frame_rgb[y1:y2, x1:x2])

        encontrados = [
            # Coordenadas del recorte -> coordenadas de la imagen completa.
            Dispositivo(clase, puntuacion, (bx1 + x1, by1 + y1, bx2 + x1, by2 + y1))
            for clase, puntuacion, (bx1, by1, bx2, by2) in self._motor.detectar(recorte)
        ]
        with self._cerrojo:
            self._ultimo = (time.monotonic(), encontrados)

    def detener(self) -> None:
        self._parar.set()


class Analizador:
    def __init__(self, modelo_movil: str = config.MODELO_OBJETOS):
        modo = mpv.RunningMode.VIDEO  # aprovecha el seguimiento entre fotogramas
        self._caras = mpv.FaceDetector.create_from_options(mpv.FaceDetectorOptions(
            base_options=_opciones_base("cara"),
            running_mode=modo,
            min_detection_confidence=config.CONFIANZA_CARA,
        ))
        self._manos = mpv.HandLandmarker.create_from_options(mpv.HandLandmarkerOptions(
            base_options=_opciones_base("manos"),
            running_mode=modo,
            num_hands=config.MAX_MANOS,
            min_hand_detection_confidence=config.CONFIANZA_MANO,
        ))
        self.dispositivos = DetectorDispositivos(modelo_movil)
        self.dispositivos.start()
        self._ultimo_ts = -1

    def analizar(self, frame_bgr, ts_ms: int) -> Observacion:
        """Analiza un fotograma BGR. ts_ms debe ser creciente (milisegundos)."""
        ts_ms = max(ts_ms, self._ultimo_ts + 1)
        self._ultimo_ts = ts_ms
        alto, ancho = frame_bgr.shape[:2]
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        imagen = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        obs = Observacion()

        for d in self._caras.detect_for_video(imagen, ts_ms).detections:
            obs.caras.append(_recuadro(d.bounding_box))

        for puntos in self._manos.detect_for_video(imagen, ts_ms).hand_landmarks:
            xs = [p.x * ancho for p in puntos]
            ys = [p.y * alto for p in puntos]
            obs.manos.append((min(xs), min(ys), max(xs), max(ys)))

        # Sin manos no puede haber "móvil en la mano": no hace falta buscarlo.
        if obs.manos:
            self.dispositivos.enviar(rgb, obs.manos)
        obs.dispositivos = self.dispositivos.resultado(time.monotonic())
        marcar_cercania(obs)
        return obs

    def cerrar(self) -> None:
        self.dispositivos.detener()
        self.dispositivos.join(timeout=2)
        self._caras.close()
        self._manos.close()
