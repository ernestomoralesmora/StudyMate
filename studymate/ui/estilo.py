"""Colores y hoja de estilo de la interfaz (los del logo y los mock-ups).

Cada estado de la detección tiene su color, y el estado se dice también con
texto (no solo con color), para que sea accesible.
"""

FONDO = "#07110D"
SUPERFICIE = "#0F2219"
SUPERFICIE_2 = "#13291F"
BORDE = "#1E3A2C"
TEXTO = "#E8FFF1"
TEXTO_2 = "#9FC2AE"
ACENTO = "#39FF88"
CIAN = "#00C2FF"
MOVIL = "#FF8A5C"
AUSENTE = "#FF6B6B"
DUDOSO = "#FFC94D"

COLOR_ESTADO = {
    "ESTUDIANDO": ACENTO,
    "AUSENTE": AUSENTE,
    "USANDO_MOVIL": MOVIL,
    "DUDOSO": DUDOSO,
}
NOMBRE_ESTADO = {
    "ESTUDIANDO": "Estudiando",
    "AUSENTE": "Ausente",
    "USANDO_MOVIL": "Usando el móvil",
    "DUDOSO": "¿Sigues ahí?",
}
COLOR_CALIFICACION = {"muy_buena": ACENTO, "regular": DUDOSO, "mala": MOVIL, "corta": TEXTO_2}
NOMBRE_CALIFICACION = {"muy_buena": "Muy buena", "regular": "Regular", "mala": "Mala", "corta": "Muy corta"}

HOJA = f"""
* {{ font-family: 'Inter', 'Segoe UI', sans-serif; }}
QMainWindow, QWidget#pagina {{ background: {FONDO}; }}
QWidget {{ color: {TEXTO}; font-size: 14px; }}
QLabel {{ background: transparent; }}
QLabel#titulo {{ font-size: 26px; font-weight: 700; }}
QLabel#subtitulo {{ font-size: 15px; color: {TEXTO_2}; }}
QLabel#seccion {{ font-size: 13px; font-weight: 700; color: {TEXTO_2}; letter-spacing: 1px; }}
QLabel#grande {{ font-size: 64px; font-weight: 700; }}
QLabel#cifra {{ font-size: 24px; font-weight: 700; }}
QLabel#nota {{ color: {TEXTO_2}; font-size: 13px; }}
QLabel#error {{ color: {AUSENTE}; }}
QLabel#aviso {{ background: #2A2410; border: 1px solid {DUDOSO}; border-radius: 10px;
               padding: 10px 12px; color: #FFE3A3; }}
QWidget#contenido_acceso {{ background: qradialgradient(cx: 0.5, cy: 0.32, radius: 0.75, fx: 0.5, fy: 0.32,
    stop: 0 #0E2A1D, stop: 1 {FONDO}); }}
QScrollArea#fondo_acceso {{ background: {FONDO}; border: 0; }}
QLabel#marca {{ font-size: 30px; font-weight: 800; letter-spacing: 0.5px; }}
QLabel#etiqueta_campo {{ font-weight: 600; font-size: 14px; }}
QFrame#tarjeta_acceso {{ background: {SUPERFICIE}; border: 1px solid #275A41; border-radius: 22px; }}
QFrame#pestanas {{ background: {FONDO}; border: 1px solid {BORDE}; border-radius: 14px; }}
QPushButton#pestana {{ background: transparent; border: 0; border-radius: 10px; min-height: 40px;
    color: {TEXTO_2}; }}
QPushButton#pestana:hover {{ color: {TEXTO}; }}
QPushButton#pestana:checked {{ background: {SUPERFICIE_2}; color: {ACENTO}; border: 1px solid {BORDE}; }}
QFrame#tarjeta {{ background: {SUPERFICIE}; border: 1px solid {BORDE}; border-radius: 16px; }}
QFrame#banner {{ background: #2A2410; border: 2px solid {DUDOSO}; border-radius: 16px; }}
QPushButton {{ min-height: 44px; border-radius: 12px; padding: 0 18px; font-weight: 600;
              background: transparent; border: 1px solid #6E8B7B; color: {TEXTO}; }}
QPushButton:hover {{ border-color: {ACENTO}; }}
QPushButton:focus {{ outline: none; border: 2px solid {ACENTO}; }}
QPushButton:disabled {{ color: #4E6B5B; border-color: #2B4A3A; }}
QPushButton#primario {{ background: {ACENTO}; color: {FONDO}; border: 0; }}
QPushButton#primario:hover {{ background: #6BFFA8; }}
QPushButton#primario:focus {{ border: 2px solid {TEXTO}; }}
QPushButton#primario:disabled {{ background: #1E5A38; color: #0B1A14; }}
QPushButton#peligro {{ border-color: {AUSENTE}; color: #FFB3B3; }}
QPushButton#opcion {{ text-align: left; padding: 12px 16px; min-height: 52px; font-weight: 500;
                     background: {SUPERFICIE_2}; border: 1px solid {BORDE}; }}
QPushButton#opcion:hover {{ border-color: {ACENTO}; }}
QPushButton#correcta {{ text-align: left; padding: 12px 16px; min-height: 52px; background: #10331F;
                       border: 2px solid {ACENTO}; }}
QPushButton#fallada {{ text-align: left; padding: 12px 16px; min-height: 52px; background: #3A1616;
                      border: 2px solid {AUSENTE}; }}
QPushButton#animal {{ background: {SUPERFICIE_2}; border: 1px solid {BORDE}; border-radius: 12px; padding: 0;
    min-height: 96px; min-width: 96px; }}
QPushButton#eleccion {{ background: {SUPERFICIE}; border: 1px solid {BORDE}; border-radius: 16px; padding: 0;
    min-height: 210px; min-width: 220px; max-width: 220px; }}
QPushButton#eleccion:hover, QPushButton#eleccion:focus {{ border: 2px solid {ACENTO}; background: {SUPERFICIE_2}; }}
QPushButton#opcion {{ background: {SUPERFICIE_2}; border: 1px solid {BORDE}; border-radius: 14px;
    padding: 0; min-height: 84px; text-align: left; }}
QPushButton#opcion:hover, QPushButton#opcion:focus {{ border: 1px solid {ACENTO}; }}
QPushButton#opcion:checked {{ background: #10331F; border: 2px solid {ACENTO}; }}
QLabel#icono_opcion {{ font-size: 30px; min-width: 44px; }}
QPushButton#animal:checked {{ background: #10331F; border: 2px solid {ACENTO}; }}
QPushButton#animal:disabled {{ background: {SUPERFICIE}; border: 1px dashed {BORDE}; }}
QDialog {{ background: {FONDO}; }}
QLineEdit, QPlainTextEdit, QSpinBox, QComboBox {{ background: {SUPERFICIE_2}; border: 1px solid {BORDE};
    border-radius: 10px; padding: 8px 10px; selection-background-color: {ACENTO};
    selection-color: {FONDO}; }}
QLineEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QComboBox:focus {{ border: 2px solid {ACENTO}; }}
QComboBox QAbstractItemView {{ background: {SUPERFICIE}; border: 1px solid {BORDE};
    selection-background-color: {SUPERFICIE_2}; selection-color: {ACENTO}; }}
QCheckBox, QRadioButton {{ spacing: 10px; }}
QCheckBox::indicator, QRadioButton::indicator {{ width: 20px; height: 20px; }}
QProgressBar {{ background: {SUPERFICIE_2}; border: 0; border-radius: 6px; height: 12px; }}
QProgressBar::chunk {{ background: {ACENTO}; border-radius: 6px; }}
QScrollArea {{ background: transparent; border: 0; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 10px; }}
QScrollBar::handle:vertical {{ background: {BORDE}; border-radius: 5px; min-height: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
QTableWidget {{ background: {SUPERFICIE}; border: 1px solid {BORDE}; border-radius: 12px;
    gridline-color: {BORDE}; }}
QHeaderView::section {{ background: {SUPERFICIE_2}; color: {TEXTO_2}; border: 0;
    border-bottom: 1px solid {BORDE}; padding: 8px; font-weight: 700; }}
QTableWidget::item {{ padding: 6px; }}
QTableWidget::item:selected {{ background: {SUPERFICIE_2}; color: {ACENTO}; }}
QToolTip {{ background: {SUPERFICIE}; color: {TEXTO}; border: 1px solid {BORDE}; }}
"""
