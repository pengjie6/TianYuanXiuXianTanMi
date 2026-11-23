# -*- coding: utf-8 -*-
"""补抓：真正的无缝毛皮贴图 + 狼/熊头像图标（替换原猫头像 UI）。"""
import json, os, re, time, urllib.parse, urllib.request, io
from PIL import Image

WORK = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(WORK, 'anchors')
RAW = os.path.join(OUT, 'raw')
os.makedirs(RAW, exist_ok=True)

ITEMS = [
    ('tex_furwolf', "extreme macro photograph of dense silver grey wolf fur, individual hairs filling the entire frame, no animal visible, no head, no face, flat even light, tileable", 768, 768),
    ('tex_furbear', "extreme macro photograph of dense chocolate brown bear fur, individual hairs filling the entire frame, no animal visible, flat even light, tileable", 768, 768),
    ('ic_wolf', "game UI icon of a silver wolf head emblem, side profile, sharp ears, hand-painted 2D mobile game style, centered on flat dark green background, gold rim outline, no text, no watermark", 512, 512),
    ('ic_bear', "game UI icon of a brown bear head emblem, round ears, hand-painted 2D mobile game style, centered on flat dark green background, gold rim outline, no text, no watermark", 512, 512),
]


def fetch(prompt, w, h, seed, retries=6):
    q = urllib.parse.urlencode({'width': w, 'height': h, 'seed': seed, 'nologo': 'true', 'model': 'flux', 'enhance': 'false'})
    url = 'https://image.pollinations.ai/prompt/%s?%s' % (urllib.parse.quote(prompt, safe=''), q)
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=180) as r:
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
                wait = 50
                m = re.search(r'after (\d+)s', msg)
                if m:
                    wait = int(m.group(1)) + 8
                print('  [%s] %s -> wait %ds' % (i, msg[:60], wait), flush=True)
                time.sleep(wait)
                continue
            except Exception:
                pass
            time.sleep(20)
        except Exception as e:
            print('  [%s] %s' % (i, e), flush=True)
            time.sleep(20)
    return None


def strip_watermark(im):
    w, h = im.size
    im = im.crop((0, 0, w, int(h * 0.90)))
    return im.resize((w, h), Image.LANCZOS)


for idx, (key, prompt, w, h) in enumerate(ITEMS):
    dst = os.path.join(OUT, key + '.png')
    if os.path.exists(dst):
        print('%s skip' % key, flush=True)
        continue
    print('[%d/%d] %s' % (idx + 1, len(ITEMS), key), flush=True)
    data = fetch(prompt, w, h, seed=880101 + idx * 31)
    if not data:
        print('  !! fail %s' % key, flush=True)
        continue
    open(os.path.join(RAW, key + '.png'), 'wb').write(data)
    im = Image.open(io.BytesIO(data)).convert('RGB')
    im = strip_watermark(im)
    im.save(dst)
    print('  ok %s %s' % (key, im.size), flush=True)
    time.sleep(48)

print('EXTRA_DONE', flush=True)
