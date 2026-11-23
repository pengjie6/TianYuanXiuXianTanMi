# -*- coding: utf-8 -*-
"""把程序化新图标 / 新底板写回 UI 贴图。用法： python apply_ui_icons.py [--apply]"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import apply_icons as A
import iconize as IZ
import vector_icons as V
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BASE = os.path.join(ROOT, 'Assets', 'Merge Beast', 'Image')
PREV = os.path.join(HERE, 'preview2')
os.makedirs(PREV, exist_ok=True)

APPLY = '--apply' in sys.argv

# 调色板
JADE = dict(base=(74, 196, 146), core=(196, 255, 228), deep=(18, 84, 68), outline_col=(14, 40, 34))
JADE_DEEP = dict(base=(46, 160, 122), core=(150, 240, 210), deep=(12, 66, 54), outline_col=(10, 32, 26))
VIOLET = dict(base=(178, 126, 246), core=(242, 218, 255), deep=(68, 32, 112), outline_col=(32, 16, 56))
AMBER = dict(base=(240, 176, 70), core=(255, 236, 186), deep=(140, 80, 16), outline_col=(58, 32, 8))


def btn(path, tone, icon, scale, glow=4):
    src = os.path.join(BASE, path)
    before = Image.open(src).convert('RGBA')
    w, h = before.size
    c = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    c.alpha_composite(A.make_plate((w, h), tone))
    if icon is not None:
        IZ.place_center(c, icon, w / 2, h / 2 + h * 0.01, int(min(w, h) * scale), glow)
    return src, before, c


def chip(path, icon, tint='gold'):
    src = os.path.join(BASE, path)
    before = Image.open(src).convert('RGBA')
    w, h = before.size
    c = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    c.alpha_composite(A.make_plate((w, h), tint, radius_ratio=0.5))
    IZ.place_center(c, icon, w / 2, h / 2, int(min(w, h) * 0.60))
    return src, before, c


def pure(path, icon, scale=0.98, glow=5):
    src = os.path.join(BASE, path)
    before = Image.open(src).convert('RGBA')
    w, h = before.size
    c = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    IZ.place_center(c, icon, w / 2, h / 2, int(min(w, h) * scale), glow)
    return src, before, c


GEM = V.gem_icon((300, 300), **JADE)
GEM_DEEP = V.gem_icon((300, 300), **JADE_DEEP)
CRYSTAL = V.gem_icon((340, 280), **VIOLET)
PILE = V.gems_pile_icon((300, 300))
COIN = V.coin_icon((300, 300))
BOLT = V.bolt_icon((240, 320))
BOOK = V.book_icon((260, 260))
POUCH = V.pouch_icon((260, 260))
SWIRL = V.swirl_icon((260, 260))
PAW = V.paw_icon((260, 260))
PLUS = V.plus_icon((160, 160))
ARROW = IZ.arrow_up(260, 260)

JOBS = [
    # 底部功能按钮
    btn('UI Main/btnUpgrade.png', 'jade', ARROW, 0.58),
    btn('UI Main/btnBoostItem.png', 'jade', BOLT, 0.56),
    btn('UI Main/btnBook.png', 'jade', BOOK, 0.60),
    btn('UI Main/btnBag.png', 'jade', POUCH, 0.60),
    btn('UI Main/btnAutoMerge.png', 'violet', SWIRL, 0.64),
    btn('UI Main/btnTotalBuff.png', 'jade', PAW, 0.62),
    btn('UI Main/btnQuickBuy.png', 'gold', None, 1.0),
    btn('UI Main/btnShop.png', 'jade', PILE, 0.82),
    chip('UI Main/btnAdd.png', PLUS, 'gold'),
    btn('UI Boost/btnBoostBuyEnable.png', 'gold', None, 1.0),
    btn('UI Boost/btnBoostBuyDisable.png', 'dark', None, 1.0),
    # 货币
    pure('UI Game/Gold.png', COIN, 1.0),
    pure('UI Upgrade/iconGold.png', COIN, 1.0),
    pure('UI Upgrade/iconGem.png', GEM, 0.98),
    pure('FreeBoost/gem.png', CRYSTAL, 0.98),
    pure('UI Main/iconGemUnlock.png', GEM_DEEP, 1.0),
]

for src, before, after in JOBS:
    name = os.path.basename(src)
    if APPLY:
        IZ.save_like(src, after)
    # 预览拼图
    w = max(before.width, after.width)
    h = before.height + after.height + 6
    canvas = Image.new('RGBA', (w, h), (238, 238, 238, 255))
    canvas.alpha_composite(before, (0, 0))
    canvas.alpha_composite(after, (0, before.height + 6))
    canvas.convert('RGB').save(os.path.join(PREV, name.replace('.png', '_prev.jpg')), quality=90)
    print(('APPLY ' if APPLY else 'DRY   ') + src.replace(BASE + os.sep, ''))

print('DONE', len(JOBS))
