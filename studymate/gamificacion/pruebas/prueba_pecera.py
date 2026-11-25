"""Pruebas de la pecera sin interfaz.

Comprueba la calificación y los cambios de la pecera, y guarda tres vistas
previas en SVG (buena, regular y mala) en la carpeta indicada.

Uso:  python -m studymate.gamificacion.pruebas.prueba_pecera [--svg carpeta]
"""

import argparse
import tempfile
from datetime import date, timedelta
from pathlib import Path

from studymate.gamificacion import pecera as pc
from studymate.gamificacion.escena import construir_escena, escena_a_svg


def comprobar(condicion: bool, texto: str) -> None:
    assert condicion, texto
    print(f"  ✓ {texto}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--svg", type=Path, help="carpeta donde guardar las vistas previas")
    args = parser.parse_args()

    print("Calificación de sesiones")
    buena = pc.calificar(pc.ResumenSesion(3600, 3420, pausas_movil=0, pausas_ausente=1))
    comprobar(buena.calificacion == pc.Calificacion.MUY_BUENA, f"95 % estudiado y 1 ausencia → muy buena ({buena.puntuacion})")
    regular = pc.calificar(pc.ResumenSesion(3600, 2700, pausas_movil=1, pausas_ausente=1))
    comprobar(regular.calificacion == pc.Calificacion.REGULAR, f"75 % y una vez el móvil → regular ({regular.puntuacion})")
    mala = pc.calificar(pc.ResumenSesion(3600, 1500, pausas_movil=4, pausas_ausente=2))
    comprobar(mala.calificacion == pc.Calificacion.MALA, f"42 % y el móvil 4 veces → mala ({mala.puntuacion})")
    movil = pc.calificar(pc.ResumenSesion(3600, 3600, pausas_movil=3))
    comprobar(movil.calificacion != pc.Calificacion.MUY_BUENA, "aunque se estudie todo, coger mucho el móvil impide la muy buena")
    corta = pc.calificar(pc.ResumenSesion(1800, 120))
    comprobar(not corta.cuenta, "una sesión de 2 minutos no cambia la pecera")
    con_test = pc.calificar(pc.ResumenSesion(3600, 2800, test_aciertos=5, test_total=5))
    sin_test = pc.calificar(pc.ResumenSesion(3600, 2800))
    comprobar(0 < con_test.puntuacion - sin_test.puntuacion <= pc.BONUS_TEST_MAX, "el test suma, pero poco (es opcional)")

    comprobar(buena.bien and not mala.bien, "autocrítica: la sesión buena tiene puntos fuertes")
    comprobar(any("móvil" in x for x in mala.mejorar), "autocrítica: la mala señala el móvil como lo que mejorar")
    texto = pc.mensaje(pc.EstadoPecera.nueva(), mala)
    comprobar("Qué puedo mejorar" in texto and "Racha" in texto, "el mensaje incluye racha y autocrítica")
    print("\n" + texto + "\n")

    print("\nCambios en la pecera")
    with tempfile.TemporaryDirectory() as tmp:
        carpeta = Path(tmp)
        e = pc.cargar(carpeta)
        comprobar(len(e.peces) == 3 and e.salud == pc.SALUD_INICIAL, "una pecera nueva empieza con 3 peces")
        hoy = date(2026, 11, 2)
        pc.aplicar_sesion(e, buena, hoy)
        comprobar(len(e.peces) == 4 and e.salud == pc.SALUD_INICIAL + 15, "sesión muy buena: +1 pez y +15 de salud")
        pc.aplicar_sesion(e, regular, hoy + timedelta(days=1))
        comprobar(len(e.peces) == 4 and e.salud == pc.SALUD_INICIAL + 15, "sesión regular: todo igual")
        cambios = pc.aplicar_sesion(e, mala, hoy + timedelta(days=2))
        comprobar(len(e.peces) == 3 and e.muertos_recientes == 1, "sesión mala: un pez muere y queda flotando")
        comprobar(e.racha_buenas == 0, "una sesión mala corta la racha")
        pc.aplicar_sesion(e, buena, hoy + timedelta(days=3))
        comprobar(e.muertos_recientes == 0, "la siguiente sesión muy buena limpia la pecera")
        antes = e.salud
        pc.aplicar_sesion(e, regular, hoy + timedelta(days=30))
        comprobar(e.salud == antes, "pasar días sin estudiar no cambia nada (la racha es por sesiones)")
        pc.aplicar_sesion(e, regular, hoy + timedelta(days=31))
        for i in range(3):
            pc.aplicar_sesion(e, buena, hoy + timedelta(days=21 + i))
        comprobar(any(p.especie == pc.ESPECIE_RARA[0] for p in e.peces), "tres muy buenas seguidas traen un pez dorado")
        comprobar(e.racha_buenas == 3, "racha de 3 sesiones muy buenas seguidas")
        comprobar("Pez dorado conseguido" in pc.texto_racha(e), "el mensaje cuenta la racha por sesiones")
        for i in range(20):
            pc.aplicar_sesion(e, buena, hoy + timedelta(days=30 + i))
        comprobar(len(e.peces) == pc.MAX_PECES and e.salud == 100, f"como máximo {pc.MAX_PECES} peces y 100 de salud")
        pc.guardar(e, carpeta)
        e2 = pc.cargar(carpeta)
        comprobar(e2 == e, "se guarda y se carga igual (data/pecera.json)")
        (carpeta / pc.ARCHIVO).write_text("{roto", encoding="utf-8")
        comprobar(len(pc.cargar(carpeta).peces) == 3, "si el archivo está estropeado, se empieza una pecera nueva")

    print("\nEscena")
    estados = {
        "buena": pc.EstadoPecera(salud=95, peces=[pc.Pez(*pc.ESPECIES[i % 6], nacido="2026-11-01") for i in range(10)]),
        "regular": pc.EstadoPecera(salud=50, peces=[pc.Pez(*pc.ESPECIES[i % 6], nacido="2026-11-01") for i in range(5)]),
        "mala": pc.EstadoPecera(salud=15, peces=[pc.Pez(*pc.ESPECIES[0], nacido="2026-11-01")], muertos_recientes=2),
    }
    for nombre, est in estados.items():
        figuras = construir_escena(est, t=1.3)
        comprobar(len(figuras) > 10, f"pecera {nombre}: {len(figuras)} figuras")
        if args.svg:
            args.svg.mkdir(parents=True, exist_ok=True)
            (args.svg / f"pecera_{nombre}.svg").write_text(escena_a_svg(figuras), encoding="utf-8")
    if args.svg:
        print(f"  Vistas previas guardadas en {args.svg}")
    print("\nTodas las pruebas pasan.")


if __name__ == "__main__":
    main()
