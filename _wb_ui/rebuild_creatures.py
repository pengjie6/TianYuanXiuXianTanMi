# -*- coding: utf-8 -*-
"""从备份重建换皮角色贴图（备份 -> 重绘 -> 量化压缩 -> 写回 Assets）。

备份目录：_wb_ui/backup_spine（相对 Assets 的路径结构）
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import creature
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BAK = os.path.join(ROOT, '_wb_ui', 'backup_spine')
ASSETS = os.path.join(ROOT, 'Assets')

RULES = [
    ('AnimationSpine/Cat/', 'fox', 1.0),
    ('AnimationSpine/Monster/Baiko/baiko.png', 'wolf', 1.30),
    ('AnimationSpine/Monster/Miu/miu.png', 'wolf', 0.85),
    ('AnimationSpine/Monster/Mijus/mijus.png', 'bear', 0.80),
    ('AnimationSpine/Monster/8 Little Mijus/little_mijus.png', 'bear', 0.80),
    ('Image/SpriteSheet/uihead.png', 'fox', 1.0),
]


def rule_for(rel):
    r = rel.replace('\\', '/')
    for pat, sp, fl in RULES:
        if pat.endswith('/'):
            if pat in r:
                return sp, fl
        elif r.endswith(pat):
            return sp, fl
    return None


def main():
    n = 0
    t0 = t1 = 0
    for root, _, files in os.walk(BAK):
        for f in sorted(files):
            b = os.path.join(root, f)
            rel = os.path.relpath(b, BAK)
            rule = rule_for(rel)
            if not rule:
                continue
            sp, fl = rule
            src = os.path.join(ASSETS, rel)
            im = Image.open(b).convert('RGBA')
            if not creature._looks_like_creature(im, (0.02, 0.995)):
                continue
            new = creature.transform_page(im, sp, fluff_scale=fl)
            q = new.quantize(colors=255, method=Image.FASTOCTREE)
            os.makedirs(os.path.dirname(src), exist_ok=True)
            q.save(src, 'PNG', optimize=True)
            n += 1
            t0 += os.path.getsize(b)
            t1 += os.path.getsize(src)
    print('重建 %d 个文件，原 %.1fMB -> 现 %.1fMB' % (n, t0 / 1e6, t1 / 1e6))


if __name__ == '__main__':
    main()
