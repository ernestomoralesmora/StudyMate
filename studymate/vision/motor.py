"""Hilo de detección: cámara -> detectores -> máquina de estados -> temporizador.

Corre aparte de la interfaz. La interfaz (OpenCV ahora, PySide6 en la fase 3)
solo lee la última `Instantanea` con `ultima()` y nunca espera a la detección.
"""

import csv
import threading
import time
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass

from . import config
from .camara import Camara
from .detectores import Analizador
from .estados import Estado, MaquinaEstados
from .observacion import Observacion, SitioMovil, clasificar
from .temporizador import Temporizador


@dataclass
class Instantanea:
    frame: object  # ndarray BGR
    observacion: Observacion
    candidato: Estado
    estado: Estado
    estudiado_s: float
    pendiente_s: float
    esperando_confirmacion: bool
    fps: float
    sitio_movil: SitioMovil = SitioMovil.SIN_USAR
    en_sesion: bool = True  # False durante la preparación (el tiempo no cuenta)


class MotorDeteccion(threading.Thread):
    def __init__(
        self,
        clases_permitidas: frozenset[str] = frozenset(),
        indice_camara: int = 0,
        modelo_movil: str = config.MODELO_OBJETOS,
        movil_a_la_vista: bool = False,
    ):
        """`movil_a_la_vista`: el estudiante deja el móvil donde la cámara lo vea
        (cuestionario). Al empezar se localiza y luego se vigila su sitio."""
        super().__init__(daemon=True, name="deteccion")
        # Aunque se estudie con tablet (que la detección no distingue de un móvil),
        # el sitio del móvil se sigue vigilando: es la forma de saber si se coge.
        self.movil_a_la_vista = movil_a_la_vista
        self.clases_permitidas = clases_permitidas
        self.indice_camara = indice_camara
        self.modelo_movil = modelo_movil
        self.maquina = MaquinaEstados()
        self.temporizador = Temporizador()
        self.error: Exception | None = None
        self._cerrojo = threading.Lock()
        self._parar = threading.Event()
        self._listo = threading.Event()
        self._ultima: Instantanea | None = None
        # Hasta que se llama a empezar_sesion() solo se mira (preparación):
        # ni la máquina de estados ni el temporizador avanzan.
        self.en_sesion = False

    def run(self) -> None:
        try:
            with Camara(self.indice_camara) as camara:
                analizador = Analizador(self.modelo_movil, movil_a_la_vista=self.movil_a_la_vista)
                self._analizador = analizador
                try:
                    self._bucle(camara, analizador)
                finally:
                    analizador.cerrar()
        except Exception as e:  # se informa al hilo principal
            self.error = e
        finally:
            self._listo.set()

    def _abrir_diagnostico(self):
        """CSV con números (sin imágenes) para ver por qué cambia o no el estado."""
        if not config.REGISTRAR_DIAGNOSTICO:
            return None, None
        try:
            carpeta = Path(__file__).resolve().parents[2] / "registros"
            carpeta.mkdir(exist_ok=True)
            archivo = open(carpeta / f"diagnostico_{datetime.now():%Y%m%d_%H%M%S}.csv", "w",
                           newline="", encoding="utf-8")
        except OSError:
            return None, None
        escritor = csv.writer(archivo)
        escritor.writerow(["t", "en_sesion", "estado", "candidato", "sitio_movil", "caras", "manos",
                           "movil_mano", "descartados", "yolo_sitio", "parecido", "cambio",
                           "quietas", "vacio_aprendido", "recuadro_sitio"])
        return archivo, escritor

    def _apuntar(self, escritor, t: float, obs: Observacion, candidato) -> None:
        v = self.vigilante
        en_mano = [d for d in obs.dispositivos if d.cerca_de_mano]
        escritor.writerow([
            f"{t:.1f}", int(self.en_sesion), self.maquina.estado.value, candidato.value,
            obs.sitio_movil.value, len(obs.caras), len(obs.manos),
            max((f"{d.puntuacion:.2f}" for d in en_mano if not d.descartado), default=""),
            " ".join(f"{d.descartado}:{d.puntuacion:.2f}" for d in en_mano if d.descartado),
            f"{v.ultima_yolo:.2f}" if v else "", f"{v.ultima_similitud:.2f}" if v else "",
            f"{v.ultimo_cambio:.2f}" if v else "", v._quietas if v else "",
            int(v is not None and v.vacio is not None),
            "" if not (v and v.recuadro) else " ".join(f"{c:.0f}" for c in v.recuadro),
        ])

    def _bucle(self, camara: Camara, analizador: Analizador) -> None:
        archivo, escritor = self._abrir_diagnostico()
        try:
            self._bucle_con(camara, analizador, escritor)
        finally:
            if archivo:
                archivo.close()

    def _bucle_con(self, camara: Camara, analizador: Analizador, escritor) -> None:
        ultimo_apunte = 0.0
        inicio = time.monotonic()
        fps = 0.0
        anterior = inicio
        while not self._parar.is_set():
            frame = camara.leer()
            if frame is None:
                time.sleep(0.01)
                continue
            ahora = time.monotonic()
            obs = analizador.analizar(frame, int((ahora - inicio) * 1000))
            candidato = clasificar(obs, self.clases_permitidas)

            with self._cerrojo:
                if self.en_sesion:
                    fuera = obs.sitio_movil == SitioMovil.FUERA
                    self.maquina.actualizar(
                        candidato, ahora,
                        margen_dudoso_s=config.MARGEN_MOVIL_FUERA_S if fuera else None,
                        insistir=fuera,
                    )
                    self.temporizador.actualizar(self.maquina.estado, ahora)
                dt = ahora - anterior
                anterior = ahora
                if dt > 0:  # media móvil para que el número no baile
                    fps = 1 / dt if fps == 0 else 0.9 * fps + 0.1 / dt
                self._ultima = Instantanea(
                    frame=frame,
                    observacion=obs,
                    candidato=candidato,
                    estado=self.maquina.estado,
                    estudiado_s=self.temporizador.estudiado_s,
                    pendiente_s=self.temporizador.pendiente_s,
                    esperando_confirmacion=self.temporizador.esperando_confirmacion,
                    fps=fps,
                    sitio_movil=obs.sitio_movil,
                    en_sesion=self.en_sesion,
                )
                if escritor is not None and ahora - ultimo_apunte >= config.PERIODO_DIAGNOSTICO_S:
                    ultimo_apunte = ahora
                    try:
                        self._apuntar(escritor, ahora - inicio, obs, candidato)
                    except Exception:  # el diagnóstico nunca debe parar la detección
                        pass
            self._listo.set()

    def esperar_listo(self, timeout: float | None = None) -> bool:
        """Espera al primer fotograma analizado (o a un error)."""
        return self._listo.wait(timeout)

    def ultima(self) -> Instantanea | None:
        with self._cerrojo:
            return self._ultima

    def confirmar_dudoso(self, estaba_estudiando: bool) -> None:
        """Respuesta a "¿Sigues estudiando?": S -> ESTUDIANDO, N -> AUSENTE."""
        with self._cerrojo:
            maquina = self.maquina
            if maquina.estado != Estado.DUDOSO:
                return  # no había ninguna pregunta en curso
            descuento = (
                maquina.duda_previa_s
                if maquina.estado_antes_de_duda == Estado.ESTUDIANDO
                else 0.0
            )
            self.temporizador.confirmar_dudoso(estaba_estudiando, descuento)
            # "Sí, sigo estudiando" con el móvil fuera de su sitio: lo ha guardado
            # o movido. Ya no se vigila el sitio (solo la mano) y no se insiste.
            analizador = getattr(self, "_analizador", None)
            if estaba_estudiando and analizador is not None:
                vigilante = analizador.dispositivos.vigilante
                if vigilante.estado == SitioMovil.FUERA:
                    vigilante.desactivar()
            maquina.confirmar(
                Estado.ESTUDIANDO if estaba_estudiando else Estado.AUSENTE,
                time.monotonic(),
            )

    def marcar_movil(self, frame_bgr, recuadro) -> None:
        """El estudiante ha marcado con el ratón dónde está el móvil."""
        import cv2
        if self.vigilante is not None:
            self.vigilante.marcar_a_mano(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB), recuadro)

    def empezar_sesion(self) -> None:
        """Acaba la preparación (o una pausa): desde aquí cuentan el estado y el tiempo."""
        with self._cerrojo:
            v = self.vigilante
            if v is not None and v.estado == SitioMovil.BUSCANDO:
                v.estado = SitioMovil.NO_ENCONTRADO  # no lo marcó: solo se vigila la mano
            self.temporizador.reiniciar_reloj()
            self.en_sesion = True

    def pausar_sesion(self) -> None:
        """Test o descanso: la cámara sigue, pero ni el estado ni el tiempo avanzan."""
        with self._cerrojo:
            self.en_sesion = False

    reanudar_sesion = empezar_sesion

    @property
    def vigilante(self):
        """El VigilanteMovil (ver aparcado.py), o None si aún no ha arrancado."""
        analizador = getattr(self, "_analizador", None)
        return analizador.dispositivos.vigilante if analizador else None

    @property
    def recuadro_aparcado(self):
        """Dónde se dejó el móvil (para dibujarlo), o None."""
        return self.vigilante.recuadro if self.vigilante else None

    def detener(self) -> None:
        self._parar.set()
