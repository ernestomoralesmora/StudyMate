"""Historial de sesiones: totales, minutos de los últimos 7 días y la lista."""

from datetime import datetime

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import (QAbstractItemView, QGridLayout, QHBoxLayout, QHeaderView,
                               QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from studymate.sesion.historial import cargar_historial, estadisticas, minutos_por_dia

from .. import estilo
from ..comun import Pagina, boton, etiqueta, tarjeta

DIAS = "LMXJVSD"


class GraficaSemana(QWidget):
    """Barras con los minutos estudiados cada día de la última semana."""

    def __init__(self):
        super().__init__()
        self.datos: list = []
        self.setMinimumHeight(170)
        self.setAccessibleName("Minutos estudiados en los últimos 7 días")

    def set_datos(self, datos) -> None:
        self.datos = datos
        self.setAccessibleDescription(", ".join(f"{d.strftime('%d/%m')}: {round(m)} min" for d, m in datos))
        self.update()

    def paintEvent(self, _evento):
        if not self.datos:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        fuente = QFont(self.font())
        fuente.setPixelSize(12)
        p.setFont(fuente)
        maximo = max(max(m for _, m in self.datos), 1)
        n = len(self.datos)
        hueco = self.width() / n
        alto_barras = self.height() - 44
        for i, (dia, mins) in enumerate(self.datos):
            ancho = min(42, hueco * 0.6)
            x = i * hueco + (hueco - ancho) / 2
            h = alto_barras * mins / maximo
            hoy = i == n - 1
            color = QColor(estilo.ACENTO if hoy else "#2BBF6A")
            p.setPen(Qt.NoPen)
            p.setBrush(color if mins else QColor(estilo.BORDE))
            p.drawRoundedRect(QRectF(x, 18 + alto_barras - max(h, 3), ancho, max(h, 3)), 5, 5)
            p.setPen(QColor(estilo.TEXTO if mins else estilo.TEXTO_2))
            p.drawText(QRectF(i * hueco, 18 + alto_barras - max(h, 3) - 18, hueco, 16),
                       Qt.AlignCenter, f"{round(mins)}" if mins else "")
            p.setPen(QColor(estilo.TEXTO if hoy else estilo.TEXTO_2))
            p.drawText(QRectF(i * hueco, self.height() - 22, hueco, 18), Qt.AlignCenter,
                       "Hoy" if hoy else DIAS[dia.weekday()])
        p.end()


class PantallaHistorial(Pagina):
    COLUMNAS = ["Fecha", "Asignatura", "Temas", "Estudiado", "Previsto", "Nota", "Test", "Móvil", "Ausencias"]

    def __init__(self, ventana):
        super().__init__(ventana)
        self.cifras = {}
        rejilla = QGridLayout()
        rejilla.setHorizontalSpacing(24)
        for i, (clave, texto) in enumerate([("sesiones", "sesiones"), ("minutos_total", "min en total"),
                                           ("minutos_semana", "min esta semana"),
                                           ("media_puntuacion", "nota media"),
                                           ("acierto_test", "% aciertos en tests")]):
            cifra = etiqueta("0", "cifra")
            self.cifras[clave] = cifra
            rejilla.addWidget(cifra, 0, i)
            rejilla.addWidget(etiqueta(texto, "nota"), 1, i)
        self.grafica = GraficaSemana()
        arriba = QHBoxLayout()
        arriba.setSpacing(16)
        arriba.addWidget(tarjeta(etiqueta("EN TOTAL", "seccion"), rejilla), 3)
        arriba.addWidget(tarjeta(etiqueta("ÚLTIMOS 7 DÍAS (MIN)", "seccion"), self.grafica), 2)

        self.tabla = QTableWidget(0, len(self.COLUMNAS))
        self.tabla.setHorizontalHeaderLabels(self.COLUMNAS)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabla.setShowGrid(False)
        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.tabla.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.vacio = etiqueta("Todavía no hay sesiones. ¡La primera te espera!", "subtitulo")

        fila = QHBoxLayout()
        fila.addWidget(boton("Volver al panel principal", None, lambda: ventana.ir("inicio")))
        fila.addStretch()

        capa = QVBoxLayout(self)
        capa.setContentsMargins(28, 24, 28, 24)
        capa.setSpacing(16)
        capa.addWidget(etiqueta("Historial", "titulo"))
        capa.addLayout(arriba)
        capa.addWidget(self.vacio)
        capa.addWidget(self.tabla, 1)
        capa.addLayout(fila)

    def al_mostrar(self) -> None:
        historial = cargar_historial()
        e = estadisticas(historial)
        for clave, cifra in self.cifras.items():
            valor = e[clave]
            cifra.setText("–" if valor is None else str(valor))
        self.grafica.set_datos(minutos_por_dia(historial))
        self.vacio.setVisible(not historial)
        self.tabla.setRowCount(0)
        for r in reversed(historial):
            fila = self.tabla.rowCount()
            self.tabla.insertRow(fila)
            fecha = datetime.fromisoformat(r.fecha).strftime("%d/%m/%Y %H:%M")
            valores = [
                fecha + ("  (prueba)" if r.modo_prueba else ""),
                r.asignatura or "—",
                ", ".join(r.temas),
                f"{round(r.estudiado_min)} min",
                f"{round(r.planificado_min)} min",
                f"{estilo.NOMBRE_CALIFICACION.get(r.calificacion, r.calificacion)} ({r.puntuacion})",
                f"{r.test_aciertos}/{r.test_total}" if r.test_total else "–",
                str(r.pausas_movil),
                str(r.pausas_ausente),
            ]
            for col, texto in enumerate(valores):
                item = QTableWidgetItem(texto)
                if col == 5:
                    item.setForeground(QColor(estilo.COLOR_CALIFICACION.get(r.calificacion, estilo.TEXTO)))
                self.tabla.setItem(fila, col, item)
