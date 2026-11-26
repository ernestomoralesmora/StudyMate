"""Entrar o crear una cuenta (usuario y contraseña, todo en local).

Todo va centrado: el compañero (logo) arriba, el nombre y la frase, y debajo una
tarjeta con dos pestañas («Entrar» y «Crear cuenta»). Va dentro de un área con
desplazamiento para que, en ventanas bajas, los campos no se aplasten.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QButtonGroup, QFrame, QHBoxLayout, QLineEdit, QPushButton, QScrollArea,
                               QVBoxLayout, QWidget)

from studymate import usuarios as us

from ..comun import Pagina, boton, etiqueta, tarjeta
from ..companero import Companero

ANCHO = 400      # ancho de la columna central
ALTO_CAMPO = 38  # alto fijo de cada campo: así nunca se cortan las letras


def _entrada(marcador: str = "", contrasena: bool = False) -> QLineEdit:
    campo = QLineEdit()
    campo.setPlaceholderText(marcador)
    campo.setFixedHeight(ALTO_CAMPO)
    if contrasena:
        campo.setEchoMode(QLineEdit.Password)
    return campo


def _campo(texto: str, campo: QLineEdit, ayuda: str | None = None) -> QWidget:
    caja = QWidget()
    capa = QVBoxLayout(caja)
    capa.setContentsMargins(0, 0, 0, 0)
    capa.setSpacing(4)
    titulo = etiqueta(texto, "etiqueta_campo")
    titulo.setBuddy(campo)  # lectores de pantalla: el rótulo nombra el campo
    capa.addWidget(titulo)
    capa.addWidget(campo)
    if ayuda:
        capa.addWidget(etiqueta(ayuda, "nota"))
    return caja


def _formulario(*hijos) -> QWidget:
    caja = QWidget()
    capa = QVBoxLayout(caja)
    capa.setContentsMargins(0, 0, 0, 0)
    capa.setSpacing(10)
    for h in hijos:
        if isinstance(h, QWidget):
            capa.addWidget(h)
        else:
            capa.addLayout(h)
    return caja


class PantallaAcceso(Pagina):
    def __init__(self, ventana):
        super().__init__(ventana)
        # --- Pestañas «Entrar» / «Crear cuenta» -------------------------------------------
        self.pestana_entrar = QPushButton("Entrar")
        self.pestana_crear = QPushButton("Crear cuenta")
        pestanas = QFrame()
        pestanas.setObjectName("pestanas")
        capa_pestanas = QHBoxLayout(pestanas)
        capa_pestanas.setContentsMargins(4, 4, 4, 4)
        capa_pestanas.setSpacing(4)
        grupo = QButtonGroup(self)
        for i, p in enumerate((self.pestana_entrar, self.pestana_crear)):
            p.setObjectName("pestana")
            p.setCheckable(True)
            p.setCursor(Qt.PointingHandCursor)
            p.clicked.connect(lambda _=False, i=i: self._modo(i))
            grupo.addButton(p)
            capa_pestanas.addWidget(p, 1)

        # --- Entrar ----------------------------------------------------------------------
        self.usuario = _entrada("Tu usuario")
        self.contrasena = _entrada("Tu contraseña", contrasena=True)
        self.usuario.returnPressed.connect(self.contrasena.setFocus)
        self.contrasena.returnPressed.connect(self._entrar)
        self.error_entrar = etiqueta("", "error")
        self.error_entrar.hide()
        self.form_entrar = _formulario(
            _campo("Usuario", self.usuario),
            _campo("Contraseña", self.contrasena),
            self.error_entrar,
            boton("Entrar", "primario", self._entrar),
        )

        # --- Crear cuenta ------------------------------------------------------------------
        self.nombre = _entrada("Por ejemplo, Pablo")
        self.nuevo_usuario = _entrada("Por ejemplo, pablo")
        self.nueva = _entrada("Contraseña", contrasena=True)
        self.repetir = _entrada("Otra vez", contrasena=True)
        siguiente = [self.nombre, self.nuevo_usuario, self.nueva, self.repetir]
        for actual, proximo in zip(siguiente, siguiente[1:]):
            actual.returnPressed.connect(proximo.setFocus)
        self.repetir.returnPressed.connect(self._registrar)
        self.error_registro = etiqueta("", "error")
        self.error_registro.hide()
        contrasenas = QHBoxLayout()
        contrasenas.setSpacing(12)
        contrasenas.addWidget(_campo("Contraseña", self.nueva), 1)
        contrasenas.addWidget(_campo("Repítela", self.repetir), 1)
        self.form_crear = _formulario(
            _campo("¿Cómo te llamas?", self.nombre),
            _campo("Usuario", self.nuevo_usuario, "Para entrar: letras sin tilde y números, sin espacios."),
            contrasenas,
            etiqueta(f"La contraseña, de al menos {us.MIN_CONTRASENA} caracteres.", "nota"),
            self.error_registro,
            boton("Crear mi cuenta", "primario", self._registrar),
        )

        caja = tarjeta(pestanas, self.form_entrar, self.form_crear, espacio=14, margen=20)
        caja.setObjectName("tarjeta_acceso")

        # --- Cabecera: logo, nombre y frase -------------------------------------------------
        companero = Companero("feliz", lado_minimo=72)
        companero.setFixedSize(72, 72)
        nombre_app = etiqueta("StudyMate", "marca")
        nombre_app.setAlignment(Qt.AlignCenter)
        frase = etiqueta("Tu compañero de estudio. Cuenta el tiempo que estudias de verdad y lo "
                         "convierte en tu propio zoo: un animal por asignatura que crece con tus "
                         "sesiones.", "subtitulo")
        frase.setAlignment(Qt.AlignCenter)
        privacidad = etiqueta("Todo se guarda en este ordenador. La contraseña no se guarda tal cual, "
                              "solo su huella.", "nota")
        privacidad.setAlignment(Qt.AlignCenter)

        columna = QWidget()
        columna.setFixedWidth(ANCHO)
        capa_columna = QVBoxLayout(columna)
        capa_columna.setContentsMargins(0, 0, 0, 0)
        capa_columna.setSpacing(0)
        capa_columna.addWidget(companero, 0, Qt.AlignHCenter)
        capa_columna.addSpacing(8)
        capa_columna.addWidget(nombre_app)
        capa_columna.addSpacing(4)
        capa_columna.addWidget(frase)
        capa_columna.addSpacing(16)
        capa_columna.addWidget(caja)
        capa_columna.addSpacing(12)
        capa_columna.addWidget(privacidad)

        # Centrado en horizontal y en vertical; si no cabe, se desplaza.
        contenido = QWidget()
        contenido.setObjectName("contenido_acceso")
        contenido.setAttribute(Qt.WA_StyledBackground, True)
        capa_contenido = QVBoxLayout(contenido)
        capa_contenido.setContentsMargins(24, 20, 24, 20)
        capa_contenido.addStretch()
        fila = QHBoxLayout()
        fila.addStretch()
        fila.addWidget(columna)
        fila.addStretch()
        capa_contenido.addLayout(fila)
        capa_contenido.addStretch()
        desplazable = QScrollArea()
        desplazable.setObjectName("fondo_acceso")
        desplazable.setWidgetResizable(True)
        desplazable.setFrameShape(QFrame.NoFrame)
        desplazable.setWidget(contenido)

        capa = QVBoxLayout(self)
        capa.setContentsMargins(0, 0, 0, 0)
        capa.addWidget(desplazable)
        # Todo un poco más pequeño que en el resto de la aplicación, para que quepa entero.
        contenido.setStyleSheet(
            "QLabel#subtitulo { font-size: 13px; } QLabel#nota { font-size: 12px; }"
            "QLabel#etiqueta_campo { font-size: 13px; } QLineEdit { font-size: 13px; padding: 0 10px; }"
            "QPushButton { min-height: 38px; font-size: 14px; }"
            "QPushButton#pestana { min-height: 32px; }")

    def al_mostrar(self) -> None:
        self._modo(0 if us.cargar_usuarios() else 1)
        for campo in (self.contrasena, self.nueva, self.repetir):
            campo.clear()

    def _modo(self, indice: int) -> None:
        self.pestana_entrar.setChecked(indice == 0)
        self.pestana_crear.setChecked(indice == 1)
        self.form_entrar.setVisible(indice == 0)
        self.form_crear.setVisible(indice == 1)
        self._error(self.error_entrar, "")
        self._error(self.error_registro, "")
        (self.usuario if indice == 0 else self.nombre).setFocus()

    @staticmethod
    def _error(etiqueta_error, texto: str) -> None:
        etiqueta_error.setText(texto)
        etiqueta_error.setVisible(bool(texto))

    def _entrar(self) -> None:
        try:
            usuario = us.iniciar_sesion(self.usuario.text(), self.contrasena.text())
        except us.ErrorUsuario as error:
            self._error(self.error_entrar, str(error))
            self.contrasena.clear()
            self.contrasena.setFocus()
            return
        self.ventana.sesion_iniciada(usuario)

    def _registrar(self) -> None:
        try:
            usuario = us.registrar(self.nuevo_usuario.text(), self.nombre.text(), self.nueva.text(),
                                   self.repetir.text())
        except us.ErrorUsuario as error:
            self._error(self.error_registro, str(error))
            return
        self.ventana.sesion_iniciada(usuario)
