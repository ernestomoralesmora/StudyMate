"""Elegir apuntes de una asignatura: subir PDF, Word o texto y marcar cuáles usar.

Se usa en el cuestionario de una sesión y al preparar un test. Los apuntes se
guardan por asignatura (llm/apuntes.py: BibliotecaApuntes, solo su texto).
"""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QApplication, QCheckBox, QFileDialog, QHBoxLayout, QMessageBox,
                               QVBoxLayout, QWidget)

from studymate.llm.apuntes import BibliotecaApuntes, ErrorApuntes

from .comun import boton, etiqueta


def nombre_tema(archivo: str) -> str:
    """«E.04.01_Testing_ES_v1.15.pdf» -> «E.04.01 Testing ES v1.15» (nombre del tema)."""
    return " ".join(Path(archivo).stem.replace("_", " ").split())[:80] or archivo


class SelectorApuntes(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.biblioteca: BibliotecaApuntes | None = None
        self.asignatura = ""
        self.casillas: list[tuple[QCheckBox, str]] = []  # (casilla, id del documento)

        fila = QHBoxLayout()
        fila.setContentsMargins(0, 0, 0, 0)
        fila.addWidget(boton("Subir apuntes (PDF, Word o texto)…", "primario", self._subir))
        for texto, valor in (("Marcar todos", True), ("Ninguno", False)):
            fila.addWidget(boton(texto, None, lambda _=False, v=valor: self.marcar_todos(v)))
        fila.addStretch()
        self.error = etiqueta("", "error")
        self.error.hide()
        self.lista = QWidget()
        self.capa_lista = QVBoxLayout(self.lista)
        self.capa_lista.setContentsMargins(0, 0, 0, 0)
        self.capa_lista.setSpacing(6)

        capa = QVBoxLayout(self)
        capa.setContentsMargins(0, 0, 0, 0)
        capa.setSpacing(8)
        capa.addLayout(fila)
        capa.addWidget(self.error)
        capa.addWidget(self.lista)

    # --- Uso desde las pantallas --------------------------------------------------------
    def cargar(self, carpeta_usuario, asignatura: str, marcados: set[str] | None = None) -> None:
        """Muestra los apuntes de la asignatura. Sin `marcados`, todos marcados."""
        self.biblioteca = BibliotecaApuntes(carpeta_usuario, asignatura)
        self.asignatura = asignatura
        self.error.hide()
        guardados = {d.id for d in self.biblioteca.documentos()}
        elegidos = (marcados & guardados) if marcados is not None else guardados
        self._mostrar(elegidos or guardados)

    def marcados(self) -> set[str]:
        return {id_ for casilla, id_ in self.casillas if casilla.isChecked()}

    def elegidos(self) -> list[tuple[str, str]]:
        """(nombre, texto) de los apuntes marcados."""
        return self.biblioteca.elegidos(sorted(self.marcados())) if self.biblioteca else []

    def hay_apuntes(self) -> bool:
        return bool(self.casillas)

    def marcar_todos(self, valor: bool) -> None:
        for casilla, _ in self.casillas:
            casilla.setChecked(valor)

    # --- Interno ----------------------------------------------------------------------------
    def _subir(self) -> None:
        rutas, _ = QFileDialog.getOpenFileNames(
            self, "Elige tus apuntes", str(Path.home()),
            "Apuntes (*.pdf *.docx *.txt *.md);;PDF (*.pdf);;Word (*.docx);;Texto (*.txt *.md)",
        )
        if not rutas or self.biblioteca is None:
            return
        marcados = self.marcados()
        errores = []
        QApplication.setOverrideCursor(Qt.WaitCursor)  # un PDF largo tarda unos segundos
        try:
            for ruta in rutas:
                try:
                    marcados.add(self.biblioteca.anadir(ruta).id)  # los recién subidos, marcados
                except ErrorApuntes as error:
                    errores.append(str(error))
        finally:
            QApplication.restoreOverrideCursor()
        self.error.setText("\n".join(errores))
        self.error.setVisible(bool(errores))
        self._mostrar(marcados)

    def _quitar(self, id_documento: str, nombre: str) -> None:
        respuesta = QMessageBox.question(
            self, "Quitar apuntes", f"¿Quitar «{nombre}» de los apuntes de {self.asignatura}? "
            "Tendrías que volver a subirlo para usarlo.")
        if respuesta != QMessageBox.Yes:
            return
        marcados = self.marcados() - {id_documento}
        self.biblioteca.quitar(id_documento)
        self._mostrar(marcados)

    def _mostrar(self, marcados: set[str]) -> None:
        while self.capa_lista.count():
            item = self.capa_lista.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.casillas = []
        documentos = self.biblioteca.documentos() if self.biblioteca else []
        if not documentos:
            self.capa_lista.addWidget(etiqueta("Esta asignatura aún no tiene apuntes guardados.", "nota"))
        for d in documentos:
            fila = QWidget()
            capa = QHBoxLayout(fila)
            capa.setContentsMargins(0, 0, 0, 0)
            fecha = d.subido[8:10] + "/" + d.subido[5:7]
            casilla = QCheckBox(f"{d.nombre}  ·  {max(1, d.caracteres // 1000)} mil caracteres  ·  subido el {fecha}")
            casilla.setChecked(d.id in marcados)
            self.casillas.append((casilla, d.id))
            quitar = boton("Quitar", None, lambda _=False, i=d.id, n=d.nombre: self._quitar(i, n))
            quitar.setAccessibleName(f"Quitar {d.nombre} de los apuntes")
            capa.addWidget(casilla, 1)
            capa.addWidget(quitar)
            self.capa_lista.addWidget(fila)
