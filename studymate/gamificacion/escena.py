"""Qué hay que dibujar en la pecera, como una lista de figuras sencillas.

Es Python puro: la ventana PySide6 (ui/pecera_widget.py) pinta estas figuras con
QPainter, y escena_a_svg() las convierte a SVG para probarlas sin interfaz.

Coordenadas lógicas: ANCHO x ALTO. El que dibuja escala al tamaño real.
"""

import math

from .pecera import EstadoPecera

ANCHO, ALTO = 720, 420

# Huecos fijos para los peces (x, y, tamaño): así cada pez tiene siempre su sitio.
HUECOS = [
    (90, 110, 1.0), (300, 80, 0.8), (470, 150, 1.1), (160, 220, 0.9),
    (380, 250, 0.75), (520, 280, 0.9), (70, 300, 1.15), (260, 320, 1.0),
    (430, 200, 0.8), (200, 140, 0.7), (560, 90, 0.85), (110, 250, 1.0),
]


def _hex(c):
    return [int(c[i:i + 2], 16) for i in (1, 3, 5)]


def _mezcla(malo, bueno, t):
    a, b = _hex(malo), _hex(bueno)
    return "#" + "".join(f"{round(x + (y - x) * t):02X}" for x, y in zip(a, b))


def _curva(x0, y0, x1, y1, cx, cy, pasos=12):
    """Puntos de una curva cuadrática (para algas y plantas)."""
    pts = []
    for i in range(pasos + 1):
        u = i / pasos
        x = (1 - u) ** 2 * x0 + 2 * (1 - u) * u * cx + u ** 2 * x1
        y = (1 - u) ** 2 * y0 + 2 * (1 - u) * u * cy + u ** 2 * y1
        pts.append((x, y))
    return pts


def _pez(cx, cy, escala, color, cola, mirando_derecha, muerto=False):
    s = escala
    d = 1 if mirando_derecha else -1
    figuras = [
        {"tipo": "poligono", "puntos": [(cx - d * 20 * s, cy), (cx - d * 34 * s, cy - 11 * s),
                                        (cx - d * 34 * s, cy + 11 * s)], "relleno": cola},
        {"tipo": "elipse", "cx": cx, "cy": cy, "rx": 22 * s, "ry": 12 * s, "relleno": color},
        {"tipo": "poligono", "puntos": [(cx - d * 6 * s, cy - 10 * s), (cx + d * 4 * s, cy - 19 * s),
                                        (cx + d * 10 * s, cy - 9 * s)], "relleno": cola},
    ]
    ox = cx + d * 11 * s
    if muerto:
        figuras += [
            {"tipo": "linea", "puntos": [(ox - 3 * s, cy - 6 * s), (ox + 3 * s, cy)], "color": "#3A4038", "grosor": 2},
            {"tipo": "linea", "puntos": [(ox + 3 * s, cy - 6 * s), (ox - 3 * s, cy)], "color": "#3A4038", "grosor": 2},
        ]
    else:
        figuras += [
            {"tipo": "elipse", "cx": ox, "cy": cy - 3 * s, "rx": 3.2 * s, "ry": 3.2 * s, "relleno": "#FFFFFF"},
            {"tipo": "elipse", "cx": ox + d * 1 * s, "cy": cy - 3 * s, "rx": 1.6 * s, "ry": 1.6 * s, "relleno": "#0B1A14"},
        ]
    return figuras


def construir_escena(estado: EstadoPecera, t: float = 0.0) -> list[dict]:
    """Figuras de la pecera en el instante t (segundos), según su salud."""
    salud = max(0, min(100, estado.salud))
    k = salud / 100
    figuras: list[dict] = []

    # Agua: de azul limpio a verde sucio.
    figuras.append({"tipo": "degradado", "x": 0, "y": 0, "w": ANCHO, "h": ALTO,
                    "arriba": _mezcla("#4A5530", "#1597D6", k),
                    "abajo": _mezcla("#232614", "#06375E", k), "radio": 26})
    figuras.append({"tipo": "rect", "x": 0, "y": 0, "w": ANCHO, "h": 14, "relleno": "#FFFFFF", "alfa": 0.08})

    # Burbujas solo si el agua está bien.
    if salud >= 45:
        for i, (bx, r) in enumerate([(345, 6), (352, 4), (338, 7), (612, 5), (618, 3.5), (96, 5)]):
            periodo = 5.0
            fase = ((t + i * 0.83) % periodo) / periodo
            by = 370 - fase * 340
            figuras.append({"tipo": "circulo_borde", "cx": bx + math.sin(t * 2 + i) * 3, "cy": by,
                            "r": r, "color": "#FFFFFF", "alfa": 0.7 * (1 - fase)})

    # Peces vivos nadando de un lado a otro.
    for i, pez in enumerate(estado.peces[:len(HUECOS)]):
        hx, hy, esc = HUECOS[i]
        periodo = 7 + (i % 4) * 1.5
        fase = 2 * math.pi * (t / periodo) + i * 0.9
        cx = hx + 60 + 60 * math.sin(fase)
        cy = hy + 6 * math.sin(fase * 2.3)
        mirando_derecha = math.cos(fase) >= 0
        figuras += _pez(cx, cy, esc, pez.color, pez.cola, mirando_derecha)

    # Peces muertos flotando arriba.
    for j in range(estado.muertos_recientes):
        mx = 210 + j * 170
        my = 30 + 3 * math.sin(t * 1.2 + j)
        figuras += _pez(mx, my, 0.9, "#9AA394", "#7C8578", True, muerto=True)

    # Suciedad: manchas de algas cuando la salud baja de 60.
    suciedad = max(0.0, min(0.85, (60 - salud) / 50))
    if suciedad > 0:
        for (mx, my, rx, ry) in [(100, 90, 70, 34), (500, 75, 85, 38), (320, 330, 75, 32), (615, 300, 60, 42)]:
            figuras.append({"tipo": "elipse", "cx": mx, "cy": my, "rx": rx, "ry": ry,
                            "relleno": "#2E3A1A", "alfa": suciedad * 0.8})

    # Plantas que se mecen (marrones si la pecera está mal) y arena.
    planta = _mezcla("#6B5530", "#2FD47F", k)
    planta2 = _mezcla("#4F4226", "#1FA866", k)
    for (x, alto, color, grosor) in [(80, 140, planta, 9), (130, 100, planta2, 7),
                                     (575, 170, planta, 10), (640, 110, planta2, 7)]:
        balanceo = 14 * math.sin(t * 0.9 + x)
        figuras.append({"tipo": "linea", "puntos": _curva(x, ALTO - 30, x + balanceo, ALTO - 30 - alto,
                                                          x - 25, ALTO - 30 - alto / 2),
                        "color": color, "grosor": grosor})
    figuras.append({"tipo": "poligono", "puntos": [(0, ALTO - 40)] + [(x, ALTO - 40 + 8 * math.sin(x / 70)) for x in range(0, ANCHO + 1, 40)] + [(ANCHO, ALTO), (0, ALTO)],
                    "relleno": _mezcla("#5E5338", "#D9C08A", k)})
    figuras.append({"tipo": "elipse", "cx": 330, "cy": ALTO - 24, "rx": 40, "ry": 13, "relleno": "#5B6168"})
    figuras.append({"tipo": "elipse", "cx": 372, "cy": ALTO - 20, "rx": 24, "ry": 9, "relleno": "#6F767D"})
    return figuras


def escena_a_svg(figuras: list[dict], ancho: int = ANCHO, alto: int = ALTO) -> str:
    """Convierte la escena a SVG (para pruebas y para el portfolio)."""
    partes = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{ancho}" height="{alto}" viewBox="0 0 {ANCHO} {ALTO}">',
              f'<clipPath id="c"><rect width="{ANCHO}" height="{ALTO}" rx="26"/></clipPath><g clip-path="url(#c)">']
    for n, f in enumerate(figuras):
        alfa = f.get("alfa", 1)
        op = f' opacity="{alfa:.3f}"' if alfa < 1 else ""
        tipo = f["tipo"]
        if tipo == "degradado":
            partes.append(f'<defs><linearGradient id="g{n}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{f["arriba"]}"/>'
                          f'<stop offset="1" stop-color="{f["abajo"]}"/></linearGradient></defs>'
                          f'<rect x="{f["x"]}" y="{f["y"]}" width="{f["w"]}" height="{f["h"]}" fill="url(#g{n})"/>')
        elif tipo == "rect":
            partes.append(f'<rect x="{f["x"]}" y="{f["y"]}" width="{f["w"]}" height="{f["h"]}" fill="{f["relleno"]}"{op}/>')
        elif tipo == "elipse":
            partes.append(f'<ellipse cx="{f["cx"]:.1f}" cy="{f["cy"]:.1f}" rx="{f["rx"]:.1f}" ry="{f["ry"]:.1f}" fill="{f["relleno"]}"{op}/>')
        elif tipo == "circulo_borde":
            partes.append(f'<circle cx="{f["cx"]:.1f}" cy="{f["cy"]:.1f}" r="{f["r"]}" fill="none" stroke="{f["color"]}" stroke-width="2"{op}/>')
        elif tipo == "poligono":
            pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in f["puntos"])
            partes.append(f'<polygon points="{pts}" fill="{f["relleno"]}"{op}/>')
        elif tipo == "linea":
            pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in f["puntos"])
            partes.append(f'<polyline points="{pts}" fill="none" stroke="{f["color"]}" stroke-width="{f["grosor"]}" stroke-linecap="round" stroke-linejoin="round"{op}/>')
    partes.append("</g></svg>")
    return "".join(partes)
