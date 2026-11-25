"""Controlador de la sesión: qué toca en cada momento según el plan.

Sigue el plan bloque a bloque: ESTUDIO -> TEST (si lo quiere) -> DESCANSO
(menos tras el último bloque) -> siguiente bloque ... -> TERMINADA.

Un bloque de estudio termina cuando se ha estudiado *de verdad* su tiempo
(el que cuenta la cámara), no cuando pasan los minutos del reloj. Así, si coge
el móvil, el bloque se alarga lo que haya estado sin estudiar.

También cuenta las veces que se coge el móvil o se ausenta (para calificar la
sesión y la pecera). Es lógica pura: la interfaz le pasa el estado y el tiempo
estudiado que da MotorDeteccion y pregunta qué mostrar.
"""

from dataclasses import dataclass, field
from enum import Enum

from studymate.gamificacion.pecera import ResumenSesion
from studymate.llm.plan import Bloque, Plan
from studymate.vision.estados import Estado


class Fase(str, Enum):
    ESTUDIO = "estudio"
    TEST = "test"
    DESCANSO = "descanso"
    TERMINADA = "terminada"


@dataclass
class ControladorSesion:
    plan: Plan
    con_test: bool = True
    # 60 en una sesión normal. En "modo prueba" cada minuto del plan dura menos
    # (p. ej., 10 s) para poder probar la aplicación entera en poco tiempo.
    segundos_por_minuto: float = 60.0

    fase: Fase = Fase.ESTUDIO
    indice: int = 0
    estudiado_s: float = 0.0
    pausas_movil: int = 0
    pausas_ausente: int = 0
    test_aciertos: int = 0
    test_total: int = 0
    terminada_antes: bool = False
    estudiado_por_bloque: list[float] = field(default_factory=list)
    _inicio_bloque_s: float = 0.0
    _estado_anterior: Estado | None = None
    _ha_estudiado: bool = False
    _inicio_descanso: float | None = None

    # --- Consultas ------------------------------------------------------------
    @property
    def bloque(self) -> Bloque:
        return self.plan.bloques[min(self.indice, len(self.plan.bloques) - 1)]

    @property
    def numero_bloques(self) -> int:
        return len(self.plan.bloques)

    @property
    def es_ultimo_bloque(self) -> bool:
        return self.indice >= len(self.plan.bloques) - 1

    @property
    def objetivo_bloque_s(self) -> float:
        return self.bloque.minutos_estudio * self.segundos_por_minuto

    @property
    def estudiado_bloque_s(self) -> float:
        return max(0.0, self.estudiado_s - self._inicio_bloque_s)

    @property
    def restante_bloque_s(self) -> float:
        return max(0.0, self.objetivo_bloque_s - self.estudiado_bloque_s)

    @property
    def progreso_bloque(self) -> float:
        return min(1.0, self.estudiado_bloque_s / self.objetivo_bloque_s) if self.objetivo_bloque_s else 1.0

    @property
    def planificado_s(self) -> float:
        return sum(b.minutos_estudio for b in self.plan.bloques) * self.segundos_por_minuto

    @property
    def toca_test(self) -> bool:
        return self.con_test and self.bloque.minutos_test > 0

    def duracion_descanso_s(self) -> float:
        return self.bloque.minutos_descanso * self.segundos_por_minuto

    def restante_descanso(self, ahora: float) -> float:
        if self._inicio_descanso is None:
            return self.duracion_descanso_s()
        return max(0.0, self.duracion_descanso_s() - (ahora - self._inicio_descanso))

    # --- Estudio ----------------------------------------------------------------
    def actualizar(self, estado: Estado, estudiado_total_s: float) -> bool:
        """Le llega el estado y el tiempo estudiado del motor. True si cambia la fase."""
        if self.fase != Fase.ESTUDIO:
            return False
        self._contar_pausa(estado)
        self.estudiado_s = estudiado_total_s
        if self.estudiado_bloque_s >= self.objetivo_bloque_s:
            self._fin_estudio_bloque()
            return True
        return False

    def _contar_pausa(self, estado: Estado) -> None:
        anterior, self._estado_anterior = self._estado_anterior, estado
        if estado == Estado.ESTUDIANDO:
            self._ha_estudiado = True
        if not self._ha_estudiado or estado == anterior:
            return  # al empezar todavía no se ha sentado: no cuenta como ausencia
        if estado == Estado.USANDO_MOVIL:
            self.pausas_movil += 1
        elif estado == Estado.AUSENTE:
            self.pausas_ausente += 1

    def _fin_estudio_bloque(self) -> None:
        self.estudiado_por_bloque.append(self.estudiado_bloque_s)
        if self.toca_test:
            self.fase = Fase.TEST
        else:
            self._tras_test()

    # --- Test y descanso ----------------------------------------------------------
    def terminar_test(self, aciertos: int, total: int) -> None:
        """Resultado del test del bloque (0 de 0 si no se pudo hacer)."""
        if self.fase != Fase.TEST:
            return
        self.test_aciertos += aciertos
        self.test_total += total
        self._tras_test()

    def _tras_test(self) -> None:
        if self.es_ultimo_bloque:
            self.fase = Fase.TERMINADA
        elif self.bloque.minutos_descanso > 0:
            self.fase = Fase.DESCANSO
            self._inicio_descanso = None
        else:
            self._siguiente_bloque()

    def empezar_descanso(self, ahora: float) -> None:
        if self.fase == Fase.DESCANSO and self._inicio_descanso is None:
            self._inicio_descanso = ahora

    def terminar_descanso(self) -> None:
        if self.fase == Fase.DESCANSO:
            self._siguiente_bloque()

    def _siguiente_bloque(self) -> None:
        self.indice += 1
        self._inicio_bloque_s = self.estudiado_s
        self._inicio_descanso = None
        self.fase = Fase.ESTUDIO

    def terminar_antes(self) -> None:
        """El estudiante termina la sesión antes de acabar el plan."""
        if self.fase == Fase.ESTUDIO:
            self.estudiado_por_bloque.append(self.estudiado_bloque_s)
        self.terminada_antes = self.fase != Fase.TERMINADA
        self.fase = Fase.TERMINADA

    # --- Resultado -----------------------------------------------------------------
    @property
    def bloques_completados(self) -> int:
        completos = sum(
            1 for i, s in enumerate(self.estudiado_por_bloque)
            if s >= self.plan.bloques[i].minutos_estudio * self.segundos_por_minuto - 1
        )
        return min(completos, self.numero_bloques)

    def resumen(self) -> ResumenSesion:
        """Lo que necesita la pecera para calificar la sesión (en segundos "reales"
        del plan: en modo prueba se escala para que la nota sea comparable)."""
        escala = 60.0 / self.segundos_por_minuto
        return ResumenSesion(
            planificado_s=self.planificado_s * escala,
            estudiado_s=self.estudiado_s * escala,
            pausas_movil=self.pausas_movil,
            pausas_ausente=self.pausas_ausente,
            test_aciertos=self.test_aciertos if self.test_total else None,
            test_total=self.test_total or None,
        )


def que_repasar(preguntas: list[dict], respuestas: list[str]) -> list[str]:
    """Consejo de repaso tras un test: lo que se ha fallado, con su explicación."""
    consejos = []
    for pregunta, respuesta in zip(preguntas, respuestas):
        if respuesta != pregunta["correcta"]:
            consejos.append(f"{pregunta['enunciado']} → {pregunta['explicacion']}")
    return consejos
