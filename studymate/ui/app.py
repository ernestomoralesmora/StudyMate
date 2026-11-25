"""Arranca la interfaz de StudyMate.

Uso:  python -m studymate.main      (o  python -m studymate.ui.app)
"""

import sys

from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import QApplication

from . import estilo
from .companero import Companero
from .ventana import VentanaPrincipal


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("StudyMate")
    fuente = QFont("Segoe UI")
    fuente.setPointSize(10)
    app.setFont(fuente)
    app.setStyleSheet(estilo.HOJA)

    icono = Companero("feliz")
    icono.resize(64, 64)
    app.setWindowIcon(QIcon(icono.grab()))

    ventana = VentanaPrincipal()
    ventana.resize(1280, 800)
    ventana.setMinimumSize(1024, 680)
    ventana.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
