"""Máquina de estados de la detección.

Recibe en cada fotograma la situación observada (un estado "candidato") y solo
cambia de estado cuando esa situación se mantiene durante MARGEN_CAMBIO_S
segundos. Las interrupciones más cortas que TOLERANCIA_FALLOS_S se consideran
fallos de detección y no reinician la cuenta.

DUDOSO es especial, porque implica preguntar al usuario y eso distrae:
- solo se entra si la duda dura MARGEN_DUDOSO_S segundos (más que los demás);
- cuando el usuario responde (confirmar), se pasa a ESTUDIANDO o AUSENTE y esa
  respuesta vale mientras siga la misma duda;
- tras responder, durante PAUSA_ENTRE_PREGUNTAS_S no se vuelve a preguntar:
  una duda nueva no cambia el estado (se sigue como se estaba).

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
        margen_dudoso_s: float = config.MARGEN_DUDOSO_S,
        pausa_preguntas_s: float = config.PAUSA_ENTRE_PREGUNTAS_S,
    ):
        self.margen_s = margen_s
        self.tolerancia_s = tolerancia_s
        self.margen_dudoso_s = margen_dudoso_s
        self.pausa_preguntas_s = pausa_preguntas_s
        self.estado = estado_inicial
        self._pendiente: Estado | None = None  # estado al que se podría cambiar
        self._desde = 0.0  # desde cuándo se observa el pendiente
        self._visto = 0.0  # última vez que se observó el pendiente

        # Respuesta a la duda actual: mientras la situación siga siendo dudosa,
        # se usa este estado en lugar de DUDOSO.
        self._confirmado: Estado | None = None
        self._sin_duda_desde: float | None = None
        # Cuándo respondió por última vez (para no preguntar otra vez enseguida).
        self._respondido_en = -1e9

        # Datos de la última entrada en DUDOSO, para corregir el temporizador:
        # cuánto tiempo de duda pasó antes de preguntar y en qué estado estaba.
        self.duda_previa_s = 0.0
        self.estado_antes_de_duda: Estado | None = None

    def confirmar(self, estado: Estado, ahora: float) -> None:
        """El usuario ha resuelto la duda: pasa ya a `estado` (ESTUDIANDO o AUSENTE)."""
        self.estado = estado
        self._confirmado = estado
        self._respondido_en = ahora
        self._sin_duda_desde = None
        self._pendiente = None

    def _resolver_duda(self, candidato: Estado, ahora: float, insistir: bool = False) -> Estado:
        """Sustituye DUDOSO por la respuesta del usuario cuando todavía vale."""
        if self._confirmado is not None:
            if candidato == Estado.DUDOSO:
                self._sin_duda_desde = None
                return self._confirmado
            # La respuesta deja de valer cuando la situación cambia de verdad.
            if self._sin_duda_desde is None:
                self._sin_duda_desde = ahora
            elif ahora - self._sin_duda_desde >= self.margen_s:
                self._confirmado = None
        if (
            candidato == Estado.DUDOSO
            and ahora - self._respondido_en < self.pausa_preguntas_s
            and self.estado != Estado.DUDOSO
            and not insistir
        ):
            # Se preguntó hace poco: no se insiste y la duda no cambia nada.
            # (No se usa la última respuesta: si fue "no", pausaría sin preguntar.)
            return self.estado
        return candidato

    def actualizar(
        self,
        candidato: Estado,
        ahora: float,
        margen_dudoso_s: float | None = None,
        insistir: bool = False,
    ) -> bool:
        """Registra la situación del fotograma actual.

        `margen_dudoso_s` sustituye a MARGEN_DUDOSO_S para esta duda e `insistir`
        pregunta aunque se haya preguntado hace poco (se usan cuando el móvil
        aparcado ha desaparecido de su sitio). Devuelve True si el estado ha cambiado.
        """
        candidato = self._resolver_duda(candidato, ahora, insistir)

        if self._pendiente is not None and candidato == self._pendiente:
            self._visto = ahora
        elif self._pendiente is not None and ahora - self._visto <= self.tolerancia_s:
            pass  # interrupción breve: se tolera
        else:
            # Empieza una situación nueva (o se vuelve a la del estado actual).
            self._pendiente = None if candidato == self.estado else candidato
            self._desde = self._visto = ahora

        if self._pendiente == Estado.DUDOSO:
            margen = self.margen_dudoso_s if margen_dudoso_s is None else margen_dudoso_s
        else:
            margen = self.margen_s
        if self._pendiente is not None and ahora - self._desde >= margen:
            if self._pendiente == Estado.DUDOSO:
                self.duda_previa_s = ahora - self._desde
                self.estado_antes_de_duda = self.estado
            self.estado = self._pendiente
            self._pendiente = None
            self._confirmado = None  # cambio por lo que se ve: la respuesta ya no vale
            return True
        return False

    @property
    def progreso_cambio(self) -> tuple[Estado | None, float]:
        """Estado al que se podría cambiar y segundos que lleva observándose."""
        if self._pendiente is None:
            return None, 0.0
        return self._pendiente, self._visto - self._desde
