# -*- coding: utf-8 -*-
"""把 Beast_SpriteSheet 里黄色/橙色的按钮底板换成墨绿苔石色。

思路：不做色相旋转（会把高光、描边、图标一起搞脏），
而是按**亮度梯度重映射**成一条墨绿→青白的色带：
形状、明暗结构、alpha 全部原样保留，只是材质从"黄金/琥珀"变成"苔石/玉"。
只改目标切片的 rect 内像素，越界 = 0。
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from beast_sheet import blur_f, crop, diffuse_fill, dilate, load_sheet  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SHEET = os.path.join(ROOT, 'Assets', 'Merge Beast', 'Image', 'SpriteSheet', 'Beast_SpriteSheet.png')
BAK = os.path.join(HERE, 'backup_beast', 'Beast_SpriteSheet.png')
LOOK = os.path.join(HERE, 'look')

# 圆角牌/长条类的按钮底板（图标类 #2 #7 #43 #45 不动）
TARGETS = [11, 24, 104, 121, 122, 125]

# 亮度 -> 颜色 的色带（苔石绿）。输入用感知亮度 L 而不是 HSV 的 V，
# 否则金色（max 通道≈1）会被直接打到最亮档，整块发白成薄荷糖。
# 暗段压得比中间调低很多，否则深棕图标换成深绿后会和底板糊在一起。
STOP_L = [0.00, 0.14, 0.26, 0.40, 0.55, 0.70, 0.82, 0.92, 1.00]
STOP_C = [(4, 12, 10), (8, 24, 20), (12, 38, 31), (20, 58, 47), (32, 84, 68),
          (48, 110, 88), (76, 146, 118), (120, 188, 158), (200, 236, 218)]


def ramp(l):
    out = np.zeros(l.shape + (3,), np.float32)
    for i in range(3):
        out[..., i] = np.interp(l, STOP_L, [c[i] for c in STOP_C])
    return out


def jadeify(rgba):
    """暖色（黄/橙/棕）像素按亮度换成苔石绿，冷色/品红/绿原样保留。"""
    a = np.asarray(rgba).astype(np.float32) / 255.0
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    mx = a[..., :3].max(axis=2)
    L = 0.299 * r + 0.587 * g + 0.114 * b
    warm = np.clip((r - b) / np.maximum(r, 1e-4), 0.0, 1.0)
    # 黄/橙/棕 的 warmness 都 >0.5；粉(#67)、品红(#112)、蓝(#45)、绿(#25) 都在 0.3 以下
    w = np.clip((warm - 0.26) / 0.16, 0.0, 1.0)
    # 高光（近白）单独往青白拉一点，否则金黄高光留在绿底上会发脏
    w_hi = np.clip((mx - 0.93) / 0.07, 0.0, 1.0) * 0.85
    w = np.maximum(w, w_hi)

    tgt = ramp(L) * 0.96
    # 极暗的描边再压一点，保住轮廓的体积感
    tgt = np.where((L < 0.14)[..., None], tgt * 0.78, tgt)
    out = a[..., :3] * (1 - w[..., None]) + tgt / 255.0 * w[..., None]
    res = np.concatenate([np.clip(out, 0, 1) * 255.0, a[..., 3:4] * 255.0], axis=2)
    return Image.fromarray(res.round().astype(np.uint8), 'RGBA')


# ---------------------------------------------------------------- #121 专属修复
def fix121(im, box):
    """#121 = btnUpgrade：原图是"金底 + 深棕猫头"，上一轮把猫头抹成了灰块。
    这里从备份贴回整块，抹平猫头，再在中央画一个金色上箭头。"""
    x, y, w, h = box
    alpha_keep = np.asarray(im.crop((x, y, x + w, y + h)))[..., 3].copy()
    block = crop(Image.open(BAK).convert('RGBA'), box)
    a = np.asarray(block).astype(np.float32)
    rgb = a[..., :3]
    V = rgb.max(axis=2) / 255.0
    warm = (rgb[..., 0] - rgb[..., 2]) / np.maximum(rgb[..., 0], 1.0)

    yy, xx = np.mgrid[0:h, 0:w]
    # 只取中心区域，避开外圈描边
    inner = ((xx > w * 0.10) & (xx < w * 0.90) & (yy > h * 0.02) & (yy < h * 0.98))
    head = inner & (V < 0.56) & (warm > 0.45)
    head = dilate(head, 2)
    head &= inner  # 膨胀后仍不许越出中心区

    filled = diffuse_fill(rgb, head, iters=120, sigma=1.8)
    block = Image.fromarray(np.concatenate([filled, a[..., 3:4]], axis=2).astype(np.uint8), 'RGBA')
    im.paste(block, (x, y))

    # 换色后再画箭头
    patch = jadeify(im.crop((x, y, x + w, y + h)))
    d = ImageDraw.Draw(patch)
    cx, cy = w / 2.0, h / 2.0
    aw = w * 0.115                        # 箭杆宽
    hw, hh = w * 0.255, h * 0.235         # 箭头宽 / 高
    gold = (250, 206, 96, 255)
    gold_d = (188, 132, 36, 255)
    top = cy - h * 0.42
    bot = cy + h * 0.40
    d.polygon([(cx, top), (cx + hw, top + hh), (cx - hw, top + hh)], fill=gold)
    d.rectangle((cx - aw / 2, top + hh * 0.9, cx + aw / 2, bot), fill=gold)
    # 描边
    d.line([(cx, top), (cx + hw, top + hh)], fill=gold_d, width=max(2, int(w * 0.014)))
    d.line([(cx, top), (cx - hw, top + hh)], fill=gold_d, width=max(2, int(w * 0.014)))
    d.line([(cx - aw / 2, top + hh * 0.9), (cx - aw / 2, bot)], fill=gold_d, width=max(2, int(w * 0.012)))
    d.line([(cx + aw / 2, top + hh * 0.9), (cx + aw / 2, bot)], fill=gold_d, width=max(2, int(w * 0.012)))
    d.line([(cx - aw / 2, bot), (cx + aw / 2, bot)], fill=gold_d, width=max(2, int(w * 0.012)))
    arr = np.asarray(patch).copy()
    arr[..., 3] = alpha_keep
    im.paste(Image.fromarray(arr, 'RGBA'), (x, y))


def build(im, rects):
    for idx in TARGETS:
        name = 'Beast_SpriteSheet_%d' % idx
        box = rects[name]
        if idx == 121:
            fix121(im, box)
            continue
        x, y, w, h = box
        im.paste(jadeify(im.crop((x, y, x + w, y + h))), (x, y))
    return im


def preview(im, rects):
    cell = 200
    cols = len(TARGETS)
    sheet = Image.new('RGBA', (cell * cols, cell * 2), (20, 40, 34, 255))
    d = ImageDraw.Draw(sheet)
    for i, idx in enumerate(TARGETS):
        name = 'Beast_SpriteSheet_%d' % idx
        x, y, w, h = rects[name]
        old = crop(Image.open(SHEET).convert('RGBA'), (x, y, w, h))
        new = im.crop((x, y, x + w, y + h))
        for j, c in enumerate((old, new)):
            k = min((cell - 26) / max(c.size), 3.0)
            s = c.resize((max(1, int(c.width * k)), max(1, int(c.height * k))), Image.LANCZOS)
            sheet.alpha_composite(s, (i * cell + (cell - s.width) // 2, j * cell + (cell - s.height) // 2))
        d.text((i * cell + 6, 4), '#%d' % idx, fill=(255, 230, 120, 255))
    out = os.path.join(LOOK, 'jade_buttons.png')
    sheet.convert('RGB').save(out, quality=95)
    print(out)


if __name__ == '__main__':
    base, rects = load_sheet()
    im = Image.open(SHEET).convert('RGBA') if os.path.exists(SHEET) else base.copy()
    before = np.asarray(im).copy()
    build(im, dict((n, (x, y, w, h)) for n, x, y, w, h in rects))
    after = np.asarray(im)
    diff = (np.abs(after.astype(np.int16) - before.astype(np.int16)).sum(axis=2) > 0)
    print('changed px %d / alpha changed %d' % (diff.sum(), (after[..., 3] != before[..., 3]).sum()))
    if '--apply' in sys.argv:
        im.save(SHEET)
        print('saved', SHEET, im.size, im.mode)
    else:
        preview(im, dict((n, (x, y, w, h)) for n, x, y, w, h in rects))
