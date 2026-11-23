import sys, os
sys.argv = ['x']
import fetch_anchors as fa
from PIL import Image
import io
prompt = ("seamless texture of antique brushed gold metal with fine ornamental engraving, "
          "soft specular highlights, hand-painted 2D mobile game art, weathered antique gold trim, "
          "rich painterly shading, no text, no letters, no watermark, no logo")
dst = os.path.join(fa.OUT, 'tex_gold.png')
for k in range(8):
    data = fa.fetch(prompt, 1024, 1024, seed=20261123 + 77 + k * 13)
    if data:
        im = Image.open(io.BytesIO(data)).convert('RGB')
        im = fa.strip_watermark(im)
        im.save(dst)
        print('ok', im.size)
        break
    print('retry', k)
