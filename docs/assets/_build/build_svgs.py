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
    svg.append(f'<rect x="{lx+16}" y="{ly+16}" width="{lw-32}" height="{lh-32}" fill="none" stroke="{BRAND}" stroke-opacity="0.35" stroke-width="1" stroke-dasharray="6 5"/>')

    # whale: centred, scaled down (independent of panel corner), framed by its own corner brackets
    wscale = 4.3
    wcx, wcy = lx + lw / 2, ly + lh / 2 - 12          # ~(299, 324)
    whale_wpx = 48.84 * wscale                         # ~210
    whale_hpx = 36.63 * wscale                         # ~157
    fpx = 24
    fx0, fy0 = wcx - whale_wpx / 2 - fpx, wcy - whale_hpx / 2 - 16   # ~(155, 220)
    fw, fh = whale_wpx + 2 * fpx, whale_hpx + 40                      # ~(258, 197)
    svg.append(rect_bracket(fx0, fy0, fw, fh, CYAN, 2.0))
    svg.append(whale_group(wcx, wcy, wscale * WW))
    svg.append(f'<circle cx="{wcx}" cy="{wcy}" r="{whale_wpx/2+8}" fill="none" stroke="{CYAN}" stroke-opacity="0.15" stroke-width="1" stroke-dasharray="2 4"/>')

    # MOUNT legend column at panel top-left, above the whale frame (clear zone)
    svg.append(label(lx + 28, ly + 24, "MOUNT", 15, MUTED))
    svg.append(label(lx + 28, ly + 44, "WHALE.SVG", 17, INK, ls="0.1em"))
    svg.append(label(lx + 28, ly + 62, "[ 0.5342, 43.5762 ]", 14, CYAN))

    # SCALE / OFFICIAL at panel bottom-left (clear of whale frame bottom @ y~417)
    svg.append(label(lx + 28, ly + lh - 44, "SCALE 1:1", 16, MUTED))
    svg.append(label(lx + 28, ly + lh - 22, "OFFICIAL MARK", 15, ACCENT))

    # ---- RIGHT: title block (uniform vertical rhythm) ----
    rx = 640
    svg.append(label(rx, 140, "SPEC  /   BLUEPRINT COVER  v2.0", 18, INK, mono=False, ls="0.18em"))
    svg.append(dataline(rx, W - 70, 164, "■ BANNER SET", CYAN, 15))
    svg.append(f"<text x=\"{rx}\" y=\"258\" font-family='{F_SANS}' font-weight=\"800\" font-size=\"78\" fill=\"{CYAN}\" letter-spacing=\"0.01em\">DSH <tspan fill=\"{INK}\">Desktop</tspan></text>")
    svg.append(f"<text x=\"{rx}\" y=\"332\" font-family='{F_SANS}' font-size=\"34\" fill=\"{INK}\" letter-spacing=\"0.04em\">DeepSeek Harness 桌面版</text>")
    svg.append(f'<line x1="{rx}" y1="370" x2="{W-70}" y2="370" stroke="{STROKE}" stroke-width="1"/>')
    svg.append(f'<rect x="{rx+14}" y="364" width="10" height="10" transform="rotate(45 {rx+19} 369)" fill="none" stroke="{ACCENT}" stroke-width="1.5"/>')

    # value chips
    chips = ["一键启动", "远程访问", "插件市场"]
    cy, cwid, gap = 416, 160, 36
    cx0 = rx
    for i, c in enumerate(chips):
        xx = cx0 + i * (cwid + gap)
        last = i == len(chips) - 1
        svg.append(f'<rect data-kind="chip" x="{xx}" y="{cy-20}" width="{cwid}" height="48" rx="3" fill="rgba(0,240,255,0.05)" stroke="{CYAN}" stroke-opacity="0.4" stroke-width="1"/>')
        svg.append(f"<text x=\"{xx+cwid/2}\" y=\"{cy+9}\" font-family='{F_SANS}' font-weight=\"600\" font-size=\"27\" fill=\"{ACCENT if last else INK}\" text-anchor=\"middle\">{c}</text>")

    # bottom tag row
    tags = ["v2.0", "Node→DSH→插件 自动引导", "服务守护"]
    ty, tx = 498, rx
    gap_between = 22
    for t in tags:
        mw = tag_calc_w(t, 19, 13)
        sn, _ = tagchip(tx, ty, t, 19, INK, CYAN, "rgba(0,240,255,0.06)", padx=13, pady=8)
        svg.append(sn)
        tx += mw + gap_between

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
    svg.append(whale_group(172, 158, 108))
    svg.append(f'<circle cx="172" cy="158" r="88" fill="none" stroke="{CYAN}" stroke-opacity="0.14" stroke-width="1" stroke-dasharray="2 4"/>')
    svg.append(label(172, 248, "WHALE.SVG", 14, CYAN, anchor="middle"))

    # divider
    svg.append(f'<line x1="268" y1="112" x2="268" y2="196" stroke="{BRAND}" stroke-opacity="0.6" stroke-width="1.2"/>')
    svg.append(f'<rect x="263" y="152" width="10" height="10" transform="rotate(45 268 157)" fill="none" stroke="{ACCENT}" stroke-width="1.5"/>')

    # ---- LEFT title block (kept within x<=760 to avoid the right pipeline) ----
    svg.append(f"<text x=\"300\" y=\"118\" font-family='{F_SANS}' font-weight=\"800\" font-size=\"60\" fill=\"{CYAN}\">DSH <tspan fill=\"{INK}\">Desktop</tspan></text>")
    svg.append(f"<text x=\"304\" y=\"196\" font-family='{F_SANS}' font-size=\"26\" fill=\"{INK}\" letter-spacing=\"0.05em\">一键零配置 · 远程访问 · 服务守护</text>")
    svg.append(label(306, 230, "DESKTOP LAUNCHER FOR DEEPSEEK HARNESS", 13, MUTED))

    # ---- RIGHT: node pipeline (x >= 800 zone) ----
    px, py = 830, 126
    steps = ["Node.js", "DSH", "插件"]
    sw, sh, gap = 110, 40, 36
    for i, s in enumerate(steps):
        xx = px + i * (sw + gap)
        svg.append(f'<rect data-kind="chip" x="{xx}" y="{py-sh/2}" width="{sw}" height="{sh}" rx="3" fill="rgba(0,240,255,0.05)" stroke="{CYAN}" stroke-opacity="0.5" stroke-width="1"/>')
        svg.append(f"<text x=\"{xx+sw/2}\" y=\"{py+7}\" font-family='{F_MONO}' font-size=\"20\" fill=\"{INK}\" text-anchor=\"middle\">{s}</text>")
        if i < len(steps) - 1:
            axx = xx + sw
            svg.append(f'<line x1="{axx+10}" y1="{py}" x2="{axx+gap-8}" y2="{py}" stroke="{ACCENT}" stroke-width="1.6"/>')
            svg.append(f'<path d="M{axx+gap-10} {py-5} L{axx+gap-4} {py} L{axx+gap-10} {py+5}" fill="none" stroke="{ACCENT}" stroke-width="1.6"/>')
    svg.append(label(px, py + sh / 2 + 30, "AUTO-BOOTSTRAP  CHAIN", 15, MUTED))
    y2 = py + sh / 2 + 52
    svg.append(dataline(px, px + 2 * sw + 2 * gap, y2, "3-STAGE", CYAN, 13))

    # right edge tags (under the pipeline, left of bottom strip)
    tg_y = py + sh / 2 + 82
    sn, w1 = tagchip(px, tg_y, "服务守护", 18, ACCENT, ACCENT, "rgba(255,94,0,0.08)")
    svg.append(sn)
    sn, _ = tagchip(px + w1 + 14, tg_y, "v2.0", 18, INK, CYAN, "rgba(0,240,255,0.06)")
    svg.append(sn)

    svg.append('</svg>')
    return "\n".join(svg)


if __name__ == "__main__":
    for fname, content in [("social-preview.svg", build_social()), ("banner.svg", build_banner())]:
        path = os.path.join(ASSETS, fname)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print("wrote", path, len(content), "chars")
