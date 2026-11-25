"""Ventana de prueba de la pecera (PySide6).

Simula el final de varias sesiones y muestra cómo cambia la pecera del panel
principal. Por defecto usa una pecera de prueba que no toca la tuya; con --real
usa la de studymate/data/pecera.json.

Uso:  python -m studymate.ui.pruebas.prueba_pecera [--real]
"""

import argparse
import sys
import tempfile
from datetime import date
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QLabel, QPushButton, QVBoxLayout,
                               QWidget)

from studymate.gamificacion import pecera as pc
from studymate.ui.pecera_widget import PeceraWidget

ESTILO = """
QWidget { background: #07110D; color: #E8FFF1; font-family: 'Inter', 'Segoe UI', sans-serif; font-size: 14px; }
QLabel#titulo { font-size: 22px; font-weight: 700; color: #39FF88; }
QLabel#mensaje { background: #0F2219; border: 1px solid #1E3A2C; border-radius: 12px; padding: 12px; }
QLabel#dato { color: #9FC2AE; }
QPushButton { min-height: 44px; border-radius: 10px; padding: 0 16px; font-weight: 600;
              background: transparent; border: 1px solid #6E8B7B; color: #E8FFF1; }
QPushButton:focus { outline: none; border: 2px solid #39FF88; }
QPushButton#buena { background: #39FF88; color: #07110D; border: 0; }
QPushButton#regular { border-color: #FFC94D; color: #FFE3A3; }
QPushButton#mala { border-color: #FF8A5C; color: #FFB596; }
"""

# Sesiones de ejemplo: (texto del botón, id, resumen)
SIMULACIONES = [
    ("Sesión muy buena", "buena", pc.ResumenSesion(3600, 3420, pausas_movil=0, pausas_ausente=1, test_aciertos=13, test_total=15)),
    ("Sesión regular", "regular", pc.ResumenSesion(3600, 2700, pausas_movil=1, pausas_ausente=1)),
    ("Sesión mala", "mala", pc.ResumenSesion(3600, 1500, pausas_movil=4, pausas_ausente=2)),
]


class VentanaPrueba(QWidget):
    def __init__(self, carpeta: Path):
        super().__init__()
        self.carpeta = carpeta
        self.estado = pc.cargar(carpeta)
        self.dia = date.today()
        self.ultimo_resultado = None
        self.setWindowTitle("StudyMate · Prueba de la pecera")
        self.setStyleSheet(ESTILO)
        self.resize(1100, 640)

        titulo = QLabel("Panel principal")
        titulo.setObjectName("titulo")
        self.pecera = PeceraWidget(self.estado)
        self.mensaje = QLabel(wordWrap=True)
        self.mensaje.setObjectName("mensaje")
        self.datos = QLabel()
        self.datos.setObjectName("dato")
        self.ultimo = QLabel(wordWrap=True)

        lateral = QVBoxLayout()
        lateral.addWidget(titulo)
        lateral.addWidget(self.mensaje)
        lateral.addWidget(self.datos)
        lateral.addWidget(QLabel("Simula cómo acaba una sesión:"))
        for texto, nombre, resumen in SIMULACIONES:
            boton = QPushButton(texto)
            boton.setObjectName(nombre)
            boton.clicked.connect(lambda _=False, r=resumen: self.terminar_sesion(r))
            lateral.addWidget(boton)
        reiniciar = QPushButton("Reiniciar pecera")
        reiniciar.clicked.connect(self.reiniciar)
        lateral.addWidget(reiniciar)
        lateral.addWidget(self.ultimo)
        lateral.addStretch()

        fila = QHBoxLayout(self)
        fila.addWidget(self.pecera, 3)
        lateral_w = QWidget()
        lateral_w.setLayout(lateral)
        lateral_w.setFixedWidth(330)
        fila.addWidget(lateral_w)
        self.refrescar()

    def terminar_sesion(self, resumen: pc.ResumenSesion) -> None:
        resultado = pc.calificar(resumen)
        cambios = pc.aplicar_sesion(self.estado, resultado, self.dia)
        pc.guardar(self.estado, self.carpeta)
        self.ultimo_resultado = resultado
        nombre = {"muy_buena": "muy buena", "regular": "regular", "mala": "mala"}[resultado.calificacion.value]
        self.ultimo.setText(f"Sesión {nombre} ({resultado.puntuacion}/100). " + " ".join(cambios))
        self.refrescar()

    def reiniciar(self) -> None:
        self.estado = pc.EstadoPecera.nueva()
        pc.guardar(self.estado, self.carpeta)
        self.ultimo_resultado = None
        self.ultimo.setText("")
        self.refrescar()

    def refrescar(self) -> None:
        e = self.estado
        self.pecera.set_estado(e)
        self.mensaje.setText(pc.mensaje(e, self.ultimo_resultado))
        self.datos.setText(f"Salud {e.salud} % · {len(e.peces)} peces · agua {e.estado_agua}"
                           f" · racha {e.racha_buenas} sesiones")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--real", action="store_true", help="usar tu pecera (studymate/data/pecera.json)")
    args = parser.parse_args()
    carpeta = pc.CARPETA_DATOS if args.real else Path(tempfile.mkdtemp(prefix="pecera_"))
    app = QApplication(sys.argv)
    ventana = VentanaPrueba(carpeta)
    ventana.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
