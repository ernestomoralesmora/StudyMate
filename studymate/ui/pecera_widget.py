"""Componente PySide6 que dibuja la pecera animada (RF14).

Pinta con QPainter las figuras de gamificacion/escena.py. No sabe nada de
cómo se califica una sesión: solo muestra el EstadoPecera que se le da.

Uso:
    widget = PeceraWidget(estado)
    widget.set_estado(nuevo_estado)   # al terminar una sesión
"""

import time

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QBrush, QColor, QLinearGradient, QPainter, QPainterPath, QPen, QPolygonF
from PySide6.QtWidgets import QSizePolicy, QWidget

from studymate.gamificacion.escena import ALTO, ANCHO, construir_escena
from studymate.gamificacion.pecera import EstadoPecera

FPS = 30


def _color(hex_, alfa=1.0):
    c = QColor(hex_)
    c.setAlphaF(max(0.0, min(1.0, alfa)))
    return c


class PeceraWidget(QWidget):
    def __init__(self, estado: EstadoPecera, parent=None):
        super().__init__(parent)
        self._estado = estado
        self._inicio = time.monotonic()
        self.setMinimumSize(360, 210)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setAccessibleName("Pecera")
        self._actualizar_descripcion()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.update)
        self._timer.start(int(1000 / FPS))

    def set_estado(self, estado: EstadoPecera) -> None:
        self._estado = estado
        self._actualizar_descripcion()
        self.update()

    def _actualizar_descripcion(self) -> None:
        e = self._estado
        self.setAccessibleDescription(
            f"{len(e.peces)} peces, agua {e.estado_agua}, salud {e.salud} por ciento"
        )

    # Pausar la animación cuando no se ve, para no gastar CPU durante el estudio.
    def showEvent(self, evento):
        self._timer.start(int(1000 / FPS))
        super().showEvent(evento)

    def hideEvent(self, evento):
        self._timer.stop()
        super().hideEvent(evento)

    def paintEvent(self, _evento):
        t = time.monotonic() - self._inicio
        figuras = construir_escena(self._estado, t)

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        # Escalar la escena lógica al tamaño del widget manteniendo la proporción.
        escala = min(self.width() / ANCHO, self.height() / ALTO)
        dx = (self.width() - ANCHO * escala) / 2
        dy = (self.height() - ALTO * escala) / 2
        p.translate(dx, dy)
        p.scale(escala, escala)

        recorte = QPainterPath()
        recorte.addRoundedRect(QRectF(0, 0, ANCHO, ALTO), 26, 26)
        p.setClipPath(recorte)

        for f in figuras:
            alfa = f.get("alfa", 1.0)
            tipo = f["tipo"]
            if tipo == "degradado":
                g = QLinearGradient(0, f["y"], 0, f["y"] + f["h"])
                g.setColorAt(0, _color(f["arriba"]))
                g.setColorAt(1, _color(f["abajo"]))
                p.setPen(Qt.NoPen)
                p.setBrush(QBrush(g))
                p.drawRect(QRectF(f["x"], f["y"], f["w"], f["h"]))
            elif tipo == "rect":
                p.setPen(Qt.NoPen)
                p.setBrush(_color(f["relleno"], alfa))
                p.drawRect(QRectF(f["x"], f["y"], f["w"], f["h"]))
            elif tipo == "elipse":
                p.setPen(Qt.NoPen)
                p.setBrush(_color(f["relleno"], alfa))
                p.drawEllipse(QPointF(f["cx"], f["cy"]), f["rx"], f["ry"])
            elif tipo == "circulo_borde":
                p.setPen(QPen(_color(f["color"], alfa), 2))
                p.setBrush(Qt.NoBrush)
                p.drawEllipse(QPointF(f["cx"], f["cy"]), f["r"], f["r"])
            elif tipo == "poligono":
                p.setPen(Qt.NoPen)
                p.setBrush(_color(f["relleno"], alfa))
                p.drawPolygon(QPolygonF([QPointF(x, y) for x, y in f["puntos"]]))
            elif tipo == "linea":
                lapiz = QPen(_color(f["color"], alfa), f["grosor"])
                lapiz.setCapStyle(Qt.RoundCap)
                lapiz.setJoinStyle(Qt.RoundJoin)
                p.setPen(lapiz)
                p.setBrush(Qt.NoBrush)
                p.drawPolyline(QPolygonF([QPointF(x, y) for x, y in f["puntos"]]))
        p.end()
