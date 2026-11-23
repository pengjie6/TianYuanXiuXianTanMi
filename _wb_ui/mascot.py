# -*- coding: utf-8 -*-
"""把 AI 狐狸吉祥物抠出来，替换 UI Game 里三张猫角色图（Avatar / CatTutor / icon_Shop）。"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import iconize as IZ

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
GAME = os.path.join(ROOT, 'Assets', 'Merge Beast', 'Image', 'UI Game')
LOOK = os.path.join(HERE, 'look')


def erase_watermark(im):
    """右下角水印：先用邻近背景色涂掉，交给后续 flood fill。"""
    w, h = im.size
    arr = np.asarray(im).astype(np.float32)
    ref = arr[int(h * 0.86):int(h * 0.91), int(w * 0.70):w]
    col = np.median(ref.reshape(-1, 3), axis=0)
    y0, x0 = int(h * 0.915), int(w * 0.68)
    arr[y0:, x0:] = col
    return Image.fromarray(arr.astype(np.uint8), 'RGB')


def fade_shadow(im, alpha):
    """中性偏暗的像素（地面投影）压淡。"""
    a = np.asarray(alpha).astype(np.float32)
    rgb = np.asarray(im.convert('RGB')).astype(np.float32)
    mx = rgb.max(axis=2)
    mn = rgb.min(axis=2)
    val = mx / 255.0
    neutral = (mx - mn) < 26
    h = a.shape[0]
    low = np.zeros_like(neutral)
    low[int(h * 0.82):, :] = True     # 只处理脚部区域，避免误伤白色肚皮
    fade = np.where(neutral & low & (val < 0.86), 0.20, 1.0)
    return Image.fromarray((a * fade).astype(np.uint8), 'L')


def fill_holes(mask):
    """无 scipy 的补洞：从边框 floodfill 掉外部背景，剩下的 0 就是洞。"""
    m = mask.copy()
    w, h = m.size
    ImageDraw.Draw(m).rectangle((0, 0, w - 1, h - 1), outline=0, width=3)
    ImageDraw.floodfill(m, (0, 0), 128, thresh=0)
    arr = np.asarray(m)
    holes = arr == 0
    out = np.where(holes, 255, arr).astype(np.uint8)
    out[out == 128] = 0
    return Image.fromarray(out, 'L')


def cut_light(path, thresh=60):
    """浅灰棚拍背景：多seed flood fill + 补洞。水印区域额外补种。"""
    im = Image.open(path).convert('RGB')
    w, h = im.size
    im = erase_watermark(im)
    work = im.copy()
    marker = (0, 255, 0)
    seeds = [(2, 2), (w - 3, 2), (2, h - 3), (w - 3, h - 3)]
    seeds += [(x, 3) for x in range(0, w, w // 10)]
    seeds += [(x, h - 4) for x in range(0, w, w // 10)]
    seeds += [(3, y) for y in range(0, h, h // 10)]
    seeds += [(w - 4, y) for y in range(0, h, h // 10)]
    # 水印角落多点补种
    seeds += [(int(w * 0.78) + i * 12, int(h * 0.93) + j * 8) for i in range(8) for j in range(4)]
    for sd in seeds:
        try:
            if 0 <= sd[0] < w and 0 <= sd[1] < h:
                ImageDraw.floodfill(work, sd, marker, thresh=thresh)
        except Exception:
            pass
    arr = np.asarray(work).astype(np.int16)
    is_bg = (arr[..., 0] < 8) & (np.abs(arr[..., 1] - 255) < 8) & (arr[..., 2] < 8)
    fg_mask = Image.fromarray(np.where(is_bg, 0, 255).astype(np.uint8), 'L')
    fg_mask = fill_holes(fg_mask).filter(ImageFilter.MedianFilter(3))
    a = fade_shadow(im, fg_mask).filter(ImageFilter.GaussianBlur(1.0))
    out = im.convert('RGBA')
    out.putalpha(a)
    return trim(out, 0.02)


def trim(im, pad_ratio=0.02):
    bb = im.getchannel('A').getbbox()
    if not bb:
        return im
    l, t, r, b = bb
    pad = int(max(r - l, b - t) * pad_ratio)
    canvas = Image.new('RGBA', (r - l + pad * 2, b - t + pad * 2), (0, 0, 0, 0))
    canvas.paste(im.crop((l, t, r, b)), (pad, pad))
    return canvas


_SRC = None


def mascot():
    global _SRC
    if _SRC is None:
        _SRC = cut_light(os.path.join(HERE, 'anchors', 'mascot_fox.png'))
    return _SRC


def upper_body(src, keep=0.62):
    w, h = src.size
    return trim(src.crop((0, 0, w, int(h * keep))), 0.02)


def head_crop(src):
    """取上半部分当头像（去掉身体）。"""
    w, h = src.size
    return trim(src.crop((0, 0, w, int(h * 0.52))), 0.02)


def fit(canvas_size, icon, pad=0.04, anchor='center'):
    w, h = canvas_size
    out = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    k = min((w * (1 - pad * 2)) / icon.width, (h * (1 - pad * 2)) / icon.height)
    ic = icon.resize((max(1, int(icon.width * k)), max(1, int(icon.height * k))), Image.LANCZOS)
    if anchor == 'bottom':
        out.alpha_composite(ic, ((w - ic.width) // 2, h - ic.height - int(h * pad * 0.4)))
    else:
        out.alpha_composite(ic, ((w - ic.width) // 2, (h - ic.height) // 2))
    return out


def build(name, size):
    src = mascot()
    if name == 'Avatar':
        return fit(size, upper_body(src), 0.03)
    if name == 'CatTutor':
        return fit(size, src, 0.02, 'bottom')
    if name == 'icon_Shop':
        return fit(size, head_crop(src), 0.02)
    raise KeyError(name)


TARGETS = ['Avatar', 'CatTutor', 'icon_Shop']


def preview():
    cell = 240
    sheet = Image.new('RGBA', (cell * len(TARGETS), cell * 2), (24, 48, 42, 255))
    d = ImageDraw.Draw(sheet)
    for i, n in enumerate(TARGETS):
        p = os.path.join(GAME, n + '.png')
        old = Image.open(p).convert('RGBA')
        new = build(n, old.size)
        for j, im in enumerate((old, new)):
            k = min((cell - 20) / max(im.size), 2.4)
            s = im.resize((max(1, int(im.width * k)), max(1, int(im.height * k))), Image.LANCZOS)
            sheet.alpha_composite(s, (i * cell + (cell - s.width) // 2, j * cell + (cell - s.height) // 2))
        d.text((i * cell + 6, cell * 2 - 12), n, fill=(225, 240, 235, 255))
    out = os.path.join(LOOK, 'mascot_after.png')
    sheet.convert('RGB').save(out, quality=94)
    print(out)


def apply():
    for n in TARGETS:
        p = os.path.join(GAME, n + '.png')
        old = Image.open(p)
        size, mode = old.size, old.mode
        new = build(n, size)
        s2, m2 = IZ.save_like(p, new)
        print('%-12s %dx%d/%s -> %dx%d/%s %s' % (n, size[0], size[1], mode, s2[0], s2[1], m2,
                                                 'OK' if (s2 == size and m2 == mode) else 'FAIL'))


if __name__ == '__main__':
    if '--apply' in sys.argv:
        apply()
    else:
        preview()
