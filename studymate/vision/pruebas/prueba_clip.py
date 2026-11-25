"""Prueba del verificador CLIP por separado (sin YOLO ni MediaPipe).

1. Comprueba que el tokenizador da los números correctos.
2. Carga CLIP (la primera vez descarga ~155 MB) y mide cuánto tarda por imagen.
3. Con --imagen, dice cuánto se parece una foto a cada frase.
4. Con --camara, analiza en directo el cuadrado del centro de la imagen:
   pon delante el móvil, un boli, el típex... y mira la probabilidad de móvil.

Uso:  python -m studymate.vision.pruebas.prueba_clip [--imagen foto.jpg] [--camara]
Los fotogramas no se guardan.
"""

import argparse
import time

import cv2
import numpy as np

from .. import config
from ..clip import VerificadorClip


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--imagen", help="foto para clasificar")
    p.add_argument("--camara", action="store_true", help="prueba en directo con la webcam")
    p.add_argument("--indice", type=int, default=config.INDICE_CAMARA)
    args = p.parse_args()

    print("Cargando CLIP (la primera vez descarga ~155 MB de Hugging Face)...")
    t0 = time.perf_counter()
    clip = VerificadorClip()
    print(f"  Cargado en {time.perf_counter() - t0:.1f} s")

    # Ejemplo clásico de CLIP: "a photo of a cat" -> estos números.
    ids = clip.tokenizador.codificar("a photo of a cat")
    esperado = [49406, 320, 1125, 539, 320, 2368, 49407]
    assert ids == esperado, f"Tokenizador mal: {ids} (se esperaba {esperado})"
    print("  ✓ Tokenizador correcto")

    ruido = np.random.default_rng(0).integers(0, 255, (300, 300, 3), dtype=np.uint8)
    clip.probabilidades(ruido)
    tiempos = []
    for _ in range(10):
        t = time.perf_counter()
        clip.probabilidades(ruido)
        tiempos.append(time.perf_counter() - t)
    print(f"  ✓ {1000 * np.median(tiempos):.0f} ms por recorte (solo se usa cuando YOLO ve algo)")

    if args.imagen:
        bgr = cv2.imread(args.imagen)
        if bgr is None:
            raise SystemExit(f"No se puede abrir {args.imagen}")
        probs = clip.probabilidades(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
        print(f"\n{args.imagen}: probabilidad de móvil {probs[:clip.n_movil].sum():.2f}")
        for frase, pr in sorted(zip(clip.textos, probs), key=lambda x: -x[1]):
            print(f"  {pr:5.2f}  {frase}")

    if args.camara:
        from ..camara import Camara
        from .dibujo import es_salir, mostrar, texto

        print("\nPon el objeto dentro del cuadrado. Q o Esc para salir.")
        with Camara(args.indice) as camara:
            while True:
                frame = camara.leer()
                if frame is None:
                    continue
                alto, ancho = frame.shape[:2]
                lado = int(min(alto, ancho) * 0.6)
                x1, y1 = (ancho - lado) // 2, (alto - lado) // 2
                recorte = cv2.cvtColor(frame[y1:y1 + lado, x1:x1 + lado], cv2.COLOR_BGR2RGB)
                probs = clip.probabilidades(recorte)
                p_movil = probs[:clip.n_movil].sum()
                mejor = clip.textos[int(np.argmax(probs))]
                color = (0, 0, 255) if p_movil >= config.UMBRAL_CLIP else (60, 180, 60)
                cv2.rectangle(frame, (x1, y1), (x1 + lado, y1 + lado), color, 2)
                texto(frame, f"Movil: {p_movil:.2f}", 0, color)
                texto(frame, mejor, 1, (230, 230, 230), 0.5)
                if es_salir(mostrar("StudyMate - prueba CLIP", frame)):
                    break
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
