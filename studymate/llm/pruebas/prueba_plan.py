"""Pruebas del cuestionario y del plan SIN conexión (respuestas de Groq inventadas).

Uso:  python -m studymate.llm.pruebas.prueba_plan
"""

from studymate.llm.cliente_groq import ErrorConexionLLM
from studymate.llm.cuestionario import PerfilSesion
from studymate.llm.plan import (
    MINUTOS_TEST,
    _a_plan,
    estudio_optimo,
    describir_plan,
    duracion_maxima_bloque,
    generar_plan,
    plan_basico,
    validar_plan,
)


def perfil(**cambios) -> PerfilSesion:
    datos = dict(
        tiempo_disponible_min=70,
        concentracion_min=20,
        cansancio=2,
        temas=["Tema 1", "Tema 2"],
        con_test=True,
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
    total = 40 + 2 * MINUTOS_TEST + 5
    comprobar(plan.origen == "llm" and plan.total == total, f"se acepta tal cual ({total} de 70 min)")

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
    comprobar(plan.origen == "basico" and "sin red" in plan.avisos[0],
              "se usa el plan básico y el aviso explica el motivo (RNF8)")

    print("\nPlan básico en varios casos (con y sin test)")
    for t, c, k in [(60, 20, 2), (25, 25, 1), (120, 45, 4), (10, 5, 3), (480, 120, 5),
                    (37, 13, 3), (20, 10, 1), (100, 20, 1)]:
        for con_test in (True, False):
            pf = perfil(tiempo_disponible_min=t, concentracion_min=c, cansancio=k,
                        con_test=con_test)
            pb = plan_basico(pf)
            errores = validar_plan(pb, pf)
            comprobar(not errores and pb.total <= t,
                      f"{t} min, concentración {c}, cansancio {k}, "
                      f"{'con' if con_test else 'sin'} test: {len(pb.bloques)} bloques, "
                      f"{pb.total} min, válido {errores or ''}")

    print("\nCaso de Pablo: 20 min, 10 de concentración, sin test")
    p20 = perfil(tiempo_disponible_min=20, concentracion_min=10, cansancio=1,
                 temas=["1", "2"], con_test=False)
    pb = plan_basico(p20)
    comprobar(sum(b.minutos_estudio for b in pb.bloques) == 17, "17 min de estudio en 20")

    print("\n70 min y 20 de concentración, con test: 2 bloques de 20 mejor que 3 de 12")
    pb = plan_basico(perfil())
    comprobar([b.minutos_estudio for b in pb.bloques] == [20, 20], "2 bloques de 20 min (40 de estudio)")
    print(describir_plan(pb))

    print("\nCaso de Pablo: 100 min, 20 de concentración, 8 temas, con test")
    p8 = perfil(tiempo_disponible_min=100, concentracion_min=20, cansancio=1,
                temas=[str(i) for i in range(1, 9)])
    pb = plan_basico(p8)
    comprobar(not validar_plan(pb, p8), "el plan es válido")
    cubiertos = {t.strip() for b in pb.bloques for t in b.tema.split(",")}
    comprobar(cubiertos == set(p8.temas), "están los 8 temas")
    estudio = sum(b.minutos_estudio for b in pb.bloques)
    comprobar(estudio == estudio_optimo(p8)[1], f"máximo tiempo de estudio posible: {estudio} min de 100")
    print(describir_plan(pb))

    print("\nPlan del LLM que desaprovecha tiempo de estudio")
    corto = {"bloques": [bloque("1, 2", 10, 0, test=0)], "justificacion": "x"}
    comprobar(bool(validar_plan(_a_plan(corto), p20)), "se rechaza (10 min de estudio cuando se pueden 17)")
    muchos = {"bloques": [bloque("Tema 1", 12), bloque("Tema 2", 12), bloque("Tema 2", 11, 0)],
              "justificacion": "x"}
    comprobar(bool(validar_plan(_a_plan(muchos), perfil())),
              "se rechazan 3 bloques de 12 min cuando caben 2 de 20")
    agrupado_mal = {"bloques": [bloque("1 y 2", 9, 3, test=0), bloque("1 y 2", 8, 0, test=0)],
                    "justificacion": "x"}
    comprobar(any("Faltan temas" in e for e in validar_plan(_a_plan(agrupado_mal), p20)),
              "«1 y 2» no cuenta como los temas 1 y 2 (deben ir separados por comas)")

    print("\nCuestionario por consola: dispositivos")
    import builtins
    from studymate.llm import cuestionario
    respuestas = iter(["q", "movil,patata", "Móvil, tablet"])
    original = builtins.input
    builtins.input = lambda _="": next(respuestas)
    try:
        comprobar(cuestionario._pedir_dispositivos() == ["movil", "tablet"],
                  "rechaza «q» y «movil,patata» y acepta «Móvil, tablet»")
    finally:
        builtins.input = original

    print("\nEjemplo de plan básico (70 min, 20 min de concentración):\n")
    print(describir_plan(plan_basico(p)))
    print("\nTodas las pruebas pasan.")


if __name__ == "__main__":
    main()
