# -*- coding: utf-8 -*-
"""Beast_SpriteSheet 去猫化：爪印 -> 野兽抓痕；猫头 -> 狼头。

原则：
- 只改目标 sprite 的像素，sprite rect 与图集尺寸完全不动
- 不依赖 cv2/scipy，纯 numpy + PIL 做扩散修复
"""
import json
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SHEET = os.path.join(ROOT, 'Assets', 'Merge Beast', 'Image',
                     'SpriteSheet', 'Beast_SpriteSheet.png')
# 处理永远基于原始备份，避免重复 apply 时叠加
SRC = os.path.join(HERE, 'backup_beast', 'Beast_SpriteSheet.png')
RECTS = os.path.join(HERE, 'bs_rects.json')
LOOK = os.path.join(HERE, 'look')

# ---------------------------------------------------------------- 基础工具


def load_sheet():
    im = Image.open(SRC if os.path.exists(SRC) else SHEET).convert('RGBA')
    data = json.load(open(RECTS))
    return im, data


def crop(im, box):
    x, y, w, h = box
    return im.crop((x, y, x + w, y + h))


def _box1(a, r, axis):
    """沿指定轴做一次盒式模糊（边界用边缘值延拓）。"""
    if r < 1:
        return a
    pad = [(0, 0)] * a.ndim
    pad[axis] = (r + 1, r)
    p = np.pad(a, pad, mode='edge')
    c = np.cumsum(p, axis=axis)
    n = a.shape[axis]
    sl_hi = [slice(None)] * a.ndim
    sl_lo = [slice(None)] * a.ndim
    sl_hi[axis] = slice(2 * r + 1, 2 * r + 1 + n)
    sl_lo[axis] = slice(0, n)
    return (c[tuple(sl_hi)] - c[tuple(sl_lo)]) / (2 * r + 1.0)


def blur_f(a, sigma):
    """三次盒式模糊近似高斯，支持任意通道数。"""
    r = max(1, int(round(sigma * 0.85)))
    out = a.astype(np.float32)
    for _ in range(3):
        out = _box1(out, r, 0)
        out = _box1(out, r, 1)
    return out


def diffuse_fill(rgb, mask, iters=90, sigma=1.6):
    """把 mask 区域用周围像素扩散填满（逐环生长）。"""
    val = rgb.astype(np.float32).copy()
    filled = (~mask).astype(np.float32)
    for _ in range(iters):
        num = blur_f(val * filled[..., None], sigma)
        den = blur_f(filled[..., None], sigma)[..., 0]
        grow = (filled < 0.5) & (den > 1e-3)
        if not grow.any():
            break
        cand = num / np.maximum(den, 1e-3)[..., None]
        val[grow] = cand[grow]
        filled[grow] = 1.0
    return val.astype(np.uint8)


def dilate(mask, r):
    """方形膨胀（mask 为 bool）。"""
    m = Image.fromarray((mask * 255).astype(np.uint8), 'L')
    m = m.filter(ImageFilter.MaxFilter(2 * r + 1))
    return np.asarray(m) > 127


def lum(rgb):
    return rgb[..., :3].astype(np.float32).mean(axis=2)


# ---------------------------------------------------------------- 爪印检测

# 真正的猫爪印（三趾垫 + 带螺旋的掌垫），附带手工标定的检测窗口
# 窗口 = (相对中心 x, 相对中心 y, 相对半径)
PAW_SPEC = {
    42: [(0.335, 0.635, 0.170), (0.575, 0.410, 0.170), (0.725, 0.720, 0.150)],
    45: [(0.500, 0.470, 0.260)],
    48: [(0.500, 0.460, 0.235)],
    121: [(0.400, 0.460, 0.210)],
    122: [(0.520, 0.430, 0.205), (0.270, 0.480, 0.140)],
    85: [(0.345, 0.365, 0.150), (0.595, 0.300, 0.165), (0.515, 0.510, 0.150)],
    97: [(0.715, 0.740, 0.135)],
    88: [(0.740, 0.680, 0.110)],
    47: [(0.480, 0.160, 0.090), (0.620, 0.230, 0.072), (0.755, 0.310, 0.078),
         (0.290, 0.690, 0.095), (0.440, 0.800, 0.070), (0.805, 0.790, 0.078)],
    86: [(0.500, 0.520, 0.560, 'dark', 0.055)],
}
# 图集里未被切成 sprite 的散置蓝牌（游戏不引用，但图集里能看见爪印）
LOOSE = [(844, 1581, 80, 105), (935, 1581, 65, 105), (1027, 1581, 49, 105),
         (1195, 1581, 49, 105), (1270, 1581, 66, 105)]
# 宝石底 + 双兽剪影的图标：整体换成冷银灰的狼
BEAST_IDX = [17, 18, 26, 27, 28, 29, 115]
PAW_IDX = sorted(PAW_SPEC)


def wolfify(rgba, thr=0.72, soft=0.20):
    """把暖棕色/深色的兽剪影改成冷银灰狼，边界软过渡避免锯齿。"""
    a = np.asarray(rgba).astype(np.float32)
    L = a[..., :3].max(axis=2) / 255.0
    w = np.clip((thr - L) / soft, 0, 1) * (a[..., 3] / 255.0)
    lum = (a[..., :3] * np.array([0.299, 0.587, 0.114])).sum(axis=2)
    # 暗部提亮，避免变成一团黑；整体偏冷银蓝
    L2 = 74.0 + lum * 0.82
    new = np.stack([L2 * 0.93, L2 * 0.98, L2 * 1.07 + 6], axis=2)
    out = a[..., :3] * (1 - w[..., None]) + new * w[..., None]
    return Image.fromarray(
        np.dstack([np.clip(out, 0, 255), a[..., 3]]).astype(np.uint8), 'RGBA')
# #5 #6 #7 是流星/彗星图案，本身已是三道拖尾，不动


def _label(mask):
    """4 邻域连通域标记，返回 (labels, n)。纯 numpy + 栈，图很小够用。"""
    h, w = mask.shape
    lab = np.zeros((h, w), np.int32)
    n = 0
    ys, xs = np.nonzero(mask)
    for sy, sx in zip(ys, xs):
        if lab[sy, sx]:
            continue
        n += 1
        stack = [(sy, sx)]
        lab[sy, sx] = n
        while stack:
            y, x = stack.pop()
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ny, nx = y + dy, x + dx
                if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not lab[ny, nx]:
                    lab[ny, nx] = n
                    stack.append((ny, nx))
    return lab, n


def paw_blobs(rgba, spec):
    """在手工标定的小窗口内分割出爪印，返回 [(wipe_mask, bbox, pure_mask)]。

    spec: [(相对 cx, 相对 cy, 相对半径[, 极性])]，极性 'light' 取亮块、
    'dark' 取暗块（石台上的凹刻爪印是暗的）。
    """
    a = np.asarray(rgba).astype(np.float32)
    L = a[..., :3].max(axis=2) / 255.0
    al = a[..., 3] / 255.0
    h, w = L.shape
    yy, xx = np.mgrid[0:h, 0:w]
    out = []
    for item in spec:
        rx, ry, rr = item[0], item[1], item[2]
        polar = item[3] if len(item) > 3 else 'light'
        cx, cy = rx * w, ry * h
        R = rr * min(w, h)
        win = ((xx - cx) ** 2 + (yy - cy) ** 2 <= R * R) & (al > 0.5)
        vals = L[win]
        if vals.size < 40:
            continue
        if polar == 'light':
            base, ext = np.percentile(vals, 55), np.percentile(vals, 98)
            if ext - base < 0.06:
                continue
            thr = base + (ext - base) * 0.34
            light = (L > thr) & win
        else:
            base, ext = np.percentile(vals, 45), np.percentile(vals, 2)
            if base - ext < 0.05:
                continue
            thr = base - (base - ext) * 0.40
            light = (L < thr) & win
        if light.sum() < 40:
            continue
        # 窗口是手工标定的，窗口内所有亮块都属于这只爪印
        keep = light
        ys, xs = np.nonzero(keep)
        if ys.size < 40:
            continue
        bw, bh = xs.max() - xs.min() + 1, ys.max() - ys.min() + 1
        if bw < 8 or bh < 8:
            continue
        bbox = (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))
        out.append((dilate(keep, 3), bbox, keep))
    return out


# ---------------------------------------------------------------- 抓痕绘制


def _blade(cx, cy, length, half_w, tilt, m=22):
    """一道柳叶形抓痕的多边形（两端尖、中间宽）。"""
    top, bot = [], []
    for k in range(m + 1):
        u = k / m
        v = u * 2 - 1
        w = half_w * max(0.0, 1 - v * v) ** 0.55
        x = cx + (u - 0.5) * length
        y = cy + (u - 0.5) * length * tilt
        top.append((x, y - w))
        bot.append((x, y + w))
    return top + bot[::-1]


def scratch_shape(d, cx, cy, diag, col, outline, tilt=-0.36, n=3,
                  half=0.040, gap=0.210):
    """画 n 道平行斜抓痕：先用粗线描外轮廓，再填内部，描边只在外侧。"""
    ow = max(2.0, diag * 0.018)
    ln_all = diag * 0.88
    # 垂直于抓痕方向的单位向量，三道沿它等距排开
    L2 = (1.0 + tilt * tilt) ** 0.5
    ux, uy = -tilt / L2, 1.0 / L2
    for i in range(n):
        t = (i - (n - 1) / 2.0) / max(1.0, (n - 1) / 2.0)       # -1..1
        ln = ln_all * (1.0 - 0.12 * abs(t))
        off = t * diag * gap
        px = cx + off * ux
        py = cy + off * uy
        poly = _blade(px, py, ln, diag * half, tilt)
        d.line(poly + [poly[0]], fill=outline,
               width=max(2, int(round(ow * 2))), joint='curve')
        d.polygon(poly, fill=col)


def pick_paw_colors(rgba, mask):
    """取爪印的高亮色和底板的描边色。"""
    a = np.asarray(rgba).astype(np.float32)
    px = a[mask & (a[..., 3] > 200)]
    if px.size == 0:
        return (232, 248, 255, 255), (20, 34, 62, 255)
    L = px[:, :3].mean(axis=1)
    hi = px[L >= np.percentile(L, 78)][:, :3].mean(axis=0)
    col = tuple(int(c) for c in np.clip(hi * 1.05, 0, 255)) + (255,)
    allp = a[a[..., 3] > 128][:, :3]
    La = allp.mean(axis=1)
    dk = allp[La <= np.percentile(La, 10)].mean(axis=0)
    out = tuple(int(c) for c in np.clip(dk * 0.55, 0, 255)) + (255,)
    return col, out


def flatten_paws(rgba, spec, lift=None):
    """把小牌上的浅色爪印抹平（不画抓痕）：用牌面基色填掉高亮部分。"""
    a = np.asarray(rgba).astype(np.float32)
    rgb, al = a[..., :3], a[..., 3]
    L = rgb.max(axis=2) / 255.0
    h, w = L.shape
    yy, xx = np.mgrid[0:h, 0:w]
    out = rgb.copy()
    for item in spec:
        rx, ry, rr = item[0], item[1], item[2]
        cx, cy = rx * w, ry * h
        R = rr * min(w, h)
        win = ((xx - cx) ** 2 + (yy - cy) ** 2 <= R * R) & (al > 0.5)
        if win.sum() < 30:
            continue
        polar = item[3] if len(item) > 3 else 'light'
        lf = item[4] if len(item) > 4 else (lift if lift is not None else 0.12)
        med = float(np.median(L[win]))
        paw = win & ((L > med + lf) if polar == 'light' else (L < med - lf))
        if paw.sum() < 10:
            continue
        base = ~paw & win
        if base.sum() < 20:
            continue
        # 用邻域模糊值填补，避免出现平的色块
        for _ in range(3):
            bi = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), 'RGB')
            b = np.asarray(bi.filter(ImageFilter.GaussianBlur(2.0))).astype(np.float32)
            out[paw] = b[paw]
    res = np.dstack([np.clip(out, 0, 255), al]).astype(np.uint8)
    # 只模糊颜色，alpha 保持原样，避免边缘发虚
    img = Image.fromarray(res, 'RGBA')
    blurred = img.convert('RGB').filter(ImageFilter.GaussianBlur(0.4))
    out2 = Image.merge('RGBA', (*blurred.split(), img.getchannel('A')))
    return out2


FLATTEN_IDX = [47, 86]


def make_paw_sprite(rgba, idx=None, spec=None):
    """把一块（或几块）爪印 sprite 改成三道抓痕。"""
    if spec is None:
        spec = PAW_SPEC[idx]
    if idx is not None and idx in FLATTEN_IDX:
        return flatten_paws(rgba, spec), 0
    blobs = paw_blobs(rgba, spec)
    if not blobs:
        return rgba, 0
    arr = np.asarray(rgba)
    h, w = arr.shape[:2]
    wipe = np.zeros((h, w), dtype=bool)
    for region, _, _ in blobs:
        wipe |= region
    filled = diffuse_fill(arr[..., :3], wipe, iters=90, sigma=1.4)
    new = Image.fromarray(
        np.dstack([filled, arr[..., 3]]).astype(np.uint8), 'RGBA')

    for _, (x0, y0, x1, y1), pure in blobs:
        col, out = pick_paw_colors(rgba, pure)
        cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
        bw, bh = x1 - x0 + 1, y1 - y0 + 1
        diag = max(bw, bh)
        d = ImageDraw.Draw(new)
        n_scr = 3 if diag >= 26 else 2
        scratch_shape(d, cx, cy, diag * 0.84, col, out, tilt=-0.52, n=n_scr,
                      half=0.072 if n_scr == 2 else 0.060,
                      gap=0.300 if n_scr == 2 else 0.262)
    return new, len(blobs)


# ---------------------------------------------------------------- 主流程

TARGETS = {'paw': PAW_IDX}


def build(apply=False, preview=True):
    im, data = load_sheet()
    out = im.copy()
    report = []
    for idx in PAW_IDX:
        n, x, y, w, h = data[idx]
        sub = crop(im, (x, y, w, h))
        new, cnt = make_paw_sprite(sub, idx)
        out.paste(new, (x, y))
        report.append((idx, n, w, h, cnt))
        print('  paw  #%-3d %-22s %dx%d paws=%d' % (idx, n, w, h, cnt))
    for (lx, ly, lw, lh) in LOOSE:
        sub = crop(im, (lx, ly, lw, lh))
        new, cnt = make_paw_sprite(sub, spec=[(0.50, 0.50, 0.44)])
        out.paste(new, (lx, ly))
        print('  loose (%d,%d) %dx%d paws=%d' % (lx, ly, lw, lh, cnt))
    for idx in BEAST_IDX:
        n, x, y, w, h = data[idx]
        sub = crop(im, (x, y, w, h))
        out.paste(wolfify(sub), (x, y))
        report.append((idx, n, w, h, 'wolf'))
        print('  wolf #%-3d %-22s %dx%d' % (idx, n, w, h))

    if preview:
        allidx = PAW_IDX + BEAST_IDX
        cell, gap = 118, 8
        per_row = 2
        rows = (len(allidx) + per_row - 1) // per_row
        W = per_row * (cell * 2 + gap * 2)
        H = rows * (cell + 22)
        sheet = Image.new('RGBA', (W, H), (18, 38, 32, 255))
        d = ImageDraw.Draw(sheet)
        for i, idx in enumerate(allidx):
            n, x, y, w, h = data[idx]
            a = crop(im, (x, y, w, h))
            b = crop(out, (x, y, w, h))
            k = min(float(cell - 8) / max(w, h), 2.4)
            ox = (i % per_row) * (cell * 2 + gap * 2)
            oy = (i // per_row) * (cell + 22)
            for j, sp in enumerate((a, b)):
                s2 = sp.resize((max(1, int(w * k)), max(1, int(h * k))),
                               Image.LANCZOS)
                sheet.alpha_composite(
                    s2, (ox + j * (cell + gap) + (cell - s2.width) // 2,
                         oy + (cell - s2.height) // 2))
            d.text((ox + 2, oy + cell + 2), '#%d  orig | new' % idx,
                   fill=(255, 240, 120, 255))
        sheet.convert('RGB').save(os.path.join(LOOK, 'paw_after.png'))
    return out, report


def save(out):
    """原地写回图集，尺寸/模式/.meta 都不动。"""
    out.save(SHEET, optimize=True)
    print('saved', SHEET, out.size, out.mode)


if __name__ == '__main__':
    import sys
    out, rep = build(preview=True)
    if '--apply' in sys.argv:
        save(out)
    print('done', len(rep))
