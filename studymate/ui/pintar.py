"""Pinta con QPainter las figuras de gamificacion/escena.py y escena_zoo.py."""

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QLinearGradient, QPainter, QPainterPath, QPen, QPolygonF


def color(hex_: str, alfa: float = 1.0) -> QColor:
    c = QColor(hex_)
    c.setAlphaF(max(0.0, min(1.0, alfa)))
    return c


def pintar_escena(p: QPainter, figuras: list[dict], ancho: float, alto: float,
                  ancho_vista: float, alto_vista: float, radio: float = 0) -> None:
    """Escala la escena lógica (ancho_vista x alto_vista) al hueco disponible,
    manteniendo la proporción y centrada, recorta las esquinas y la pinta."""
    p.save()
    p.setRenderHint(QPainter.Antialiasing)
    escala = min(ancho / ancho_vista, alto / alto_vista)
    p.translate((ancho - ancho_vista * escala) / 2, (alto - alto_vista * escala) / 2)
    p.scale(escala, escala)
    if radio:
        recorte = QPainterPath()
        recorte.addRoundedRect(QRectF(0, 0, ancho_vista, alto_vista), radio, radio)
        p.setClipPath(recorte)
    pintar_figuras(p, figuras)
    p.restore()


def pintar_figuras(p: QPainter, figuras: list[dict]) -> None:
    for f in figuras:
        alfa = f.get("alfa", 1.0)
        tipo = f["tipo"]
        if tipo == "degradado":
            g = QLinearGradient(0, f["y"], 0, f["y"] + f["h"])
            g.setColorAt(0, color(f["arriba"]))
            g.setColorAt(1, color(f["abajo"]))
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(g))
            p.drawRect(QRectF(f["x"], f["y"], f["w"], f["h"]))
        elif tipo == "rect":
            p.setPen(Qt.NoPen)
            p.setBrush(color(f["relleno"], alfa))
            p.drawRect(QRectF(f["x"], f["y"], f["w"], f["h"]))
        elif tipo == "elipse":
            p.setPen(Qt.NoPen)
            p.setBrush(color(f["relleno"], alfa))
            p.drawEllipse(QPointF(f["cx"], f["cy"]), f["rx"], f["ry"])
        elif tipo == "circulo_borde":
            p.setPen(QPen(color(f["color"], alfa), 2))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(QPointF(f["cx"], f["cy"]), f["r"], f["r"])
        elif tipo == "poligono":
            p.setPen(Qt.NoPen)
            p.setBrush(color(f["relleno"], alfa))
            p.drawPolygon(QPolygonF([QPointF(x, y) for x, y in f["puntos"]]))
        elif tipo == "linea":
            lapiz = QPen(color(f["color"], alfa), f["grosor"])
            lapiz.setCapStyle(Qt.RoundCap)
            lapiz.setJoinStyle(Qt.RoundJoin)
            p.setPen(lapiz)
            p.setBrush(Qt.NoBrush)
            p.drawPolyline(QPolygonF([QPointF(x, y) for x, y in f["puntos"]]))
