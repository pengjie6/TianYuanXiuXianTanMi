# -*- coding: utf-8 -*-
"""用 Pollinations 生成 2 张货币母图（钻石 / 点券代币），白底便于抠图。"""
import io
import json
import os
import re
import time
import urllib.parse
import urllib.request

from PIL import Image

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'anchors')

JOBS = [
    ('cur_gem.png',
     "a single violet crystal gem, chunky faceted gemstone, mobile game currency icon, "
     "glossy polished surface, bright inner glow, cool rim light, thick dark outline, "
     "clean cel shading, centered, slightly three quarter view, "
     "isolated on flat pure white background, no shadow, no text, no letters, "
     "no watermark, no logo, no border, no frame, no gem pile, one gem only"),
    ('cur_token.png',
     "a single round game token coin, blue steel and bronze rim, engraved stylized wolf claw sigil "
     "in the center, mobile game currency icon, glossy metal, thick dark outline, clean cel shading, "
     "centered, front view, "
     "isolated on flat pure white background, no shadow, no text, no letters, "
     "no watermark, no logo, no border, no frame, one coin only"),
]


def fetch(prompt, w, h, seed, retries=16):
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
    for idx, (name, prompt) in enumerate(JOBS):
        dst = os.path.join(OUT, name)
        if os.path.exists(dst):
            print('exists', name, flush=True)
            continue
        for attempt in range(2):
            print('fetch', name, 'attempt', attempt, flush=True)
            data = fetch(prompt, 768, 768, seed=1100 + idx * 37 + attempt * 5)
            if data:
                open(dst, 'wb').write(data)
                print('saved', name, len(data), flush=True)
                break
            time.sleep(60)
        if idx == 0:
            time.sleep(58)


if __name__ == '__main__':
    main()
