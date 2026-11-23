# -*- coding: utf-8 -*-
"""调试：把某个 Spine 图集按物种重绘后输出对比图（不落盘到 Assets）。"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from PIL import Image
import spine_atlas as sa
import creature

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOOK = os.path.join(ROOT, '_wb_ui', 'look')
os.makedirs(LOOK, exist_ok=True)


def render(atlas_txt, species, out_name):
    pages, regions = sa.parse(atlas_txt)
    for page_name, pw, ph in pages:
        src = os.path.join(os.path.dirname(atlas_txt), page_name)
        if not os.path.exists(src):
            continue
        page = Image.open(src).convert('RGBA')
        sx = page.size[0] / float(pw)
        sy = page.size[1] / float(ph)
        new = creature.transform_page(page, page_name, regions, ph, sx, sy, species)
        for im, tag in ((page, 'before'), (new, 'after')):
            bg = Image.new('RGBA', im.size, (250, 250, 250, 255))
            bg.alpha_composite(im)
            bg.convert('RGB').save(os.path.join(LOOK, '%s_%s_%s.jpg' % (out_name, tag, page_name.replace('.png', ''))), quality=92)
        print('saved', out_name, page_name)


if __name__ == '__main__':
    base = os.path.join(ROOT, 'Assets', 'Merge Beast', 'AnimationSpine')
    if len(sys.argv) > 1:
        render(os.path.join(base, sys.argv[1]), sys.argv[2], sys.argv[3])
    else:
        render(os.path.join(base, 'Monster/Baiko/baiko.atlas.txt'), 'wolf', 'p_baiko_wolf')
