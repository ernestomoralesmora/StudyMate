"""Componentes del zoo: un recinto animado y el icono de un animal."""

import time

from PySide6.QtCore import QTimer
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QSizePolicy, QWidget

from studymate.gamificacion.escena_zoo import ALTO, ANCHO, colocar, construir_recinto, dibujo_animal
from studymate.gamificacion.zoo import ANIMALES, Recinto

from .pintar import pintar_escena

FPS = 24


class RecintoWidget(QWidget):
    """El recinto de una asignatura, con sus animales moviéndose."""

    def __init__(self, recinto: Recinto, parent=None, animado: bool = True):
        super().__init__(parent)
        self._recinto = recinto
        self._inicio = time.monotonic()
        self.setMinimumSize(240, 135)
        politica = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        politica.setHeightForWidth(True)  # siempre con la proporción del dibujo
        self.setSizePolicy(politica)
        self.setAccessibleName("Recinto del zoo")
        self._describir()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.update)
        self._animado = animado
        if animado:
            self._timer.start(int(1000 / FPS))

    def set_recinto(self, recinto: Recinto) -> None:
        self._recinto = recinto
        self._describir()
        self.update()

    def _describir(self) -> None:
        r = self._recinto
        self.setAccessibleDescription(f"{r.animal.habitat} de {r.asignatura}: {r.describir_animales()}, "
                                      f"salud {r.salud} por ciento, nivel {r.nivel}")

    def heightForWidth(self, ancho: int) -> int:
        return int(ancho * ALTO / ANCHO)

    def hasHeightForWidth(self) -> bool:
        return True

    def showEvent(self, evento):
        if self._animado:
            self._timer.start(int(1000 / FPS))
        super().showEvent(evento)

    def hideEvent(self, evento):
        self._timer.stop()
        super().hideEvent(evento)

    def paintEvent(self, _evento):
        figuras = construir_recinto(self._recinto, time.monotonic() - self._inicio)
        p = QPainter(self)
        pintar_escena(p, figuras, self.width(), self.height(), ANCHO, ALTO, radio=16)
        p.end()


class AnimalIcono(QWidget):
    """Un animal solo, para elegirlo o junto al nombre de la asignatura."""

    def __init__(self, especie: str, lado: int = 36, parent=None):
        super().__init__(parent)
        self._especie = especie
        self.setFixedSize(lado, lado)
        self.setAccessibleName(ANIMALES[especie].nombre)

    def set_especie(self, especie: str) -> None:
        self._especie = especie
        self.setAccessibleName(ANIMALES[especie].nombre)
        self.update()

    def paintEvent(self, _evento):
        p = QPainter(self)
        pintar_escena(p, colocar(dibujo_animal(self._especie), 20, 20, 1.0), self.width(), self.height(), 40, 40)
        p.end()
