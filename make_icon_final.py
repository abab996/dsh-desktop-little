# -*- coding: utf-8 -*-
"""最终图标：原版黑色鲸鱼，透明底，圆角（squircle）。输出 icon.png / icon.ico。"""
import re
import numpy as np
from PIL import Image, ImageDraw
from make_icon import parse_subpaths, flatten_subpath

SRC = r"D:\pyx\DSH_RUN\dsh-desktop\favicon.svg"
OUT = r"D:\pyx\DSH_RUN\dsh-desktop"

def whale_mask(size, content_frac=0.92, seg=48):
    d = re.search(r'<path[^>]* d="([^"]*)"', open(SRC, encoding="utf-8").read()).group(1)
    subpaths = parse_subpaths(d)
    def sa(sp):
        f = flatten_subpath(sp, seg)
        a = 0.0
        for p, q in zip(f, f[1:] + [f[0]]):
            a += p[0]*q[1] - q[0]*p[1]
        return a / 2.0
    areas = [sa(sp) for sp in subpaths]
    oi = max(range(len(subpaths)), key=lambda k: abs(areas[k]))
    outer = flatten_subpath(subpaths[oi], seg)
    holes = [flatten_subpath(sp, seg) for k, sp in enumerate(subpaths) if k != oi]
    xs = [p[0] for p in outer]; ys = [p[1] for p in outer]
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    w, h = maxx - minx, maxy - miny
    scale = size * content_frac / max(w, h)
    ox = (size - w * scale) / 2 - minx * scale
    oy = (size - h * scale) / 2 - miny * scale
    img = Image.new("L", (size, size), 0)
    dr = ImageDraw.Draw(img)
    dr.polygon([(p[0]*scale + ox, p[1]*scale + oy) for p in outer], fill=255)
    for hp in holes:
        dr.polygon([(p[0]*scale + ox, p[1]*scale + oy) for p in hp], fill=0)
    return img

def rounded_icon(size, content_frac=0.92, radius_frac=0.20):
    ss = size * 4
    whale = whale_mask(ss, content_frac).resize((size, size), Image.LANCZOS)
    sq = Image.new("L", (size, size), 0)
    dr = ImageDraw.Draw(sq)
    dr.rounded_rectangle([0, 0, size - 1, size - 1], radius=int(size * radius_frac), fill=255)
    final = np.minimum(np.array(whale), np.array(sq)).astype("uint8")
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    black = Image.new("RGBA", (size, size), (0, 0, 0, 255))
    img.paste(black, (0, 0), Image.fromarray(final))
    return img

if __name__ == "__main__":
    rounded_icon(512).save(OUT + "\\icon.png")
    rounded_icon(256).save(OUT + "\\icon.ico",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print("saved icon.png (512) and icon.ico (multi-size)")
    im = Image.open(OUT + "\\icon.ico")
    print("ico sizes:", im.ico.sizes() if hasattr(im, "ico") else "n/a")
    print("ico info:", im.info.get("sizes"))
