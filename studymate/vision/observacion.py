"""Qué se ha visto en un fotograma y qué estado sugiere.

Es lógica pura (sin MediaPipe ni cámara) para poder probarla con datos inventados.
Los recuadros son tuplas (x1, y1, x2, y2) en píxeles.
"""

from dataclasses import dataclass, field

from . import config
from .estados import Estado

Recuadro = tuple[float, float, float, float]


@dataclass
class Dispositivo:
    clase: str
    puntuacion: float
    recuadro: Recuadro
    cerca_de_mano: bool = False


@dataclass
class Observacion:
    caras: list[Recuadro] = field(default_factory=list)
    manos: list[Recuadro] = field(default_factory=list)
    dispositivos: list[Dispositivo] = field(default_factory=list)

    @property
    def hay_cara(self) -> bool:
        return bool(self.caras)


def ampliar(r: Recuadro, fraccion: float) -> Recuadro:
    x1, y1, x2, y2 = r
    dx, dy = (x2 - x1) * fraccion, (y2 - y1) * fraccion
    return (x1 - dx, y1 - dy, x2 + dx, y2 + dy)


def se_tocan(a: Recuadro, b: Recuadro) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def marcar_cercania(obs: Observacion, margen: float = config.MARGEN_MANO) -> None:
    """Marca los dispositivos cuyo recuadro toca el de alguna mano (ampliado)."""
    manos = [ampliar(m, margen) for m in obs.manos]
    for d in obs.dispositivos:
        d.cerca_de_mano = any(se_tocan(m, d.recuadro) for m in manos)


def clasificar(obs: Observacion, clases_permitidas: frozenset[str] = frozenset()) -> Estado:
    """Estado que sugiere este fotograma por sí solo (el "candidato")."""
    en_mano = [
        d for d in obs.dispositivos
        if d.cerca_de_mano and d.clase not in clases_permitidas
    ]
    mejor = max((d.puntuacion for d in en_mano), default=0.0)

    if mejor >= config.UMBRAL_MOVIL:
        return Estado.USANDO_MOVIL
    if mejor >= config.UMBRAL_MOVIL_DUDOSO:
        return Estado.DUDOSO
    if obs.hay_cara:
        return Estado.ESTUDIANDO
    if obs.manos:
        # Hay alguien (se ven las manos) pero no la cara: puede estar mirando
        # los apuntes muy agachado. Mejor preguntar que pausar sin más.
        return Estado.DUDOSO
    return Estado.AUSENTE
