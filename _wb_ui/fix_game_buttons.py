# -*- coding: utf-8 -*-
"""替换 UI Game/ 里真正在用的金色按钮图标（此前误改的 UI Main/ 是没人引用的死图）。

按钮底板沿用第一轮定的墨绿苔石 + 金边风格，图标全部换成矢量绘制的非猫符号。
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import iconize as IZ
from apply_icons import make_plate, shadow
from vector_icons import bolt_icon, book_icon, pouch_icon, swirl_icon, gems_pile_icon, _shade, outline
from currency_icons import token_icon

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
GAME = os.path.join(ROOT, 'Assets', 'Merge Beast', 'Image', 'UI Game')
LOOK = os.path.join(HERE, 'look')
SS = 4


# ---------------------------------------------------------------- 狼头
def wolf_head_icon(size, base=(252, 220, 138), deep=(160, 98, 28),
                   dark=(52, 30, 8), eye=(34, 22, 10)):
    """正面狼头：圆头 + 两只独立尖耳 + 长吻，金铜色。mask 合成保证轮廓可读。"""
    W, H = int(size[0] * SS), int(size[1] * SS)
    s = min(W, H) * 0.98
    ox, oy = (W - s) / 2, (H - s) / 2

    def P(pts):
        return [(ox + x * s, oy + y * s) for x, y in pts]

    # ---- 轮廓 mask
    mask = Image.new('L', (W, H), 0)
    md = ImageDraw.Draw(mask)
    head = [(0.500, 0.300), (0.640, 0.340), (0.790, 0.410), (0.825, 0.520),
            (0.800, 0.660), (0.720, 0.790), (0.610, 0.900), (0.500, 0.955),
            (0.390, 0.900), (0.280, 0.790), (0.200, 0.660), (0.175, 0.520),
            (0.210, 0.410), (0.360, 0.340)]
    md.polygon(P(head), fill=255)
    md.polygon(P([(0.640, 0.360), (0.985, 0.015), (0.845, 0.470)]), fill=255)
    md.polygon(P([(0.360, 0.360), (0.015, 0.015), (0.155, 0.470)]), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(s * 0.002))

    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    # 底色（上亮下深）
    d.bitmap((0, 0), mask, fill=deep + (255,))
    top = Image.new('RGBA', (W, H), base + (255,))
    gmask = Image.new('L', (W, H), 0)
    ImageDraw.Draw(gmask).rectangle((0, 0, W, int(H * 0.62)), fill=255)
    gmask = gmask.filter(ImageFilter.GaussianBlur(s * 0.10))
    top.putalpha(Image.composite(gmask, Image.new('L', (W, H), 0), mask))
    im.alpha_composite(top)

    # 内耳
    for pts in ([(0.700, 0.230), (0.930, 0.075), (0.835, 0.420)],
                [(0.300, 0.230), (0.070, 0.075), (0.165, 0.420)]):
        d.polygon(P(pts), fill=_shade(deep, 0.74) + (255,))

    # 长吻亮面
    d.polygon(P([(0.500, 0.470), (0.570, 0.590), (0.545, 0.880), (0.500, 0.935),
                 (0.455, 0.880), (0.430, 0.590)]), fill=_shade(base, 1.09) + (255,))
    # 鼻
    d.polygon(P([(0.500, 0.790), (0.548, 0.845), (0.500, 0.905), (0.452, 0.845)]),
              fill=eye + (255,))
    # 眼（上斜细眼）
    d.polygon(P([(0.330, 0.470), (0.440, 0.505), (0.436, 0.560), (0.334, 0.520)]), fill=eye + (255,))
    d.polygon(P([(0.670, 0.470), (0.560, 0.505), (0.564, 0.560), (0.666, 0.520)]), fill=eye + (255,))

    # 只在 mask 内保留细节
    im.putalpha(Image.composite(im.getchannel('A'), Image.new('L', (W, H), 0), mask))
    im = outline(im, dark + (255,), width=max(2, int(s * 0.026)))
    return im.resize(size, Image.LANCZOS)


def ring_icon(size, inner, ring=(248, 246, 238), ring_dark=(176, 168, 150)):
    """白环 + 深色内盘 + 中心图标。"""
    W, H = int(size[0] * SS), int(size[1] * SS)
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx, cy = W / 2, H / 2
    R = min(W, H) * 0.47
    d.ellipse((cx - R, cy - R, cx + R, cy + R), fill=ring_dark + (255,))
    d.ellipse((cx - R * 0.96, cy - R * 0.96, cx + R * 0.96, cy + R * 0.96), fill=ring + (255,))
    d.ellipse((cx - R * 0.76, cy - R * 0.76, cx + R * 0.76, cy + R * 0.76), fill=(20, 34, 30, 255))
    grad = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(grad).ellipse((cx - R * 0.76, cy - R * 0.76, cx + R * 0.76, cy + R * 0.30),
                                 fill=(60, 120, 96, 110))
    grad = grad.filter(ImageFilter.GaussianBlur(R * 0.08))
    m = Image.new('L', (W, H), 0)
    ImageDraw.Draw(m).ellipse((cx - R * 0.76, cy - R * 0.76, cx + R * 0.76, cy + R * 0.76), fill=255)
    grad.putalpha(Image.composite(grad.getchannel('A'), Image.new('L', (W, H), 0), m))
    im.alpha_composite(grad)
    IZ.place_center(im, inner, cx, cy, int(R * 1.18))
    im = outline(im, (18, 30, 26, 255), width=max(2, int(R * 0.055)))
    return im.resize(size, Image.LANCZOS)


# ---------------------------------------------------------------- 装配
def plate_btn(path, icon, tone='jade', scale=0.54, radius=0.20, glow=None):
    w, h = Image.open(path).size
    canvas = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    canvas.alpha_composite(make_plate((w, h), tone, radius))
    if icon is not None:
        IZ.place_center(canvas, icon, w / 2, h / 2 + h * 0.015, int(min(w, h) * scale), glow)
    return canvas


def build(name, size):
    if name == 'btnDeleteBeast' or name == 'btnShopBeast':
        return plate_btn(os.path.join(GAME, name + '.png'), wolf_head_icon((256, 256)), 'jade', 0.66)
    if name == 'btn_Boost':
        return plate_btn(os.path.join(GAME, name + '.png'), bolt_icon((256, 256)), 'jade', 0.56)
    if name == 'btnUpgrade':
        return plate_btn(os.path.join(GAME, name + '.png'), book_icon((256, 256)), 'jade', 0.64)
    if name == 'btnBoost':
        return plate_btn(os.path.join(GAME, name + '.png'), pouch_icon((256, 256)), 'jade', 0.64)
    if name == 'btnShopIAP':
        return plate_btn(os.path.join(GAME, name + '.png'), gems_pile_icon((256, 256)), 'jade', 0.86)
    if name == 'icon_MergeClick':
        return plate_btn(os.path.join(GAME, name + '.png'), swirl_icon((256, 256)), 'dark', 0.74, 0.24)
    if name == 'icon_Buff':
        return ring_icon(size, burst_icon((256, 256)))
    raise KeyError(name)


def burst_icon(size, col=(250, 210, 120), deep=(170, 96, 28)):
    """四向光芒（增益）。"""
    W, H = int(size[0] * SS), int(size[1] * SS)
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx, cy = W / 2, H / 2
    R = min(W, H) * 0.46
    pts = []
    for i in range(16):
        a = -np.pi / 2 + i * np.pi / 8
        rr = R if i % 2 == 0 else R * 0.34
        pts.append((cx + np.cos(a) * rr, cy + np.sin(a) * rr))
    d.polygon(pts, fill=col + (255,))
    d.ellipse((cx - R * 0.22, cy - R * 0.22, cx + R * 0.22, cy + R * 0.22), fill=deep + (255,))
    im = outline(im, (46, 28, 8, 255), width=max(2, int(R * 0.07)))
    return im.resize(size, Image.LANCZOS)


TARGETS = ['btnDeleteBeast', 'btn_Boost', 'btnUpgrade', 'btnBoost',
           'btnShopBeast', 'btnShopIAP', 'icon_MergeClick', 'icon_Buff']


def preview():
    cell = 200
    sheet = Image.new('RGBA', (cell * len(TARGETS), cell * 2), (24, 48, 42, 255))
    d = ImageDraw.Draw(sheet)
    for i, n in enumerate(TARGETS):
        p = os.path.join(GAME, n + '.png')
        old = Image.open(p).convert('RGBA')
        new = build(n, old.size)
        for j, im in enumerate((old, new)):
            k = min((cell - 22) / max(im.size), 2.6)
            s = im.resize((max(1, int(im.width * k)), max(1, int(im.height * k))), Image.LANCZOS)
            sheet.alpha_composite(s, (i * cell + (cell - s.width) // 2, j * cell + (cell - s.height) // 2))
        d.text((i * cell + 6, cell * 2 - 12), n[:18], fill=(225, 240, 235, 255))
    out = os.path.join(LOOK, 'btns_after.png')
    sheet.convert('RGB').save(out, quality=94)
    print(out)


def apply():
    for n in TARGETS:
        p = os.path.join(GAME, n + '.png')
        old = Image.open(p)
        size, mode = old.size, old.mode
        new = build(n, size)
        s2, m2 = IZ.save_like(p, new)
        print('%-18s %dx%d/%s -> %dx%d/%s %s' % (n, size[0], size[1], mode, s2[0], s2[1], m2,
                                                 'OK' if (s2 == size and m2 == mode) else 'FAIL'))


if __name__ == '__main__':
    if '--apply' in sys.argv:
        apply()
    else:
        preview()
