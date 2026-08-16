# -*- coding: utf-8 -*-
"""Generate the two self-contained brand cover SVGs for DSH Desktop.

Dark Blueprint (engineering drawing) aesthetic.
Output: docs/assets/social-preview.svg (1200x630), docs/assets/banner.svg (1280x320)
"""
import os, re, subprocess

_HERE = os.path.dirname(os.path.abspath(__file__))              # docs/assets/_build
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_HERE))) # project root
FAVICON = os.path.join(ROOT, "favicon.svg")
ASSETS = os.path.dirname(_HERE)                                 # docs/assets

# ---- whale path (extracted intact from the official favicon.svg) ----
fav = open(FAVICON, encoding="utf-8").read()
WHALE = re.search(r'<path[^>]*d="([^"]+)"', fav).group(1)

# ---- whale bbox in the 0 0 50 50 favicon viewBox ----
WCX, WCY, WW, WH = 24.95264, 25.260025, 48.83692, 36.63235

# ---------- palette (Dark Blueprint) ----------
BG     = "#0A1424"
CARD   = "#0E1B30"
GRID   = "rgba(0,240,255,0.055)"
CYAN   = "#00F0FF"
BRAND  = "#4D6BFE"
ACCENT = "#FF5E00"
INK    = "#E6F4F7"
MUTED  = "#6C7E99"
STROKE = "rgba(0,240,255,0.30)"

F_SANS = '"Segoe UI","Microsoft YaHei",-apple-system,sans-serif'
F_MONO = 'Consolas,"JetBrains Mono","Courier New",monospace'

# ---------- reusable builders (return svg snippet strings) ----------

def grid(w, h, step):
    """Full-canvas background grid."""
    lines = []
    for x in range(0, w + 1, step):
        lines.append(f'<line x1="{x}" y1="0" x2="{x}" y2="{h}" stroke="{GRID}" stroke-width="1" vector-effect="non-scaling-stroke"/>')
    for y in range(0, h + 1, step):
        lines.append(f'<line x1="0" y1="{y}" x2="{w}" y2="{y}" stroke="{GRID}" stroke-width="1" vector-effect="non-scaling-stroke"/>')
    return "\n".join(lines)


def sparse_grid(w, h, step, opacity=None):
    """Very faint, coarser grid for whitespace-forward minimal designs."""
    color = opacity if opacity else "rgba(0,240,255,0.028)"
    lines = []
    for x in range(0, w + 1, step):
        lines.append(f'<line x1="{x}" y1="0" x2="{x}" y2="{h}" stroke="{color}" stroke-width="1" vector-effect="non-scaling-stroke"/>')
    for y in range(0, h + 1, step):
        lines.append(f'<line x1="0" y1="{y}" x2="{w}" y2="{y}" stroke="{color}" stroke-width="1" vector-effect="non-scaling-stroke"/>')
    return "\n".join(lines)


def bracket(x, y, s=18, c=CYAN, t=2.0, arm=8):
    """Four L-shaped sight brackets delineating a square box (top-left x,y, outer size s)."""
    return rect_bracket(x, y, s, s, c, t, arm)


def rect_bracket(x, y, w, h, c=CYAN, t=2.0, arm=10):
    """Four L-shaped sight brackets delineating a rectangle (top-left x,y, size w x h)."""
    def corner(cx, cy, hx, hy):
        return (f'<path d="M{cx} {cy} h{arm*hx}" stroke="{c}" stroke-width="{t}" fill="none" stroke-linecap="square"/>'
                f'<path d="M{cx} {cy} v{arm*hy}" stroke="{c}" stroke-width="{t}" fill="none" stroke-linecap="square"/>')
    x1 = x + w
    y1 = y + h
    return "\n".join([corner(x, y, 1, 1), corner(x1, y, -1, 1),
                      corner(x, y1, 1, -1), corner(x1, y1, -1, -1)])


def label(x, y, text, size=16, c=MUTED, mono=True, anchor="start", ls="0.06em", ff=None):
    fam = ff or (F_MONO if mono else F_SANS)
    ffattr = f" font-family='{fam}'"
    return f'<text x="{x}" y="{y}"{ffattr} font-size="{size}" fill="{c}" text-anchor="{anchor}" letter-spacing="{ls}">{text}</text>'


def tag_calc_w(text, size, padx=14, letter_spacing='0.05em'):
    """Tag box width sized to ACTUALLY contain the text (measured with the chip's
    own letter-spacing) + padx + safety margin."""
    try:
        w = measure_text_width(text, size, mono=True, letter_spacing=letter_spacing)
    except Exception:
        import re as _re
        cjk = _re.compile(r'[\u2E80-\u9FFF\uF900-\uFAFF\uFF00-\uFFEF\u3000-\u303F]')
        w = sum((size if cjk.match(ch) else size * 0.62) for ch in text)
    return w + padx * 2 + 6


def measure_text_width(text, size, mono=True, cw=2000, ch=200, letter_spacing=None):
    """Render one text line via resvg and return its ink width in SVG units."""
    import json
    fam = F_MONO if mono else F_SANS
    ls = f' letter-spacing="{letter_spacing}"' if letter_spacing else ''
    xml = f"<text x=\"20\" y=\"60\" font-family='{fam}' font-size=\"{size}\" fill=\"#fff\"{ls}>{text}</text>"
    payload = json.dumps({'width': cw, 'height': ch, 'texts': [{'id': '0', 'xml': xml}]})
    p = subprocess.run([os.environ.get('DSH_NODE', 'node'),
                        os.path.join(_HERE, '..', '_render', 'measure_texts.mjs')],
                       input=payload, capture_output=True, text=True,
                       cwd=os.path.join(_HERE, '..', '_render'))
    res = json.loads(p.stdout).get('0')
    if not res:
        raise RuntimeError('measure empty')
    return res[2] - res[0]


def tagchip(x, y, text, size=16, c=CYAN, border=CYAN, bg="rgba(0,240,255,0.06)", padx=14, pady=7, w=None):
    """Draw a bracketed tag like [SPEC-01]. Returns (snippet, width)."""
    if w is None:
        w = tag_calc_w(text, size, padx)
    snip = "\n".join([
        f'<rect data-kind="chip" x="{x}" y="{y-(size/2+pady)}" width="{w}" height="{size+pady*2}" rx="2" fill="{bg}" stroke="{border}" stroke-opacity="0.6" stroke-width="1"/>',
        f"<text x=\"{x+padx}\" y=\"{y+size*0.34}\" font-family='{F_MONO}' font-size=\"{size}\" fill=\"{c}\" letter-spacing=\"0.05em\">{text}</text>",
    ])
    return snip, w


def dataline(x1, x2, y, text, c=CYAN, size=15):
    """Horizontal dimension line with end ticks + centered label."""
    t = 1.4
    return "\n".join([
        f'<line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" stroke="{STROKE}" stroke-width="{t}"/>',
        f'<line x1="{x1}" y1="{y-5}" x2="{x1}" y2="{y+5}" stroke="{c}" stroke-width="{t}"/>',
        f'<line x1="{x2}" y1="{y-5}" x2="{x2}" y2="{y+5}" stroke="{c}" stroke-width="{t}"/>',
        f"<text x=\"{(x1+x2)/2}\" y=\"{y-8}\" font-family='{F_MONO}' font-size=\"{size}\" fill=\"{c}\" text-anchor=\"middle\" letter-spacing=\"0.08em\">{text}</text>",
    ])


def whale_group(cx, cy, s):
    """Place official whale centred at (cx,cy); ~s px wide, blueprint-styled."""
    sc = s / WW
    tx = cx - WCX * sc
    ty = cy - WCY * sc
    main = (f'<path d="{WHALE}" fill="rgba(77,107,254,0.30)" stroke="{CYAN}" '
            f'stroke-width="{1.8*sc}" stroke-linejoin="round" stroke-linecap="round" fill-rule="evenodd"/>')
    ghost = (f'<path d="{WHALE}" fill="none" stroke="{BRAND}" stroke-width="1.1" '
             f'stroke-linejoin="round" stroke-linecap="round" fill-rule="evenodd" '
             f'stroke-dasharray="{3.5*sc} {2.5*sc}" stroke-opacity="0.55" '
             f'transform="translate({2.2*sc},{2.2*sc})"/>')
    return (f'<g data-kind="whale" transform="translate({tx:.2f},{ty:.2f}) scale({sc:.3f})">'
            f'{ghost}\n{main}</g>')


def glow_defs(gid="glow"):
    return (f'<radialGradient id="{gid}" cx="0.5" cy="0.5" r="0.75">'
            '<stop offset="0%" stop-color="#000" stop-opacity="0"/>'
            '<stop offset="72%" stop-color="#000" stop-opacity="0"/>'
            '<stop offset="100%" stop-color="#000" stop-opacity="0.55"/>'
            '</radialGradient>')


# ============================================================
# 1) SOCIAL PREVIEW  1200 x 630  (minimal / whitespace-forward)
# ============================================================
def build_social():
    W, H = 1200, 630
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
    svg.append(f'<rect width="{W}" height="{H}" fill="{BG}"/>')
    svg.append(f'<ellipse cx="600" cy="315" rx="640" ry="360" fill="url(#glow)"/>')
    svg.append(sparse_grid(W, H, 48))
    svg.append(f'<defs>{glow_defs()}</defs>')

    # ---- centered whale (main visual) ----
    whale_s = 240
    svg.append(whale_group(600, 232, whale_s))
    svg.append(f'<circle cx="600" cy="232" r="{whale_s/2+8}" fill="none" stroke="{CYAN}" stroke-opacity="0.12" stroke-width="1" stroke-dasharray="2 4"/>')

    # ---- title (only focal typography) ----
    svg.append(f"<text x=\"600\" y=\"420\" font-family='{F_SANS}' font-weight=\"800\" font-size=\"92\" fill=\"{CYAN}\" text-anchor=\"middle\" letter-spacing=\"0.01em\">DSH <tspan fill=\"{INK}\">Desktop</tspan></text>")
    # ---- subtitle ----
    svg.append(f"<text x=\"600\" y=\"486\" font-family='{F_SANS}' font-size=\"40\" fill=\"{MUTED}\" text-anchor=\"middle\" letter-spacing=\"0.06em\">DeepSeek Harness 桌面版</text>")

    # ---- value chips (single centered row) ----
    chips = ["一键启动", "远程访问", "插件市场"]
    cwid, gap = 190, 40
    cy = 550
    total = len(chips) * cwid + (len(chips) - 1) * gap
    x0 = 600 - total / 2
    for i, c in enumerate(chips):
        xx = x0 + i * (cwid + gap)
        last = i == len(chips) - 1
        svg.append(f'<rect data-kind="chip" x="{xx}" y="{cy-28}" width="{cwid}" height="56" rx="3" fill="rgba(0,240,255,0.05)" stroke="{CYAN}" stroke-opacity="0.3" stroke-width="1"/>')
        svg.append(f"<text x=\"{xx+cwid/2}\" y=\"{cy+10}\" font-family='{F_SANS}' font-weight=\"600\" font-size=\"30\" fill=\"{ACCENT if last else INK}\" text-anchor=\"middle\">{c}</text>")

    # ---- one small version line ----
    svg.append(f"<text x=\"600\" y=\"604\" font-family='{F_MONO}' font-size=\"16\" fill=\"{MUTED}\" text-anchor=\"middle\" letter-spacing=\"0.14em\">[ v2.0 · WINDOWS DOT-AND-PLAY LAUNCHER ]</text>")

    svg.append('</svg>')
    return "\n".join(svg)


# ============================================================
# 2) BANNER  1280 x 320  (minimal / whitespace-forward)
# ============================================================
def build_banner():
    W, H = 1280, 320
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
    svg.append(f'<rect width="{W}" height="{H}" fill="{BG}"/>')
    svg.append(f'<ellipse cx="640" cy="160" rx="800" ry="260" fill="url(#glow)"/>')
    svg.append(sparse_grid(W, H, 48))
    svg.append(f'<defs>{glow_defs()}</defs>')

    # ----- whale: single graphic focus, left, centred vertically -----
    svg.append(whale_group(250, 168, 150))
    svg.append(f'<circle cx="250" cy="168" r="92" fill="none" stroke="{CYAN}" stroke-opacity="0.12" stroke-width="1" stroke-dasharray="2 4"/>')

    # subtle divider is enough (no dimensional clutter)
    svg.append(f'<line x1="378" y1="120" x2="378" y2="216" stroke="{BRAND}" stroke-opacity="0.5" stroke-width="1.2"/>')

    # ----- title: the only strong type -----
    svg.append(f"<text x=\"440\" y=\"152\" font-family='{F_SANS}' font-weight=\"800\" font-size=\"92\" fill=\"{CYAN}\" letter-spacing=\"0.01em\">DSH <tspan fill=\"{INK}\">Desktop</tspan></text>")
    # ----- slogan -----
    svg.append(f"<text x=\"446\" y=\"228\" font-family='{F_SANS}' font-size=\"40\" fill=\"{INK}\" letter-spacing=\"0.05em\">一键零配置 · 远程访问 · 服务守护</text>")
    # ----- one tiny meta line (bottom area, wide breath above) -----
    svg.append(label(448, 276, "DESKTOP LAUNCHER FOR DEEPSEEK HARNESS  ·  v2.0  ·  WINDOWS", 16, MUTED))

    svg.append('</svg>')
    return "\n".join(svg)


if __name__ == "__main__":
    for fname, content in [("social-preview.svg", build_social()), ("banner.svg", build_banner())]:
        path = os.path.join(ASSETS, fname)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print("wrote", path, len(content), "chars")
