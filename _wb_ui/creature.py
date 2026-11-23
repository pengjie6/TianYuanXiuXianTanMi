# -*- coding: utf-8 -*-
"""把 Spine 角色图集从「猫」改造成「狼 / 熊 / 狐」等非猫物种。

为什么整页处理而不是逐区域：
  图集头里的 size 与 PNG 实际尺寸经常不一致（页面被放大成 2 的幂），
  region 矩形只能近似对应像素，逐区域回填会留下米黄色接缝。
  所以这里完全按像素判断：色相落在暖棕区间或接近中性色的像素 = 毛皮。

处理链：
  1. 乘性着色：保留原画明暗结构，只把毛色映射到目标物种
  2. 毛皮纹理：叠加 Pollinations 生成的毛皮高频细节（幅度很低，只带毛流感）
  3. 轮廓绒毛：沿毛皮区 alpha 边缘做噪声扩张，剪影从光滑猫形变毛茸茸
"""
import os, sys, shutil
import numpy as np
from PIL import Image, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spine_atlas as sa

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = os.path.join(ROOT, '_wb_ui')
ANCH = os.path.join(WORK, 'anchors')
BAK = os.path.join(WORK, 'backup_spine')

SPECIES = {
    'wolf': dict(base=(0.605, 0.620, 0.660), ref=0.86, tex='grain_wolf',
                 grain=0.07, fluff=1.30, sat=0.62, shadow=(0.97, 0.99, 1.03)),
    'bear': dict(base=(0.545, 0.385, 0.255), ref=0.86, tex='grain_bear',
                 grain=0.07, fluff=1.45, sat=0.64, shadow=(1.02, 0.96, 0.90)),
    'fox': dict(base=(0.790, 0.435, 0.205), ref=0.86, tex='grain_fox',
                grain=0.07, fluff=1.35, sat=0.64, shadow=(1.04, 0.94, 0.86)),
    'boar': dict(base=(0.440, 0.420, 0.400), ref=0.86, tex='grain_wolf',
                 grain=0.12, fluff=1.55, sat=0.62, shadow=(1.0, 1.0, 1.0)),
    'deer': dict(base=(0.660, 0.505, 0.345), ref=0.86, tex='grain_bear',
                 grain=0.10, fluff=1.20, sat=0.64, shadow=(1.0, 0.98, 0.94)),
}

_TEX_CACHE = {}


def load_tex(name):
    p = os.path.join(ANCH, name + '.png')
    return Image.open(p).convert('L') if os.path.exists(p) else None


def grain_map(name, size, blur_div=34.0):
    w, h = size
    key = (name, w, h)
    if key in _TEX_CACHE:
        return _TEX_CACHE[key]
    im = load_tex(name)
    if im is None:
        _TEX_CACHE[key] = None
        return None
    tw, th = im.size
    reps_x = int(np.ceil(w / float(tw)))
    reps_y = int(np.ceil(h / float(th)))
    big = Image.new('L', (tw * reps_x, th * reps_y))
    for iy in range(reps_y):
        for ix in range(reps_x):
            big.paste(im, (ix * tw, iy * th))
    big = big.crop((0, 0, w, h))
    a = np.asarray(big, dtype=np.float32) / 255.0
    med = np.asarray(big.filter(ImageFilter.GaussianBlur(max(1.5, min(w, h) / blur_div))),
                     dtype=np.float32) / 255.0
    a = a - med
    a = np.clip(a / (float(a.std()) or 1e-5), -1.5, 1.5)
    _TEX_CACHE[key] = a
    return a


def fur_mask_of(rgb, alpha, sat_limit):
    mx = rgb.max(axis=-1)
    mn = rgb.min(axis=-1)
    sat = (mx - mn) / np.maximum(mx, 1e-4)
    lum = 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]

    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    d = mx - mn
    hue = np.zeros_like(mx)
    nz = d > 1e-4
    # 只关心是否落在暖色（橙/棕/黄）区间，简化算法即可
    with np.errstate(invalid='ignore', divide='ignore'):
        hr = ((g - b) / np.where(nz, d, 1)) % 6.0
        hg = (b - r) / np.where(nz, d, 1) + 2.0
        hb = (r - g) / np.where(nz, d, 1) + 4.0
    hue = np.where(mx == r, hr, np.where(mx == g, hg, hb)) * 60.0

    opaque = alpha > 0.06
    warm = (hue >= 14) & (hue <= 62) & (sat < sat_limit) & (sat > 0.02)
    # 中性色只认「暖白/米白」(R>=B)，避免把蓝白史莱姆、冷色道具一起染掉
    neutral = (sat <= 0.18) & (r >= b - 0.015) & (lum > 0.10)
    fur = (warm | neutral) & opaque & (lum > 0.10)
    return fur, sat, lum


def transform_page(page, species, fluff_scale=1.0):
    """整页重绘（不依赖 region 几何），返回新的 RGBA 页。"""
    spec = SPECIES[species]
    w, h = page.size
    arr = np.asarray(page, dtype=np.float32)
    rgb = arr[..., :3] / 255.0
    alpha = arr[..., 3] / 255.0
    if alpha.max() < 0.05:
        return page

    fur, sat, lum = fur_mask_of(rgb, alpha, spec['sat'])
    if fur.sum() < 64:
        return page

    base = np.array(spec['base'], dtype=np.float32)
    shadow = np.array(spec['shadow'], dtype=np.float32)
    # 以本页毛皮的中位亮度为参考，保证深棕毛也能映射到目标中调色
    ref = float(np.median(lum[fur])) if fur.sum() > 0 else spec['ref']
    ref = min(max(ref, 0.06), 0.95)
    # 阻尼：深色毛（黑猫）只提亮一部分，保留各阶级之间的明暗差异
    ref = (ref ** 0.55) * (spec['ref'] ** 0.45)
    ref = min(max(ref, 0.22), 0.95)
    ratio = np.clip(lum / ref, 0.42, 1.42)

    # 乘性着色 + 高光提白 + 阴影轻微偏色（狼偏冷 / 熊偏暖）
    new_rgb = base[None, None, :] * ratio[..., None] * shadow[None, None, :]
    hi = np.clip((lum - 0.84) / 0.18, 0, 1)[..., None]
    hl = np.clip(base * 1.45 + 0.20, 0, 1)[None, None, :]
    new_rgb = new_rgb * (1 - hi) + hl * hi
    new_rgb = np.clip(new_rgb, 0, 1)

    fm = fur.astype(np.float32)
    fm = np.asarray(Image.fromarray((fm * 255).astype(np.uint8)).filter(
        ImageFilter.GaussianBlur(1.1)), dtype=np.float32) / 255.0
    fm = np.clip(fm, 0, 1)[..., None]

    out = rgb * (1 - fm) + new_rgb * fm

    g = grain_map(spec['tex'], (w, h))
    if g is not None:
        strength = spec['grain'] * fm * (alpha[..., None] ** 0.5)
        out = np.clip(out * (1.0 + g[..., None] * strength), 0, 1)

    res = np.dstack([out * 255.0, alpha * 255.0]).astype(np.uint8)
    im = Image.fromarray(res, 'RGBA')

    # 绒毛只作用在毛皮区
    zone = np.asarray(Image.fromarray((fur.astype(np.uint8) * 255), 'L').filter(
        ImageFilter.MaxFilter(5)), dtype=np.uint8) > 127
    im = _fluff(im, zone, spec['fluff'] * fluff_scale)
    return im


def _fluff(im, zone, amount):
    w, h = im.size
    A = im.getchannel('A')
    a = np.asarray(A, dtype=np.float32) / 255.0
    d1 = np.asarray(A.filter(ImageFilter.MaxFilter(7)), dtype=np.float32) / 255.0
    rim = np.clip(d1 - a, 0, 1) * zone
    if rim.sum() < 4:
        return im
    rng = np.random.default_rng(97531 + w * 13 + h * 7)
    noise = rng.random((max(2, h // 2), max(2, w // 2))).astype(np.float32)
    noise = np.asarray(Image.fromarray((noise * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC),
                       dtype=np.float32) / 255.0
    add = rim * np.clip((noise - 0.28) / 0.72, 0, 1) * amount
    a2 = np.clip(a + add, 0, 1)
    out = im.copy()
    out.putalpha(Image.fromarray((a2 * 255).astype(np.uint8), 'L'))
    return out


def process_atlas(atlas_txt, species, apply=False, verbose=False, fluff_scale=1.0,
                  cov_range=(0.02, 0.995)):
    pages, _ = sa.parse(atlas_txt)
    d = os.path.dirname(atlas_txt)
    n = 0
    for page_name, pw, ph in pages:
        src = os.path.join(d, page_name)
        if not os.path.exists(src):
            continue
        img = Image.open(src)
        fmt, mode = img.format, img.mode
        page = img.convert('RGBA')
        if not _looks_like_creature(page, cov_range):
            if verbose:
                print('   %-22s skip(覆盖率)' % page_name)
            continue
        new = transform_page(page, species, fluff_scale=fluff_scale)
        if apply:
            out = new
            if fmt == 'JPEG':
                out = out.convert('RGB')
            elif mode in ('P', 'L', 'LA'):
                out = out.convert(mode)
            bak = os.path.join(BAK, os.path.relpath(src, os.path.join(ROOT, 'Assets')))
            os.makedirs(os.path.dirname(bak), exist_ok=True)
            if not os.path.exists(bak):
                shutil.copy2(src, bak)
            out.save(src)
        n += 1
        if verbose:
            print('   %-22s ok' % page_name)
    return n


def _looks_like_creature(page, cov_range):
    """毛皮像素占比过低（纯道具页）或过高（纯贴图页）就不动，避免把木棍蘑菇染成毛。"""
    arr = np.asarray(page, dtype=np.float32)
    rgb = arr[..., :3] / 255.0
    alpha = arr[..., 3] / 255.0
    if alpha.max() < 0.05:
        return False
    fur, _, _ = fur_mask_of(rgb, alpha, 0.62)
    cov = float(fur.sum()) / max(1, int((alpha > 0.06).sum()))
    return cov_range[0] <= cov <= cov_range[1]
