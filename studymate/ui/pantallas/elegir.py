"""Nueva sesión: elige el animal de la asignatura que vas a estudiar."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QPushButton, QScrollArea, QVBoxLayout, QWidget

from studymate.gamificacion import zoo as z
from studymate.llm.apuntes import BibliotecaApuntes

from ..comun import Pagina, boton, etiqueta
from ..zoo_widget import AnimalIcono


class BotonAsignatura(QPushButton):
    def __init__(self, recinto: z.Recinto, al_elegir, apuntes: int = 0):
        super().__init__()
        self.setObjectName("eleccion")
        self.setFixedSize(220, 210)
        self.setAccessibleName(f"Estudiar {recinto.asignatura} ({recinto.animal.nombre})")
        capa = QVBoxLayout(self)
        capa.setContentsMargins(12, 14, 12, 12)
        capa.setSpacing(6)
        icono = AnimalIcono(recinto.especie, 72)
        icono.setAttribute(Qt.WA_TransparentForMouseEvents)
        nombre = etiqueta(recinto.asignatura, "cifra", ajustar=True)
        nombre.setTextFormat(Qt.PlainText)
        nombre.setAlignment(Qt.AlignCenter)
        nombre.setStyleSheet("font-size: 17px;")
        guardados = f"{apuntes} apuntes guardados" if apuntes != 1 else "1 apunte guardado"
        detalle = etiqueta(f"{recinto.describir_animales()}\n{guardados if apuntes else 'sin apuntes todavía'}",
                           "nota", ajustar=True)
        detalle.setTextFormat(Qt.PlainText)
        detalle.setAlignment(Qt.AlignCenter)
        for w in (nombre, detalle):
            w.setAttribute(Qt.WA_TransparentForMouseEvents)
        capa.addWidget(icono, 0, Qt.AlignHCenter)
        capa.addWidget(nombre)
        capa.addWidget(detalle)
        self.clicked.connect(lambda: al_elegir(recinto.asignatura))


class PantallaElegir(Pagina):
    def __init__(self, ventana):
        super().__init__(ventana)
        self.contenido = QWidget()
        self.rejilla = QGridLayout(self.contenido)
        self.rejilla.setSpacing(16)
        self.rejilla.setContentsMargins(0, 0, 8, 0)
        desplazable = QScrollArea()
        desplazable.setWidgetResizable(True)
        desplazable.setWidget(self.contenido)
        fila = QHBoxLayout()
        fila.addWidget(boton("Volver al zoo", None, lambda: ventana.ir("inicio")))
        fila.addStretch()
        capa = QVBoxLayout(self)
        capa.setContentsMargins(28, 24, 28, 24)
        capa.setSpacing(16)
        capa.addWidget(etiqueta("Nueva sesión", "titulo"))
        capa.addWidget(etiqueta("¿Qué vas a estudiar? Elige el animal de la asignatura.", "subtitulo"))
        capa.addWidget(desplazable, 1)
        capa.addLayout(fila)

    def al_mostrar(self) -> None:
        while self.rejilla.count():
            item = self.rejilla.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        zoo = z.cargar(self.ventana.carpeta)
        primero = None
        for i, r in enumerate(zoo.recintos):
            apuntes = len(BibliotecaApuntes(self.ventana.carpeta, r.asignatura).documentos())
            b = BotonAsignatura(r, self.ventana.elegir_asignatura, apuntes)
            primero = primero or b
            self.rejilla.addWidget(b, i // 5, i % 5, Qt.AlignTop | Qt.AlignLeft)
        self.rejilla.setRowStretch((len(zoo.recintos) + 4) // 5, 1)
        self.rejilla.setColumnStretch(5, 1)
        if primero:
            primero.setFocus()
