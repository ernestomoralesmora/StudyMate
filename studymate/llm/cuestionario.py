"""Cuestionario inicial de cada sesión (RF5, RF11).

Antes de estudiar, el estudiante dice cuánto tiempo tiene, cuántos minutos seguidos
aguanta concentrado, cómo de cansado está, qué temas quiere estudiar y qué dispositivos
necesita (por ejemplo, una tablet con apuntes). Con eso se adapta el plan.

La interfaz PySide6 (fase 3) rellenará un PerfilSesion; mientras tanto,
`preguntar_por_consola()` sirve para probarlo.
"""

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

# Dispositivos que el estudiante puede marcar como material de estudio.
# Se corresponden con las clases COCO que usa la detección (vision/config.py).
DISPOSITIVOS = {
    "movil": "cell phone",  # COCO no distingue móvil de tablet: los dos salen como "cell phone"
    "tablet": "cell phone",
}

NIVELES_CANSANCIO = {
    1: "Descansado",
    2: "Bien",
    3: "Algo cansado",
    4: "Cansado",
    5: "Muy cansado",
}

NIVELES_CONOCIMIENTO = {
    1: "No sé nada del tema",
    2: "Me suena",
    3: "Lo conozco a medias",
    4: "Lo domino casi todo",
    5: "Solo quiero repasar",
}

CARPETA_DATOS = Path(__file__).resolve().parent.parent / "data"


@dataclass
class PerfilSesion:
    tiempo_disponible_min: int
    concentracion_min: int
    cansancio: int  # 1 (descansado) a 5 (muy cansado)
    temas: list[str]
    conocimiento_previo: int = 2  # 1 (nada) a 5 (solo repasar)
    dispositivos_permitidos: list[str] = field(default_factory=list)  # claves de DISPOSITIVOS
    fecha: str = field(default_factory=lambda: datetime.now().isoformat(timespec="minutes"))

    def __post_init__(self) -> None:
        self.temas = [t.strip() for t in self.temas if t and t.strip()]
        errores = validar_perfil(self)
        if errores:
            raise ValueError("; ".join(errores))

    @property
    def clases_permitidas(self) -> frozenset[str]:
        """Clases COCO que no deben pausar el tiempo (para MotorDeteccion)."""
        return frozenset(DISPOSITIVOS[d] for d in self.dispositivos_permitidos)


def validar_perfil(p: PerfilSesion) -> list[str]:
    errores = []
    if not 10 <= p.tiempo_disponible_min <= 480:
        errores.append("El tiempo disponible debe estar entre 10 y 480 minutos.")
    if not 5 <= p.concentracion_min <= 120:
        errores.append("La concentración debe estar entre 5 y 120 minutos.")
    if p.cansancio not in NIVELES_CANSANCIO:
        errores.append("El cansancio debe ser un número del 1 al 5.")
    if p.conocimiento_previo not in NIVELES_CONOCIMIENTO:
        errores.append("El conocimiento previo debe ser un número del 1 al 5.")
    if not p.temas:
        errores.append("Indica al menos un tema.")
    desconocidos = [d for d in p.dispositivos_permitidos if d not in DISPOSITIVOS]
    if desconocidos:
        errores.append(f"Dispositivos no reconocidos: {', '.join(desconocidos)}.")
    return errores


def guardar_perfil(p: PerfilSesion, carpeta: Path = CARPETA_DATOS) -> Path:
    """Guarda el último perfil en data/perfil.json (no se sube al repositorio)."""
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / "perfil.json"
    ruta.write_text(json.dumps(asdict(p), ensure_ascii=False, indent=2), encoding="utf-8")
    return ruta


def cargar_perfil(carpeta: Path = CARPETA_DATOS) -> PerfilSesion | None:
    """Devuelve el último perfil guardado, para proponerlo por defecto, o None."""
    ruta = carpeta / "perfil.json"
    if not ruta.exists():
        return None
    try:
        return PerfilSesion(**json.loads(ruta.read_text(encoding="utf-8")))
    except (ValueError, TypeError):
        return None


# --- Versión de consola (hasta que exista la interfaz) ----------------------

def _pedir_entero(texto: str, minimo: int, maximo: int, defecto: int | None) -> int:
    sufijo = f" [{defecto}]" if defecto is not None else ""
    while True:
        valor = input(f"{texto}{sufijo}: ").strip()
        if not valor and defecto is not None:
            return defecto
        if valor.isdigit() and minimo <= int(valor) <= maximo:
            return int(valor)
        print(f"  Escribe un número entre {minimo} y {maximo}.")


def preguntar_por_consola() -> PerfilSesion:
    anterior = cargar_perfil()
    print("\n=== StudyMate · Antes de empezar ===\n")
    tiempo = _pedir_entero(
        "¿Cuántos minutos tienes para estudiar hoy?", 10, 480,
        anterior.tiempo_disponible_min if anterior else 60,
    )
    concentracion = _pedir_entero(
        "¿Cuántos minutos seguidos sueles aguantar concentrado?", 5, 120,
        anterior.concentracion_min if anterior else 25,
    )
    print("¿Cómo de cansado estás? " + ", ".join(f"{k}={v}" for k, v in NIVELES_CANSANCIO.items()))
    cansancio = _pedir_entero("Cansancio", 1, 5, 2)
    temas_txt = input("¿Qué temas o apartados vas a estudiar? (separados por comas): ")
    print("¿Cuánto sabes ya? " + ", ".join(f"{k}={v}" for k, v in NIVELES_CONOCIMIENTO.items()))
    conocimiento = _pedir_entero("Conocimiento previo", 1, 5, 2)
    disp = input("¿Necesitas usar el móvil o la tablet para estudiar? (movil, tablet o nada): ")
    dispositivos = [d.strip().lower() for d in disp.split(",") if d.strip().lower() in DISPOSITIVOS]

    perfil = PerfilSesion(
        tiempo_disponible_min=tiempo,
        concentracion_min=concentracion,
        cansancio=cansancio,
        temas=temas_txt.split(","),
        conocimiento_previo=conocimiento,
        dispositivos_permitidos=dispositivos,
    )
    guardar_perfil(perfil)
    return perfil
