"""Verificador del móvil con CLIP (ViT-B/32, ONNX cuantizado).

YOLO dice "aquí hay algo que parece un móvil". CLIP mira ese trozo de imagen y
lo compara con frases ("una mano sujetando un móvil", "una mano sujetando un
boli"...). Si se parece más a las frases de objetos que no son un móvil, la
detección se descarta. No hay que entrenar nada (zero-shot).

- Solo se usa cuando YOLO ya ha encontrado un candidato, así que no gasta CPU
  el resto del tiempo. Va en el mismo hilo que YOLO, no baja los fps de la cámara.
- Los fotogramas se procesan en local; no se guardan ni se envían.
- Los modelos (~155 MB) se descargan de Hugging Face la primera vez.

Prueba aparte:  python -m studymate.vision.pruebas.prueba_clip
"""

import json
import re
from functools import lru_cache

import cv2
import numpy as np

from . import config
from .modelos import ruta_modelo

LADO = 224
MEDIA = np.array([0.48145466, 0.4578275, 0.40821073], dtype=np.float32)
DESVIACION = np.array([0.26862954, 0.26130258, 0.27577711], dtype=np.float32)
ESCALA_LOGITS = 100.0  # la "temperatura" con la que se entrenó CLIP


# --- Tokenizador BPE de CLIP (sin dependencias, solo para nuestras frases) -----
def _bytes_a_unicode() -> dict[int, str]:
    bs = list(range(ord("!"), ord("~") + 1)) + list(range(ord("¡"), ord("¬") + 1)) \
        + list(range(ord("®"), ord("ÿ") + 1))
    cs = bs[:]
    n = 0
    for b in range(256):
        if b not in bs:
            bs.append(b)
            cs.append(256 + n)
            n += 1
    return dict(zip(bs, map(chr, cs)))


class TokenizadorClip:
    PATRON = re.compile(
        r"<\|startoftext\|>|<\|endoftext\|>|'s|'t|'re|'ve|'m|'ll|'d|[^\W\d_]+|\d|[^\s\w]+|_+",
        re.IGNORECASE,
    )

    def __init__(self, ruta_vocab: str, ruta_merges: str):
        with open(ruta_vocab, encoding="utf-8") as f:
            self.codigos: dict[str, int] = json.load(f)
        with open(ruta_merges, encoding="utf-8") as f:
            lineas = [l for l in f.read().split("\n") if l and not l.startswith("#version")]
        self.rangos = {tuple(l.split()): i for i, l in enumerate(lineas)}
        self.byte_unicode = _bytes_a_unicode()
        self.inicio = self.codigos["<|startoftext|>"]
        self.fin = self.codigos["<|endoftext|>"]

    @lru_cache(maxsize=1024)
    def _bpe(self, palabra: str) -> tuple[str, ...]:
        partes = list(palabra[:-1]) + [palabra[-1] + "</w>"]
        while len(partes) > 1:
            pares = [(partes[i], partes[i + 1]) for i in range(len(partes) - 1)]
            mejor = min(pares, key=lambda p: self.rangos.get(p, float("inf")))
            if mejor not in self.rangos:
                break
            nuevas, i = [], 0
            while i < len(partes):
                if i < len(partes) - 1 and (partes[i], partes[i + 1]) == mejor:
                    nuevas.append(partes[i] + partes[i + 1])
                    i += 2
                else:
                    nuevas.append(partes[i])
                    i += 1
            partes = nuevas
        return tuple(partes)

    def codificar(self, texto: str) -> list[int]:
        texto = " ".join(texto.split()).strip().lower()
        ids = [self.inicio]
        for trozo in self.PATRON.findall(texto):
            palabra = "".join(self.byte_unicode[b] for b in trozo.encode("utf-8"))
            ids += [self.codigos[t] for t in self._bpe(palabra)]
        return ids + [self.fin]


# --- Utilidades ------------------------------------------------------------------
def _normalizar(v: np.ndarray) -> np.ndarray:
    return v / np.linalg.norm(v, axis=-1, keepdims=True)


def _salida(sesion, preferida: str) -> str:
    nombres = [o.name for o in sesion.get_outputs()]
    return preferida if preferida in nombres else nombres[0]


def recorte_cuadrado(frame_rgb: np.ndarray, recuadro, margen: float) -> np.ndarray:
    """Recorte cuadrado alrededor del recuadro, ampliado `margen` por cada lado."""
    alto, ancho = frame_rgb.shape[:2]
    x1, y1, x2, y2 = recuadro
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    lado = max(x2 - x1, y2 - y1) * (1 + 2 * margen)
    lado = int(min(max(lado, 32), ancho, alto))
    rx1 = int(min(max(cx - lado / 2, 0), ancho - lado))
    ry1 = int(min(max(cy - lado / 2, 0), alto - lado))
    return frame_rgb[ry1:ry1 + lado, rx1:rx1 + lado]


def preprocesar(recorte_rgb: np.ndarray) -> np.ndarray:
    x = cv2.resize(recorte_rgb, (LADO, LADO), interpolation=cv2.INTER_CUBIC)
    x = (x.astype(np.float32) / 255 - MEDIA) / DESVIACION
    return x.transpose(2, 0, 1)[None]


# --- Verificador -----------------------------------------------------------------
class VerificadorClip:
    def __init__(
        self,
        textos_movil=config.CLIP_TEXTOS_MOVIL,
        textos_otros=config.CLIP_TEXTOS_OTROS,
        hilos: int = config.HILOS_CLIP,
    ):
        import onnxruntime as ort

        opciones = ort.SessionOptions()
        opciones.intra_op_num_threads = hilos
        proveedores = ["CPUExecutionProvider"]
        self._vision = ort.InferenceSession(ruta_modelo("clip_vision"), opciones, providers=proveedores)
        self._entrada_vision = self._vision.get_inputs()[0].name
        self._salida_vision = _salida(self._vision, "image_embeds")

        self.tokenizador = TokenizadorClip(ruta_modelo("clip_vocab"), ruta_modelo("clip_merges"))
        texto = ort.InferenceSession(ruta_modelo("clip_texto"), opciones, providers=proveedores)

        self.textos = list(textos_movil) + list(textos_otros)
        self.n_movil = len(textos_movil)
        # Las frases no cambian: se calculan una vez al arrancar.
        self._embeds_texto = _normalizar(np.concatenate([self._embed_texto(texto, t) for t in self.textos]))

    def _embed_texto(self, sesion, frase: str) -> np.ndarray:
        ids = self.tokenizador.codificar(frase)
        entradas = {e.name: e for e in sesion.get_inputs()}
        largo = entradas["input_ids"].shape[1]
        if isinstance(largo, int):  # modelo exportado con longitud fija (77)
            ids = ids + [self.tokenizador.fin] * (largo - len(ids))
        datos = {"input_ids": np.array([ids], dtype=np.int64)}
        if "attention_mask" in entradas:
            datos["attention_mask"] = np.array([[1] * len(ids)], dtype=np.int64)
        return sesion.run([_salida(sesion, "text_embeds")], datos)[0]

    def probabilidades(self, recorte_rgb: np.ndarray) -> np.ndarray:
        """Probabilidad de cada frase (suman 1) para un recorte RGB."""
        img = self._vision.run([self._salida_vision], {self._entrada_vision: preprocesar(recorte_rgb)})[0]
        logits = ESCALA_LOGITS * (_normalizar(img) @ self._embeds_texto.T)[0]
        e = np.exp(logits - logits.max())
        return e / e.sum()

    def prob_movil(self, frame_rgb: np.ndarray, recuadro) -> float:
        """Probabilidad de que el recuadro (en el fotograma completo) sea un móvil."""
        recorte = recorte_cuadrado(frame_rgb, recuadro, config.MARGEN_RECORTE_CLIP)
        return float(self.probabilidades(recorte)[: self.n_movil].sum())
