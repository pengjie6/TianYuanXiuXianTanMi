# -*- coding: utf-8 -*-
"""用 Pollinations 生成 红宝石 / 金币 两张货币母图（白底、粗描边、卡通）。"""
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

JOBS = [
    ('cur_ruby.png',
     "a single bright red ruby gemstone, chunky faceted crystal, vivid crimson red with pink highlights, "
     "mobile game currency icon, glossy polished surface, thick dark maroon outline, clean cel shading, "
     "slightly three quarter view, centered, "
     "isolated on flat pure white background, no shadow, no text, no letters, no watermark, no logo, "
     "no border, no frame, one gem only"),
    ('cur_coin.png',
     "a single cartoon gold coin, round, thick bronze rim, bright yellow gold face, bold embossed yen symbol "
     "in the center, mobile game currency icon, glossy metal, thick dark brown outline, clean cel shading, "
     "front view, centered, "
     "isolated on flat pure white background, no shadow, no text, no letters, no watermark, no logo, "
     "no border, no frame, one coin only"),
]


def fetch(prompt, w, h, seed, retries=18):
    q = urllib.parse.urlencode({'width': w, 'height': h, 'seed': seed,
                                'nologo': 'true', 'model': 'flux', 'enhance': 'false'})
    url = 'https://image.pollinations.ai/prompt/%s?%s' % (urllib.parse.quote(prompt, safe=''), q)
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=220) as r:
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
                wait = int(m.group(1)) + 15 if m else 55
                print('  [%d] %s -> wait %ds' % (i, msg[:60], wait), flush=True)
                time.sleep(wait)
                continue
            except Exception:
                pass
            print('  [%d] non-image %d bytes' % (i, len(data)), flush=True)
            time.sleep(30)
        except Exception as e:
            print('  [%d] %s' % (i, e), flush=True)
            time.sleep(30)
    return None


def main():
    os.makedirs(OUT, exist_ok=True)
    only = sys.argv[1:] or [n for n, _ in JOBS]
    for idx, (name, prompt) in enumerate(JOBS):
        if name not in only:
            continue
        dst = os.path.join(OUT, name)
        if os.path.exists(dst):
            print('exists', name, flush=True)
            continue
        for attempt in range(2):
            print('fetch', name, 'attempt', attempt, flush=True)
            data = fetch(prompt, 768, 768, seed=2200 + idx * 41 + attempt * 7)
            if data:
                open(dst, 'wb').write(data)
                print('saved', name, len(data), flush=True)
                break
            time.sleep(45)
        time.sleep(20)


if __name__ == '__main__':
    main()
