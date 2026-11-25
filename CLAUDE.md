# StudyMate

Proyecto de la asignatura Diseño de Sistemas Interactivos (UCLM, curso 26/27).
Autores: Pablo Santillana Fernández y Ernesto Morales Mora.

StudyMate es un compañero de estudio virtual. Usa la cámara para saber si el estudiante
está estudiando y pausa el tiempo cuando no lo está. Además, planifica las sesiones de
forma personalizada con un LLM.

## Prioridades (indicadas por el profesor)
1. **Cámara (lo más importante):** detectar si el estudiante está presente y estudiando.
   El temporizador se pausa si se ausenta o si usa un dispositivo que no es de estudio
   (móvil, tablet…).
2. **Personalización:** antes de cada sesión, un cuestionario pregunta el tiempo
   disponible y cuántos minutos seguidos aguanta concentrado. Con eso se adaptan los bloques.
3. **Gestión del LLM:** repartir el contenido en bloques, generar preguntas tipo test y
   asesorar sobre qué repasar.
4. **Tests:** se responden con el ratón o con las teclas A, B y C.

Fuera del alcance (no implementar): respuesta con gestos de las manos y ESP32/BLE.

## Stack
- Python 3.11+
- OpenCV: captura de la webcam
- MediaPipe: Face Detection, Hands y Object Detector (modelo COCO, clase "cell phone").
  YOLO (Ultralytics) solo como plan B si MediaPipe no detecta bien el móvil.
- Groq API, modelo `openai/gpt-oss-120b`. La clave va en la variable de entorno
  `GROQ_API_KEY` y nunca se sube al repositorio.
- PySide6 para la interfaz.
- JSON para el perfil y el historial (carpeta `data/`).
- Equipo de pruebas: portátil MSI Bravo 15 (AMD Ryzen 5, gráfica AMD Radeon, Windows),
  con la webcam integrada.

## Estructura
```
studymate/
├── main.py      # arranca la app
├── vision/      # cámara, detectores y máquina de estados
├── llm/         # prompts y llamadas a Groq
├── ui/          # ventanas PySide6 y compañero con expresiones
└── data/        # perfil e historial (JSON)
```

## Reglas de la detección
- Estados: ESTUDIANDO, AUSENTE, USANDO_MOVIL, DUDOSO.
- Solo se cambia de estado si la situación se mantiene unos segundos. El margen va en una
  constante configurable (1,5 s; al principio eran 3 s).
- "Usando el móvil" significa móvil detectado **cerca de una mano** de forma continuada,
  no simplemente que el móvil esté sobre la mesa.
- Los dispositivos marcados como permitidos en el cuestionario (p. ej., una tablet con
  apuntes) no pausan el tiempo.
- Si la detección es dudosa, se pide confirmación al usuario en vez de pausar sin más.
- Objetivo: al menos 10 fps en el MSI sin GPU NVIDIA. La detección va en un hilo aparte
  de la interfaz.
- Privacidad: los fotogramas se procesan en local; no se guardan ni se envían a internet.
  Al LLM solo se le manda texto.

## Reglas del LLM
- El LLM no se reentrena: se personaliza con contexto (cuestionario, apuntes del bloque
  y resultados anteriores).
- Se le pide la respuesta en JSON, y la aplicación valida que los tiempos sumen bien
  y quepan en el tiempo disponible.
- Si falla la conexión, se avisa y se ofrece un plan básico sin LLM.

## Forma de trabajar
- Código y comentarios en español.
- Avanzar por fases: 1) cámara y temporizador, 2) LLM, 3) interfaz PySide6.
- Cada módulo de `vision/` debe poder probarse por separado con un script pequeño.
- Incluir y mantener `requirements.txt` y un `README.md` con las instrucciones para ejecutarlo.
