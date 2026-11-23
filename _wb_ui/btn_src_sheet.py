# -*- coding: utf-8 -*-
"""把 Main 场景里按钮实际用到的切片裁出来，和备份原图并排对照。"""
import json
import os

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CUR = os.path.join(ROOT, 'Assets', 'Merge Beast', 'Image', 'SpriteSheet', 'Beast_SpriteSheet.png')
BAK = os.path.join(HERE, 'backup_beast', 'Beast_SpriteSheet.png')

USED = [2, 7, 11, 24, 25, 40, 43, 45, 51, 67, 104, 112, 121, 122, 125, 127]

rects = dict((n, (x, y, w, h)) for n, x, y, w, h in json.load(open(os.path.join(HERE, 'bs_rects.json'), encoding='utf-8')))
cur = Image.open(CUR).convert('RGBA')
bak = Image.open(BAK).convert('RGBA')

cell = 190
cols = 8
rows = (len(USED) + cols - 1) // cols
sheet = Image.new('RGBA', (cell * cols, cell * rows * 2), (22, 44, 38, 255))
d = ImageDraw.Draw(sheet)

for i, idx in enumerate(USED):
    name = 'Beast_SpriteSheet_%d' % idx
    x, y, w, h = rects[name]
    for j, im in enumerate((bak, cur)):
        c = im.crop((x, y, x + w, y + h))
        k = min((cell - 26) / max(c.size), 1.0)
        s = c.resize((max(1, int(c.width * k)), max(1, int(c.height * k))), Image.LANCZOS)
        bx = (i % cols) * cell + (cell - s.width) // 2
        by = (i // cols) * cell * 2 + j * cell + (cell - s.height) // 2
        sheet.alpha_composite(s, (bx, by))
    d.text(((i % cols) * cell + 6, (i // cols) * cell * 2 + 2), '#%d' % idx, fill=(255, 230, 120, 255))

out = os.path.join(HERE, 'look', 'btn_real_src.png')
sheet.convert('RGB').save(out, quality=95)
print(out, sheet.size)
