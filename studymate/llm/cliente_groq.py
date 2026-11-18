"""Llamadas a Groq con respuesta en JSON validado por esquema.

La clave se lee de la variable de entorno GROQ_API_KEY (nunca va en el código).
Al LLM solo se le envía texto: nunca imágenes de la cámara.
"""

import json
import os

MODELO = "openai/gpt-oss-120b"


class ErrorConexionLLM(RuntimeError):
    """No se ha podido hablar con Groq (sin clave, sin red o error del servicio)."""


ESQUEMA_TEST = {
    "type": "object",
    "properties": {
        "preguntas": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "enunciado": {"type": "string"},
                    "opciones": {"type": "array", "items": {"type": "string"}},
                    "correcta": {"type": "string", "enum": ["A", "B", "C"]},
                    "explicacion": {"type": "string"},
                },
                "required": ["enunciado", "opciones", "correcta", "explicacion"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["preguntas"],
    "additionalProperties": False,
}


def consultar_json(
    peticion: str,
    esquema: dict,
    nombre: str,
    temperatura: float = 0.2,
) -> dict:
    """Envía la petición a Groq y devuelve el JSON que cumple `esquema`.

    Lanza ErrorConexionLLM si no hay clave, no hay red o el servicio falla,
    y ValueError si la respuesta llega vacía o no es JSON.
    """
    try:
        from groq import Groq
    except ImportError as error:
        raise ErrorConexionLLM(
            "Falta la librería groq: ejecuta pip install -r requirements.txt"
        ) from error
    if not os.environ.get("GROQ_API_KEY"):
        raise ErrorConexionLLM(
            "No está definida la variable GROQ_API_KEY (tras el setx, cierra y "
            "vuelve a abrir VS Code)"
        )
    try:
        cliente = Groq()
        respuesta = cliente.chat.completions.create(
            model=MODELO,
            messages=[{"role": "user", "content": peticion}],
            temperature=temperatura,
            response_format={
                "type": "json_schema",
                "json_schema": {"name": nombre, "strict": True, "schema": esquema},
            },
        )
    except Exception as error:  # sin clave, sin red, límite de uso...
        raise ErrorConexionLLM(f"No se ha podido consultar a Groq: {error}") from error

    contenido = respuesta.choices[0].message.content
    if not contenido or not contenido.strip():
        raise ValueError("Groq devolvió una respuesta vacía.")
    return json.loads(contenido)


def consultar_groq(peticion: str) -> str:
    """Consulta para las preguntas tipo test (devuelve la lista como texto JSON)."""
    datos = consultar_json(peticion, ESQUEMA_TEST, "test_studymate")
    return json.dumps(datos["preguntas"], ensure_ascii=False)
