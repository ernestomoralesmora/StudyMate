"""Captura de la webcam con OpenCV.

Los fotogramas solo viven en memoria: no se guardan ni se envían a ningún sitio.
"""

import sys

import cv2

from . import config


class Camara:
    def __init__(
        self,
        indice: int = config.INDICE_CAMARA,
        ancho: int = config.ANCHO_CAMARA,
        alto: int = config.ALTO_CAMARA,
    ):
        # En Windows, DirectShow abre la webcam integrada mucho más rápido.
        backend = cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_ANY
        self._cap = cv2.VideoCapture(indice, backend)
        if not self._cap.isOpened():
            raise RuntimeError(
                f"No se pudo abrir la cámara {indice}. "
                "¿Está en uso por otra aplicación o bloqueada en la privacidad de Windows?"
            )
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, ancho)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, alto)

    def leer(self):
        """Devuelve el fotograma en BGR (como espejo) o None si falla."""
        ok, frame = self._cap.read()
        if not ok:
            return None
        return cv2.flip(frame, 1)

    def cerrar(self) -> None:
        self._cap.release()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.cerrar()
