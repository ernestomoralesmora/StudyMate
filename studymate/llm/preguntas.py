"""Preguntas tipo test con el LLM (RF de los tests: 10 preguntas, opciones A, B y C).

El modelo a veces devuelve alguna pregunta mal formada (dos opciones iguales,
cuatro opciones, sin explicación…). En vez de tirar el test entero:

1. Se arreglan los fallos sin importancia (espacios, opciones que empiezan por «A.»).
2. Las preguntas que siguen mal se descartan.
3. Si faltan preguntas, se piden solo las que faltan (como mucho MAX_INTENTOS veces).

Solo si tras esos intentos no hay NUM_PREGUNTAS válidas, se avisa del error.
"""

import json
import re
from collections.abc import Callable

NUM_PREGUNTAS = 10  # preguntas del test de cada bloque
MAX_INTENTOS = 3    # peticiones al modelo como mucho, contando la primera
LETRAS = ("A", "B", "C")

_PREFIJO = re.compile(r"^\s*[\(\[]?[ABCabc][\)\]\.:\-]\s+")  # «A. », «b) », «(C) »…


def _texto(valor) -> str:
    return " ".join(valor.split()) if isinstance(valor, str) else ""


def normalizar(pregunta) -> dict | None:
    """Devuelve la pregunta arreglada o None si no se puede usar."""
    if not isinstance(pregunta, dict):
        return None
    enunciado, explicacion = _texto(pregunta.get("enunciado")), _texto(pregunta.get("explicacion"))
    opciones = pregunta.get("opciones")
    correcta = _texto(pregunta.get("correcta")).upper()[:1]
    if not enunciado or not explicacion or correcta not in LETRAS:
        return None
    if not isinstance(opciones, list) or len(opciones) != 3:
        return None
    opciones = [_PREFIJO.sub("", _texto(o)) for o in opciones]
    if not all(opciones) or len({o.casefold() for o in opciones}) != 3:
        return None  # dos opciones iguales: no se sabría cuál es la buena
    if enunciado.casefold() in {o.casefold() for o in opciones}:
        return None
    return {"enunciado": enunciado, "opciones": opciones, "correcta": correcta,
            "explicacion": explicacion}


def _peticion(apuntes: str, cuantas: int, ya_hechas: list[dict]) -> str:
    peticion = (
        f"Genera {cuantas} preguntas tipo test basadas únicamente en los apuntes. "
        'Devuelve un objeto JSON con una clave "preguntas" que contiene el array, sin Markdown. '
        "Cada pregunta debe tener 'enunciado', 'opciones' (EXACTAMENTE tres textos, todos "
        "distintos entre sí, en orden A, B y C, sin poner la letra delante), 'correcta' "
        "(A, B o C) y 'explicacion'. Solo una opción es correcta. "
        "La explicación debe justificar la respuesta con el contenido de los apuntes.\n\n"
        "La opción correcta y su explicación deben coincidir exactamente. "
        "Respeta distinciones como antes, durante y después. "
        "Reparte las preguntas entre distintos conceptos de los apuntes.\n\n"
    )
    if ya_hechas:
        peticion += ("No repitas estas preguntas, que ya están hechas:\n"
                     + "\n".join(f"- {p['enunciado']}" for p in ya_hechas) + "\n\n")
    return peticion + f"APUNTES:\n{apuntes}"


def generar_preguntas(
    apuntes: str,
    consultar_modelo: Callable[[str], str],
) -> list[dict]:
    """Genera y valida NUM_PREGUNTAS preguntas sobre unos apuntes."""
    apuntes = apuntes.strip()
    if not apuntes:
        raise ValueError("El bloque de apuntes está vacío.")

    validas: list[dict] = []
    ultimo_fallo = ""
    for _ in range(MAX_INTENTOS):
        faltan = NUM_PREGUNTAS - len(validas)
        try:
            recibidas = json.loads(consultar_modelo(_peticion(apuntes, faltan, validas)))
        except json.JSONDecodeError:
            ultimo_fallo = "el modelo no devolvió un JSON válido"
            continue
        if not isinstance(recibidas, list):
            ultimo_fallo = "el modelo no devolvió una lista de preguntas"
            continue
        vistas = {p["enunciado"].casefold() for p in validas}
        for pregunta in recibidas:
            buena = normalizar(pregunta)
            if buena is None:
                ultimo_fallo = "alguna pregunta venía mal formada"
            elif buena["enunciado"].casefold() not in vistas:
                validas.append(buena)
                vistas.add(buena["enunciado"].casefold())
        if len(validas) >= NUM_PREGUNTAS:
            return validas[:NUM_PREGUNTAS]

    raise ValueError(f"El asistente solo ha preparado bien {len(validas)} de {NUM_PREGUNTAS} "
                     f"preguntas ({ultimo_fallo or 'faltaban preguntas'}).")
