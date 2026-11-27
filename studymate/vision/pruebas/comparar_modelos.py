"""Compara varios modelos YOLO sobre los mismos fotogramas.

Cada vez que hay una mano a la vista, recorta la zona de la mano y la pasa por
todos los modelos. A cada detección le aplica las mismas reglas que la
aplicación (umbral, tamaño respecto a la mano y pinza) y cuenta cuántas veces
cada modelo habría dicho "móvil en la mano".

Uso (una pasada por objeto, de 30-40 s):
    python -m studymate.vision.pruebas.comparar_modelos --objeto cartera
    python -m studymate.vision.pruebas.comparar_modelos --objeto movil

Guarda registro_comparar_<objeto>.csv (solo números, nunca imágenes).
Tecla Q / Esc para salir.
"""

import argparse
import csv
import threading
import time

import cv2
import numpy as np

from .. import config
from ..camara import Camara
from ..detectores import Analizador, _MovilYolo, recorte_mano
from ..observacion import Dispositivo, Observacion, marcar_cercania
from .dibujo import dibujar_observacion, es_salir, mostrar, texto

MODELOS = ["yolo_s", "yolo_s416", "yolo_m"]


class Comparador(threading.Thread):
    """Pasa el último recorte de la mano por todos los modelos, en segundo plano."""

    def __init__(self, registro):
        super().__init__(daemon=True)
        self.motores = {m: _MovilYolo(m) for m in MODELOS}
        self.registro = registro
        self.inicio = time.monotonic()
        self.peticion = None
        self.cerrojo = threading.Lock()
        self.parar = threading.Event()
        self.analisis = 0
        self.cuenta = {m: 0 for m in MODELOS}
        self.ultimo = {m: "-" for m in MODELOS}

    def enviar(self, rgb, obs: Observacion) -> None:
        with self.cerrojo:
            self.peticion = (rgb, obs)

    def run(self) -> None:
        while not self.parar.is_set():
            with self.cerrojo:
                peticion, self.peticion = self.peticion, None
            if peticion is None:
                time.sleep(0.01)
                continue
            self._comparar(*peticion)

    def _comparar(self, rgb, obs: Observacion) -> None:
        alto, ancho = rgb.shape[:2]
        x1, y1, x2, y2 = recorte_mano(obs.manos[0], ancho, alto)
        recorte = np.ascontiguousarray(rgb[y1:y2, x1:x2])
        t = time.monotonic() - self.inicio
        self.analisis += 1
        for nombre, motor in self.motores.items():
            dispositivos = [
                Dispositivo(c, p, (bx1 + x1, by1 + y1, bx2 + x1, by2 + y1))
                for c, p, (bx1, by1, bx2, by2) in motor.detectar(recorte)
            ]
            prueba = Observacion(manos=obs.manos, pinza_manos=obs.pinza_manos,
                                 apertura_manos=obs.apertura_manos, dispositivos=dispositivos)
            marcar_cercania(prueba)
            mejor = max(dispositivos, key=lambda d: d.puntuacion, default=None)
            contaria = any(d.cerca_de_mano and d.puntuacion >= config.UMBRAL_MOVIL
                           for d in dispositivos)
            self.cuenta[nombre] += contaria
            self.ultimo[nombre] = (
                f"{mejor.puntuacion:.2f}" + (" MOVIL" if contaria else f" {mejor.descartado}")
                if mejor else "-"
            )
            self.registro.writerow([
                f"{t:.2f}", nombre,
                f"{mejor.puntuacion:.3f}" if mejor else "0",
                mejor.descartado if mejor else "",
                int(contaria),
                f"{obs.pinza_manos[0]:.3f}",
            ])


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--objeto", required=True, help="qué tienes en la mano (p. ej., cartera, movil)")
    p.add_argument("--camara", type=int, default=0)
    args = p.parse_args()

    archivo = f"registro_comparar_{args.objeto}.csv"
    with open(archivo, "w", newline="", encoding="utf-8") as f:
        registro = csv.writer(f)
        registro.writerow(["t", "modelo", "puntuacion", "descartado", "cuenta_como_movil", "pinza"])
        analizador = Analizador()  # cara y manos (su detector de móvil no se usa aquí)
        comparador = Comparador(registro)
        comparador.start()
        inicio = time.monotonic()
        with Camara(args.camara) as camara:
            try:
                while True:
                    frame = camara.leer()
                    if frame is None:
                        continue
                    obs = analizador.analizar(frame, int((time.monotonic() - inicio) * 1000))
                    if obs.manos:
                        comparador.enviar(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), obs)
                    dibujar_observacion(frame, Observacion(caras=obs.caras, manos=obs.manos))
                    texto(frame, f"Objeto: {args.objeto}   analisis: {comparador.analisis}", 0)
                    for i, m in enumerate(MODELOS, start=1):
                        texto(frame, f"{m}: {comparador.ultimo[m]}", i, (200, 200, 200), 0.5)
                    if es_salir(mostrar("StudyMate - comparar modelos", frame)):
                        break
            finally:
                comparador.parar.set()
                comparador.join(timeout=3)
                analizador.cerrar()
                cv2.destroyAllWindows()

    print(f"\nObjeto: {args.objeto}   análisis con la mano a la vista: {comparador.analisis}")
    for m in MODELOS:
        pct = 100 * comparador.cuenta[m] / comparador.analisis if comparador.analisis else 0
        print(f"  {m:10s} lo cuenta como móvil en el {pct:5.1f} % de los análisis")
    print(f"Registro guardado en {archivo}")


if __name__ == "__main__":
    main()
