"""Parámetros configurables de la detección.

Todos los umbrales están aquí para poder ajustarlos sin tocar la lógica.
"""

# --- Máquina de estados ---------------------------------------------------
# Segundos que debe mantenerse una situación antes de cambiar de estado.
MARGEN_CAMBIO_S = 3.0
# Durante esos segundos se toleran fallos sueltos de detección de hasta esta
# duración sin reiniciar la cuenta (p. ej., la cara se pierde 2 fotogramas).
TOLERANCIA_FALLOS_S = 0.5

# --- Cámara ----------------------------------------------------------------
INDICE_CAMARA = 0
ANCHO_CAMARA = 640
ALTO_CAMARA = 480

# --- Detectores ------------------------------------------------------------
CONFIANZA_CARA = 0.5
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

# Modelo para el móvil: "objetos_preciso" (EfficientDet-Lite2, ~175 ms) u
# "objetos" (Lite0, ~60 ms, detecta peor). Va en su propio hilo, así que el
# modelo lento no baja los fps de la cámara.
MODELO_OBJETOS = "objetos_preciso"

# El móvil se busca en un recorte alrededor de cada mano (en vez de en la imagen
# entera reducida), para que salga grande. El recorte es la mano ampliada esta
# fracción de su tamaño por cada lado, con un lado mínimo en píxeles.
MARGEN_RECORTE = 1.0
LADO_MIN_RECORTE = 200

# Se usa la mejor detección del móvil de estos últimos segundos: si deja de
# detectarse un momento o sale con poca puntuación (medio tapado por los dedos),
# se sigue dando por visto.
MEMORIA_MOVIL_S = 1.0
