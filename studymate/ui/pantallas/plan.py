"""El plan de la sesión (RF9, RF10): se genera con el asistente y se revisa antes de empezar."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QScrollArea, QVBoxLayout, QWidget

from studymate.llm.plan import Plan

from ..comun import Pagina, boton, etiqueta, tarjeta
from ..companero import Companero


class PantallaPlan(Pagina):
    def __init__(self, ventana):
        super().__init__(ventana)
        self.companero = Companero("pregunta", lado_minimo=64)
        self.companero.setFixedSize(64, 64)
        self.titulo = etiqueta("Preparando tu plan…", "titulo")
        self.subtitulo = etiqueta("El asistente está repartiendo los temas en bloques.", "subtitulo")
        cabecera = QHBoxLayout()
        cabecera.addWidget(self.companero)
        textos = QVBoxLayout()
        textos.addWidget(self.titulo)
        textos.addWidget(self.subtitulo)
        cabecera.addLayout(textos, 1)

        self.contenido = QWidget()
        self.capa_contenido = QVBoxLayout(self.contenido)
        self.capa_contenido.setContentsMargins(0, 0, 8, 0)
        self.capa_contenido.setSpacing(12)
        desplazable = QScrollArea()
        desplazable.setWidgetResizable(True)
        desplazable.setWidget(self.contenido)

        botones = QHBoxLayout()
        botones.addWidget(boton("Cambiar mis respuestas", None, lambda: ventana.ir("cuestionario")))
        botones.addStretch()
        self.empezar = boton("Preparar mi sitio y empezar", "primario", ventana.empezar_preparacion)
        botones.addWidget(self.empezar)

        capa = QVBoxLayout(self)
        capa.setContentsMargins(28, 24, 28, 24)
        capa.setSpacing(16)
        capa.addLayout(cabecera)
        capa.addWidget(desplazable, 1)
        capa.addLayout(botones)

    def _vaciar(self) -> None:
        while self.capa_contenido.count():
            item = self.capa_contenido.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def cargando(self) -> None:
        self._vaciar()
        self.companero.set_expresion("pregunta")
        self.titulo.setText("Preparando tu plan…")
        self.subtitulo.setText("El asistente está repartiendo los temas en bloques. Tarda unos segundos.")
        self.empezar.setEnabled(False)

    def mostrar(self, plan: Plan) -> None:
        self._vaciar()
        self.companero.set_expresion("feliz")
        self.titulo.setText("Tu plan para hoy")
        origen = "Plan del asistente" if plan.origen == "llm" else "Plan básico (sin asistente)"
        self.subtitulo.setText(f"{origen} · {plan.total} min en total")
        for aviso in plan.avisos:
            self.capa_contenido.addWidget(etiqueta(f"⚠  {aviso}", "aviso"))
        for i, b in enumerate(plan.bloques, start=1):
            partes = [f"{b.minutos_estudio} min de estudio"]
            if b.minutos_test:
                partes.append(f"{b.minutos_test} min de test")
            if b.minutos_descanso and i < len(plan.bloques):
                partes.append(f"{b.minutos_descanso} min de descanso")
            nombre = etiqueta(f"Bloque {i} · {b.tema}", "cifra", ajustar=True)
            nombre.setTextFormat(Qt.PlainText)
            objetivo = etiqueta(b.objetivo)
            objetivo.setTextFormat(Qt.PlainText)
            self.capa_contenido.addWidget(tarjeta(nombre, objetivo, etiqueta("  ·  ".join(partes), "nota"),
                                                  espacio=6, margen=16))
        if plan.justificacion:
            porque = etiqueta(plan.justificacion, "nota")
            porque.setTextFormat(Qt.PlainText)
            self.capa_contenido.addWidget(tarjeta(etiqueta("POR QUÉ ESTE PLAN", "seccion"), porque))
        self.capa_contenido.addStretch()
        self.empezar.setEnabled(True)
        self.empezar.setFocus()
