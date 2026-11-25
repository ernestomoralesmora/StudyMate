"""Resumen al terminar: nota de la sesión, autocrítica y cómo queda la pecera (RF14)."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QScrollArea, QVBoxLayout, QWidget

from studymate.gamificacion import pecera as pc
from studymate.gamificacion import zoo as z

from .. import estilo
from ..comun import Pagina, boton, etiqueta, minutos, tarjeta
from ..companero import Companero
from ..zoo_widget import RecintoWidget


def _lista(lineas: list[str]) -> str:
    return "\n".join(f"•  {l}" for l in lineas)


class PantallaResumen(Pagina):
    def __init__(self, ventana):
        super().__init__(ventana)
        self.companero = Companero("feliz", lado_minimo=96)
        self.companero.setFixedSize(96, 96)
        self.titulo = etiqueta("Sesión terminada", "titulo")
        self.nota = etiqueta("", "cifra", ajustar=True)
        cabecera = QHBoxLayout()
        cabecera.addWidget(self.companero)
        textos = QVBoxLayout()
        textos.addWidget(self.titulo)
        textos.addWidget(self.nota)
        cabecera.addLayout(textos, 1)

        self.cifras = {}
        rejilla = QGridLayout()
        for i, (clave, texto) in enumerate([("estudiado", "estudiado"), ("plan", "previsto"),
                                           ("bloques", "bloques completos"), ("test", "aciertos en tests"),
                                           ("movil", "veces con el móvil"), ("ausente", "ausencias")]):
            cifra = etiqueta("–", "cifra")
            self.cifras[clave] = cifra
            rejilla.addWidget(cifra, (i // 3) * 2, i % 3)
            rejilla.addWidget(etiqueta(texto, "nota"), (i // 3) * 2 + 1, i % 3)
        self.bien = etiqueta("")
        self.mejorar = etiqueta("")
        self.motivos = etiqueta("", "nota")
        autocritica = tarjeta(etiqueta("CÓMO HA IDO", "seccion"), rejilla, self.motivos,
                              etiqueta("QUÉ HA IDO BIEN", "seccion"), self.bien,
                              etiqueta("QUÉ PUEDO MEJORAR", "seccion"), self.mejorar)

        self.titulo_recinto = etiqueta("TU ZOO", "seccion")
        self.recinto = RecintoWidget(z.Recinto("—", "pez"))
        self.recinto.setMinimumSize(420, 236)
        self.cambios = etiqueta("")
        caja_pecera = tarjeta(self.titulo_recinto, self.recinto, self.cambios)

        contenido = QWidget()
        cuerpo = QHBoxLayout(contenido)
        cuerpo.setContentsMargins(0, 0, 8, 0)
        cuerpo.setSpacing(16)
        cuerpo.addWidget(autocritica, 1)
        cuerpo.addWidget(caja_pecera, 1)
        desplazable = QScrollArea()
        desplazable.setWidgetResizable(True)
        desplazable.setWidget(contenido)

        self.volver = boton("Volver al panel principal", "primario", lambda: ventana.ir("inicio"))
        fila = QHBoxLayout()
        fila.addStretch()
        fila.addWidget(self.volver)

        capa = QVBoxLayout(self)
        capa.setContentsMargins(28, 24, 28, 24)
        capa.setSpacing(16)
        capa.addLayout(cabecera)
        capa.addWidget(desplazable, 1)
        capa.addLayout(fila)

    def mostrar(self, resultado: pc.ResultadoCalificacion, recinto: z.Recinto | None,
                cambios: list[str], controlador, terminada_antes: bool) -> None:
        c = controlador
        escala = 60.0 / c.segundos_por_minuto  # en modo prueba, minutos "del plan"
        cal = resultado.calificacion.value
        if not resultado.cuenta:
            self.nota.setText("Sesión demasiado corta: no cuenta para la pecera")
            self.nota.setStyleSheet(f"color: {estilo.TEXTO_2};")
            self.companero.set_expresion("neutro")
        else:
            self.nota.setText(f"Sesión {estilo.NOMBRE_CALIFICACION[cal].lower()} · {resultado.puntuacion}/100")
            self.nota.setStyleSheet(f"color: {estilo.COLOR_CALIFICACION[cal]};")
            self.companero.set_expresion({"muy_buena": "feliz", "regular": "concentrado",
                                          "mala": "triste"}[cal])
        self.titulo.setText("Sesión terminada antes de tiempo" if terminada_antes else "¡Sesión terminada!")
        self.cifras["estudiado"].setText(minutos(c.estudiado_s * escala))
        self.cifras["plan"].setText(minutos(c.planificado_s * escala))
        self.cifras["bloques"].setText(f"{c.bloques_completados}/{c.numero_bloques}")
        self.cifras["test"].setText(f"{c.test_aciertos}/{c.test_total}" if c.test_total else "–")
        self.cifras["movil"].setText(str(c.pausas_movil))
        self.cifras["ausente"].setText(str(c.pausas_ausente))
        self.motivos.setText(" ".join(resultado.motivos))
        self.bien.setText(_lista(resultado.bien) if resultado.bien else "—")
        self.mejorar.setText(_lista(resultado.mejorar) if resultado.mejorar else "¡Nada! Sigue así.")
        if recinto is not None:
            self.recinto.show()
            self.recinto.set_recinto(recinto)
            self.titulo_recinto.setText(f"RECINTO DE {recinto.asignatura.upper()} · NIVEL {recinto.nivel}")
            racha = f"Racha: {recinto.texto_racha()}." if recinto.racha_buenas else ""
            self.cambios.setText(_lista(cambios) + ("\n\n" + racha if racha else ""))
        else:
            self.recinto.hide()
            self.titulo_recinto.setText("TU ZOO")
            self.cambios.setText(_lista(cambios))
        self.volver.setFocus()
