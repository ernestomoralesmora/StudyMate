"""Prueba de cámara + detectores en bruto, sin máquina de estados.

Sirve para ajustar umbrales en config.py: muestra cara, manos y móvil
(en rojo si está cerca de una mano) con su puntuación y los fps. El cuadro
azul fino es el recorte donde se está buscando el móvil.

Al salir, imprime cuántas veces se detectó el móvil en la mano mientras
había manos a la vista, y con qué puntuación.

Para comprobar falsos positivos, haz lo mismo sin móvil (escribir, dibujar...):
el porcentaje de "móvil en la mano" debería quedarse cerca de 0 %.

Uso:  python -m studymate.vision.pruebas.prueba_detectores [--camara N] [--modelo M]
Tecla Q / Esc para salir.
"""

import argparse
import csv
import time

import cv2

from .. import config
from ..camara import Camara
from ..detectores import Analizador
from ..observacion import clasificar
from .dibujo import dibujar_observacion, es_salir, mostrar, texto


def _area(r) -> float:
    return max(0.0, r[2] - r[0]) * max(0.0, r[3] - r[1])


def _medidas(movil, obs) -> list[str]:
    """Solape, tamaño y postura respecto a la mano que más solapa con el móvil."""
    def interseccion(m):
        return _area((max(movil[0], m[0]), max(movil[1], m[1]),
                      min(movil[2], m[2]), min(movil[3], m[3])))

    i = max(range(len(obs.manos)), key=lambda k: interseccion(obs.manos[k]))
    mano = obs.manos[i]
    inter = interseccion(mano)
    a_movil, a_mano = _area(movil), _area(mano)
    iou = inter / (a_movil + a_mano - inter) if a_movil + a_mano > inter else 0.0
    lados = sorted([movil[2] - movil[0], movil[3] - movil[1]])
    ancho_mano = mano[2] - mano[0]
    return [f"{iou:.3f}", f"{inter / a_movil if a_movil else 0:.3f}",
            f"{a_movil / a_mano if a_mano else 0:.3f}",
            f"{lados[1] / lados[0] if lados[0] else 0:.2f}",
            f"{lados[0] / ancho_mano if ancho_mano else 0:.3f}",
            f"{obs.pinza_manos[i]:.3f}", f"{obs.apertura_manos[i]:.3f}"]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--camara", type=int, default=0)
    p.add_argument("--modelo", default=config.MODELO_OBJETOS,
                   choices=["yolo", "yolo_s", "yolo_s416", "yolo_m", "objetos_preciso", "objetos"],
                   help="detector del móvil (para comparar)")
    p.add_argument("--registrar", metavar="ARCHIVO.csv",
                   help="guarda números de cada detección del móvil en la mano "
                        "(puntuación, solape y tamaño respecto a la mano); nunca imágenes")
    p.add_argument("--registrar-caras", metavar="ARCHIVO.csv",
                   help="guarda, por fotograma, la confianza y el tamaño de cada cara "
                        "detectada (solo números, nunca imágenes)")
    args = p.parse_args()

    registro_caras = None
    if args.registrar_caras:
        registro_caras = csv.writer(open(args.registrar_caras, "w", newline="", encoding="utf-8"))
        registro_caras.writerow(["t", "n_caras", "confianza", "ancho", "alto", "cx", "cy"])

    registro = None
    if args.registrar:
        registro = csv.writer(open(args.registrar, "w", newline="", encoding="utf-8"))
        registro.writerow(["t", "puntuacion", "iou_mano", "dentro_de_mano",
                           "area_movil_entre_mano", "aspecto", "lado_corto_entre_ancho_mano",
                           "pinza", "apertura", "hay_cara"])

    analizador = Analizador(modelo_movil=args.modelo)
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

                if registro_caras:
                    t = f"{ahora - inicio:.2f}"
                    if not obs.caras:
                        registro_caras.writerow([t, 0, "", "", "", "", ""])
                    for (x1, y1, x2, y2), conf in zip(obs.caras, obs.confianza_caras):
                        registro_caras.writerow([t, len(obs.caras), f"{conf:.3f}",
                                                 f"{x2 - x1:.0f}", f"{y2 - y1:.0f}",
                                                 f"{(x1 + x2) / 2:.0f}", f"{(y1 + y2) / 2:.0f}"])

                if obs.manos:
                    con_manos += 1
                    en_mano = [d.puntuacion for d in obs.dispositivos if d.cerca_de_mano]
                    if en_mano:
                        con_movil += 1
                        puntuaciones.append(max(en_mano))
                    if registro:
                        for d in obs.dispositivos:
                            if d.cerca_de_mano:
                                registro.writerow([f"{ahora - inicio:.2f}", f"{d.puntuacion:.3f}",
                                                   *_medidas(d.recuadro, obs), int(obs.hay_cara)])

                recorte = analizador.dispositivos.recorte_actual
                if obs.manos and recorte:
                    cv2.rectangle(frame, recorte[:2], recorte[2:], (255, 120, 0), 1)
                dibujar_observacion(frame, obs)
                texto(frame, f"Fotograma sugiere: {clasificar(obs).value}", 0)
                texto(frame, f"{fps:.1f} fps   modelo movil: {args.modelo}", 1,
                      (200, 200, 200), 0.5)
                if es_salir(mostrar("StudyMate - detectores", frame)):
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
    if con_manos:
        # Cuántos fotogramas con manos superarían cada umbral posible.
        partes = [
            f">= {u:.2f}: {100 * sum(p >= u for p in puntuaciones) / con_manos:.0f} %"
            for u in (0.3, 0.45, 0.6, 0.75)
        ]
        print("Fotogramas por encima de:  " + "   ".join(partes))
    print(f"Modelo del móvil: {args.modelo}")


if __name__ == "__main__":
    main()
