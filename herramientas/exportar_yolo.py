"""Genera studymate/vision/modelos/yolo26n_320.onnx a partir de YOLO26n.

Solo hace falta si se quiere regenerar o cambiar el modelo: el .onnx ya viene en
el repositorio. Necesita Ultralytics (que instala PyTorch, más de 1 GB y
opencv-python, incompatible con el OpenCV de MediaPipe), así que se ejecuta en
un entorno virtual APARTE, nunca en el .venv del proyecto:

    python -m venv .venv-exportar
    .venv-exportar\\Scripts\\pip install ultralytics onnx onnxslim --extra-index-url https://download.pytorch.org/whl/cpu
    .venv-exportar\\Scripts\\python herramientas\\exportar_yolo.py

Licencia: los modelos YOLO de Ultralytics se distribuyen con licencia AGPL-3.0.
"""

import shutil
from pathlib import Path

from ultralytics import YOLO

LADO = 320  # debe coincidir con _MovilYolo.LADO en studymate/vision/detectores.py
DESTINO = Path(__file__).resolve().parents[1] / "studymate" / "vision" / "modelos" / "yolo26n_320.onnx"

modelo = YOLO("yolo26n.pt")  # se descarga solo
assert modelo.names[67] == "cell phone"
ruta = modelo.export(format="onnx", imgsz=LADO, simplify=True, dynamic=False)
DESTINO.parent.mkdir(parents=True, exist_ok=True)
shutil.copy(ruta, DESTINO)
print("Modelo exportado en", DESTINO)
