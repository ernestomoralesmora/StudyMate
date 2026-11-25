"""Funciones para dibujar las detecciones sobre el fotograma (solo para pruebas).

cv2.putText no admite tildes ni eñes, por eso los textos en pantalla van sin ellas.
"""

import cv2

from ..estados import Estado
from ..observacion import Observacion

COLOR_ESTADO = {  # BGR
    Estado.ESTUDIANDO: (60, 180, 60),
    Estado.AUSENTE: (60, 60, 200),
    Estado.USANDO_MOVIL: (0, 140, 255),
    Estado.DUDOSO: (0, 210, 230),
}


def _rect(frame, r, color, texto=None):
    x1, y1, x2, y2 = (int(v) for v in r)
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
    if texto:
        cv2.putText(frame, texto, (x1, max(15, y1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)


def dibujar_observacion(frame, obs: Observacion) -> None:
    for c in obs.caras:
        _rect(frame, c, (255, 200, 0), "cara")
    for m in obs.manos:
        _rect(frame, m, (200, 120, 255), "mano")
    for d in obs.dispositivos:
        color = (0, 0, 255) if d.cerca_de_mano else (160, 160, 160)
        texto = f"movil {d.puntuacion:.2f}"
        if d.prob_clip is not None:
            texto += f" clip {d.prob_clip:.2f}"
        texto += " EN MANO" if d.cerca_de_mano else f" (descartado: {d.descartado})" if d.descartado else ""
        _rect(frame, d.recuadro, color, texto)


def texto(frame, linea: str, fila: int, color=(255, 255, 255), escala=0.6) -> None:
    y = 28 + fila * 26
    cv2.putText(frame, linea, (10, y), cv2.FONT_HERSHEY_SIMPLEX, escala, (0, 0, 0), 4)
    cv2.putText(frame, linea, (10, y), cv2.FONT_HERSHEY_SIMPLEX, escala, color, 1)


def mostrar(ventana: str, frame, espera_ms: int = 1) -> int:
    """Muestra el fotograma y devuelve la tecla pulsada, o -1 si no hay.

    Añade abajo cómo salir. Devuelve ord("q") si se cerró la ventana con la X:
    si no, OpenCV la volvería a abrir con la cámara encendida.
    """
    alto = frame.shape[0]
    cv2.putText(frame, "Q o Esc: salir (con esta ventana seleccionada)", (10, alto - 12),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 3)
    cv2.putText(frame, "Q o Esc: salir (con esta ventana seleccionada)", (10, alto - 12),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
    cv2.imshow(ventana, frame)
    tecla = cv2.waitKey(espera_ms) & 0xFF
    if cv2.getWindowProperty(ventana, cv2.WND_PROP_VISIBLE) < 1:
        return ord("q")
    return -1 if tecla == 255 else tecla


def es_salir(tecla: int) -> bool:
    return tecla in (ord("q"), ord("Q"), 27)
