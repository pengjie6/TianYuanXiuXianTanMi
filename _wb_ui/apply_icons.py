# -*- coding: utf-8 -*-
"""把新图标/新底板写回原有 UI 贴图，尺寸与格式严格保持不变。"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import iconize as IZ

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
IMG = os.path.join(ROOT, 'Assets', 'Merge Beast', 'Image')
ANCH = os.path.join(HERE, 'anchors')
OUT = os.path.join(HERE, 'preview2')
os.makedirs(OUT, exist_ok=True)

SS = 4  # 超采样倍数


# ------------------------------------------------------------ 程序化底板
def _round_mask(size, radius, ss=SS):
    w, h = size
    m = Image.new('L', (w * ss, h * ss), 0)
    d = ImageDraw.Draw(m)
    d.rounded_rectangle((0, 0, w * ss - 1, h * ss - 1), radius=radius * ss, fill=255)
    return m.resize((w, h), Image.LANCZOS)


def _vgrad(size, top, bottom):
    w, h = size
    ramp = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
    a = np.array(top, dtype=np.float32)[None, None, :]
    b = np.array(bottom, dtype=np.float32)[None, None, :]
    arr = a * (1 - ramp) + b * ramp
    arr = np.repeat(arr, w, axis=1)
    return Image.fromarray(arr.astype(np.uint8), 'RGB')


def stone_patch(size):
    """取 AI 石图里一小块纯石面（单次覆盖，不平铺），缩放后加轻微镜像去重复感。"""
    src = Image.open(os.path.join(ANCH, 'tex_stone.png')).convert('RGB')
    w, h = src.size
    box = (int(w * 0.07), int(h * 0.03), int(w * 0.29), int(h * 0.20))
    tile = src.crop(box).resize((max(64, size[0] * 2), max(64, size[1] * 2)), Image.LANCZOS)
    tile = tile.transpose(Image.FLIP_LEFT_RIGHT)
    return tile.resize((size[0], size[1]), Image.LANCZOS)


def make_plate(size, tone='jade', radius_ratio=0.20, border=True):
    """深绿苔石 / 古金 按钮底板 + 描边 + 高光。"""
    w, h = size
    radius = int(min(w, h) * radius_ratio)

    if tone == 'jade':
        top, bot = (96, 168, 128), (20, 56, 44)
        edge_hi, edge_lo = (255, 240, 196), (182, 138, 62)
        tex_k, shade_k = 0.40, 0.30
    elif tone == 'gold':
        top, bot = (255, 236, 128), (238, 148, 30)
        edge_hi, edge_lo = (255, 214, 120), (176, 62, 8)
        tex_k, shade_k = 0.10, 0.10
    elif tone == 'violet':
        top, bot = (168, 122, 208), (66, 38, 96)
        edge_hi, edge_lo = (242, 220, 255), (156, 112, 196)
        tex_k, shade_k = 0.26, 0.24
    else:  # dark
        top, bot = (54, 70, 62), (18, 28, 24)
        edge_hi, edge_lo = (200, 196, 178), (98, 94, 80)
        tex_k, shade_k = 0.45, 0.34

    base = _vgrad(size, top, bot)

    # 石头纹理：低频石面 + 高频颗粒
    tex = stone_patch(size).convert('L')
    tex = tex.filter(ImageFilter.GaussianBlur(max(0.4, min(w, h) * 0.006)))
    tl = np.asarray(tex, dtype=np.float32) / 255.0
    tl = 1.0 + (tl - tl.mean()) * (0.42 * tex_k / 0.40)          # 压到接近 1 的乘性系数
    tl = np.clip(tl, 0.55, 1.35)[..., None]
    arr = np.asarray(base, dtype=np.float32) * tl
    rng = np.random.default_rng(7)
    grain = rng.normal(0, 3.4, (h, w, 1))
    arr = np.clip(arr + grain, 0, 255).astype(np.uint8)
    base = Image.fromarray(arr, 'RGB')

    mask = _round_mask(size, radius)

    # 内凹阴影（下沿重、上沿轻）
    shade = Image.new('L', (w, h), 0)
    sd = ImageDraw.Draw(shade)
    sd.rounded_rectangle((int(w * 0.03), int(h * 0.10), int(w * 0.97), int(h * 1.06)),
                         radius=int(radius * 0.9), fill=255)
    shade = shade.filter(ImageFilter.GaussianBlur(max(1.2, h * 0.05)))
    base = Image.composite(Image.blend(base, Image.new('RGB', (w, h), (0, 0, 0)), shade_k),
                           base, shade)

    # 顶部高光带
    gloss = Image.new('L', (w, h), 0)
    ImageDraw.Draw(gloss).rounded_rectangle(
        (int(w * 0.035), int(h * 0.045), int(w * 0.965), int(h * 0.46)),
        radius=max(2, radius - int(h * 0.03)), fill=255)
    gloss = gloss.filter(ImageFilter.GaussianBlur(max(1.5, h * 0.055)))
    base = Image.composite(Image.new('RGB', (w, h), (255, 255, 255)), base,
                           gloss.point(lambda v: int(v * 0.34)))

    out = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    out.paste(base, (0, 0), mask)

    if border:
        bw = max(2, int(min(w, h) * 0.052))
        ring = Image.new('L', (w, h), 0)
        ImageDraw.Draw(ring).rounded_rectangle(
            (1, 1, w - 2, h - 2), radius=radius, outline=255, width=bw)
        ring = ring.filter(ImageFilter.GaussianBlur(0.5))
        g = _vgrad(size, edge_hi, edge_lo).convert('RGB').convert('RGBA')
        g.putalpha(ring)
        out.alpha_composite(g)

        # 描边内侧暗线
        ring2 = Image.new('L', (w, h), 0)
        ImageDraw.Draw(ring2).rounded_rectangle(
            (bw + 1, bw + 1, w - 2 - bw, h - 2 - bw),
            radius=max(2, radius - bw), outline=255, width=1)
        dark = Image.new('RGBA', (w, h), (8, 14, 10, 255))
        dark.putalpha(ring2.point(lambda v: int(v * 0.62)))
        out.alpha_composite(dark)

        # 底沿反光
        rim = Image.new('L', (w, h), 0)
        ImageDraw.Draw(rim).rounded_rectangle(
            (bw + 2, h - bw - 4, w - 2 - bw, h - 2 - bw),
            radius=max(2, radius - bw), fill=255)
        rim = rim.filter(ImageFilter.GaussianBlur(1.4))
        hi = Image.new('RGBA', (w, h), edge_hi + (255,))
        hi.putalpha(rim.point(lambda v: int(v * 0.22)))
        out.alpha_composite(hi)

    return out


def shadow(im, blur=6, alpha=110, dy=2):
    a = im.getchannel('A').filter(ImageFilter.GaussianBlur(blur))
    sh = Image.new('RGBA', im.size, (0, 0, 0, 0))
    sh.putalpha(a.point(lambda v: int(v * alpha / 255)))
    canvas = Image.new('RGBA', (im.width + 8, im.height + 8), (0, 0, 0, 0))
    canvas.alpha_composite(sh, (4, 4 + dy))
    canvas.alpha_composite(im, (4, 4))
    return canvas


# ------------------------------------------------------------ 图标装配
def load_icon(name, cut=True):
    p = os.path.join(ANCH, name)
    im = Image.open(p)
    im = im.convert('RGB') if im.mode != 'RGBA' else im
    if cut:
        im = IZ.cut_black(im.convert('RGB'))
        im = IZ.trim_edges(im, 0.02)
    return im


def compose_icon(path, plate_tone, icon, icon_scale=0.56, glow=None, radius_ratio=0.20,
                 edge_margin=0.02):
    w, h = Image.open(path).size
    canvas = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    base = make_plate((w, h), plate_tone, radius_ratio)
    canvas.alpha_composite(base)
    if icon is not None:
        IZ.place_center(canvas, icon, w / 2, h / 2 + h * 0.01, int(min(w, h) * icon_scale), glow)
    return canvas


def pure_icon(path, icon, scale=0.96, glow=6):
    """替换整张 PNG 为一个居中图标（金币、宝石类）。"""
    w, h = Image.open(path).size
    canvas = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    IZ.place_center(canvas, icon, w / 2, h / 2, int(min(w, h) * scale), glow)
    return canvas


def round_chip(path, icon, tone='gold'):
    """圆形底 + 图标（加号按钮用）。"""
    w, h = Image.open(path).size
    canvas = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(canvas)
    d.ellipse((1, 1, w - 2, h - 2), fill=(0, 0, 0, 0))
    base = make_plate((w, h), tone, radius_ratio=0.5)
    canvas.alpha_composite(base)
    IZ.place_center(canvas, icon, w / 2, h / 2, int(min(w, h) * 0.62))
    return canvas
