"""Entrar o crear una cuenta (usuario y contraseña, todo en local)."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QStackedWidget, QVBoxLayout, QWidget

from studymate import usuarios as us

from ..comun import Pagina, boton, etiqueta, tarjeta
from ..companero import Companero


def _campo(texto: str, campo: QLineEdit, ayuda: str | None = None) -> QWidget:
    caja = QWidget()
    capa = QVBoxLayout(caja)
    capa.setContentsMargins(0, 0, 0, 0)
    capa.setSpacing(4)
    titulo = etiqueta(texto)
    titulo.setStyleSheet("font-weight: 600;")
    titulo.setBuddy(campo)
    capa.addWidget(titulo)
    capa.addWidget(campo)
    if ayuda:
        capa.addWidget(etiqueta(ayuda, "nota"))
    return caja


def _contrasena() -> QLineEdit:
    c = QLineEdit()
    c.setEchoMode(QLineEdit.Password)
    return c


class PantallaAcceso(Pagina):
    def __init__(self, ventana):
        super().__init__(ventana)
        # Entrar
        self.usuario = QLineEdit()
        self.contrasena = _contrasena()
        self.contrasena.returnPressed.connect(self._entrar)
        self.error_entrar = etiqueta("", "error")
        entrar = tarjeta(
            etiqueta("Entrar", "cifra"),
            _campo("Usuario", self.usuario),
            _campo("Contraseña", self.contrasena),
            self.error_entrar,
            boton("Entrar", "primario", self._entrar),
            boton("Soy nuevo: crear una cuenta", None, lambda: self._modo(1)),
            espacio=12, margen=28,
        )
        # Crear cuenta
        self.nombre = QLineEdit()
        self.nuevo_usuario = QLineEdit()
        self.curso = QLineEdit()
        self.curso.setPlaceholderText("Opcional, por ejemplo 2º de Ingeniería Informática")
        self.nueva = _contrasena()
        self.repetir = _contrasena()
        self.repetir.returnPressed.connect(self._registrar)
        self.error_registro = etiqueta("", "error")
        registro = tarjeta(
            etiqueta("Crear una cuenta", "cifra"),
            _campo("¿Cómo te llamas?", self.nombre),
            _campo("Usuario", self.nuevo_usuario, "Para entrar: letras sin tilde y números, sin espacios."),
            _campo("Curso", self.curso),
            _campo("Contraseña", self.nueva, f"Al menos {us.MIN_CONTRASENA} caracteres."),
            _campo("Repite la contraseña", self.repetir),
            self.error_registro,
            boton("Crear mi cuenta", "primario", self._registrar),
            boton("Ya tengo cuenta: entrar", None, lambda: self._modo(0)),
            espacio=12, margen=28,
        )
        self.modos = QStackedWidget()
        self.modos.addWidget(entrar)
        self.modos.addWidget(registro)
        self.modos.setFixedWidth(440)

        companero = Companero("feliz", lado_minimo=120)
        companero.setFixedSize(120, 120)
        presentacion = QVBoxLayout()
        presentacion.addStretch()
        presentacion.addWidget(companero)
        presentacion.addWidget(etiqueta("StudyMate", "titulo"))
        presentacion.addWidget(etiqueta(
            "Tu compañero de estudio. Cuenta el tiempo que estudias de verdad y lo convierte "
            "en tu propio zoo: un animal por asignatura que crece con tus sesiones.", "subtitulo"))
        presentacion.addWidget(etiqueta(
            "Todo se guarda en este ordenador. La contraseña no se guarda tal cual, solo su huella.", "nota"))
        presentacion.addStretch()

        cuerpo = QHBoxLayout(self)
        cuerpo.setContentsMargins(60, 40, 60, 40)
        cuerpo.setSpacing(48)
        cuerpo.addLayout(presentacion, 1)
        cuerpo.addWidget(self.modos, 0, Qt.AlignVCenter)

    def al_mostrar(self) -> None:
        self._modo(0 if us.cargar_usuarios() else 1)
        for campo in (self.contrasena, self.nueva, self.repetir):
            campo.clear()

    def _modo(self, indice: int) -> None:
        self.modos.setCurrentIndex(indice)
        self.error_entrar.setText("")
        self.error_registro.setText("")
        (self.usuario if indice == 0 else self.nombre).setFocus()

    def _entrar(self) -> None:
        try:
            usuario = us.iniciar_sesion(self.usuario.text(), self.contrasena.text())
        except us.ErrorUsuario as error:
            self.error_entrar.setText(str(error))
            self.contrasena.clear()
            return
        self.ventana.sesion_iniciada(usuario)

    def _registrar(self) -> None:
        try:
            usuario = us.registrar(self.nuevo_usuario.text(), self.nombre.text(), self.nueva.text(),
                                   self.repetir.text(), self.curso.text())
        except us.ErrorUsuario as error:
            self.error_registro.setText(str(error))
            return
        self.ventana.sesion_iniciada(usuario)
