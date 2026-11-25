"""El compañero de estudio: la cara del logo con expresiones (RF: compañero).

Cambia de cara según lo que pasa: concentrado mientras estudias, preocupado si
coges el móvil, buscándote si te vas, con una duda si no lo tiene claro,
relajado en el descanso y contento o triste al acabar. Parpadea de vez en cuando.
Se dibuja con QPainter (no usa imágenes).
"""

import math
import time

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from . import estilo

EXPRESIONES = {
    # expresión: (color del borde, ojos, boca, extra)
    "concentrado": (estilo.ACENTO, "abiertos", "sonrisa", None),
    "feliz": (estilo.ACENTO, "felices", "sonrisa_grande", None),
    "preocupado": (estilo.MOVIL, "abiertos", "triste", "cejas"),
    "buscando": (estilo.AUSENTE, "a_un_lado", "o", None),
    "pregunta": (estilo.DUDOSO, "abiertos", "recta", "?"),
    "descanso": (estilo.CIAN, "cerrados", "sonrisa", "z"),
    "triste": (estilo.MOVIL, "abiertos", "triste", None),
    "neutro": (estilo.ACENTO, "abiertos", "recta", None),
}
POR_ESTADO = {
    "ESTUDIANDO": "concentrado",
    "USANDO_MOVIL": "preocupado",
    "AUSENTE": "buscando",
    "DUDOSO": "pregunta",
}


class Companero(QWidget):
    def __init__(self, expresion: str = "concentrado", lado_minimo: int = 120, parent=None):
        super().__init__(parent)
        self._expresion = expresion
        self._inicio = time.monotonic()
        self.setMinimumSize(lado_minimo, lado_minimo)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.setAccessibleName("Compañero de estudio")
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.update)
        self._timer.start(60)

    def set_expresion(self, expresion: str) -> None:
        if expresion in EXPRESIONES and expresion != self._expresion:
            self._expresion = expresion
            self.setAccessibleDescription(expresion)
            self.update()

    def set_estado(self, estado: str) -> None:
        self.set_expresion(POR_ESTADO.get(estado, "neutro"))

    def hideEvent(self, evento):
        self._timer.stop()
        super().hideEvent(evento)

    def showEvent(self, evento):
        self._timer.start(60)
        super().showEvent(evento)

    def paintEvent(self, _evento):
        color, ojos, boca, extra = EXPRESIONES[self._expresion]
        t = time.monotonic() - self._inicio
        lado = min(self.width(), self.height())
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.translate((self.width() - lado) / 2, (self.height() - lado) / 2)
        p.scale(lado / 100, lado / 100)

        # Flota un poco arriba y abajo.
        p.translate(0, 1.5 * math.sin(t * 1.6))
        acento = QColor(color)

        # Cuerpo: cuadrado redondeado con borde de neón (halo suave detrás).
        for ancho, alfa in ((9, 0.10), (6, 0.18)):
            halo = QColor(acento)
            halo.setAlphaF(alfa)
            p.setPen(QPen(halo, ancho))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(QRectF(10, 10, 80, 80), 24, 24)
        p.setPen(QPen(acento, 3))
        p.setBrush(QColor("#0B1A14"))
        p.drawRoundedRect(QRectF(10, 10, 80, 80), 24, 24)

        # Mejillas.
        mejilla = QColor(estilo.CIAN)
        mejilla.setAlphaF(0.55)
        p.setPen(Qt.NoPen)
        p.setBrush(mejilla)
        p.drawEllipse(QPointF(28, 60), 5, 3.5)
        p.drawEllipse(QPointF(72, 60), 5, 3.5)

        # Ojos (parpadeo cada ~4 s si están abiertos).
        parpadeo = (t % 4.2) < 0.14
        lapiz = QPen(acento, 3.2)
        lapiz.setCapStyle(Qt.RoundCap)
        p.setPen(lapiz)
        for x in (38, 62):
            if ojos == "abiertos" and not parpadeo:
                p.setPen(Qt.NoPen)
                p.setBrush(acento)
                p.drawEllipse(QPointF(x, 45), 4.5, 5.5)
                p.setPen(lapiz)
            elif ojos == "a_un_lado" and not parpadeo:
                desplazamiento = 3 * math.sin(t * 2)
                p.setPen(Qt.NoPen)
                p.setBrush(acento)
                p.drawEllipse(QPointF(x + desplazamiento, 45), 4.5, 5.5)
                p.setPen(lapiz)
            elif ojos == "felices":
                arco = QPainterPath(QPointF(x - 5, 47))
                arco.quadTo(QPointF(x, 39), QPointF(x + 5, 47))
                p.setBrush(Qt.NoBrush)
                p.drawPath(arco)
            else:  # cerrados o parpadeando
                p.drawLine(QPointF(x - 5, 46), QPointF(x + 5, 46))

        if extra == "cejas":
            p.drawLine(QPointF(32, 35), QPointF(42, 38))
            p.drawLine(QPointF(68, 35), QPointF(58, 38))

        # Boca.
        p.setBrush(Qt.NoBrush)
        if boca in ("sonrisa", "sonrisa_grande"):
            hondo = 74 if boca == "sonrisa_grande" else 70
            camino = QPainterPath(QPointF(41, 64))
            camino.quadTo(QPointF(50, hondo), QPointF(59, 64))
            p.drawPath(camino)
        elif boca == "triste":
            camino = QPainterPath(QPointF(42, 70))
            camino.quadTo(QPointF(50, 63), QPointF(58, 70))
            p.drawPath(camino)
        elif boca == "o":
            p.drawEllipse(QPointF(50, 67), 3.5, 4)
        else:
            p.drawLine(QPointF(43, 67), QPointF(57, 67))

        # Detalles: interrogación o "z" del descanso.
        if extra in ("?", "z"):
            fuente = QFont(self.font())
            fuente.setPixelSize(18 if extra == "?" else 14)
            fuente.setBold(True)
            p.setFont(fuente)
            p.setPen(acento)
            y = 22 + (2 * math.sin(t * 2) if extra == "z" else 0)
            p.drawText(QRectF(70, y - 16, 26, 22), Qt.AlignCenter, extra)
        p.end()
