"""Móvil aparcado: vigilar que el móvil sigue en su sitio (idea de la profesora).

Reconocer el móvil en la mano es difícil: la mano tapa la mitad y lo que queda se
parece a un típex o a un boli. Reconocerlo sobre la mesa, entero, es mucho más
fácil. Así que:

1. Al empezar, el estudiante deja el móvil donde la cámara lo vea y se localiza
   (varias imágenes seguidas, para no quedarse con una detección suelta).
2. Durante la sesión, cada PERIODO_APARCADO_S se mira solo ese sitio:
   - con YOLO en un recorte alrededor del sitio, y
   - comparando el trozo de imagen con el que se guardó al empezar.
   Si cualquiera de las dos dice que sigue ahí, está en su sitio.
3. Si falta varias comprobaciones seguidas, el móvil está "fuera": si además se
   ve en la mano, USANDO_MOVIL; si no, se pregunta ("¿Has cogido el móvil?").

Es lógica sin hilos ni cámara: `detectar` es una función que recibe un recorte
RGB cuadrado y devuelve [(clase, puntuación, (x1, y1, x2, y2))] en coordenadas
del recorte (lo que hace el YOLO de detectores.py). Así se puede probar con
detecciones simuladas.
"""

from dataclasses import dataclass, field

import cv2
import numpy as np

from . import config
from .observacion import Recuadro, SitioMovil, ampliar, area


def cuadros_imagen_completa(ancho: int, alto: int, lado: int | None = None) -> list[tuple[int, int, int, int]]:
    """Cuadrados que cubren toda la imagen, solapados (YOLO trabaja con entradas cuadradas).

    Con lado=320 y 640x480 salen 6 cuadros a tamaño real: así el móvil sobre la
    mesa, que se ve pequeño y en un borde, no se encoge al pasarlo a YOLO.
    """
    lado = min(lado or config.LADO_BUSQUEDA_APARCADO, ancho, alto)

    def posiciones(total: int) -> list[int]:
        if total <= lado:
            return [0]
        n = -(-(total - lado) // (lado // 2)) + 1  # paso de medio cuadro
        return sorted({round(i * (total - lado) / (n - 1)) for i in range(n)})

    return [(x, y, x + lado, y + lado) for y in posiciones(alto) for x in posiciones(ancho)]


def iou(a: Recuadro, b: Recuadro) -> float:
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    inter = area((x1, y1, x2, y2))
    union = area(a) + area(b) - inter
    return inter / union if union > 0 else 0.0


def similitud(gris: np.ndarray, plantilla: np.ndarray, recuadro: Recuadro) -> float:
    """Parecido (-1 a 1) entre la plantilla y la zona del recuadro, permitiendo
    que el móvil se haya movido un poco (se busca en la zona ampliada)."""
    alto, ancho = gris.shape[:2]
    x1, y1, x2, y2 = (int(round(v)) for v in ampliar(recuadro, config.HOLGURA_APARCADO))
    x1, y1, x2, y2 = max(0, x1), max(0, y1), min(ancho, x2), min(alto, y2)
    zona = gris[y1:y2, x1:x2]
    ph, pw = plantilla.shape[:2]
    if zona.shape[0] < ph or zona.shape[1] < pw:
        return -1.0
    valor = float(cv2.matchTemplate(zona, plantilla, cv2.TM_CCOEFF_NORMED).max())
    return valor if np.isfinite(valor) else -1.0


def _recorte_cuadrado(recuadro: Recuadro, ancho: int, alto: int, margen: float) -> tuple[int, int, int, int]:
    x1, y1, x2, y2 = recuadro
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    lado = int(min(max(max(x2 - x1, y2 - y1) * (1 + 2 * margen), config.LADO_MIN_RECORTE), ancho, alto))
    rx = int(min(max(cx - lado / 2, 0), ancho - lado))
    ry = int(min(max(cy - lado / 2, 0), alto - lado))
    return rx, ry, rx + lado, ry + lado


@dataclass
class VigilanteMovil:
    detectar: object  # función recorte_rgb -> [(clase, puntuación, recuadro)]
    activo: bool = True  # False si el estudiante tiene el móvil guardado

    estado: SitioMovil = SitioMovil.SIN_USAR
    recuadro: Recuadro | None = None
    plantilla: np.ndarray | None = None
    zona_plantilla: Recuadro | None = None
    _vistos: list[Recuadro] = field(default_factory=list)
    _intentos: int = 0
    _fallos_seguidos: int = 0
    ultima_similitud: float = 0.0
    ultima_yolo: float = 0.0
    # Lo mejor que se ha visto buscando (para enseñarlo en pantalla y ayudar a colocarlo).
    mejor_busqueda: tuple[float, Recuadro] | None = None

    def __post_init__(self):
        self.estado = SitioMovil.BUSCANDO if self.activo else SitioMovil.SIN_USAR

    # --- 1. Localizarlo al empezar ------------------------------------------------
    def buscar(self, frame_rgb: np.ndarray) -> None:
        """Analiza una imagen completa mientras se busca el móvil."""
        if self.estado != SitioMovil.BUSCANDO:
            return
        alto, ancho = frame_rgb.shape[:2]
        mejor, puntuacion = None, 0.0
        for cx1, cy1, cx2, cy2 in cuadros_imagen_completa(ancho, alto):
            recorte = np.ascontiguousarray(frame_rgb[cy1:cy2, cx1:cx2])
            for clase, p, (x1, y1, x2, y2) in self.detectar(recorte):
                if clase in config.CLASES_DISPOSITIVO and p > puntuacion:
                    mejor, puntuacion = (x1 + cx1, y1 + cy1, x2 + cx1, y2 + cy1), p
        if mejor is not None:
            self.mejor_busqueda = (puntuacion, mejor)
        if puntuacion < config.UMBRAL_APARCADO:
            mejor = None
        self._intentos += 1
        if mejor is not None:
            self._vistos.append(mejor)
        self._decidir_busqueda(frame_rgb)

    def _decidir_busqueda(self, frame_rgb: np.ndarray) -> None:
        if len(self._vistos) >= config.VECES_PARA_APARCAR:
            # Se queda con el recuadro que más coincide con los demás (no uno suelto).
            centro = max(self._vistos, key=lambda r: sum(iou(r, o) > 0.5 for o in self._vistos))
            iguales = [r for r in self._vistos if iou(r, centro) > 0.5]
            if len(iguales) >= config.VECES_PARA_APARCAR:
                self.recuadro = tuple(float(np.median([r[i] for r in iguales])) for i in range(4))
                # La plantilla incluye un poco de mesa alrededor: así tiene bordes
                # aunque el móvil sea de un color liso (p. ej., boca abajo y negro).
                self._guardar_plantilla(frame_rgb)
                self.estado = SitioMovil.EN_SU_SITIO
                return
        if self._intentos >= config.INTENTOS_BUSCAR_APARCADO:
            self.estado = SitioMovil.NO_ENCONTRADO

    def _guardar_plantilla(self, frame_rgb: np.ndarray) -> None:
        gris = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2GRAY)
        alto, ancho = gris.shape
        x1, y1, x2, y2 = (int(round(v)) for v in ampliar(self.recuadro, 0.15))
        x1, y1, x2, y2 = max(0, x1), max(0, y1), min(ancho, x2), min(alto, y2)
        self.zona_plantilla = (x1, y1, x2, y2)
        self.plantilla = gris[y1:y2, x1:x2].copy()

    def marcar_a_mano(self, frame_rgb: np.ndarray, recuadro: Recuadro) -> None:
        """Si YOLO no lo encuentra, el estudiante señala dónde está el móvil.
        Entonces se vigila sobre todo comparando con la imagen guardada."""
        self.recuadro = tuple(float(v) for v in recuadro)
        self._guardar_plantilla(frame_rgb)
        self._fallos_seguidos = 0
        self.estado = SitioMovil.EN_SU_SITIO

    def buscar_de_nuevo(self) -> None:
        self._vistos, self._intentos, self._fallos_seguidos = [], 0, 0
        self.recuadro = self.plantilla = self.zona_plantilla = self.mejor_busqueda = None
        self.estado = SitioMovil.BUSCANDO

    # --- 2. Comprobar que sigue ahí ---------------------------------------------
    def comprobar(self, frame_rgb: np.ndarray) -> None:
        if self.estado not in (SitioMovil.EN_SU_SITIO, SitioMovil.FUERA):
            return
        alto, ancho = frame_rgb.shape[:2]
        x1, y1, x2, y2 = _recorte_cuadrado(self.recuadro, ancho, alto, config.MARGEN_RECORTE)
        recorte = np.ascontiguousarray(frame_rgb[y1:y2, x1:x2])
        self.ultima_yolo = max(
            (p for clase, p, (bx1, by1, bx2, by2) in self.detectar(recorte)
             if clase in config.CLASES_DISPOSITIVO
             and iou((bx1 + x1, by1 + y1, bx2 + x1, by2 + y1), self.recuadro) >= 0.3),
            default=0.0,
        )
        self.ultima_similitud = similitud(cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2GRAY), self.plantilla, self.zona_plantilla)
        presente = (self.ultima_yolo >= config.UMBRAL_MOVIL_DUDOSO
                    or self.ultima_similitud >= config.SIMILITUD_APARCADO)
        self.registrar(presente)

    def registrar(self, presente: bool) -> None:
        """Una comprobación: hace falta fallar varias seguidas para pasar a FUERA."""
        if presente:
            self._fallos_seguidos = 0
            self.estado = SitioMovil.EN_SU_SITIO
        else:
            self._fallos_seguidos += 1
            if self._fallos_seguidos >= config.FALLOS_PARA_FUERA:
                self.estado = SitioMovil.FUERA

    def desactivar(self) -> None:
        """El estudiante dice que sigue estudiando sin el móvil a la vista (lo ha
        guardado o lo ha movido): a partir de ahora solo se vigila la mano."""
        self.estado = SitioMovil.SIN_USAR

    @property
    def vigilando(self) -> bool:
        return self.estado in (SitioMovil.EN_SU_SITIO, SitioMovil.FUERA)
