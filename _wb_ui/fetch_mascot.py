# -*- coding: utf-8 -*-
"""生成一张狐/狼探险家吉祥物，用于替换 Avatar / CatTutor / icon_Shop 三张猫角色图。"""
import io
import json
import os
import re
import time
import urllib.parse
import urllib.request

from PIL import Image

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'anchors')

PROMPT = ("cute red fox explorer mascot character, round brass goggles pushed up on forehead, "
          "small leather backpack, standing full body, one paw raised waving hello, big friendly eyes, "
          "2D cartoon game character art, thick clean dark outlines, soft cel shading, vibrant, "
          "isolated on flat pure white background, no shadow, no text, no letters, "
          "no watermark, no logo, no border, no frame")


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


dst = os.path.join(OUT, 'mascot_fox.png')
if os.path.exists(dst):
    print('exists', flush=True)
else:
    for attempt in range(3):
        print('fetch attempt', attempt, flush=True)
        data = fetch(PROMPT, 768, 768, seed=2100 + attempt * 13)
        if data:
            open(dst, 'wb').write(data)
            print('saved', len(data), flush=True)
            break
        time.sleep(50)
