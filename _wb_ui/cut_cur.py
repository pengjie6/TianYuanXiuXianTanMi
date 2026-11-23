# -*- coding: utf-8 -*-
"""AI 母图 → 抠图 → 描边 → 贴进 Beast_SpriteSheet 的 #10 / #45。

抠图不用"白底 flood fill"（AI 母图是浅灰渐变 + 地面投影，边界根本抓不住），
改成**按饱和度取主体 + 填内部空洞**：
  主体 = 高饱和像素 | 很暗像素；再从画布四角 flood 一遍，把"外部连通的非主体"判为背景。
这样宝石内部的高光、金币中间的浮雕都不会被挖成洞。
最后按目标尺寸补一圈深色描边，让 AI 图和游戏里其它图标风格对齐。
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ANCH = os.path.join(HERE, 'anchors')
LOOK = os.path.join(HERE, 'look')
SHEET = os.path.join(ROOT, 'Assets', 'Merge Beast', 'Image', 'SpriteSheet', 'Beast_SpriteSheet.png')
RECTS = os.path.join(HERE, 'bs_rects.json')


def cut(im, sat_thr=26, force_circle=False):
    im = im.convert('RGB')
    w, h = im.size
    rgb = np.asarray(im).astype(np.int16)
    mx = rgb.max(axis=2)
    mn = rgb.min(axis=2)
    core = ((mx - mn) > sat_thr) | (mx < 60)

    # 水印固定在右下角，先掐掉免得被当成主体
    core[int(h * 0.86):, int(w * 0.74):] = False

    # 注意：PIL 的 floodfill 在 'L' 图上不写入，必须走 RGB 才能生效（老坑）
    m = Image.fromarray((core * 255).astype(np.uint8), 'L').convert('RGB')
    for seed in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)):
        if m.getpixel(seed) == (0, 0, 0):
            try:
                ImageDraw.floodfill(m, seed, (255, 0, 255), thresh=0)
            except Exception:
                pass
    arr = np.asarray(m)
    is_bg = (arr[..., 0] == 255) & (arr[..., 1] == 0) & (arr[..., 2] == 255)
    alpha = np.where(is_bg, 0, 255).astype(np.uint8)

    # 贴地投影：低饱和、中等亮度、而且落在画面下半部 —— 主体本身要么高饱和要么很暗，不会中招
    lower = np.zeros_like(core)
    lower[int(h * 0.68):, :] = True
    shadow = lower & ((mx - mn) < 46) & (mx > 55) & (mx < 215)
    if shadow.any():
        sa = Image.fromarray((shadow * 255).astype(np.uint8), 'L')
        sa = sa.filter(ImageFilter.MaxFilter(9))     # 稍微外扩，吃掉过渡带
        alpha[np.asarray(sa) > 0] = 0

    a = Image.fromarray(alpha, 'L')
    a = a.filter(ImageFilter.MinFilter(5))          # 收一圈，去掉贴着主体的浅灰边
    if force_circle:
        # 硬币边缘被 AI 画得不圆/刻纹压到边，直接换成标准圆，免得留缺口
        bb = a.point(lambda v: 255 if v > 60 else 0).getbbox()
        if bb:
            cx, cy = (bb[0] + bb[2]) / 2.0, (bb[1] + bb[3]) / 2.0
            r = min(bb[2] - bb[0], bb[3] - bb[1]) / 2.0
            circle = Image.new('L', (w, h), 0)
            ImageDraw.Draw(circle).ellipse((cx - r, cy - r, cx + r, cy + r), fill=255)
            circle = circle.filter(ImageFilter.GaussianBlur(0.8))
            a = circle
    a = a.filter(ImageFilter.GaussianBlur(1.2))
    out = im.convert('RGBA')
    out.putalpha(a)
    bb = out.getchannel('A').point(lambda v: 255 if v > 60 else 0).getbbox()
    if bb:
        out = out.crop(bb)
    return out


def square(im, pad=0.02):
    bb = im.getchannel('A').getbbox()
    if not bb:
        return im
    l, t, r, b = bb
    cx, cy = (l + r) // 2, (t + b) // 2
    side = int(max(r - l, b - t) * (1 + pad * 2))
    canvas = Image.new('RGBA', (side, side), (0, 0, 0, 0))
    canvas.alpha_composite(im, (side // 2 - cx, side // 2 - cy))
    return canvas


def outline(icon, width=2, col=(54, 26, 32)):
    """按 alpha 外扩一圈深色描边。"""
    if width <= 0:
        return icon
    a = icon.getchannel('A')
    edge = a.filter(ImageFilter.MaxFilter(width * 2 + 1))
    out = Image.new('RGBA', icon.size, col + (255,))
    out.putalpha(edge)
    out.alpha_composite(icon)
    return out


def load_icon(name, box_w, box_h, ow=2, circle=False, stretch=False):
    ic = square(cut(Image.open(os.path.join(ANCH, name)), force_circle=circle))
    if stretch:
        # 母图里宝石偏横宽，原 rect 是竖长的 —— 直接非等比铺满，比例反而更接近原图
        ic = ic.resize((max(1, int(box_w * 0.99)), max(1, int(box_h * 0.99))), Image.LANCZOS)
    else:
        ic.thumbnail((int(box_w * 0.98), int(box_h * 0.98)), Image.LANCZOS)
    canvas = Image.new('RGBA', (box_w, box_h), (0, 0, 0, 0))
    canvas.alpha_composite(ic, ((box_w - ic.width) // 2, (box_h - ic.height) // 2))
    return outline(canvas, ow)


def build(pairs, apply=False):
    rects = dict((n, (x, y, w, h)) for n, x, y, w, h in json.load(open(RECTS, encoding='utf-8')))
    src = Image.open(SHEET).convert('RGBA')
    im = src.copy()
    before = np.asarray(im).copy()

    cw = 150
    prev = Image.new('RGBA', (cw * len(pairs) * 3, cw + 46), (18, 36, 31, 255))
    d = ImageDraw.Draw(prev)

    for i, (name, idx, ow, circle, stretch) in enumerate(pairs):
        x, y, w, h = rects['Beast_SpriteSheet_%d' % idx]
        ic = load_icon(name, w, h, ow, circle=circle, stretch=stretch)
        old = src.crop((x, y, x + w, y + h))

        patch = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        patch.alpha_composite(ic, ((w - ic.width) // 2, (h - ic.height) // 2))
        arr = np.asarray(patch).copy()
        arr[..., 3] = np.where(np.asarray(old)[..., 3] > 0, arr[..., 3], 0)
        im.paste(Image.fromarray(arr, 'RGBA'), (x, y))

        for j, c in enumerate((old, im.crop((x, y, x + w, y + h)), ic)):
            k = (cw - 16) / max(c.width, c.height)
            s = c.resize((max(1, int(c.width * k)), max(1, int(c.height * k))), Image.LANCZOS)
            prev.alpha_composite(s, (i * cw * 3 + j * cw + (cw - s.width) // 2,
                                     40 + (cw - s.height) // 2))
        d.text((i * cw * 3 + 8, 10), '#%d  %s' % (idx, name), fill=(255, 230, 120, 255))

    after = np.asarray(im)
    diff = (np.abs(after.astype(np.int16) - before.astype(np.int16)).sum(2) > 0)
    print('changed %d  alpha changed %d' % (diff.sum(), int((after[..., 3] != before[..., 3]).sum())))
    prev.convert('RGB').save(os.path.join(LOOK, 'currency_ai.png'), quality=95)
    print(os.path.join(LOOK, 'currency_ai.png'))
    if apply:
        im.save(SHEET)
        print('saved', im.size, im.mode)


if __name__ == '__main__':
    pairs = [('cur_ruby.png', 10, 2), ('cur_coin.png', 45, 2)]
    if len(sys.argv) > 1 and sys.argv[1].startswith('--'):
        pass
    else:
        pass
    build(pairs, apply='--apply' in sys.argv)
