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
from .observacion import Observacion, clasificar
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


class MotorDeteccion(threading.Thread):
    def __init__(
        self,
        clases_permitidas: frozenset[str] = frozenset(),
        indice_camara: int = 0,
        modelo_movil: str = config.MODELO_OBJETOS,
    ):
        super().__init__(daemon=True, name="deteccion")
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

    def run(self) -> None:
        try:
            with Camara(self.indice_camara) as camara:
                analizador = Analizador(self.modelo_movil)
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
                self.maquina.actualizar(candidato, ahora)
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
                )
            self._listo.set()

    def esperar_listo(self, timeout: float | None = None) -> bool:
        """Espera al primer fotograma analizado (o a un error)."""
        return self._listo.wait(timeout)

    def ultima(self) -> Instantanea | None:
        with self._cerrojo:
            return self._ultima

    def confirmar_dudoso(self, estaba_estudiando: bool) -> None:
        with self._cerrojo:
            self.temporizador.confirmar_dudoso(estaba_estudiando)

    def detener(self) -> None:
        self._parar.set()
