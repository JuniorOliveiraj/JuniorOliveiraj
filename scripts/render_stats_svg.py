#!/usr/bin/env python3
"""
Render the streak / numbers card from data/contributions.json.
Canvas 840x880 (same as portrait SVG).

Usa SMIL puro (<animate>, <set>) para ser compativel com o GitHub
que bloqueia CSS @keyframes / transform dentro de SVG via <img>.

    python scripts/render_stats_svg.py [data.json] [output.svg]
"""
import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC  = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "data", "contributions.json")
OUT  = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "..", "stats.svg")

BG    = "#0d1117"
BG2   = "#111722"
TILE  = "#161b22"
FRAME = "#30363d"
MUTED = "#7d8590"
INK   = "#e6edf3"
GREEN = "#39d353"
BAR   = "#26a641"

W, H        = 840, 880
PAD         = 20
TITLEBAR_H  = 30
COLS, ROWS  = 2, 3
GAP         = 16
TILE_W      = (W - PAD * 2 - GAP * (COLS - 1)) / COLS
TILE_H      = 150
TILES_TOP   = TITLEBAR_H + PAD + 4
CHART_TOP   = TILES_TOP + ROWS * TILE_H + (ROWS - 1) * GAP + GAP

# timing (segundos)
TILE_STAGGER = 0.18   # delay entre tiles
FADE_DUR     = 0.5    # fade-in de cada tile
COUNT_DUR    = 1.2    # contagem do número
FRAMES       = 16     # frames da contagem
BAR_DELAY    = TILE_STAGGER * COLS * ROWS + 0.5
BAR_STAGGER  = 0.07
BAR_DUR      = 0.5


def short(d):
    dt = datetime.date.fromisoformat(d)
    return f"{dt.strftime('%b')} {dt.day}"


def span(s):
    if not s["length"]:
        return "-"
    return f'{short(s["start"])} - {short(s["end"])}'


def fmt(v, like):
    return f"{v:,.1f}" if isinstance(like, float) else f"{int(round(v)):,}"


data = json.load(open(SRC, encoding="utf-8"))
cur, lng, best = data["current_streak"], data["longest_streak"], data["best_day"]
n_days = len(data["days"])

tiles = [
    ("current streak", cur["length"],             " days", span(cur),                                     GREEN),
    ("longest streak", lng["length"],             " days", span(lng),                                     INK),
    ("contributions",  data["total_contributions"], "",    "in the last year",                            INK),
    ("active days",    data["active_days"],         "",    f'{data["active_days"]} of {n_days} days',     INK),
    ("best day",       best["count"],               "",    short(best["date"]),                            INK),
    ("avg / active",   data["avg_per_active_day"],  "",    "contributions / day",                         INK),
]

parts = []

# ── SVG root ────────────────────────────────────────────────────────────────
parts.append(
    f'<svg xmlns="http://www.w3.org/2000/svg"'
    f' width="{W}" height="{H}" viewBox="0 0 {W} {H}"'
    f' font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,monospace">'
)

# ── defs: gradiente de fundo ────────────────────────────────────────────────
parts.append(
    f'<defs><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">'
    f'<stop offset="0" stop-color="{BG2}"/>'
    f'<stop offset="1" stop-color="{BG}"/>'
    f'</linearGradient></defs>'
)

# ── fundo + borda ───────────────────────────────────────────────────────────
parts.append(f'<rect width="{W}" height="{H}" rx="12" fill="url(#bg)"/>')
parts.append(
    f'<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="12"'
    f' fill="none" stroke="{FRAME}" stroke-width="1"/>'
)

# ── titlebar ────────────────────────────────────────────────────────────────
parts.append(f'<line x1="0" y1="{TITLEBAR_H}" x2="{W}" y2="{TITLEBAR_H}" stroke="{FRAME}"/>')
for i, dot in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"]):
    parts.append(f'<circle cx="{PAD + i*16}" cy="{TITLEBAR_H/2}" r="5" fill="{dot}"/>')
parts.append(
    f'<text x="{W/2}" y="{TITLEBAR_H/2 + 4}" fill="{MUTED}" font-size="12"'
    f' text-anchor="middle">junior@github: ~$ ./stats.sh</text>'
)

# ── tiles de stats ──────────────────────────────────────────────────────────
for i, (label, value, suffix, caption, accent) in enumerate(tiles):
    col, row  = i % COLS, i // COLS
    x         = PAD + col * (TILE_W + GAP)
    y         = TILES_TOP + row * (TILE_H + GAP)
    t_start   = i * TILE_STAGGER          # quando o tile aparece
    t_count   = t_start + FADE_DUR * 0.6  # quando começa a contar

    # container do tile: fade-in via SMIL
    parts.append(
        f'<g opacity="0">'
        f'<animate attributeName="opacity" from="0" to="1"'
        f' begin="{t_start:.2f}s" dur="{FADE_DUR:.2f}s" fill="freeze"/>'
    )

    # fundo do tile
    parts.append(
        f'<rect x="{x:.1f}" y="{y}" width="{TILE_W:.1f}" height="{TILE_H}"'
        f' rx="10" fill="{TILE}" stroke="{FRAME}"/>'
    )

    # label
    parts.append(
        f'<text x="{x+24:.1f}" y="{y+40}" fill="{MUTED}" font-size="22">$ {label}</text>'
    )

    # contagem animada — frames com <set>
    num_y = y + 100
    for k in range(1, FRAMES + 1):
        p     = k / FRAMES
        v     = value * (1 - (1 - p) ** 3)   # ease-out cubic
        t_on  = t_count + COUNT_DUR * (k - 1) / FRAMES
        t_off = t_count + COUNT_DUR * k       / FRAMES

        anim = f'<set attributeName="opacity" to="1" begin="{t_on:.3f}s"/>'
        if k < FRAMES:
            anim += f'<set attributeName="opacity" to="0" begin="{t_off:.3f}s"/>'

        parts.append(
            f'<text x="{x+24:.1f}" y="{num_y}" opacity="0"'
            f' font-size="54" font-weight="700" fill="{accent}">'
            f'{fmt(v, value)}'
            f'<tspan font-size="24" font-weight="400" fill="{MUTED}">{suffix}</tspan>'
            f'{anim}</text>'
        )

    # caption
    parts.append(
        f'<text x="{x+24:.1f}" y="{y+132}" fill="{MUTED}" font-size="20">{caption}</text>'
    )
    parts.append('</g>')

# ── gráfico de barras mensal ─────────────────────────────────────────────────
monthly  = data["monthly"]
chart_x  = PAD
chart_w  = W - PAD * 2
chart_h  = H - PAD - CHART_TOP
plot_top = CHART_TOP + 64
plot_bot = CHART_TOP + chart_h - 40
plot_l   = chart_x + 24
plot_r   = chart_x + chart_w - 24
slot     = (plot_r - plot_l) / max(len(monthly), 1)
bar_w    = slot * 0.62
peak     = max((m["total"] for m in monthly), default=1) or 1

# container do gráfico: fade-in
parts.append(
    f'<g opacity="0">'
    f'<animate attributeName="opacity" from="0" to="1"'
    f' begin="{BAR_DELAY - 0.3:.2f}s" dur="{FADE_DUR:.2f}s" fill="freeze"/>'
)
parts.append(
    f'<rect x="{chart_x}" y="{CHART_TOP}" width="{chart_w}" height="{chart_h}"'
    f' rx="10" fill="{TILE}" stroke="{FRAME}"/>'
)
parts.append(
    f'<text x="{chart_x+24}" y="{CHART_TOP+40}" fill="{MUTED}" font-size="22">'
    f'$ contributions / month</text>'
)
parts.append('</g>')

# barras — crescem via animateTransform (SMIL, suportado pelo GitHub)
for i, m in enumerate(monthly):
    bar_h   = max(2, (plot_bot - plot_top) * m["total"] / peak)
    bx      = plot_l + i * slot + (slot - bar_w) / 2
    by      = plot_bot - bar_h
    fill    = GREEN if m["total"] == peak else BAR
    delay   = BAR_DELAY + i * BAR_STAGGER

    # barra: começa com altura 0 e cresce usando animateTransform scaleY
    # O truque: a barra começa na posição final mas scale Y de 0->1
    # com transform-origin no fundo (plot_bot)
    parts.append(
        f'<rect x="{bx:.1f}" y="{by:.1f}" width="{bar_w:.1f}" height="{bar_h:.1f}"'
        f' rx="3" fill="{fill}" opacity="0">'
        f'<set attributeName="opacity" to="1" begin="{delay:.2f}s"/>'
        f'<animateTransform attributeName="transform" type="scale"'
        f' from="1 0" to="1 1" additive="sum"'
        f' begin="{delay:.2f}s" dur="{BAR_DUR:.2f}s" fill="freeze"'
        f' calcMode="spline" keySplines="0.2 0.8 0.2 1"/>'
        f'<animateTransform attributeName="transform" type="translate"'
        f' from="0 {bar_h:.1f}" to="0 0" additive="sum"'
        f' begin="{delay:.2f}s" dur="{BAR_DUR:.2f}s" fill="freeze"'
        f' calcMode="spline" keySplines="0.2 0.8 0.2 1"/>'
        f'</rect>'
    )

    # label do mês
    mon = datetime.date.fromisoformat(m["month"] + "-01").strftime("%b")[0]
    parts.append(
        f'<text x="{bx + bar_w/2:.1f}" y="{plot_bot + 28}"'
        f' fill="{MUTED}" font-size="18" text-anchor="middle">{mon}</text>'
    )

    # valor no pico
    if m["total"] == peak:
        parts.append(
            f'<text x="{bx + bar_w/2:.1f}" y="{by - 10:.1f}"'
            f' fill="{INK}" font-size="18" text-anchor="middle" opacity="0">'
            f'{peak:,}'
            f'<set attributeName="opacity" to="1" begin="{delay + BAR_DUR:.2f}s"/>'
            f'</text>'
        )

parts.append('</svg>')

svg = "".join(parts)
with open(OUT, "w", encoding="utf-8") as f:
    f.write(svg)
print(f"wrote {OUT}: {W}x{H}, {len(svg)//1024} KB")
