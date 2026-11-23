# -*- coding: utf-8 -*-
"""用最少的 Pollinations 请求生成换皮图标母件（共 6 张）。

图标清单：
  ic_gem      翡翠宝石（替代原紫色钻石）
  ic_coin     古金硬币
  ic_crystal  紫水晶碎片（灵魂/次级货币）
  ic_plate    空按钮底板（深绿苔石 + 古金描边）
  ic_row_a    横排三个：书本 / 闪电 / 布袋
  ic_row_b    横排三个：漩涡符文 / 兽爪印 / 加号
"""
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'anchors')
RAW = os.path.join(OUT, 'raw')
os.makedirs(RAW, exist_ok=True)

BASE = ("hand-painted 2D mobile game UI asset, ancient jungle ruins expedition theme, "
        "mossy carved dark green stone, antique weathered gold trim, subtle amber inner glow, "
        "thick clean outline, glossy painterly shading, centered, filling most of the frame, "
        "isolated on flat pure black background, no shadow, no text, no letters, "
        "no watermark, no logo, no frame border, no mockup")

JOBS = [
    ('ui_gem',
     "a single large faceted emerald gemstone, jade green crystal with bright inner light "
     "and sharp facets, classic mobile game currency icon, " + BASE,
     1024, 1024),
    ('ui_coin',
     "a single antique gold coin with a carved jungle leaf emblem on its face, thick beveled rim, "
     "warm polished metal, classic mobile game currency icon, " + BASE,
     1024, 1024),
    ('ui_crystal',
     "a cluster of three faceted amethyst purple crystal shards, violet inner glow, "
     "sharp clean facets, mobile game energy shard icon, " + BASE,
     1024, 1024),
    ('ui_plate',
     "an empty rounded rectangle button plate made of dark mossy stone with an antique gold trim "
     "edge and small carved vine corners, completely blank smooth center, front view, "
     "horizontal, " + BASE,
     1024, 512),
    ('ui_row_a',
     "three separate icons in one horizontal row, evenly spaced, same size, "
     "left: a closed leather-bound field journal with gold clasp, "
     "middle: a bright amber lightning bolt, "
     "right: a small burlap pouch tied with cord, " + BASE,
     1024, 512),
    ('ui_row_b',
     "three separate icons in one horizontal row, evenly spaced, same size, "
     "left: a carved jade spiral rune disc, "
     "middle: a carved stone beast paw print tile, "
     "right: a thick gold plus sign, " + BASE,
     1024, 512),
]


def fetch(prompt, w, h, seed, retries=12):
    q = urllib.parse.urlencode({
        'width': w, 'height': h, 'seed': seed,
        'nologo': 'true', 'model': 'flux', 'enhance': 'false',
    })
    url = 'https://image.pollinations.ai/prompt/%s?%s' % (
        urllib.parse.quote(prompt, safe=''), q)
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=200) as r:
                data = r.read()
            if len(data) > 4000:
                try:
                    Image.open(io.BytesIO(data)).verify()
                    return data
                except Exception:
                    pass
            try:
                j = json.loads(data.decode('utf-8', 'ignore'))
                msg = j.get('error', {}).get('message', '')
                m = re.search(r'after (\d+)s', msg)
                wait = int(m.group(1)) + 12 if m else 52
                print('  [%d] %s -> 等 %ds' % (i, msg[:70], wait), flush=True)
                time.sleep(wait)
                continue
            except Exception:
                pass
            print('  [%d] 非图片 %d bytes' % (i, len(data)), flush=True)
            time.sleep(20)
        except Exception as e:
            print('  [%d] %s' % (i, e), flush=True)
            time.sleep(20)
    return None


def trim(im, is_row=False):
    """裁掉底部水印带，再取顶部正方形 / 保留横排完整宽度。"""
    w, h = im.size
    keep = int(h * 0.88)
    im = im.crop((0, 0, w, keep))
    if is_row:
        return im
    side = min(w, im.size[1])
    x = (w - side) // 2
    return im.crop((x, 0, x + side, side))


done = 0
for idx, (key, prompt, w, h) in enumerate(JOBS):
    dst = os.path.join(OUT, key + '.png')
    if os.path.exists(dst):
        print('%s 已存在，跳过' % key, flush=True)
        done += 1
        continue
    print('[%d/%d] %s %dx%d ...' % (idx + 1, len(JOBS), key, w, h), flush=True)
    data = fetch(prompt, w, h, seed=20261124 + idx * 13)
    if not data:
        print('  !! %s 失败' % key, flush=True)
        continue
    open(os.path.join(RAW, key + '.bin'), 'wb').write(data)
    im = Image.open(io.BytesIO(data)).convert('RGB')
    im = trim(im, is_row=key.startswith('ic_row'))
    im.save(dst)
    print('  ok %s %s' % (key, im.size), flush=True)
    done += 1
    time.sleep(55)

print('ICONS_DONE %d/%d' % (done, len(JOBS)), flush=True)
