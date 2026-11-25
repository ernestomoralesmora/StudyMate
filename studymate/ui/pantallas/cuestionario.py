"""Cuestionario antes de cada sesión (RF5, RF11): con él se adapta el plan."""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QApplication, QButtonGroup, QCheckBox, QRadioButton, QComboBox, QFileDialog, QHBoxLayout, QLineEdit,
                               QMessageBox,
                               QPlainTextEdit,
                               QScrollArea, QSpinBox, QVBoxLayout, QWidget)

from studymate.gamificacion import zoo as z
from studymate.llm.apuntes import unir
from studymate.llm.cuestionario import NIVELES_CANSANCIO, NIVELES_CONOCIMIENTO, PerfilSesion

from ..comun import Pagina, boton, etiqueta, tarjeta
from ..selector_apuntes import SelectorApuntes, nombre_tema
from ..zoo_widget import AnimalIcono



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
        # Forma de estudiar: solo con apuntes (papel) o con tablet. Con tablet, lo que
        # parezca un móvil en la mano no pausa (COCO no distingue tablet de móvil), pero
        # se sigue vigilando el sitio del móvil si está a la vista.
        self.solo_apuntes = QRadioButton("Solo con apuntes (papel, libro…)")
        self.con_tablet = QRadioButton("Con tablet")
        self.forma = QButtonGroup(self)
        self.forma.addButton(self.solo_apuntes)
        self.forma.addButton(self.con_tablet)
        self.solo_apuntes.setChecked(True)
        dispositivos = QWidget()
        fila = QVBoxLayout(dispositivos)
        fila.setContentsMargins(0, 0, 0, 0)
        fila.addWidget(self.solo_apuntes)
        fila.addWidget(self.con_tablet)
        self.a_la_vista = QCheckBox("Dejaré el móvil sobre la mesa, donde lo vea la cámara")
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
        self.modo_prueba = QCheckBox("Modo prueba: cada minuto del plan dura 10 segundos")
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
                      "Si estudias con tablet, usarla no pausará el tiempo."),
            _pregunta("Tu móvil", self.a_la_vista,
                      "Si lo dejas a la vista, antes de empezar marcarás dónde está y "
                      "avisaremos si se mueve de ahí. Si lo tienes guardado, desmárcalo."),
            _pregunta("Test", self.con_test),
            _pregunta("Para probar la aplicación", self.modo_prueba),
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
        permitidos = u.get("dispositivos_permitidos", [])
        (self.con_tablet if "tablet" in permitidos else self.solo_apuntes).setChecked(True)
        self.a_la_vista.setChecked(u.get("movil_a_la_vista", True))
        self.con_test.setChecked(u.get("con_test", True))
        self.modo_prueba.setChecked(self.ventana.modo_prueba)
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
                movil_a_la_vista=self.a_la_vista.isChecked(),
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
            "movil_a_la_vista": perfil.movil_a_la_vista, "con_test": perfil.con_test,
            "apuntes": sorted(self.selector.marcados()),
        }
        z.guardar(zoo, self.ventana.carpeta)
        self.ventana.cuestionario_listo(perfil, unir(pegado, elegidos),
                                        self.modo_prueba.isChecked())
