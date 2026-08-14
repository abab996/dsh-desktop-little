# -*- coding: utf-8 -*-
"""DSH 桌面图标生成器。

从官方 favicon.svg（黑色鲸鱼）渲染鲸鱼蒙版，再合成到圆角底色上，
输出 PNG 预览与多尺寸 .ico。
纯 Pillow 实现，无原生依赖。
"""
import re
from PIL import Image, ImageDraw

SRC = r"D:\pyx\DSH_RUN\dsh-desktop\favicon.svg"

# ---------- SVG path 解析 ----------
def tokenize(path):
    return re.findall(r'[A-Za-z]|-?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?', path)

def parse_subpaths(path):
    toks = tokenize(path)
    i = 0
    subpaths, cur = [], []
    cx = cy = 0.0
    def num():
        nonlocal i
        v = float(toks[i]); i += 1
        return v
    while i < len(toks):
        cmd = toks[i]; i += 1
        if cmd in 'Mm':
            x, y = num(), num()
            if cmd == 'm':
                x += cx; y += cy
            cx, cy = x, y
            if cur:
                subpaths.append(cur)
            cur = [(x, y)]
        elif cmd in 'Cc':
            while i < len(toks) and not toks[i].isalpha():
                x1, y1, x2, y2, x, y = num(), num(), num(), num(), num(), num()
                if cmd == 'c':
                    x1 += cx; y1 += cy; x2 += cx; y2 += cy; x += cx; y += cy
                cur.append((x1, y1)); cur.append((x2, y2)); cur.append((x, y))
                cx, cy = x, y
        elif cmd in 'Ll':
            while i < len(toks) and not toks[i].isalpha():
                x, y = num(), num()
                if cmd == 'l':
                    x += cx; y += cy
                cur.append((x, y))
                cx, cy = x, y
        elif cmd in 'Zz':
            if cur:
                subpaths.append(cur)
            cur = []
    if cur:
        subpaths.append(cur)
    return subpaths

def cubic(p0, p1, p2, p3, t):
    mt = 1 - t
    return (mt**3*p0[0] + 3*mt**2*t*p1[0] + 3*mt*t**2*p2[0] + t**3*p3[0],
            mt**3*p0[1] + 3*mt**2*t*p1[1] + 3*mt*t**2*p2[1] + t**3*p3[1])

def flatten_subpath(sp, seg=48):
    """sp = [p0, c1, c2, p1, c3, c4, p2, ...] -> 折线点列表"""
    pts = [sp[0]]
    j = 1
    while j + 2 < len(sp):
        p0 = pts[-1]
        p1, p2, p3 = sp[j], sp[j+1], sp[j+2]
        for k in range(1, seg + 1):
            pts.append(cubic(p0, p1, p2, p3, k / seg))
        j += 3
    return pts

# ---------- 鲸鱼蒙版渲染 ----------
def render_whale_mask(size, seg=48):
    """渲染鲸鱼蒙版（L 模式，255=鲸鱼，0=背景/镂空），返回 (mask, bbox)。"""
    d = re.search(r'<path[^>]* d="([^"]*)"', open(SRC, encoding="utf-8").read()).group(1)
    subpaths = parse_subpaths(d)
    # 外轮廓 = 面积最大的子路径；其余按绕向相反即镂空
    def signed_area(sp):
        flat = flatten_subpath(sp, seg)
        a = 0.0
        for p, q in zip(flat, flat[1:] + [flat[0]]):
            a += p[0]*q[1] - q[0]*p[1]
        return a / 2.0
    areas = [signed_area(sp) for sp in subpaths]
    outer_i = max(range(len(subpaths)), key=lambda k: abs(areas[k]))
    outer = flatten_subpath(subpaths[outer_i], seg)
    holes = [flatten_subpath(sp, seg) for k, sp in enumerate(subpaths) if k != outer_i]

    # 单位归一：viewBox 0..50
    def norm(pt):
        return (pt[0]/50.0, pt[1]/50.0)

    # 先按 content 比例缩放居中
    img = Image.new("L", (size, size), 0)
    dr = ImageDraw.Draw(img)

    def to_px(poly, scale, ox, oy):
        return [(p[0]*scale + ox, p[1]*scale + oy) for p in poly]

    # 鲸鱼 bbox（外轮廓，SVG 单位）
    xs = [p[0] for p in outer]; ys = [p[1] for p in outer]
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    w, h = maxx - minx, maxy - miny
    content_frac = 0.72
    scale = size * content_frac / max(w, h)
    ox = (size - w * scale) / 2 - minx * scale
    oy = (size - h * scale) / 2 - miny * scale

    dr.polygon(to_px(outer, scale, ox, oy), fill=255)
    for hp in holes:
        dr.polygon(to_px(hp, scale, ox, oy), fill=0)
    return img

# ---------- 圆角图标合成 ----------
def make_icon(bg, whale, size=1024, radius_frac=0.225):
    """bg: (r,g,b) 底色；whale: (r,g,b) 鲸鱼色。返回 RGBA 图像。"""
    ss = size * 4  # 超采样
    mask_big = render_whale_mask(ss)
    mask = mask_big.resize((size, size), Image.LANCZOS)

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    dr.rounded_rectangle([0, 0, size - 1, size - 1], radius=int(size * radius_frac), fill=(*bg, 255))

    # 鲸鱼层
    whale_layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    whale_layer.paste((*whale, 255), (0, 0), mask)
    img.alpha_composite(whale_layer)
    return img

if __name__ == "__main__":
    out_dir = r"D:\pyx\DSH_RUN\dsh-desktop"
    # 预览：白底黑鲸、深底白鲸、品牌蓝底白鲸
    make_icon((255, 255, 255), (15, 15, 15), 512).save(out_dir + "\\preview_white.png")
    make_icon((17, 17, 20), (245, 245, 245), 512).save(out_dir + "\\preview_dark.png")
    make_icon((77, 107, 254), (255, 255, 255), 512).save(out_dir + "\\preview_blue.png")
    # 纯鲸鱼蒙版预览（白底）
    m = render_whale_mask(512)
    Image.merge("RGBA", (Image.new("L", m.size, 255), Image.new("L", m.size, 255), Image.new("L", m.size, 255), m)).save(out_dir + "\\preview_whale_mask.png")
    print("previews done")
    im = Image.open(out_dir + "\\preview_white.png")
    print("white preview", im.size, im.mode)
    # 蒙版占比 sanity check
    import numpy as np
    arr = np.array(render_whale_mask(512))
    print("whale filled fraction", round(float((arr > 127).mean()), 4))
