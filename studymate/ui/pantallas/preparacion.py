"""Preparación (30 s): la cámara enseña el sitio de estudio y se marca el móvil.

Idea de la profesora: el móvil se deja a la vista y, si desaparece de ese
sitio durante la sesión, salta un aviso. El tiempo todavía no cuenta.
"""

import time

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout

from studymate.vision.observacion import SitioMovil
from studymate.vision.preparacion import Preparacion

from .. import estilo
from ..camara_widget import CamaraWidget
from ..comun import Pagina, boton, etiqueta, tarjeta


class PantallaPreparacion(Pagina):
    def __init__(self, ventana):
        super().__init__(ventana)
        self.preparacion: Preparacion | None = None
        self._ultimo_frame = None

        self.camara = CamaraWidget(permitir_marcar=True)
        self.camara.movil_marcado.connect(self._marcar)
        self.cuenta = etiqueta("30", "grande")
        self.cuenta.setAlignment(Qt.AlignCenter)
        self.instrucciones = etiqueta("")
        self.estado_movil = etiqueta("", "nota")
        self.empezar = boton("Empezar ya  (Enter)", "primario", self._empezar)
        self.empezar.setEnabled(False)

        lateral = QVBoxLayout()
        lateral.setSpacing(16)
        lateral.addWidget(tarjeta(etiqueta("EMPIEZA EN", "seccion"), self.cuenta,
                                  etiqueta("segundos (el tiempo de estudio aún no cuenta)", "nota")))
        lateral.addWidget(tarjeta(etiqueta("QUÉ HACER", "seccion"), self.instrucciones, self.estado_movil))
        lateral.addStretch()
        lateral.addWidget(self.empezar)
        lateral.addWidget(boton("Cancelar", None, ventana.cancelar_sesion))

        cuerpo = QHBoxLayout()
        cuerpo.setSpacing(16)
        cuerpo.addWidget(self.camara, 3)
        cuerpo.addLayout(lateral, 1)

        capa = QVBoxLayout(self)
        capa.setContentsMargins(28, 24, 28, 24)
        capa.setSpacing(14)
        capa.addWidget(etiqueta("Prepara tu sitio de estudio", "titulo"))
        capa.addWidget(etiqueta("Comprueba que la cámara te ve bien antes de empezar.", "subtitulo"))
        capa.addLayout(cuerpo, 1)

    def al_mostrar(self) -> None:
        self.preparacion = None
        self._ultimo_frame = None
        a_la_vista = self.ventana.perfil.movil_a_la_vista
        self.camara.permitir_marcar = a_la_vista
        self.camara.set_sitio(None)
        self.camara.set_mensaje("Abriendo la cámara y cargando los modelos…")
        self.empezar.setEnabled(False)
        self.cuenta.setText("…")
        if a_la_vista:
            self.instrucciones.setText(
                "1. Siéntate como vas a estudiar.\n"
                "2. Deja el móvil sobre la mesa, donde se vea en la imagen.\n"
                "3. Arrastra con el ratón un recuadro ajustado alrededor del móvil.\n"
                "4. Pulsa «Empezar ya» o espera a que acabe la cuenta atrás.")
        else:
            self.instrucciones.setText(
                "Siéntate como vas a estudiar y comprueba que se te ve la cara. "
                "Pulsa «Empezar ya» o espera a que acabe la cuenta atrás.")
        self.estado_movil.setText("")
        self.setFocus()

    def con_instantanea(self, inst) -> None:
        """La ventana le pasa el último análisis de la cámara (unas 20 veces por segundo)."""
        if inst is None:
            return
        ahora = time.monotonic()
        if self.preparacion is None:  # la cuenta empieza cuando la cámara ya funciona
            self.preparacion = Preparacion(inicio=ahora)
            self.empezar.setEnabled(True)
            self.empezar.setFocus()
        self._ultimo_frame = inst.frame
        self.camara.set_frame(inst.frame)
        self.cuenta.setText(str(int(self.preparacion.restante(ahora) + 0.99)))

        if self.ventana.perfil.movil_a_la_vista:
            recuadro = self.ventana.motor.recuadro_aparcado if self.ventana.motor else None
            if inst.sitio_movil in (SitioMovil.EN_SU_SITIO, SitioMovil.FUERA) and recuadro:
                self.camara.set_sitio(recuadro, estilo.ACENTO, "tu móvil")
                self.estado_movil.setText("✓ Móvil marcado. Si no es correcto, vuelve a marcarlo.")
            else:
                self.estado_movil.setText("Todavía no has marcado el móvil.")
        if not inst.observacion.hay_cara:
            self.camara.set_borde(estilo.DUDOSO)
        else:
            self.camara.set_borde(None)

        if self.preparacion.debe_empezar(ahora):
            self._empezar()

    def _marcar(self, recuadro) -> None:
        if self.preparacion is None or self._ultimo_frame is None:
            return
        if self.preparacion.marcar_movil(*recuadro):
            self.ventana.motor.marcar_movil(self._ultimo_frame, self.preparacion.movil_marcado)

    def _empezar(self) -> None:
        if self.preparacion is None or self.preparacion.empezada:
            return
        self.preparacion.empezar()
        self.ventana.empezar_sesion()

    def keyPressEvent(self, evento):
        if evento.key() in (Qt.Key_Return, Qt.Key_Enter) and self.empezar.isEnabled():
            self._empezar()
        else:
            super().keyPressEvent(evento)
