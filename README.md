# StudyMate

Proyecto de Diseño de Sistemas Interactivos (UCLM, curso 26/27).
Autores: Pablo Santillana Fernández y Ernesto Morales Mora.

StudyMate es un compañero de estudio virtual. Usa la cámara para saber si estás
estudiando y pausa el tiempo cuando no lo haces. Más adelante planificará las sesiones
con un LLM.

**Estado actual: fase 1 (cámara y temporizador) hecha; fase 2 (LLM) en curso.**

## Requisitos

- Windows 10/11 (probado en un MSI Bravo 15 con la webcam integrada).
- Python 3.11 o superior (desarrollado con 3.14).
- Conexión a internet la primera vez, para descargar los modelos de MediaPipe (unos 12 MB).

## Instalación

Desde la carpeta del repositorio, en PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Si PowerShell no deja activar el entorno, ejecuta antes
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

> No instales `opencv-python` además de `opencv-contrib-python` (MediaPipe ya instala
> este último). Los dos comparten la carpeta `cv2` y se rompen entre sí.

## Ejecutar la prueba de la cámara

Con el entorno activado y desde la raíz del repositorio:

```powershell
python -m studymate.vision.pruebas.prueba_camara
```

Se abre una ventana con la imagen de la cámara, el estado detectado y el tiempo estudiado.
La primera vez descarga los modelos en `studymate/vision/modelos/`.

| Tecla   | Acción                                                          |
|---------|-----------------------------------------------------------------|
| `S`     | Responder "sí" a *¿Sigues estudiando?* (estado DUDOSO)          |
| `N`     | Responder "no" (el tiempo pendiente se descarta)                |
| `Q`/Esc | Salir; en la consola se muestra el tiempo total estudiado       |

Opciones:

- `--camara 1`: usar otra cámara (por defecto, la 0, que es la integrada).
- `--permitir-movil`: el móvil o la tablet en la mano no pausan el tiempo
  (dispositivo permitido).

La consola muestra varias líneas `INFO:` de MediaPipe al arrancar. Son normales.

### Otras pruebas

```powershell
# Lógica de estados y temporizador con tiempos simulados (no usa la cámara)
python -m studymate.vision.pruebas.prueba_estados

# Detecciones en bruto (cara, manos, móvil y puntuaciones), para ajustar umbrales
python -m studymate.vision.pruebas.prueba_detectores
```

## Cómo funciona la detección

En cada fotograma se detectan la cara y las manos con MediaPipe. El móvil (clase COCO
`cell phone`) se busca con **YOLO26n** en un hilo aparte, en un recorte alrededor de
cada mano para que salga grande. Con eso, el fotograma sugiere un estado:

| Situación en el fotograma                                    | Estado sugerido |
|--------------------------------------------------------------|-----------------|
| Móvil cerca de una mano con puntuación ≥ 0,45                | USANDO_MOVIL    |
| Móvil cerca de una mano con puntuación entre 0,25 y 0,45     | DUDOSO          |
| Se ve la cara                                                | ESTUDIANDO      |
| No se ve la cara, pero sí las manos                          | DUDOSO          |
| No se ve nada                                                | AUSENTE         |

Un móvil sobre la mesa, lejos de las manos, no cuenta.

El estado solo cambia cuando la nueva situación se mantiene **1,5 segundos**. Los cortes
de menos de 0,5 s (fallos sueltos del detector) no reinician la cuenta.

El temporizador solo suma en ESTUDIANDO.

DUDOSO significa que StudyMate te pregunta *¿Sigues estudiando?*. Como la pregunta
distrae, sale poco:

- Solo se pregunta si la duda dura **15 s** seguidos. Mientras tanto, el estado sigue
  como estaba.
- Tras responder, no se vuelve a preguntar en **10 minutos**. Una duda nueva en ese
  tiempo no cambia el estado.

Qué pasa al responder:

- `S`: pasa a **ESTUDIANDO** y se suma el tiempo pendiente. La respuesta vale mientras
  siga la misma duda, así que no vuelve a preguntar.
- `N`: pasa a **AUSENTE**, se pausa y se descuenta el tiempo de duda que ya se había
  contado. En cuanto vuelva a verte, regresa a ESTUDIANDO.
- Si no respondes y la detección vuelve a ESTUDIANDO, el pendiente se suma. Si pasa a
  otro estado, se descarta.

Todos los umbrales están en [`studymate/vision/config.py`](studymate/vision/config.py).

La detección se ejecuta en un hilo aparte de la interfaz. En el MSI va a unos 16 fps.

### Por qué YOLO para el móvil

Primero se usó el detector de objetos de MediaPipe (EfficientDet-Lite), pero confundía
con un móvil cosas rectangulares cerca de la mano, por ejemplo al dibujar cuadrados.
Por eso se pasó a YOLO, que era el plan B del proyecto:

- El modelo va exportado a ONNX y se ejecuta con `onnxruntime`. No hace falta instalar
  Ultralytics ni PyTorch.
- Tarda unos 20 ms por análisis, frente a los ~175 ms de EfficientDet-Lite2.
- El modelo (`studymate/vision/modelos/yolo26n_320.onnx`, ~10 MB) va incluido en el
  repositorio. Cómo se generó: [`herramientas/exportar_yolo.py`](herramientas/exportar_yolo.py).
- Los modelos YOLO de Ultralytics tienen licencia AGPL-3.0.

Para comparar con los detectores de MediaPipe, los dos scripts de prueba admiten
`--modelo objetos_preciso` (Lite2) o `--modelo objetos` (Lite0).

**Privacidad:** los fotogramas se procesan en memoria. No se guardan ni se envían a
internet.

### Móvil aparcado (idea de la profesora)

Reconocer el móvil en la mano falla porque la mano tapa la mitad y lo que queda se parece
a un típex. Sobre la mesa se ve entero, así que:

1. En el cuestionario se pregunta si vas a dejar el móvil a la vista (si lo tienes
   guardado, solo se vigila la mano, como antes).
2. **Preparación (30 s, el tiempo no cuenta):** la cámara enseña el sitio de estudio; deja
   el móvil en la mesa donde se vea (por ejemplo, a la izquierda) y arrastra con el ratón
   un recuadro sobre él. Con Enter empiezas antes; si no, la sesión empieza sola a los 30 s
   (si no has marcado el móvil, se vigila solo la mano). Tumbado en la mesa YOLO casi
   nunca reconoce el móvil, por eso el sitio lo marca el estudiante.
3. Cada segundo se mira solo ese sitio: se compara con la imagen del principio (parecido)
   y se mide qué parte de la zona ha cambiado (sirve aunque el recuadro sea más grande
   que el móvil). Conviene rodear el móvil ajustado.
   - **En su sitio:** lo que parezca un móvil en la mano se ignora (típex, boli...).
   - **Fuera de su sitio** y en la mano: USANDO_MOVIL.
   - **Fuera de su sitio** y no se ve: a los 4 s suena un aviso y pregunta "¿Has cogido el móvil?".
     Si respondes que sigues estudiando (lo has guardado), deja de vigilar el sitio.

```powershell
python -m studymate.vision.pruebas.prueba_camara --modelo yolo_s --movil-a-la-vista
```

Los valores están en `config.py`, apartado "Móvil aparcado".

### Verificador CLIP (en pruebas, rama `mejora/clip`)

YOLO a veces confunde con un móvil un boli, el típex o la cartera. Las reglas de tamaño y
pinza quitan casi todos esos errores, pero también parte de los aciertos. CLIP (ViT-B/32)
revisa cada candidato de YOLO comparándolo con frases ("a hand holding a smartphone",
"a hand holding a pen"...). No hay que entrenar nada, y solo se ejecuta cuando YOLO ve algo
junto a la mano, así que no baja los fps. La primera vez se descargan ~155 MB de Hugging Face.

Se elige con `MODO_VERIFICACION` en `config.py`: `"reglas"` (por defecto, no carga CLIP),
`"reglas+clip"` o `"clip"`.

```powershell
# 1) Comprobar CLIP por separado (tokenizador, tiempo y prueba en directo con objetos)
python -m studymate.vision.pruebas.prueba_clip --camara

# 2) Comparar las tres variantes en los mismos fotogramas (al salir imprime la tabla)
python -m studymate.vision.pruebas.prueba_detectores --modelo yolo_s --clip
```

Haz la prueba 2 una vez usando el móvil y otra con boli, típex o cartera. Con el móvil
interesa el porcentaje más alto; con lo demás, el más bajo.

## Fase 2: cuestionario y plan con el LLM

Antes de cada sesión, un cuestionario pregunta el tiempo disponible, cuántos minutos
seguidos aguantas concentrado, el cansancio, los temas, lo que ya sabes y si necesitas el
móvil o la tablet para estudiar, y si quieres test al final de cada bloque (por defecto,
sí). Con eso, Groq propone un plan de bloques (estudio + test de 5 min + descanso) que
**maximiza el tiempo de estudio**: como cada bloque añade un test y un descanso, usa los
menos bloques posibles, cada uno lo más cerca de lo que aguantas concentrado.

La aplicación **no se fía del plan**: comprueba que cada bloque cabe en tu concentración
(más corto si estás cansado), que los descansos son razonables y que el total cabe en el
tiempo disponible. Si no cumple, le pide a Groq que lo corrija una vez. Si sigue mal o no
hay conexión, usa un **plan básico** calculado sin LLM y avisa.

### Clave de Groq

Crea una clave en <https://console.groq.com/keys> y guárdala como variable de entorno
(no la pongas en el código ni la subas al repositorio):

```powershell
setx GROQ_API_KEY "tu_clave"
```

Cierra y vuelve a abrir la terminal (o VS Code) para que se aplique.

### Probarlo

```powershell
# Sin conexión: lógica del cuestionario, validación y plan básico con respuestas inventadas
python -m studymate.llm.pruebas.prueba_plan

# Con Groq: rellenas el cuestionario en la consola y ves el plan propuesto
python -m studymate.llm.pruebas.prueba_plan_groq
python -m studymate.llm.pruebas.prueba_plan_groq --apuntes mis_apuntes.txt
```

El último cuestionario se guarda en `studymate/data/perfil.json` (no se sube) y se propone
por defecto la siguiente vez.

> COCO no distingue el móvil de la tablet. Si marcas cualquiera de los dos como permitido,
> ninguno de los dos pausará el tiempo en esa sesión.

## Gamificación: la pecera del panel principal

La pecera **no cambia mientras se estudia**. Al terminar cada sesión, StudyMate la califica
y la pecera del panel principal se actualiza:

| Sesión | Cómo se decide | Qué pasa en la pecera |
|---|---|---|
| Muy buena | puntuación ≥ 80 | +15 de salud y llega un pez nuevo (un pez dorado cada 3 muy buenas seguidas). Limpia los peces muertos |
| Regular | entre 50 y 79 | se queda igual |
| Mala | < 50 | −20 de salud, un pez muere y queda flotando, el agua se ensucia |

La puntuación parte del **porcentaje del tiempo previsto que se ha estudiado de verdad** y
resta 8 puntos por cada vez que se coge el móvil y 4 por cada ausencia. El test, si se hace,
suma como mucho 5. Las sesiones de menos de 5 minutos no cuentan. Todos los valores están
al principio de `studymate/gamificacion/pecera.py`.

La **racha** se cuenta por sesiones muy buenas seguidas (no por días): cada 3 llega un pez
dorado. Al acabar, el panel muestra una **autocrítica** de la sesión en primera persona:
qué ha ido bien y qué mejorar la próxima vez (móvil, ausencias, tiempo aprovechado, test).

La pecera se guarda en `studymate/data/pecera.json` (no se sube al repositorio).

```powershell
# Pruebas sin interfaz (y vistas previas en SVG)
python -m studymate.gamificacion.pruebas.prueba_pecera --svg pecera_svg

# Ventana de prueba con la pecera animada (usa una pecera de prueba; --real para la tuya)
python -m studymate.ui.pruebas.prueba_pecera
```

## Estructura

```
studymate/
├── main.py              # arranca la app (por ahora, la prueba de cámara)
├── vision/
│   ├── config.py        # umbrales y constantes
│   ├── camara.py        # captura con OpenCV
│   ├── modelos.py       # descarga de los modelos de MediaPipe
│   ├── detectores.py    # cara, manos y móvil con MediaPipe
│   ├── observacion.py   # qué se ve en un fotograma y qué estado sugiere
│   ├── estados.py       # máquina de estados con el margen de 1,5 s
│   ├── temporizador.py  # cuenta solo en ESTUDIANDO
│   ├── motor.py         # hilo de detección que une todo lo anterior
│   └── pruebas/         # scripts de prueba de cada parte
├── llm/
│   ├── cliente_groq.py  # llamadas a Groq con respuesta JSON por esquema
│   ├── preguntas.py     # 5 preguntas tipo test por bloque (RF7)
│   ├── cuestionario.py  # cuestionario inicial y perfil de la sesión (RF5, RF11)
│   ├── plan.py          # plan de bloques, validación y plan básico (RF6, RNF5, RNF8)
│   └── pruebas/         # pruebas con y sin conexión
├── ui/                  # fase 3
└── data/                # perfil e historial (JSON, no se suben)
```
