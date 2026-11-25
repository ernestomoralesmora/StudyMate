"""Apuntes del estudiante: leerlos de archivos y elegir qué parte enviar al asistente.

- Se pueden subir PDF, Word (.docx) y texto (.txt, .md). Solo se lee el texto:
  los archivos no se copian ni se guardan, y al asistente solo le llega texto.
- Un temario entero no cabe en una consulta (y Groq limita los tokens por
  minuto), así que para cada cosa se manda solo lo más relacionado:
  para el plan, lo que más tiene que ver con los temas; para el test de un
  bloque, lo que más tiene que ver con el tema y el objetivo de ese bloque.
"""

import re
import unicodedata
import zipfile
from pathlib import Path
from xml.etree import ElementTree

EXTENSIONES = (".pdf", ".docx", ".txt", ".md")
MAX_PLAN = 6000      # caracteres de apuntes para pedir el plan
MAX_TEST = 6000      # caracteres de apuntes para las preguntas de un bloque
TAM_FRAGMENTO = 900  # los apuntes se trocean en fragmentos de este tamaño (aprox.)

# Palabras tan comunes que no sirven para saber de qué trata un fragmento.
VACIAS = set("""
a al algo ante antes como con contra cual cuando de del desde donde dos el ella ellos en entre
era es esa ese eso esta este esto fue ha han hay la las le les lo los mas me mi muy no nos o
otra otro para pero por porque que se sea segun ser si sin sobre son su sus tambien tema
tiene todo tras un una uno unos y ya objetivo entender aprender estudiar repasar bloque
""".split())


class ErrorApuntes(ValueError):
    """No se ha podido leer un archivo de apuntes (se enseña al usuario)."""


# --- Leer archivos ---------------------------------------------------------------------
def leer_archivo(ruta: str | Path) -> str:
    ruta = Path(ruta)
    extension = ruta.suffix.lower()
    if extension not in EXTENSIONES:
        raise ErrorApuntes(f"{ruta.name}: solo se pueden subir PDF, Word (.docx) o texto (.txt, .md).")
    try:
        if extension == ".pdf":
            texto = _leer_pdf(ruta)
        elif extension == ".docx":
            texto = _leer_docx(ruta)
        else:
            texto = ruta.read_text(encoding="utf-8", errors="replace")
    except ErrorApuntes:
        raise
    except Exception as error:
        raise ErrorApuntes(f"{ruta.name}: no se ha podido leer ({error}).") from error
    texto = _limpiar(texto)
    if len(texto) < 40:
        raise ErrorApuntes(
            f"{ruta.name}: no tiene texto que se pueda leer "
            "(puede ser un PDF escaneado, es decir, solo imágenes)."
        )
    return texto


def _leer_pdf(ruta: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as error:
        raise ErrorApuntes("Para leer PDF falta la librería pypdf: pip install -r requirements.txt") from error
    lector = PdfReader(str(ruta))
    if lector.is_encrypted:
        try:
            lector.decrypt("")
        except Exception as error:
            raise ErrorApuntes(f"{ruta.name}: el PDF está protegido con contraseña.") from error
    return "\n\n".join((pagina.extract_text() or "") for pagina in lector.pages)


def _leer_docx(ruta: Path) -> str:
    """Texto de un .docx sin librerías extra: es un zip con word/document.xml."""
    w = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    with zipfile.ZipFile(ruta) as z:
        raiz = ElementTree.fromstring(z.read("word/document.xml"))
    parrafos = ["".join(t.text or "" for t in p.iter(f"{w}t")) for p in raiz.iter(f"{w}p")]
    return "\n".join(parrafos)


def _limpiar(texto: str) -> str:
    texto = texto.replace("\x00", "")
    texto = re.sub(r"-\n(\w)", r"\1", texto)       # palabras partidas con guion al final de línea
    texto = re.sub(r"[ \t]+", " ", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return texto.strip()


def unir(pegados: str, archivos: list[tuple[str, str]]) -> str:
    """Junta lo pegado a mano y el texto de los archivos, con el nombre de cada uno."""
    partes = [pegados.strip()] if pegados.strip() else []
    partes += [f"=== {nombre} ===\n{texto}" for nombre, texto in archivos]
    return "\n\n".join(partes)


# --- Elegir la parte que más tiene que ver ----------------------------------------------
def _normalizar(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in sin_tildes if not unicodedata.combining(c))


def _palabras(texto: str) -> list[str]:
    return [p for p in re.findall(r"[a-z0-9]+", _normalizar(texto)) if len(p) > 2 and p not in VACIAS]


def fragmentos(texto: str, tam: int = TAM_FRAGMENTO) -> list[str]:
    """Trocea por párrafos, juntándolos hasta unos `tam` caracteres."""
    trozos, actual = [], ""
    for parrafo in re.split(r"\n\s*\n", texto):
        parrafo = parrafo.strip()
        if not parrafo:
            continue
        while len(parrafo) > tam * 2:  # párrafos enormes (PDF sin saltos): se cortan
            trozos.append(parrafo[:tam])
            parrafo = parrafo[tam:]
        if actual and len(actual) + len(parrafo) > tam:
            trozos.append(actual)
            actual = parrafo
        else:
            actual = f"{actual}\n\n{parrafo}" if actual else parrafo
    if actual:
        trozos.append(actual)
    return trozos


def seleccionar(texto: str, consulta: str, maximo: int) -> str:
    """Lo más relacionado con `consulta`, hasta `maximo` caracteres, en el orden original.

    Si los apuntes caben enteros, se mandan enteros.
    """
    texto = texto.strip()
    if len(texto) <= maximo:
        return texto
    claves = set(_palabras(consulta))
    trozos = fragmentos(texto)
    puntos = []
    for i, trozo in enumerate(trozos):
        palabras = _palabras(trozo)
        coincidencias = sum(1 for p in palabras if p in claves)
        # Un poco de preferencia por el principio (suele estar el índice o la introducción).
        puntos.append((coincidencias / (1 + len(palabras)) ** 0.5 + (0.01 if i < 2 else 0), i))
    elegidos, total = [], 0
    for _, i in sorted(puntos, reverse=True):
        if total + len(trozos[i]) > maximo:
            continue
        elegidos.append(i)
        total += len(trozos[i]) + 2
    return "\n\n[...]\n\n".join(trozos[i] for i in sorted(elegidos))


def para_plan(apuntes: str, temas: list[str]) -> str:
    return seleccionar(apuntes, " ".join(temas), MAX_PLAN)


def para_test(apuntes: str, tema: str, objetivo: str) -> str:
    return seleccionar(apuntes, f"{tema} {objetivo}", MAX_TEST)


# --- Apuntes guardados de cada asignatura ----------------------------------------------
# Para no tener que subirlos en cada sesión, se guarda SOLO EL TEXTO de cada archivo
# (no el archivo) en la carpeta del usuario, separado por asignatura:
#   data/usuarios/<usuario>/apuntes/<asignatura>/indice.json y <id>.txt
import hashlib as _hashlib
import json as _json
import secrets as _secrets
from dataclasses import asdict as _asdict
from dataclasses import dataclass as _dataclass
from datetime import datetime as _datetime

MAX_DOCUMENTOS = 30


@_dataclass
class Documento:
    id: str
    nombre: str
    caracteres: int
    subido: str


def _carpeta_asignatura(carpeta_usuario: Path, asignatura: str) -> Path:
    limpio = re.sub(r"[^a-z0-9]+", "-", _normalizar(asignatura)).strip("-")[:30] or "asignatura"
    huella = _hashlib.sha1(asignatura.casefold().encode("utf-8")).hexdigest()[:8]
    return Path(carpeta_usuario) / "apuntes" / f"{limpio}-{huella}"


class BibliotecaApuntes:
    """Los apuntes guardados de una asignatura de un usuario."""

    def __init__(self, carpeta_usuario: Path, asignatura: str):
        self.carpeta = _carpeta_asignatura(carpeta_usuario, asignatura)

    def _indice(self) -> list[Documento]:
        ruta = self.carpeta / "indice.json"
        if not ruta.exists():
            return []
        try:
            return [Documento(**d) for d in _json.loads(ruta.read_text(encoding="utf-8"))]
        except (ValueError, TypeError):
            return []

    def _guardar_indice(self, documentos: list[Documento]) -> None:
        self.carpeta.mkdir(parents=True, exist_ok=True)
        (self.carpeta / "indice.json").write_text(
            _json.dumps([_asdict(d) for d in documentos], ensure_ascii=False, indent=2), encoding="utf-8")

    def documentos(self) -> list[Documento]:
        return [d for d in self._indice() if (self.carpeta / f"{d.id}.txt").exists()]

    def anadir(self, ruta: str | Path) -> Documento:
        """Lee el archivo y guarda su texto. Si ya había uno con el mismo nombre, lo sustituye."""
        nombre = Path(ruta).name
        texto = leer_archivo(ruta)
        documentos = [d for d in self.documentos() if d.nombre != nombre]
        if len(documentos) >= MAX_DOCUMENTOS:
            raise ErrorApuntes(f"Como mucho {MAX_DOCUMENTOS} archivos de apuntes por asignatura.")
        for viejo in self.documentos():
            if viejo.nombre == nombre:
                (self.carpeta / f"{viejo.id}.txt").unlink(missing_ok=True)
        nuevo = Documento(_secrets.token_hex(6), nombre, len(texto),
                          _datetime.now().isoformat(timespec="minutes"))
        self.carpeta.mkdir(parents=True, exist_ok=True)
        (self.carpeta / f"{nuevo.id}.txt").write_text(texto, encoding="utf-8")
        self._guardar_indice(documentos + [nuevo])
        return nuevo

    def quitar(self, id_documento: str) -> None:
        (self.carpeta / f"{id_documento}.txt").unlink(missing_ok=True)
        self._guardar_indice([d for d in self.documentos() if d.id != id_documento])

    def texto(self, id_documento: str) -> str:
        return (self.carpeta / f"{id_documento}.txt").read_text(encoding="utf-8")

    def elegidos(self, ids: list[str]) -> list[tuple[str, str]]:
        """(nombre, texto) de los documentos marcados, en el orden en que se subieron."""
        return [(d.nombre, self.texto(d.id)) for d in self.documentos() if d.id in ids]
