"""Pruebas sin conexión de la lectura y selección de apuntes.

Uso:  python -m studymate.llm.pruebas.prueba_apuntes [archivo.pdf ...]
Con archivos, además enseña cuánto texto se saca de cada uno.
"""

import sys
import tempfile
import zipfile
from pathlib import Path

from studymate.llm.apuntes import (BibliotecaApuntes, ErrorApuntes, fragmentos, leer_archivo, para_test,
                                   seleccionar, unir)


def ok(cond: bool, texto: str) -> None:
    assert cond, texto
    print(f"  ✓ {texto}")


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "a.txt").write_text("Tema 1. La usabilidad mide lo fácil que es usar un sistema.\n" * 3,
                                   encoding="utf-8")
        ok("usabilidad" in leer_archivo(tmp / "a.txt"), "lee .txt")
        doc = tmp / "b.docx"
        with zipfile.ZipFile(doc, "w") as z:
            z.writestr("word/document.xml",
                       '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                       "<w:body><w:p><w:r><w:t>El prototipado rápido permite probar ideas</w:t></w:r></w:p>"
                       "<w:p><w:r><w:t>antes de programar la aplicación completa.</w:t></w:r></w:p>"
                       "</w:body></w:document>")
        ok("prototipado" in leer_archivo(doc), "lee .docx sin librerías extra")
        try:
            leer_archivo(tmp / "c.png")
            ok(False, "rechaza otros formatos")
        except ErrorApuntes:
            ok(True, "rechaza otros formatos con un mensaje claro")
        (tmp / "vacio.txt").write_text("  ", encoding="utf-8")
        try:
            leer_archivo(tmp / "vacio.txt")
            ok(False, "avisa si no hay texto")
        except ErrorApuntes as e:
            ok("escaneado" in str(e), "avisa si no hay texto (PDF escaneado)")

    print("\nApuntes guardados por asignatura")
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "tema1.txt").write_text("Derivadas: la pendiente de la recta tangente. " * 3, encoding="utf-8")
        (tmp / "tema2.txt").write_text("Integrales: el área bajo la curva de una función. " * 3, encoding="utf-8")
        usuario = tmp / "usuario"
        mates = BibliotecaApuntes(usuario, "Matemáticas")
        d1 = mates.anadir(tmp / "tema1.txt")
        d2 = mates.anadir(tmp / "tema2.txt")
        ok([d.nombre for d in mates.documentos()] == ["tema1.txt", "tema2.txt"], "se guardan los subidos")
        ok(not list((mates.carpeta).glob("*.pdf")) and (mates.carpeta / f"{d1.id}.txt").exists(),
           "solo se guarda el texto, no el archivo")
        ok(BibliotecaApuntes(usuario, "Lengua").documentos() == [], "cada asignatura tiene los suyos")
        ok(BibliotecaApuntes(usuario, "matemáticas").documentos() != [], "misma asignatura aunque cambien mayúsculas")
        ok([n for n, _ in mates.elegidos([d2.id])] == ["tema2.txt"], "se eligen los que se quieren usar")
        (tmp / "tema1.txt").write_text("Derivadas (versión nueva con más ejemplos). " * 3, encoding="utf-8")
        mates.anadir(tmp / "tema1.txt")
        ok(len(mates.documentos()) == 2 and "nueva" in mates.elegidos([d.id for d in mates.documentos()])[1][1],
           "subir otra vez el mismo nombre lo sustituye")
        mates.quitar(d2.id)
        ok([d.nombre for d in mates.documentos()] == ["tema1.txt"], "se puede quitar uno")

    temario = "\n\n".join(
        [f"Tema {i}. " + ("Relleno sobre otras cosas distintas. " * 30) for i in range(1, 30)]
        + ["Tema 30. La heurística de Nielsen de visibilidad del estado del sistema dice que "
           "el usuario debe saber siempre qué está pasando. " * 4]
    )
    ok(len(fragmentos(temario)) > 20, f"trocea un temario largo ({len(temario)} caracteres)")
    corto = para_test(temario, "Heurísticas de Nielsen", "Visibilidad del estado del sistema")
    ok(len(corto) <= 6000 and "Nielsen" in corto, "para el test del bloque elige la parte del tema")
    ok(seleccionar("poco texto", "x", 6000) == "poco texto", "si cabe entero, va entero")
    ok(unir("notas mías", [("t1.pdf", "texto")]).startswith("notas mías\n\n=== t1.pdf ==="), "junta todo")

    for ruta in sys.argv[1:]:
        try:
            texto = leer_archivo(ruta)
            print(f"\n{ruta}: {len(texto)} caracteres. Empieza así:\n{texto[:300]}")
        except ErrorApuntes as e:
            print(f"\n{e}")
    print("\nTodas las pruebas pasan.")


if __name__ == "__main__":
    main()
