"""Cuestionario antes de cada sesión (RF5, RF11): con él se adapta el plan."""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QFileDialog, QHBoxLayout, QLineEdit,
                               QPlainTextEdit,
                               QScrollArea, QSpinBox, QVBoxLayout, QWidget)

from studymate.gamificacion import zoo as z
from studymate.llm.apuntes import ErrorApuntes, leer_archivo, unir
from studymate.llm.cuestionario import NIVELES_CANSANCIO, NIVELES_CONOCIMIENTO, PerfilSesion

from ..comun import Pagina, boton, etiqueta, tarjeta
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
        # Temas de ESTA asignatura (se marcan los de hoy) y añadir uno nuevo.
        self.casillas_temas: list[QCheckBox] = []
        self.caja_temas = QWidget()
        self.capa_temas = QVBoxLayout(self.caja_temas)
        self.capa_temas.setContentsMargins(0, 0, 0, 0)
        self.capa_temas.setSpacing(6)
        self.nuevo_tema = QLineEdit()
        self.nuevo_tema.setPlaceholderText("Nuevo tema de esta asignatura")
        self.nuevo_tema.setMaxLength(80)
        self.nuevo_tema.returnPressed.connect(self._anadir_tema)
        fila_tema = QHBoxLayout()
        fila_tema.setContentsMargins(0, 0, 0, 0)
        fila_tema.addWidget(self.nuevo_tema, 1)
        fila_tema.addWidget(boton("Añadir tema", None, self._anadir_tema))
        self.error_tema = etiqueta("", "error")
        caja_temas_total = QWidget()
        capa_total = QVBoxLayout(caja_temas_total)
        capa_total.setContentsMargins(0, 0, 0, 0)
        capa_total.setSpacing(8)
        capa_total.addWidget(self.caja_temas)
        capa_total.addLayout(fila_tema)
        capa_total.addWidget(self.error_tema)
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
            _pregunta("¿Qué temas vas a estudiar hoy?", caja_temas_total,
                      "Son los temas de esta asignatura. Los que añadas se quedan guardados en ella."),
            _pregunta("¿Cuánto tiempo tienes hoy para estudiar?", self.tiempo),
            _pregunta("¿Cuántos minutos seguidos sueles aguantar concentrado?", self.concentracion,
                      "Con esto se decide lo largo que es cada bloque."),
            _pregunta("¿Cómo de cansado estás?", self.cansancio),
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
        botones.addWidget(boton("Elegir otra asignatura", None, lambda: ventana.ir("elegir")))
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

    # --- Temas -------------------------------------------------------------------------
    def _recinto(self) -> z.Recinto | None:
        return z.cargar(self.ventana.carpeta).recinto(self.ventana.asignatura)

    def _mostrar_temas(self, marcados: set[str]) -> None:
        while self.capa_temas.count():
            item = self.capa_temas.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.casillas_temas = []
        recinto = self._recinto()
        temas = recinto.temas if recinto else []
        if not temas:
            self.capa_temas.addWidget(etiqueta("Esta asignatura aún no tiene temas: añade al menos uno.", "nota"))
        for tema in temas:
            casilla = QCheckBox(tema)
            casilla.setChecked(tema in marcados)
            self.casillas_temas.append(casilla)
            self.capa_temas.addWidget(casilla)

    def _anadir_tema(self) -> None:
        zoo = z.cargar(self.ventana.carpeta)
        recinto = zoo.recinto(self.ventana.asignatura)
        try:
            tema = recinto.anadir_tema(self.nuevo_tema.text())
        except z.ErrorZoo as error:
            self.error_tema.setText(str(error))
            return
        z.guardar(zoo, self.ventana.carpeta)
        marcados = {c.text() for c in self.casillas_temas if c.isChecked()} | {tema}
        self.nuevo_tema.clear()
        self.error_tema.setText("")
        self._mostrar_temas(marcados)

    def al_mostrar(self) -> None:
        recinto = self._recinto()
        self.icono.set_especie(recinto.especie)
        self.titulo.setText(f"Estudiar {recinto.asignatura}")
        # Se proponen las respuestas de la última sesión de ESTA asignatura.
        u = recinto.ultimo_cuestionario
        self._mostrar_temas(set(u.get("temas", [])) or (set(recinto.temas[:1])))
        self.tiempo.setValue(u.get("tiempo_disponible_min", 60))
        self.concentracion.setValue(u.get("concentracion_min", 25))
        self.cansancio.setCurrentIndex(u.get("cansancio", 2) - 1)
        self.conocimiento.setCurrentIndex(u.get("conocimiento_previo", 2) - 1)
        permitidos = u.get("dispositivos_permitidos", [])
        self.permitir_movil.setChecked("movil" in permitidos)
        self.permitir_tablet.setChecked("tablet" in permitidos)
        self.a_la_vista.setChecked(u.get("movil_a_la_vista", True))
        self._actualizar_a_la_vista()
        self.con_test.setChecked(u.get("con_test", True))
        self.modo_prueba.setChecked(self.ventana.modo_prueba)
        self.archivos = []
        self.apuntes.clear()
        self._mostrar_archivos()
        self.nuevo_tema.clear()
        self.error_tema.setText("")
        self.error.setText("")
        self.tiempo.setFocus()

    def _enviar(self) -> None:
        asignatura = self.ventana.asignatura
        temas = [c.text() for c in self.casillas_temas if c.isChecked()]
        if not temas:
            self.error.setText("Marca al menos un tema de los que vas a estudiar hoy (o añade uno).")
            return
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
                asignatura=asignatura,
            )
        except ValueError as error:
            self.error.setText(str(error))
            return
        # Se guardan en la asignatura para proponerlas la próxima vez (cada asignatura las suyas).
        zoo = z.cargar(self.ventana.carpeta)
        zoo.recinto(asignatura).ultimo_cuestionario = {
            "temas": temas, "tiempo_disponible_min": perfil.tiempo_disponible_min,
            "concentracion_min": perfil.concentracion_min, "cansancio": perfil.cansancio,
            "conocimiento_previo": perfil.conocimiento_previo,
            "dispositivos_permitidos": perfil.dispositivos_permitidos,
            "movil_a_la_vista": perfil.movil_a_la_vista, "con_test": perfil.con_test,
        }
        z.guardar(zoo, self.ventana.carpeta)
        self.ventana.cuestionario_listo(perfil, unir(self.apuntes.toPlainText(), self.archivos),
                                        self.modo_prueba.isChecked())
