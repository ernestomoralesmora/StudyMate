"""Preparación antes de empezar la sesión (idea de la profesora).

La cámara enseña el sitio de estudio y el estudiante marca con el ratón dónde
deja el móvil. Por defecto no hay cuenta atrás (PREPARACION_S = None): la sesión
empieza cuando pulsa «Empezar». Con una duración, empieza sola al acabar. Si no
ha marcado el móvil, se vigila solo la mano.

Mientras dura la preparación, el temporizador no cuenta.
Lógica pura: la ventana (OpenCV ahora, PySide6 después) solo la consulta.
"""

from dataclasses import dataclass

from . import config
from .observacion import Recuadro

LADO_MINIMO = 12  # px: un recuadro más pequeño se toma como un clic sin querer


@dataclass
class Preparacion:
    inicio: float
    duracion_s: float | None = config.PREPARACION_S  # None: sin cuenta atrás
    movil_marcado: Recuadro | None = None
    empezada: bool = False

    def restante(self, ahora: float) -> float | None:
        if self.duracion_s is None:
            return None
        return max(0.0, self.duracion_s - (ahora - self.inicio))

    def marcar_movil(self, x1: float, y1: float, x2: float, y2: float) -> bool:
        """Guarda el recuadro arrastrado con el ratón (en cualquier dirección)."""
        r = (min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))
        if r[2] - r[0] < LADO_MINIMO or r[3] - r[1] < LADO_MINIMO:
            return False
        self.movil_marcado = r
        return True

    def debe_empezar(self, ahora: float) -> bool:
        """Se acabó el tiempo: empieza la sesión aunque no haya marcado nada."""
        restante = self.restante(ahora)
        return not self.empezada and restante is not None and restante <= 0

    def empezar(self) -> None:
        self.empezada = True

    def mensaje(self, ahora: float, movil_a_la_vista: bool) -> str:
        restante = self.restante(ahora)
        cuenta = "" if restante is None else f" (empieza sola en {int(restante + 0.99)} s)"
        if not movil_a_la_vista:
            return f"Preparate. Enter = empezar{cuenta}"
        if self.movil_marcado is None:
            return f"Deja el movil en la mesa y rodealo con el raton, ajustado{cuenta}"
        return f"Movil marcado. Enter = empezar{cuenta}"
