"""Cuestionario antes de cada sesión (RF5, RF11): con él se adapta el plan."""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QApplication, QButtonGroup, QCheckBox, QRadioButton, QComboBox, QFileDialog, QHBoxLayout, QLineEdit,
                               QMessageBox,
                               QPlainTextEdit,
                               QScrollArea, QSpinBox, QVBoxLayout, QWidget)

from studymate.gamificacion import zoo as z
from studymate.llm.apuntes import BibliotecaApuntes, ErrorApuntes, unir
from studymate.llm.cuestionario import NIVELES_CANSANCIO, NIVELES_CONOCIMIENTO, PerfilSesion

from ..comun import Pagina, boton, etiqueta, tarjeta
from ..zoo_widget import AnimalIcono


def nombre_tema(archivo: str) -> str:
    """«E.04.01_Testing_ES_v1.15.pdf» -> «E.04.01 Testing ES v1.15» (nombre del tema en el plan)."""
    return " ".join(Path(archivo).stem.replace("_", " ").split())[:80] or archivo


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
        # Apuntes guardados de ESTA asignatura: se suben una vez y en cada sesión se
        # marcan los que se quieren usar. Y, si se quiere, texto pegado solo para hoy.
        self.casillas_apuntes: list[tuple[QCheckBox, str]] = []  # (casilla, id del documento)
        self.caja_lista_apuntes = QWidget()
        self.capa_lista_apuntes = QVBoxLayout(self.caja_lista_apuntes)
        self.capa_lista_apuntes.setContentsMargins(0, 0, 0, 0)
        self.capa_lista_apuntes.setSpacing(6)
        self.error_archivos = etiqueta("", "error")
        self.error_archivos.hide()
        fila_archivos = QHBoxLayout()
        fila_archivos.setContentsMargins(0, 0, 0, 0)
        fila_archivos.addWidget(boton("Subir apuntes (PDF, Word o texto)…", "primario", self._subir))
        for texto, valor in (("Marcar todos", True), ("Ninguno", False)):
            fila_archivos.addWidget(boton(texto, None, lambda _=False, v=valor: self._marcar_apuntes(v)))
        fila_archivos.addStretch()
        self.apuntes = QPlainTextEdit()
        self.apuntes.setPlaceholderText("O pega aquí un texto solo para esta sesión (opcional).")
        self.apuntes.setFixedHeight(70)
        caja_apuntes = QWidget()
        capa_apuntes = QVBoxLayout(caja_apuntes)
        capa_apuntes.setContentsMargins(0, 0, 0, 0)
        capa_apuntes.setSpacing(8)
        capa_apuntes.addLayout(fila_archivos)
        capa_apuntes.addWidget(self.error_archivos)
        capa_apuntes.addWidget(self.caja_lista_apuntes)
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

    def _biblioteca(self) -> BibliotecaApuntes:
        return BibliotecaApuntes(self.ventana.carpeta, self.ventana.asignatura)

    def _subir(self) -> None:
        rutas, _ = QFileDialog.getOpenFileNames(
            self, "Elige tus apuntes", str(Path.home()),
            "Apuntes (*.pdf *.docx *.txt *.md);;PDF (*.pdf);;Word (*.docx);;Texto (*.txt *.md)",
        )
        if not rutas:
            return
        biblioteca = self._biblioteca()
        marcados = self._apuntes_marcados()
        errores = []
        QApplication.setOverrideCursor(Qt.WaitCursor)  # un PDF largo tarda unos segundos
        try:
            for ruta in rutas:
                try:
                    marcados.add(biblioteca.anadir(ruta).id)  # los recién subidos, marcados
                except ErrorApuntes as error:
                    errores.append(str(error))
        finally:
            QApplication.restoreOverrideCursor()
        self.error_archivos.setText("\n".join(errores))
        self.error_archivos.setVisible(bool(errores))
        self._mostrar_apuntes(marcados)

    def _apuntes_marcados(self) -> set[str]:
        return {id_ for casilla, id_ in self.casillas_apuntes if casilla.isChecked()}

    def _marcar_apuntes(self, valor: bool) -> None:
        for casilla, _ in self.casillas_apuntes:
            casilla.setChecked(valor)

    def _quitar_apunte(self, id_documento: str, nombre: str) -> None:
        respuesta = QMessageBox.question(
            self, "Quitar apuntes", f"¿Quitar «{nombre}» de los apuntes de {self.ventana.asignatura}? "
            "Tendrías que volver a subirlo para usarlo.")
        if respuesta != QMessageBox.Yes:
            return
        marcados = self._apuntes_marcados() - {id_documento}
        self._biblioteca().quitar(id_documento)
        self._mostrar_apuntes(marcados)

    def _mostrar_apuntes(self, marcados: set[str]) -> None:
        while self.capa_lista_apuntes.count():
            item = self.capa_lista_apuntes.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.casillas_apuntes = []
        documentos = self._biblioteca().documentos()
        if not documentos:
            self.capa_lista_apuntes.addWidget(etiqueta("Esta asignatura aún no tiene apuntes guardados.", "nota"))
        for d in documentos:
            fila = QWidget()
            capa = QHBoxLayout(fila)
            capa.setContentsMargins(0, 0, 0, 0)
            fecha = d.subido[8:10] + "/" + d.subido[5:7]
            casilla = QCheckBox(f"{d.nombre}  ·  {max(1, d.caracteres // 1000)} mil caracteres  ·  subido el {fecha}")
            casilla.setChecked(d.id in marcados)
            self.casillas_apuntes.append((casilla, d.id))
            quitar = boton("Quitar", None, lambda _=False, i=d.id, n=d.nombre: self._quitar_apunte(i, n))
            quitar.setAccessibleName(f"Quitar {d.nombre} de los apuntes")
            capa.addWidget(casilla, 1)
            capa.addWidget(quitar)
            self.capa_lista_apuntes.addWidget(fila)

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
        self.error_archivos.hide()
        guardados = {d.id for d in self._biblioteca().documentos()}
        anteriores = set(u.get("apuntes", [])) & guardados
        self._mostrar_apuntes(anteriores or guardados)  # la primera vez, todos marcados
        self.error.setText("")
        self.tiempo.setFocus()

    def _enviar(self) -> None:
        asignatura = self.ventana.asignatura
        # Lo que se estudia hoy son los apuntes marcados: cada archivo es un tema del plan.
        elegidos = self._biblioteca().elegidos(sorted(self._apuntes_marcados()))
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
            "apuntes": sorted(self._apuntes_marcados()),
        }
        z.guardar(zoo, self.ventana.carpeta)
        self.ventana.cuestionario_listo(perfil, unir(pegado, elegidos),
                                        self.modo_prueba.isChecked())
