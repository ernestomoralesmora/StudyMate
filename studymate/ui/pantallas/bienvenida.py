"""Primera vez: crear el zoo. Nombre del zoo y las asignaturas, cada una con su animal."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QScrollArea, QVBoxLayout, QWidget

from studymate.gamificacion import zoo as z

from ..comun import Pagina, boton, etiqueta, tarjeta
from ..dialogo_asignatura import DialogoAsignatura
from ..zoo_widget import AnimalIcono


class PantallaBienvenida(Pagina):
    def __init__(self, ventana):
        super().__init__(ventana)
        self.saludo = etiqueta("", "titulo")
        self.nombre_zoo = QLineEdit()
        self.nombre_zoo.setMaxLength(40)
        titulo_nombre = etiqueta("1. ¿Cómo se va a llamar tu zoo?")
        titulo_nombre.setStyleSheet("font-weight: 600;")
        titulo_nombre.setBuddy(self.nombre_zoo)

        self.lista = QWidget()
        self.capa_lista = QVBoxLayout(self.lista)
        self.capa_lista.setContentsMargins(0, 0, 0, 0)
        self.capa_lista.setSpacing(8)
        desplazable = QScrollArea()
        desplazable.setWidgetResizable(True)
        desplazable.setWidget(self.lista)
        desplazable.setMinimumHeight(220)

        self.error = etiqueta("", "error")
        self.crear = boton("Crear mi zoo", "primario", self._crear)
        caja = tarjeta(
            titulo_nombre, self.nombre_zoo,
            etiqueta("2. ¿Qué asignaturas tienes este curso? Añade cada una y elige su animal "
                     "(uno distinto por asignatura). Los apuntes de cada una se suben al estudiarla.", None),
            boton("Añadir una asignatura", None, self._anadir),
            desplazable, self.error, self.crear,
            espacio=14, margen=28,
        )
        caja.setMaximumWidth(760)

        capa = QVBoxLayout(self)
        capa.setContentsMargins(28, 24, 28, 24)
        capa.setSpacing(16)
        capa.addWidget(self.saludo)
        capa.addWidget(etiqueta("Vamos a crear tu zoo. Cada asignatura tendrá su recinto con su animal, "
                                "y crecerá con las sesiones de esa asignatura.", "subtitulo"))
        fila = QHBoxLayout()
        fila.addWidget(caja, 1)
        fila.addStretch()
        capa.addLayout(fila, 1)

    def al_mostrar(self) -> None:
        self.saludo.setText(f"¡Hola, {self.ventana.usuario.nombre.split()[0]}!")
        zoo = z.cargar(self.ventana.carpeta)
        if zoo.nombre == z.NOMBRE_POR_DEFECTO:
            self.nombre_zoo.setText(f"El zoo de {self.ventana.usuario.nombre.split()[0]}")
        else:
            self.nombre_zoo.setText(zoo.nombre)
        self._mostrar(zoo)
        self.nombre_zoo.setFocus()

    def _mostrar(self, zoo: z.Zoo) -> None:
        while self.capa_lista.count():
            item = self.capa_lista.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if not zoo.recintos:
            self.capa_lista.addWidget(etiqueta("Todavía no has añadido ninguna asignatura.", "nota"))
        for r in zoo.recintos:
            fila = QWidget()
            capa = QHBoxLayout(fila)
            capa.setContentsMargins(0, 0, 0, 0)
            capa.addWidget(AnimalIcono(r.especie, 36))
            texto = etiqueta(f"{r.asignatura}  ·  {r.animal.nombre}  ·  {r.animal.habitat.lower()}")
            texto.setTextFormat(Qt.PlainText)
            capa.addWidget(texto, 1)
            self.capa_lista.addWidget(fila)
        self.capa_lista.addStretch()
        self.crear.setEnabled(bool(zoo.recintos))

    def _anadir(self) -> None:
        dialogo = DialogoAsignatura(z.cargar(self.ventana.carpeta), self.ventana.carpeta, self)
        if dialogo.exec():
            self._mostrar(z.cargar(self.ventana.carpeta))

    def _crear(self) -> None:
        zoo = z.cargar(self.ventana.carpeta)
        try:
            zoo.renombrar(self.nombre_zoo.text())
        except z.ErrorZoo as error:
            self.error.setText(str(error))
            return
        if not zoo.recintos:
            self.error.setText("Añade al menos una asignatura.")
            return
        z.guardar(zoo, self.ventana.carpeta)
        self.ventana.ir("inicio")
