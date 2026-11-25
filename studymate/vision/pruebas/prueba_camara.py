"""Prueba principal de la fase 1: cámara con el estado y el tiempo en pantalla.

Uso (desde la raíz del repositorio):
    python -m studymate.vision.pruebas.prueba_camara [--camara N] [--permitir-movil] [--modelo M]
                                                     [--movil-a-la-vista]

Con --movil-a-la-vista, al empezar deja el móvil sobre la mesa donde la cámara lo
vea (por ejemplo, a un lado): se localiza en unos segundos y luego se vigila su sitio.

Teclas:  Q / Esc = salir   S = sí estaba estudiando   N = no estaba estudiando
"""

import argparse

import cv2

from .. import config
from ..estados import Estado
from ..observacion import SitioMovil
from ..motor import MotorDeteccion
from ..temporizador import Temporizador
from .dibujo import COLOR_ESTADO, dibujar_observacion, texto

VENTANA = "StudyMate - prueba de camara"


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--camara", type=int, default=0, help="índice de la webcam (0 = integrada)")
    p.add_argument("--permitir-movil", action="store_true",
                   help="el móvil/tablet en la mano no pausa (dispositivo permitido)")
    p.add_argument("--modelo", default=config.MODELO_OBJETOS,
                   choices=["yolo", "yolo_s", "yolo_s416", "yolo_m", "objetos_preciso", "objetos"],
                   help="detector del móvil (para comparar)")
    p.add_argument("--movil-a-la-vista", action="store_true",
                   help="vigilar el sitio donde se deja el móvil al empezar")
    args = p.parse_args()

    permitidas = frozenset({"cell phone"}) if args.permitir_movil else frozenset()
    motor = MotorDeteccion(clases_permitidas=permitidas, indice_camara=args.camara,
                           modelo_movil=args.modelo, movil_a_la_vista=args.movil_a_la_vista)
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
                sitio = inst.sitio_movil
                if sitio != SitioMovil.SIN_USAR:
                    avisos = {
                        SitioMovil.BUSCANDO: "Movil: dejalo sobre la mesa, a la vista...",
                        SitioMovil.NO_ENCONTRADO: "Movil: no lo veo, se vigila solo la mano",
                        SitioMovil.EN_SU_SITIO: "Movil: en su sitio",
                        SitioMovil.FUERA: "Movil: NO esta en su sitio",
                    }
                    texto(frame, avisos[sitio], 5, (255, 220, 120), 0.5)
                recuadro = motor.recuadro_aparcado
                if recuadro is not None and sitio in (SitioMovil.EN_SU_SITIO, SitioMovil.FUERA):
                    x1, y1, x2, y2 = (int(v) for v in recuadro)
                    color_sitio = (60, 180, 60) if sitio == SitioMovil.EN_SU_SITIO else (0, 140, 255)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color_sitio, 2)
                    cv2.putText(frame, "sitio del movil", (x1, max(15, y1 - 6)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.45, color_sitio, 1)
                if inst.estado == Estado.DUDOSO and inst.esperando_confirmacion:
                    pregunta = ("Has cogido el movil? S = no, sigo estudiando / N = si"
                                if sitio == SitioMovil.FUERA else "Sigues estudiando? S = si / N = no")
                    texto(frame, f"{pregunta}  (pendiente {int(inst.pendiente_s)} s)", 4, (0, 230, 255))
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
