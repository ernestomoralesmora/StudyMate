# StudyMate

Proyecto de Diseño de Sistemas Interactivos (UCLM, curso 26/27).
Autores: Pablo Santillana Fernández y Ernesto Morales Mora.

StudyMate es un compañero de estudio virtual. Usa la cámara para saber si estás
estudiando y pausa el tiempo cuando no lo haces, y planifica las sesiones con un LLM.

**Estado actual: las tres fases montadas (cámara, LLM e interfaz PySide6). Queda afinar
la detección del móvil con pruebas.**

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

## Ejecutar la aplicación

```powershell
python -m studymate.main
```

Recorrido:
1. **Acceso:** entrar con usuario y contraseña o crear una cuenta. Cada usuario tiene su zoo y
   sus datos en `studymate/data/usuarios/<usuario>/`. La contraseña no se guarda: solo su
   huella (PBKDF2-SHA256 con sal). La primera cuenta se queda con los datos de antes.
2. **La primera vez, crear el zoo:** su nombre (se puede cambiar luego) y las asignaturas,
   cada una con su animal (uno distinto por asignatura) y, si se quiere, sus temas.
3. **Zoo:** un recinto pequeño por asignatura con su avance.
4. **Nueva sesión:** se elige el animal de la asignatura → **cuestionario de esa asignatura**
   (sus temas, que se pueden ampliar; se proponen las respuestas de su última sesión) →
   **plan** → **preparación** de 30 s (marcar el móvil) → **sesión** por bloques (estudio →
   test → descanso) → **resumen** (nota, autocrítica y su recinto) → vuelta al zoo.

Cada asignatura es independiente: sus temas, sus sesiones, su avance y sus animales solo
cambian con sus propias sesiones. El **historial** se puede ver por asignatura.

- En la sesión, el tiempo del bloque solo avanza mientras estudias. Si hay una duda,
  aparece una pregunta abajo: botones o teclas **S** / **N**.
- El test se responde con el ratón o con **A**, **B** y **C**; **Enter** pasa a la siguiente.
- Para probarlo todo en poco tiempo, marca en el cuestionario **Modo prueba**: cada minuto
  del plan dura 10 s. Las sesiones de prueba salen en el historial marcadas, pero no cuentan
  en los totales (el zoo sí cambia).
- Sin `GROQ_API_KEY` funciona igual, con el plan básico y sin test.
- **Apuntes:** en el cuestionario se pueden subir PDF, Word (.docx) o texto. Solo se lee el
  texto (un PDF escaneado, que es solo imagen, no sirve). Para el plan y para el test de cada
  bloque se manda al asistente solo la parte de los apuntes más relacionada con ese tema
  (`llm/apuntes.py`), porque un temario entero no cabe en una consulta.
- Usuarios, zoo e historial se guardan en `studymate/data/` (no se suben al repositorio).

Pruebas sin cámara ni ventana de la lógica de la sesión y el historial:

```powershell
python -m studymate.sesion.pruebas.prueba_sesion
python -m studymate.pruebas.prueba_usuarios
```

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

## Gamificación: el zoo (un recinto por asignatura)

La pecera ha evolucionado a un **zoo**: cada asignatura del curso tiene su recinto con un
animal que elige el estudiante entre **10** (pez, pingüino, león, jirafa, loro, mono,
tortuga, rana, búho y zorro), uno distinto por asignatura. Cada animal tiene su recinto
(acuario, polo, sabana, selva, playa, estanque, bosque…). En el panel principal se ve el
recinto de cada asignatura con su nivel, su salud y el **avance**: las últimas sesiones
(color = nota, alto = minutos) y las horas totales.

Como la pecera, el zoo **no cambia mientras se estudia**. En el cuestionario se elige la
asignatura de la sesión y, al terminar, solo cambia su recinto:

| Sesión | Cómo se decide | Qué pasa en el recinto |
|---|---|---|
| Muy buena | puntuación ≥ 80 | +15 de salud y llega otro animal; cada 3 animales, el recinto sube de nivel (máximo 9) |
| Regular | entre 50 y 79 | se queda igual (y se corta la racha) |
| Mala | < 50 | −20 de salud, se va un animal y el recinto pierde color |

La puntuación parte del **porcentaje del tiempo previsto que se ha estudiado de verdad** y
resta 8 puntos por cada vez que se coge el móvil y 4 por cada ausencia. El test, si se hace,
suma como mucho 5. Las sesiones de menos de 5 minutos no cuentan. Al acabar, el resumen
muestra una **autocrítica** en primera persona: qué ha ido bien y qué mejorar.

- Reglas: `studymate/gamificacion/zoo.py` (la nota y la autocrítica, en `pecera.py`).
- Dibujo: `studymate/gamificacion/escena_zoo.py` (Python puro; se pinta con QPainter y se
  puede pasar a SVG).
- Se guarda en `studymate/data/zoo.json`. Si ya había una pecera, la primera vez pasa a ser
  el acuario de una asignatura «General».

```powershell
# Pruebas sin interfaz (y vista previa de los 10 recintos en SVG)
python -m studymate.gamificacion.pruebas.prueba_zoo --svg recintos_svg
```

## Estructura

```
studymate/
├── main.py              # arranca la interfaz
├── usuarios.py          # registro e inicio de sesión (contraseña con PBKDF2), datos por usuario
├── vision/
│   ├── config.py        # umbrales y constantes
│   ├── camara.py        # captura con OpenCV
│   ├── modelos.py       # descarga de los modelos de MediaPipe
│   ├── detectores.py    # cara, manos y móvil con MediaPipe
│   ├── observacion.py   # qué se ve en un fotograma y qué estado sugiere
│   ├── estados.py       # máquina de estados con el margen de 1,5 s
│   ├── temporizador.py  # cuenta solo en ESTUDIANDO
│   ├── motor.py         # hilo de detección que une todo lo anterior
│   ├── aparcado.py      # vigilar el sitio del móvil (idea de la profesora)
│   ├── preparacion.py   # los 30 s de preparación antes de la sesión
│   ├── clip.py          # verificador CLIP (en pruebas, desactivado)
│   └── pruebas/         # scripts de prueba de cada parte
├── llm/
│   ├── cliente_groq.py  # llamadas a Groq con respuesta JSON por esquema
│   ├── preguntas.py     # 5 preguntas tipo test por bloque (RF7)
│   ├── cuestionario.py  # cuestionario inicial y perfil de la sesión (RF5, RF11)
│   ├── plan.py          # plan de bloques, validación y plan básico (RF6, RNF5, RNF8)
│   └── pruebas/         # pruebas con y sin conexión
├── gamificacion/
│   ├── zoo.py           # un recinto por asignatura con su animal (10 a elegir)
│   ├── escena_zoo.py    # dibujo de los recintos y los animales
│   ├── pecera.py        # nota de la sesión y autocrítica (y la pecera original)
│   └── pruebas/
├── sesion/
│   ├── controlador.py   # bloques y fases (estudio, test, descanso), pausas, resumen
│   ├── historial.py     # data/historial.json y estadísticas
│   └── pruebas/
├── ui/
│   ├── app.py           # QApplication y estilo
│   ├── ventana.py       # une las pantallas y lleva la sesión
│   ├── estilo.py        # colores y hoja de estilo
│   ├── companero.py     # la cara del logo con expresiones
│   ├── camara_widget.py # imagen de la cámara y marcar el móvil con el ratón
│   ├── zoo_widget.py    # un recinto del zoo animado y el icono de cada animal
│   ├── dialogo_asignatura.py  # añadir una asignatura y elegir su animal
│   ├── pintar.py        # pinta con QPainter las figuras de las escenas
│   └── pantallas/       # acceso, bienvenida (crear el zoo), zoo, elegir asignatura,
│                        # cuestionario, plan, preparación, sesión, test, descanso,
│                        # resumen e historial
└── data/                # perfil e historial (JSON, no se suben)
```
