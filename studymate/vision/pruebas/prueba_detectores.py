"""Prueba de cámara + detectores en bruto, sin máquina de estados.

Sirve para ajustar umbrales en config.py: muestra cara, manos y móvil
(en rojo si está cerca de una mano) con su puntuación y los fps.

Uso:  python -m studymate.vision.pruebas.prueba_detectores [--camara N]
Tecla Q / Esc para salir.
"""

import argparse
import time

import cv2

from ..camara import Camara
from ..detectores import Analizador
from ..observacion import clasificar
from .dibujo import dibujar_observacion, texto


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--camara", type=int, default=0)
    args = p.parse_args()

    analizador = Analizador()
    inicio = anterior = time.monotonic()
    fps = 0.0
    with Camara(args.camara) as camara:
        try:
            while True:
                frame = camara.leer()
                if frame is None:
                    continue
                ahora = time.monotonic()
                obs = analizador.analizar(frame, int((ahora - inicio) * 1000))
                dt, anterior = ahora - anterior, ahora
                if dt > 0:
                    fps = 1 / dt if fps == 0 else 0.9 * fps + 0.1 / dt

                dibujar_observacion(frame, obs)
                texto(frame, f"Fotograma sugiere: {clasificar(obs).value}", 0)
                texto(frame, f"{fps:.1f} fps", 1, (200, 200, 200), 0.5)
                cv2.imshow("StudyMate - detectores", frame)
                if cv2.waitKey(1) & 0xFF in (ord("q"), ord("Q"), 27):
                    break
        finally:
            analizador.cerrar()
            cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
