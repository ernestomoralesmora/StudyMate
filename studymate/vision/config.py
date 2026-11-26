"""Parámetros configurables de la detección.

Todos los umbrales están aquí para poder ajustarlos sin tocar la lógica.
"""

# --- Máquina de estados ---------------------------------------------------
# Segundos que debe mantenerse una situación antes de cambiar de estado.
# Antes 3 s: se notaba lento al coger el móvil o al irse. 1,5 s responde antes;
# si aparecen pausas falsas por detecciones sueltas, subirlo un poco (2 s).
MARGEN_CAMBIO_S = 1.5
# Durante esos segundos se toleran fallos sueltos de detección de hasta esta
# duración sin reiniciar la cuenta (p. ej., la cara se pierde 2 fotogramas).
TOLERANCIA_FALLOS_S = 0.5

# Entrar en DUDOSO implica preguntar al usuario, y eso distrae. Por eso:
# la duda tiene que durar más que el resto de cambios antes de preguntar...
MARGEN_DUDOSO_S = 15.0
# ...y, tras responder, no se vuelve a preguntar en este tiempo (las dudas
# nuevas se resuelven solas con la última respuesta).
PAUSA_ENTRE_PREGUNTAS_S = 10 * 60

# --- Cámara ----------------------------------------------------------------
INDICE_CAMARA = 0
ANCHO_CAMARA = 640
ALTO_CAMARA = 480

# --- Detectores ------------------------------------------------------------
# Medido: una cara real da 0,89-0,97; el respaldo de una silla vacía llegaba a
# 0,50-0,75 y hacía que AUSENTE y ESTUDIANDO se alternaran. Con 0,80 no pasa
# ninguna detección de la silla y no se pierde ningún fotograma de la cara real.
CONFIANZA_CARA = 0.8
CONFIANZA_MANO = 0.5
MAX_MANOS = 2

# Clases COCO que cuentan como dispositivo que no es de estudio.
# Nota: COCO no distingue tablet de móvil; una tablet suele salir como "cell phone".
CLASES_DISPOSITIVO = ("cell phone",)
# Por encima de este valor, el móvil se considera detectado con seguridad.
UMBRAL_MOVIL = 0.45
# Entre este valor y UMBRAL_MOVIL, la detección se considera dudosa.
UMBRAL_MOVIL_DUDOSO = 0.25

# El recuadro de la mano se amplía esta fracción de su tamaño por cada lado
# antes de comprobar si toca el recuadro del móvil.
MARGEN_MANO = 0.5

# Una detección junto a la mano no cuenta como móvil si (medido con YOLO26s):
# - es pequeña respecto a la mano: un dedo, el hueco de la mano o el boli
#   (falsos positivos al dibujar, escribir o hacer el gesto del teléfono);
# - la mano está en pinza (puntas del pulgar y el índice juntas): así se coge
#   un boli; un móvil se coge con la mano rodeando algo ancho.
MIN_TAMANO_RESPECTO_MANO = 0.40  # área del móvil / área de la mano
MIN_PINZA = 0.25                 # distancia pulgar-índice / tamaño de la palma

# --- Preparación de la sesión (ver preparacion.py) ---------------------------
# Segundos para colocar el sitio de estudio y marcar el móvil antes de empezar.
# None: sin cuenta atrás, la sesión empieza cuando el estudiante pulsa «Empezar».
# Durante la preparación el tiempo no cuenta.
PREPARACION_S = None

# --- Móvil aparcado (idea de la profesora, ver aparcado.py) -----------------
# Cómo se sabe al empezar dónde está el móvil:
#   "a_mano"      el estudiante lo marca con el ratón sobre la imagen (fiable)
#   "automatico"  se sigue desde la mano hasta la mesa (en pruebas: el 25/11
#                 fijó el sitio con el móvil todavía en el aire)
# Medido el 25/11 marcándolo: "parecido" 0,68-0,74 con el móvil en su sitio y
# 0,15-0,23 al cogerlo, así que el umbral de 0,60 los separa bien.
LOCALIZAR_APARCADO = "a_mano"
VECES_EN_MANO_PARA_SEGUIR = 2   # veces que tiene que verse en la mano (puntuación >= UMBRAL_MOVIL)
PASADAS_MANO_APARTADA = 4       # análisis sin verlo en la mano y con la mano lejos para fijar el sitio
UMBRAL_APARCADO = 0.30          # puntuación de YOLO para aceptar el móvil sobre la mesa
VECES_PARA_APARCAR = 3          # tiene que verse en el mismo sitio estas veces...
INTENTOS_BUSCAR_APARCADO = 30   # ...en como mucho estos análisis (unos 45 s)
PERIODO_BUSQUEDA_APARCADO_S = 1.5  # cada cuánto se busca en toda la imagen
LADO_BUSQUEDA_APARCADO = 320    # al buscarlo, la imagen se recorre en cuadros de este lado
# Si aun así no lo encuentra, en la prueba de cámara se puede marcar a mano (tecla M).
PERIODO_APARCADO_S = 1.0        # cada cuánto se comprueba el sitio
HOLGURA_APARCADO = 0.25         # cuánto se puede haber movido sin contar como "fuera"
SIMILITUD_APARCADO = 0.60       # parecido mínimo con la imagen guardada al empezar
# Además del parecido, qué parte de la zona marcada ha cambiado: si el recuadro
# es grande y el móvil pequeño dentro, el parecido apenas baja al quitarlo.
# Se compara en COLOR (espacio Lab), no en gris: un móvil oscuro sobre una mesa
# oscura apenas cambia el gris al quitarlo, pero sí el tono. Medido el 26/11 con
# el vídeo de Pablo (móvil negro en mesa oscura, recuadro ajustado): con el móvil
# en su sitio cambia un 0-5 %; sin él, un 32-35 %. Con un recuadro grande y el
# móvil pequeño dentro, al quitarlo cambia menos (~18 %): por eso el límite es
# bajo. Si se deja el móvil algo movido (~22 %), se reconoce porque la zona ya no
# se parece a cómo quedó vacía (ver aparcado.py) y se toma como su nuevo sitio.
DIFERENCIA_PIXEL = 15           # distancia de color (Lab) para contar un píxel como cambiado
CAMBIO_MAXIMO_APARCADO = 0.15   # si cambia más de esta fracción de la zona, no está
CAMBIO_QUIETO = 0.05            # entre dos comprobaciones: la zona está quieta (no pasa una mano)
FALLOS_PARA_FUERA = 2           # comprobaciones seguidas sin verlo para decir "fuera"
# Si el móvil no está en su sitio ni en la mano, se pregunta "¿Has cogido el
# móvil?" tras estos segundos (más rápido que otras dudas, que esperan 15 s).
MARGEN_MOVIL_FUERA_S = 4.0

# --- Verificador CLIP (rama mejora/clip, en pruebas) --------------------------
# Qué decide si una detección junto a la mano cuenta como móvil:
#   "reglas"        solo las reglas de tamaño y pinza (lo de siempre)
#   "reglas+clip"   las reglas y, además, CLIP tiene que decir que es un móvil
#   "clip"          solo CLIP (sin las reglas de tamaño y pinza)
# Con "reglas" no se carga CLIP. Para compararlas con la cámara:
#   python -m studymate.vision.pruebas.prueba_detectores --modelo yolo_s --clip
MODO_VERIFICACION = "reglas"
# Probabilidad mínima (0-1) que tiene que dar CLIP a las frases de móvil.
UMBRAL_CLIP = 0.5
# El recorte para CLIP es el recuadro del móvil ampliado esta fracción por cada
# lado (así se ve también la mano, que ayuda a distinguir boli y móvil).
MARGEN_RECORTE_CLIP = 0.3
HILOS_CLIP = 2
# CLIP funciona mejor en inglés. Las del móvil suman a favor; las otras, en contra.
CLIP_TEXTOS_MOVIL = (
    "a photo of a hand holding a smartphone",
    "a photo of a person using a mobile phone",
    "a close-up photo of a phone screen",
)
CLIP_TEXTOS_OTROS = (
    "a photo of a hand holding a pen",
    "a photo of a hand holding a correction fluid pen",
    "a photo of a hand holding a wallet",
    "a photo of a hand writing on paper",
    "a photo of an empty hand",
    "a photo of a hand holding a notebook",
    "a photo of a person's face",
)

# Modelo para el móvil (va en su propio hilo, no baja los fps de la cámara):
#   "yolo"            YOLO26n con onnxruntime, ~20 ms. Menos falsos positivos.
#   "objetos_preciso" EfficientDet-Lite2 de MediaPipe, ~175 ms.
#   "objetos"         EfficientDet-Lite0 de MediaPipe, ~60 ms. El que peor detecta.
# Los de MediaPipe confundían con un móvil cosas rectangulares cerca de la mano
# (p. ej., dibujar cuadrados), por eso se usa YOLO (plan B del proyecto).
MODELO_OBJETOS = "yolo"
# Hilos de CPU para YOLO; el resto queda para la cara y las manos.
HILOS_YOLO = 2

# El móvil se busca en un recorte alrededor de cada mano (en vez de en la imagen
# entera reducida), para que salga grande. El recorte es la mano ampliada esta
# fracción de su tamaño por cada lado, con un lado mínimo en píxeles.
MARGEN_RECORTE = 1.0
LADO_MIN_RECORTE = 200

# El resultado del último análisis del móvil sigue siendo válido estos segundos
# (el hilo del móvil puede ir algo por detrás de la cámara). Los cortes más
# largos ya los tolera la máquina de estados.
MEMORIA_MOVIL_S = 0.5
