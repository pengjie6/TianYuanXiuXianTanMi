# -*- coding: utf-8 -*-
"""程序化绘制游戏 UI 图标（多面宝石 / 金币 / 闪电 / 书本 / 布袋等），
用 4 倍超采样保证边缘干净，风格对齐原作的扁平描边卡通。"""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

SS = 4


def _canvas(size):
    w, h = int(size[0] * SS), int(size[1] * SS)
    return Image.new('RGBA', (w, h), (0, 0, 0, 0))


def _done(im, size):
    return im.resize(size, Image.LANCZOS)


def _shade(rgb, k):
    return tuple(int(max(0, min(255, c * k))) for c in rgb)


def outline(im, color=(28, 30, 36, 255), width=3, size=None, blur=0.0):
    """给不透明内容加外描边。"""
    a = im.getchannel('A')
    grow = a.filter(ImageFilter.MaxFilter(width * 2 + 1))
    if blur:
        grow = grow.filter(ImageFilter.GaussianBlur(blur))
    edge = Image.new('RGBA', im.size, color)
    edge.putalpha(grow)
    out = Image.new('RGBA', im.size, (0, 0, 0, 0))
    out.alpha_composite(edge)
    out.alpha_composite(im)
    return out


def glow(im, color=(255, 220, 150), strength=0.45, radius=8):
    a = im.getchannel('A').filter(ImageFilter.MaxFilter(radius * 2 + 1)).filter(
        ImageFilter.GaussianBlur(radius))
    halo = Image.new('RGBA', im.size, color + (255,))
    halo.putalpha(a.point(lambda v: int(v * strength)))
    out = Image.new('RGBA', im.size, (0, 0, 0, 0))
    out.alpha_composite(halo)
    out.alpha_composite(im)
    return out


# ---------------------------------------------------------------- 宝石
def gem_icon(size, base=(74, 196, 146), core=(190, 255, 226), deep=(20, 86, 70),
             outline_col=(18, 46, 40), style='emerald', glow_col=(140, 240, 200)):
    """经典多面宝石：台面 + 冠部 + 亭部，6 个切面不同亮度。"""
    W, H = int(size[0] * SS), int(size[1] * SS)
    im = _canvas(size)
    d = ImageDraw.Draw(im)
    cx = W * 0.5

    # 归一化关键点
    table_l, table_r = 0.315, 0.685
    gird_l, gird_r = 0.055, 0.945
    y_table, y_gird, y_tip = 0.115, 0.415, 0.945
    pts = {
        'tl': (table_l, y_table), 'tr': (table_r, y_table),
        'ml': ((table_l + gird_l) / 2 + 0.01, (y_table + y_gird) / 2),
        'mr': ((table_r + gird_r) / 2 - 0.01, (y_table + y_gird) / 2),
        'gl': (gird_l, y_gird), 'gr': (gird_r, y_gird),
        'gc': (0.5, y_gird + 0.012),
        'tip': (0.5, y_tip),
        'ptl': (0.245, y_gird), 'ptr': (0.755, y_gird),
    }
    P = {k: (v[0] * W, v[1] * H) for k, v in pts.items()}

    faces = [
        # (顶点, 亮度)
        (['tl', 'tr', 'mr', 'gc', 'ml'], 1.22),          # 台面
        (['tl', 'ml', 'gl'], 0.96),                      # 冠左
        (['tr', 'mr', 'gr'], 1.36),                      # 冠右（受光）
        (['ml', 'gc', 'gl'], 1.05),                      # 冠中左
        (['mr', 'gr', 'gc'], 1.12),                      # 冠中右
        (['gl', 'gc', 'ptl'], 0.74),                     # 亭左
        (['ptl', 'gc', 'tip'], 1.02),                    # 亭中左
        (['gc', 'ptr', 'tip'], 0.88),                    # 亭中右
        (['ptr', 'gr', 'tip'], 0.66),                    # 亭右
    ]
    for keys, k in faces:
        d.polygon([P[x] for x in keys], fill=_shade(base, k) + (255,))

    # 内芯发光
    core_im = Image.new('RGBA', im.size, (0, 0, 0, 0))
    cd = ImageDraw.Draw(core_im)
    rw = W * 0.20
    cd.polygon([(cx - rw, H * 0.42), (cx + rw * 0.55, H * 0.34),
                (cx + rw * 0.30, H * 0.78), (cx - rw * 0.62, H * 0.72)],
               fill=core + (255,))
    core_im = core_im.filter(ImageFilter.GaussianBlur(W * 0.045))
    core_im.putalpha(core_im.getchannel('A').point(lambda v: int(v * 0.55)))
    im.alpha_composite(core_im)

    # 台面高光
    hl = Image.new('RGBA', im.size, (0, 0, 0, 0))
    hd = ImageDraw.Draw(hl)
    hd.polygon([(P['tl'][0] + W * 0.02, P['tl'][1] + H * 0.012),
                (P['tr'][0] - W * 0.03, P['tr'][1] + H * 0.012),
                (P['tr'][0] - W * 0.10, P['tr'][1] + H * 0.055),
                (P['tl'][0] + W * 0.07, P['tl'][1] + H * 0.055)],
               fill=(255, 255, 255, 120))
    hl = hl.filter(ImageFilter.GaussianBlur(W * 0.006))
    im.alpha_composite(hl)

    # 边缘棱线
    rim = Image.new('RGBA', im.size, (0, 0, 0, 0))
    rd = ImageDraw.Draw(rim)
    for keys in [['gl', 'gc'], ['gc', 'gr'], ['gc', 'tip'], ['tl', 'ml'], ['tr', 'mr']]:
        rd.line([P[x] for x in keys], fill=(255, 255, 255, 70), width=max(2, int(W * 0.006)))
    im.alpha_composite(rim)

    im = outline(im, outline_col + (255,), width=max(2, int(W * 0.012)))
    im = glow(im, glow_col, 0.40, max(3, int(W * 0.035)))
    return _done(im, size)


# ---------------------------------------------------------------- 金币
def coin_icon(size, base=(244, 190, 84), light=(255, 248, 208), deep=(172, 110, 32),
              outline_col=(78, 46, 10), emblem='star'):
    W, H = int(size[0] * SS), int(size[1] * SS)
    im = _canvas(size)
    d = ImageDraw.Draw(im)
    cx, cy = W / 2, H / 2
    R = min(W, H) * 0.46

    # 外圈（暗）
    d.ellipse((cx - R, cy - R * 0.98, cx + R, cy + R * 0.98), fill=deep + (255,))
    # 主体
    R2 = R * 0.92
    d.ellipse((cx - R2, cy - R2 * 0.98, cx + R2, cy + R2 * 0.98), fill=_shade(base, 0.94) + (255,))
    # 币面
    R3 = R * 0.76
    d.ellipse((cx - R3, cy - R3 * 0.98, cx + R3, cy + R3 * 0.98), fill=base + (255,))

    # 齿纹
    for i in range(32):
        a = i * math.pi * 2 / 32
        x1 = cx + math.cos(a) * R * 0.955
        y1 = cy + math.sin(a) * R * 0.955 * 0.98
        x2 = cx + math.cos(a) * R * 0.885
        y2 = cy + math.sin(a) * R * 0.885 * 0.98
        d.line([(x1, y1), (x2, y2)], fill=_shade(deep, 1.25) + (255,),
               width=max(1, int(R * 0.055)))

    # 中央浮雕：四芒古币星纹
    R4 = R3 * 0.50
    sw = R4 * 0.30
    star = [(cx, cy - R4), (cx + sw, cy - sw), (cx + R4, cy), (cx + sw, cy + sw),
            (cx, cy + R4), (cx - sw, cy + sw), (cx - R4, cy), (cx - sw, cy - sw)]
    d.polygon(star, fill=_shade(base, 1.16) + (255,))
    d.line(star + [star[0]], fill=_shade(deep, 1.05) + (255,), width=max(2, int(R * 0.028)))
    # 中心小圆
    d.ellipse((cx - sw * 0.75, cy - sw * 0.75, cx + sw * 0.75, cy + sw * 0.75),
              fill=_shade(deep, 1.05) + (255,))

    # 币面内圈线
    d.arc((cx - R3 * 0.99, cy - R3 * 0.99 * 0.98, cx + R3 * 0.99, cy + R3 * 0.99 * 0.98),
          start=0, end=360, fill=_shade(deep, 1.4) + (255,), width=max(1, int(R * 0.035)))

    # 斜向高光
    hl = Image.new('RGBA', im.size, (0, 0, 0, 0))
    hd = ImageDraw.Draw(hl)
    hd.polygon([(cx - R * 1.10, cy + R * 0.10), (cx - R * 0.55, cy - R * 1.10),
                (cx - R * 0.10, cy - R * 1.10), (cx - R * 0.68, cy + R * 0.10)],
               fill=light + (110,))
    hl = hl.filter(ImageFilter.GaussianBlur(R * 0.10))
    m = Image.new('L', im.size, 0)
    ImageDraw.Draw(m).ellipse((cx - R2, cy - R2 * 0.98, cx + R2, cy + R2 * 0.98), fill=255)
    hl.putalpha(Image.composite(hl.getchannel('A'), Image.new('L', im.size, 0), m))
    im.alpha_composite(hl)

    im = outline(im, outline_col + (255,), width=max(2, int(R * 0.075)))
    im = glow(im, (255, 210, 130), 0.34, max(3, int(W * 0.03)))
    return _done(im, size)


# ---------------------------------------------------------------- 闪电
def bolt_icon(size, col=(255, 206, 92), deep=(178, 108, 22), outline_col=(58, 34, 8)):
    W, H = int(size[0] * SS), int(size[1] * SS)
    im = _canvas(size)
    d = ImageDraw.Draw(im)
    pts = [(0.56, 0.04), (0.16, 0.56), (0.44, 0.56), (0.34, 0.96),
           (0.84, 0.40), (0.54, 0.40), (0.72, 0.04)]
    P = [(p[0] * W, p[1] * H) for p in pts]
    d.polygon(P, fill=col + (255,))
    # 左侧暗面
    d.polygon([P[0], P[1], P[2], (0.44 * W, 0.56 * H), (0.46 * W, 0.20 * H)],
              fill=_shade(col, 0.78) + (255,))
    im = outline(im, outline_col + (255,), width=max(2, int(W * 0.035)))
    im = glow(im, (255, 220, 120), 0.40, max(2, int(W * 0.03)))
    return _done(im, size)


# ---------------------------------------------------------------- 加号
def plus_icon(size, col=(255, 226, 150), deep=(180, 120, 30), outline_col=(70, 44, 10)):
    W, H = int(size[0] * SS), int(size[1] * SS)
    im = _canvas(size)
    d = ImageDraw.Draw(im)
    th = 0.22
    pts = [(0.5 - th / 2, 0.10), (0.5 + th / 2, 0.10), (0.5 + th / 2, 0.5 - th / 2),
           (0.90, 0.5 - th / 2), (0.90, 0.5 + th / 2), (0.5 + th / 2, 0.5 + th / 2),
           (0.5 + th / 2, 0.90), (0.5 - th / 2, 0.90), (0.5 - th / 2, 0.5 + th / 2),
           (0.10, 0.5 + th / 2), (0.10, 0.5 - th / 2), (0.5 - th / 2, 0.5 - th / 2)]
    d.polygon([(p[0] * W, p[1] * H) for p in pts], fill=col + (255,))
    im = outline(im, outline_col + (255,), width=max(2, int(W * 0.05)))
    return _done(im, size)


# ---------------------------------------------------------------- 书本
def book_icon(size, cover=(158, 62, 46), page=(248, 236, 206), gold=(232, 184, 84),
              outline_col=(52, 20, 14)):
    W, H = int(size[0] * SS), int(size[1] * SS)
    im = _canvas(size)
    d = ImageDraw.Draw(im)
    # 书页（右下偏移）
    d.polygon([(0.30 * W, 0.20 * H), (0.92 * W, 0.26 * H),
               (0.90 * W, 0.82 * H), (0.28 * W, 0.78 * H)], fill=page + (255,))
    for i in range(5):
        t = 0.14 + i * 0.13
        d.line([(0.32 * W, t * H), (0.90 * W, (t + 0.05) * H)],
               fill=(212, 196, 160, 255), width=max(1, int(W * 0.012)))
    # 封面
    d.polygon([(0.10 * W, 0.14 * H), (0.80 * W, 0.20 * H),
               (0.78 * W, 0.80 * H), (0.08 * W, 0.74 * H)], fill=cover + (255,))
    d.polygon([(0.10 * W, 0.14 * H), (0.19 * W, 0.155 * H),
               (0.17 * W, 0.745 * H), (0.08 * W, 0.74 * H)],
              fill=_shade(cover, 0.68) + (255,))
    # 金饰：中央菱形徽记 + 边角
    cx, cy = 0.44 * W, 0.47 * H
    r = W * 0.10
    d.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], fill=gold + (255,))
    d.polygon([(cx, cy - r * 0.55), (cx + r * 0.55, cy), (cx, cy + r * 0.55), (cx - r * 0.55, cy)],
              fill=_shade(gold, 1.3) + (255,))
    im = outline(im, outline_col + (255,), width=max(2, int(W * 0.028)))
    return _done(im, size)


# ---------------------------------------------------------------- 布袋
def pouch_icon(size, body=(178, 122, 66), dark=(112, 70, 30), gold=(232, 186, 92),
               outline_col=(56, 32, 12)):
    W, H = int(size[0] * SS), int(size[1] * SS)
    im = _canvas(size)
    d = ImageDraw.Draw(im)
    # 袋身
    d.polygon([(0.22 * W, 0.36 * H), (0.78 * W, 0.36 * H),
               (0.93 * W, 0.76 * H), (0.86 * W, 0.92 * H),
               (0.14 * W, 0.92 * H), (0.07 * W, 0.76 * H)], fill=body + (255,))
    # 左侧暗面
    d.polygon([(0.22 * W, 0.36 * H), (0.36 * W, 0.36 * H),
               (0.30 * W, 0.92 * H), (0.14 * W, 0.92 * H), (0.07 * W, 0.76 * H)],
              fill=_shade(body, 0.76) + (255,))
    # 袋口
    d.polygon([(0.24 * W, 0.20 * H), (0.76 * W, 0.20 * H),
               (0.80 * W, 0.40 * H), (0.20 * W, 0.40 * H)], fill=_shade(body, 0.88) + (255,))
    # 束绳 + 金珠
    d.rounded_rectangle((0.17 * W, 0.33 * H, 0.83 * W, 0.42 * H),
                        radius=int(W * 0.045), fill=dark + (255,))
    d.ellipse((0.62 * W, 0.29 * H, 0.80 * W, 0.44 * H), fill=gold + (255,))
    d.ellipse((0.66 * W, 0.32 * H, 0.74 * W, 0.39 * H), fill=_shade(gold, 1.35) + (255,))
    # 高光
    hl = Image.new('RGBA', im.size, (0, 0, 0, 0))
    ImageDraw.Draw(hl).ellipse((0.30 * W, 0.46 * H, 0.62 * W, 0.72 * H),
                               fill=(255, 236, 190, 70))
    hl = hl.filter(ImageFilter.GaussianBlur(W * 0.03))
    im.alpha_composite(hl)
    im = outline(im, outline_col + (255,), width=max(2, int(W * 0.030)))
    return _done(im, size)


# ---------------------------------------------------------------- 漩涡符文
def swirl_icon(size, ring=(96, 168, 132), core=(58, 42, 84), gold=(246, 202, 108),
               outline_col=(28, 18, 44)):
    W, H = int(size[0] * SS), int(size[1] * SS)
    im = _canvas(size)
    d = ImageDraw.Draw(im)
    R = min(W, H) * 0.45
    cx, cy = W / 2, H / 2
    d.ellipse((cx - R, cy - R, cx + R, cy + R), fill=core + (255,))
    d.ellipse((cx - R * 0.86, cy - R * 0.86, cx + R * 0.86, cy + R * 0.86),
              outline=gold + (255,), width=max(2, int(R * 0.10)))
    # 螺旋
    pts = []
    for i in range(160):
        t = i / 159.0
        ang = t * math.pi * 4.2
        rr = R * (0.16 + 0.62 * t)
        pts.append((cx + math.cos(ang) * rr, cy + math.sin(ang) * rr))
    d.line(pts, fill=gold + (255,), width=max(3, int(R * 0.20)), joint='curve')
    im = outline(im, outline_col + (255,), width=max(2, int(W * 0.028)))
    return _done(im, size)


# ---------------------------------------------------------------- 兽爪印
def paw_icon(size, pad=(226, 176, 78), dark=(140, 94, 30), outline_col=(56, 34, 10)):
    W, H = int(size[0] * SS), int(size[1] * SS)
    im = _canvas(size)
    d = ImageDraw.Draw(im)
    # 掌垫
    d.ellipse((0.24 * W, 0.48 * H, 0.76 * W, 0.92 * H), fill=pad + (255,))
    # 四趾
    toes = [(0.16, 0.36, 0.16, 0.22), (0.36, 0.24, 0.20, 0.24),
            (0.62, 0.24, 0.20, 0.24), (0.82, 0.36, 0.16, 0.22)]
    for cx_, cy_, rw, rh in toes:
        d.ellipse(((cx_ - rw / 2) * W, (cy_ - rh / 2) * H,
                   (cx_ + rw / 2) * W, (cy_ + rh / 2) * H), fill=pad + (255,))
    # 阴影内圈
    im2 = im.copy()
    d2 = ImageDraw.Draw(im2)
    d2.ellipse((0.30 * W, 0.56 * H, 0.70 * W, 0.86 * H), fill=_shade(dark, 1.0) + (90,))
    im = Image.alpha_composite(im, im2.filter(ImageFilter.GaussianBlur(W * 0.02)))
    im = outline(im, outline_col + (255,), width=max(2, int(W * 0.030)))
    return _done(im, size)


# ---------------------------------------------------------------- 宝石堆
def gems_pile_icon(size, fam=None):
    """三颗大小不一的宝石堆成一堆（商店图标）。"""
    fam = fam or [dict(base=(74, 196, 146), core=(196, 255, 228), deep=(18, 84, 68),
                        outline_col=(14, 40, 34)),
                  dict(base=(178, 126, 246), core=(242, 218, 255), deep=(68, 32, 112),
                       outline_col=(32, 16, 56)),
                  dict(base=(240, 176, 70), core=(255, 236, 186), deep=(140, 80, 16),
                       outline_col=(58, 32, 8))]
    W, H = int(size[0] * SS), int(size[1] * SS)
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    spots = [(0.30, 0.62, 0.40), (0.66, 0.66, 0.36), (0.50, 0.36, 0.34)]
    for (cx_, cy_, s_), f in zip(spots, fam):
        g = gem_icon((int(W * s_), int(H * s_)), **f)
        im.alpha_composite(g, (int(cx_ * W - g.width / 2), int(cy_ * H - g.height / 2)))
    return _done(im, size)
