# -*- coding: utf-8 -*-
"""#119（btnBoost 闪电）与 #120（btnBook 书本）：黄底板 → 墨绿苔石。

这两块底板是纯金黄、图标是深棕同色系，直接换绿会糊在一起。
所以走「抹平 + 重绘金色图标」：
  1) 从备份读整块，按亮度/暖度找出原图标，diffuse_fill 抹平回底板
  2) 整块 jadeify 换绿
  3) 画深棕描边 + 金色图标（闪电 / 书本），与 #121 的金箭头同一套配色
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from beast_sheet import crop, diffuse_fill, dilate, load_sheet  # noqa: E402
from jade_buttons import jadeify  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SHEET = os.path.join(ROOT, 'Assets', 'Merge Beast', 'Image', 'SpriteSheet', 'Beast_SpriteSheet.png')
BAK = os.path.join(HERE, 'backup_beast', 'Beast_SpriteSheet.png')
LOOK = os.path.join(HERE, 'look')

GOLD = (250, 206, 96, 255)
GOLD_HI = (255, 236, 160, 255)
GOLD_D = (196, 138, 34, 255)
EDGE = (44, 26, 8, 255)

SPEC = {
    # idx: (抹平区域 x0,x1,y0,y1, 亮度上限)
    119: ((0.12, 0.90, 0.02, 0.98), 0.62),
    120: ((0.04, 0.97, 0.05, 0.99), 0.74),
}


def luma(rgb):
    return (0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]) / 255.0


def flatten(block, region, thr):
    a = np.asarray(block).astype(np.float32)
    rgb, alpha = a[..., :3], a[..., 3:4]
    L = luma(rgb)
    warm = (rgb[..., 0] - rgb[..., 2]) / np.maximum(rgb[..., 0], 1.0)
    h, w = L.shape
    yy, xx = np.mgrid[0:h, 0:w]
    x0, x1, y0, y1 = region
    rm = (xx > w * x0) & (xx < w * x1) & (yy > h * y0) & (yy < h * y1)
    m = (L < thr) & (warm > 0.30) & rm
    m = dilate(m, 3) & rm
    filled = diffuse_fill(rgb, m, iters=160, sigma=1.9)
    return Image.fromarray(np.concatenate([filled, alpha], axis=2).round().astype(np.uint8), 'RGBA')


def draw_bolt(d, w, h):
    """金色闪电：深棕描边 + 金填充 + 左上亮面。"""
    cx, cy = w * 0.555, h * 0.515
    sw, sh = w * 0.230, h * 0.300
    pts = [(-0.34, -1.00), (0.64, -1.00), (0.22, -0.10),
           (0.64, -0.10), (-0.12, 1.00), (0.04, 0.10), (-0.32, 0.10)]
    poly = [(cx + px * sw, cy + py * sh) for px, py in pts]
    d.polygon(poly, fill=GOLD, outline=EDGE)
    # 亮面：左半边叠一条浅金
    hi = [(cx + px * sw, cy + py * sh) for px, py in
          [(-0.34, -1.00), (0.16, -1.00), (-0.04, -0.10), (-0.32, 0.10)]]
    d.polygon(hi, fill=GOLD_HI)
    d.line(poly + [poly[0]], fill=EDGE, width=max(2, int(w * 0.016)), joint='curve')


def draw_book(d, w, h):
    """斜放的金边书：金边封面朝上，书口是浅金书页。"""
    cx, cy = w * 0.50, h * 0.485
    S = 0.90                             # 整体缩一点，别顶满圆角
    # 顶面四点（平行四边形，斜放）
    A = (cx - w * 0.295 * S, cy - h * 0.110 * S)
    B = (cx + w * 0.145 * S, cy - h * 0.375 * S)
    C = (cx + w * 0.325 * S, cy + h * 0.030 * S)
    DD = (cx - w * 0.115 * S, cy + h * 0.285 * S)
    dk = h * 0.100 * S                   # 书厚
    # 书页侧面（左厚、右厚）
    d.polygon([A, DD, (DD[0], DD[1] + dk), (A[0], A[1] + dk)], fill=(248, 228, 176, 255), outline=EDGE)
    d.polygon([C, DD, (DD[0], DD[1] + dk), (C[0], C[1] + dk)], fill=GOLD_HI, outline=EDGE)
    # 页纹
    for k in range(1, 4):
        y = k / 4.0
        d.line([(A[0] + 1, A[1] + dk * y), (DD[0] - 1, DD[1] + dk * y)],
               fill=(208, 178, 122, 255), width=max(1, int(h * 0.011)))

    # 封面：金色描边 + 深棕面
    ins = 0.075
    P = lambda p, c: (p[0] + (c[0] - p[0]) * ins, p[1] + (c[1] - p[1]) * ins)
    band = [P(A, (cx, cy)), P(B, (cx, cy)), P(C, (cx, cy)), P(DD, (cx, cy))]
    d.polygon([A, B, C, DD], fill=EDGE)
    d.polygon(band, fill=GOLD, outline=(150, 98, 18, 255))
    ins2 = 0.20
    Q = lambda p, c: (p[0] + (c[0] - p[0]) * ins2, p[1] + (c[1] - p[1]) * ins2)
    cover = [Q(A, (cx, cy)), Q(B, (cx, cy)), Q(C, (cx, cy)), Q(DD, (cx, cy))]
    d.polygon(cover, fill=(128, 84, 30, 255), outline=(60, 36, 8, 255))
    # 封面上的金色菱徽
    mx, my = (cover[0][0] + cover[2][0]) / 2, (cover[0][1] + cover[2][1]) / 2
    rw, rh = w * 0.058, h * 0.062
    d.polygon([(mx, my - rh), (mx + rw, my), (mx, my + rh), (mx - rw, my)],
              fill=GOLD, outline=(60, 36, 8, 255))
    d.polygon([(mx, my - rh * 0.45), (mx + rw * 0.42, my), (mx, my + rh * 0.45), (mx - rw * 0.42, my)],
              fill=GOLD_HI)


def build_one(im, box, idx):
    x, y, w, h = box
    region, thr = SPEC[idx]
    block = crop(Image.open(BAK).convert('RGBA'), box)
    flat = flatten(block, region, thr)
    patch = jadeify(flat)
    d = ImageDraw.Draw(patch)
    if idx == 119:
        draw_bolt(d, w, h)
    else:
        draw_book(d, w, h)
    # alpha 用备份原通道，避免描边/填充溢出到透明的圆角外
    arr = np.asarray(patch).copy()
    arr[..., 3] = np.asarray(block)[..., 3]
    im.paste(Image.fromarray(arr, 'RGBA'), (x, y))


TARGETS = [119, 120]


def preview(im, rects):
    cell = 240
    cols = len(TARGETS) + 1
    sheet = Image.new('RGBA', (cell * cols, cell * 2), (20, 40, 34, 255))
    d = ImageDraw.Draw(sheet)
    items = list(TARGETS) + [121]
    for i, idx in enumerate(items):
        x, y, w, h = rects['Beast_SpriteSheet_%d' % idx]
        old = crop(Image.open(SHEET).convert('RGBA'), (x, y, w, h))
        new = im.crop((x, y, x + w, y + h))
        for j, c in enumerate((old, new)):
            k = min((cell - 26) / max(c.size), 3.0)
            s = c.resize((max(1, int(c.width * k)), max(1, int(c.height * k))), Image.LANCZOS)
            sheet.alpha_composite(s, (i * cell + (cell - s.width) // 2, j * cell + (cell - s.height) // 2))
        d.text((i * cell + 6, 4), '#%d' % idx, fill=(255, 230, 120, 255))
    out = os.path.join(LOOK, 'jade_more.png')
    sheet.convert('RGB').save(out, quality=95)
    print(out)


if __name__ == '__main__':
    base, rects = load_sheet()
    rects = dict((n, (x, y, w, h)) for n, x, y, w, h in rects)
    im = Image.open(SHEET).convert('RGBA')
    before = np.asarray(im).copy()
    for idx in TARGETS:
        build_one(im, rects['Beast_SpriteSheet_%d' % idx], idx)
    after = np.asarray(im)
    diff = (np.abs(after.astype(np.int16) - before.astype(np.int16)).sum(axis=2) > 0)
    allowed = np.zeros(diff.shape, bool)
    for idx in TARGETS:
        x, y, w, h = rects['Beast_SpriteSheet_%d' % idx]
        allowed[y:y + h, x:x + w] = True
    print('changed %d  越界 %d  alpha变化 %d'
          % (diff.sum(), (diff & ~allowed).sum(), (after[..., 3] != before[..., 3]).sum()))
    if '--apply' in sys.argv:
        im.save(SHEET)
        print('saved', SHEET, im.size, im.mode)
    else:
        preview(im, rects)
