"""Detectores de MediaPipe (API Tasks): cara, manos y móvil.

`Analizador.analizar(frame)` devuelve una Observacion con todo lo detectado
en el fotograma, ya con los móviles marcados como "cerca de una mano" o no.
"""

import cv2
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python import vision as mpv

from . import config
from .modelos import ruta_modelo
from .observacion import Dispositivo, Observacion, marcar_cercania


def _opciones_base(nombre: str) -> BaseOptions:
    # CPU: el MSI tiene gráfica AMD y el delegado GPU de MediaPipe no la usa en Windows.
    return BaseOptions(model_asset_path=ruta_modelo(nombre))


def _recuadro(bb) -> tuple[float, float, float, float]:
    return (bb.origin_x, bb.origin_y, bb.origin_x + bb.width, bb.origin_y + bb.height)


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
        self._objetos = mpv.ObjectDetector.create_from_options(mpv.ObjectDetectorOptions(
            base_options=_opciones_base("objetos"),
            running_mode=modo,
            category_allowlist=list(config.CLASES_DISPOSITIVO),
            score_threshold=config.UMBRAL_MOVIL_DUDOSO,
            max_results=3,
        ))
        self._n = 0
        self._ultimo_ts = -1
        self._ultimos_dispositivos: list[Dispositivo] = []

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

        # Sin manos no puede haber "móvil en la mano": nos ahorramos el detector
        # más lento. Con manos, se ejecuta cada DETECTAR_OBJETOS_CADA fotogramas
        # y en los intermedios se reutiliza el último resultado.
        if not obs.manos:
            self._ultimos_dispositivos = []
            self._n = 0  # la próxima vez que aparezca una mano, se detecta al momento
        elif self._n % config.DETECTAR_OBJETOS_CADA == 0:
            self._ultimos_dispositivos = [
                Dispositivo(
                    clase=d.categories[0].category_name,
                    puntuacion=d.categories[0].score,
                    recuadro=_recuadro(d.bounding_box),
                )
                for d in self._objetos.detect_for_video(imagen, ts_ms).detections
            ]
        if obs.manos:
            self._n += 1
        obs.dispositivos = [
            Dispositivo(d.clase, d.puntuacion, d.recuadro) for d in self._ultimos_dispositivos
        ]
        marcar_cercania(obs)
        return obs

    def cerrar(self) -> None:
        self._caras.close()
        self._manos.close()
        self._objetos.close()
