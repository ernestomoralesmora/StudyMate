"""Plan de bloques de estudio personalizado (RF6, RNF5, RNF8).

1. Se pide a Groq un plan en JSON a partir del cuestionario (y, si los hay, de los apuntes).
2. La aplicación valida que los tiempos cuadran: cada bloque cabe en la concentración
   del estudiante y el total cabe en el tiempo disponible.
3. Si el plan no es válido, se le pide a Groq que lo corrija una vez, indicándole los errores.
4. Si sigue sin ser válido o no hay conexión, se usa un plan básico calculado sin LLM.

Las funciones reciben `consultar_modelo` (como en preguntas.py) para poder probarlas
sin conexión con respuestas inventadas.
"""

from collections.abc import Callable
from dataclasses import dataclass, field

from studymate.llm.cuestionario import NIVELES_CANSANCIO, NIVELES_CONOCIMIENTO, PerfilSesion

# --- Reglas de tiempos -------------------------------------------------------
MIN_ESTUDIO = 5          # minutos mínimos de un bloque de estudio
MINUTOS_TEST = 5         # el test de 5 preguntas (si el estudiante lo quiere)
MAX_SIN_USAR = 3         # minutos de estudio que el plan del LLM puede perder respecto al óptimo
MIN_DESCANSO = 3
MAX_DESCANSO = 15
# Con cansancio alto se acortan los bloques respecto a la concentración declarada.
FACTOR_CANSANCIO = {1: 1.0, 2: 1.0, 3: 0.9, 4: 0.8, 5: 0.7}

ESQUEMA_PLAN = {
    "type": "object",
    "properties": {
        "bloques": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "tema": {"type": "string"},
                    "objetivo": {"type": "string"},
                    "minutos_estudio": {"type": "integer"},
                    "minutos_test": {"type": "integer"},
                    "minutos_descanso": {"type": "integer"},
                },
                "required": ["tema", "objetivo", "minutos_estudio", "minutos_test",
                             "minutos_descanso"],
                "additionalProperties": False,
            },
        },
        "justificacion": {"type": "string"},
    },
    "required": ["bloques", "justificacion"],
    "additionalProperties": False,
}


@dataclass
class Bloque:
    tema: str
    objetivo: str
    minutos_estudio: int
    minutos_test: int
    minutos_descanso: int

    @property
    def total(self) -> int:
        return self.minutos_estudio + self.minutos_test + self.minutos_descanso


@dataclass
class Plan:
    bloques: list[Bloque]
    justificacion: str
    origen: str = "llm"  # "llm" o "basico"
    avisos: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return sum(b.total for b in self.bloques)


def minutos_test(perfil: PerfilSesion) -> int:
    return MINUTOS_TEST if perfil.con_test else 0


def descanso_base(perfil: PerfilSesion) -> int:
    """Descanso entre bloques: más largo si está cansado, más corto con bloques cortos."""
    if perfil.cansancio >= 4:
        return 10
    return 5 if duracion_maxima_bloque(perfil) >= 20 else MIN_DESCANSO


def estudio_optimo(perfil: PerfilSesion) -> tuple[int, int]:
    """(número de bloques, minutos de estudio) que dan MÁS tiempo de estudio.

    Cada bloque añade un test y un descanso, así que más bloques no siempre es
    mejor: se prueba cada número de bloques y se queda el que más estudio deja
    (con empate, el de menos bloques).
    """
    maximo = duracion_maxima_bloque(perfil)
    test, descanso = minutos_test(perfil), descanso_base(perfil)
    mejor = (1, max(MIN_ESTUDIO, min(maximo, perfil.tiempo_disponible_min - test)))
    n = 2
    while True:
        disponible = perfil.tiempo_disponible_min - n * test - (n - 1) * descanso
        if disponible < n * MIN_ESTUDIO:
            break
        estudio = min(n * maximo, disponible)
        if estudio > mejor[1]:
            mejor = (n, estudio)
        n += 1
    return mejor


def duracion_maxima_bloque(perfil: PerfilSesion) -> int:
    """Minutos máximos de estudio seguidos, según concentración y cansancio."""
    return max(MIN_ESTUDIO, int(perfil.concentracion_min * FACTOR_CANSANCIO[perfil.cansancio]))


def validar_plan(plan: Plan, perfil: PerfilSesion) -> list[str]:
    """Devuelve la lista de errores del plan (vacía si es válido)."""
    errores = []
    maximo = duracion_maxima_bloque(perfil)
    if not plan.bloques:
        return ["El plan no tiene bloques."]
    for i, b in enumerate(plan.bloques, start=1):
        if not b.tema.strip():
            errores.append(f"Bloque {i}: falta el tema.")
        if not MIN_ESTUDIO <= b.minutos_estudio <= maximo:
            errores.append(
                f"Bloque {i}: {b.minutos_estudio} min de estudio; debe estar entre "
                f"{MIN_ESTUDIO} y {maximo}."
            )
        if b.minutos_test != minutos_test(perfil):
            errores.append(f"Bloque {i}: el test debe durar {minutos_test(perfil)} min.")
        ultimo = i == len(plan.bloques)
        minimo_descanso = 0 if ultimo else MIN_DESCANSO
        if not minimo_descanso <= b.minutos_descanso <= MAX_DESCANSO:
            errores.append(
                f"Bloque {i}: {b.minutos_descanso} min de descanso; debe estar entre "
                f"{minimo_descanso} y {MAX_DESCANSO}."
            )
    if plan.total > perfil.tiempo_disponible_min:
        errores.append(
            f"El plan dura {plan.total} min y solo hay {perfil.tiempo_disponible_min}."
        )
    temas_plan = {
        parte.strip().casefold() for b in plan.bloques for parte in b.tema.split(",")
    }
    sin_cubrir = [t for t in perfil.temas if t.casefold() not in temas_plan]
    if sin_cubrir:
        errores.append(f"Faltan temas por incluir: {', '.join(sin_cubrir)}.")
    _, optimo = estudio_optimo(perfil)
    estudio = sum(b.minutos_estudio for b in plan.bloques)
    if estudio < optimo - MAX_SIN_USAR:
        errores.append(
            f"Solo hay {estudio} min de estudio y se pueden conseguir {optimo}: usa menos "
            f"bloques y más largos (hasta {maximo} min cada uno)."
        )
    return errores


def _peticion(perfil: PerfilSesion, apuntes: str | None, errores: list[str] | None) -> str:
    maximo = duracion_maxima_bloque(perfil)
    texto = (
        "Eres StudyMate, un compañero de estudio que planifica sesiones personalizadas.\n"
        "Reparte la sesión en bloques. Cada bloque tiene: tema, objetivo (una frase "
        "concreta de qué aprender), minutos_estudio, minutos_test y minutos_descanso.\n\n"
        "REGLAS (obligatorias):\n"
        f"- minutos_estudio entre {MIN_ESTUDIO} y {maximo} en cada bloque.\n"
        f"- minutos_test = {minutos_test(perfil)} en todos los bloques "
        f"({'el estudiante quiere test' if perfil.con_test else 'el estudiante no quiere test'}).\n"
        f"- minutos_descanso entre {MIN_DESCANSO} y {MAX_DESCANSO}; en el último bloque puede ser 0.\n"
        f"- La suma de todos los minutos no puede pasar de {perfil.tiempo_disponible_min}.\n"
        "- Usa exactamente los nombres de los temas que da el estudiante y que todos "
        "aparezcan. Si hay más temas que bloques, agrupa varios en un bloque "
        "separándolos por comas en 'tema'.\n"
        f"- Maximiza el tiempo de ESTUDIO: cada bloque añade test y descanso, así que usa "
        f"los menos bloques posibles, cada uno lo más cerca de {maximo} min. El estudio total "
        f"debe ser de al menos {estudio_optimo(perfil)[1] - MAX_SIN_USAR} min. Bloques de "
        "duración parecida.\n"
        "- Si el estudiante está cansado, pon descansos algo más largos.\n"
        "- Si conoce poco el tema, dedica más bloques a los temas nuevos; si solo quiere "
        "repasar, bloques más cortos y variados.\n"
        "- En 'justificacion', explica en 2 o 3 frases, hablándole de tú, por qué el plan es así.\n\n"
        "ESTUDIANTE:\n"
        f"- Tiempo disponible: {perfil.tiempo_disponible_min} min\n"
        f"- Minutos seguidos que aguanta concentrado: {perfil.concentracion_min}\n"
        f"- Cansancio: {NIVELES_CANSANCIO[perfil.cansancio]}\n"
        f"- Conocimiento previo: {NIVELES_CONOCIMIENTO[perfil.conocimiento_previo]}\n"
        f"- Temas: {'; '.join(perfil.temas)}\n"
    )
    if apuntes and apuntes.strip():
        texto += f"\nAPUNTES (para fijar los objetivos):\n\"\"\"\n{apuntes.strip()[:6000]}\n\"\"\"\n"
    if errores:
        texto += (
            "\nTu plan anterior no cumplía las reglas por estos motivos. Corrígelo:\n- "
            + "\n- ".join(errores) + "\n"
        )
    return texto


def _a_plan(datos: dict) -> Plan:
    bloques = [Bloque(**b) for b in datos["bloques"]]
    return Plan(bloques=bloques, justificacion=datos.get("justificacion", "").strip())


def _agrupar(temas: list[str], n: int) -> list[list[str]]:
    """Reparte los temas en n grupos seguidos y lo más parecidos posible."""
    grupos, inicio = [], 0
    for i in range(n):
        fin = round((i + 1) * len(temas) / n)
        grupos.append(temas[inicio:fin] or [temas[i % len(temas)]])
        inicio = fin
    return grupos


def plan_basico(perfil: PerfilSesion, aviso: str | None = None) -> Plan:
    """Plan sin LLM: usa todo el tiempo con bloques parecidos y reparte todos los temas."""
    maximo = duracion_maxima_bloque(perfil)
    test = minutos_test(perfil)
    descanso = descanso_base(perfil)
    n, total = estudio_optimo(perfil)
    estudios = [total // n + (1 if i < total % n else 0) for i in range(n)]

    grupos = _agrupar(perfil.temas, n)
    bloques = []
    for i, (grupo, estudio) in enumerate(zip(grupos, estudios)):
        tema = ", ".join(grupo)
        bloques.append(Bloque(tema, f"Estudiar {tema}", estudio, test,
                              0 if i == n - 1 else descanso))
    avisos = [aviso] if aviso else []
    if len(perfil.temas) > n:
        avisos.append(
            f"Tienes {len(perfil.temas)} temas y caben {n} bloques: se estudian "
            "varios temas en cada bloque."
        )
    con_test = f", un test de {test} min" if test else ""
    return Plan(
        bloques=bloques,
        justificacion=(
            f"{n} bloque{'s' if n > 1 else ''} de unos {estudios[0]} min (según tu "
            f"concentración y cansancio){con_test} y {descanso} min de descanso entre bloques."
        ),
        origen="basico",
        avisos=avisos,
    )


def generar_plan(
    perfil: PerfilSesion,
    consultar_modelo: Callable[[str], dict] | None = None,
    apuntes: str | None = None,
    reintentos: int = 1,
) -> Plan:
    """Genera el plan con el LLM, lo valida y, si hace falta, usa el plan básico.

    `consultar_modelo(peticion) -> dict` devuelve el JSON del plan. Por defecto usa Groq.
    """
    from studymate.llm.cliente_groq import ErrorConexionLLM, consultar_json

    if consultar_modelo is None:
        def consultar_modelo(peticion: str) -> dict:
            return consultar_json(peticion, ESQUEMA_PLAN, "plan_studymate", temperatura=0.3)

    errores: list[str] | None = None
    for _ in range(reintentos + 1):
        try:
            plan = _a_plan(consultar_modelo(_peticion(perfil, apuntes, errores)))
        except ErrorConexionLLM as error:
            return plan_basico(perfil, f"No se ha podido usar el asistente ({error}). Se usa un plan básico.")
        except (KeyError, TypeError, ValueError) as error:
            errores = [f"La respuesta no tenía el formato pedido ({error})."]
            continue
        errores = validar_plan(plan, perfil)
        if not errores:
            return plan
    return plan_basico(
        perfil, "El asistente no ha dado un plan válido: se usa un plan básico."
    )


def describir_plan(plan: Plan) -> str:
    """Texto del plan para mostrarlo en consola (y revisarlo antes de empezar, RF10)."""
    lineas = []
    for aviso in plan.avisos:
        lineas.append(f"⚠ {aviso}")
    for i, b in enumerate(plan.bloques, start=1):
        test = f" + {b.minutos_test} min test" if b.minutos_test else ""
        descanso = f" + {b.minutos_descanso} min descanso" if b.minutos_descanso else ""
        lineas.append(
            f"{i}. {b.tema}: {b.minutos_estudio} min estudio{test}{descanso}"
            f"\n   Objetivo: {b.objetivo}"
        )
    lineas.append(f"Total: {plan.total} min")
    if plan.justificacion:
        lineas.append(f"\n{plan.justificacion}")
    return "\n".join(lineas)
