"""Prueba de cámara + detectores en bruto, sin máquina de estados.

Sirve para ajustar umbrales en config.py: muestra cara, manos y móvil
(en rojo si está cerca de una mano) con su puntuación y los fps. El cuadro
azul fino es el recorte donde se está buscando el móvil.

Al salir, imprime cuántas veces se detectó el móvil en la mano mientras
había manos a la vista, y con qué puntuación.

Uso:  python -m studymate.vision.pruebas.prueba_detectores [--camara N]
Tecla Q / Esc para salir.
"""

import argparse
import time

import cv2

from .. import config
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
    con_manos = con_movil = 0
    puntuaciones: list[float] = []
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

                if obs.manos:
                    con_manos += 1
                    en_mano = [d.puntuacion for d in obs.dispositivos if d.cerca_de_mano]
                    if en_mano:
                        con_movil += 1
                        puntuaciones.append(max(en_mano))

                recorte = analizador.dispositivos.recorte_actual
                if obs.manos and recorte:
                    cv2.rectangle(frame, recorte[:2], recorte[2:], (255, 120, 0), 1)
                dibujar_observacion(frame, obs)
                texto(frame, f"Fotograma sugiere: {clasificar(obs).value}", 0)
                texto(frame, f"{fps:.1f} fps   modelo movil: {config.MODELO_OBJETOS}", 1,
                      (200, 200, 200), 0.5)
                cv2.imshow("StudyMate - detectores", frame)
                if cv2.waitKey(1) & 0xFF in (ord("q"), ord("Q"), 27):
                    break
        finally:
            analizador.cerrar()
            cv2.destroyAllWindows()

    print(f"\nFotogramas con manos: {con_manos}")
    if con_manos:
        print(f"Con móvil en la mano: {con_movil} ({100 * con_movil / con_manos:.0f} %)")
    if puntuaciones:
        puntuaciones.sort()
        print(f"Puntuación del móvil: mínima {puntuaciones[0]:.2f}, "
              f"mediana {puntuaciones[len(puntuaciones) // 2]:.2f}, "
              f"máxima {puntuaciones[-1]:.2f}  "
              f"(USANDO_MOVIL a partir de {config.UMBRAL_MOVIL})")


if __name__ == "__main__":
    main()
