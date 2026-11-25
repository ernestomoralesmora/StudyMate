"""Panel principal: la pecera, el mensaje del compañero y empezar a estudiar."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QVBoxLayout

from studymate.gamificacion import pecera as pc
from studymate.sesion.historial import cargar_historial, estadisticas

from ..comun import Pagina, boton, etiqueta, tarjeta
from ..companero import Companero
from ..pecera_widget import PeceraWidget


class PantallaInicio(Pagina):
    def __init__(self, ventana):
        super().__init__(ventana)
        self.estado = pc.cargar()

        cabecera = QHBoxLayout()
        self.companero = Companero("concentrado", lado_minimo=72)
        self.companero.setFixedSize(72, 72)
        titulos = QVBoxLayout()
        titulos.addWidget(etiqueta("StudyMate", "titulo"))
        titulos.addWidget(etiqueta("Tu compañero de estudio", "subtitulo"))
        cabecera.addWidget(self.companero)
        cabecera.addLayout(titulos, 1)

        self.pecera = PeceraWidget(self.estado)
        self.pecera.setMinimumSize(520, 300)
        self.mensaje = etiqueta("", None)
        self.mensaje.setTextFormat(Qt.PlainText)
        izquierda = tarjeta(etiqueta("TU PECERA", "seccion"), self.pecera, self.mensaje)

        self.cifras = {}
        rejilla = QGridLayout()
        rejilla.setHorizontalSpacing(16)
        for i, (clave, texto) in enumerate([("minutos_semana", "min esta semana"),
                                           ("sesiones_semana", "sesiones esta semana"),
                                           ("racha", "muy buenas seguidas"),
                                           ("peces", "peces")]):
            cifra = etiqueta("0", "cifra")
            self.cifras[clave] = cifra
            rejilla.addWidget(cifra, (i // 2) * 2, i % 2)
            rejilla.addWidget(etiqueta(texto, "nota"), (i // 2) * 2 + 1, i % 2)
        resumen = tarjeta(etiqueta("ESTA SEMANA", "seccion"), rejilla)

        self.empezar = boton("Empezar una sesión", "primario", ventana.ir_cuestionario)
        self.empezar.setMinimumHeight(56)
        acciones = tarjeta(
            etiqueta("¿Listo para estudiar?", "cifra"),
            etiqueta("Te haremos unas preguntas rápidas para adaptar los bloques a ti.", "nota"),
            self.empezar,
            boton("Ver el historial", None, lambda: ventana.ir("historial")),
        )

        derecha = QVBoxLayout()
        derecha.setSpacing(16)
        derecha.addWidget(acciones)
        derecha.addWidget(resumen)
        derecha.addStretch()

        cuerpo = QHBoxLayout()
        cuerpo.setSpacing(16)
        cuerpo.addWidget(izquierda, 3)
        cuerpo.addLayout(derecha, 2)

        capa = QVBoxLayout(self)
        capa.setContentsMargins(28, 24, 28, 24)
        capa.setSpacing(18)
        capa.addLayout(cabecera)
        capa.addLayout(cuerpo, 1)

    def al_mostrar(self) -> None:
        self.estado = pc.cargar()
        self.pecera.set_estado(self.estado)
        self.mensaje.setText(pc.mensaje(self.estado, self.ventana.ultimo_resultado))
        e = estadisticas(cargar_historial())
        self.cifras["minutos_semana"].setText(str(e["minutos_semana"]))
        self.cifras["sesiones_semana"].setText(str(e["sesiones_semana"]))
        self.cifras["racha"].setText(str(self.estado.racha_buenas))
        self.cifras["peces"].setText(str(len(self.estado.peces)))
        salud = self.estado.salud
        self.companero.set_expresion("feliz" if salud >= 80 else "concentrado" if salud >= 45 else "triste")
        self.empezar.setFocus()
