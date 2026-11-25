"""Temporizador de estudio.

Solo suma tiempo mientras el estado es ESTUDIANDO. El tiempo pasado en DUDOSO
no se pierde ni se cuenta directamente: queda "pendiente" hasta que el usuario
confirme si estaba estudiando (o hasta que la detección salga de la duda).
"""

from .estados import Estado


class Temporizador:
    def __init__(self):
        self.estudiado_s = 0.0
        self.pendiente_s = 0.0
        self._ultimo: float | None = None
        self._estado_anterior: Estado | None = None
        # Respuesta del usuario para el episodio DUDOSO actual (None = sin respuesta).
        self._respuesta_dudoso: bool | None = None

    def actualizar(self, estado: Estado, ahora: float) -> None:
        if self._ultimo is None:
            self._ultimo = ahora
        dt = max(0.0, ahora - self._ultimo)
        self._ultimo = ahora

        # Al terminar un episodio DUDOSO sin respuesta: si se vuelve a
        # ESTUDIANDO, la duda se resuelve a favor; si no, se descarta.
        if self._estado_anterior == Estado.DUDOSO and estado != Estado.DUDOSO:
            if self._respuesta_dudoso is None and estado == Estado.ESTUDIANDO:
                self.estudiado_s += self.pendiente_s
            self.pendiente_s = 0.0
            self._respuesta_dudoso = None
        self._estado_anterior = estado

        if estado == Estado.ESTUDIANDO:
            self.estudiado_s += dt
        elif estado == Estado.DUDOSO:
            if self._respuesta_dudoso is True:
                self.estudiado_s += dt
            elif self._respuesta_dudoso is None:
                self.pendiente_s += dt
            # Si el usuario dijo que no estaba estudiando, no se cuenta nada.

    def confirmar_dudoso(self, estaba_estudiando: bool, descontar_s: float = 0.0) -> None:
        """Respuesta del usuario a "¿Sigues estudiando?" durante un episodio DUDOSO.

        `descontar_s`: tiempo de duda que ya se había contado como estudio antes
        de preguntar (la máquina espera MARGEN_DUDOSO_S); si la respuesta es que
        no, se resta.
        """
        if estaba_estudiando:
            self.estudiado_s += self.pendiente_s
        else:
            self.estudiado_s = max(0.0, self.estudiado_s - descontar_s)
        self.pendiente_s = 0.0
        self._respuesta_dudoso = estaba_estudiando

    @property
    def esperando_confirmacion(self) -> bool:
        return self._estado_anterior == Estado.DUDOSO and self._respuesta_dudoso is None

    @staticmethod
    def formatear(segundos: float) -> str:
        s = int(segundos)
        return f"{s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}"
