"""Qué se dibuja en un recinto del zoo, como figuras sencillas (igual que escena.py).

- dibujo_animal(especie): el animal en un cuadro de 40x40 (para iconos).
- construir_recinto(recinto, t): el recinto entero en ANCHO x ALTO, animado.
Las figuras las pinta la interfaz con QPainter (ui/pintar.py) y escena_a_svg()
las pasa a SVG para probarlas sin interfaz.
"""

import math

from .escena import _curva, _mezcla
from .zoo import ANIMALES, Recinto

ANCHO, ALTO = 480, 270
SECO = ("#6B6550", "#3A3628")   # hacia donde va el fondo cuando el recinto está mal
SUELO_SECO = "#4A4234"
GRIS = "#8A8F88"


def _c(cx, cy, r, color):
    return {"tipo": "elipse", "cx": cx, "cy": cy, "rx": r, "ry": r, "relleno": color}


def _e(cx, cy, rx, ry, color):
    return {"tipo": "elipse", "cx": cx, "cy": cy, "rx": rx, "ry": ry, "relleno": color}


def _p(puntos, color):
    return {"tipo": "poligono", "puntos": puntos, "relleno": color}


def _l(puntos, color, grosor):
    return {"tipo": "linea", "puntos": puntos, "color": color, "grosor": grosor}


def _sonrisa(x0, y0, x1, y1, cy, color="#0B1A14", grosor=1.6):
    return _l(_curva(x0, y0, x1, y1, (x0 + x1) / 2, cy, 8), color, grosor)


OJO = "#0B1A14"


def dibujo_animal(especie: str) -> list[dict]:
    """El animal dibujado en coordenadas 0-40 (mismo diseño que el prototipo)."""
    if especie == "pez":
        return [_p([(4, 12), (13, 20), (4, 28)], "#F29E4C"), _e(24, 20, 13, 8, "#FF8A5C"), _c(31, 18, 2, OJO)]
    if especie == "pinguino":
        return [_e(20, 23, 12, 15, "#1B2430"), _e(20, 26, 8, 10, "#F4F7FA"), _c(16, 14, 1.8, "#F4F7FA"),
                _c(24, 14, 1.8, "#F4F7FA"), _p([(17, 18), (23, 18), (20, 22)], "#FFB347")]
    if especie == "leon":
        return [_c(20, 20, 17, "#B5652B"), _c(20, 21, 11, "#F2C14E"), _c(16, 19, 1.8, OJO), _c(24, 19, 1.8, OJO),
                _sonrisa(17, 25, 23, 25, 28)]
    if especie == "jirafa":
        return [_l([(12, 33), (12, 39)], "#C99A3A", 2.4), _l([(26, 33), (26, 39)], "#C99A3A", 2.4),
                _p([(24, 10), (29, 10), (29, 28), (24, 28)], "#F2C14E"), _e(29, 8, 6, 4, "#F2C14E"),
                _c(31, 7, 1.2, OJO), _l([(27, 4), (26, 1)], "#B5652B", 1.6), _e(18, 28, 12, 7, "#F2C14E"),
                _c(14, 27, 2, "#B5652B"), _c(21, 29, 2, "#B5652B"), _c(26, 16, 1.5, "#B5652B")]
    if especie == "loro":
        return [_e(20, 25, 11, 13, "#2FD47F"), _c(20, 12, 8, "#FF6B6B"), _p([(26, 11), (34, 14), (26, 16)], "#FFC94D"),
                _c(22, 10, 1.6, OJO), _e(14, 27, 5, 9, "#00C2FF")]
    if especie == "mono":
        return [_c(8, 18, 5, "#8B5A2B"), _c(32, 18, 5, "#8B5A2B"), _c(20, 19, 13, "#8B5A2B"), _e(20, 22, 9, 8, "#E0B98A"),
                _c(16, 18, 1.8, OJO), _c(24, 18, 1.8, OJO), _sonrisa(16, 25, 24, 25, 28)]
    if especie == "tortuga":
        caparazon = [(5, 29)] + [(x, y) for x, y in _curva(5, 29, 31, 29, 18, 6, 12)][1:]
        return [_c(33, 24, 4.5, "#9ACD32"), _c(34.5, 23, 1, OJO), _e(11, 31, 4, 3, "#9ACD32"),
                _e(25, 31, 4, 3, "#9ACD32"), _p(caparazon, "#2E8B57"),
                _l([(12, 22), (18, 17), (24, 22)], "#1E5E3B", 1.6)]
    if especie == "rana":
        return [_e(20, 27, 15, 10, "#4CAF50"), _c(12, 16, 5, "#4CAF50"), _c(28, 16, 5, "#4CAF50"),
                _c(12, 15, 2.6, "#F4F7FA"), _c(28, 15, 2.6, "#F4F7FA"), _c(12, 15, 1.3, OJO), _c(28, 15, 1.3, OJO),
                _sonrisa(13, 27, 27, 27, 32, "#1E5E3B")]
    if especie == "buho":
        return [_p([(9, 8), (14, 13), (8, 14)], "#6D4C41"), _p([(31, 8), (26, 13), (32, 14)], "#6D4C41"),
                _e(20, 23, 13, 15, "#8D6E63"), _e(20, 28, 8, 8, "#BCAAA4"), _c(14, 17, 5, "#F4F7FA"),
                _c(26, 17, 5, "#F4F7FA"), _c(14, 17, 2.2, OJO), _c(26, 17, 2.2, OJO),
                _p([(18, 21), (22, 21), (20, 25)], "#FFB347")]
    if especie == "zorro":
        return [_p([(6, 6), (15, 14), (9, 18)], "#C85A1E"), _p([(34, 6), (25, 14), (31, 18)], "#C85A1E"),
                _p([(5, 14), (35, 14), (20, 36)], "#F07B2A"), _p([(9, 20), (20, 36), (14, 21)], "#F4F7FA"),
                _p([(31, 20), (20, 36), (26, 21)], "#F4F7FA"), _c(15, 21, 1.8, OJO), _c(25, 21, 1.8, OJO),
                _c(20, 34, 2, OJO)]
    raise ValueError(f"Animal desconocido: {especie}")


def colocar(figuras: list[dict], x: float, y: float, escala: float, espejo: bool = False) -> list[dict]:
    """Mueve y escala un dibujo de 40x40 para que su centro quede en (x, y)."""
    def px(vx):
        dx = (vx - 20) * escala
        return x - dx if espejo else x + dx

    def py(vy):
        return y + (vy - 20) * escala

    salida = []
    for f in figuras:
        g = dict(f)
        if f["tipo"] == "elipse":
            g.update(cx=px(f["cx"]), cy=py(f["cy"]), rx=f["rx"] * escala, ry=f["ry"] * escala)
        elif f["tipo"] in ("poligono", "linea"):
            g["puntos"] = [(px(a), py(b)) for a, b in f["puntos"]]
            if f["tipo"] == "linea":
                g["grosor"] = max(1.0, f["grosor"] * escala)
        salida.append(g)
    return salida


def apagar(figuras: list[dict], cuanto: float) -> list[dict]:
    """Quita color a los dibujos cuando el recinto está mal (0 = igual, 1 = gris)."""
    if cuanto <= 0:
        return figuras
    salida = []
    for f in figuras:
        g = dict(f)
        for clave in ("relleno", "color"):
            if clave in g:
                g[clave] = _mezcla(g[clave], GRIS, cuanto)
        salida.append(g)
    return salida


def construir_recinto(recinto: Recinto, t: float = 0.0) -> list[dict]:
    animal = recinto.animal
    # Con 60 % o más, colores plenos; por debajo se van apagando un poco (un recinto
    # nuevo, con 1 animal y 10 %, se ve con color, no seco). Vacío (0 %), casi gris.
    k = max(0.0, min(1.0, 0.45 + recinto.salud / 110))
    figs: list[dict] = [{"tipo": "degradado", "x": 0, "y": 0, "w": ANCHO, "h": ALTO,
                         "arriba": _mezcla(SECO[0], animal.cielo[0], k),
                         "abajo": _mezcla(SECO[1], animal.cielo[1], k)}]

    # Decoración según el recinto.
    especie = recinto.especie
    if especie == "pez":
        if recinto.animales:
            for i, (bx, r) in enumerate([(70, 5), (78, 3), (400, 4.5), (408, 3)]):
                fase = ((t + i * 0.9) % 5) / 5
                figs.append({"tipo": "circulo_borde", "cx": bx + 3 * math.sin(t * 2 + i), "cy": 230 - fase * 200,
                             "r": r, "color": "#FFFFFF", "alfa": 0.7 * (1 - fase)})
        for x, alto in ((40, 90), (440, 110)):
            figs.append(_l(_curva(x, ALTO - 24, x + 10 * math.sin(t + x), ALTO - 24 - alto, x - 18,
                                  ALTO - 24 - alto / 2), _mezcla("#6B5530", "#2FD47F", k), 7))
    elif especie == "buho":
        figs.append(_c(400, 50, 22, _mezcla("#9A9A8A", "#F4F1C9", k)))
        for sx, sy in ((60, 40), (150, 70), (250, 30), (330, 90), (110, 110)):
            figs.append(_c(sx, sy, 1.6, "#FFFFFF") | {"alfa": 0.5 + 0.4 * math.sin(t * 2 + sx)})
    elif especie in ("pinguino",):
        figs.append(_p([(300, ALTO - 24), (360, 120), (420, ALTO - 24)], _mezcla("#9AA1A6", "#E3F1FA", k)))
    elif especie in ("loro", "mono", "rana", "zorro"):
        hoja = _mezcla("#4F4226", {"zorro": "#C9622B", "rana": "#2E8B57"}.get(especie, "#1F7A4A"), k)
        for x in (30, 450):
            figs.append(_e(x, 60, 70, 48, hoja))
    else:  # sabana, acacias, playa: un sol
        figs.append(_c(410, 52, 26, _mezcla("#B0A27A", "#FFE680", k)) | {"alfa": 0.9})
        if especie == "jirafa":
            figs.append(_l([(80, ALTO - 24), (80, 150)], "#6B4A2B", 6))
            figs.append(_e(80, 145, 50, 14, _mezcla("#4F4226", "#3F8F45", k)))

    # Suelo (en el acuario, arena; en el estanque, agua y orilla).
    suelo = _mezcla(SUELO_SECO, animal.suelo, k)
    figs.append(_p([(0, ALTO - 30)] + [(x, ALTO - 30 + 6 * math.sin(x / 60)) for x in range(0, ANCHO + 1, 40)]
                   + [(ANCHO, ALTO), (0, ALTO)], suelo))

    # Animales: hasta 10, en dos filas de 5; los que nadan, a media altura.
    for i in range(recinto.animales):
        col, fila = i % 5, i // 5
        x = 60 + col * 90 + fila * 30  # la 2.ª fila, algo desplazada (sin salirse)
        if animal.nada:
            fase = 2 * math.pi * t / (6 + i % 3) + i
            x += 18 * math.sin(fase)
            y = 90 + fila * 80 + (col % 2) * 24 + 4 * math.sin(fase * 2)
            espejo = math.cos(fase) < 0
        else:
            y = ALTO - 60 - fila * 70 - 3 * abs(math.sin(t * 2.2 + i))
            espejo = i % 2 == 1
        figs += colocar(dibujo_animal(especie), x, y, 1.7 - 0.25 * fila, espejo)

    if recinto.animales == 0:  # velo gris cuando se ha quedado vacío
        figs.append({"tipo": "rect", "x": 0, "y": 0, "w": ANCHO, "h": ALTO, "relleno": "#2A2A22",
                     "alfa": 0.35})
    return figs
