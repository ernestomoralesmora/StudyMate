"""Piezas comunes de la interfaz: tarjetas, textos, botones e hilos de trabajo."""

import cv2
from PySide6.QtCore import QRegularExpression, QThread, Qt, Signal
from PySide6.QtGui import QImage, QPixmap, QRegularExpressionValidator
from PySide6.QtWidgets import QComboBox, QFrame, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget


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


class ComboSinRueda(QComboBox):
    """Desplegable que no cambia con la rueda del ratón: la rueda mueve la página.

    Así, al bajar por un formulario con la rueda, no se cambia un valor sin querer.
    """

    def wheelEvent(self, evento):  # noqa: N802 (nombre de Qt)
        evento.ignore()


class SelectorMinutos(ComboSinRueda):
    """Minutos: se eligen en la lista que se despliega o se escriben con el teclado.

    No hay flechas ni rueda. Lo escrito se limita al rango [minimo, maximo].
    """

    def __init__(self, opciones: list[int], minimo: int, maximo: int, parent=None):
        super().__init__(parent)
        self.minimo, self.maximo = minimo, maximo
        self.opciones, self.tope = list(opciones), maximo
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.NoInsert)  # lo escrito no se añade a la lista
        self._llenar()
        self.lineEdit().setValidator(
            QRegularExpressionValidator(QRegularExpression(r"^\s*\d{0,3}\s*(m|mi|min)?\s*$"), self))
        self.lineEdit().editingFinished.connect(lambda: self.setValue(self.value()))

    def _llenar(self) -> None:
        self.clear()
        opciones = [m for m in self.opciones if self.minimo <= m <= self.maximo]
        if self.maximo not in opciones and self.maximo < self.tope:
            opciones.append(self.maximo)  # p. ej., con 25 min de estudio, la opción «25 min»
        for m in opciones:
            self.addItem(f"{m} min", m)

    def poner_maximo(self, maximo: int) -> None:
        """Cambia el máximo (sin pasar del original) y ajusta la lista y el valor elegido."""
        actual = self.value()
        self.maximo = max(self.minimo, min(self.tope, int(maximo)))
        self._llenar()
        self.setValue(min(actual, self.maximo))

    def value(self) -> int:
        cifras = "".join(c for c in self.currentText() if c.isdigit())
        valor = int(cifras) if cifras else self.minimo
        return max(self.minimo, min(self.maximo, valor))

    def setValue(self, minutos: int) -> None:  # noqa: N802 (como QSpinBox)
        minutos = max(self.minimo, min(self.maximo, int(minutos)))
        indice = self.findData(minutos)
        if indice >= 0:
            self.setCurrentIndex(indice)
        else:
            self.setEditText(f"{minutos} min")
