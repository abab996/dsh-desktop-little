# -*- coding: utf-8 -*-
"""Generate the two self-contained brand cover SVGs for DSH Desktop.

Dark Blueprint (engineering drawing) aesthetic.
Output: docs/assets/social-preview.svg (1200x630), docs/assets/banner.svg (1280x320)
"""
import os, re

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


def bracket(x, y, s=18, c=CYAN, t=2.0, arm=8):
    """Four L-shaped sight brackets delineating a square box (top-left x,y, outer size s)."""
    def corner(cx, cy, hx, hy):
        return (f'<path d="M{cx} {cy} h{arm*hx}" stroke="{c}" stroke-width="{t}" fill="none" stroke-linecap="square"/>'
                f'<path d="M{cx} {cy} v{arm*hy}" stroke="{c}" stroke-width="{t}" fill="none" stroke-linecap="square"/>')
    return "\n".join([corner(x, y, 1, 1), corner(x + s, y, -1, 1),
                      corner(x, y + s, 1, -1), corner(x + s, y + s, -1, -1)])


def label(x, y, text, size=16, c=MUTED, mono=True, anchor="start", ls="0.06em", ff=None):
    fam = ff or (F_MONO if mono else F_SANS)
    ffattr = f" font-family='{fam}'"
    return f'<text x="{x}" y="{y}"{ffattr} font-size="{size}" fill="{c}" text-anchor="{anchor}" letter-spacing="{ls}">{text}</text>'


def tag_calc_w(text, size, padx=14):
    return len(text) * (size * 0.62) + padx * 2


def tagchip(x, y, text, size=16, c=CYAN, border=CYAN, bg="rgba(0,240,255,0.06)", padx=14, pady=7, w=None):
    """Draw a bracketed tag like [SPEC-01]. Returns (snippet, width)."""
    if w is None:
        w = tag_calc_w(text, size, padx)
    snip = "\n".join([
        f'<rect x="{x}" y="{y-(size/2+pady)}" width="{w}" height="{size+pady*2}" rx="2" fill="{bg}" stroke="{border}" stroke-opacity="0.6" stroke-width="1"/>',
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
    return f'<g transform="translate({tx:.2f},{ty:.2f}) scale({sc:.3f})">{ghost}\n{main}</g>'


def glow_defs(gid="glow"):
    return (f'<radialGradient id="{gid}" cx="0.5" cy="0.5" r="0.75">'
            '<stop offset="0%" stop-color="#000" stop-opacity="0"/>'
            '<stop offset="72%" stop-color="#000" stop-opacity="0"/>'
            '<stop offset="100%" stop-color="#000" stop-opacity="0.55"/>'
            '</radialGradient>')


# ============================================================
# 1) SOCIAL PREVIEW  1200 x 630
# ============================================================
def build_social():
    W, H = 1200, 630
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
    svg.append(f'<rect width="{W}" height="{H}" fill="{BG}"/>')
    svg.append(f'<ellipse cx="600" cy="315" rx="620" ry="340" fill="url(#glow)"/>')
    svg.append(grid(W, H, 28))
    svg.append(f'<defs>{glow_defs()}</defs>')

    # top mono strip
    svg.append(label(56, 54, "DEEPSEEK HARNESS  //  DESKTOP BRAND COVER  [FIG.01]", 18, MUTED))
    sn, _ = tagchip(W - 332, 54, "[STATUS: ACTIVE]", 18, ACCENT, ACCENT, "rgba(255,94,0,0.08)")
    svg.append(sn)

    # ---- LEFT: whale card ----
    lx, ly, lw, lh = 64, 118, 470, 412
    svg.append(f'<rect x="{lx}" y="{ly}" width="{lw}" height="{lh}" fill="{CARD}" stroke="{STROKE}" stroke-width="1"/>')
    svg.append(bracket(lx + 22, ly + 22, 46, CYAN, 2.5))
    svg.append(f'<rect x="{lx+16}" y="{ly+16}" width="{lw-32}" height="{lh-32}" fill="none" stroke="{BRAND}" stroke-opacity="0.35" stroke-width="1" stroke-dasharray="6 5"/>')
    svg.append(whale_group(lx + lw / 2, ly + lh / 2, 250))
    svg.append(f'<circle cx="{lx+lw/2}" cy="{ly+lh/2}" r="118" fill="none" stroke="{CYAN}" stroke-opacity="0.15" stroke-width="1" stroke-dasharray="2 4"/>')
    svg.append(label(lx + 26, ly + 44, "MOUNT", 15, MUTED))
    svg.append(label(lx + 26, ly + 64, "WHALE.SVG", 17, INK, ls="0.1em"))
    svg.append(label(lx + 26, ly + 82, "[ 0.5342, 43.5762 ]", 14, CYAN))
    svg.append(label(lx + lw - 26, ly + lh - 42, "SCALE 1:1", 16, MUTED, anchor="end"))
    svg.append(label(lx + lw - 26, ly + lh - 22, "OFFICIAL MARK", 15, ACCENT, anchor="end"))

    # ---- RIGHT: title block ----
    rx = 640
    svg.append(label(rx, 168, "SPEC  /   BLUEPRINT COVER  v2.0", 18, INK, mono=False, ls="0.18em"))
    svg.append(dataline(rx, W - 70, 192, "■ BANNER SET", CYAN, 15))
    svg.append(f"<text x=\"{rx}\" y=\"288\" font-family='{F_SANS}' font-weight=\"800\" font-size=\"96\" fill=\"{CYAN}\" letter-spacing=\"0.01em\">DSH <tspan fill=\"{INK}\">Desktop</tspan></text>")
    svg.append(f"<text x=\"{rx}\" y=\"340\" font-family='{F_SANS}' font-size=\"40\" fill=\"{INK}\" letter-spacing=\"0.04em\">DeepSeek Harness 桌面版</text>")
    svg.append(f'<line x1="{rx}" y1="372" x2="{W-70}" y2="372" stroke="{STROKE}" stroke-width="1"/>')
    svg.append(f'<rect x="{rx+14}" y="366" width="10" height="10" transform="rotate(45 {rx+19} 371)" fill="none" stroke="{ACCENT}" stroke-width="1.5"/>')

    # value chips
    chips = ["一键启动", "远程访问", "插件市场"]
    cy, cwid, gap = 420, 160, 24
    cx0 = rx
    for i, c in enumerate(chips):
        xx = cx0 + i * (cwid + gap)
        last = i == len(chips) - 1
        svg.append(f'<rect x="{xx}" y="{cy-20}" width="{cwid}" height="48" rx="3" fill="rgba(0,240,255,0.05)" stroke="{CYAN}" stroke-opacity="0.4" stroke-width="1"/>')
        svg.append(f"<text x=\"{xx+cwid/2}\" y=\"{cy+9}\" font-family='{F_SANS}' font-weight=\"600\" font-size=\"27\" fill=\"{ACCENT if last else INK}\" text-anchor=\"middle\">{c}</text>")
        svg.append(label(xx + 12, cy - 6, f"{i+1:02d}", 13, MUTED))

    # bottom tag row
    tags = ["v2.0", "Node → DSH → 插件  自动引导", "服务守护"]
    ty, tx = 524, rx
    for i, t in enumerate(tags):
        mw = tag_calc_w(t, 24, 18)
        border = CYAN if i != 1 else BRAND
        cc = INK if i != 1 else CYAN
        sn, _ = tagchip(tx, ty, t, 24, cc, border, padx=18, pady=10)
        svg.append(sn)
        tx += mw + 16

    # bottom X dimension scale
    baseY = 598
    svg.append(dataline(56, W - 56, baseY, "1200 px", MUTED, 14))
    for x in range(56, W - 48, 96):
        svg.append(f'<line x1="{x}" y1="{baseY-4}" x2="{x}" y2="{baseY+4}" stroke="rgba(0,240,255,0.5)" stroke-width="1"/>')

    # right vertical dimension
    vx, v1, v2 = W - 46, 118, H - 70
    vym = (v1 + v2) / 2
    svg.append(f'<line x1="{vx}" y1="{v1}" x2="{vx}" y2="{v2}" stroke="{STROKE}" stroke-width="1.4"/>')
    svg.append(f'<line x1="{vx-5}" y1="{v1}" x2="{vx+5}" y2="{v1}" stroke="{CYAN}" stroke-width="1.4"/>')
    svg.append(f'<line x1="{vx-5}" y1="{v2}" x2="{vx+5}" y2="{v2}" stroke="{CYAN}" stroke-width="1.4"/>')
    svg.append(f"<text x=\"{vx}\" y=\"{vym}\" font-family='{F_MONO}' font-size=\"14\" fill=\"{MUTED}\" text-anchor=\"middle\" letter-spacing=\"0.08em\" transform=\"rotate(-90 {vx} {vym})\">630 px</text>")

    svg.append(label(W - 56, H - 44, f"@ 1200 x 630  ·  {BG}", 15, MUTED, anchor="end"))
    svg.append('</svg>')
    return "\n".join(svg)


# ============================================================
# 2) BANNER  1280 x 320
# ============================================================
def build_banner():
    W, H = 1280, 320
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
    svg.append(f'<rect width="{W}" height="{H}" fill="{BG}"/>')
    svg.append(f'<ellipse cx="640" cy="160" rx="760" ry="240" fill="url(#glow)"/>')
    svg.append(grid(W, H, 24))
    svg.append(f'<defs>{glow_defs()}</defs>')

    # top / bottom mono strips
    svg.append(label(44, 42, "DSH-DESKTOP  /  RELEASE 2.0  [BLUEPRINT]", 17, MUTED))
    sn, _ = tagchip(W - 330, 42, "[STATUS: ACTIVE]", 17, ACCENT, ACCENT, "rgba(255,94,0,0.08)")
    svg.append(sn)
    svg.append(label(44, H - 34, "DEEPSEEK HARNESS  DESKTOP APP  --  WINDOWS  /  PYTHON + PYWEBVIEW", 15, MUTED))
    svg.append(label(W - 44, H - 34, "1280 × 320", 15, MUTED, anchor="end"))

    # frame brackets
    svg.append(bracket(30, 58, 56, CYAN, 2.5))
    svg.append(bracket(26, 252, 56, CYAN, 2.5))

    # left: whale
    svg.append(whale_group(172, 162, 116))
    svg.append(f'<circle cx="172" cy="162" r="96" fill="none" stroke="{CYAN}" stroke-opacity="0.14" stroke-width="1" stroke-dasharray="2 4"/>')
    svg.append(label(172, 284, "WHALE.SVG", 14, CYAN, anchor="middle"))

    # divider
    svg.append(f'<line x1="268" y1="118" x2="268" y2="218" stroke="{BRAND}" stroke-opacity="0.6" stroke-width="1.2"/>')
    svg.append(f'<rect x="263" y="159" width="10" height="10" transform="rotate(45 268 164)" fill="none" stroke="{ACCENT}" stroke-width="1.5"/>')

    # title block
    svg.append(f"<text x=\"310\" y=\"154\" font-family='{F_SANS}' font-weight=\"800\" font-size=\"84\" fill=\"{CYAN}\">DSH <tspan fill=\"{INK}\">Desktop</tspan></text>")
    svg.append(f"<text x=\"314\" y=\"216\" font-family='{F_SANS}' font-size=\"36\" fill=\"{INK}\" letter-spacing=\"0.05em\">一键启动 · 零配置  · 远程访问 · 服务守护</text>")
    svg.append(label(316, 244, "THE DESKTOP LAUNCHER FOR DEEPSEEK HARNESS  --  PYTHON + PYWEBVIEW", 15, MUTED))

    # right: node pipeline
    px, py = 748, 150
    steps = ["Node.js", "DSH", "插件"]
    sw, sh = 138, 46
    for i, s in enumerate(steps):
        xx = px + i * (sw + 50)
        svg.append(f'<rect x="{xx}" y="{py-sh/2}" width="{sw}" height="{sh}" rx="3" fill="rgba(0,240,255,0.05)" stroke="{CYAN}" stroke-opacity="0.5" stroke-width="1"/>')
        svg.append(f"<text x=\"{xx+sw/2}\" y=\"{py+7}\" font-family='{F_MONO}' font-size=\"22\" fill=\"{INK}\" text-anchor=\"middle\">{s}</text>")
        svg.append(label(xx + 10, py - sh / 2 + 16, f"{i+1}", 13, MUTED))
        if i < len(steps) - 1:
            axx = xx + sw
            svg.append(f'<line x1="{axx+8}" y1="{py}" x2="{axx+42}" y2="{py}" stroke="{ACCENT}" stroke-width="1.6"/>')
            svg.append(f'<path d="M{axx+40} {py-5} L{axx+46} {py} L{axx+40} {py+5}" fill="none" stroke="{ACCENT}" stroke-width="1.6"/>')
    svg.append(label(px, py + sh / 2 + 28, "AUTO-BOOTSTRAP  CHAIN", 15, MUTED))
    y2 = py + sh / 2 + 50
    svg.append(dataline(px, px + 2 * sw + 2 * 50, y2, "3-STAGE", CYAN, 14))

    # right edge tags
    sn, w1 = tagchip(px, py + sh / 2 + 88, "服务守护", 20, ACCENT, ACCENT, "rgba(255,94,0,0.08)")
    svg.append(sn)
    sn, _ = tagchip(px + w1 + 16, py + sh / 2 + 88, "v2.0", 20, INK, CYAN, "rgba(0,240,255,0.06)")
    svg.append(sn)

    svg.append('</svg>')
    return "\n".join(svg)


if __name__ == "__main__":
    for fname, content in [("social-preview.svg", build_social()), ("banner.svg", build_banner())]:
        path = os.path.join(ASSETS, fname)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print("wrote", path, len(content), "chars")
