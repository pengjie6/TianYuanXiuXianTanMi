# -*- coding: utf-8 -*-
"""生成登录页角色群像（狼/熊/狐），白底便于抠图。"""
import io
import json
import os
import re
import time
import urllib.parse
import urllib.request

from PIL import Image

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'anchors')

PROMPT = ("a lineup of six cute stylized animal adventurers standing side by side facing viewer, "
          "one grey wolf, one brown bear, one red fox, one white wolf, one black panther, "
          "one small wild boar, all wearing simple jungle explorer gear, "
          "flat 2D vector cartoon game art, thick clean dark outlines, soft cel shading, "
          "matching heights, evenly spaced, full body, "
          "isolated on flat pure white background, no shadow, no text, no letters, "
          "no watermark, no logo, no border, no frame")


def fetch(prompt, w, h, seed, retries=14):
    q = urllib.parse.urlencode({'width': w, 'height': h, 'seed': seed,
                                'nologo': 'true', 'model': 'flux', 'enhance': 'false'})
    url = 'https://image.pollinations.ai/prompt/%s?%s' % (urllib.parse.quote(prompt, safe=''), q)
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


dst = os.path.join(OUT, 'crew_wolf.png')
if os.path.exists(dst):
    print('exists')
else:
    data = fetch(PROMPT, 1216, 576, 20261125)
    if not data:
        print('FAILED')
    else:
        open(os.path.join(OUT, 'raw', 'crew_wolf.bin'), 'wb').write(data)
        im = Image.open(io.BytesIO(data)).convert('RGB')
        im.save(dst)
        print('OK', im.size)
