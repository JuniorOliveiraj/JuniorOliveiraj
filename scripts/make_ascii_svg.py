"""
Converte a imagem preto-e-branco em um SVG ASCII monocromático estilo terminal
animado (fundo escuro, cor única, cursor que digita linha por linha).

    python scripts/make_ascii_svg.py [input.png] [output.svg]
"""
from PIL import Image, ImageEnhance
import html
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "ese-preto-branco.png")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "..", "junior-ascii.svg")

# ── Parâmetros de conversão ─────────────────────────────────────────────────
COLS = int(os.environ.get("COLS", 180))
ART_W_TARGET = 800
CELL_W = ART_W_TARGET / COLS
CELL_H = CELL_W * 15 / 8
ROWS = round(COLS * 8 / 15)

# Rampa: espaço (branco) → @ (preto)
RAMP = " .:-=+*cs#%@"

GAMMA      = 1.1    # esta imagem já tem bom contraste, gamma suave
WHITE_FLOOR = 0.90  # fundo cinza claro ~239/255 → espaço em branco

# Cortar bordas da imagem
CROP_TOP    = 20    # px a cortar do topo
CROP_BOTTOM = 55    # px a cortar do fundo (barra "junior@github:~$")
CROP_LEFT   = 6     # px a cortar da esquerda
CROP_RIGHT  = 6     # px a cortar da direita

# ── Layout do SVG ───────────────────────────────────────────────────────────
PAD         = 20
TITLEBAR_H  = 30
STATUS_H    = 30
ART_W       = COLS * CELL_W
ART_H       = ROWS * CELL_H
CANVAS_W    = ART_W + PAD * 2
CANVAS_H    = TITLEBAR_H + ART_H + STATUS_H + PAD

BG          = "#0d1117"
BG2         = "#111722"
FRAME       = "#30363d"
TITLE_TEXT  = "#7d8590"
INK         = "#c9d1d9"
CURSOR      = "#c9d1d9"

# Timing da animação: portrait inteiro em ~6s
ROW_DUR  = 5.8 / ROWS
STAGGER  = ROW_DUR

# ── 1. Carregar e preparar imagem ───────────────────────────────────────────
im = Image.open(SRC).convert("L")
w, h = im.size

# Cortar bordas
im = im.crop((CROP_LEFT, CROP_TOP, w - CROP_RIGHT, h - CROP_BOTTOM))

# Redimensionar para grade de colunas
im = im.resize((COLS, ROWS), Image.LANCZOS)
px = im.load()

STATIC = bool(os.environ.get("STATIC"))

# ── 2. Converter pixels → caracteres ───────────────────────────────────────
rows_txt = []
for y in range(ROWS):
    chars = []
    for x in range(COLS):
        lum = px[x, y] / 255.0
        lum = pow(lum, GAMMA)
        if lum >= WHITE_FLOOR:
            chars.append(" ")
        else:
            idx = int((1.0 - lum) * (len(RAMP) - 1) + 0.5)
            chars.append(RAMP[max(0, min(len(RAMP) - 1, idx))])
    rows_txt.append("".join(chars))

art_top = TITLEBAR_H + PAD * 0.35

# ── 3. Montar SVG ───────────────────────────────────────────────────────────
parts = []
parts.append(
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{CANVAS_W}" height="{CANVAS_H}" '
    f'viewBox="0 0 {CANVAS_W} {CANVAS_H}" '
    f'font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace">'
)

# gradiente de fundo
parts.append(
    f'<defs><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">'
    f'<stop offset="0" stop-color="{BG2}"/>'
    f'<stop offset="1" stop-color="{BG}"/>'
    f'</linearGradient></defs>'
)

# fundo + borda arredondada
parts.append(f'<rect width="{CANVAS_W}" height="{CANVAS_H}" rx="12" fill="url(#bg)"/>')
parts.append(
    f'<rect x="0.5" y="0.5" width="{CANVAS_W-1}" height="{CANVAS_H-1}" rx="12" '
    f'fill="none" stroke="{FRAME}" stroke-width="1"/>'
)

# barra de título
parts.append(f'<line x1="0" y1="{TITLEBAR_H}" x2="{CANVAS_W}" y2="{TITLEBAR_H}" stroke="{FRAME}"/>')
for i, dotcol in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"]):
    parts.append(f'<circle cx="{PAD + i*16}" cy="{TITLEBAR_H/2}" r="5" fill="{dotcol}"/>')
parts.append(
    f'<text x="{CANVAS_W/2}" y="{TITLEBAR_H/2 + 4}" fill="{TITLE_TEXT}" font-size="12" '
    f'text-anchor="middle">junior@github: ~$ ./portrait.sh</text>'
)

# linhas ASCII com animação de digitação
font_size = CELL_H * 0.86
for ry, line in enumerate(rows_txt):
    y      = art_top + ry * CELL_H + CELL_H * 0.74
    row_y  = art_top + ry * CELL_H
    delay  = ry * STAGGER
    safe   = html.escape(line)
    text   = (
        f'<text xml:space="preserve" x="{PAD}" y="{y:.1f}" fill="{INK}" '
        f'font-size="{font_size:.1f}" textLength="{ART_W}" lengthAdjust="spacing">'
        f'{safe}</text>'
    )

    if STATIC:
        parts.append(text)
        continue

    # clip que revela a linha da esquerda para a direita
    parts.append(
        f'<clipPath id="r{ry}">'
        f'<rect x="{PAD}" y="{row_y:.1f}" height="{CELL_H}" width="0">'
        f'<animate attributeName="width" from="0" to="{ART_W}" '
        f'begin="{delay:.3f}s" dur="{ROW_DUR:.2f}s" fill="freeze"/>'
        f'</rect></clipPath>'
    )
    parts.append(f'<g clip-path="url(#r{ry})">{text}</g>')

    # cursor que percorre a linha
    parts.append(
        f'<rect y="{row_y+1:.1f}" width="{CELL_W}" height="{CELL_H-2}" '
        f'fill="{CURSOR}" opacity="0">'
        f'<animate attributeName="x" from="{PAD}" to="{PAD+ART_W}" '
        f'begin="{delay:.3f}s" dur="{ROW_DUR:.2f}s" fill="freeze"/>'
        f'<set attributeName="opacity" to="0.85" begin="{delay:.3f}s"/>'
        f'<set attributeName="opacity" to="0" begin="{delay+ROW_DUR:.3f}s"/>'
        f'</rect>'
    )

# barra de status com cursor piscante
status_line_y = TITLEBAR_H + ART_H + PAD * 0.35
status_y      = status_line_y + 19
parts.append(
    f'<line x1="0" y1="{status_line_y:.1f}" x2="{CANVAS_W}" '
    f'y2="{status_line_y:.1f}" stroke="{FRAME}"/>'
)
parts.append(
    f'<text x="{PAD}" y="{status_y:.1f}" fill="{TITLE_TEXT}" font-size="13">'
    f'junior@github:~$ whoami '
    f'<tspan fill="{INK}">Junior Oliveira</tspan></text>'
)
status_chars = len("junior@github:~$ whoami Junior Oliveira ")
cursor_x = PAD + status_chars * 13 * 0.6
parts.append(
    f'<rect x="{cursor_x:.1f}" y="{status_y-12:.1f}" width="8" height="14" fill="{INK}">'
    f'<animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.5;0.51;1" '
    f'dur="1s" repeatCount="indefinite"/></rect>'
)

parts.append("</svg>")
svg = "".join(parts)

with open(OUT, "w", encoding="utf-8") as f:
    f.write(svg)
print(f"wrote {OUT}  {len(svg):,} bytes  canvas {CANVAS_W:.0f}x{CANVAS_H:.0f}")
