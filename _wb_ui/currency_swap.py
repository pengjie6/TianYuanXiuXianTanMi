# -*- coding: utf-8 -*-
"""货币图标替换：
#10（顶部第一条，紫/品红宝石）→ 红宝石（亮度梯度重映射，切面结构保留）
#45（顶部第二条，蓝白爪痕牌）→ 普通金币（重画）

两个切片都只改自己的 rect；尺寸、.meta 全不变。
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SHEET = os.path.join(ROOT, 'Assets', 'Merge Beast', 'Image', 'SpriteSheet', 'Beast_SpriteSheet.png')
LOOK = os.path.join(HERE, 'look')
RECTS = os.path.join(HERE, 'bs_rects.json')

# 红宝石色带
RUBY_L = [0.00, 0.12, 0.26, 0.42, 0.58, 0.74, 0.88, 1.00]
RUBY_C = [(28, 2, 8), (62, 4, 14), (104, 8, 22), (150, 14, 34),
          (192, 28, 50), (224, 72, 88), (246, 146, 146), (255, 228, 228)]

RIM = (58, 33, 6)


def ramp(l, stop_l, stop_c):
    out = np.zeros(l.shape + (3,), np.float32)
    for i in range(3):
        out[..., i] = np.interp(l, stop_l, [c[i] for c in stop_c])
    return out


def remap(img, stop_l, stop_c, keep_dark=0.0):
    """按亮度整块换色（宝石这类纯色立体物，不需要 warm 判据）。"""
    a = np.asarray(img).astype(np.float32) / 255.0
    rgb = a[..., :3]
    L = 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]
    tgt = ramp(L, stop_l, stop_c) / 255.0
    if keep_dark > 0:
        tgt = np.where((L < keep_dark)[..., None], tgt * 0.8, tgt)
    res = np.concatenate([np.clip(tgt, 0, 1) * 255.0, a[..., 3:4] * 255.0], axis=2)
    return Image.fromarray(res.round().astype(np.uint8), 'RGBA')


# ---------------------------------------------------------------- 金币
def coin(size=88, ss=6):
    """普通金币：深棕描边 + 径向金渐变 + 一道内凹线 + 粗 ¥ 浮雕。
    圆外的 RGB 必须填成描边色，否则缩放时透明边缘会插出彩色脏边。"""
    S = size * ss
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
    cx = cy = S / 2.0
    R = S * 0.5 - S * 0.008
    dist = np.minimum(np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / R, 1.0)

    center = np.array([255, 226, 126], np.float32)
    mid = np.array([238, 182, 52], np.float32)
    edge = np.array([190, 120, 24], np.float32)
    t = dist[..., None]
    lo = center[None, None, :] * (1 - t / 0.62) + mid[None, None, :] * (t / 0.62)
    hi = mid[None, None, :] * (1 - (t - 0.62) / 0.38) + edge[None, None, :] * ((t - 0.62) / 0.38)
    grad = np.where((t <= 0.62), lo, hi)

    hl = np.clip(1.0 - np.sqrt((xx - S * 0.32) ** 2 + (yy - S * 0.24) ** 2) / (S * 0.30), 0, 1) ** 2
    grad = np.clip(grad + np.array([255, 250, 225], np.float32) * (hl[..., None] * 0.40), 0, 255)

    # 外描边 + 内凹线（按半径遮罩，不用 PIL 的 ellipse 描边，避免接缝）
    grad = np.where(((dist > 0.962))[..., None], np.array(RIM, np.float32), grad)
    grad = np.where((((dist > 0.900) & (dist <= 0.916)))[..., None],
                    np.array([166, 102, 16], np.float32), grad)
    # 圆外统一填描边色，缩放时只会有深棕过渡
    grad = np.where((dist >= 1.0)[..., None], np.array(RIM, np.float32), grad)

    alpha = np.clip((1.0 - dist) * R / (S * 0.006), 0, 1) * 255.0
    img = Image.fromarray(np.concatenate([grad, alpha[..., None]], axis=2)
                          .clip(0, 255).round().astype(np.uint8), 'RGBA')

    # ¥ 浮雕：先画深金，再上移一点画亮金
    def yen(dy, col, k, wmul=1.0):
        d = ImageDraw.Draw(img)
        bw = S * 0.052 * k * wmul
        d.rectangle((cx - bw, cy - S * 0.235 + S * dy, cx + bw, cy + S * 0.235 + S * dy), fill=col)
        for sgn in (-1, 1):
            d.line([(cx + sgn * S * 0.175 * k, cy - S * 0.275 + S * dy),
                    (cx, cy + S * 0.030 + S * dy)],
                   fill=col, width=max(3, int(S * 0.038 * k * wmul)))
        for yy0 in (0.050, 0.140):
            d.rectangle((cx - S * 0.150 * k, cy + S * yy0 + S * dy - S * 0.023,
                         cx + S * 0.150 * k, cy + S * yy0 + S * dy + S * 0.023), fill=col)

    yen(0.016, (162, 98, 12), 1.06)
    yen(0.000, (255, 232, 148), 1.0)

    return img.resize((size, size), Image.LANCZOS)


def build(rects):
    im = Image.open(SHEET).convert('RGBA')
    before = np.asarray(im).copy()

    x, y, w, h = rects['Beast_SpriteSheet_10']
    im.paste(remap(im.crop((x, y, x + w, y + h)), RUBY_L, RUBY_C, 0.10), (x, y))

    x, y, w, h = rects['Beast_SpriteSheet_45']
    patch = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    c = coin(min(w, h))
    patch.alpha_composite(c, ((w - c.width) // 2, (h - c.height) // 2))
    im.paste(patch, (x, y))

    after = np.asarray(im)
    diff = (np.abs(after.astype(np.int16) - before.astype(np.int16)).sum(2) > 0)
    print('changed %d  alpha changed %d' % (diff.sum(), int((after[..., 3] != before[..., 3]).sum())))
    return im, rects


def preview(im, rects):
    cell = 220
    sheet = Image.new('RGBA', (cell * 2, cell * 2), (18, 36, 31, 255))
    d = ImageDraw.Draw(sheet)
    for i, idx in enumerate((10, 45)):
        x, y, w, h = rects['Beast_SpriteSheet_%d' % idx]
        old = Image.open(SHEET).convert('RGBA').crop((x, y, x + w, y + h))
        new = im.crop((x, y, x + w, y + h))
        for j, c in enumerate((old, new)):
            k = min((cell - 34) / c.width, (cell - 34) / c.height)
            s = c.resize((int(c.width * k), int(c.height * k)), Image.LANCZOS)
            sheet.alpha_composite(s, (i * cell + (cell - s.width) // 2, j * cell + (cell - s.height) // 2))
        d.text((i * cell + 8, 4), '#%d' % idx, fill=(255, 230, 120, 255))
    out = os.path.join(LOOK, 'currency_swap.png')
    sheet.convert('RGB').save(out, quality=95)
    print(out)


if __name__ == '__main__':
    rects = dict((n, (x, y, w, h)) for n, x, y, w, h in json.load(open(RECTS, encoding='utf-8')))
    im, rects = build(rects)
    if '--apply' in sys.argv:
        im.save(SHEET)
        print('saved', im.size, im.mode)
    else:
        preview(im, rects)
        b = coin(88)
        b.resize((b.width * 6, b.height * 6), Image.LANCZOS).convert('RGB').save(
            os.path.join(LOOK, 'coin_big.png'), quality=95)
