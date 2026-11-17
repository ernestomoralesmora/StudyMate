# Pruebas de la fase 1 (cámara y temporizador)

Lista para comprobar la detección en un equipo nuevo. Anota en cada fila si sale
bien (✅) o mal (❌) y, si falla, qué ha pasado.

Equipo: ______________________   Fecha: __________   Probado por: ______________

## 0. Preparación

En PowerShell:

```powershell
git clone https://github.com/ernestomoralesmora/StudyMate.git   # o "git pull" si ya lo tienes
cd StudyMate
git checkout feature/presencia-camara
python --version            # tiene que ser 3.11 o superior
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

- [ ] La instalación termina sin errores.
- [ ] `python -m studymate.vision.pruebas.prueba_estados` termina con
      "Todas las pruebas pasan".

## 1. Prueba principal

```powershell
python -m studymate.vision.pruebas.prueba_camara
```

La primera vez tarda un poco en descargar los modelos de MediaPipe (~12 MB). El de YOLO
ya viene en el repositorio. Las líneas `INFO:` y `W0000` de la consola son normales.

- [ ] Se abre la ventana con la cámara.
- [ ] Los fps de la esquina superior izquierda están en 10 o más. Anota cuántos: ______

| # | Qué hacer | Resultado esperado | ✅/❌ | Notas |
|---|-----------|--------------------|------|-------|
| 1 | Sentarte delante, normal | A los ~3 s, **ESTUDIANDO** (borde verde) y el tiempo avanza | | |
| 2 | Levantarte e irte | A los ~3 s, **AUSENTE** (rojo) y el tiempo se para | | |
| 3 | Volver a sentarte | A los ~3 s, **ESTUDIANDO** otra vez | | |
| 4 | Girar la cabeza 1 s y volver | **No** cambia de estado | | |
| 5 | Mirar los apuntes agachado (sin móvil) | Sigue en ESTUDIANDO, o pasa a **DUDOSO** y pregunta | | |
| 6 | Escribir a mano o pasar páginas | Sigue en **ESTUDIANDO** (nunca USANDO_MOVIL) | | |
| 7 | Teclear en el portátil | Sigue en **ESTUDIANDO** | | |
| 8 | Móvil sobre la mesa, sin tocarlo | Sigue en **ESTUDIANDO** | | |
| 8b | Dibujar cuadrados o rectángulos, sujetar una goma, una calculadora o un estuche | Sigue en **ESTUDIANDO** (nunca USANDO_MOVIL) | | |
| 9 | Coger el móvil y usarlo 15 s | A los ~3 s, **USANDO_MOVIL** (naranja) y se mantiene; el tiempo se para | | |
| 10 | Soltar el móvil en la mesa | A los ~3–4 s, **ESTUDIANDO** | | |
| 11 | Usar el móvil con la otra mano | Igual que la prueba 9 | | |
| 12 | Taparte la cara con las manos a la vista | **DUDOSO** (amarillo) con "Sigues estudiando?" | | |
| 13 | En DUDOSO, pulsar **S** | El tiempo pendiente se suma al estudiado | | |
| 14 | En DUDOSO, pulsar **N** | El tiempo pendiente se descarta | | |
| 15 | Pulsar **Q** | Se cierra y la consola muestra el tiempo total | | |

Repite las pruebas 9 y 10 con el portátil en otra posición o con otra luz (por ejemplo,
de noche con la lámpara).

### Dispositivo permitido

```powershell
python -m studymate.vision.pruebas.prueba_camara --permitir-movil
```

| # | Qué hacer | Resultado esperado | ✅/❌ | Notas |
|---|-----------|--------------------|------|-------|
| 16 | Usar el móvil 15 s | Sigue en **ESTUDIANDO** | | |

## 2. Medir el detector del móvil

```powershell
python -m studymate.vision.pruebas.prueba_detectores
```

Haz cada prueba por separado (pulsa Q al acabar y vuelve a lanzar el script) y copia
lo que sale en la consola.

**a) Usando el móvil 20–30 s.** El porcentaje debería ser alto.

```
Fotogramas con manos:
Con móvil en la mano:
Puntuación del móvil:
```

**b) Sin móvil: dibujando cuadrados, escribiendo, con una goma o calculadora en la mano,
20–30 s.** El porcentaje debería ser cercano a 0 %.

```
Fotogramas con manos:
Con móvil en la mano:
Puntuación del móvil:
```

Opcional: repite a) y b) con `--modelo objetos_preciso` (el detector antiguo de
MediaPipe) para comparar los dos.

Los umbrales están en `studymate/vision/config.py`. No los cambies sin avisar:
anota los números y lo ajustamos juntos.
