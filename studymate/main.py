"""Punto de entrada de StudyMate.

Por ahora (fase 1) lanza la prueba de cámara. En la fase 3 abrirá la interfaz PySide6.
Uso:  python -m studymate.main
"""

from studymate.vision.pruebas.prueba_camara import main

if __name__ == "__main__":
    main()
