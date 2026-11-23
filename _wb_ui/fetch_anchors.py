# -*- coding: utf-8 -*-
"""按 Pollinations 免费额度（1 张 / 45s / IP）顺序抓取风格母图，并裁掉底部水印带。"""
import json, os, sys, time, urllib.parse, urllib.request, io
from PIL import Image

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'anchors')
RAW = os.path.join(OUT, 'raw')
os.makedirs(RAW, exist_ok=True)

STYLE = ("hand-painted 2D mobile game art, ancient jungle ruins expedition theme, "
         "mossy carved stone, weathered antique gold trim, deep emerald green and amber torchlight, "
         "rich painterly shading, no text, no letters, no watermark, no logo")

ANCHORS = [
    # key, prompt, width, height
    ('bg_jungle',   "vertical background of a mysterious ancient jungle temple entrance, giant mossy stone steps, hanging vines, glowing amber torches, dense mist, " + STYLE, 832, 1472),
    ('bg_temple',   "vertical background of a ruined temple interior hall, carved pillars, shafts of golden light through broken roof, floating dust, " + STYLE, 832, 1472),
    ('bg_map',      "ancient explorer treasure map of a jungle region drawn on old parchment, hand inked coastlines and mountain ridges, compass roses, burnt edges, top down flat view, " + STYLE.replace('no text, no letters, ', ''), 1024, 1024),
    ('tex_stone',   "seamless texture of weathered carved stone slab with subtle cracks and moss in the crevices, flat even lighting, " + STYLE, 1024, 1024),
    ('tex_parchment', "seamless texture of aged parchment paper, soft fibers, faint water stains, warm beige, flat even lighting, " + STYLE, 1024, 1024),
    ('tex_gold',    "seamless texture of antique brushed gold metal with fine ornamental engraving, soft specular highlights, " + STYLE, 1024, 1024),
    ('tex_vine',    "seamless texture of dense dark green jungle foliage and fern leaves, soft depth, " + STYLE, 1024, 1024),
    ('tex_runes',   "seamless texture of ancient engraved rune symbols carved into dark green stone, glowing amber in the grooves, " + STYLE, 1024, 1024),
    ('emblem_coin', "a single antique gold coin with a carved compass rose emblem, facing viewer, centered, isolated on flat dark green background, " + STYLE, 768, 768),
    ('emblem_gem',  "a single glowing amber crystal gem, faceted, centered, isolated on flat black background, " + STYLE, 768, 768),
    ('emblem_flame', "a single torch flame, warm orange gradient, centered, isolated on flat black background, " + STYLE, 768, 768),
    ('emblem_corner', "an ornate antique gold corner ornament with vine leaves, viewed from front, isolated on flat dark green background, " + STYLE, 768, 768),
    ('logo_plate',  "an empty carved stone plaque with thick antique gold border and vine ornaments at the corners, horizontal, blank center, " + STYLE, 1024, 512),
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
                import re
                m = re.search(r'after (\d+)s', msg)
                if m:
                    wait = int(m.group(1)) + 8
                print('  [%s] %s -> 等 %ds' % (i, msg[:60], wait), flush=True)
                time.sleep(wait)
                continue
            except Exception:
                pass
            print('  [%s] 非图片返回 %d bytes' % (i, len(data)), flush=True)
            time.sleep(20)
        except Exception as e:
            print('  [%s] %s' % (i, e), flush=True)
            time.sleep(20)
    return None

def strip_watermark(im):
    """裁掉底部水印带（约 9%），再等比还原到原尺寸。"""
    w, h = im.size
    keep = int(h * 0.90)
    im = im.crop((0, 0, w, keep))
    return im.resize((w, h), Image.LANCZOS)

done = {}
for idx, (key, prompt, w, h) in enumerate(ANCHORS):
    dst = os.path.join(OUT, key + '.png')
    if os.path.exists(dst):
        print('%s 已存在，跳过' % key, flush=True)
        done[key] = dst
        continue
    print('[%d/%d] %s %dx%d ...' % (idx + 1, len(ANCHORS), key, w, h), flush=True)
    data = fetch(prompt, w, h, seed=20261123 + idx * 7)
    if not data:
        print('  !! %s 失败' % key, flush=True)
        continue
    open(os.path.join(RAW, key + '.png'), 'wb').write(data)
    im = Image.open(io.BytesIO(data)).convert('RGB')
    im = strip_watermark(im)
    im.save(dst)
    print('  ok %s %s' % (key, im.size), flush=True)
    done[key] = dst
    time.sleep(48)

print('ANCHORS_DONE %d/%d' % (len(done), len(ANCHORS)), flush=True)
