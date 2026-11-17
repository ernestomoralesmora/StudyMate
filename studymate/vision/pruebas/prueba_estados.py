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
    print("OK  clasificación")


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


if __name__ == "__main__":
    prueba_clasificacion()
    prueba_margen()
    prueba_temporizador()
    print("Todas las pruebas pasan.")
