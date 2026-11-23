# -*- coding: utf-8 -*-
"""抓取狼/熊/狐的毛皮无缝纹理 + 角色头部参考（用于 Spine 图集重绘）。"""
import json, os, re, time, urllib.parse, urllib.request, io
from PIL import Image

WORK = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(WORK, 'anchors')
RAW = os.path.join(OUT, 'raw')
os.makedirs(RAW, exist_ok=True)

STYLE = ("seamless flat tileable texture, hand-painted 2D mobile game art, "
         "soft cel shading, no text, no letters, no watermark, no logo")

ITEMS = [
    ('fur_wolf', "seamless texture of thick silver grey wolf fur, individual strands, cold blue grey tones with lighter tips, flat even lighting, " + STYLE, 768, 768),
    ('fur_bear', "seamless texture of thick warm brown bear fur, individual strands, chocolate brown with honey highlights, flat even lighting, " + STYLE, 768, 768),
    ('fur_fox',  "seamless texture of fluffy rust orange fox fur, individual strands, deep orange with cream tips, flat even lighting, " + STYLE, 768, 768),
    ('ref_wolf_head', "portrait of a chibi cartoon silver grey wolf cub head, short muzzle, triangular ears with dark tips, hand-painted 2D mobile game enemy art, centered on flat white background, no text, no watermark", 768, 768),
    ('ref_bear_head', "portrait of a chibi cartoon brown bear cub head, round ears, short muzzle, hand-painted 2D mobile game enemy art, centered on flat white background, no text, no watermark", 768, 768),
]


def fetch(prompt, w, h, seed, retries=6):
    q = urllib.parse.urlencode({
        'width': w, 'height': h, 'seed': seed,
        'nologo': 'true', 'model': 'flux', 'enhance': 'false',
    })
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
            print('  [%s] not image %d bytes' % (i, len(data)), flush=True)
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
    data = fetch(prompt, w, h, seed=771001 + idx * 13)
    if not data:
        print('  !! fail %s' % key, flush=True)
        continue
    open(os.path.join(RAW, key + '.png'), 'wb').write(data)
    im = Image.open(io.BytesIO(data)).convert('RGB')
    im = strip_watermark(im)
    im.save(dst)
    print('  ok %s %s' % (key, im.size), flush=True)
    time.sleep(48)

print('CREATURES_DONE', flush=True)
