# -*- coding: utf-8 -*-
"""把 AI 图标母件抠底、缩放、合成进原有 UI 贴图（尺寸/模式/.meta 一律不变）。"""
import os
import shutil
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
IMG = os.path.join(ROOT, 'Assets', 'Merge Beast', 'Image')
ANCH = os.path.join(HERE, 'anchors')
BAK = os.path.join(HERE, 'backup_icons')


# ---------------------------------------------------------------- 抠图
def cut_black(im, tol=46, feather=1.4):
    """从四角 flood fill 去掉纯黑背景，返回 RGBA。"""
    im = im.convert('RGB')
    w, h = im.size
    marker = (255, 0, 255)
    work = im.copy()
    px = work.load()
    for seed in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1), (w // 2, h - 1)):
        try:
            if sum(px[seed][:3]) < tol * 3:
                ImageDraw.floodfill(work, seed, marker, thresh=tol)
        except Exception:
            pass
    arr = np.asarray(work).astype(np.int16)
    is_bg = (np.abs(arr[..., 0] - 255) < 6) & (arr[..., 1] < 6) & (np.abs(arr[..., 2] - 255) < 6)
    alpha = np.where(is_bg, 0, 255).astype(np.uint8)
    a_im = Image.fromarray(alpha, 'L')
    if feather > 0:
        a_im = a_im.filter(ImageFilter.MinFilter(3)).filter(
            ImageFilter.GaussianBlur(feather))
    out = im.convert('RGBA')
    out.putalpha(a_im)
    return out


def fit_square(im):
    """裁到不透明内容的外接正方形。"""
    bb = im.getchannel('A').getbbox()
    if not bb:
        return im
    l, t, r, b = bb
    cx, cy = (l + r) // 2, (t + b) // 2
    side = max(r - l, b - t)
    pad = int(side * 0.06)
    side += pad * 2
    box = (cx - side // 2, cy - side // 2, cx - side // 2 + side, cy - side // 2 + side)
    canvas = Image.new('RGBA', (side, side), (0, 0, 0, 0))
    canvas.paste(im.crop((max(0, box[0]), max(0, box[1]),
                          min(im.width, box[2]), min(im.height, box[3]))),
                 (max(0, -box[0]), max(0, -box[1])))
    return canvas


def trim_edges(im, pad_ratio=0.03):
    """去掉四周多余透明边，留一点内边距。"""
    bb = im.getchannel('A').getbbox()
    if not bb:
        return im
    l, t, r, b = bb
    pad = int(max(r - l, b - t) * pad_ratio)
    canvas = Image.new('RGBA', (r - l + pad * 2, b - t + pad * 2), (0, 0, 0, 0))
    canvas.paste(im.crop((l, t, r, b)), (pad, pad))
    return canvas


def split_row(im, n=3, thr=8):
    """横排图标按透明间隙切成 n 份。"""
    a = np.asarray(im.getchannel('A'))
    cols = (a > thr).any(axis=0)
    runs, start = [], None
    for i, v in enumerate(cols):
        if v and start is None:
            start = i
        elif not v and start is not None:
            runs.append((start, i))
            start = None
    if start is not None:
        runs.append((start, len(cols)))
    runs = [r for r in runs if r[1] - r[0] > im.width * 0.06]
    if len(runs) != n:
        # 退化为等分
        step = im.width // n
        runs = [(i * step, (i + 1) * step) for i in range(n)]
    out = []
    for l, r in runs:
        sub = im.crop((l, 0, r, im.height))
        out.append(fit_square(sub))
    return out


# ---------------------------------------------------------------- 合成
def place_center(dst, icon, cx, cy, size, glow=None):
    """把 icon 等比缩放到 size 后居中贴到 dst。"""
    ic = icon.copy()
    ic.thumbnail((size, size), Image.LANCZOS)
    if glow:
        pad = glow * 3
        base = Image.new('RGBA', (ic.width + pad * 2, ic.height + pad * 2), (0, 0, 0, 0))
        base.alpha_composite(ic, (pad, pad))
        a = base.getchannel('A').filter(ImageFilter.GaussianBlur(glow))
        halo = Image.new('RGBA', base.size, (255, 214, 140, 255))
        halo.putalpha(a.point(lambda v: int(v * 0.40)))
        ic = Image.alpha_composite(halo, base)
    dst.alpha_composite(ic, (int(cx - ic.width / 2), int(cy - ic.height / 2)))


def plate(size, src):
    """AI 底板缩放到目标尺寸。"""
    p = src.resize(size, Image.LANCZOS)
    return p


def mask_with_alpha(plate_img, ref_alpha):
    """用原图的 alpha 轮廓约束新底板，保持圆角/八角外形。"""
    a = ref_alpha.filter(ImageFilter.GaussianBlur(0.6))
    out = plate_img.convert('RGBA')
    out.putalpha(a)
    return out


def load_alpha(path):
    return Image.open(path).convert('RGBA').getchannel('A')


def backup(path):
    rel = os.path.relpath(path, os.path.join(ROOT, 'Assets'))
    dst = os.path.join(BAK, rel)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if not os.path.exists(dst):
        shutil.copy2(path, dst)
    return dst


def save_like(path, im):
    """按原文件的模式与格式写回，保持尺寸。"""
    old = Image.open(path)
    fmt, mode, size = old.format, old.mode, old.size
    out = im
    if out.size != size:
        out = out.resize(size, Image.LANCZOS)
    if fmt == 'JPEG':
        out = out.convert('RGB')
    elif mode == 'P':
        out = out.convert('RGBA')
    elif mode in ('RGB', 'L'):
        out = out.convert(mode) if mode == 'L' else out.convert('RGB')
    backup(path)
    out.save(path, fmt or 'PNG', optimize=True)
    return Image.open(path).size, Image.open(path).mode


def arrow_up(w, h, col=(250, 206, 108), dark=(84, 50, 10), light=(255, 246, 206)):
    """程序化画一个粗壮向上箭头（升级）。"""
    ss = 4
    W, H = w * ss, h * ss
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx = W // 2
    top = int(H * 0.10)
    head_h = int(H * 0.42)
    shaft_w = int(W * 0.26)
    head_w = int(W * 0.44)
    pts = [
        (cx, top), (cx + head_w // 2, top + head_h), (cx + shaft_w // 2, top + head_h),
        (cx + shaft_w // 2, H - int(H * 0.12)), (cx - shaft_w // 2, H - int(H * 0.12)),
        (cx - shaft_w // 2, top + head_h), (cx - head_w // 2, top + head_h),
    ]
    d.polygon(pts, fill=col + (255,))
    im = im.resize((w, h), Image.LANCZOS)
    # 描边 + 顶部高光
    a = im.getchannel('A')
    edge = Image.new('RGBA', (w, h), dark + (255,))
    edge.putalpha(a.filter(ImageFilter.MaxFilter(5)))
    out = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    out.alpha_composite(edge)
    out.alpha_composite(im)
    grad = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grad)
    gd.ellipse((-w * 0.2, -h * 0.55, w * 1.2, h * 0.55), fill=light + (70,))
    grad.putalpha(Image.composite(grad.getchannel('A'), Image.new('L', (w, h), 0), a))
    out.alpha_composite(grad)
    return out
