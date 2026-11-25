"""Componente PySide6 que dibuja la pecera animada (RF14).

Pinta con QPainter las figuras de gamificacion/escena.py. No sabe nada de
cómo se califica una sesión: solo muestra el EstadoPecera que se le da.

Uso:
    widget = PeceraWidget(estado)
    widget.set_estado(nuevo_estado)   # al terminar una sesión
"""

import time

from PySide6.QtCore import QTimer
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QSizePolicy, QWidget

from studymate.gamificacion.escena import ALTO, ANCHO, construir_escena
from studymate.gamificacion.pecera import EstadoPecera

from .pintar import pintar_escena

FPS = 30


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
        pintar_escena(p, figuras, self.width(), self.height(), ANCHO, ALTO, radio=26)
        p.end()
