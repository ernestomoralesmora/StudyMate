"""El zoo: un recinto por asignatura (RF14, evolución de la pecera).

Cada asignatura del curso tiene su recinto con un animal que elige el
estudiante entre 10 (uno distinto por asignatura). Igual que la pecera, el
zoo NO cambia mientras se estudia: al terminar una sesión se califica
(pecera.calificar) y solo cambia el recinto de la asignatura estudiada:

    muy buena -> +15 de salud y llega otro animal (cada 3, el recinto sube de nivel)
    regular   -> igual
    mala      -> -20 de salud y se va un animal

Cada recinto guarda sus sesiones, para ver el avance de cada asignatura.
Python puro: la interfaz solo lo dibuja. Se guarda en data/zoo.json.
"""

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from .pecera import CARPETA_DATOS, Calificacion, ResultadoCalificacion
from .pecera import cargar as cargar_pecera

ARCHIVO = "zoo.json"
MAX_RECINTOS = 10
MAX_ANIMALES = 9
SALUD_INICIAL = 60
CAMBIO_SALUD = {"muy_buena": 15, "regular": 0, "mala": -20}
ANIMALES_POR_NIVEL = 3
MAX_HISTORIAL = 100
MAX_TEMAS = 40


@dataclass(frozen=True)
class Animal:
    nombre: str
    plural: str
    habitat: str
    cielo: tuple[str, str]   # degradado del fondo (arriba, abajo) con el recinto sano
    suelo: str
    nada: bool = False        # los que nadan se reparten a media altura


# Los 10 animales que se pueden elegir (uno por asignatura).
ANIMALES: dict[str, Animal] = {
    "pez": Animal("Pez", "peces", "Acuario", ("#1597D6", "#06375E"), "#D9C08A", nada=True),
    "pinguino": Animal("Pingüino", "pingüinos", "Polo", ("#9FD3F0", "#5FA4D1"), "#F4F7FA"),
    "leon": Animal("León", "leones", "Sabana", ("#F7C873", "#E59A4C"), "#B98B4E"),
    "jirafa": Animal("Jirafa", "jirafas", "Llanura de acacias", ("#FBD38D", "#F2A65A"), "#C9A063"),
    "loro": Animal("Loro", "loros", "Selva", ("#2E9E6A", "#0F4D33"), "#5B3E24"),
    "mono": Animal("Mono", "monos", "Bosque tropical", ("#3FAF7A", "#14573A"), "#6B4A2B"),
    "tortuga": Animal("Tortuga", "tortugas", "Playa", ("#7FD4E8", "#F5DEB3"), "#E8C98E"),
    "rana": Animal("Rana", "ranas", "Estanque", ("#7BC47F", "#2F6B4F"), "#3E6B48"),
    "buho": Animal("Búho", "búhos", "Bosque de noche", ("#2B3A67", "#141B33"), "#2E3B2F"),
    "zorro": Animal("Zorro", "zorros", "Bosque de otoño", ("#F4A259", "#8C4A2F"), "#6B4226"),
}


class ErrorZoo(ValueError):
    """Algo que no se puede hacer (se enseña al usuario tal cual)."""


@dataclass
class Recinto:
    asignatura: str
    especie: str
    salud: int = SALUD_INICIAL
    animales: int = 0
    racha_buenas: int = 0
    sesiones: list[dict] = field(default_factory=list)  # {fecha, calificacion, puntuacion, minutos}
    temas: list[str] = field(default_factory=list)      # temas de la asignatura (los elige el estudiante)
    # Respuestas del último cuestionario de ESTA asignatura (para proponerlas la próxima vez).
    ultimo_cuestionario: dict = field(default_factory=dict)

    @property
    def animal(self) -> Animal:
        return ANIMALES[self.especie]

    @property
    def nivel(self) -> int:
        return 1 + self.animales // ANIMALES_POR_NIVEL

    @property
    def minutos(self) -> float:
        return sum(s.get("minutos", 0) for s in self.sesiones)

    def describir_animales(self) -> str:
        n = self.animales
        nombre = self.animal.nombre.lower() if n == 1 else self.animal.plural
        return f"{n} de {MAX_ANIMALES} {nombre}"

    def anadir_tema(self, tema: str) -> str:
        tema = " ".join(tema.split())
        if not tema:
            raise ErrorZoo("Escribe el nombre del tema.")
        if len(tema) > 80:
            raise ErrorZoo("El nombre del tema es demasiado largo (máximo 80 letras).")
        repetido = next((t for t in self.temas if t.casefold() == tema.casefold()), None)
        if repetido:
            raise ErrorZoo(f"«{repetido}» ya está en {self.asignatura}.")
        if len(self.temas) >= MAX_TEMAS:
            raise ErrorZoo(f"Como mucho {MAX_TEMAS} temas por asignatura.")
        self.temas.append(tema)
        return tema

    def quitar_tema(self, tema: str) -> None:
        self.temas = [t for t in self.temas if t != tema]

    def texto_racha(self) -> str:
        n = self.racha_buenas
        return f"{n} sesiones muy buenas seguidas" if n != 1 else "1 sesión muy buena seguida"


NOMBRE_POR_DEFECTO = "Mi zoo"


@dataclass
class Zoo:
    recintos: list[Recinto] = field(default_factory=list)
    nombre: str = NOMBRE_POR_DEFECTO

    def renombrar(self, nombre: str) -> None:
        nombre = " ".join(nombre.split())
        if not nombre:
            raise ErrorZoo("Escribe un nombre para tu zoo.")
        if len(nombre) > 40:
            raise ErrorZoo("El nombre del zoo es demasiado largo (máximo 40 letras).")
        self.nombre = nombre

    # --- Asignaturas ------------------------------------------------------------------
    def recinto(self, asignatura: str) -> Recinto | None:
        clave = asignatura.strip().casefold()
        return next((r for r in self.recintos if r.asignatura.casefold() == clave), None)

    @property
    def asignaturas(self) -> list[str]:
        return [r.asignatura for r in self.recintos]

    def especies_libres(self) -> list[str]:
        usadas = {r.especie for r in self.recintos}
        return [e for e in ANIMALES if e not in usadas]

    def dueno(self, especie: str) -> str | None:
        """Asignatura que ya tiene ese animal (o None)."""
        return next((r.asignatura for r in self.recintos if r.especie == especie), None)

    def anadir(self, asignatura: str, especie: str, temas: list[str] | None = None) -> Recinto:
        asignatura = " ".join(asignatura.split())
        if not asignatura:
            raise ErrorZoo("Escribe el nombre de la asignatura.")
        if len(asignatura) > 60:
            raise ErrorZoo("El nombre de la asignatura es demasiado largo (máximo 60 letras).")
        if especie not in ANIMALES:
            raise ErrorZoo("Elige uno de los 10 animales.")
        if self.recinto(asignatura):
            raise ErrorZoo(f"{self.recinto(asignatura).asignatura} ya tiene su recinto en el zoo.")
        if self.dueno(especie):
            raise ErrorZoo(f"El {ANIMALES[especie].nombre.lower()} ya es de {self.dueno(especie)}: elige otro.")
        if len(self.recintos) >= MAX_RECINTOS:
            raise ErrorZoo(f"El zoo tiene como mucho {MAX_RECINTOS} asignaturas (una por animal).")
        nuevo = Recinto(asignatura, especie)
        for tema in temas or []:
            if tema.strip() and not any(t.casefold() == " ".join(tema.split()).casefold() for t in nuevo.temas):
                nuevo.anadir_tema(tema)
        self.recintos.append(nuevo)
        return nuevo

    def quitar(self, asignatura: str) -> None:
        r = self.recinto(asignatura)
        if r:
            self.recintos.remove(r)

    # --- Resúmenes ------------------------------------------------------------------------
    @property
    def total_animales(self) -> int:
        return sum(r.animales for r in self.recintos)

    @property
    def total_minutos(self) -> float:
        return sum(r.minutos for r in self.recintos)

    def necesita_atencion(self) -> Recinto | None:
        return min(self.recintos, key=lambda r: r.salud) if self.recintos else None


def aplicar_sesion(zoo: Zoo, asignatura: str, resultado: ResultadoCalificacion,
                   minutos: float = 0, fecha: datetime | None = None) -> list[str]:
    """Cambia el recinto de la asignatura al terminar una sesión. Devuelve qué ha cambiado."""
    r = zoo.recinto(asignatura)
    if r is None:
        return [f"{asignatura} no tiene recinto en el zoo: no cambia nada."]
    if not resultado.cuenta:
        return resultado.motivos[:]
    cal = resultado.calificacion
    animal = r.animal.nombre.lower()
    r.salud = max(0, min(100, r.salud + CAMBIO_SALUD[cal.value]))
    cambios = []
    if cal == Calificacion.MUY_BUENA:
        r.racha_buenas += 1
        if r.animales < MAX_ANIMALES:
            r.animales += 1
            if r.animales % ANIMALES_POR_NIVEL == 0:
                cambios.append(f"¡Ha llegado otro {animal} y el recinto sube al nivel {r.nivel}!")
            else:
                cambios.append(f"Ha llegado otro {animal} al recinto de {r.asignatura}.")
        else:
            cambios.append(f"El recinto de {r.asignatura} está completo y en su mejor momento.")
    elif cal == Calificacion.MALA:
        r.racha_buenas = 0
        if r.animales:
            r.animales -= 1
            cambios.append(f"Se ha ido un {animal} del recinto de {r.asignatura}.")
        cambios.append("El recinto ha perdido color.")
    else:
        r.racha_buenas = 0
        cambios.append(f"El recinto de {r.asignatura} se queda igual.")
    r.sesiones.append({
        "fecha": (fecha or datetime.now()).isoformat(timespec="minutes"),
        "calificacion": cal.value,
        "puntuacion": resultado.puntuacion,
        "minutos": round(minutos, 1),
    })
    r.sesiones = r.sesiones[-MAX_HISTORIAL:]
    return cambios


def mensaje(zoo: Zoo) -> str:
    """Frase para el panel principal."""
    if not zoo.recintos:
        return "Tu zoo está vacío. Añade tus asignaturas y elige un animal para cada una."
    peor = zoo.necesita_atencion()
    if peor.salud >= 80:
        return "Todo tu zoo está en plena forma. ¡Sigue así!"
    if peor.salud >= 45:
        return f"El zoo va bien. Una sesión muy buena de {peor.asignatura} lo pondría a tope."
    return (f"El recinto de {peor.asignatura} lo está pasando mal: "
            f"tus {peor.animal.plural} te esperan para una buena sesión.")


# --- Guardar y cargar (data/zoo.json, no se sube al repositorio) --------------------------
def cargar(carpeta: Path = CARPETA_DATOS) -> Zoo:
    ruta = carpeta / ARCHIVO
    if ruta.exists():
        try:
            datos = json.loads(ruta.read_text(encoding="utf-8"))
            validos = Recinto.__dataclass_fields__
            recintos = [Recinto(**{k: v for k, v in r.items() if k in validos})
                        for r in datos.get("recintos", []) if r.get("especie") in ANIMALES]
            return Zoo(recintos[:MAX_RECINTOS], datos.get("nombre") or NOMBRE_POR_DEFECTO)
        except (ValueError, TypeError, AttributeError):
            return Zoo()
    # Primera vez: si había pecera, pasa a ser el acuario de una asignatura "General".
    if (carpeta / "pecera.json").exists():
        pecera = cargar_pecera(carpeta)
        return Zoo([Recinto("General", "pez", salud=pecera.salud,
                            animales=min(len(pecera.peces), MAX_ANIMALES),
                            racha_buenas=pecera.racha_buenas)])
    return Zoo()


def guardar(zoo: Zoo, carpeta: Path = CARPETA_DATOS) -> Path:
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / ARCHIVO
    ruta.write_text(json.dumps({"nombre": zoo.nombre, "recintos": [asdict(r) for r in zoo.recintos]},
                               ensure_ascii=False, indent=2), encoding="utf-8")
    return ruta
