"""Test de 5 preguntas al final de un bloque (RF7). Se responde con el ratón o
con las teclas A, B y C; Enter pasa a la siguiente."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout

from studymate.sesion.controlador import que_repasar

from ..comun import Pagina, boton, etiqueta, tarjeta
from ..companero import Companero

LETRAS = ("A", "B", "C")


def _poner_estilo(boton_, nombre: str) -> None:
    """Cambia el aspecto de un botón (verde si es la correcta, rojo si se falló)."""
    boton_.setObjectName(nombre)
    boton_.style().unpolish(boton_)
    boton_.style().polish(boton_)


class PantallaTest(Pagina):
    def __init__(self, ventana):
        super().__init__(ventana)
        self.preguntas: list[dict] = []
        self.respuestas: list[str] = []
        self.actual = 0
        self.respondida = False
        self.terminado = False

        self.companero = Companero("pregunta", lado_minimo=64)
        self.companero.setFixedSize(64, 64)
        self.titulo = etiqueta("", "titulo")
        self.titulo.setTextFormat(Qt.PlainText)
        self.progreso = etiqueta("", "subtitulo")
        cabecera = QHBoxLayout()
        cabecera.addWidget(self.companero)
        textos = QVBoxLayout()
        textos.addWidget(self.titulo)
        textos.addWidget(self.progreso)
        cabecera.addLayout(textos, 1)

        self.enunciado = etiqueta("", "cifra", ajustar=True)
        self.enunciado.setTextFormat(Qt.PlainText)
        self.opciones = [boton("", "opcion", lambda _=False, l=l: self._responder(l)) for l in LETRAS]
        self.explicacion = etiqueta("")
        self.explicacion.setTextFormat(Qt.PlainText)
        self.caja = tarjeta(self.enunciado, *self.opciones, self.explicacion, espacio=12, margen=24)

        self.saltar = boton("Saltar el test", None, self._saltar)
        self.siguiente = boton("Siguiente  (Enter)", "primario", self._siguiente)
        botones = QHBoxLayout()
        botones.addWidget(self.saltar)
        botones.addStretch()
        botones.addWidget(self.siguiente)

        capa = QVBoxLayout(self)
        capa.setContentsMargins(28, 24, 28, 24)
        capa.setSpacing(16)
        capa.addLayout(cabecera)
        capa.addWidget(self.caja, 1)
        capa.addLayout(botones)

    # --- Carga de las preguntas (se generan en segundo plano al empezar el bloque)
    def al_mostrar(self) -> None:
        c = self.ventana.controlador
        self.titulo.setText(f"Test del bloque {c.indice + 1} · {c.bloque.tema}")
        self.preguntas, self.respuestas, self.actual = [], [], 0
        self.respondida = self.terminado = False
        self.actualizar_preguntas()
        self.setFocus()

    def actualizar_preguntas(self) -> None:
        """La ventana lo llama también cuando terminan de generarse."""
        if self.preguntas:
            return
        estado, datos = self.ventana.preguntas_del_bloque()
        if estado == "listo":
            self.preguntas = datos
            self._mostrar_pregunta()
        elif estado == "error":
            self._mensaje("No se ha podido preparar el test",
                          f"{datos}\n\nPuedes continuar sin test.", "triste")
        else:
            self._mensaje("Preparando las preguntas…",
                          "El asistente está escribiendo 5 preguntas sobre este bloque.", "pregunta")

    def _mensaje(self, titulo: str, texto: str, cara: str) -> None:
        self.companero.set_expresion(cara)
        self.progreso.setText("")
        self.enunciado.setText(titulo)
        self.explicacion.setText(texto)
        for b in self.opciones:
            b.hide()
        self.siguiente.setText("Continuar sin test")
        self.siguiente.setEnabled(True)
        self.terminado = True

    # --- Preguntas -------------------------------------------------------------------
    def _mostrar_pregunta(self) -> None:
        p = self.preguntas[self.actual]
        self.companero.set_expresion("pregunta")
        self.progreso.setText(f"Pregunta {self.actual + 1} de {len(self.preguntas)}  ·  "
                              "responde con el ratón o con A, B y C")
        self.enunciado.setText(p["enunciado"])
        for letra, b, texto in zip(LETRAS, self.opciones, p["opciones"]):
            b.setText(f"{letra}.  {texto}")
            _poner_estilo(b, "opcion")
            b.setEnabled(True)
            b.show()
        self.explicacion.setText("")
        self.siguiente.setText("Siguiente  (Enter)")
        self.siguiente.setEnabled(False)
        self.respondida = False
        self.terminado = False

    def _responder(self, letra: str) -> None:
        if self.respondida or self.terminado or not self.preguntas:
            return
        p = self.preguntas[self.actual]
        self.respuestas.append(letra)
        self.respondida = True
        acierto = letra == p["correcta"]
        for l, b in zip(LETRAS, self.opciones):
            if l == p["correcta"]:
                _poner_estilo(b, "correcta")
            elif l == letra:
                _poner_estilo(b, "fallada")
        self.companero.set_expresion("feliz" if acierto else "triste")
        self.explicacion.setText(("✓ ¡Correcto! " if acierto else f"✗ La correcta era la {p['correcta']}. ")
                                 + p["explicacion"])
        self.siguiente.setEnabled(True)
        self.siguiente.setFocus()

    def _siguiente(self) -> None:
        if self.terminado:
            self._finalizar()
            return
        if not self.respondida:
            return
        self.actual += 1
        if self.actual < len(self.preguntas):
            self._mostrar_pregunta()
        else:
            self._resultado()

    def _resultado(self) -> None:
        aciertos = sum(r == p["correcta"] for r, p in zip(self.respuestas, self.preguntas))
        total = len(self.preguntas)
        repasar = que_repasar(self.preguntas, self.respuestas)
        self.terminado = True
        self._aciertos, self._total = aciertos, total
        self.companero.set_expresion("feliz" if aciertos >= total * 0.7 else "concentrado")
        self.progreso.setText("")
        self.enunciado.setText(f"Has acertado {aciertos} de {total}")
        for b in self.opciones:
            b.hide()
        if repasar:
            self.explicacion.setText("Qué repasar:\n\n" + "\n\n".join(f"•  {r}" for r in repasar))
        else:
            self.explicacion.setText("¡Todo correcto! Este bloque lo llevas bien.")
        self.siguiente.setText("Continuar  (Enter)")
        self.siguiente.setEnabled(True)
        self.siguiente.setFocus()

    def _finalizar(self) -> None:
        aciertos, total = getattr(self, "_aciertos", 0), getattr(self, "_total", 0)
        self._aciertos = self._total = 0
        self.ventana.test_terminado(aciertos, total)

    def _saltar(self) -> None:
        self._aciertos = self._total = 0
        self.ventana.test_terminado(0, 0)

    def keyPressEvent(self, evento):
        teclas = {Qt.Key_A: "A", Qt.Key_B: "B", Qt.Key_C: "C"}
        if evento.key() in teclas and self.opciones[0].isVisible():
            self._responder(teclas[evento.key()])
        elif evento.key() in (Qt.Key_Return, Qt.Key_Enter) and self.siguiente.isEnabled():
            self._siguiente()
        else:
            super().keyPressEvent(evento)
