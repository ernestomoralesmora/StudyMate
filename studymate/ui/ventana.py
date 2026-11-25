"""Ventana principal de StudyMate: une las pantallas y lleva la sesión.

Recorrido:  acceso (usuario y contraseña) → la primera vez, crear el zoo →
            zoo → elegir el animal de la asignatura → cuestionario de esa asignatura →
            plan → preparación (30 s) → [estudio → test → descanso] × bloques →
            resumen → zoo   (y el historial desde el zoo).

Cada usuario tiene su carpeta de datos (data/usuarios/<usuario>/) y, dentro de su
zoo, cada asignatura guarda sus temas, sus sesiones y su avance por separado.

La cámara la lleva MotorDeteccion en su propio hilo; la ventana solo lee su
último resultado unas 20 veces por segundo (no espera nunca a la detección).
Las llamadas al asistente (plan y preguntas) van también en segundo plano.
"""

import time
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QMainWindow, QMessageBox, QStackedWidget

from studymate import usuarios as us
from studymate.gamificacion import pecera as pc
from studymate.gamificacion import zoo as z
from studymate.llm.apuntes import para_plan, para_test
from studymate.llm.cliente_groq import consultar_groq
from studymate.llm.cuestionario import PerfilSesion
from studymate.llm.plan import Plan, generar_plan, plan_basico
from studymate.llm.preguntas import generar_preguntas
from studymate.sesion.controlador import ControladorSesion, Fase
from studymate.sesion.historial import RegistroSesion, guardar_registro
from studymate.vision import config, modelos
from studymate.vision.motor import MotorDeteccion

from .comun import Trabajo
from .pantallas.acceso import PantallaAcceso
from .pantallas.bienvenida import PantallaBienvenida
from .pantallas.cuestionario import PantallaCuestionario
from .pantallas.elegir import PantallaElegir
from .pantallas.descanso import PantallaDescanso
from .pantallas.historial import PantallaHistorial
from .pantallas.inicio import PantallaInicio
from .pantallas.plan import PantallaPlan
from .pantallas.preparacion import PantallaPreparacion
from .pantallas.resumen import PantallaResumen
from .pantallas.sesion import PantallaSesion
from .pantallas.test import PantallaTest

SEGUNDOS_POR_MINUTO_PRUEBA = 10  # modo prueba: cada minuto del plan dura 10 s


def modelo_movil() -> str:
    """YOLO26s si está descargado (detecta mejor), si no el de config.py."""
    if (Path(modelos.CARPETA) / modelos.MODELOS["yolo_s"][0]).exists():
        return "yolo_s"
    return config.MODELO_OBJETOS


class VentanaPrincipal(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("StudyMate")
        self.usuario: us.Usuario | None = None
        self.carpeta = None           # carpeta de datos del usuario que ha entrado
        self.asignatura = ""          # asignatura de la sesión (la del animal elegido)
        self.perfil: PerfilSesion | None = None
        self.apuntes = ""
        self.modo_prueba = False
        self.plan: Plan | None = None
        self.motor: MotorDeteccion | None = None
        self.controlador: ControladorSesion | None = None
        # (asignatura, resultado) de la última sesión, para el panel principal.
        self.ultima_sesion: tuple[str, pc.ResultadoCalificacion] | None = None
        self._preguntas: dict[int, tuple[str, object]] = {}
        self._trabajos: list[Trabajo] = []

        self.pila = QStackedWidget()
        self.setCentralWidget(self.pila)
        self.paginas = {
            "acceso": PantallaAcceso(self),
            "bienvenida": PantallaBienvenida(self),
            "elegir": PantallaElegir(self),
            "inicio": PantallaInicio(self),
            "cuestionario": PantallaCuestionario(self),
            "plan": PantallaPlan(self),
            "preparacion": PantallaPreparacion(self),
            "sesion": PantallaSesion(self),
            "test": PantallaTest(self),
            "descanso": PantallaDescanso(self),
            "resumen": PantallaResumen(self),
            "historial": PantallaHistorial(self),
        }
        for pagina in self.paginas.values():
            self.pila.addWidget(pagina)

        self.reloj = QTimer(self)
        self.reloj.setInterval(50)
        self.reloj.timeout.connect(self._tick)
        self.ir("acceso")

    # --- Navegación -------------------------------------------------------------------
    def ir(self, nombre: str) -> None:
        actual = self.pila.currentWidget()
        if actual is not None:
            actual.al_ocultar()
        pagina = self.paginas[nombre]
        self.pila.setCurrentWidget(pagina)
        pagina.al_mostrar()

    def ir_cuestionario(self) -> None:
        self.ir("elegir")

    # --- Usuario ------------------------------------------------------------------------
    def sesion_iniciada(self, usuario: us.Usuario) -> None:
        self.usuario = usuario
        self.carpeta = usuario.carpeta()
        self.ultima_sesion = None
        self.setWindowTitle(f"StudyMate · {usuario.nombre}")
        # La primera vez (zoo sin asignaturas) se crea el zoo.
        self.ir("inicio" if z.cargar(self.carpeta).recintos else "bienvenida")

    def cerrar_sesion(self) -> None:
        self._parar_motor()
        self.usuario = self.carpeta = None
        self.asignatura = ""
        self.ultima_sesion = None
        self.setWindowTitle("StudyMate")
        self.ir("acceso")

    def elegir_asignatura(self, asignatura: str) -> None:
        """Al elegir el animal de una asignatura se abre su cuestionario."""
        self.asignatura = asignatura
        self.ir("cuestionario")

    # --- Cuestionario y plan -----------------------------------------------------------
    def cuestionario_listo(self, perfil: PerfilSesion, apuntes: str, modo_prueba: bool) -> None:
        self.perfil, self.apuntes, self.modo_prueba = perfil, apuntes, modo_prueba
        self.plan = None
        self.ir("plan")
        self.paginas["plan"].cargando()
        apuntes_plan = para_plan(apuntes, perfil.temas) if apuntes else None
        self._lanzar(lambda: generar_plan(perfil, apuntes=apuntes_plan), "plan",
                     self._plan_listo, self._plan_fallo)

    def _plan_listo(self, _etiqueta, plan: Plan) -> None:
        self.plan = plan
        self.paginas["plan"].mostrar(plan)

    def _plan_fallo(self, _etiqueta, error: str) -> None:
        self._plan_listo(None, plan_basico(self.perfil, f"No se ha podido crear el plan ({error})."))

    # --- Preparación y sesión ------------------------------------------------------------
    def empezar_preparacion(self) -> None:
        if self.plan is None:
            return
        self._parar_motor()
        self.motor = MotorDeteccion(
            clases_permitidas=self.perfil.clases_permitidas,
            indice_camara=config.INDICE_CAMARA,
            modelo_movil=modelo_movil(),
            movil_a_la_vista=self.perfil.movil_a_la_vista,
        )
        self.motor.start()
        self.controlador = None
        self._preguntas = {}
        self.reloj.start()
        self.ir("preparacion")

    def empezar_sesion(self) -> None:
        spm = SEGUNDOS_POR_MINUTO_PRUEBA if self.modo_prueba else 60
        self.controlador = ControladorSesion(self.plan, con_test=self.perfil.con_test,
                                             segundos_por_minuto=spm)
        self.motor.empezar_sesion()
        self._preparar_test(0)
        self.ir("sesion")

    def cancelar_sesion(self) -> None:
        self._parar_motor()
        self.ir("inicio")

    def responder_duda(self, estudiando: bool) -> None:
        if self.motor is not None:
            self.motor.confirmar_dudoso(estudiando)

    def _tick(self) -> None:
        motor = self.motor
        if motor is None:
            return
        if motor.error is not None:
            error = motor.error
            self._parar_motor()
            QMessageBox.warning(self, "Cámara", f"No se ha podido usar la cámara:\n{error}")
            self.ir("inicio")
            return
        inst = motor.ultima()
        pagina = self.pila.currentWidget()
        if hasattr(pagina, "con_instantanea"):
            pagina.con_instantanea(inst)
        c = self.controlador
        if c is not None and inst is not None and motor.en_sesion and c.fase == Fase.ESTUDIO:
            if c.actualizar(inst.estado, inst.estudiado_s):
                self._cambio_fase()

    def _cambio_fase(self) -> None:
        c = self.controlador
        if c.fase == Fase.TEST:
            self.motor.pausar_sesion()
            self.ir("test")
        elif c.fase == Fase.DESCANSO:
            self.motor.pausar_sesion()
            c.empezar_descanso(time.monotonic())
            self.ir("descanso")
        elif c.fase == Fase.ESTUDIO:
            self.motor.reanudar_sesion()
            self._preparar_test(c.indice)
            self.ir("sesion")
        else:
            self._terminar()

    def test_terminado(self, aciertos: int, total: int) -> None:
        if self.controlador is not None and self.controlador.fase == Fase.TEST:
            self.controlador.terminar_test(aciertos, total)
            self._cambio_fase()

    def descanso_terminado(self) -> None:
        if self.controlador is not None and self.controlador.fase == Fase.DESCANSO:
            self.controlador.terminar_descanso()
            self._cambio_fase()

    def terminar_sesion(self) -> None:
        if self.controlador is not None:
            self.controlador.terminar_antes()
            self._terminar()

    def _terminar(self) -> None:
        c = self.controlador
        self._parar_motor()
        resumen = c.resumen()
        resultado = pc.calificar(resumen)
        asignatura = self.perfil.asignatura
        zoo = z.cargar(self.carpeta)
        cambios = z.aplicar_sesion(zoo, asignatura, resultado, minutos=resumen.estudiado_s / 60)
        z.guardar(zoo, self.carpeta)
        if resultado.cuenta:
            self.ultima_sesion = (asignatura, resultado)
        guardar_registro(RegistroSesion(
            temas=[b.tema for b in self.plan.bloques],
            planificado_min=round(resumen.planificado_s / 60, 1),
            estudiado_min=round(resumen.estudiado_s / 60, 1),
            pausas_movil=c.pausas_movil,
            pausas_ausente=c.pausas_ausente,
            calificacion=resultado.calificacion.value if resultado.cuenta else "corta",
            puntuacion=resultado.puntuacion,
            bloques_completados=c.bloques_completados,
            bloques_totales=c.numero_bloques,
            test_aciertos=c.test_aciertos if c.test_total else None,
            test_total=c.test_total or None,
            origen_plan=self.plan.origen,
            modo_prueba=self.modo_prueba,
            asignatura=asignatura,
        ), self.carpeta)
        self.ir("resumen")
        self.paginas["resumen"].mostrar(resultado, zoo.recinto(asignatura), cambios, c, c.terminada_antes)

    # --- Preguntas del test (se piden al empezar cada bloque) -----------------------------
    def _preparar_test(self, indice: int) -> None:
        if not self.perfil.con_test or indice in self._preguntas:
            return
        bloque = self.plan.bloques[indice]
        if not bloque.minutos_test:
            return
        texto = (f"Tema del bloque: {bloque.tema}\nObjetivo del bloque: {bloque.objetivo}\n\n"
                 + (para_test(self.apuntes, bloque.tema, bloque.objetivo) if self.apuntes
                    else "No hay apuntes: pregunta por los conceptos básicos de este tema."))
        self._preguntas[indice] = ("cargando", None)
        self._lanzar(lambda: generar_preguntas(texto, consultar_groq), indice,
                     self._preguntas_listas, self._preguntas_fallo)

    def _preguntas_listas(self, indice, preguntas) -> None:
        self._preguntas[indice] = ("listo", preguntas)
        self._avisar_test()

    def _preguntas_fallo(self, indice, error: str) -> None:
        self._preguntas[indice] = ("error", error)
        self._avisar_test()

    def _avisar_test(self) -> None:
        if self.pila.currentWidget() is self.paginas["test"]:
            self.paginas["test"].actualizar_preguntas()

    def preguntas_del_bloque(self) -> tuple[str, object]:
        indice = self.controlador.indice
        return self._preguntas.get(indice, ("error", "No se pidieron preguntas para este bloque."))

    # --- Utilidades -----------------------------------------------------------------------
    def _lanzar(self, funcion, etiqueta, al_terminar, al_fallar) -> None:
        # Se guardan las referencias para que Python no los borre mientras trabajan.
        self._trabajos = [t for t in self._trabajos if not t.isFinished()]
        trabajo = Trabajo(funcion, etiqueta, self)
        trabajo.listo.connect(al_terminar)
        trabajo.fallo.connect(al_fallar)
        self._trabajos.append(trabajo)
        trabajo.start()

    def _parar_motor(self) -> None:
        self.reloj.stop()
        if self.motor is not None:
            self.motor.detener()
            self.motor.join(timeout=3)  # suelta la cámara antes de volver a abrirla
            self.motor = None

    def closeEvent(self, evento):
        self._parar_motor()
        for trabajo in list(self._trabajos):
            trabajo.wait(2000)
        super().closeEvent(evento)
