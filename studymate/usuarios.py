"""Usuarios de StudyMate: registro e inicio de sesión con contraseña (todo en local).

- Cada usuario tiene su carpeta en data/usuarios/<usuario>/ con su zoo, su
  historial y su último cuestionario. Nada se sube ni se envía.
- La contraseña nunca se guarda: se guarda su huella (PBKDF2-SHA256 con sal
  aleatoria y 200 000 iteraciones), y al entrar se compara de forma segura.
- La primera cuenta que se crea se queda con los datos de antes de que
  hubiera usuarios (zoo, pecera, historial y perfil sueltos en data/).
"""

import hashlib
import hmac
import json
import re
import secrets
import shutil
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

CARPETA_DATOS = Path(__file__).resolve().parent / "data"
ARCHIVO = "usuarios.json"
ITERACIONES = 200_000
MIN_CONTRASENA = 6
ARCHIVOS_ANTIGUOS = ("zoo.json", "pecera.json", "historial.json", "perfil.json")


class ErrorUsuario(ValueError):
    """Mensaje para el usuario (registro o inicio de sesión)."""


@dataclass
class Usuario:
    usuario: str          # nombre para entrar: minúsculas, números, punto, guion
    nombre: str           # cómo se le saluda
    curso: str = ""
    sal: str = ""
    huella: str = ""
    creado: str = field(default_factory=lambda: datetime.now().isoformat(timespec="minutes"))

    def carpeta(self, base: Path = CARPETA_DATOS) -> Path:
        return base / "usuarios" / self.usuario


def _huella(contrasena: str, sal: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", contrasena.encode("utf-8"), bytes.fromhex(sal), ITERACIONES).hex()


def _normalizar(usuario: str) -> str:
    return usuario.strip().lower()


def cargar_usuarios(base: Path = CARPETA_DATOS) -> list[Usuario]:
    ruta = base / ARCHIVO
    if not ruta.exists():
        return []
    try:
        validos = Usuario.__dataclass_fields__
        return [Usuario(**{k: v for k, v in u.items() if k in validos})
                for u in json.loads(ruta.read_text(encoding="utf-8"))]
    except (ValueError, TypeError, AttributeError):
        return []


def _guardar_usuarios(usuarios: list[Usuario], base: Path) -> None:
    base.mkdir(parents=True, exist_ok=True)
    (base / ARCHIVO).write_text(json.dumps([asdict(u) for u in usuarios], ensure_ascii=False, indent=2),
                                encoding="utf-8")


def registrar(usuario: str, nombre: str, contrasena: str, repetir: str, curso: str = "",
              base: Path = CARPETA_DATOS) -> Usuario:
    usuario = _normalizar(usuario)
    nombre = " ".join(nombre.split())
    if not nombre:
        raise ErrorUsuario("Escribe tu nombre.")
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{2,29}", usuario):
        raise ErrorUsuario("El usuario debe tener entre 3 y 30 caracteres: letras sin tilde, "
                           "números, punto, guion o guion bajo (sin espacios).")
    if len(contrasena) < MIN_CONTRASENA:
        raise ErrorUsuario(f"La contraseña debe tener al menos {MIN_CONTRASENA} caracteres.")
    if contrasena != repetir:
        raise ErrorUsuario("Las dos contraseñas no coinciden.")
    usuarios = cargar_usuarios(base)
    if any(u.usuario == usuario for u in usuarios):
        raise ErrorUsuario("Ese usuario ya existe. Elige otro o inicia sesión.")
    sal = secrets.token_hex(16)
    nuevo = Usuario(usuario, nombre, " ".join(curso.split()), sal, _huella(contrasena, sal))
    carpeta = nuevo.carpeta(base)
    carpeta.mkdir(parents=True, exist_ok=True)
    if not usuarios:
        _pasar_datos_antiguos(base, carpeta)
    _guardar_usuarios(usuarios + [nuevo], base)
    return nuevo


def iniciar_sesion(usuario: str, contrasena: str, base: Path = CARPETA_DATOS) -> Usuario:
    usuario = _normalizar(usuario)
    encontrado = next((u for u in cargar_usuarios(base) if u.usuario == usuario), None)
    # Siempre se calcula una huella, exista o no el usuario, para no dar pistas por el tiempo.
    sal = encontrado.sal if encontrado else secrets.token_hex(16)
    huella = _huella(contrasena, sal)
    if encontrado is None or not hmac.compare_digest(huella, encontrado.huella):
        raise ErrorUsuario("Usuario o contraseña incorrectos.")
    encontrado.carpeta(base).mkdir(parents=True, exist_ok=True)
    return encontrado


def _pasar_datos_antiguos(base: Path, carpeta: Path) -> None:
    """Los datos de antes de haber usuarios pasan a la primera cuenta."""
    for nombre in ARCHIVOS_ANTIGUOS:
        origen = base / nombre
        if origen.exists() and not (carpeta / nombre).exists():
            shutil.move(str(origen), str(carpeta / nombre))
