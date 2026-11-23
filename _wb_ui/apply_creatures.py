# -*- coding: utf-8 -*-
"""把 Spine 角色图集从猫改造成非猫物种（只处理已验证为纯角色页的图集）。

已验证：Cat(玩家合并兽 58 页) / Baiko / Miu / Mijus。
其余怪物页含金币、月亮、道具等黄色物件，重上色会误伤，故不动。

用法：
  python _wb_ui/apply_creatures.py --apply
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import creature

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPINE = os.path.join(ROOT, 'Assets', 'Merge Beast', 'AnimationSpine')

JOBS = [
    ('Cat', None, 'fox', 1.0),                    # 全部 58 页
    ('Monster/Baiko', 'baiko', 'wolf', 1.30),     # 白可 -> 银狼（1 级 Boss）
    ('Monster/Miu', 'miu', 'wolf', 0.85),
    ('Monster/Mijus', 'mijus', 'bear', 0.80),
    ('Monster/8 Little Mijus', 'little_mijus', 'bear', 0.80),
]


def run(apply=False):
    total = 0
    for folder, fn, sp, fl in JOBS:
        d = os.path.join(SPINE, folder)
        if not os.path.isdir(d):
            print('  ! 缺目录', folder)
            continue
        for f in sorted(os.listdir(d)):
            if not f.endswith('.atlas.txt'):
                continue
            if fn and not f.startswith(fn):
                continue
            if 'weapon' in f or 'effect' in f:
                continue
            n = creature.process_atlas(os.path.join(d, f), sp, apply=apply, fluff_scale=fl)
            total += n
            print('  %-24s %-5s %2d 页' % (folder + '/' + f, sp, n), flush=True)
    print('共 %d 页' % total)
    if not apply:
        print('（预演；加 --apply 执行）')


if __name__ == '__main__':
    run('--apply' in sys.argv)
