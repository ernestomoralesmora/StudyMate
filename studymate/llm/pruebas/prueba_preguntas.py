"""Prueba de las preguntas tipo test sin conexión (el modelo es una función falsa).

    python -m studymate.llm.pruebas.prueba_preguntas
"""

import json

from studymate.llm.preguntas import NUM_PREGUNTAS, generar_preguntas, normalizar


def ok(condicion, texto):
    assert condicion, texto
    print(f"  ✓ {texto}")


def pregunta(i, opciones=None, correcta="A"):
    return {"enunciado": f"¿Pregunta {i}?", "opciones": opciones or [f"Sí {i}", f"No {i}", f"Quizá {i}"],
            "correcta": correcta, "explicacion": "Porque lo dicen los apuntes."}


def modelo(respuestas):
    """Devuelve las respuestas en orden y guarda las peticiones."""
    pedidas = []

    def consultar(peticion):
        pedidas.append(peticion)
        return json.dumps(respuestas[len(pedidas) - 1])
    return consultar, pedidas


def main():
    print("Arreglar o descartar preguntas")
    ok(normalizar(pregunta(1, ["A. Uno", "B) Dos", "(C) Tres"]))["opciones"] == ["Uno", "Dos", "Tres"],
       "se quita la letra que el modelo pone delante")
    ok(normalizar(pregunta(1, ["Uno", "uno ", "Dos"])) is None, "dos opciones iguales: se descarta")
    ok(normalizar(pregunta(1, ["Uno", "Dos", "Tres", "Cuatro"])) is None, "cuatro opciones: se descarta")
    ok(normalizar(pregunta(1, correcta="D")) is None, "la correcta tiene que ser A, B o C")
    ok(normalizar(pregunta(1, correcta=" b"))["correcta"] == "B", "«b» vale como B")

    print("\nPedir solo las que faltan")
    primera = [pregunta(i) for i in range(8)] + [pregunta(8, ["X", "X", "Y"]), pregunta(9, ["X", "Y"])]
    segunda = [pregunta(20), pregunta(21)]
    consultar, pedidas = modelo([primera, segunda])
    preguntas = generar_preguntas("Apuntes de física.", consultar)
    ok(len(preguntas) == NUM_PREGUNTAS and len(pedidas) == 2, "2 mal: se piden otras 2 y sale el test")
    ok("Genera 2 preguntas" in pedidas[1] and "¿Pregunta 0?" in pedidas[1], "y sin repetir las que ya hay")

    consultar, pedidas = modelo([[pregunta(i) for i in range(12)]])
    ok(len(generar_preguntas("Apuntes.", consultar)) == NUM_PREGUNTAS, "si sobran, se usan 10")

    malas = [pregunta(i, ["X", "X", "Y"]) for i in range(10)]
    consultar, pedidas = modelo([malas, malas, malas])
    try:
        generar_preguntas("Apuntes.", consultar)
        raise AssertionError("debería fallar")
    except ValueError as error:
        ok("0 de 10" in str(error) and len(pedidas) == 3, "si siempre vienen mal, avisa tras 3 intentos")
    print("\nTodas las pruebas pasan.")


if __name__ == "__main__":
    main()
