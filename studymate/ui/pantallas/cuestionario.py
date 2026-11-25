"""Cuestionario antes de cada sesión (RF5, RF11): con él se adapta el plan."""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QComboBox, QHBoxLayout, QPlainTextEdit,
                               QPushButton, QScrollArea, QSizePolicy, QSpinBox, QVBoxLayout, QWidget)

from studymate.gamificacion import zoo as z
from studymate.llm.apuntes import unir
from studymate.llm.cuestionario import NIVELES_CANSANCIO, NIVELES_CONOCIMIENTO, PerfilSesion

from ..comun import Pagina, boton, etiqueta, tarjeta
from ..selector_apuntes import SelectorApuntes, nombre_tema
from ..zoo_widget import AnimalIcono


class OpcionMovil(QPushButton):
    """Tarjeta que se puede elegir (icono, título y explicación) para decir dónde va el móvil."""

    def __init__(self, icono: str, titulo: str, texto: str):
        super().__init__()
        self.setObjectName("opcion")
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setAccessibleName(f"{titulo}. {texto}")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        capa = QHBoxLayout(self)
        capa.setContentsMargins(16, 14, 16, 14)
        capa.setSpacing(14)
        dibujo = etiqueta(icono, "icono_opcion")
        dibujo.setAlignment(Qt.AlignCenter)
        textos = QVBoxLayout()
        textos.setSpacing(4)
        nombre = etiqueta(titulo)
        nombre.setStyleSheet("font-weight: 600;")
        explicacion = etiqueta(texto, "nota")
        textos.addWidget(nombre)
        textos.addWidget(explicacion)
        capa.addWidget(dibujo)
        capa.addLayout(textos, 1)
        for w in (dibujo, nombre, explicacion):  # el clic lo recibe el botón
            w.setAttribute(Qt.WA_TransparentForMouseEvents)

    def sizeHint(self):
        return self.layout().sizeHint()

    def minimumSizeHint(self):
        return self.layout().minimumSize()


def _pregunta(texto: str, campo, ayuda: str | None = None) -> QWidget:
    caja = QWidget()
    capa = QVBoxLayout(caja)
    capa.setContentsMargins(0, 0, 0, 6)
    capa.setSpacing(6)
    titulo = etiqueta(texto)
    titulo.setStyleSheet("font-weight: 600;")
    titulo.setBuddy(campo)  # lectores de pantalla: la pregunta nombra el campo
    capa.addWidget(titulo)
    if ayuda:
        capa.addWidget(etiqueta(ayuda, "nota"))
    capa.addWidget(campo)
    return caja


class PantallaCuestionario(Pagina):
    def __init__(self, ventana):
        super().__init__(ventana)
        self.tiempo = QSpinBox()
        self.tiempo.setRange(10, 480)
        self.tiempo.setSingleStep(5)
        self.tiempo.setSuffix(" min")
        self.concentracion = QSpinBox()
        self.concentracion.setRange(5, 120)
        self.concentracion.setSingleStep(5)
        self.concentracion.setSuffix(" min")
        self.cansancio = QComboBox()
        for k, v in NIVELES_CANSANCIO.items():
            self.cansancio.addItem(f"{k} · {v}", k)
        self.conocimiento = QComboBox()
        for k, v in NIVELES_CONOCIMIENTO.items():
            self.conocimiento.addItem(f"{k} · {v}", k)
        # Forma de estudiar: con apuntes, con tablet o con las dos cosas. Con tablet, lo que
        # parezca un móvil en la mano no pausa (COCO no distingue tablet de móvil), pero
        # se sigue vigilando el sitio del móvil si está a la vista.
        self.con_apuntes = QCheckBox("Con apuntes (papel, libro…)")
        self.con_tablet = QCheckBox("Con tablet")
        dispositivos = QWidget()
        fila = QVBoxLayout(dispositivos)
        fila.setContentsMargins(0, 0, 0, 0)
        fila.addWidget(self.con_apuntes)
        fila.addWidget(self.con_tablet)
        # Dónde va a estar el móvil: dos tarjetas, se elige una.
        self.movil_mesa = OpcionMovil(
            "📱", "Sobre la mesa, a la vista",
            "Antes de empezar marcarás dónde está. Si lo coges o lo mueves de ahí, te avisamos.")
        self.movil_guardado = OpcionMovil(
            "🎒", "Guardado, fuera de la vista",
            "En la mochila, en otra habitación… Solo se pausa si aparece en tu mano.")
        self.donde_movil = QButtonGroup(self)
        self.donde_movil.setExclusive(True)
        caja_movil = QWidget()
        capa_movil = QHBoxLayout(caja_movil)
        capa_movil.setContentsMargins(0, 0, 0, 0)
        capa_movil.setSpacing(12)
        for opcion in (self.movil_mesa, self.movil_guardado):
            self.donde_movil.addButton(opcion)
            capa_movil.addWidget(opcion, 1)
        self.movil_mesa.setChecked(True)
        self.con_test = QCheckBox("Quiero un test de 10 preguntas al final de cada bloque")
        # Apuntes guardados de ESTA asignatura (se marcan los de hoy) y texto pegado solo para hoy.
        self.selector = SelectorApuntes()
        self.apuntes = QPlainTextEdit()
        self.apuntes.setPlaceholderText("O pega aquí un texto solo para esta sesión (opcional).")
        self.apuntes.setFixedHeight(70)
        caja_apuntes = QWidget()
        capa_apuntes = QVBoxLayout(caja_apuntes)
        capa_apuntes.setContentsMargins(0, 0, 0, 0)
        capa_apuntes.setSpacing(8)
        capa_apuntes.addWidget(self.selector)
        capa_apuntes.addWidget(self.apuntes)
        self.error = etiqueta("", "error")

        formulario = tarjeta(
            _pregunta("¿Qué vas a estudiar hoy?", caja_apuntes,
                      "Marca los apuntes de hoy: cada uno será un tema del plan. Los que subes se quedan "
                      "guardados en esta asignatura para las próximas veces. Se guarda solo su texto, en "
                      "este ordenador, y al asistente se le manda solo la parte de cada tema."),
            _pregunta("¿Cuánto tiempo tienes hoy para estudiar?", self.tiempo),
            _pregunta("¿Cuántos minutos seguidos sueles aguantar concentrado?", self.concentracion,
                      "Con esto se decide lo largo que es cada bloque."),
            _pregunta("¿Cómo de cansado estás?", self.cansancio),
            _pregunta("¿Cuánto sabes ya del tema?", self.conocimiento),
            _pregunta("¿Cómo vas a estudiar?", dispositivos,
                      "Marca una o las dos. Si estudias con tablet, usarla no pausará el tiempo."),
            _pregunta("¿Dónde vas a dejar el móvil?", caja_movil),
            _pregunta("Test", self.con_test),
            espacio=14, margen=24,
        )

        contenido = QWidget()
        capa_contenido = QVBoxLayout(contenido)
        capa_contenido.setContentsMargins(0, 0, 8, 0)
        capa_contenido.addWidget(formulario)
        capa_contenido.addStretch()
        desplazable = QScrollArea()
        desplazable.setWidgetResizable(True)
        desplazable.setWidget(contenido)

        botones = QHBoxLayout()
        botones.addWidget(boton("Volver al zoo", None, lambda: ventana.ir("inicio")))
        botones.addStretch()
        self.siguiente = boton("Crear mi plan", "primario", self._enviar)
        botones.addWidget(self.siguiente)

        capa = QVBoxLayout(self)
        capa.setContentsMargins(28, 24, 28, 24)
        capa.setSpacing(14)
        self.icono = AnimalIcono("pez", 56)
        self.titulo = etiqueta("", "titulo")
        self.titulo.setTextFormat(Qt.PlainText)
        cabecera = QHBoxLayout()
        cabecera.addWidget(self.icono)
        textos = QVBoxLayout()
        textos.addWidget(self.titulo)
        textos.addWidget(etiqueta("Unas preguntas rápidas para adaptar esta sesión a cómo estás hoy.",
                                  "subtitulo"))
        cabecera.addLayout(textos, 1)
        capa.addLayout(cabecera)
        capa.addWidget(desplazable, 1)
        capa.addWidget(self.error)
        capa.addLayout(botones)

    def _recinto(self) -> z.Recinto | None:
        return z.cargar(self.ventana.carpeta).recinto(self.ventana.asignatura)

    def al_mostrar(self) -> None:
        recinto = self._recinto()
        self.icono.set_especie(recinto.especie)
        self.titulo.setText(f"Estudiar {recinto.asignatura}")
        # Se proponen las respuestas de la última sesión de ESTA asignatura.
        u = recinto.ultimo_cuestionario
        self.tiempo.setValue(u.get("tiempo_disponible_min", 60))
        self.concentracion.setValue(u.get("concentracion_min", 25))
        self.cansancio.setCurrentIndex(u.get("cansancio", 2) - 1)
        self.conocimiento.setCurrentIndex(u.get("conocimiento_previo", 2) - 1)
        self.con_tablet.setChecked("tablet" in u.get("dispositivos_permitidos", []))
        self.con_apuntes.setChecked(u.get("con_apuntes", True))
        (self.movil_mesa if u.get("movil_a_la_vista", True) else self.movil_guardado).setChecked(True)
        self.con_test.setChecked(u.get("con_test", True))
        self.apuntes.clear()
        # Se marcan los de la última sesión de esta asignatura (la primera vez, todos).
        anteriores = set(u["apuntes"]) if u.get("apuntes") else None
        self.selector.cargar(self.ventana.carpeta, recinto.asignatura, anteriores)
        self.error.setText("")
        self.tiempo.setFocus()

    def _enviar(self) -> None:
        asignatura = self.ventana.asignatura
        # Lo que se estudia hoy son los apuntes marcados: cada archivo es un tema del plan.
        elegidos = self.selector.elegidos()
        pegado = self.apuntes.toPlainText().strip()
        if not elegidos and not pegado:
            self.error.setText("Marca los apuntes que vas a estudiar hoy (o sube alguno, o pega un texto).")
            return
        if not self.con_apuntes.isChecked() and not self.con_tablet.isChecked():
            self.error.setText("Marca cómo vas a estudiar: con apuntes, con tablet o con las dos.")
            return
        temas = [nombre_tema(nombre) for nombre, _ in elegidos] or [asignatura]
        dispositivos = ["tablet"] if self.con_tablet.isChecked() else []
        try:
            perfil = PerfilSesion(
                tiempo_disponible_min=self.tiempo.value(),
                concentracion_min=self.concentracion.value(),
                cansancio=self.cansancio.currentData(),
                temas=temas,
                conocimiento_previo=self.conocimiento.currentData(),
                dispositivos_permitidos=dispositivos,
                con_test=self.con_test.isChecked(),
                movil_a_la_vista=self.movil_mesa.isChecked(),
                asignatura=asignatura,
            )
        except ValueError as error:
            self.error.setText(str(error))
            return
        # Se guardan en la asignatura para proponerlas la próxima vez (cada asignatura las suyas).
        zoo = z.cargar(self.ventana.carpeta)
        zoo.recinto(asignatura).ultimo_cuestionario = {
            "tiempo_disponible_min": perfil.tiempo_disponible_min,
            "concentracion_min": perfil.concentracion_min, "cansancio": perfil.cansancio,
            "conocimiento_previo": perfil.conocimiento_previo,
            "dispositivos_permitidos": perfil.dispositivos_permitidos,
            "con_apuntes": self.con_apuntes.isChecked(),
            "movil_a_la_vista": perfil.movil_a_la_vista, "con_test": perfil.con_test,
            "apuntes": sorted(self.selector.marcados()),
        }
        z.guardar(zoo, self.ventana.carpeta)
        self.ventana.cuestionario_listo(perfil, unir(pegado, elegidos))
