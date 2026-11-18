import json

from groq import Groq


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


def consultar_groq(peticion: str) -> str:
    cliente = Groq()
    respuesta = cliente.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[{"role": "user", "content": peticion}],
        temperature=0.2,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "test_studymate",
                "strict": True,
                "schema": ESQUEMA_TEST,
            },
        },
    )

    contenido = respuesta.choices[0].message.content
    if not contenido or not contenido.strip():
        raise ValueError("Groq devolvió una respuesta vacía.")

    datos = json.loads(contenido)
    return json.dumps(datos["preguntas"], ensure_ascii=False)