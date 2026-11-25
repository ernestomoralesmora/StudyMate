"""La sesión de estudio: tiempo del bloque, estado de la cámara y el compañero.

El tiempo del bloque solo avanza mientras estás estudiando (lo decide la
cámara). Si hay una duda, aparece una pregunta abajo: se responde con los
botones o con las teclas S y N. Si el móvil se mueve de su sitio, suena un aviso.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QApplication, QCheckBox, QFrame, QHBoxLayout, QMessageBox,
                               QProgressBar, QVBoxLayout)

from studymate.vision.estados import Estado
from studymate.vision.observacion import SitioMovil

from .. import estilo
from ..camara_widget import CamaraWidget
from ..comun import Pagina, boton, etiqueta, minutos, tarjeta
from ..companero import Companero


class PantallaSesion(Pagina):
    def __init__(self, ventana):
        super().__init__(ventana)
        self._banner_visible = False

        self.bloque = etiqueta("", "titulo")
        self.bloque.setTextFormat(Qt.PlainText)
        self.objetivo = etiqueta("", "subtitulo")
        self.objetivo.setTextFormat(Qt.PlainText)
        cabecera = QHBoxLayout()
        textos = QVBoxLayout()
        textos.addWidget(self.bloque)
        textos.addWidget(self.objetivo)
        cabecera.addLayout(textos, 1)
        cabecera.addWidget(boton("Terminar la sesión", "peligro", self._terminar), 0, Qt.AlignTop)

        # Columna principal: compañero, estado y tiempo.
        self.companero = Companero("concentrado", lado_minimo=150)
        self.estado = etiqueta("", "cifra")
        self.estado.setAlignment(Qt.AlignCenter)
        self.restante = etiqueta("00:00", "grande")
        self.restante.setAlignment(Qt.AlignCenter)
        self.progreso = QProgressBar()
        self.progreso.setRange(0, 1000)
        self.progreso.setTextVisible(False)
        self.progreso.setAccessibleName("Progreso del bloque")
        self.total = etiqueta("", "nota")
        self.total.setAlignment(Qt.AlignCenter)
        principal = tarjeta(self.companero, self.estado, etiqueta("QUEDA DE ESTE BLOQUE", "seccion"),
                            self.restante, self.progreso, self.total, espacio=10, margen=24)

        # Columna de la cámara.
        self.camara = CamaraWidget(permitir_marcar=False)
        self.ver_camara = QCheckBox("Ver la cámara")
        self.ver_camara.setChecked(True)
        self.ver_camara.toggled.connect(self.camara.setVisible)
        self.sitio = etiqueta("", "nota")
        lateral = tarjeta(etiqueta("CÁMARA", "seccion"), self.camara, self.ver_camara, self.sitio,
                          etiqueta("Las imágenes se analizan en tu ordenador y no se guardan.", "nota"))

        cuerpo = QHBoxLayout()
        cuerpo.setSpacing(16)
        cuerpo.addWidget(principal, 3)
        cuerpo.addWidget(lateral, 2)

        # Pregunta cuando hay una duda.
        self.banner = QFrame()
        self.banner.setObjectName("banner")
        self.pregunta = etiqueta("", "cifra")
        self.si = boton("Sí, sigo estudiando  (S)", "primario", lambda: self._responder(True))
        self.no = boton("No  (N)", None, lambda: self._responder(False))
        fila = QHBoxLayout(self.banner)
        fila.setContentsMargins(20, 14, 20, 14)
        fila.addWidget(self.pregunta, 1)
        fila.addWidget(self.si)
        fila.addWidget(self.no)
        self.banner.hide()

        capa = QVBoxLayout(self)
        capa.setContentsMargins(28, 24, 28, 24)
        capa.setSpacing(16)
        capa.addLayout(cabecera)
        capa.addLayout(cuerpo, 1)
        capa.addWidget(self.banner)

    def al_mostrar(self) -> None:
        c = self.ventana.controlador
        b = c.bloque
        self.bloque.setText(f"Bloque {c.indice + 1} de {c.numero_bloques} · {b.tema}")
        self.objetivo.setText(f"Objetivo: {b.objetivo}")
        self.banner.hide()
        self._banner_visible = False
        self.setFocus()

    def con_instantanea(self, inst) -> None:
        if inst is None:
            return
        c = self.ventana.controlador
        estado = inst.estado.value
        color = estilo.COLOR_ESTADO[estado]
        self.estado.setText(estilo.NOMBRE_ESTADO[estado])
        self.estado.setStyleSheet(f"color: {color};")
        self.companero.set_estado(estado)
        self.restante.setText(minutos(c.restante_bloque_s))
        self.restante.setStyleSheet(f"color: {estilo.TEXTO if estado == 'ESTUDIANDO' else estilo.TEXTO_2};")
        self.progreso.setValue(int(1000 * c.progreso_bloque))
        pausa = "" if estado == "ESTUDIANDO" else "  ·  el tiempo está parado"
        self.total.setText(f"Estudiado hoy: {minutos(c.estudiado_s)}{pausa}")

        if self.camara.isVisible():
            self.camara.set_frame(inst.frame)
            self.camara.set_borde(color)
        recuadro = self.ventana.motor.recuadro_aparcado if self.ventana.motor else None
        sitio = inst.sitio_movil
        if sitio == SitioMovil.EN_SU_SITIO and recuadro:
            self.camara.set_sitio(recuadro, estilo.ACENTO, "móvil en su sitio")
            self.sitio.setText("📱 Tu móvil está en su sitio.")
        elif sitio == SitioMovil.FUERA and recuadro:
            self.camara.set_sitio(recuadro, estilo.MOVIL, "¡no está!")
            self.sitio.setText("📱 Tu móvil no está en su sitio.")
        else:
            self.camara.set_sitio(None)
            self.sitio.setText("Se vigila el móvil en tus manos." if sitio != SitioMovil.SIN_USAR
                               else "")

        duda = inst.estado == Estado.DUDOSO and inst.esperando_confirmacion
        if duda and not self._banner_visible:
            if sitio == SitioMovil.FUERA:
                self.pregunta.setText("Tu móvil no está en su sitio. ¿Sigues estudiando?")
                QApplication.beep()  # la alarma
            else:
                self.pregunta.setText("No te veo bien. ¿Sigues estudiando?")
            self.banner.show()
            self.si.setFocus()
        elif not duda and self._banner_visible:
            self.banner.hide()
            self.setFocus()
        self._banner_visible = duda

    def _responder(self, estudiando: bool) -> None:
        self.ventana.responder_duda(estudiando)
        self.banner.hide()
        self._banner_visible = False
        self.setFocus()

    def _terminar(self) -> None:
        respuesta = QMessageBox.question(
            self, "Terminar la sesión",
            "¿Seguro que quieres terminar ya? La sesión se calificará con lo que llevas.",
        )
        if respuesta == QMessageBox.Yes:
            self.ventana.terminar_sesion()

    def keyPressEvent(self, evento):
        if self._banner_visible and evento.key() == Qt.Key_S:
            self._responder(True)
        elif self._banner_visible and evento.key() == Qt.Key_N:
            self._responder(False)
        else:
            super().keyPressEvent(evento)
