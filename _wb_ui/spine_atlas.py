# -*- coding: utf-8 -*-
"""Spine 3.x/4.x .atlas.txt 解析 + 区域拆包/回填（用于图集重绘）。

坐标约定：atlas 里的 xy 是「左下角原点」，PIL 是「左上角原点」。
rotate:true 表示该区域在图集页里被顺时针旋转 90° 存放。
"""
import os
import numpy as np
from PIL import Image

PAGE_KEYS = ('size', 'format', 'filter', 'repeat', 'pma', 'scale', 'poweroftwo')


class Region:
    __slots__ = ('name', 'page', 'rotate', 'x', 'y', 'w', 'h', 'sw', 'sh', 'ox', 'oy', 'line')

    def __repr__(self):
        return '<%s %dx%d rot=%s>' % (self.name, self.sw or self.w, self.sh or self.h, self.rotate)


def parse(atlas_path):
    """返回 (pages_info, regions)。pages_info: list of (page_name, w, h)"""
    txt = open(atlas_path, encoding='utf-8').read()
    lines = txt.splitlines()
    pages, regions = [], []
    page = None
    in_header = False
    cur = None
    for i, raw in enumerate(lines):
        line = raw.rstrip('\r')
        if not line.strip():
            continue
        stripped = line.strip()
        if not line.startswith((' ', '\t')):
            if stripped.lower().endswith('.png'):
                page = stripped
                cur = None
                in_header = True
                pages.append((page, 0, 0))
                continue
            key = stripped.split(':')[0].strip().lower()
            if in_header and key in PAGE_KEYS:
                if key == 'size':
                    a = [int(t) for t in stripped.split(':', 1)[1].split(',')]
                    pages[-1] = (page, a[0], a[1])
                continue
            in_header = False
            cur = Region()
            cur.name = stripped
            cur.page = page
            cur.rotate = False
            cur.x = cur.y = cur.w = cur.h = 0
            cur.sw = cur.sh = 0
            cur.ox = cur.oy = 0
            cur.line = i
            regions.append(cur)
            continue
        if cur is None:
            continue
        k, _, v = stripped.partition(':')
        k = k.strip().lower()
        v = v.strip()
        if k == 'size':
            a = [int(t) for t in v.split(',')]
            cur.sw, cur.sh = a
            if cur.w == 0 and cur.h == 0:
                cur.w, cur.h = a
        elif k == 'xy':
            a = [int(t) for t in v.split(',')]
            cur.x, cur.y = a
        elif k == 'orig':
            a = [int(t) for t in v.split(',')]
            if len(a) == 2:
                cur.w, cur.h = a
        elif k == 'offset':
            a = [int(t) for t in v.split(',')]
            cur.ox, cur.oy = a
        elif k == 'rotate':
            cur.rotate = v.lower() == 'true'
    return pages, regions


def page_size(pages, page_name):
    for n, w, h in pages:
        if n == page_name:
            return w, h
    raise KeyError(page_name)


def page_bbox(reg, ph, sx=1.0, sy=1.0):
    """区域在图集页 PIL 坐标下的包围盒 (left, top, right, bottom)

    atlas 头里的 size 与 PNG 实际尺寸常常不一致（图集被整体缩放成 2 的幂），
    runtime 会按 PNG 尺寸等比换算，这里用 sx/sy 做同样的换算。
    """
    w = reg.sw or reg.w
    h = reg.sh or reg.h
    if reg.rotate:
        bw, bh = h, w            # 页里是转置存放
    else:
        bw, bh = w, h
    left = int(round(reg.x * sx))
    top = int(round((ph - reg.y - bh) * sy))
    return left, top, int(round(left + bw * sx)), int(round(top + bh * sy))


def extract(page_img, reg, ph, sx=1.0, sy=1.0):
    """取出区域并还原为正向图（PNG 像素空间尺寸）。"""
    l, t, r, b = page_bbox(reg, ph, sx, sy)
    blk = page_img.crop((l, t, r, b)).convert('RGBA')
    if reg.rotate:
        blk = blk.transpose(Image.ROTATE_90)   # 页内顺时针 90° -> 还原逆时针
    return blk


def put_back(page_img, reg, ph, region_img, sx=1.0, sy=1.0):
    """把正向区域图写回图集页（自动处理旋转）。"""
    l, t, r, b = page_bbox(reg, ph, sx, sy)
    blk = region_img
    if blk.size != (r - l, b - t):
        blk = blk.resize((r - l, b - t), Image.LANCZOS)
    if reg.rotate:
        blk = blk.transpose(Image.ROTATE_270)
    if blk.size != (r - l, b - t):
        blk = blk.resize((r - l, b - t), Image.NEAREST)
    page_img.paste(blk, (l, t))
