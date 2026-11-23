# -*- coding: utf-8 -*-
"""生成 原图/新图 对比图，用于目检。"""
import os, sys, json
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import retheme

ROOT = retheme.ROOT
WORK = retheme.WORK
OUT = os.path.join(WORK, 'preview')
os.makedirs(OUT, exist_ok=True)

PICK = [
    'UI Game/Spawnbar.png',
    'UI Game/Gold.png',
    'UI Game/Bar_Currency.png',
    'UI Main/11211.png',
    'UI Main/Quick_Buy.png',
    'UI Book/bookTitle.png',
    'UI Book/bgUIBookBottom.png',
    'Asend/titleAscendReward.png',
    'Asend/ascend.png',
    'Vip/BG_Shop.jpg',
    'UI Upgrade/bgCategoryUpg.png',
    '_Tile/ui_board.png',
    'Map/bg01_1.png',
    'BG/jpg_main_bg.png',
    'NewMain/NewMainUISpriteSheet.png',
    'item/Gem.png',
    'StarShop/StarShop/titleStarShop.png',
    'nextStage/titleNextStage.png',
]


def checker(size, c1=60, c2=90):
    w, h = size
    im = Image.new('RGB', size, (c1, c1, c1))
    d = ImageDraw.Draw(im)
    s = 12
    for y in range(0, h, s):
        for x in range(0, w, s):
            if ((x // s) + (y // s)) % 2 == 0:
                d.rectangle((x, y, x + s - 1, y + s - 1), fill=(c2, c2, c2))
    return im


def cell(src_rel, maxw=320, maxh=320):
    src = os.path.join(ROOT, 'Assets', 'Merge Beast', 'Image', src_rel.replace('/', os.sep))
    if not os.path.exists(src):
        return None
    orig = Image.open(src).convert('RGBA')
    new, method, cov = retheme.process(src_rel.replace('/', os.sep), apply=False)
    sc = min(maxw / orig.width, maxh / orig.height, 1.0)
    w, h = max(1, int(orig.width * sc)), max(1, int(orig.height * sc))
    o2 = orig.resize((w, h), Image.LANCZOS)
    n2 = new.resize((w, h), Image.LANCZOS)
    bg = checker((w * 2 + 16, h + 26))
    bg.paste(o2, (0, 20), o2)
    bg.paste(n2, (w + 16, 20), n2)
    d = ImageDraw.Draw(bg)
    try:
        f = ImageFont.truetype(r'C:\Windows\Fonts\msyh.ttc', 13)
    except Exception:
        f = ImageFont.load_default()
    d.text((2, 2), '%s  [%s]' % (src_rel.split('/')[-1][:26], method), fill=(255, 255, 255), font=f)
    return bg


def main():
    cells = []
    for rel in PICK:
        c = cell(rel)
        if c:
            cells.append(c)
        else:
            print('缺:', rel)
    if not cells:
        print('无可预览项')
        return
    cols = 3
    cw = max(c.width for c in cells)
    ch = max(c.height for c in cells)
    rows = (len(cells) + cols - 1) // cols
    sheet = Image.new('RGB', (cw * cols, ch * rows), (30, 30, 30))
    for i, c in enumerate(cells):
        sheet.paste(c, ((i % cols) * cw, (i // cols) * ch))
    p = os.path.join(OUT, 'compare.png')
    sheet.save(p)
    print('写出', p, sheet.size)


if __name__ == '__main__':
    main()
