"""Lógica de la pecera: calificar una sesión y actualizar el estado guardado.

No depende de la interfaz: la ventana PySide6 solo dibuja lo que hay aquí
(ver escena.py y ui/pecera_widget.py).
"""

import json
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from enum import Enum
from pathlib import Path

CARPETA_DATOS = Path(__file__).resolve().parent.parent / "data"
ARCHIVO = "pecera.json"

# --- Ajustes de la calificación ----------------------------------------------
MIN_ESTUDIO_PARA_CONTAR_S = 5 * 60   # una sesión más corta no cambia la pecera
UMBRAL_MUY_BUENA = 80                # puntuación ≥ 80 → muy buena
UMBRAL_MALA = 50                     # puntuación < 50 → mala
PENALIZACION_PAUSA_MOVIL = 8         # puntos por cada vez que se coge el móvil
PENALIZACION_PAUSA_AUSENTE = 4       # puntos por cada ausencia
BONUS_TEST_MAX = 5                   # el test es opcional y pesa poco

# --- Ajustes de la pecera -------------------------------------------------------
MAX_PECES = 12
SALUD_INICIAL = 60
CAMBIO_SALUD = {"muy_buena": 15, "regular": 0, "mala": -20}

ESPECIES = [  # (nombre, color del cuerpo, color de la cola)
    ("Pez naranja", "#FF8A3D", "#E56F22"),
    ("Pez limón", "#FFD23D", "#E0B21C"),
    ("Pez rosa", "#FF5CA8", "#E03E8C"),
    ("Pez neón", "#39FF88", "#22D06C"),
    ("Pez lila", "#B18CFF", "#9370E6"),
    ("Pez cian", "#00C2FF", "#00A0D6"),
]
ESPECIE_RARA = ("Pez dorado", "#FFE066", "#F2B705")  # premio cada 3 sesiones muy buenas seguidas


class Calificacion(str, Enum):
    MUY_BUENA = "muy_buena"
    REGULAR = "regular"
    MALA = "mala"


@dataclass
class ResumenSesion:
    """Lo que hace falta saber de una sesión terminada para calificarla."""
    planificado_s: float           # tiempo de estudio previsto en el plan
    estudiado_s: float             # tiempo contado por el temporizador
    pausas_movil: int = 0          # veces que pasó a USANDO_MOVIL
    pausas_ausente: int = 0        # veces que pasó a AUSENTE
    test_aciertos: int | None = None
    test_total: int | None = None


@dataclass
class ResultadoCalificacion:
    calificacion: Calificacion
    puntuacion: int
    motivos: list[str]
    cuenta: bool = True            # False si la sesión fue demasiado corta
    bien: list[str] = field(default_factory=list)      # autocrítica: qué ha ido bien
    mejorar: list[str] = field(default_factory=list)   # autocrítica: qué cambiar la próxima vez


def calificar(resumen: ResumenSesion) -> ResultadoCalificacion:
    """Califica una sesión como muy buena, regular o mala, explicando por qué."""
    if resumen.estudiado_s < MIN_ESTUDIO_PARA_CONTAR_S:
        return ResultadoCalificacion(
            Calificacion.REGULAR, 0,
            ["La sesión ha sido muy corta: la pecera no cambia."], cuenta=False,
        )
    previsto = max(resumen.planificado_s, resumen.estudiado_s, 1.0)
    aprovechamiento = min(1.0, resumen.estudiado_s / previsto)
    puntos = 100 * aprovechamiento
    motivos = [f"Has estudiado el {round(aprovechamiento * 100)} % del tiempo previsto."]
    if resumen.pausas_movil:
        puntos -= PENALIZACION_PAUSA_MOVIL * resumen.pausas_movil
        motivos.append(f"Has cogido el móvil {resumen.pausas_movil} "
                       f"{'vez' if resumen.pausas_movil == 1 else 'veces'}.")
    if resumen.pausas_ausente:
        puntos -= PENALIZACION_PAUSA_AUSENTE * resumen.pausas_ausente
        motivos.append(f"Te has ausentado {resumen.pausas_ausente} "
                       f"{'vez' if resumen.pausas_ausente == 1 else 'veces'}.")
    if resumen.test_total:
        acierto = (resumen.test_aciertos or 0) / resumen.test_total
        puntos += BONUS_TEST_MAX * acierto
        motivos.append(f"Test: {resumen.test_aciertos}/{resumen.test_total} aciertos.")
    puntos = int(round(max(0, min(100, puntos))))
    bien, mejorar = _autocritica(resumen, aprovechamiento)
    if puntos >= UMBRAL_MUY_BUENA:
        cal = Calificacion.MUY_BUENA
    elif puntos < UMBRAL_MALA:
        cal = Calificacion.MALA
    else:
        cal = Calificacion.REGULAR
    return ResultadoCalificacion(cal, puntos, motivos, bien=bien, mejorar=mejorar)


def _veces(n: int) -> str:
    return "1 vez" if n == 1 else f"{n} veces"


def _autocritica(r: ResumenSesion, aprovechamiento: float) -> tuple[list[str], list[str]]:
    """Reflexión en primera persona sobre la sesión: qué ha ido bien y qué mejorar."""
    bien: list[str] = []
    mejorar: list[str] = []
    pct = round(aprovechamiento * 100)
    if aprovechamiento >= 0.9:
        bien.append(f"He aprovechado casi todo el tiempo ({pct} %).")
    elif aprovechamiento < 0.75:
        mejorar.append(f"Solo he estudiado el {pct} % del tiempo previsto. "
                       "Quizá los bloques eran demasiado largos: probaré con bloques más cortos.")
    if r.pausas_movil == 0:
        bien.append("No he cogido el móvil en toda la sesión.")
    elif r.pausas_movil == 1:
        mejorar.append("He cogido el móvil 1 vez. La próxima, en silencio y boca abajo.")
    else:
        mejorar.append(f"He cogido el móvil {_veces(r.pausas_movil)}: es lo que más me ha distraído. "
                       "La próxima vez lo dejo en otra habitación.")
    if r.pausas_ausente >= 2:
        mejorar.append(f"Me he levantado {_veces(r.pausas_ausente)}. "
                       "Antes de empezar preparo agua y todo el material.")
    elif r.pausas_ausente == 0:
        bien.append("No me he levantado de la mesa.")
    if r.test_total:
        acierto = (r.test_aciertos or 0) / r.test_total
        if acierto >= 0.7:
            bien.append(f"En el test he acertado {r.test_aciertos} de {r.test_total}.")
        elif acierto < 0.5:
            mejorar.append(f"En el test solo he acertado {r.test_aciertos} de {r.test_total}: "
                           "tengo que repasar las preguntas falladas.")
    return bien, mejorar


@dataclass
class Pez:
    especie: str
    color: str
    cola: str
    nacido: str  # fecha ISO


@dataclass
class EstadoPecera:
    salud: int = SALUD_INICIAL
    peces: list[Pez] = field(default_factory=list)
    muertos_recientes: int = 0       # peces flotando, se limpian con la siguiente buena sesión
    racha_buenas: int = 0            # sesiones muy buenas seguidas (cada 3, un pez dorado)
    historial: list[dict] = field(default_factory=list)

    @classmethod
    def nueva(cls) -> "EstadoPecera":
        hoy = date.today().isoformat()
        peces = [Pez(*ESPECIES[i], nacido=hoy) for i in range(3)]
        return cls(peces=peces)

    # --- Calidad del agua, para la escena -----------------------------------------
    @property
    def estado_agua(self) -> str:
        if self.salud >= 60:
            return "cristalina"
        return "turbia" if self.salud >= 30 else "sucia"


def aplicar_sesion(estado: EstadoPecera, resultado: ResultadoCalificacion,
                   fecha: date | None = None) -> list[str]:
    """Actualiza la pecera con el resultado de una sesión. Devuelve qué ha cambiado."""
    fecha = fecha or date.today()
    cambios: list[str] = []
    if not resultado.cuenta:
        return resultado.motivos[:]

    cal = resultado.calificacion
    estado.salud = max(0, min(100, estado.salud + CAMBIO_SALUD[cal.value]))

    if cal == Calificacion.MUY_BUENA:
        estado.racha_buenas += 1
        if estado.muertos_recientes:
            cambios.append("Has limpiado la pecera.")
            estado.muertos_recientes = 0
        if len(estado.peces) < MAX_PECES:
            if estado.racha_buenas % 3 == 0:
                estado.peces.append(Pez(*ESPECIE_RARA, nacido=fecha.isoformat()))
                cambios.append("¡Tres sesiones muy buenas seguidas: ha llegado un pez dorado!")
            else:
                especie = ESPECIES[len(estado.peces) % len(ESPECIES)]
                estado.peces.append(Pez(*especie, nacido=fecha.isoformat()))
                cambios.append(f"Ha llegado un pez nuevo ({especie[0].lower()}).")
        else:
            cambios.append("Tu pecera está llena y en su mejor momento.")
    elif cal == Calificacion.MALA:
        estado.racha_buenas = 0
        if estado.peces:
            muerto = estado.peces.pop()
            estado.muertos_recientes = min(3, estado.muertos_recientes + 1)
            cambios.append(f"Un {muerto.especie.lower()} no lo ha superado.")
        cambios.append("El agua se ha ensuciado.")
    else:
        estado.racha_buenas = 0
        cambios.append("La pecera se mantiene igual.")

    estado.historial.append({
        "fecha": datetime.combine(fecha, datetime.now().time()).isoformat(timespec="minutes"),
        "calificacion": cal.value,
        "puntuacion": resultado.puntuacion,
        "salud": estado.salud,
        "peces": len(estado.peces),
    })
    estado.historial = estado.historial[-60:]
    return cambios


def texto_racha(estado: EstadoPecera) -> str:
    """La racha se cuenta por sesiones muy buenas seguidas, no por días."""
    n = estado.racha_buenas
    if n == 0:
        return "Racha: 0 sesiones muy buenas seguidas."
    faltan = 3 - n % 3
    sesion = "sesión muy buena seguida" if n == 1 else "sesiones muy buenas seguidas"
    extra = ("¡Pez dorado conseguido!" if faltan == 3
             else f"{'Falta 1 sesión' if faltan == 1 else f'Faltan {faltan} sesiones'} para el pez dorado.")
    return f"Racha: {n} {sesion}. {extra}"


def mensaje(estado: EstadoPecera, resultado: ResultadoCalificacion | None = None) -> str:
    """Texto del panel principal: cómo está la pecera, la racha y la autocrítica de la última sesión."""
    if estado.salud >= 80:
        lineas = ["Tu pecera está en su mejor momento. ¡Sigue así!"]
    elif estado.salud >= 55:
        lineas = ["Va bien. Una sesión muy buena más y llegará un pez nuevo."]
    elif estado.salud >= 30:
        lineas = ["El agua está turbia. Una sesión sin móvil la limpiará."]
    else:
        lineas = ["Tus peces lo están pasando mal. La próxima sesión muy buena los salvará."]
    lineas.append(texto_racha(estado))
    if resultado and resultado.cuenta:
        if resultado.bien:
            lineas.append("\nQué ha ido bien:")
            lineas += [f"• {x}" for x in resultado.bien]
        if resultado.mejorar:
            lineas.append("\nQué puedo mejorar:")
            lineas += [f"• {x}" for x in resultado.mejorar]
    return "\n".join(lineas)


# --- Guardar y cargar (studymate/data/pecera.json, no se sube al repositorio) ---------
def cargar(carpeta: Path = CARPETA_DATOS) -> EstadoPecera:
    ruta = carpeta / ARCHIVO
    if not ruta.exists():
        return EstadoPecera.nueva()
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        datos["peces"] = [Pez(**p) for p in datos.get("peces", [])]
        validos = EstadoPecera.__dataclass_fields__
        return EstadoPecera(**{k: v for k, v in datos.items() if k in validos})
    except (ValueError, TypeError, KeyError):
        return EstadoPecera.nueva()


def guardar(estado: EstadoPecera, carpeta: Path = CARPETA_DATOS) -> Path:
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / ARCHIVO
    ruta.write_text(json.dumps(asdict(estado), ensure_ascii=False, indent=2), encoding="utf-8")
    return ruta
