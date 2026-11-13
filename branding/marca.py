"""Fuente única del isotipo de NeuroLift (la N hecha con una mancuerna), con geometría exacta.

Coordenadas normalizadas: el isotipo mide 100 de alto y está centrado en (0, 0); se dibuja recto y la cursiva es
un solo skewX(-15). La mitad derecha es la izquierda girada 180°. De aquí salen:
  - branding/: SVG negro, blanco y blanco sobre negro, y PNG 4K (3840 px)
  - web/public/icon.svg: ícono de la PWA (de él salen los PNG con `npm run pwa-assets`)
  - web/public/favicon.svg
  - el JSX del componente <Logo/> (se imprime para pegarlo en src/components/icons.tsx)

Uso (desde la raíz del repo; necesita `pip install resvg-py pillow`):
    python branding/marca.py branding web/public
Después, para regenerar los PNG de la PWA a partir de web/public/icon.svg:
    cd web && npm run pwa-assets
"""
import io
import math
import sys
from pathlib import Path

import resvg_py
from PIL import Image

BRANDING = Path(sys.argv[1])
PUBLIC = Path(sys.argv[2])

# Medidas tomadas del concepto 1 (en px del original de 2880) y llevadas a un alto de 100
K = 100 / 1124
ANGULO = 15.0
T = math.tan(math.radians(ANGULO))
TRAZO, INTERIOR, SEP = 420 * K, 354 * K, 40 * K
D1_ANCHO, D1_ALTO = 185 * K, 75.0
D2_ANCHO, D2_ALTO = 140 * K, 45.0
DIAG_GROSOR = 320 * K
DIAG_ARRIBA = (1090 - 1443) * K
R_TRAZO, R_D1, R_D2 = 48 * K, 36 * K, 30 * K

Y0, Y1 = -50.0, 50.0
L1 = -INTERIOR
L0 = L1 - TRAZO
R0, R1 = INTERIOR, INTERIOR + TRAZO
ya_sup, ya_inf = DIAG_ARRIBA, DIAG_ARRIBA + DIAG_GROSOR
yb_sup, yb_inf = -ya_inf, -ya_sup


def f(v: float) -> str:
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def arco(r, x, y):
    return f"A{f(r)} {f(r)} 0 0 1 {f(x)} {f(y)}"


r = R_TRAZO
N = "".join([
    f"M{f(L0 + r)} {f(Y0)}H{f(L1 - r)}", arco(r, L1, Y0 + r), f"V{f(ya_sup)}",
    f"L{f(R0)} {f(yb_sup)}",
    f"V{f(Y0 + r)}", arco(r, R0 + r, Y0), f"H{f(R1 - r)}", arco(r, R1, Y0 + r),
    f"V{f(Y1 - r)}", arco(r, R1 - r, Y1), f"H{f(R0 + r)}", arco(r, R0, Y1 - r),
    f"V{f(yb_inf)}", f"L{f(L1)} {f(ya_inf)}",
    f"V{f(Y1 - r)}", arco(r, L1 - r, Y1), f"H{f(L0 + r)}", arco(r, L0, Y1 - r),
    f"V{f(Y0 + r)}", arco(r, L0 + r, Y0), "Z",
])


def rect(x, y, w, h, rr):
    return (f"M{f(x + rr)} {f(y)}H{f(x + w - rr)}{arco(rr, x + w, y + rr)}V{f(y + h - rr)}{arco(rr, x + w - rr, y + h)}"
            f"H{f(x + rr)}{arco(rr, x, y + h - rr)}V{f(y + rr)}{arco(rr, x + rr, y)}Z")


d1_x = L0 - SEP - D1_ANCHO
d2_x = d1_x - SEP - D2_ANCHO
CAMINOS = [
    N,
    rect(d1_x, -D1_ALTO / 2, D1_ANCHO, D1_ALTO, R_D1),
    rect(d2_x, -D2_ALTO / 2, D2_ANCHO, D2_ALTO, R_D2),
    rect(-d1_x - D1_ANCHO, -D1_ALTO / 2, D1_ANCHO, D1_ALTO, R_D1),
    rect(-d2_x - D2_ANCHO, -D2_ALTO / 2, D2_ANCHO, D2_ALTO, R_D2),
]
# Ancho del isotipo ya inclinado: lo más externo es la esquina del disco pequeño
ANCHO = 2 * (-(d2_x - T * D2_ALTO / 2))
ALTO = 100.0


# Versión para tamaños mínimos (favicon): sin los discos exteriores, que a 16 px miden 1 píxel y se vuelven gris
ANCHO_SIMPLE = 2 * (-(d1_x - T * D1_ALTO / 2))


def marca(cx: float, cy: float, ancho: float, color: str = "", clase: str = "", simple: bool = False) -> str:
    """El isotipo centrado en (cx, cy) con el ancho pedido."""
    s = ancho / (ANCHO_SIMPLE if simple else ANCHO)
    atributo = f' fill="{color}"' if color else f' className="{clase}"'
    caminos = "".join(f'<path d="{d}"/>' for d in (CAMINOS[:2] + CAMINOS[3:4] if simple else CAMINOS))
    return f'<g{atributo} transform="translate({f(cx)} {f(cy)}) scale({s:.4f}) skewX({f(-ANGULO)})">{caminos}</g>'


def svg(lado: float, cuerpo: str, tam: int | None = None, titulo: str = "NeuroLift") -> str:
    medidas = f' width="{tam}" height="{tam}"' if tam else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {f(lado)} {f(lado)}"{medidas}>'
            f"<title>{titulo}</title>{cuerpo}</svg>\n")


def dibujar(texto: str, tam: int, fondo: str) -> Image.Image:
    return Image.open(io.BytesIO(bytes(resvg_py.svg_to_bytes(svg_string=texto, width=tam, height=tam, background=fondo)))).convert("RGB")


# ---------------------------------------------------------------- branding (cuadrado, margen 14 %)
LADO = 1000.0
ANCHO_BRANDING = LADO * (1 - 2 * 0.14)
BRANDING.mkdir(parents=True, exist_ok=True)
fondo_negro = f'<rect width="{f(LADO)}" height="{f(LADO)}" fill="#000000"/>'
piezas = {
    "neurolift-isotipo-negro.svg": svg(LADO, marca(500, 500, ANCHO_BRANDING, "#000000"), 3840),
    "neurolift-isotipo-blanco.svg": svg(LADO, marca(500, 500, ANCHO_BRANDING, "#FFFFFF"), 3840),
    "neurolift-isotipo-blanco-sobre-negro.svg": svg(LADO, fondo_negro + marca(500, 500, ANCHO_BRANDING, "#FFFFFF"), 3840),
}
for nombre, texto in piezas.items():
    (BRANDING / nombre).write_text('<?xml version="1.0" encoding="UTF-8"?>\n' + texto, encoding="utf-8")
dibujar(piezas["neurolift-isotipo-negro.svg"], 3840, "#ffffff").save(BRANDING / "neurolift-isotipo-negro-4k.png", optimize=True)
dibujar(piezas["neurolift-isotipo-blanco-sobre-negro.svg"], 3840, "#000000").save(BRANDING / "neurolift-isotipo-blanco-sobre-negro-4k.png", optimize=True)

# ---------------------------------------------------------------- PWA: icon.svg (fondo negro a sangre)
# El isotipo es ancho (2,2:1): al 62 % del lado cabe entero en la "zona segura" del ícono adaptable de Android
# (un círculo del 80 %), así el mismo SVG sirve para el ícono normal, el adaptable y el de iOS.
icono = svg(512, '<rect width="512" height="512" fill="#000000"/>' + marca(256, 256, 512 * 0.62, "#FFFFFF"))
(PUBLIC / "icon.svg").write_text(icono, encoding="utf-8")

# Favicon: más grande dentro del recuadro (a 16 px cada píxel cuenta), con esquinas redondeadas
favicon = svg(512, '<rect width="512" height="512" rx="112" fill="#000000"/>' + marca(256, 256, 512 * 0.86, "#FFFFFF", simple=True))
(PUBLIC / "favicon.svg").write_text(favicon, encoding="utf-8")

# Vistas de control
for nombre, texto, tam in (("icono_512.png", icono, 512), ("favicon_32.png", favicon, 32), ("favicon_16.png", favicon, 16)):
    dibujar(texto, tam, "#808080").save(Path(__file__).parent / nombre)

# ---------------------------------------------------------------- JSX del componente Logo (viewBox 32)
print("ANCHO_NORMALIZADO", round(ANCHO, 3))
print("JSX_LOGO_INICIO")
print(marca(16, 16, 32 * 0.80, clase="fill-fg").replace("><path", ">\n        <path").replace("</g>", "\n      </g>"))
print("JSX_LOGO_FIN")
