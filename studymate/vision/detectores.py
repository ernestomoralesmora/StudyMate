"""Detectores de MediaPipe (API Tasks): cara, manos y móvil.

`Analizador.analizar(frame)` devuelve una Observacion con todo lo detectado
en el fotograma, ya con los móviles marcados como "cerca de una mano" o no.

La cara y las manos se detectan en cada fotograma. El móvil se busca en un hilo
aparte (DetectorDispositivos) porque su modelo es lento: así no frena la cámara.
"""

import threading
import time
from collections import deque

import cv2
import mediapipe as mp
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


class DetectorDispositivos(threading.Thread):
    """Busca el móvil alrededor de las manos en segundo plano.

    `enviar()` deja el fotograma más reciente (los anteriores se descartan si
    el hilo va retrasado) y `resultado()` devuelve lo último detectado.
    """

    def __init__(self):
        super().__init__(daemon=True, name="deteccion-movil")
        self._detector = mpv.ObjectDetector.create_from_options(mpv.ObjectDetectorOptions(
            base_options=_opciones_base(config.MODELO_OBJETOS),
            running_mode=mpv.RunningMode.IMAGE,  # cada recorte es independiente
            category_allowlist=list(config.CLASES_DISPOSITIVO),
            score_threshold=config.UMBRAL_MOVIL_DUDOSO,
            max_results=3,
        ))
        self._cerrojo = threading.Lock()
        self._hay_trabajo = threading.Event()
        self._parar = threading.Event()
        self._peticion: tuple | None = None
        self._siguiente_mano = 0  # con dos manos, se alternan
        # Detecciones no vacías recientes: (instante, dispositivos encontrados).
        self._historial: deque[tuple[float, list[Dispositivo]]] = deque()
        self.recorte_actual: tuple[int, int, int, int] | None = None  # para depurar

    def enviar(self, frame_rgb, manos: list[Recuadro]) -> None:
        with self._cerrojo:
            self._peticion = (frame_rgb, list(manos))
        self._hay_trabajo.set()

    def resultado(self, ahora: float) -> list[Dispositivo]:
        """La mejor detección de los últimos MEMORIA_MOVIL_S segundos.

        Así, un análisis flojo (móvil medio tapado) entre dos buenos no hace
        que el fotograma pase de USANDO_MOVIL a DUDOSO o ESTUDIANDO.
        """
        with self._cerrojo:
            while self._historial and ahora - self._historial[0][0] > config.MEMORIA_MOVIL_S:
                self._historial.popleft()
            if not self._historial:
                return []
            _, mejor = max(self._historial, key=lambda h: max(d.puntuacion for d in h[1]))
            return [Dispositivo(d.clase, d.puntuacion, d.recuadro) for d in mejor]

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
            self._detector.close()

    def _procesar(self, frame_rgb, manos: list[Recuadro]) -> None:
        alto, ancho = frame_rgb.shape[:2]
        mano = manos[self._siguiente_mano % len(manos)]
        self._siguiente_mano += 1
        x1, y1, x2, y2 = recorte_mano(mano, ancho, alto)
        self.recorte_actual = (x1, y1, x2, y2)
        recorte = frame_rgb[y1:y2, x1:x2].copy()  # MediaPipe necesita memoria contigua
        imagen = mp.Image(image_format=mp.ImageFormat.SRGB, data=recorte)

        encontrados = [
            Dispositivo(
                clase=d.categories[0].category_name,
                puntuacion=d.categories[0].score,
                # Coordenadas del recorte -> coordenadas de la imagen completa.
                recuadro=(
                    d.bounding_box.origin_x + x1,
                    d.bounding_box.origin_y + y1,
                    d.bounding_box.origin_x + d.bounding_box.width + x1,
                    d.bounding_box.origin_y + d.bounding_box.height + y1,
                ),
            )
            for d in self._detector.detect(imagen).detections
        ]
        if encontrados:
            with self._cerrojo:
                self._historial.append((time.monotonic(), encontrados))

    def detener(self) -> None:
        self._parar.set()


class Analizador:
    def __init__(self):
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
        self.dispositivos = DetectorDispositivos()
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
