"""Pruebas del zoo sin interfaz.

Comprueba las reglas (un animal por asignatura, crecer y decrecer, niveles),
guardar y cargar, el paso desde la pecera y que se dibujan los 10 recintos.
Con --svg, guarda una vista previa de cada recinto.

Uso:  python -m studymate.gamificacion.pruebas.prueba_zoo [--svg carpeta]
"""

import argparse
import json
import tempfile
from pathlib import Path

from studymate.gamificacion import pecera as pc
from studymate.gamificacion import zoo as z
from studymate.gamificacion.escena import escena_a_svg
from studymate.gamificacion.escena_zoo import ALTO, ANCHO, construir_recinto


def ok(cond: bool, texto: str) -> None:
    assert cond, texto
    print(f"  ✓ {texto}")


def falla(funcion, texto: str) -> None:
    try:
        funcion()
    except z.ErrorZoo as error:
        print(f"  ✓ {texto} («{error}»)")
        return
    raise AssertionError(texto)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--svg", type=Path)
    args = p.parse_args()

    buena = pc.calificar(pc.ResumenSesion(3600, 3500))
    regular = pc.calificar(pc.ResumenSesion(3600, 2700, pausas_movil=1))
    mala = pc.calificar(pc.ResumenSesion(3600, 1500, pausas_movil=4))
    corta = pc.calificar(pc.ResumenSesion(3600, 60))

    print("Asignaturas y animales")
    zoo = z.Zoo()
    zoo.anadir("Matemáticas", "leon")
    zoo.anadir("  Diseño   de Sistemas Interactivos ", "pez")
    ok(zoo.asignaturas == ["Matemáticas", "Diseño de Sistemas Interactivos"], "se añaden (limpiando espacios)")
    falla(lambda: zoo.anadir("Física", "leon"), "un animal solo puede ser de una asignatura")
    falla(lambda: zoo.anadir("matemáticas", "rana"), "no se repite una asignatura")
    falla(lambda: zoo.anadir("  ", "rana"), "hace falta el nombre")
    falla(lambda: zoo.anadir("Física", "dragón"), "solo los 10 animales")
    ok(zoo.dueno("pez") == "Diseño de Sistemas Interactivos" and len(zoo.especies_libres()) == 8,
       "se sabe qué animales quedan libres")
    otro = z.Zoo()
    for i, especie in enumerate(z.ANIMALES):
        otro.anadir(f"Asignatura {i}", especie)
    ok(len(otro.recintos) == 10 and not otro.especies_libres(), "caben 10 asignaturas, una por animal")

    print("\nTemas de cada asignatura")
    fis = otro.recinto("Asignatura 0")
    fis.anadir_tema("  Cinemática ")
    fis.anadir_tema("Dinámica")
    ok(fis.temas == ["Cinemática", "Dinámica"], "se añaden temas a una asignatura")
    falla(lambda: fis.anadir_tema("cinemática"), "no se repite un tema")
    falla(lambda: fis.anadir_tema(" "), "hace falta el nombre del tema")
    fis.quitar_tema("Cinemática")
    ok(fis.temas == ["Dinámica"], "se puede quitar un tema")
    con_temas = z.Zoo()
    r_temas = con_temas.anadir("Química", "rana", ["Átomos", "", "átomos", "Enlaces"])
    ok(r_temas.temas == ["Átomos", "Enlaces"], "al crear la asignatura se pueden dar sus temas")

    print("\nCrecer y decrecer")
    r = zoo.recinto("matemáticas")
    ok(r.salud == 50 and r.animales == 2 and r.nivel == 1, "un recinto nuevo empieza con 2 animales y 50 de salud")
    cambios = z.aplicar_sesion(zoo, "Matemáticas", buena, minutos=58)
    ok(r.animales == 3 and r.salud == 65 and "nivel 2" in cambios[0], "muy buena: +1 animal y +15; con 3, nivel 2")
    z.aplicar_sesion(zoo, "Matemáticas", buena, minutos=55)
    z.aplicar_sesion(zoo, "Matemáticas", buena, minutos=55)
    ok(r.animales == 5 and r.racha_buenas == 3, "racha de 3 muy buenas")
    z.aplicar_sesion(zoo, "Matemáticas", regular, minutos=45)
    ok(r.animales == 5 and r.racha_buenas == 0, "regular: igual, pero corta la racha")
    z.aplicar_sesion(zoo, "Matemáticas", mala, minutos=25)
    ok(r.animales == 4 and r.salud == 75, "mala: se va un animal y −20 de salud")
    ok(zoo.recinto("Diseño de Sistemas Interactivos").animales == 2, "solo cambia el recinto de esa asignatura")
    z.aplicar_sesion(zoo, "Matemáticas", corta, minutos=1)
    ok(len(r.sesiones) == 5, "una sesión demasiado corta no cuenta")
    ok(r.minutos == 238 and [s["calificacion"] for s in r.sesiones][-1] == "mala", "guarda el avance de cada sesión")
    ok("no tiene recinto" in z.aplicar_sesion(zoo, "Química", buena)[0], "asignatura sin recinto: no cambia nada")
    for _ in range(12):
        z.aplicar_sesion(zoo, "Matemáticas", buena)
    ok(r.animales == z.MAX_ANIMALES and r.salud == 100, f"como mucho {z.MAX_ANIMALES} animales")

    print("\nGuardar, cargar y pasar desde la pecera")
    with tempfile.TemporaryDirectory() as tmp:
        carpeta = Path(tmp)
        ok(z.cargar(carpeta).recintos == [], "sin archivos, zoo vacío")
        (carpeta / z.ARCHIVO).write_text(json.dumps({"recintos": [
            {"asignatura": "Física", "especie": "buho", "salud": 60, "animales": 0}]}), encoding="utf-8")
        viejo = z.cargar(carpeta).recinto("Física")
        ok(viejo.salud == 50 and viejo.animales == 2, "los recintos de antes sin sesiones se ponen como los nuevos")
        (carpeta / z.ARCHIVO).unlink()
        pecera = pc.EstadoPecera.nueva()
        pecera.salud, pecera.racha_buenas = 85, 2
        pecera.peces += [pc.Pez(*pc.ESPECIES[0], nacido="2026-11-20")] * 2
        pc.guardar(pecera, carpeta)
        migrado = z.cargar(carpeta)
        ok(migrado.recintos[0].asignatura == "General" and migrado.recintos[0].especie == "pez"
           and migrado.recintos[0].animales == 5 and migrado.recintos[0].salud == 85,
           "la pecera que había pasa a ser el acuario de «General»")
        zoo.renombrar("  El zoo   de Lucía ")
        falla(lambda: zoo.renombrar(" "), "el zoo necesita nombre")
        zoo.recinto("Matemáticas").ultimo_cuestionario = {"tiempo_disponible_min": 90}
        z.guardar(zoo, carpeta)
        cargado = z.cargar(carpeta)
        ok(cargado == zoo and cargado.nombre == "El zoo de Lucía", "se guarda y se carga igual, con su nombre")
        ok(cargado.recinto("Diseño de Sistemas Interactivos").ultimo_cuestionario == {},
           "el último cuestionario es de cada asignatura")
        (carpeta / z.ARCHIVO).write_text(json.dumps({"recintos": [{"asignatura": "X", "especie": "dragón"}]}))
        ok(z.cargar(carpeta).recintos == [], "ignora animales que no existen")
        (carpeta / z.ARCHIVO).write_text("{roto")
        ok(z.cargar(carpeta).recintos == [], "si el archivo está roto, no falla")

    print("\nDibujo de los 10 recintos")
    for i, especie in enumerate(z.ANIMALES):
        recinto = z.Recinto(f"A{i}", especie, salud=[95, 60, 25][i % 3], animales=i % 10)
        figuras = construir_recinto(recinto, t=1.0)
        assert len(figuras) > 3
        if args.svg:
            args.svg.mkdir(parents=True, exist_ok=True)
            (args.svg / f"recinto_{especie}.svg").write_text(
                escena_a_svg(figuras, ANCHO, ALTO, vista=(ANCHO, ALTO), radio=18), encoding="utf-8")
    ok(True, "se dibujan todos" + (f" (vistas previas en {args.svg})" if args.svg else ""))
    print("\nTodas las pruebas pasan.")


if __name__ == "__main__":
    main()
