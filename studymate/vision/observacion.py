"""Qué se ha visto en un fotograma y qué estado sugiere.

Es lógica pura, sin MediaPipe ni cámara.
Los recuadros son tuplas (x1, y1, x2, y2) en píxeles.
"""

from dataclasses import dataclass, field
from enum import Enum

from . import config
from .estados import Estado

Recuadro = tuple[float, float, float, float]


class SitioMovil(str, Enum):
    SIN_USAR = "sin usar"            # el estudiante lo tiene guardado: no se vigila
    BUSCANDO = "buscando"            # localizándolo al empezar
    NO_ENCONTRADO = "no encontrado"  # no se ha visto: se vigila solo la mano
    EN_SU_SITIO = "en su sitio"
    FUERA = "fuera"                  # no está donde se dejó


@dataclass
class Dispositivo:
    clase: str
    puntuacion: float
    recuadro: Recuadro
    cerca_de_mano: bool = False
    # Motivo por el que una detección junto a la mano no cuenta como móvil
    # ("" si cuenta): "pequeño" o "pinza" (reglas) o "clip".
    descartado: str = ""
    # Para comparar las variantes en prueba_detectores:
    toca_mano: bool = False       # toca el recuadro ampliado de una mano
    descarte_reglas: str = ""     # lo que dirían las reglas aunque no se usen
    prob_clip: float | None = None  # probabilidad de móvil según CLIP (None si no se usa)


@dataclass
class Observacion:
    caras: list[Recuadro] = field(default_factory=list)
    confianza_caras: list[float] = field(default_factory=list)  # una por cara
    manos: list[Recuadro] = field(default_factory=list)
    # Postura de cada mano (mismo orden que `manos`), relativa al tamaño de la palma:
    # pinza = distancia entre las puntas del pulgar y el índice;
    # apertura = distancia entre las puntas del índice y el meñique.
    pinza_manos: list[float] = field(default_factory=list)
    apertura_manos: list[float] = field(default_factory=list)
    dispositivos: list[Dispositivo] = field(default_factory=list)
    # Dónde está el móvil que se dejó a la vista al empezar (ver aparcado.py).
    sitio_movil: SitioMovil = SitioMovil.SIN_USAR

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


def area(r: Recuadro) -> float:
    return max(0.0, r[2] - r[0]) * max(0.0, r[3] - r[1])


def _interseccion(a: Recuadro, b: Recuadro) -> float:
    return area((max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])))


def _mano_del_movil(movil: Recuadro, manos: list[Recuadro]) -> int:
    """Índice de la mano que más solapa con el móvil (o la más cercana, si ninguna)."""
    def clave(i: int):
        m = manos[i]
        distancia = abs((m[0] + m[2]) - (movil[0] + movil[2])) + abs((m[1] + m[3]) - (movil[1] + movil[3]))
        return (_interseccion(movil, m), -distancia)
    return max(range(len(manos)), key=clave)


def descartar_junto_a_mano(movil: Recuadro, obs: Observacion) -> str:
    """Motivo para no contar como móvil una detección junto a la mano ("" si cuenta).

    Medido con YOLO26s en las pruebas de Pablo:
    - "pequeño": un dedo, el hueco de la mano o el boli dan recuadros de un
      11-37 % de la mano; un móvil real mide como la mano o más.
    - "pinza": un boli se coge con las puntas del pulgar y el índice juntas;
      un móvil, con la mano rodeando algo ancho.
    Con las dos reglas, el boli pasaba del 8 % al 0 % del tiempo en USANDO_MOVIL
    y el móvil real, del 61 % al 49 %.
    """
    i = _mano_del_movil(movil, obs.manos)
    a_mano = area(obs.manos[i])
    if a_mano and area(movil) / a_mano < config.MIN_TAMANO_RESPECTO_MANO:
        return "pequeño"
    if i < len(obs.pinza_manos) and obs.pinza_manos[i] < config.MIN_PINZA:
        return "pinza"
    return ""


def marcar_cercania(
    obs: Observacion,
    margen: float = config.MARGEN_MANO,
    modo: str = config.MODO_VERIFICACION,
) -> None:
    """Marca los dispositivos que están en la mano.

    Tiene que tocar el recuadro ampliado de alguna mano y pasar la verificación
    del `modo` (ver MODO_VERIFICACION en config.py). Si el modo usa CLIP pero
    CLIP no ha dado resultado, no se descarta por CLIP.
    """
    manos = [ampliar(mano, margen) for mano in obs.manos]
    usa_reglas = modo in ("reglas", "reglas+clip")
    usa_clip = modo in ("clip", "reglas+clip")
    for d in obs.dispositivos:
        d.toca_mano = any(se_tocan(mano, d.recuadro) for mano in manos)
        d.descarte_reglas = descartar_junto_a_mano(d.recuadro, obs) if d.toca_mano else ""
        d.descartado = ""
        if d.toca_mano:
            if usa_reglas and d.descarte_reglas:
                d.descartado = d.descarte_reglas
            elif usa_clip and d.prob_clip is not None and d.prob_clip < config.UMBRAL_CLIP:
                d.descartado = "clip"
        d.cerca_de_mano = d.toca_mano and not d.descartado


def clasificar(
    obs: Observacion,
    clases_permitidas: frozenset[str] = frozenset(),
) -> Estado:
    """Devuelve el estado que sugiere este fotograma."""
    # Móvil aparcado y en su sitio: lo que parezca un móvil en la mano es otra
    # cosa (típex, boli, cartera...). Solo cuenta si hay alguien delante.
    if obs.sitio_movil == SitioMovil.EN_SU_SITIO:
        return Estado.ESTUDIANDO if obs.hay_cara else (Estado.DUDOSO if obs.manos else Estado.AUSENTE)
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

    # El móvil no está donde se dejó: lo está usando, aunque no se vea en la mano
    # (en la mano YOLO solo lo reconoce a ratos; el sitio vacío se ve siempre).
    # Si de verdad lo ha guardado, lo dice con el botón «He guardado el móvil».
    if obs.sitio_movil == SitioMovil.FUERA and (obs.hay_cara or obs.manos):
        return Estado.USANDO_MOVIL

    if obs.hay_cara:
        return Estado.ESTUDIANDO
    if obs.manos:
        # Puede estar mirando los apuntes con la cabeza fuera del encuadre.
        return Estado.DUDOSO
    return Estado.AUSENTE