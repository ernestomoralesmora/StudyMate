"""Prueba principal de la fase 1: cámara con el estado y el tiempo en pantalla.

Uso (desde la raíz del repositorio):
    python -m studymate.vision.pruebas.prueba_camara [--camara N] [--permitir-movil]

Teclas:  Q / Esc = salir   S = sí estaba estudiando   N = no estaba estudiando
"""

import argparse

import cv2

from ..estados import Estado
from ..motor import MotorDeteccion
from ..temporizador import Temporizador
from .dibujo import COLOR_ESTADO, dibujar_observacion, texto

VENTANA = "StudyMate - prueba de camara"


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--camara", type=int, default=0, help="índice de la webcam (0 = integrada)")
    p.add_argument("--permitir-movil", action="store_true",
                   help="el móvil/tablet en la mano no pausa (dispositivo permitido)")
    args = p.parse_args()

    permitidas = frozenset({"cell phone"}) if args.permitir_movil else frozenset()
    motor = MotorDeteccion(clases_permitidas=permitidas, indice_camara=args.camara)
    print("Abriendo cámara y cargando modelos...")
    motor.start()
    motor.esperar_listo(timeout=60)
    if motor.error:
        raise SystemExit(f"Error: {motor.error}")

    try:
        while motor.is_alive():
            inst = motor.ultima()
            if inst is not None:
                frame = inst.frame.copy()
                dibujar_observacion(frame, inst.observacion)
                color = COLOR_ESTADO[inst.estado]
                cv2.rectangle(frame, (0, 0), (frame.shape[1] - 1, frame.shape[0] - 1), color, 6)
                texto(frame, f"Estado: {inst.estado.value}", 0, color, 0.8)
                texto(frame, f"Tiempo estudiado: {Temporizador.formatear(inst.estudiado_s)}", 1)
                texto(frame, f"Fotograma sugiere: {inst.candidato.value}", 2, (200, 200, 200), 0.5)
                texto(frame, f"{inst.fps:.1f} fps", 3, (200, 200, 200), 0.5)
                if inst.estado == Estado.DUDOSO and inst.esperando_confirmacion:
                    texto(frame, f"Sigues estudiando? S = si / N = no  "
                                 f"(pendiente {int(inst.pendiente_s)} s)", 4, (0, 230, 255))
                cv2.imshow(VENTANA, frame)

            tecla = cv2.waitKey(15) & 0xFF
            if tecla in (ord("q"), ord("Q"), 27):
                break
            if tecla in (ord("s"), ord("S")):
                motor.confirmar_dudoso(True)
            elif tecla in (ord("n"), ord("N")):
                motor.confirmar_dudoso(False)
            if cv2.getWindowProperty(VENTANA, cv2.WND_PROP_VISIBLE) < 1 and inst is not None:
                break  # se cerró la ventana con la X
    finally:
        motor.detener()
        motor.join(timeout=3)
        cv2.destroyAllWindows()

    if motor.error:
        print(f"Error en la detección: {motor.error}")
    print(f"Tiempo estudiado: {Temporizador.formatear(motor.temporizador.estudiado_s)}")


if __name__ == "__main__":
    main()
