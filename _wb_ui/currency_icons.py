# -*- coding: utf-8 -*-
"""钻石 / 点券 / 金币 三类货币图标统一重制。

钻石：Pollinations 生成的紫水晶母图（anchors/cur_gem.png）抠底 + 卡通描边；
点券：程序化蓝钢圆牌 + 银白狼爪抓痕（替换掉原猫爪印）；
金币：沿用已重制的四芒星金币。

先 --preview 出对照图确认，再 --apply 写盘。
"""
import os
import shutil
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from vector_icons import coin_icon, outline, glow, _shade
from vector_icons import gem_icon as gicon

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ANCH = os.path.join(HERE, 'anchors')
LOOK = os.path.join(HERE, 'look')
BAK = os.path.join(HERE, 'backup_icons')

SS = 4


# ------------------------------------------------------------------ 抠图
def cut_gem(path, sat_thr=0.38):
    """抠掉淡紫灰摄影背景：按饱和度取前景 + 补洞 + 取最大连通域。"""
    im = Image.open(path).convert('RGB')
    hsv = np.asarray(im.convert('HSV')).astype(np.float32)
    sat = hsv[..., 1] / 255.0
    fg = sat > sat_thr
    try:
        from scipy import ndimage as ndi
        fg = ndi.binary_fill_holes(fg)
        fg = ndi.binary_opening(fg, np.ones((5, 5)))
        lab, n = ndi.label(fg)
        if n > 1:
            sizes = ndi.sum(fg, lab, range(1, n + 1))
            fg = lab == (int(np.argmax(sizes)) + 1)
        fg = ndi.binary_fill_holes(ndi.binary_closing(fg, np.ones((9, 9))))
    except ImportError:
        pass
    a = Image.fromarray((fg * 255).astype(np.uint8), 'L').filter(ImageFilter.GaussianBlur(1.1))
    out = im.convert('RGBA')
    out.putalpha(a)
    return out


def trim(im, pad_ratio=0.04):
    bb = im.getchannel('A').getbbox()
    if not bb:
        return im
    l, t, r, b = bb
    pad = int(max(r - l, b - t) * pad_ratio)
    canvas = Image.new('RGBA', (r - l + pad * 2, b - t + pad * 2), (0, 0, 0, 0))
    canvas.paste(im.crop((l, t, r, b)), (pad, pad))
    return canvas


_PAL = None


def ai_palette():
    """从 Pollinations 紫水晶母图里取主色：base / core / deep。"""
    global _PAL
    if _PAL is None:
        im = Image.open(os.path.join(ANCH, 'cur_gem.png')).convert('RGB')
        arr = np.asarray(im).astype(np.float32)
        hsv = np.asarray(im.convert('HSV')).astype(np.float32)
        sat = hsv[..., 1] / 255.0
        sel = arr[(sat > 0.55) & (hsv[..., 2] > 60)]
        if len(sel) < 100:
            _PAL = ((124, 66, 220), (222, 202, 255), (54, 24, 112))
        else:
            lum = sel.mean(axis=1)
            order = np.argsort(lum)
            sel = sel[order]

            def pick(p):
                return tuple(int(v) for v in sel[int(len(sel) * p)])

            base = pick(0.62)
            # 母图偏蓝，往紫水晶方向拉一点
            base = (min(255, int(base[0] * 1.46)), int(base[1] * 0.92), int(base[2] * 0.90))
            base = tuple(min(255, int(c * 1.16)) for c in base)
            core = tuple(min(255, int(c * 1.55 + 74)) for c in base)
            deep = tuple(int(c * 0.50) for c in base)
            _PAL = (base, core, deep)
    return _PAL


def sparkle(d, cx, cy, r, col=(255, 255, 255, 235)):
    sw = r * 0.20
    d.polygon([(cx, cy - r), (cx + sw, cy - sw), (cx + r, cy), (cx + sw, cy + sw),
               (cx, cy + r), (cx - sw, cy + sw), (cx - r, cy), (cx - sw, cy - sw)], fill=col)


def gem_icon(size):
    """紫水晶：取 Pollinations 母图的真实配色，用矢量切面重绘（小尺寸才清晰）。"""
    base, core, deep = ai_palette()
    return gicon(size, base=base, core=core, deep=deep,
                 outline_col=(32, 12, 62), glow_col=(152, 112, 255))


# ------------------------------------------------------------------ 点券
def _claw(d, cx, cy, R, off_x, length, wid, col):
    """一片爪痕：上宽下尖、微微弯曲的柳叶刀形。"""
    tilt = 0.34
    curve = 0.10
    pts_l, pts_r = [], []
    n = 18
    for i in range(n + 1):
        t = i / n
        y = cy - R * length * 0.5 + R * length * t
        w = wid * max(0.02, (1.0 - t) ** 0.62) * min(1.0, 0.55 + 3.2 * t)
        x = cx + off_x * R + (y - cy) * tilt + R * curve * np.sin(np.pi * t) * (1 if off_x >= 0 else -1)
        pts_l.append((x - w, y))
        pts_r.append((x + w, y))
    d.polygon(pts_l + pts_r[::-1], fill=col)


def token_icon(size, ring=(206, 218, 238), ring_dark=(98, 116, 148),
               core=(58, 96, 152), core_dark=(16, 30, 54),
               sigil=(240, 247, 255), edge=(14, 20, 34)):
    """蓝钢圆牌 + 铜环 + 狼爪抓痕。"""
    W, H = int(size[0] * SS), int(size[1] * SS)
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx, cy = W / 2, H / 2
    R = min(W, H) * 0.455

    # 铜环
    d.ellipse((cx - R, cy - R, cx + R, cy + R), fill=ring_dark + (255,))
    R2 = R * 0.94
    d.ellipse((cx - R2, cy - R2, cx + R2, cy + R2), fill=ring + (255,))
    # 环上齿纹
    for i in range(28):
        a = i * np.pi * 2 / 28
        d.line([(cx + np.cos(a) * R * 0.97, cy + np.sin(a) * R * 0.97),
                (cx + np.cos(a) * R * 0.90, cy + np.sin(a) * R * 0.90)],
               fill=_shade(ring_dark, 1.05) + (255,), width=max(1, int(R * 0.05)))
    # 内阶
    R3 = R * 0.80
    d.ellipse((cx - R3, cy - R3, cx + R3, cy + R3), fill=_shade(ring_dark, 0.82) + (255,))
    # 蓝钢币面
    R4 = R * 0.73
    d.ellipse((cx - R4, cy - R4, cx + R4, cy + R4), fill=core_dark + (255,))
    d.ellipse((cx - R4 * 0.97, cy - R4 * 0.99, cx + R4 * 0.97, cy + R4 * 0.88),
              fill=core + (255,))

    # 爪痕
    sig = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sig)
    for off, ln, wd in ((-0.28, 0.66, 0.085), (0.0, 0.80, 0.095), (0.28, 0.66, 0.085)):
        _claw(sd, cx, cy + R * 0.02, R, off, ln, R * wd, sigil + (255,))
    sig = outline(sig, (14, 22, 36, 255), width=max(1, int(R * 0.022)))
    # 只保留币面范围内的爪痕
    mask = Image.new('L', (W, H), 0)
    ImageDraw.Draw(mask).ellipse((cx - R4 * 0.96, cy - R4 * 0.96, cx + R4 * 0.96, cy + R4 * 0.96),
                                 fill=255)
    sig.putalpha(Image.composite(sig.getchannel('A'), Image.new('L', (W, H), 0), mask))
    im.alpha_composite(sig)

    # 斜向高光
    hl = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    hd = ImageDraw.Draw(hl)
    hd.polygon([(cx - R * 1.10, cy + R * 0.15), (cx - R * 0.50, cy - R * 1.10),
                (cx - R * 0.05, cy - R * 1.10), (cx - R * 0.62, cy + R * 0.15)],
               fill=(255, 255, 255, 92))
    hl = hl.filter(ImageFilter.GaussianBlur(R * 0.09))
    m = Image.new('L', (W, H), 0)
    ImageDraw.Draw(m).ellipse((cx - R4, cy - R4, cx + R4, cy + R4), fill=255)
    hl.putalpha(Image.composite(hl.getchannel('A'), Image.new('L', (W, H), 0), m))
    im.alpha_composite(hl)

    im = outline(im, edge + (255,), width=max(1, int(R * 0.035)), blur=0.6)
    im = glow(im, (120, 172, 240), 0.22, max(2, int(W * 0.03)))
    return im.resize(size, Image.LANCZOS)


# ------------------------------------------------------------------ 清单
GEM_FILES = [
    'Assets/Merge Beast/Image/UI Boost/iconGemSmall.png',
    'Assets/Merge Beast/Image/UI Main/iconGemUnlock.png',
    'Assets/Merge Beast/Image/UI Upgrade/iconGem.png',
    'Assets/Merge Beast/Image/FreeBoost/gem.png',
    'Assets/Merge Beast/Image/UI Game/currencyGem.png',
    'Assets/1_FX_AutoBeast/Image/gem.png',
]

TOKEN_FILES = [
    'Assets/Merge Beast/Image/UI Game/icon_CommonCur.png',
    'Assets/Merge Beast/Image/FreeBoost/common_icon_dianquan.png',
    'Assets/Merge Beast/Image/FreeBoost/shop_img_dianquan1.png',
    'Assets/1_FX_AutoBeast/Image/coin.png',
]

COIN_FILES = [
    'Assets/1_FX_AutoBeast/Image/gold_coin.png',
    'Assets/Merge Beast/Image/UI Game/currencyGold.png',
]

GEM_SRC_FILES = [
    'Assets/Merge Beast/Image/UI Game/currencyGem.png',
]


def build(kind, size):
    if kind == 'gem':
        return gem_icon(size)
    if kind == 'token':
        return token_icon(size)
    return coin_icon(size)


def render(kind, path):
    rel = path
    p = os.path.join(ROOT, rel)
    old = Image.open(p)
    return p, build(kind, old.size), old.size, old.mode


def save_like(path, im):
    old = Image.open(path)
    fmt, mode, size = old.format, old.mode, old.size
    out = im if im.size == size else im.resize(size, Image.LANCZOS)
    if fmt == 'JPEG':
        out = out.convert('RGB')
    elif mode == 'P':
        out = out.convert('RGBA')
    elif mode == 'RGB':
        out = out.convert('RGB')
    elif mode == 'L':
        out = out.convert('L')
    rel = os.path.relpath(path, os.path.join(ROOT, 'Assets'))
    dst = os.path.join(BAK, rel)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if not os.path.exists(dst):
        shutil.copy2(path, dst)
    out.save(path, fmt or 'PNG', optimize=True)
    chk = Image.open(path)
    return chk.size, chk.mode


def preview():
    rows = []
    for kind, files in (('gem', GEM_FILES), ('token', TOKEN_FILES), ('coin', COIN_FILES)):
        for f in files:
            rows.append((kind, f))
    cell = 200
    sheet = Image.new('RGBA', (cell * len(rows), cell * 2 + 26), (26, 46, 40, 255))
    d = ImageDraw.Draw(sheet)
    for i, (kind, f) in enumerate(rows):
        p, new, size, mode = render(kind, f)
        old = Image.open(p).convert('RGBA')
        for j, im in enumerate((old, new)):
            k = min((cell - 24) / max(im.size), 3.0)
            show = im.resize((max(1, int(im.width * k)), max(1, int(im.height * k))), Image.LANCZOS)
            x = i * cell + (cell - show.width) // 2
            y = j * cell + (cell - show.height) // 2
            sheet.alpha_composite(show, (x, y))
        d.text((i * cell + 6, 4), os.path.basename(f)[:18], fill=(200, 230, 220, 255))
        d.text((i * cell + 6, cell * 2 + 8), '%dx%d' % size, fill=(160, 200, 190, 255))
    out = os.path.join(LOOK, 'cur_after.png')
    sheet.convert('RGB').save(out, quality=94)
    print(out)


def apply():
    n = 0
    for kind, files in (('gem', GEM_FILES), ('token', TOKEN_FILES), ('coin', COIN_FILES)):
        for f in files:
            p, new, size, mode = render(kind, f)
            s2, m2 = save_like(p, new)
            ok = (s2 == size and m2 == mode)
            print('%-6s %-58s %s -> %s %s' % (kind, os.path.basename(f), '%dx%d/%s' % (size[0], size[1], mode),
                                              '%dx%d/%s' % (s2[0], s2[1], m2), 'OK' if ok else 'FAIL'))
            n += 1
    print('done', n)


if __name__ == '__main__':
    if '--apply' in sys.argv:
        apply()
    else:
        preview()
