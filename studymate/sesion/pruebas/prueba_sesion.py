"""Pruebas sin cámara ni interfaz de la sesión y el historial.

Uso:  python -m studymate.sesion.pruebas.prueba_sesion
"""

import tempfile
from datetime import date
from pathlib import Path

from studymate.gamificacion import pecera as pc
from studymate.llm.plan import Bloque, Plan
from studymate.sesion.controlador import ControladorSesion, Fase, que_repasar
from studymate.sesion.historial import (RegistroSesion, cargar_historial, estadisticas,
                                        guardar_registro, minutos_por_dia)
from studymate.vision.estados import Estado

E_, A_, M_, D_ = Estado.ESTUDIANDO, Estado.AUSENTE, Estado.USANDO_MOVIL, Estado.DUDOSO


def ok(cond: bool, texto: str) -> None:
    assert cond, texto
    print(f"  ✓ {texto}")


def plan_de_prueba() -> Plan:
    return Plan([
        Bloque("Tema 1", "Entender A", 25, 5, 5),
        Bloque("Tema 2", "Entender B", 20, 5, 5),
    ], "Prueba", origen="basico")


def prueba_controlador() -> None:
    print("Controlador de la sesión")
    c = ControladorSesion(plan_de_prueba(), con_test=True)
    ok(c.fase == Fase.ESTUDIO and c.objetivo_bloque_s == 25 * 60, "empieza estudiando el bloque 1 (25 min)")
    c.actualizar(A_, 0)  # aún no se ha sentado
    c.actualizar(E_, 10)
    ok(c.pausas_ausente == 0, "la ausencia del principio no cuenta")
    c.actualizar(M_, 100); c.actualizar(M_, 100); c.actualizar(E_, 100)
    c.actualizar(A_, 200); c.actualizar(E_, 200); c.actualizar(D_, 210); c.actualizar(E_, 220)
    ok(c.pausas_movil == 1 and c.pausas_ausente == 1, "cuenta 1 vez el móvil y 1 ausencia")
    ok(round(c.restante_bloque_s) == 25 * 60 - 220, "lo que queda depende del tiempo estudiado de verdad")
    cambio = c.actualizar(E_, 25 * 60)
    ok(cambio and c.fase == Fase.TEST, "al estudiar 25 min pasa al test")
    c.actualizar(M_, 9999)
    ok(c.pausas_movil == 1 and c.estudiado_s == 25 * 60, "durante el test no cuenta nada")
    c.terminar_test(4, 5)
    ok(c.fase == Fase.DESCANSO, "después del test, descanso")
    c.empezar_descanso(1000.0)
    ok(c.restante_descanso(1060.0) == 4 * 60, "el descanso cuenta con el reloj")
    c.terminar_descanso()
    ok(c.fase == Fase.ESTUDIO and c.indice == 1 and c.restante_bloque_s == 20 * 60, "bloque 2")
    c.actualizar(E_, 25 * 60 + 20 * 60)
    c.terminar_test(5, 5)
    ok(c.fase == Fase.TERMINADA, "tras el último test no hay descanso: termina")
    r = c.resumen()
    ok(r.planificado_s == 45 * 60 and r.estudiado_s == 45 * 60 and r.test_aciertos == 9 and r.test_total == 10,
       "resumen para la pecera")
    ok(pc.calificar(r).calificacion == pc.Calificacion.MUY_BUENA, "una sesión así es muy buena")
    ok(c.bloques_completados == 2, "2 de 2 bloques completados")

    sin_test = ControladorSesion(plan_de_prueba(), con_test=False)
    sin_test.actualizar(E_, 25 * 60)
    ok(sin_test.fase == Fase.DESCANSO, "sin test, del estudio pasa al descanso")

    rapido = ControladorSesion(plan_de_prueba(), segundos_por_minuto=10)
    ok(rapido.objetivo_bloque_s == 250, "modo prueba: 25 min del plan son 250 s")
    rapido.actualizar(E_, 125)
    rapido.terminar_antes()
    r = rapido.resumen()
    ok(rapido.terminada_antes and r.planificado_s == 45 * 60 and r.estudiado_s == 12.5 * 60,
       "terminar antes: la nota se calcula sobre todo el plan (escalado a minutos reales)")
    ok(rapido.bloques_completados == 0, "ningún bloque completo")

    preguntas = [{"enunciado": "¿1+1?", "correcta": "B", "explicacion": "Es 2."},
                 {"enunciado": "¿2+2?", "correcta": "A", "explicacion": "Es 4."}]
    ok(que_repasar(preguntas, ["B", "C"]) == ["¿2+2? → Es 4."], "qué repasar: solo lo fallado")


def prueba_historial() -> None:
    print("\nHistorial")
    with tempfile.TemporaryDirectory() as tmp:
        carpeta = Path(tmp)
        ok(cargar_historial(carpeta) == [], "sin historial, lista vacía")
        for fecha, minutos, prueba in [("2026-11-20T10:00", 50, False), ("2026-11-24T18:00", 40, False),
                                       ("2026-11-25T09:00", 30, False), ("2026-11-25T11:00", 2, True)]:
            guardar_registro(RegistroSesion(["T"], 60, minutos, 1, 0, "regular", 70, 1, 2,
                                            test_aciertos=3, test_total=5, modo_prueba=prueba, fecha=fecha), carpeta)
        h = cargar_historial(carpeta)
        ok(len(h) == 4 and h[-1].modo_prueba, "se guardan en orden")
        e = estadisticas(h, hoy=date(2026, 11, 25))
        ok(e["sesiones"] == 3 and e["minutos_total"] == 120 and e["minutos_semana"] == 120,
           "estadísticas sin contar el modo prueba")
        ok(e["acierto_test"] == 60, "acierto medio en los tests")
        dias = minutos_por_dia(h, 7, hoy=date(2026, 11, 25))
        ok(len(dias) == 7 and dias[-1] == (date(2026, 11, 25), 30) and dias[-2][1] == 40, "minutos por día")
        (carpeta / "historial.json").write_text("{roto", encoding="utf-8")
        ok(cargar_historial(carpeta) == [], "si el archivo está roto, no falla")


if __name__ == "__main__":
    prueba_controlador()
    prueba_historial()
    print("\nTodas las pruebas pasan.")
