"""Cuestionario antes de cada sesión (RF5, RF11): con él se adapta el plan."""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QFileDialog, QHBoxLayout, QPlainTextEdit,
                               QScrollArea, QSpinBox, QVBoxLayout, QWidget)

from studymate.llm.apuntes import ErrorApuntes, leer_archivo, unir
from studymate.llm.cuestionario import (NIVELES_CANSANCIO, NIVELES_CONOCIMIENTO, PerfilSesion,
                                        cargar_perfil, guardar_perfil)

from ..comun import Pagina, boton, etiqueta, tarjeta


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
        self.temas = QPlainTextEdit()
        self.temas.setPlaceholderText("Un tema por línea, por ejemplo:\nTema 3: Interacción\nTema 4: Prototipado")
        self.temas.setFixedHeight(96)
        self.conocimiento = QComboBox()
        for k, v in NIVELES_CONOCIMIENTO.items():
            self.conocimiento.addItem(f"{k} · {v}", k)
        self.permitir_movil = QCheckBox("El móvil")
        self.permitir_tablet = QCheckBox("Una tablet (por ejemplo, con los apuntes)")
        dispositivos = QWidget()
        fila = QVBoxLayout(dispositivos)
        fila.setContentsMargins(0, 0, 0, 0)
        fila.addWidget(self.permitir_tablet)
        fila.addWidget(self.permitir_movil)
        self.a_la_vista = QCheckBox("Dejaré el móvil sobre la mesa, donde lo vea la cámara")
        self.permitir_movil.toggled.connect(self._actualizar_a_la_vista)
        self.con_test = QCheckBox("Quiero un test de 5 preguntas al final de cada bloque")
        # Apuntes: archivos (PDF, Word, texto) y, si se quiere, texto pegado.
        self.archivos: list[tuple[str, str]] = []  # (nombre, texto)
        self.lista_archivos = etiqueta("Ningún archivo.", "nota")
        self.lista_archivos.setTextFormat(Qt.PlainText)
        self.error_archivos = etiqueta("", "error")
        subir = boton("Subir apuntes (PDF, Word o texto)…", "primario", self._subir)
        self.quitar = boton("Quitar los archivos", None, self._quitar)
        self.quitar.setEnabled(False)
        fila_archivos = QHBoxLayout()
        fila_archivos.addWidget(subir)
        fila_archivos.addWidget(self.quitar)
        fila_archivos.addStretch()
        self.apuntes = QPlainTextEdit()
        self.apuntes.setPlaceholderText("También puedes pegar aquí texto (opcional).")
        self.apuntes.setFixedHeight(80)
        caja_apuntes = QWidget()
        capa_apuntes = QVBoxLayout(caja_apuntes)
        capa_apuntes.setContentsMargins(0, 0, 0, 0)
        capa_apuntes.setSpacing(8)
        capa_apuntes.addLayout(fila_archivos)
        capa_apuntes.addWidget(self.lista_archivos)
        capa_apuntes.addWidget(self.error_archivos)
        capa_apuntes.addWidget(self.apuntes)
        self.modo_prueba = QCheckBox("Modo prueba: cada minuto del plan dura 10 segundos")
        self.error = etiqueta("", "error")

        formulario = tarjeta(
            _pregunta("¿Cuánto tiempo tienes hoy para estudiar?", self.tiempo),
            _pregunta("¿Cuántos minutos seguidos sueles aguantar concentrado?", self.concentracion,
                      "Con esto se decide lo largo que es cada bloque."),
            _pregunta("¿Cómo de cansado estás?", self.cansancio),
            _pregunta("¿Qué vas a estudiar?", self.temas),
            _pregunta("¿Cuánto sabes ya del tema?", self.conocimiento),
            _pregunta("¿Necesitas alguno de estos para estudiar?", dispositivos,
                      "Lo que marques aquí no pausará el tiempo aunque lo uses."),
            _pregunta("Tu móvil", self.a_la_vista,
                      "Si lo dejas a la vista, antes de empezar marcarás dónde está y "
                      "avisaremos si se mueve de ahí. Si lo tienes guardado, desmárcalo."),
            _pregunta("Test", self.con_test),
            _pregunta("Tus apuntes (opcional)", caja_apuntes,
                      "Si los subes, el plan y las preguntas del test se basan en ellos. Solo se lee "
                      "el texto, no se guarda ninguna copia, y al asistente se le manda solo la parte "
                      "de cada tema."),
            _pregunta("Para probar la aplicación", self.modo_prueba),
            espacio=14, margen=24,
        )

        contenido = QWidget()
        capa_contenido = QVBoxLayout(contenido)
        capa_contenido.setContentsMargins(0, 0, 8, 0)
        capa_contenido.addWidget(formulario)
        desplazable = QScrollArea()
        desplazable.setWidgetResizable(True)
        desplazable.setWidget(contenido)

        botones = QHBoxLayout()
        botones.addWidget(boton("Volver", None, lambda: ventana.ir("inicio")))
        botones.addStretch()
        self.siguiente = boton("Crear mi plan", "primario", self._enviar)
        botones.addWidget(self.siguiente)

        capa = QVBoxLayout(self)
        capa.setContentsMargins(28, 24, 28, 24)
        capa.setSpacing(14)
        capa.addWidget(etiqueta("Antes de empezar", "titulo"))
        capa.addWidget(etiqueta("Unas preguntas rápidas para adaptar la sesión a cómo estás hoy.", "subtitulo"))
        capa.addWidget(desplazable, 1)
        capa.addWidget(self.error)
        capa.addLayout(botones)

    def _subir(self) -> None:
        rutas, _ = QFileDialog.getOpenFileNames(
            self, "Elige tus apuntes", str(Path.home()),
            "Apuntes (*.pdf *.docx *.txt *.md);;PDF (*.pdf);;Word (*.docx);;Texto (*.txt *.md)",
        )
        if not rutas:
            return
        errores = []
        QApplication.setOverrideCursor(Qt.WaitCursor)  # un PDF largo tarda unos segundos
        try:
            for ruta in rutas:
                nombre = Path(ruta).name
                if any(n == nombre for n, _ in self.archivos):
                    continue
                try:
                    self.archivos.append((nombre, leer_archivo(ruta)))
                except ErrorApuntes as error:
                    errores.append(str(error))
        finally:
            QApplication.restoreOverrideCursor()
        self.error_archivos.setText("\n".join(errores))
        self._mostrar_archivos()

    def _quitar(self) -> None:
        self.archivos = []
        self.error_archivos.setText("")
        self._mostrar_archivos()

    def _mostrar_archivos(self) -> None:
        if not self.archivos:
            self.lista_archivos.setText("Ningún archivo.")
        else:
            self.lista_archivos.setText("\n".join(
                f"📄 {nombre} · {len(texto) // 1000 or 1} mil caracteres" for nombre, texto in self.archivos))
        self.quitar.setEnabled(bool(self.archivos))

    def _actualizar_a_la_vista(self) -> None:
        # Si el móvil está permitido, no se vigila su sitio.
        self.a_la_vista.setEnabled(not self.permitir_movil.isChecked())
        if self.permitir_movil.isChecked():
            self.a_la_vista.setChecked(False)

    def al_mostrar(self) -> None:
        anterior = cargar_perfil()
        self.tiempo.setValue(anterior.tiempo_disponible_min if anterior else 60)
        self.concentracion.setValue(anterior.concentracion_min if anterior else 25)
        self.cansancio.setCurrentIndex((anterior.cansancio if anterior else 2) - 1)
        self.temas.setPlainText("\n".join(anterior.temas) if anterior else "")
        self.conocimiento.setCurrentIndex((anterior.conocimiento_previo if anterior else 2) - 1)
        permitidos = anterior.dispositivos_permitidos if anterior else []
        self.permitir_movil.setChecked("movil" in permitidos)
        self.permitir_tablet.setChecked("tablet" in permitidos)
        self.a_la_vista.setChecked(anterior.movil_a_la_vista if anterior else True)
        self._actualizar_a_la_vista()
        self.con_test.setChecked(anterior.con_test if anterior else True)
        self.modo_prueba.setChecked(self.ventana.modo_prueba)
        self._mostrar_archivos()
        self.error.setText("")
        self.tiempo.setFocus()

    def _enviar(self) -> None:
        temas = [t.strip() for t in self.temas.toPlainText().replace(",", "\n").splitlines() if t.strip()]
        dispositivos = [d for d, c in (("movil", self.permitir_movil), ("tablet", self.permitir_tablet))
                        if c.isChecked()]
        try:
            perfil = PerfilSesion(
                tiempo_disponible_min=self.tiempo.value(),
                concentracion_min=self.concentracion.value(),
                cansancio=self.cansancio.currentData(),
                temas=temas,
                conocimiento_previo=self.conocimiento.currentData(),
                dispositivos_permitidos=dispositivos,
                con_test=self.con_test.isChecked(),
                movil_a_la_vista=self.a_la_vista.isChecked() and "movil" not in dispositivos,
            )
        except ValueError as error:
            self.error.setText(str(error))
            return
        guardar_perfil(perfil)
        self.ventana.cuestionario_listo(perfil, unir(self.apuntes.toPlainText(), self.archivos),
                                        self.modo_prueba.isChecked())
