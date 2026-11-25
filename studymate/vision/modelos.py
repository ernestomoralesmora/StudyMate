"""Rutas de los modelos de MediaPipe y descarga la primera vez que se usan.

Los modelos no se suben al repositorio (ver .gitignore).
Se puede lanzar la descarga a mano con:  python -m studymate.vision.modelos
"""

import urllib.request
from pathlib import Path

CARPETA = Path(__file__).resolve().parent / "modelos"
_BASE = "https://storage.googleapis.com/mediapipe-models/"

MODELOS = {
    "cara": (
        "blaze_face_short_range.tflite",
        _BASE + "face_detector/blaze_face_short_range/float16/latest/blaze_face_short_range.tflite",
    ),
    "manos": (
        "hand_landmarker.task",
        _BASE + "hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task",
    ),
    "objetos": (
        "efficientdet_lite0.tflite",
        _BASE + "object_detector/efficientdet_lite0/int8/latest/efficientdet_lite0.tflite",
    ),
    "objetos_preciso": (
        "efficientdet_lite2.tflite",
        _BASE + "object_detector/efficientdet_lite2/float32/latest/efficientdet_lite2.tflite",
    ),
    # YOLO26n exportado a ONNX (entrada 320x320). Va incluido en el repositorio
    # porque exportarlo requiere PyTorch; ver herramientas/exportar_yolo.py.
    "yolo": ("yolo26n_320.onnx", None),
    # YOLO26s (más grande, ~76 ms): en pruebas, todavía no va en el repositorio.
    "yolo_s": ("yolo26s_320.onnx", None),
    # En comparación (todavía no van en el repositorio):
    "yolo_s416": ("yolo26s_416.onnx", None),  # YOLO26s con entrada 416, ~127 ms
    "yolo_m": ("yolo26m_320.onnx", None),     # YOLO26m, ~246 ms, 82 MB
}


def ruta_modelo(nombre: str) -> str:
    """Devuelve la ruta local del modelo, descargándolo si no existe."""
    archivo, url = MODELOS[nombre]
    ruta = CARPETA / archivo
    if not ruta.exists() and url is None:
        raise FileNotFoundError(
            f"Falta {ruta}. Debería venir en el repositorio; "
            "si no, genéralo con herramientas/exportar_yolo.py."
        )
    if not ruta.exists():
        CARPETA.mkdir(parents=True, exist_ok=True)
        print(f"Descargando modelo '{nombre}'...")
        temporal = ruta.with_suffix(ruta.suffix + ".part")
        urllib.request.urlretrieve(url, temporal)
        temporal.replace(ruta)
    return str(ruta)


if __name__ == "__main__":
    for n in MODELOS:
        print(n, "->", ruta_modelo(n))
