# -*- coding: utf-8 -*-
"""Overlap + bounds self-check for the two brand-cover SVGs.

Ground truth is the ACTUAL rendered pixels, not a width heuristic:
  * every <text> is re-rendered alone (same fonts/position/rotation) via
    @resvg/resvg-js and its true ink AABB measured;
  * chip/tag <rect data-kind=chip> and the <g data-kind=whale> boxes come from
    their exact SVG geometry (attributes / transform).

Then we assert: no two content boxes intersect (tolerance 0px, except text
contained inside its own chip which is intended), and none exceeds the canvas
(left/top/right/bottom edges included).

Run:
    .venv/Scripts/python docs/assets/_build/check_overlap.py
Requires node + @resvg/resvg-js + pngjs under docs/assets/_render (npm install).
"""
import json, os, re, subprocess, sys
import xml.dom.minidom as m

_HERE = os.path.dirname(os.path.abspath(__file__))   # docs/assets/_build
ASSETS = os.path.dirname(_HERE)                       # docs/assets
RENDER = os.path.join(ASSETS, '_render')              # node tooling
VALID = True


def _run_measure(svg_path):
    """Render every <text> alone and return ({idx:[x0,y0,x1,y1]}, CW, CH) in SVG units."""
    dom = m.parse(svg_path)
    root = dom.documentElement
    CW = float(root.getAttribute('width'))
    CH = float(root.getAttribute('height'))
    jobs = []
    for i, e in enumerate(dom.getElementsByTagName('text')):
        xml = '\n'.join(l for l in e.toprettyxml(indent='', newl='').splitlines() if l.strip())
        jobs.append({'id': str(i), 'xml': xml})
    if not jobs:
        return {}, CW, CH
    payload = json.dumps({'width': CW, 'height': CH, 'texts': jobs})
    node = os.environ.get('DSH_NODE', 'node')
    p = subprocess.run([node, os.path.join(RENDER, 'measure_texts.mjs')],
                       input=payload, capture_output=True, text=True, cwd=RENDER)
    if p.returncode != 0:
        raise RuntimeError(f'text measurement failed:\n{p.stdout}\n{p.stderr}')
    return json.loads(p.stdout), CW, CH


def chip_box(e):
    x, y = float(e.getAttribute('x')), float(e.getAttribute('y'))
    return (x, y, x + float(e.getAttribute('width')), y + float(e.getAttribute('height')))


def whale_box(e):
    tr = e.getAttribute('transform')
    mt = re.search(r'translate\(([-\d.]+)[ ,]([-\d.]+)\)', tr)
    ms = re.search(r'scale\(([-\d.]+)\)', tr)
    tx, ty, sc = float(mt.group(1)), float(mt.group(2)), float(ms.group(1))
    return (tx + 0.53 * sc, ty + 6.94 * sc, tx + 49.37 * sc, ty + 43.58 * sc)


def intersect(a, b, tol=0.0):
    return not (a[2] <= b[0] + tol or b[2] <= a[0] + tol
                or a[3] <= b[1] + tol or b[3] <= a[1] + tol)


def contains(outer, inner, pad=1.0):
    return (inner[0] >= outer[0] - pad and inner[1] >= outer[1] - pad
            and inner[2] <= outer[2] + pad and inner[3] <= outer[3] + pad)


def inspect(fname):
    global VALID
    path = os.path.join(ASSETS, fname)
    dom0 = m.parse(path)
    root = dom0.documentElement
    CW = float(root.getAttribute('width'))
    CH = float(root.getAttribute('height'))
    measured, _, _ = _run_measure(path)
    dom = m.parse(path)
    texts = dom.getElementsByTagName('text')
    names = []
    for e in texts:
        t = ' '.join(re.sub(r'<[^>]+>', ' ', e.toxml()).split())
        names.append(t[:30])
    boxes = []
    for i, e in enumerate(texts):
        bb = measured.get(str(i))
        if bb:
            boxes.append((names[i], ('text', *bb)))
    for e in dom.getElementsByTagName('rect'):
        if e.getAttribute('data-kind') == 'chip':
            boxes.append(('CHIP', ('chip', *chip_box(e))))
    for e in dom.getElementsByTagName('g'):
        if e.getAttribute('data-kind') == 'whale':
            boxes.append(('WHALE', ('whale', *whale_box(e))))

    print(f'\n===== {fname}  canvas {CW:.0f}x{CH:.0f}  ({len(boxes)} content boxes) =====')
    failures = 0
    out = [(n, bb) for n, bb in boxes
           if bb[1] < -0.5 or bb[2] < -0.5 or bb[3] > CW + 0.5 or bb[4] > CH + 0.5]
    for n, bb in out:
        failures += 1
        print(f'  OUT-OF-CANVAS: {n!r:42} [{bb[1]:.1f},{bb[2]:.1f}]-[{bb[3]:.1f},{bb[4]:.1f}]')
    if not out:
        print('  BOUNDS OK')

    problems = 0
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            n1, b1 = boxes[i]
            n2, b2 = boxes[j]
            if not intersect(b1[1:], b2[1:]):
                continue
            intended = (b1[0] == 'chip' and b2[0] == 'text' and contains(b1[1:], b2[1:])) or \
                       (b2[0] == 'chip' and b1[0] == 'text' and contains(b2[1:], b1[1:]))
            if intended:
                continue
            problems += 1
            print(f'  OVERLAP: {n1!r:42} [{b1[1]:.1f},{b1[2]:.1f}]-[{b1[3]:.1f},{b1[4]:.1f}]'
                  f'  vs  {n2!r:42} [{b2[1]:.1f},{b2[2]:.1f}]-[{b2[3]:.1f},{b2[4]:.1f}]')
    if problems == 0 and not out:
        print('  RESULT: PASS')
    else:
        VALID = False
        print(f'  RESULT: FAIL  ({problems} overlap(s), {len(out)} out-of-canvas)')


if __name__ == '__main__':
    for f in ['social-preview.svg', 'banner.svg']:
        inspect(f)
    print('\n' + ('ALL CLEAN.' if VALID else '** FAILURES PRESENT **'))
    sys.exit(0 if VALID else 1)
