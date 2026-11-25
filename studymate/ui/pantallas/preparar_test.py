"""Hacer un test directamente (sin sesión de estudio): se eligen los apuntes de la
asignatura y el asistente prepara 10 preguntas sobre ellos. No usa la cámara ni
cambia el zoo."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QScrollArea, QVBoxLayout, QWidget

from studymate.gamificacion import zoo as z
from studymate.llm.preguntas import NUM_PREGUNTAS

from ..comun import Pagina, boton, etiqueta, tarjeta
from ..selector_apuntes import SelectorApuntes
from ..zoo_widget import AnimalIcono


class PantallaPrepararTest(Pagina):
    def __init__(self, ventana):
        super().__init__(ventana)
        self.icono = AnimalIcono("pez", 56)
        self.titulo = etiqueta("", "titulo")
        self.titulo.setTextFormat(Qt.PlainText)
        cabecera = QHBoxLayout()
        cabecera.addWidget(self.icono)
        textos = QVBoxLayout()
        textos.addWidget(self.titulo)
        textos.addWidget(etiqueta(f"Elige de qué apuntes quieres el test: {NUM_PREGUNTAS} preguntas, "
                                  "respondiendo con el ratón o con A, B y C.", "subtitulo"))
        cabecera.addLayout(textos, 1)

        self.selector = SelectorApuntes()
        self.error = etiqueta("", "error")
        caja = tarjeta(etiqueta("¿Sobre qué quieres el test?", None), self.selector,
                       etiqueta("Cada apunte marcado es un tema: las preguntas serán solo sobre "
                                "los temas que marques.", "nota"),
                       self.error, espacio=12, margen=24)
        contenido = QWidget()
        capa_contenido = QVBoxLayout(contenido)
        capa_contenido.setContentsMargins(0, 0, 8, 0)
        capa_contenido.addWidget(caja)
        capa_contenido.addStretch()
        desplazable = QScrollArea()
        desplazable.setWidgetResizable(True)
        desplazable.setWidget(contenido)

        botones = QHBoxLayout()
        botones.addWidget(boton("Volver al zoo", None, lambda: ventana.ir("inicio")))
        botones.addStretch()
        self.empezar = boton("Empezar el test", "primario", self._empezar)
        botones.addWidget(self.empezar)

        capa = QVBoxLayout(self)
        capa.setContentsMargins(28, 24, 28, 24)
        capa.setSpacing(16)
        capa.addLayout(cabecera)
        capa.addWidget(desplazable, 1)
        capa.addLayout(botones)

    def al_mostrar(self) -> None:
        recinto = z.cargar(self.ventana.carpeta).recinto(self.ventana.asignatura)
        self.icono.set_especie(recinto.especie)
        self.titulo.setText(f"Test de {recinto.asignatura}")
        self.selector.cargar(self.ventana.carpeta, recinto.asignatura)
        self.error.setText("")
        self.empezar.setFocus()

    def _empezar(self) -> None:
        elegidos = self.selector.elegidos()
        if not elegidos:
            self.error.setText("No hay ningún tema seleccionado para hacer el test. "
                               + ("Marca al menos uno." if self.selector.hay_apuntes()
                                  else "Sube primero los apuntes del tema."))
            return
        self.ventana.empezar_test_libre(elegidos)
