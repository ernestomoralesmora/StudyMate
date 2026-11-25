"""Parámetros configurables de la detección.

Todos los umbrales están aquí para poder ajustarlos sin tocar la lógica.
"""

# --- Máquina de estados ---------------------------------------------------
# Segundos que debe mantenerse una situación antes de cambiar de estado.
MARGEN_CAMBIO_S = 3.0
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
