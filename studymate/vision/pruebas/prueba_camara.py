"""Prueba principal de la fase 1: cámara con el estado y el tiempo en pantalla.

Uso (desde la raíz del repositorio):
    python -m studymate.vision.pruebas.prueba_camara [--camara N] [--permitir-movil] [--modelo M]
                                                     [--movil-a-la-vista]

Antes de empezar hay 30 s de preparación (el tiempo no cuenta). Con
--movil-a-la-vista, deja el móvil en la mesa donde la cámara lo vea y arrastra
con el ratón un recuadro sobre él. Enter empieza la sesión antes; si no, empieza
sola a los 30 s. Si el móvil desaparece de su sitio, suena un aviso y pregunta.

Teclas:  Q / Esc = salir   S = sí estaba estudiando   N = no estaba estudiando
         Enter / Espacio = empezar la sesión (durante la preparación)
         Ratón: arrastrar un recuadro sobre el móvil (se puede volver a marcar)
"""

import argparse

import cv2

from .. import config
from ..estados import Estado
from ..observacion import SitioMovil
from ..preparacion import Preparacion
from ..motor import MotorDeteccion
from ..temporizador import Temporizador
from .dibujo import COLOR_ESTADO, dibujar_observacion, texto

VENTANA = "StudyMate - prueba de camara"


def avisar() -> None:
    """Aviso sonoro (en Windows, el sonido de alerta del sistema)."""
    try:
        import winsound
        winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
    except Exception:  # otros sistemas
        print("\a", end="", flush=True)


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
    p.add_argument("--registrar-aparcado", metavar="ARCHIVO.csv",
                   help="guarda cada segundo los números de la vigilancia del móvil (nunca imágenes)")
    args = p.parse_args()
    registro, ultimo_registro = None, 0.0
    if args.registrar_aparcado:
        import csv
        archivo_registro = open(args.registrar_aparcado, "w", newline="", encoding="utf-8")
        registro = csv.writer(archivo_registro)
        registro.writerow(["t", "estado", "sitio_movil", "candidato", "caras", "manos",
                           "movil_detectado", "visto_en_mano", "mejor_busqueda",
                           "yolo_sitio", "parecido", "recuadro_sitio", "cambio"])

    permitidas = frozenset({"cell phone"}) if args.permitir_movil else frozenset()
    motor = MotorDeteccion(clases_permitidas=permitidas, indice_camara=args.camara,
                           modelo_movil=args.modelo, movil_a_la_vista=args.movil_a_la_vista)
    print("Abriendo cámara y cargando modelos...")
    motor.start()
    motor.esperar_listo(timeout=60)
    if motor.error:
        raise SystemExit(f"Error: {motor.error}")

    import time
    preparacion = Preparacion(time.monotonic())
    arrastre = {"inicio": None, "actual": None}

    def raton(evento, x, y, _flags, _param):
        """Arrastrar un recuadro sobre el móvil en la imagen en directo."""
        if not args.movil_a_la_vista:
            return
        if evento == cv2.EVENT_LBUTTONDOWN:
            arrastre["inicio"] = arrastre["actual"] = (x, y)
        elif evento == cv2.EVENT_MOUSEMOVE and arrastre["inicio"]:
            arrastre["actual"] = (x, y)
        elif evento == cv2.EVENT_LBUTTONUP and arrastre["inicio"]:
            (x1, y1), arrastre["inicio"] = arrastre["inicio"], None
            inst_ = motor.ultima()
            if inst_ is not None and preparacion.marcar_movil(x1, y1, x, y):
                motor.marcar_movil(inst_.frame, preparacion.movil_marcado)

    cv2.namedWindow(VENTANA)
    cv2.setMouseCallback(VENTANA, raton)
    estado_anterior = None
    try:
        while motor.is_alive():
            inst = motor.ultima()
            if inst is not None:
                frame = inst.frame.copy()
                dibujar_observacion(frame, inst.observacion)
                if inst.en_sesion:
                    color = COLOR_ESTADO[inst.estado]
                    cv2.rectangle(frame, (0, 0), (frame.shape[1] - 1, frame.shape[0] - 1), color, 6)
                    texto(frame, f"Estado: {inst.estado.value}", 0, color, 0.8)
                    texto(frame, f"Tiempo estudiado: {Temporizador.formatear(inst.estudiado_s)}", 1)
                    texto(frame, f"Fotograma sugiere: {inst.candidato.value}", 2, (200, 200, 200), 0.5)
                texto(frame, f"{inst.fps:.1f} fps", 3, (200, 200, 200), 0.5)
                sitio = inst.sitio_movil
                if sitio != SitioMovil.SIN_USAR:
                    v = motor.vigilante
                    buscando = ("Movil: sin marcar" if config.LOCALIZAR_APARCADO == "a_mano"
                                else "Movil: ensenalo a la camara y dejalo en la mesa")
                    if v is not None and v.visto_en_mano:
                        buscando = "Movil: visto! Dejalo en la mesa y aparta la mano"
                        x1, y1, x2, y2 = (int(c) for c in v.ultimo_en_mano)
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 220, 120), 2)
                    elif v is not None and v.mejor_busqueda:
                        p_mejor, r_mejor = v.mejor_busqueda
                        buscando = (f"Movil: buscando... mejor {p_mejor:.2f} "
                                    f"(minimo {config.UMBRAL_APARCADO:.2f})")
                        if sitio == SitioMovil.BUSCANDO:
                            x1, y1, x2, y2 = (int(c) for c in r_mejor)
                            cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 220, 120), 1)
                    avisos = {
                        SitioMovil.BUSCANDO: buscando,
                        SitioMovil.NO_ENCONTRADO: "Movil: sin marcar, se vigila solo la mano",
                        SitioMovil.EN_SU_SITIO: "Movil: en su sitio",
                        SitioMovil.FUERA: "Movil: NO esta en su sitio",
                    }
                    if v is not None and sitio in (SitioMovil.EN_SU_SITIO, SitioMovil.FUERA):
                        avisos[sitio] += (f"  (parecido {v.ultima_similitud:.2f}, "
                                          f"cambio {100 * v.ultimo_cambio:.0f} %)")
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
                if arrastre["inicio"] and arrastre["actual"]:
                    cv2.rectangle(frame, arrastre["inicio"], arrastre["actual"], (255, 255, 255), 1)
                if not inst.en_sesion:
                    ahora_ = time.monotonic()
                    cv2.rectangle(frame, (0, 0), (frame.shape[1] - 1, frame.shape[0] - 1), (255, 220, 120), 6)
                    texto(frame, "PREPARACION (el tiempo no cuenta)", 0, (255, 220, 120), 0.8)
                    texto(frame, preparacion.mensaje(ahora_, args.movil_a_la_vista), 1, (255, 255, 255), 0.5)
                    if preparacion.debe_empezar(ahora_):
                        preparacion.empezar()
                        motor.empezar_sesion()
                elif inst.estado != estado_anterior:
                    # Alarma: el móvil no está en su sitio y se pregunta.
                    if inst.estado == Estado.DUDOSO and sitio == SitioMovil.FUERA:
                        avisar()
                    estado_anterior = inst.estado
                cv2.imshow(VENTANA, frame)

            if registro is not None and inst is not None:
                ahora = time.monotonic()
                if ahora - ultimo_registro >= 0.5:
                    ultimo_registro = ahora
                    v = motor.vigilante
                    o = inst.observacion
                    registro.writerow([
                        f"{ahora:.1f}", inst.estado.value, inst.sitio_movil.value, inst.candidato.value,
                        len(o.caras), len(o.manos),
                        max((f"{d.puntuacion:.2f}" for d in o.dispositivos), default=""),
                        int(bool(v and v.visto_en_mano)),
                        f"{v.mejor_busqueda[0]:.2f}" if v and v.mejor_busqueda else "",
                        f"{v.ultima_yolo:.2f}" if v else "", f"{v.ultima_similitud:.2f}" if v else "",
                        "" if not (v and v.recuadro) else " ".join(f"{c:.0f}" for c in v.recuadro),
                        f"{v.ultimo_cambio:.2f}" if v else "",
                    ])
                    archivo_registro.flush()

            tecla = cv2.waitKey(15) & 0xFF
            if tecla in (ord("q"), ord("Q"), 27):
                break
            if tecla in (ord("s"), ord("S")):
                motor.confirmar_dudoso(True)
            elif tecla in (ord("n"), ord("N")):
                motor.confirmar_dudoso(False)
            elif tecla in (13, 32) and not motor.en_sesion:  # Enter o Espacio
                preparacion.empezar()
                motor.empezar_sesion()
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
