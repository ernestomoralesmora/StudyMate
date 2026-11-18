"""Qué se ha visto en un fotograma y qué estado sugiere.

Es lógica pura, sin MediaPipe ni cámara.
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
    dx = (x2 - x1) * fraccion
    dy = (y2 - y1) * fraccion
    return x1 - dx, y1 - dy, x2 + dx, y2 + dy


def se_tocan(a: Recuadro, b: Recuadro) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def marcar_cercania(obs: Observacion, margen: float = config.MARGEN_MANO) -> None:
    """Marca los dispositivos que tocan el recuadro ampliado de alguna mano."""
    manos = [ampliar(mano, margen) for mano in obs.manos]
    for dispositivo in obs.dispositivos:
        dispositivo.cerca_de_mano = any(
            se_tocan(mano, dispositivo.recuadro) for mano in manos
        )


def clasificar(
    obs: Observacion,
    clases_permitidas: frozenset[str] = frozenset(),
) -> Estado:
    """Devuelve el estado que sugiere este fotograma."""
    en_mano = [
        dispositivo
        for dispositivo in obs.dispositivos
        if dispositivo.cerca_de_mano
        and dispositivo.clase not in clases_permitidas
    ]
    mejor = max((dispositivo.puntuacion for dispositivo in en_mano), default=0.0)

    if mejor >= config.UMBRAL_MOVIL:
        return Estado.USANDO_MOVIL
    if mejor >= config.UMBRAL_MOVIL_DUDOSO:
        return Estado.DUDOSO

    # Si no vemos las manos, un móvil junto a la oreja es un caso dudoso.
    if not obs.manos:
        for dispositivo in obs.dispositivos:
            if dispositivo.clase in clases_permitidas:
                continue
            if dispositivo.puntuacion < config.UMBRAL_MOVIL_DUDOSO:
                continue

            mx1, my1, mx2, my2 = dispositivo.recuadro
            cx = (mx1 + mx2) / 2
            cy = (my1 + my2) / 2

            for x1, y1, x2, y2 in obs.caras:
                ancho = x2 - x1
                alto = y2 - y1

                lado_izquierdo = x1 - 0.40 * ancho <= cx <= x1 + 0.25 * ancho
                lado_derecho = x2 - 0.25 * ancho <= cx <= x2 + 0.40 * ancho
                altura_oreja = y1 + 0.15 * alto <= cy <= y1 + 0.85 * alto

                if altura_oreja and (lado_izquierdo or lado_derecho):
                    return Estado.DUDOSO

    if obs.hay_cara:
        return Estado.ESTUDIANDO
    if obs.manos:
        # Puede estar mirando los apuntes con la cabeza fuera del encuadre.
        return Estado.DUDOSO
    return Estado.AUSENTE