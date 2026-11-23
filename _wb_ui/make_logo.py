# -*- coding: utf-8 -*-
"""生成新 Logo（踏足秘境探险）与 512x512 应用图标。

Logo 母图中央有 AI 生成的乱码刻字，因此改为：AI 丛林材质 + 程序化双层金边框 + 渐变金字。
"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = os.path.join(ROOT, '_wb_ui')
ANCH = os.path.join(WORK, 'anchors')
BAK = os.path.join(WORK, 'backup')

TITLE = '踏足秘境探险'
FONT_CANDIDATES = [
    r'C:\Windows\Fonts\msyhbd.ttc',
    r'C:\Windows\Fonts\msyh.ttc',
    r'C:\Windows\Fonts\simhei.ttf',
    os.path.join(ROOT, 'Assets', 'AdSDK', 'AdSDK', 'Font', 'DroidSansFallback.ttf'),
]

GOLD_D = (150, 112, 26)
GOLD_M = (214, 176, 74)
GOLD_L = (255, 238, 176)
DARK = (10, 26, 18)


def font(size):
    for p in FONT_CANDIDATES:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size, index=0)
            except Exception:
                pass
    raise RuntimeError('找不到可用中文字体')


def cover(path, size):
    im = Image.open(path).convert('RGB')
    tw, th = size
    w, h = im.size
    sc = max(tw / w, th / h)
    im = im.resize((max(tw, int(w * sc + 1)), max(th, int(h * sc + 1))), Image.LANCZOS)
    w, h = im.size
    return im.crop(((w - tw) // 2, (h - th) // 2, (w - tw) // 2 + tw, (h - th) // 2 + th))


def vgrad(size, stops):
    w, h = size
    ys = np.linspace(0, 1, h)
    col = np.zeros((h, 3), dtype=np.float32)
    for c in range(3):
        col[:, c] = np.interp(ys, [s[0] for s in stops], [s[1][c] for s in stops])
    return Image.fromarray(np.repeat(col[:, None, :], w, axis=1).astype(np.uint8), 'RGB')


def plate(size):
    """深绿石板：渐变打底 + 丛林材质叠加 + 边缘压暗。"""
    w, h = size
    base = vgrad(size, [(0.0, (32, 74, 54)), (0.45, (18, 48, 34)), (1.0, (11, 30, 22))]).convert('RGBA')

    tex = cover(os.path.join(ANCH, 'bg_jungle.png'), size).convert('L')
    t = np.asarray(tex.filter(ImageFilter.GaussianBlur(1.2)), dtype=np.float32) / 255.0
    t = (t - t.mean()) / max(t.std(), 1e-5)
    t = np.clip(t, -2, 2)
    arr = np.asarray(base, dtype=np.float32)[..., :3]
    arr = arr * (1.0 + 0.16 * t[..., None])
    base = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')

    # 四角压暗
    vig = Image.new('L', size, 0)
    d = ImageDraw.Draw(vig)
    d.ellipse((-w * 0.18, -h * 0.30, w * 1.18, h * 1.30), fill=255)
    vig = vig.filter(ImageFilter.GaussianBlur(min(w, h) * 0.12)).point(lambda v: int(255 - v * 0.55))
    base = Image.composite(Image.new('RGBA', size, DARK + (255,)), base, vig)
    return base


def round_frame(size, radius, color, width, inset):
    w, h = size
    layer = Image.new('RGBA', size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle((inset, inset, w - 1 - inset, h - 1 - inset),
                        radius=radius, outline=color + (255,), width=width)
    return layer


def make_logo(size=(487, 227)):
    w, h = size
    base = plate(size)
    r = int(min(w, h) * 0.12)

    # 外暗边 + 金框（双层，做出立体倒角）
    base = Image.alpha_composite(base, round_frame(size, r + 2, (8, 20, 14), 6, 1))
    base = Image.alpha_composite(base, round_frame(size, r, GOLD_D, 5, 4))
    base = Image.alpha_composite(base, round_frame(size, r - 2, GOLD_M, 3, 9))
    base = Image.alpha_composite(base, round_frame(size, r - 4, GOLD_L, 1, 12))

    layer = Image.new('RGBA', size, (0, 0, 0, 0))
    fs = int(h * 0.44)
    while True:
        f = font(fs)
        bb = f.getbbox(TITLE, stroke_width=int(fs * 0.12))
        if (bb[2] - bb[0]) <= w * 0.82 or fs <= 14:
            break
        fs -= 1
    stroke = max(4, int(fs * 0.12))
    cx, cy = w // 2, int(h * 0.50)

    # 投影
    sh = Image.new('RGBA', size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).text((cx, cy + fs * 0.09), TITLE, font=f, fill=(0, 0, 0, 150),
                            anchor='mm', stroke_width=stroke + 2, stroke_fill=(0, 0, 0, 150))
    layer = Image.alpha_composite(layer, sh.filter(ImageFilter.GaussianBlur(fs * 0.11)))

    # 深绿描边
    ol = Image.new('RGBA', size, (0, 0, 0, 0))
    ImageDraw.Draw(ol).text((cx, cy), TITLE, font=f, fill=(12, 34, 24, 255),
                            anchor='mm', stroke_width=stroke + 3, stroke_fill=(12, 34, 24, 255))
    layer = Image.alpha_composite(layer, ol)

    # 金→浅金渐变填充
    mask = Image.new('L', size, 0)
    ImageDraw.Draw(mask).text((cx, cy), TITLE, font=f, fill=255, anchor='mm')
    grad = vgrad(size, [(0.30, (255, 244, 200)), (0.46, (232, 190, 84)),
                        (0.62, (186, 140, 34)), (0.78, (236, 198, 104)),
                        (0.92, (160, 116, 26))])
    gold = grad.convert('RGBA')
    gold.putalpha(mask)
    layer = Image.alpha_composite(layer, gold)

    # 顶部高光
    hi = Image.new('RGBA', size, (0, 0, 0, 0))
    ImageDraw.Draw(hi).text((cx - 1, cy - 2), TITLE, font=f, fill=(255, 252, 235, 64), anchor='mm')
    layer = Image.alpha_composite(layer, hi)

    return Image.alpha_composite(base, layer)


def make_icon(size=(512, 512)):
    s = size[0]
    bg = cover(os.path.join(ANCH, 'bg_jungle.png'), size).convert('RGBA')
    vig = Image.new('L', size, 0)
    ImageDraw.Draw(vig).ellipse((-s * 0.15, -s * 0.15, s * 1.15, s * 1.15), fill=255)
    vig = vig.filter(ImageFilter.GaussianBlur(s * 0.10)).point(lambda v: int(255 - v * 0.45))
    bg = Image.composite(Image.new('RGBA', size, (6, 20, 14, 255)), bg, vig)

    coin_p = os.path.join(ANCH, 'emblem_coin.png')
    if os.path.exists(coin_p):
        coin = Image.open(coin_p).convert('RGBA')
        cs = int(s * 0.78)
        coin = coin.resize((cs, cs), Image.LANCZOS)
        # 圆形遮罩
        m = Image.new('L', (cs, cs), 0)
        ImageDraw.Draw(m).ellipse((int(cs * 0.02), int(cs * 0.02), cs - int(cs * 0.02), cs - int(cs * 0.02)), fill=255)
        m = m.filter(ImageFilter.GaussianBlur(1.2))
        coin.putalpha(m)
        bg.alpha_composite(coin, ((s - cs) // 2, (s - cs) // 2))

    ring = Image.new('RGBA', size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ring)
    pad = int(s * 0.038)
    d.ellipse((pad, pad, s - pad, s - pad), outline=(146, 110, 30, 255), width=max(4, int(s * 0.020)))
    d.ellipse((pad + int(s * 0.011), pad + int(s * 0.011), s - pad - int(s * 0.011), s - pad - int(s * 0.011)),
              outline=(236, 202, 108, 220), width=max(2, int(s * 0.008)))
    return Image.alpha_composite(bg, ring)


def main():
    apply = '--apply' in sys.argv
    os.makedirs(BAK, exist_ok=True)
    logo_src = os.path.join(ROOT, 'Assets', 'Merge Beast', 'Image', 'BG', 'logo 1.png')
    icon_src = os.path.join(ROOT, 'Assets', 'Merge Beast', 'Image', 'icon-game.png')

    for src in (logo_src, icon_src):
        bak = os.path.join(BAK, os.path.relpath(src, os.path.join(ROOT, 'Assets')))
        os.makedirs(os.path.dirname(bak), exist_ok=True)
        if not os.path.exists(bak):
            Image.open(src).save(bak)

    logo = make_logo(Image.open(logo_src).size)
    logo.save(os.path.join(WORK, 'preview', 'new_logo.png'))
    ic = make_icon((512, 512))
    ic.save(os.path.join(WORK, 'preview', 'new_icon.png'))

    if apply:
        logo.save(logo_src)
        ic.save(icon_src)
        print('已写入 logo 与 icon')
    print('logo', logo.size, 'icon', ic.size)


if __name__ == '__main__':
    main()
