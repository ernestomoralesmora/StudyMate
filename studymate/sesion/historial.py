"""Historial de sesiones (data/historial.json, no se sube al repositorio).

Cada sesión terminada guarda un resumen con números: nunca imágenes.
"""

import json
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

CARPETA_DATOS = Path(__file__).resolve().parent.parent / "data"
ARCHIVO = "historial.json"
MAXIMO = 500  # sesiones guardadas como mucho


@dataclass
class RegistroSesion:
    temas: list[str]
    planificado_min: float
    estudiado_min: float
    pausas_movil: int
    pausas_ausente: int
    calificacion: str          # "muy_buena", "regular" o "mala"
    puntuacion: int
    bloques_completados: int
    bloques_totales: int
    test_aciertos: int | None = None
    test_total: int | None = None
    origen_plan: str = "llm"
    modo_prueba: bool = False
    fecha: str = field(default_factory=lambda: datetime.now().isoformat(timespec="minutes"))

    @property
    def dia(self) -> date:
        return datetime.fromisoformat(self.fecha).date()


def cargar_historial(carpeta: Path = CARPETA_DATOS) -> list[RegistroSesion]:
    """Sesiones guardadas, de la más antigua a la más reciente."""
    ruta = carpeta / ARCHIVO
    if not ruta.exists():
        return []
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        validos = RegistroSesion.__dataclass_fields__
        return [RegistroSesion(**{k: v for k, v in d.items() if k in validos}) for d in datos]
    except (ValueError, TypeError, KeyError):
        return []


def guardar_registro(registro: RegistroSesion, carpeta: Path = CARPETA_DATOS) -> Path:
    historial = cargar_historial(carpeta) + [registro]
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / ARCHIVO
    ruta.write_text(
        json.dumps([asdict(r) for r in historial[-MAXIMO:]], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return ruta


def estadisticas(historial: list[RegistroSesion], hoy: date | None = None) -> dict:
    """Números para el panel principal y la pantalla de historial (sin el modo prueba)."""
    hoy = hoy or date.today()
    reales = [r for r in historial if not r.modo_prueba]
    semana = [r for r in reales if hoy - r.dia < timedelta(days=7)]
    con_test = [r for r in reales if r.test_total]
    return {
        "sesiones": len(reales),
        "minutos_total": round(sum(r.estudiado_min for r in reales)),
        "minutos_semana": round(sum(r.estudiado_min for r in semana)),
        "sesiones_semana": len(semana),
        "media_puntuacion": round(sum(r.puntuacion for r in reales) / len(reales)) if reales else 0,
        "acierto_test": round(100 * sum(r.test_aciertos for r in con_test)
                              / sum(r.test_total for r in con_test)) if con_test else None,
        "pausas_movil": sum(r.pausas_movil for r in reales),
    }


def minutos_por_dia(historial: list[RegistroSesion], dias: int = 7,
                    hoy: date | None = None) -> list[tuple[date, float]]:
    """Minutos estudiados en cada uno de los últimos `dias` días (para la gráfica)."""
    hoy = hoy or date.today()
    cuenta = {hoy - timedelta(days=i): 0.0 for i in range(dias)}
    for r in historial:
        if not r.modo_prueba and r.dia in cuenta:
            cuenta[r.dia] += r.estudiado_min
    return sorted(cuenta.items())
