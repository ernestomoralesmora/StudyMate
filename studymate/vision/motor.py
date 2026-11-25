"""Hilo de detección: cámara -> detectores -> máquina de estados -> temporizador.

Corre aparte de la interfaz. La interfaz (OpenCV ahora, PySide6 en la fase 3)
solo lee la última `Instantanea` con `ultima()` y nunca espera a la detección.
"""

import threading
import time
from dataclasses import dataclass

from . import config
from .camara import Camara
from .detectores import Analizador
from .estados import Estado, MaquinaEstados
from .observacion import Observacion, SitioMovil, clasificar
from .temporizador import Temporizador


@dataclass
class Instantanea:
    frame: object  # ndarray BGR
    observacion: Observacion
    candidato: Estado
    estado: Estado
    estudiado_s: float
    pendiente_s: float
    esperando_confirmacion: bool
    fps: float
    sitio_movil: SitioMovil = SitioMovil.SIN_USAR
    en_sesion: bool = True  # False durante la preparación (el tiempo no cuenta)


class MotorDeteccion(threading.Thread):
    def __init__(
        self,
        clases_permitidas: frozenset[str] = frozenset(),
        indice_camara: int = 0,
        modelo_movil: str = config.MODELO_OBJETOS,
        movil_a_la_vista: bool = False,
    ):
        """`movil_a_la_vista`: el estudiante deja el móvil donde la cámara lo vea
        (cuestionario). Al empezar se localiza y luego se vigila su sitio."""
        super().__init__(daemon=True, name="deteccion")
        self.movil_a_la_vista = movil_a_la_vista and "cell phone" not in clases_permitidas
        self.clases_permitidas = clases_permitidas
        self.indice_camara = indice_camara
        self.modelo_movil = modelo_movil
        self.maquina = MaquinaEstados()
        self.temporizador = Temporizador()
        self.error: Exception | None = None
        self._cerrojo = threading.Lock()
        self._parar = threading.Event()
        self._listo = threading.Event()
        self._ultima: Instantanea | None = None
        # Hasta que se llama a empezar_sesion() solo se mira (preparación):
        # ni la máquina de estados ni el temporizador avanzan.
        self.en_sesion = False

    def run(self) -> None:
        try:
            with Camara(self.indice_camara) as camara:
                analizador = Analizador(self.modelo_movil, movil_a_la_vista=self.movil_a_la_vista)
                self._analizador = analizador
                try:
                    self._bucle(camara, analizador)
                finally:
                    analizador.cerrar()
        except Exception as e:  # se informa al hilo principal
            self.error = e
        finally:
            self._listo.set()

    def _bucle(self, camara: Camara, analizador: Analizador) -> None:
        inicio = time.monotonic()
        fps = 0.0
        anterior = inicio
        while not self._parar.is_set():
            frame = camara.leer()
            if frame is None:
                time.sleep(0.01)
                continue
            ahora = time.monotonic()
            obs = analizador.analizar(frame, int((ahora - inicio) * 1000))
            candidato = clasificar(obs, self.clases_permitidas)

            with self._cerrojo:
                if self.en_sesion:
                    fuera = obs.sitio_movil == SitioMovil.FUERA
                    self.maquina.actualizar(
                        candidato, ahora,
                        margen_dudoso_s=config.MARGEN_MOVIL_FUERA_S if fuera else None,
                        insistir=fuera,
                    )
                    self.temporizador.actualizar(self.maquina.estado, ahora)
                dt = ahora - anterior
                anterior = ahora
                if dt > 0:  # media móvil para que el número no baile
                    fps = 1 / dt if fps == 0 else 0.9 * fps + 0.1 / dt
                self._ultima = Instantanea(
                    frame=frame,
                    observacion=obs,
                    candidato=candidato,
                    estado=self.maquina.estado,
                    estudiado_s=self.temporizador.estudiado_s,
                    pendiente_s=self.temporizador.pendiente_s,
                    esperando_confirmacion=self.temporizador.esperando_confirmacion,
                    fps=fps,
                    sitio_movil=obs.sitio_movil,
                    en_sesion=self.en_sesion,
                )
            self._listo.set()

    def esperar_listo(self, timeout: float | None = None) -> bool:
        """Espera al primer fotograma analizado (o a un error)."""
        return self._listo.wait(timeout)

    def ultima(self) -> Instantanea | None:
        with self._cerrojo:
            return self._ultima

    def confirmar_dudoso(self, estaba_estudiando: bool) -> None:
        """Respuesta a "¿Sigues estudiando?": S -> ESTUDIANDO, N -> AUSENTE."""
        with self._cerrojo:
            maquina = self.maquina
            if maquina.estado != Estado.DUDOSO:
                return  # no había ninguna pregunta en curso
            descuento = (
                maquina.duda_previa_s
                if maquina.estado_antes_de_duda == Estado.ESTUDIANDO
                else 0.0
            )
            self.temporizador.confirmar_dudoso(estaba_estudiando, descuento)
            # "Sí, sigo estudiando" con el móvil fuera de su sitio: lo ha guardado
            # o movido. Ya no se vigila el sitio (solo la mano) y no se insiste.
            analizador = getattr(self, "_analizador", None)
            if estaba_estudiando and analizador is not None:
                vigilante = analizador.dispositivos.vigilante
                if vigilante.estado == SitioMovil.FUERA:
                    vigilante.desactivar()
            maquina.confirmar(
                Estado.ESTUDIANDO if estaba_estudiando else Estado.AUSENTE,
                time.monotonic(),
            )

    def marcar_movil(self, frame_bgr, recuadro) -> None:
        """El estudiante ha marcado con el ratón dónde está el móvil."""
        import cv2
        if self.vigilante is not None:
            self.vigilante.marcar_a_mano(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB), recuadro)

    def empezar_sesion(self) -> None:
        """Acaba la preparación: desde aquí cuentan el estado y el tiempo."""
        with self._cerrojo:
            v = self.vigilante
            if v is not None and v.estado == SitioMovil.BUSCANDO:
                v.estado = SitioMovil.NO_ENCONTRADO  # no lo marcó: solo se vigila la mano
            self.en_sesion = True

    @property
    def vigilante(self):
        """El VigilanteMovil (ver aparcado.py), o None si aún no ha arrancado."""
        analizador = getattr(self, "_analizador", None)
        return analizador.dispositivos.vigilante if analizador else None

    @property
    def recuadro_aparcado(self):
        """Dónde se dejó el móvil (para dibujarlo), o None."""
        return self.vigilante.recuadro if self.vigilante else None

    def detener(self) -> None:
        self._parar.set()
