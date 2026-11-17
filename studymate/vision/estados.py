"""Máquina de estados de la detección.

Recibe en cada fotograma la situación observada (un estado "candidato") y solo
cambia de estado cuando esa situación se mantiene durante MARGEN_CAMBIO_S
segundos. Las interrupciones más cortas que TOLERANCIA_FALLOS_S se consideran
fallos de detección y no reinician la cuenta.

No depende de la cámara: se puede probar con tiempos simulados.
"""

from enum import Enum

from . import config


class Estado(Enum):
    ESTUDIANDO = "ESTUDIANDO"
    AUSENTE = "AUSENTE"
    USANDO_MOVIL = "USANDO_MOVIL"
    DUDOSO = "DUDOSO"


class MaquinaEstados:
    def __init__(
        self,
        margen_s: float = config.MARGEN_CAMBIO_S,
        tolerancia_s: float = config.TOLERANCIA_FALLOS_S,
        estado_inicial: Estado = Estado.AUSENTE,
    ):
        self.margen_s = margen_s
        self.tolerancia_s = tolerancia_s
        self.estado = estado_inicial
        self._pendiente: Estado | None = None  # estado al que se podría cambiar
        self._desde = 0.0  # desde cuándo se observa el pendiente
        self._visto = 0.0  # última vez que se observó el pendiente

    def actualizar(self, candidato: Estado, ahora: float) -> bool:
        """Registra la situación del fotograma actual.

        Devuelve True si el estado ha cambiado en esta llamada.
        """
        if self._pendiente is not None and candidato == self._pendiente:
            self._visto = ahora
        elif self._pendiente is not None and ahora - self._visto <= self.tolerancia_s:
            pass  # interrupción breve: se tolera
        else:
            # Empieza una situación nueva (o se vuelve a la del estado actual).
            self._pendiente = None if candidato == self.estado else candidato
            self._desde = self._visto = ahora

        if self._pendiente is not None and ahora - self._desde >= self.margen_s:
            self.estado = self._pendiente
            self._pendiente = None
            return True
        return False

    @property
    def progreso_cambio(self) -> tuple[Estado | None, float]:
        """Estado al que se podría cambiar y segundos que lleva observándose."""
        if self._pendiente is None:
            return None, 0.0
        return self._pendiente, self._visto - self._desde
