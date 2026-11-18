"""Prueba real: cuestionario por consola + plan con Groq.

Necesita la variable de entorno GROQ_API_KEY y conexión a internet.
Uso:  python -m studymate.llm.pruebas.prueba_plan_groq [--apuntes fichero.txt]
"""

import argparse
from pathlib import Path

from studymate.llm.cuestionario import preguntar_por_consola
from studymate.llm.plan import describir_plan, generar_plan


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apuntes", type=Path, help="fichero de texto con los apuntes")
    args = parser.parse_args()
    apuntes = args.apuntes.read_text(encoding="utf-8") if args.apuntes else None

    perfil = preguntar_por_consola()
    print("\nPreparando tu plan...\n")
    plan = generar_plan(perfil, apuntes=apuntes)
    origen = "Groq" if plan.origen == "llm" else "plan básico (sin LLM)"
    print(f"--- Plan propuesto ({origen}) ---\n")
    print(describir_plan(plan))


if __name__ == "__main__":
    main()
