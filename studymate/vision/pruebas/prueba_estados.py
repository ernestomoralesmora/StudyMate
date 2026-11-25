"""Prueba sin cámara de la clasificación, la máquina de estados y el temporizador.

Usa tiempos simulados, así que tarda menos de un segundo.
Uso:  python -m studymate.vision.pruebas.prueba_estados
"""

from ..estados import Estado, MaquinaEstados
from ..observacion import Dispositivo, Observacion, clasificar, marcar_cercania
from ..temporizador import Temporizador

E, A, M, D = Estado.ESTUDIANDO, Estado.AUSENTE, Estado.USANDO_MOVIL, Estado.DUDOSO
FPS = 10


def simular(maquina, temporizador, candidato, segundos, t0):
    """Envía `candidato` durante `segundos` a FPS fotogramas por segundo."""
    t = t0
    for _ in range(int(segundos * FPS)):
        t += 1 / FPS
        maquina.actualizar(candidato, t)
        temporizador.actualizar(maquina.estado, t)
    return t


def prueba_clasificacion():
    cara = (100, 100, 200, 200)
    mano = (300, 300, 380, 380)
    movil_mano = Dispositivo("cell phone", 0.8, (360, 320, 420, 400))
    movil_mesa = Dispositivo("cell phone", 0.8, (550, 400, 620, 470))

    assert clasificar(Observacion()) == A
    assert clasificar(Observacion(caras=[cara])) == E
    assert clasificar(Observacion(manos=[mano])) == D  # manos sin cara

    obs = Observacion(caras=[cara], manos=[mano], dispositivos=[movil_mano])
    marcar_cercania(obs)
    assert movil_mano.cerca_de_mano
    assert clasificar(obs) == M
    assert clasificar(obs, frozenset({"cell phone"})) == E  # dispositivo permitido

    obs = Observacion(caras=[cara], manos=[mano], dispositivos=[movil_mesa])
    marcar_cercania(obs)
    assert not movil_mesa.cerca_de_mano
    assert clasificar(obs) == E  # móvil sobre la mesa, lejos de la mano

    dudoso = Dispositivo("cell phone", 0.3, movil_mano.recuadro)
    obs = Observacion(caras=[cara], manos=[mano], dispositivos=[dudoso])
    marcar_cercania(obs)
    assert clasificar(obs) == D

    # Recuadro pequeño metido dentro de la mano (dedo, bolígrafo, gesto con la
    # mano vacía): no es un móvil aunque la puntuación sea alta.
    falso = Dispositivo("cell phone", 0.8, (320, 320, 350, 350))
    obs = Observacion(caras=[cara], manos=[mano], dispositivos=[falso])
    marcar_cercania(obs)
    assert falso.descartado == "pequeño" and not falso.cerca_de_mano
    assert clasificar(obs) == E

    # Boli cogido en pinza (pulgar e índice juntos): el recuadro de mano + boli
    # es grande, pero la postura delata que no es un móvil.
    boli = Dispositivo("cell phone", 0.65, (310, 260, 370, 370))
    obs = Observacion(caras=[cara], manos=[mano], pinza_manos=[0.15], dispositivos=[boli])
    marcar_cercania(obs)
    assert boli.descartado == "pinza" and clasificar(obs) == E

    # Un móvil del tamaño de la mano, con la mano rodeándolo, sí cuenta.
    real = Dispositivo("cell phone", 0.8, (310, 260, 370, 370))
    obs = Observacion(caras=[cara], manos=[mano], pinza_manos=[0.7], dispositivos=[real])
    marcar_cercania(obs)
    assert not real.descartado and real.cerca_de_mano
    assert clasificar(obs) == M
    print("OK  clasificación")


def prueba_modos_clip():
    """Las tres variantes con un boli que pasa las reglas pero CLIP rechaza, y al revés."""
    cara, mano = (100, 100, 200, 200), (300, 300, 380, 380)

    def ver(modo, prob, pinza=0.7, recuadro=(310, 260, 370, 370)):
        d = Dispositivo("cell phone", 0.8, recuadro, prob_clip=prob)
        obs = Observacion(caras=[cara], manos=[mano], pinza_manos=[pinza], dispositivos=[d])
        marcar_cercania(obs, modo=modo)
        return d, clasificar(obs)

    # CLIP dice que no es un móvil (p. ej., una cartera del tamaño de la mano).
    assert ver("reglas", 0.1)[1] == M           # las reglas solas no lo pillan
    d, estado = ver("reglas+clip", 0.1)
    assert d.descartado == "clip" and estado == E
    assert ver("clip", 0.1)[1] == E
    # CLIP dice que sí, pero la mano está en pinza.
    assert ver("reglas+clip", 0.9, pinza=0.1)[0].descartado == "pinza"
    assert ver("clip", 0.9, pinza=0.1)[1] == M  # sin reglas, cuenta
    # Si CLIP no ha dado resultado, no se descarta por CLIP.
    assert ver("clip", None)[1] == M
    # Lo que dirían las reglas se guarda siempre, para comparar.
    d, _ = ver("clip", 0.9, recuadro=(320, 320, 350, 350))
    assert d.descarte_reglas == "pequeño" and d.toca_mano
    print("OK  modos de verificación (reglas / reglas+clip / clip)")


def prueba_margen():
    m, t = MaquinaEstados(margen_s=3.0, estado_inicial=E), Temporizador()
    t_ = simular(m, t, E, 5, 0)
    t_ = simular(m, t, A, 2.5, t_)
    assert m.estado == E, "no debe cambiar antes de 3 s"
    t_ = simular(m, t, A, 1.0, t_)
    assert m.estado == A, "debe cambiar a los 3 s"

    # Fallos sueltos (1 de cada 5 fotogramas) no impiden el cambio.
    m = MaquinaEstados(margen_s=3.0, estado_inicial=E)
    tt = 0.0
    for i in range(40):
        tt += 1 / FPS
        m.actualizar(E if i % 5 == 0 else M, tt)
    assert m.estado == M
    print("OK  margen de 3 s")


def prueba_temporizador():
    m, t = MaquinaEstados(margen_s=3.0, estado_inicial=E), Temporizador()
    t_ = simular(m, t, E, 10, 0)
    t_ = simular(m, t, A, 20, t_)
    t_ = simular(m, t, E, 10, t_)
    # 10 s + ~3 s de margen al irse - ~3 s de margen al volver = ~20 s
    assert 19 <= t.estudiado_s <= 21, t.estudiado_s

    # DUDOSO: el tiempo queda pendiente y se suma si el usuario confirma.
    m, t = MaquinaEstados(margen_s=3.0, estado_inicial=D), Temporizador()
    simular(m, t, D, 10, 0)
    assert t.estudiado_s == 0 and t.pendiente_s > 9 and t.esperando_confirmacion
    t.confirmar_dudoso(True)
    assert t.estudiado_s > 9 and t.pendiente_s == 0

    # Si dice que no, el pendiente se descarta.
    m, t = MaquinaEstados(margen_s=3.0, estado_inicial=D), Temporizador()
    simular(m, t, D, 10, 0)
    t.confirmar_dudoso(False)
    assert t.estudiado_s == 0
    print("OK  temporizador")


def responder(m, t, estaba_estudiando, ahora):
    """Lo mismo que hace MotorDeteccion.confirmar_dudoso al pulsar S o N."""
    descuento = m.duda_previa_s if m.estado_antes_de_duda == E else 0.0
    t.confirmar_dudoso(estaba_estudiando, descuento)
    m.confirmar(E if estaba_estudiando else A, ahora)


def prueba_preguntas():
    m, t = MaquinaEstados(margen_s=3.0, estado_inicial=E), Temporizador()
    t_ = simular(m, t, E, 5, 0)

    # Taparse la cara un rato no pregunta: hace falta duda durante 15 s.
    t_ = simular(m, t, D, 10, t_)
    assert m.estado == E, "con 10 s de duda todavía no pregunta"
    t_ = simular(m, t, D, 6, t_)
    assert m.estado == D and t.esperando_confirmacion

    # N -> AUSENTE, y se descuentan los 15 s de duda que se habían contado.
    responder(m, t, False, t_)
    assert m.estado == A
    assert 4 <= t.estudiado_s <= 6, t.estudiado_s
    t_ = simular(m, t, D, 30, t_)
    assert m.estado == A, "la misma duda no vuelve a preguntar"
    assert t.estudiado_s <= 6

    # Se destapa la cara: vuelve a ESTUDIANDO por lo que se ve.
    t_ = simular(m, t, E, 4, t_)
    assert m.estado == E
    # Otra duda antes de 10 min: no pregunta y no pausa (no usa el "no" de antes).
    antes = t.estudiado_s
    t_ = simular(m, t, D, 30, t_)
    assert m.estado == E and t.estudiado_s > antes + 25

    # Pasados 10 min desde la respuesta, una duda larga vuelve a preguntar.
    t_ = simular(m, t, E, 600, t_)
    t_ = simular(m, t, D, 16, t_)
    assert m.estado == D

    # S -> ESTUDIANDO, y sigue así aunque la duda continúe.
    responder(m, t, True, t_)
    assert m.estado == E
    antes = t.estudiado_s
    simular(m, t, D, 30, t_)
    assert m.estado == E and t.estudiado_s > antes + 25
    print("OK  preguntas (S -> ESTUDIANDO, N -> AUSENTE, pocas preguntas)")


if __name__ == "__main__":
    prueba_clasificacion()
    prueba_modos_clip()
    prueba_margen()
    prueba_temporizador()
    prueba_preguntas()
    print("Todas las pruebas pasan.")
