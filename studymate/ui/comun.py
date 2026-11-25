"""Piezas comunes de la interfaz: tarjetas, textos, botones e hilos de trabajo."""

import cv2
from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget


class Pagina(QWidget):
    """Una pantalla. Recibe el foco al mostrarse para que funcionen las teclas."""

    def __init__(self, ventana):
        super().__init__()
        self.ventana = ventana
        self.setObjectName("pagina")
        self.setFocusPolicy(Qt.StrongFocus)  # para recibir las teclas (S/N, A/B/C, Enter)

    def al_mostrar(self) -> None:
        """La ventana lo llama cada vez que se enseña esta pantalla."""

    def al_ocultar(self) -> None:
        """La ventana lo llama al cambiar a otra pantalla."""


def tarjeta(*hijos, espacio: int = 12, margen: int = 20) -> QFrame:
    marco = QFrame()
    marco.setObjectName("tarjeta")
    capa = QVBoxLayout(marco)
    capa.setContentsMargins(margen, margen, margen, margen)
    capa.setSpacing(espacio)
    for h in hijos:
        if isinstance(h, QWidget):
            capa.addWidget(h)
        else:
            capa.addLayout(h)
    return marco


# Textos de una sola línea (cifras grandes, rótulos): sin ajuste de línea.
UNA_LINEA = ("cifra", "grande", "seccion")


def etiqueta(texto: str = "", nombre: str | None = None, ajustar: bool | None = None) -> QLabel:
    e = QLabel(texto)
    if nombre:
        e.setObjectName(nombre)
    e.setWordWrap(nombre not in UNA_LINEA if ajustar is None else ajustar)
    # Que la ventana nunca la haga más baja de lo que necesita el texto: si no,
    # al maximizar se cortaban las letras. (Se modifica la política que ya tiene
    # para no perder el "alto según el ancho" de los textos con varias líneas.)
    politica = e.sizePolicy()
    politica.setVerticalPolicy(QSizePolicy.Minimum)
    e.setSizePolicy(politica)
    return e


def boton(texto: str, nombre: str | None = None, al_pulsar=None) -> QPushButton:
    b = QPushButton(texto)
    if nombre:
        b.setObjectName(nombre)
    if al_pulsar:
        b.clicked.connect(al_pulsar)
    return b


def minutos(segundos: float) -> str:
    s = max(0, int(round(segundos)))
    return f"{s // 60:02d}:{s % 60:02d}" if s < 3600 else f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}"


def frame_a_pixmap(frame_bgr) -> QPixmap:
    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    alto, ancho = rgb.shape[:2]
    imagen = QImage(rgb.data, ancho, alto, 3 * ancho, QImage.Format_RGB888)
    return QPixmap.fromImage(imagen.copy())


class Trabajo(QThread):
    """Ejecuta una función lenta (LLM) sin congelar la ventana.

    Emite (etiqueta, resultado) o (etiqueta, mensaje de error). Conviene
    conectarlo a métodos de la ventana (no a lambdas) para que la respuesta se
    procese en el hilo de la interfaz.
    """

    listo = Signal(object, object)
    fallo = Signal(object, str)

    def __init__(self, funcion, etiqueta=None, parent=None):
        super().__init__(parent)
        self._funcion = funcion
        self.etiqueta = etiqueta

    def run(self) -> None:
        try:
            resultado = self._funcion()
        except Exception as error:  # se enseña al usuario
            self.fallo.emit(self.etiqueta, str(error))
            return
        self.listo.emit(self.etiqueta, resultado)
