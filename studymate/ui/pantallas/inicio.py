"""Panel principal: el zoo (un recinto por asignatura), la última sesión y empezar a estudiar."""

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (QFrame, QGridLayout, QHBoxLayout, QMessageBox, QProgressBar,
                               QScrollArea, QVBoxLayout, QWidget)

from studymate.gamificacion import zoo as z
from studymate.sesion.historial import cargar_historial, estadisticas

from .. import estilo
from ..comun import Pagina, boton, etiqueta, tarjeta
from ..companero import Companero
from ..dialogo_asignatura import DialogoAsignatura
from ..zoo_widget import AnimalIcono, RecintoWidget


def color_salud(salud: int) -> str:
    return estilo.ACENTO if salud >= 60 else estilo.DUDOSO if salud >= 30 else estilo.MOVIL


def horas(minutos: float) -> str:
    m = int(round(minutos))
    return f"{m // 60} h {m % 60} min" if m >= 60 else f"{m} min"


class BarrasAvance(QWidget):
    """Las últimas 10 sesiones de una asignatura: color = calificación, alto = minutos."""

    def __init__(self, sesiones: list[dict]):
        super().__init__()
        self.sesiones = sesiones[-10:]
        self.setFixedHeight(34)
        nombres = {"muy_buena": "muy buena", "regular": "regular", "mala": "mala"}
        self.setAccessibleName("Últimas sesiones: " + (", ".join(
            nombres.get(s["calificacion"], s["calificacion"]) for s in self.sesiones) or "ninguna"))

    def paintEvent(self, _evento):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        if not self.sesiones:
            p.setPen(QColor(estilo.TEXTO_2))
            p.drawText(self.rect(), Qt.AlignVCenter | Qt.AlignLeft, "Aún no hay sesiones")
            p.end()
            return
        ancho = min(22.0, (self.width() - 9 * 5) / 10)
        maximo = max(60.0, max(s.get("minutos", 0) for s in self.sesiones))
        for i, s in enumerate(self.sesiones):
            alto = 8 + 26 * min(1.0, s.get("minutos", 0) / maximo)
            p.setBrush(QColor(estilo.COLOR_CALIFICACION.get(s["calificacion"], estilo.TEXTO_2)))
            p.drawRoundedRect(QRectF(i * (ancho + 5), self.height() - alto, ancho, alto), 4, 4)
        p.end()


class TarjetaRecinto(QFrame):
    def __init__(self, recinto: z.Recinto, al_quitar):
        super().__init__()
        self.setObjectName("tarjeta")
        r = recinto
        capa = QVBoxLayout(self)
        capa.setContentsMargins(0, 0, 0, 16)
        capa.setSpacing(10)
        capa.addWidget(RecintoWidget(r))

        cuerpo = QVBoxLayout()
        cuerpo.setContentsMargins(16, 0, 16, 0)
        cuerpo.setSpacing(8)
        cabecera = QHBoxLayout()
        cabecera.addWidget(AnimalIcono(r.especie, 34))
        textos = QVBoxLayout()
        nombre = etiqueta(r.asignatura, "cifra", ajustar=True)
        nombre.setTextFormat(Qt.PlainText)
        nombre.setStyleSheet("font-size: 18px;")
        textos.addWidget(nombre)
        textos.addWidget(etiqueta(f"{r.animal.habitat} · nivel {r.nivel} · {r.describir_animales()}", "nota"))
        cabecera.addLayout(textos, 1)
        quitar = boton("Quitar", None, lambda: al_quitar(r))
        quitar.setToolTip(f"Quitar {r.asignatura} del zoo")
        quitar.setMinimumHeight(32)
        cabecera.addWidget(quitar, 0, Qt.AlignTop)
        cuerpo.addLayout(cabecera)

        salud = QProgressBar()
        salud.setRange(0, 100)
        salud.setValue(r.salud)
        salud.setTextVisible(False)
        salud.setAccessibleName(f"Salud del recinto: {r.salud} por ciento")
        salud.setStyleSheet(f"QProgressBar::chunk {{ background: {color_salud(r.salud)}; border-radius: 6px; }}")
        fila_salud = QHBoxLayout()
        fila_salud.addWidget(salud, 1)
        fila_salud.addWidget(etiqueta(f"{r.salud} % salud", "nota", ajustar=False))
        cuerpo.addLayout(fila_salud)

        fila_avance = QHBoxLayout()
        fila_avance.addWidget(etiqueta("AVANCE", "seccion"))
        fila_avance.addStretch()
        resumen = f"{len(r.sesiones)} sesiones · {horas(r.minutos)}" if r.sesiones else "sin sesiones"
        if r.racha_buenas:
            resumen += f" · racha {r.racha_buenas}"
        fila_avance.addWidget(etiqueta(resumen, "nota", ajustar=False))
        cuerpo.addLayout(fila_avance)
        cuerpo.addWidget(BarrasAvance(r.sesiones))
        capa.addLayout(cuerpo)


class PantallaInicio(Pagina):
    def __init__(self, ventana):
        super().__init__(ventana)
        cabecera = QHBoxLayout()
        self.companero = Companero("concentrado", lado_minimo=72)
        self.companero.setFixedSize(72, 72)
        titulos = QVBoxLayout()
        titulos.addWidget(etiqueta("Mi zoo", "titulo"))
        titulos.addWidget(etiqueta("Un animal por asignatura. Cada uno crece con tus sesiones de esa asignatura.",
                                   "subtitulo"))
        cabecera.addWidget(self.companero)
        cabecera.addLayout(titulos, 1)

        # Recintos (se rehacen cada vez que se muestra la pantalla).
        self.contenido = QWidget()
        self.rejilla = QGridLayout(self.contenido)
        self.rejilla.setContentsMargins(0, 0, 8, 0)
        self.rejilla.setSpacing(16)
        desplazable = QScrollArea()
        desplazable.setWidgetResizable(True)
        desplazable.setWidget(self.contenido)

        self.empezar = boton("Empezar una sesión", "primario", ventana.ir_cuestionario)
        self.empezar.setMinimumHeight(56)
        self.mensaje = etiqueta("")
        acciones = tarjeta(self.mensaje, self.empezar,
                           boton("Añadir una asignatura", None, self._anadir),
                           boton("Ver el historial", None, lambda: ventana.ir("historial")))

        self.cifras = {}
        cifras = QGridLayout()
        cifras.setHorizontalSpacing(16)
        for i, (clave, texto) in enumerate([("asignaturas", "asignaturas"), ("animales", "animales"),
                                           ("semana", "min esta semana"), ("total", "estudiado en total")]):
            cifra = etiqueta("0", "cifra")
            self.cifras[clave] = cifra
            cifras.addWidget(cifra, (i // 2) * 2, i % 2)
            cifras.addWidget(etiqueta(texto, "nota"), (i // 2) * 2 + 1, i % 2)
        resumen = tarjeta(etiqueta("TU ZOO", "seccion"), cifras)

        self.ultima_titulo = etiqueta("", "cifra", ajustar=True)
        self.ultima_texto = etiqueta("")
        self.ultima = tarjeta(etiqueta("TU ÚLTIMA SESIÓN", "seccion"), self.ultima_titulo, self.ultima_texto)

        lateral = QVBoxLayout()
        lateral.setSpacing(16)
        lateral.addWidget(acciones)
        lateral.addWidget(resumen)
        lateral.addWidget(self.ultima)
        lateral.addStretch()
        caja_lateral = QWidget()
        caja_lateral.setLayout(lateral)
        caja_lateral.setFixedWidth(340)

        cuerpo = QHBoxLayout()
        cuerpo.setSpacing(16)
        cuerpo.addWidget(desplazable, 1)
        cuerpo.addWidget(caja_lateral)

        capa = QVBoxLayout(self)
        capa.setContentsMargins(28, 24, 28, 24)
        capa.setSpacing(18)
        capa.addLayout(cabecera)
        capa.addLayout(cuerpo, 1)

    def al_mostrar(self) -> None:
        zoo = z.cargar()
        self._pintar_recintos(zoo)
        self.mensaje.setText(z.mensaje(zoo))
        e = estadisticas(cargar_historial())
        self.cifras["asignaturas"].setText(f"{len(zoo.recintos)}/{z.MAX_RECINTOS}")
        self.cifras["animales"].setText(str(zoo.total_animales))
        self.cifras["semana"].setText(str(e["minutos_semana"]))
        self.cifras["total"].setText(horas(zoo.total_minutos))
        peor = zoo.necesita_atencion()
        self.companero.set_expresion("neutro" if peor is None else "feliz" if peor.salud >= 80
                                     else "concentrado" if peor.salud >= 45 else "triste")

        ultima = self.ventana.ultima_sesion
        self.ultima.setVisible(ultima is not None)
        if ultima:
            asignatura, resultado = ultima
            cal = resultado.calificacion.value
            self.ultima_titulo.setText(f"{asignatura}: {estilo.NOMBRE_CALIFICACION[cal].lower()}")
            self.ultima_titulo.setStyleSheet(f"color: {estilo.COLOR_CALIFICACION[cal]}; font-size: 18px;")
            consejos = resultado.mejorar or resultado.bien
            self.ultima_texto.setText("\n".join(f"•  {c}" for c in consejos[:3]))
        self.empezar.setFocus()

    def _pintar_recintos(self, zoo: z.Zoo) -> None:
        while self.rejilla.count():
            item = self.rejilla.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if not zoo.recintos:
            vacio = tarjeta(
                etiqueta("Tu zoo está vacío", "cifra"),
                etiqueta("Añade las asignaturas de este curso y elige un animal para cada una. "
                         "Cada recinto crecerá con tus sesiones de esa asignatura."),
                boton("Añadir mi primera asignatura", "primario", self._anadir),
            )
            self.rejilla.addWidget(vacio, 0, 0)
            self.rejilla.setRowStretch(1, 1)
            return
        for i, recinto in enumerate(zoo.recintos):
            self.rejilla.addWidget(TarjetaRecinto(recinto, self._quitar), i // 2, i % 2)
        self.rejilla.setRowStretch((len(zoo.recintos) + 1) // 2, 1)

    def _anadir(self) -> None:
        dialogo = DialogoAsignatura(z.cargar(), self)
        if dialogo.exec():
            self.al_mostrar()

    def _quitar(self, recinto: z.Recinto) -> None:
        respuesta = QMessageBox.question(
            self, "Quitar asignatura",
            f"¿Quitar {recinto.asignatura} del zoo? Se pierden su recinto, sus "
            f"{recinto.animal.plural} y su avance. No se puede deshacer.",
        )
        if respuesta == QMessageBox.Yes:
            zoo = z.cargar()
            zoo.quitar(recinto.asignatura)
            z.guardar(zoo)
            self.al_mostrar()
