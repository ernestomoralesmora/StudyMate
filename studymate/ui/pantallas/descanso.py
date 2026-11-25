"""Descanso entre bloques: cuenta atrás y el compañero relajado."""

import random
import time

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QHBoxLayout, QVBoxLayout

from ..comun import Pagina, boton, etiqueta, minutos, tarjeta
from ..companero import Companero

CONSEJOS = [
    "Levántate y estira la espalda y los brazos.",
    "Bebe un poco de agua.",
    "Mira algo lejano por la ventana: descansa la vista.",
    "Respira hondo cinco veces.",
    "Mejor sin móvil: así el descanso descansa de verdad.",
    "Da un paseo corto por la habitación.",
]


class PantallaDescanso(Pagina):
    def __init__(self, ventana):
        super().__init__(ventana)
        self._avisado = False
        self.companero = Companero("descanso", lado_minimo=180)
        self.cuenta = etiqueta("05:00", "grande")
        self.cuenta.setAlignment(Qt.AlignCenter)
        self.consejo = etiqueta("")
        self.consejo.setAlignment(Qt.AlignCenter)
        self.siguiente = etiqueta("", "nota")
        self.siguiente.setAlignment(Qt.AlignCenter)
        self.siguiente.setTextFormat(Qt.PlainText)
        caja = tarjeta(self.companero, etiqueta("DESCANSO", "seccion"), self.cuenta, self.consejo,
                       self.siguiente, espacio=12, margen=28)

        centro = QHBoxLayout()
        centro.addStretch()
        centro.addWidget(caja, 2)
        centro.addStretch()
        self.continuar = boton("Empezar ya el siguiente bloque", "primario", ventana.descanso_terminado)

        capa = QVBoxLayout(self)
        capa.setContentsMargins(28, 24, 28, 24)
        capa.setSpacing(16)
        capa.addWidget(etiqueta("¡Bloque terminado! Toca descansar", "titulo"))
        capa.addWidget(etiqueta("El tiempo de estudio está parado durante el descanso.", "subtitulo"))
        capa.addLayout(centro, 1)
        fila = QHBoxLayout()
        fila.addStretch()
        fila.addWidget(self.continuar)
        capa.addLayout(fila)

    def al_mostrar(self) -> None:
        c = self.ventana.controlador
        self._avisado = False
        self.consejo.setText(random.choice(CONSEJOS))
        siguiente = c.plan.bloques[c.indice + 1] if c.indice + 1 < c.numero_bloques else None
        self.siguiente.setText(f"Después: bloque {c.indice + 2} · {siguiente.tema}" if siguiente else "")
        self.continuar.setFocus()

    def con_instantanea(self, _inst) -> None:
        restante = self.ventana.controlador.restante_descanso(time.monotonic())
        self.cuenta.setText(minutos(restante))
        if restante <= 0 and not self._avisado:
            self._avisado = True
            QApplication.beep()
            self.ventana.descanso_terminado()
