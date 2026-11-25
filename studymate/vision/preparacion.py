"""Preparación antes de empezar la sesión (idea de la profesora).

Durante PREPARACION_S segundos la cámara enseña el sitio de estudio y el
estudiante marca con el ratón dónde deja el móvil. Puede empezar antes si ya
lo tiene todo listo. Al acabar el tiempo, la sesión empieza sola; si no ha
marcado el móvil, se vigila solo la mano.

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
    duracion_s: float = config.PREPARACION_S
    movil_marcado: Recuadro | None = None
    empezada: bool = False

    def restante(self, ahora: float) -> float:
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
        return not self.empezada and self.restante(ahora) <= 0

    def empezar(self) -> None:
        self.empezada = True

    def mensaje(self, ahora: float, movil_a_la_vista: bool) -> str:
        segundos = int(self.restante(ahora) + 0.99)
        if not movil_a_la_vista:
            return f"Preparate. Empieza en {segundos} s (Enter = empezar ya)"
        if self.movil_marcado is None:
            return f"Deja el movil en la mesa y marcalo con el raton ({segundos} s)"
        return f"Movil marcado. Enter = empezar ya (empieza sola en {segundos} s)"
