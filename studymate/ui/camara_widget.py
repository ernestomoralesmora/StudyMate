"""Vista de la cámara dentro de la ventana.

Enseña el último fotograma que ha analizado MotorDeteccion (no abre la cámara
por su cuenta). Puede dibujar encima el sitio del móvil y, si se activa,
permite marcarlo arrastrando un recuadro con el ratón.

Los fotogramas solo se muestran: no se guardan ni se envían.
"""

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from . import estilo
from .comun import frame_a_pixmap


class CamaraWidget(QWidget):
    movil_marcado = Signal(tuple)  # (x1, y1, x2, y2) en píxeles del fotograma

    def __init__(self, parent=None, permitir_marcar: bool = False):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(240, 180)
        self.setMouseTracking(True)
        self.permitir_marcar = permitir_marcar
        self._pixmap = None
        self._tam_frame = (640, 480)
        self._sitio = None          # recuadro del móvil (en el fotograma)
        self._color_sitio = estilo.ACENTO
        self._texto_sitio = ""
        self._arrastre = None       # (inicio, actual) en coordenadas del widget
        self._mensaje = "Abriendo la cámara…"
        self._borde = None
        self.setAccessibleName("Imagen de la cámara")

    # --- Datos que se dibujan --------------------------------------------------
    def set_frame(self, frame_bgr) -> None:
        self._tam_frame = (frame_bgr.shape[1], frame_bgr.shape[0])
        self._pixmap = frame_a_pixmap(frame_bgr)
        self._mensaje = ""
        self.update()

    def set_mensaje(self, texto: str) -> None:
        self._mensaje = texto
        self.update()

    def set_sitio(self, recuadro, color: str = estilo.ACENTO, texto: str = "") -> None:
        self._sitio, self._color_sitio, self._texto_sitio = recuadro, color, texto
        self.update()

    def set_borde(self, color: str | None) -> None:
        self._borde = color
        self.update()

    # --- Conversión entre el widget y el fotograma ---------------------------
    def _area_imagen(self) -> QRectF:
        ancho, alto = self._tam_frame
        escala = min(self.width() / ancho, self.height() / alto)
        w, h = ancho * escala, alto * escala
        return QRectF((self.width() - w) / 2, (self.height() - h) / 2, w, h)

    def _a_frame(self, punto: QPointF) -> tuple[float, float]:
        area = self._area_imagen()
        ancho, alto = self._tam_frame
        x = (punto.x() - area.x()) / area.width() * ancho
        y = (punto.y() - area.y()) / area.height() * alto
        return min(max(x, 0), ancho), min(max(y, 0), alto)

    def _a_widget(self, recuadro) -> QRectF:
        area = self._area_imagen()
        ancho, alto = self._tam_frame
        sx, sy = area.width() / ancho, area.height() / alto
        x1, y1, x2, y2 = recuadro
        return QRectF(area.x() + x1 * sx, area.y() + y1 * sy, (x2 - x1) * sx, (y2 - y1) * sy)

    # --- Ratón: marcar el móvil -------------------------------------------------
    def mousePressEvent(self, evento):
        if self.permitir_marcar and evento.button() == Qt.LeftButton and self._pixmap is not None:
            p = evento.position()
            self._arrastre = (p, p)
            self.update()

    def mouseMoveEvent(self, evento):
        if self._arrastre:
            self._arrastre = (self._arrastre[0], evento.position())
            self.update()
        elif self.permitir_marcar:
            self.setCursor(Qt.CrossCursor)

    def mouseReleaseEvent(self, evento):
        if not self._arrastre:
            return
        inicio, fin = self._arrastre[0], evento.position()
        self._arrastre = None
        (x1, y1), (x2, y2) = self._a_frame(inicio), self._a_frame(fin)
        self.movil_marcado.emit((min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)))
        self.update()

    # --- Dibujo ---------------------------------------------------------------
    def paintEvent(self, _evento):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        area = self._area_imagen()
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(estilo.SUPERFICIE))
        p.drawRoundedRect(area, 14, 14)
        if self._pixmap is not None:
            p.drawPixmap(area.toRect(), self._pixmap)
        if self._mensaje:
            p.setPen(QColor(estilo.TEXTO_2))
            p.drawText(area, Qt.AlignCenter | Qt.TextWordWrap, self._mensaje)
        if self._sitio is not None:
            r = self._a_widget(self._sitio)
            p.setPen(QPen(QColor(self._color_sitio), 3))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(r, 6, 6)
            if self._texto_sitio:
                fuente = QFont(self.font())
                fuente.setPixelSize(13)
                fuente.setBold(True)
                p.setFont(fuente)
                p.drawText(QPointF(r.x(), max(14.0, r.y() - 6)), self._texto_sitio)
        if self._arrastre:
            p.setPen(QPen(QColor(estilo.TEXTO), 2, Qt.DashLine))
            p.setBrush(Qt.NoBrush)
            p.drawRect(QRectF(self._arrastre[0], self._arrastre[1]).normalized())
        if self._borde:
            p.setPen(QPen(QColor(self._borde), 4))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(area.adjusted(2, 2, -2, -2), 12, 12)
        p.end()
