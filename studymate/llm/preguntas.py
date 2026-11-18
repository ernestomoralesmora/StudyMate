import json
from collections.abc import Callable


def generar_preguntas(
    apuntes: str,
    consultar_modelo: Callable[[str], str],
) -> list[dict]:
    """Genera y valida cinco preguntas sobre un bloque de apuntes."""
    apuntes = apuntes.strip()
    if not apuntes:
        raise ValueError("El bloque de apuntes está vacío.")

    peticion = (
        "Genera cinco preguntas tipo test basadas únicamente en los apuntes. "
        'Devuelve un objeto JSON con una clave "preguntas" que contiene el array, sin Markdown. '
        "Cada pregunta debe tener 'enunciado', 'opciones' (tres textos distintos "
        "en orden A, B y C), 'correcta' (A, B o C) y 'explicacion'. "
        "La explicación debe justificar la respuesta con el contenido del bloque.\n\n"
         "La opción correcta y su explicación deben coincidir exactamente. "
        "Respeta distinciones como antes, durante y después. "
        "Reparte las preguntas entre distintos conceptos del bloque.\n\n"
        f"APUNTES:\n{apuntes}"
    )

    try:
        preguntas = json.loads(consultar_modelo(peticion))
    except json.JSONDecodeError as error:
        raise ValueError("El modelo no devolvió un JSON válido.") from error

    if not isinstance(preguntas, list) or len(preguntas) != 5:
        raise ValueError("La respuesta debe contener exactamente cinco preguntas.")

    def tiene_texto(valor):
        return isinstance(valor, str) and bool(valor.strip())

    for numero, pregunta in enumerate(preguntas, start=1):
        if not isinstance(pregunta, dict):
            raise ValueError(f"Pregunta {numero}: formato incorrecto.")

        opciones = pregunta.get("opciones")
        if (
            not isinstance(opciones, list)
            or len(opciones) != 3
            or not all(tiene_texto(opcion) for opcion in opciones)
            or len({opcion.strip().casefold() for opcion in opciones}) != 3
        ):
            raise ValueError(f"Pregunta {numero}: hacen falta tres opciones distintas.")

        if pregunta.get("correcta") not in ("A", "B", "C"):
            raise ValueError(f"Pregunta {numero}: la respuesta debe ser A, B o C.")

        if not all(tiene_texto(pregunta.get(campo))
                   for campo in ("enunciado", "explicacion")):
            raise ValueError(f"Pregunta {numero}: falta el enunciado o la explicación.")

    return preguntas