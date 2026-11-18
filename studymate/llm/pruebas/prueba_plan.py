"""Pruebas del cuestionario y del plan SIN conexión (respuestas de Groq inventadas).

Uso:  python -m studymate.llm.pruebas.prueba_plan
"""

from studymate.llm.cliente_groq import ErrorConexionLLM
from studymate.llm.cuestionario import PerfilSesion
from studymate.llm.plan import (
    MINUTOS_TEST,
    describir_plan,
    duracion_maxima_bloque,
    generar_plan,
    plan_basico,
    validar_plan,
)


def perfil(**cambios) -> PerfilSesion:
    datos = dict(
        tiempo_disponible_min=60,
        concentracion_min=20,
        cansancio=2,
        temas=["Tema 1", "Tema 2"],
    )
    datos.update(cambios)
    return PerfilSesion(**datos)


def bloque(tema, estudio, descanso=5, test=MINUTOS_TEST):
    return {"tema": tema, "objetivo": f"Entender {tema}", "minutos_estudio": estudio,
            "minutos_test": test, "minutos_descanso": descanso}


def comprobar(condicion: bool, mensaje: str) -> None:
    assert condicion, mensaje
    print(f"  ✓ {mensaje}")


def main() -> None:
    print("Cuestionario")
    try:
        perfil(tiempo_disponible_min=5)
        comprobar(False, "rechaza un tiempo disponible de 5 min")
    except ValueError:
        comprobar(True, "rechaza un tiempo disponible de 5 min")
    try:
        perfil(temas=["  ", ""])
        comprobar(False, "rechaza una sesión sin temas")
    except ValueError:
        comprobar(True, "rechaza una sesión sin temas")
    comprobar(perfil(dispositivos_permitidos=["tablet"]).clases_permitidas == {"cell phone"},
              "la tablet permitida se traduce a la clase COCO de la detección")
    comprobar(duracion_maxima_bloque(perfil(cansancio=5)) == 14,
              "muy cansado: bloques de 14 min en vez de 20")

    print("\nPlan válido del LLM")
    p = perfil()
    valido = {"bloques": [bloque("Tema 1", 20), bloque("Tema 2", 20, 0)],
              "justificacion": "Dos bloques de 20 min."}
    plan = generar_plan(p, lambda _: valido)
    comprobar(plan.origen == "llm" and plan.total == 55, "se acepta tal cual (55 de 60 min)")

    print("\nPlan inválido que el LLM corrige al segundo intento")
    respuestas = iter([
        {"bloques": [bloque("Tema 1", 45), bloque("Tema 2", 30, 0)], "justificacion": "x"},
        valido,
    ])
    peticiones = []
    plan = generar_plan(p, lambda pet: (peticiones.append(pet), next(respuestas))[1])
    comprobar(plan.origen == "llm", "acaba aceptando el plan corregido")
    comprobar("Corrígelo" in peticiones[1], "la segunda petición incluye los errores del primero")

    print("\nPlan inválido dos veces")
    malo = {"bloques": [bloque("Tema 1", 90, 0)], "justificacion": "x"}
    plan = generar_plan(p, lambda _: malo)
    comprobar(plan.origen == "basico" and plan.avisos, "se usa el plan básico con un aviso")

    print("\nSin conexión")
    def sin_red(_):
        raise ErrorConexionLLM("sin red")
    plan = generar_plan(p, sin_red)
    comprobar(plan.origen == "basico" and "conexión" in plan.avisos[0],
              "se usa el plan básico y se avisa de la falta de conexión (RNF8)")

    print("\nPlan básico en varios casos")
    for t, c, k in [(60, 20, 2), (25, 25, 1), (120, 45, 4), (10, 5, 3), (480, 120, 5), (37, 13, 3)]:
        pb = plan_basico(perfil(tiempo_disponible_min=t, concentracion_min=c, cansancio=k))
        errores = validar_plan(pb, perfil(tiempo_disponible_min=t, concentracion_min=c, cansancio=k))
        comprobar(not errores, f"{t} min, concentración {c}, cansancio {k}: "
                               f"{len(pb.bloques)} bloques, {pb.total} min, válido")

    print("\nEjemplo de plan básico (60 min, 20 min de concentración):\n")
    print(describir_plan(plan_basico(p)))
    print("\nTodas las pruebas pasan.")


if __name__ == "__main__":
    main()
