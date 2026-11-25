"""Diálogo para añadir una asignatura al zoo y elegir su animal (uno por asignatura)."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QGraphicsOpacityEffect, QGridLayout, QHBoxLayout, QLineEdit, QPushButton,
                               QVBoxLayout)

from studymate.gamificacion import zoo as z

from .comun import boton, etiqueta
from .zoo_widget import AnimalIcono


class BotonAnimal(QPushButton):
    """Botón con el dibujo del animal y su nombre debajo."""

    def __init__(self, especie: str, dueno: str | None):
        super().__init__()
        animal = z.ANIMALES[especie]
        self.especie = especie
        self.setCheckable(True)
        self.setMinimumSize(96, 96)
        self.setObjectName("animal")
        capa = QVBoxLayout(self)
        capa.setContentsMargins(6, 8, 6, 6)
        capa.setSpacing(2)
        icono = AnimalIcono(especie, 44)
        icono.setAttribute(Qt.WA_TransparentForMouseEvents)
        nombre = etiqueta(animal.nombre, "nota", ajustar=False)
        nombre.setAlignment(Qt.AlignCenter)
        nombre.setAttribute(Qt.WA_TransparentForMouseEvents)
        capa.addWidget(icono, 0, Qt.AlignHCenter)
        capa.addWidget(nombre)
        if dueno:
            atenuar = QGraphicsOpacityEffect(icono)
            atenuar.setOpacity(0.3)
            icono.setGraphicsEffect(atenuar)
            self.setEnabled(False)
            self.setToolTip(f"Ya es de {dueno}")
            self.setAccessibleName(f"{animal.nombre}, ya es de {dueno}")
        else:
            self.setToolTip(f"{animal.nombre} · {animal.habitat}")
            self.setAccessibleName(f"{animal.nombre}, recinto: {animal.habitat}")


class DialogoAsignatura(QDialog):
    def __init__(self, zoo: z.Zoo, parent=None):
        super().__init__(parent)
        self.zoo = zoo
        self.recinto: z.Recinto | None = None
        self.setWindowTitle("Añadir una asignatura")
        self.setModal(True)

        self.nombre = QLineEdit()
        self.nombre.setPlaceholderText("Por ejemplo, Estadística")
        self.nombre.setMaxLength(60)
        titulo_nombre = etiqueta("¿Qué asignatura es?")
        titulo_nombre.setStyleSheet("font-weight: 600;")
        titulo_nombre.setBuddy(self.nombre)

        self.botones: list[BotonAnimal] = []
        rejilla = QGridLayout()
        rejilla.setSpacing(8)
        for i, especie in enumerate(z.ANIMALES):
            b = BotonAnimal(especie, zoo.dueno(especie))
            b.clicked.connect(lambda _=False, e=especie: self._elegir(e))
            self.botones.append(b)
            rejilla.addWidget(b, i // 5, i % 5)
        self.habitat = etiqueta("", "nota")
        self.error = etiqueta("", "error")
        self.aceptar = boton("Añadir al zoo", "primario", self._aceptar)
        fila = QHBoxLayout()
        fila.addWidget(boton("Cancelar", None, self.reject))
        fila.addStretch()
        fila.addWidget(self.aceptar)

        capa = QVBoxLayout(self)
        capa.setContentsMargins(24, 24, 24, 24)
        capa.setSpacing(12)
        capa.addWidget(etiqueta("Nueva asignatura", "cifra"))
        capa.addWidget(titulo_nombre)
        capa.addWidget(self.nombre)
        elige = etiqueta("Elige su animal (cada asignatura tiene uno distinto)")
        elige.setStyleSheet("font-weight: 600;")
        capa.addWidget(elige)
        capa.addLayout(rejilla)
        capa.addWidget(self.habitat)
        capa.addWidget(self.error)
        capa.addLayout(fila)

        libres = zoo.especies_libres()
        self.especie = libres[0] if libres else None
        if self.especie:
            self._elegir(self.especie)
        else:
            self.error.setText("Ya tienes 10 asignaturas: no quedan animales libres.")
            self.aceptar.setEnabled(False)
        self.nombre.setFocus()

    def _elegir(self, especie: str) -> None:
        self.especie = especie
        for b in self.botones:
            b.setChecked(b.especie == especie)
        animal = z.ANIMALES[especie]
        self.habitat.setText(f"Su recinto será: {animal.habitat.lower()}.")

    def _aceptar(self) -> None:
        try:
            self.recinto = self.zoo.anadir(self.nombre.text(), self.especie)
        except z.ErrorZoo as error:
            self.error.setText(str(error))
            return
        z.guardar(self.zoo)
        self.accept()
