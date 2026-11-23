# -*- coding: utf-8 -*-
"""把 Merge Beast/Image 下被引用的 UI 图整体换皮为「踏足秘境探险」风格。

原则：
  1. 尺寸、色彩模式（RGBA 的 alpha）、文件格式、路径、.meta 全部不动 -> 不破坏布局与 sprite 引用
  2. 满幅背景 -> 用 AI 母图 cover 裁切整替（每类界面用不同母图，保证画面不一样）
  3. 控件图标/边框/条 -> 保留原始 alpha 与明暗结构，色相重映射到新调色板，
     再叠一层「AI 母图裁出的苔藓/石面无缝纹理 + 程序噪声」，避免场景构图糊到控件上
"""
import json, os, sys, shutil, zlib
import numpy as np
from PIL import Image, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = os.path.join(ROOT, '_wb_ui')
ANCH = os.path.join(WORK, 'anchors')
BAK = os.path.join(WORK, 'backup')
os.makedirs(os.path.join(WORK, 'preview'), exist_ok=True)
os.makedirs(BAK, exist_ok=True)

# ── 新调色板：秘境 / 古庙 / 苔石 / 古金 ───────────────────────────
PALETTE = {
    'dark':  (14, 34, 26),
    'green': (26, 74, 51),
    'moss':  (58, 107, 62),
    'jade':  (74, 143, 120),
    'gold':  (201, 162, 39),
    'amber': (230, 150, 51),
    'cream': (242, 217, 139),
}

HUE_STOPS = [(0, 28), (18, 30), (45, 40), (70, 158), (100, 176),
             (150, 186), (190, 172), (220, 196), (255, 162),
             (300, 26), (360, 28)]

_TILE_CACHE = {}


def map_hue(h_deg):
    xs = np.array([s[0] for s in HUE_STOPS], dtype=np.float32)
    ys = np.array([s[1] for s in HUE_STOPS], dtype=np.float32)
    return np.interp(h_deg, xs, ys)


def _mirror_tile(name, box_rel):
    """从 AI 母图取一块区域，做四方镜像拼接，得到可无缝平铺的纹理。"""
    key = (name, box_rel)
    if key in _TILE_CACHE:
        return _TILE_CACHE[key]
    p = os.path.join(ANCH, name + '.png')
    if not os.path.exists(p):
        return None
    im = Image.open(p).convert('L')
    w, h = im.size
    x0, y0, x1, y1 = [int(v * (w if i % 2 == 0 else h)) for i, v in enumerate(box_rel)]
    crop = im.crop((x0, y0, x1, y1))
    cw, ch = crop.size
    t = Image.new('L', (cw * 2, ch * 2))
    t.paste(crop, (0, 0))
    t.paste(crop.transpose(Image.FLIP_LEFT_RIGHT), (cw, 0))
    t.paste(crop.transpose(Image.FLIP_TOP_BOTTOM), (0, ch))
    t.paste(crop.transpose(Image.ROTATE_180), (cw, ch))
    _TILE_CACHE[key] = t
    return t


def material(size):
    """AI 苔藓/石面纹理 + 程序噪声，归一化到均值 1.0，幅度约 ±12%。"""
    w, h = size
    base = None
    tile = _mirror_tile('bg_jungle', (0.70, 0.78, 1.0, 1.0))
    if tile is not None:
        tw, th = tile.size
        reps_x = int(np.ceil(w / tw)) + 1
        reps_y = int(np.ceil(h / th)) + 1
        big = Image.new('L', (tw * reps_x, th * reps_y))
        for iy in range(reps_y):
            for ix in range(reps_x):
                big.paste(tile, (ix * tw, iy * th))
        big = big.crop((0, 0, w, h))
        base = np.asarray(big, dtype=np.float32) / 255.0

    rng = np.random.default_rng(12345 + w * 31 + h)
    lo = rng.random((max(2, h // 24), max(2, w // 24))).astype(np.float32)
    lo_img = Image.fromarray((lo * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)
    lo = np.asarray(lo_img, dtype=np.float32) / 255.0
    fine = rng.random((h, w)).astype(np.float32)
    fine = np.asarray(Image.fromarray((fine * 255).astype(np.uint8)).filter(
        ImageFilter.GaussianBlur(0.6)), dtype=np.float32) / 255.0

    if base is None:
        m = 0.6 * lo + 0.4 * fine
    else:
        m = 0.65 * base + 0.20 * lo + 0.15 * fine
    m = (m - m.mean()) / max(float(m.std()), 1e-5)
    m = np.clip(m, -2.2, 2.2)
    return 1.0 + 0.085 * m


# 渐变映射色阶（亮度 -> 颜色）
# 主色系一律走"苔玉/翡翠"冷色，只有金币/宝石类保留古金，确保与原暖橙色系彻底分开
RAMP_JADE = [(0.00, (6, 20, 16)), (0.30, (20, 62, 48)), (0.55, (42, 110, 86)),
             (0.75, (86, 156, 130)), (0.90, (152, 202, 174)), (1.00, (212, 236, 214))]
RAMP_GOLD = [(0.00, (20, 26, 16)), (0.30, (74, 68, 30)), (0.55, (140, 116, 42)),
             (0.75, (196, 164, 74)), (0.90, (232, 208, 132)), (1.00, (252, 242, 204))]
GOLD_KEYS = ('coin', 'gold', 'currency', 'gem', 'ruby', 'diamond', 'star', 'ticket', 'crown', 'key')


def _ramp(rgb_arr, stops):
    xs = np.array([s[0] for s in stops], dtype=np.float32)
    out = np.zeros(rgb_arr.shape + (3,), dtype=np.float32)
    for c in range(3):
        out[..., c] = np.interp(rgb_arr, xs, [s[1][c] for s in stops])
    return out / 255.0


def retheme_widget(im_rgba, rel=''):
    """亮度渐变映射重绘：保留原图描边/高光/阴影结构，颜色整体换成新风格。"""
    w, h = im_rgba.size
    arr = np.asarray(im_rgba, dtype=np.float32)
    alpha = arr[..., 3]
    rgb = arr[..., :3]

    lum = (0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]) / 255.0

    low = rel.replace('\\', '/').lower()
    if any(k in low for k in GOLD_KEYS):
        base = _ramp(lum, RAMP_GOLD)
        family = 'gold'
    else:
        base = _ramp(lum, RAMP_JADE)
        family = 'jade'

    # 略提饱和与对比，做出手绘层次
    gray = base.mean(axis=-1, keepdims=True)
    base = np.clip(gray + (base - gray) * 1.10, 0, 1)
    base = np.clip((base - 0.5) * 1.05 + 0.5, 0, 1)

    # 材质（AI 苔藓/石面无缝纹理 + 噪声），幅度压低，避免"锈金"质感
    a_norm = np.clip((alpha - 2) / 60.0, 0, 1)[..., None]
    base = base * (1.0 + (material((w, h))[..., None] - 1.0) * a_norm * 0.38)

    return Image.fromarray(np.dstack([np.clip(base, 0, 1) * 255.0, alpha]).astype(np.uint8), 'RGBA'), family


FOLDER_ART = {
    'Map': 'bg_map',
    'UI Book': 'tex_parchment',
    'Vip': 'bg_temple',
    'Asend': 'bg_temple',
    'BG': 'bg_jungle',
    'SHOP IAP': 'emblem_corner',
    'Battle': 'bg_jungle',
    '_Tile': 'bg_map',
    'FreeBoost': 'tex_stone',
    'UI Upgrade': 'tex_parchment',
    'StarShop': 'bg_temple',
    'nextStage': 'bg_jungle',
    'UI Boost': 'tex_parchment',
    'BuyPopup': 'tex_parchment',
    'Rating': 'bg_temple',
    'newBeast': 'bg_jungle',
    'NewMain': 'bg_jungle',
    'UI Game': 'bg_jungle',
    'UI Main': 'bg_jungle',
}


VARIED = {
    'map': ['bg_map', 'bg_temple', 'bg_jungle', 'tex_stone'],
    'bg': ['bg_jungle', 'tex_stone', 'bg_temple'],
    'asend': ['bg_temple', 'tex_stone', 'bg_jungle'],
    'vip': ['bg_temple', 'emblem_corner', 'bg_jungle'],
}


_ORD = {}


def _order_idx(rel):
    head = rel.split(os.sep)[0]
    lst = _ORD.setdefault(head, [])
    if rel not in lst:
        lst.append(rel)
    return lst.index(rel)


def pick_bg_art(rel, size):
    head = rel.split(os.sep)[0]
    if head.lower() in VARIED:
        cands = [c for c in VARIED[head.lower()] if os.path.exists(os.path.join(ANCH, c + '.png'))]
        if cands:
            return cands[_order_idx(rel) % len(cands)]
    for k in sorted(FOLDER_ART, key=len, reverse=True):
        if head.lower() == k.lower():
            cand = FOLDER_ART[k]
            if os.path.exists(os.path.join(ANCH, cand + '.png')):
                return cand
    w, h = size
    names = ['bg_jungle', 'tex_stone', 'bg_temple', 'tex_parchment', 'emblem_corner']
    names = [n for n in names if os.path.exists(os.path.join(ANCH, n + '.png'))]
    if not names:
        return None
    return names[zlib.crc32(rel.encode('utf-8')) % len(names)]


def cover_image(path, size, ox=0.5, oy=0.5):
    """ox/oy 为 0-1 的取景位置，用来让同一张母图裁出不同构图。"""
    im = Image.open(path).convert('RGB')
    tw, th = size
    w, h = im.size
    sc = max(tw / w, th / h)
    im = im.resize((max(tw, int(w * sc + 1)), max(th, int(h * sc + 1))), Image.LANCZOS)
    w, h = im.size
    left = int((w - tw) * ox)
    top = int((h - th) * oy)
    return im.crop((left, top, left + tw, top + th))


def palette_strip(size):
    w, h = size
    stops = [(0.0, PALETTE['dark']), (0.35, PALETTE['green']),
             (0.70, PALETTE['moss']), (0.92, PALETTE['gold'])]
    ys = np.linspace(0, 1, h)
    col = np.zeros((h, 3), dtype=np.float32)
    for c in range(3):
        col[:, c] = np.interp(ys, [s[0] for s in stops], [s[1][c] for s in stops])
    return Image.fromarray(np.repeat(col[:, None, :], w, axis=1).astype(np.uint8), 'RGB').convert('RGBA')


def alpha_coverage(im_rgba):
    a = np.asarray(im_rgba)[..., 3]
    return float((a > 250).mean())


def process(rel, apply=False):
    src = os.path.join(ROOT, 'Assets', 'Merge Beast', 'Image', rel)
    im = Image.open(src)
    fmt, mode, size = im.format, im.mode, im.size
    rgba = im.convert('RGBA')
    cov = alpha_coverage(rgba)

    if cov > 0.965 and max(size) >= 256:
        aspect = max(size) / max(1, min(size))
        if min(size) < 40:
            new, method = palette_strip(size), 'strip'
        elif aspect > 3.2:
            # 细长条/木板：AI 场景图裁切后只剩一条边框，保留原结构更好
            new, fam = retheme_widget(rgba, rel)
            method = 'widget(wide)'
        else:
            art = pick_bg_art(rel, size)
            if art:
                h_code = zlib.crc32(rel.encode('utf-8'))
                ox = 0.12 + (h_code % 7) / 10.0
                oy = 0.12 + ((h_code // 7) % 7) / 10.0
                new = cover_image(os.path.join(ANCH, art + '.png'), size, ox, oy).convert('RGBA')
                new.putalpha(rgba.getchannel('A'))
                method = 'bg:' + art
            else:
                new, fam = retheme_widget(rgba, rel)
                method = 'widget(fallback)'
    else:
        new, fam = retheme_widget(rgba, rel)
        method = 'widget:' + fam

    if apply:
        bak = os.path.join(BAK, rel)
        os.makedirs(os.path.dirname(bak), exist_ok=True)
        if not os.path.exists(bak):
            shutil.copy2(src, bak)
        if fmt == 'JPEG':
            new.convert('RGB').save(src, quality=93, subsampling=0)
        elif mode in ('P', 'L', 'LA'):
            new.convert(mode).save(src)
        else:
            new.save(src)
    return new, method, cov


def targets(include_beast=False):
    rows = json.load(open(os.path.join(WORK, 'used_imgs.json'), encoding='utf-8'))
    out = []
    for r in rows:
        p = r['path'].replace('\\', '/')
        if 'Merge Beast/Image/' not in p:
            continue
        rel = p.split('Merge Beast/Image/', 1)[1].replace('/', os.sep)
        if not include_beast and rel.split(os.sep)[0] == 'SpriteSheet':
            continue
        low = rel.replace('\\', '/').lower()
        # Logo 与 App 图标由 make_logo.py 单独合成，不能在这里重绘
        if low.endswith('logo 1.png') or low.endswith('icon-game.png'):
            continue
        out.append(rel)
    return sorted(out)


def main():
    apply = '--apply' in sys.argv
    ts = targets('--with-beast' in sys.argv)
    print('待处理 %d 张' % len(ts))
    stat, fails = {}, []
    for i, rel in enumerate(ts):
        try:
            _, method, _ = process(rel, apply=apply)
            stat[method] = stat.get(method, 0) + 1
            if apply and i % 25 == 0:
                print('  %d/%d' % (i, len(ts)))
        except Exception as e:
            fails.append((rel, str(e)))
    print('\n方式统计:')
    for k, v in sorted(stat.items(), key=lambda x: -x[1]):
        print('  %-20s %d' % (k, v))
    if fails:
        print('\n失败 %d:' % len(fails))
        for rel, e in fails[:20]:
            print('  %s -> %s' % (rel, e))


if __name__ == '__main__':
    main()
