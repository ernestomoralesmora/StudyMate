"""Pruebas sin interfaz del registro y el inicio de sesión.

Uso:  python -m studymate.pruebas.prueba_usuarios
"""

import json
import tempfile
from pathlib import Path

from studymate import usuarios as us


def ok(cond: bool, texto: str) -> None:
    assert cond, texto
    print(f"  ✓ {texto}")


def falla(funcion, texto: str) -> None:
    try:
        funcion()
    except us.ErrorUsuario as error:
        print(f"  ✓ {texto} («{error}»)")
        return
    raise AssertionError(texto)


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        # Datos de antes de que hubiera usuarios.
        (base / "zoo.json").write_text('{"recintos": []}', encoding="utf-8")
        (base / "historial.json").write_text("[]", encoding="utf-8")

        print("Registro")
        falla(lambda: us.registrar("ab", "Lucía", "secreto1", "secreto1", base=base), "usuario demasiado corto")
        falla(lambda: us.registrar("lucía g", "Lucía", "secreto1", "secreto1", base=base), "sin espacios ni tildes")
        falla(lambda: us.registrar("lucia", "Lucía", "12345", "12345", base=base), "contraseña de 6 o más")
        falla(lambda: us.registrar("lucia", "Lucía", "secreto1", "secreto2", base=base), "las contraseñas deben coincidir")
        falla(lambda: us.registrar("lucia", "  ", "secreto1", "secreto1", base=base), "hace falta el nombre")
        lucia = us.registrar(" Lucia ", "Lucía  García", "secreto1", "secreto1", "2º Informática", base=base)
        ok(lucia.usuario == "lucia" and lucia.nombre == "Lucía García", "se registra (usuario en minúsculas)")
        guardado = json.loads((base / us.ARCHIVO).read_text(encoding="utf-8"))[0]
        ok("secreto1" not in json.dumps(guardado) and len(guardado["huella"]) == 64 and guardado["sal"],
           "la contraseña no se guarda: solo su huella con sal")
        ok((lucia.carpeta(base) / "zoo.json").exists() and not (base / "zoo.json").exists(),
           "los datos de antes pasan a la primera cuenta")
        falla(lambda: us.registrar("LUCIA", "Otra", "secreto1", "secreto1", base=base), "no se repite el usuario")
        javier = us.registrar("javier", "Javier", "tablet123", "tablet123", base=base)
        ok(not (javier.carpeta(base) / "zoo.json").exists(), "la segunda cuenta empieza vacía")

        print("\nInicio de sesión")
        ok(us.iniciar_sesion("LUCIA", "secreto1", base=base).nombre == "Lucía García", "entra con su contraseña")
        falla(lambda: us.iniciar_sesion("lucia", "secreto2", base=base), "contraseña incorrecta")
        falla(lambda: us.iniciar_sesion("nadie", "secreto1", base=base), "usuario que no existe (mismo mensaje)")
        ok(lucia.carpeta(base) != javier.carpeta(base), "cada usuario tiene su carpeta de datos")
        (base / us.ARCHIVO).write_text("{roto", encoding="utf-8")
        ok(us.cargar_usuarios(base) == [], "si el archivo está roto, no falla")
    print("\nTodas las pruebas pasan.")


if __name__ == "__main__":
    main()
