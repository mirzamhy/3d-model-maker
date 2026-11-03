# Side-by-side check of a rendered ear against the traced reference picture (plain Python + Pillow, not Blender).
#   python tools/blender/ear_compare.py v13 <reference.png>
# Draws the projected front-face edges (from ear_view.py's *_wire.json) over each ear render, mirrors it
# (the reference shows a left ear, the render the right one) and puts the reference first.
import json
import os
import sys
from PIL import Image, ImageDraw, ImageOps

R = os.path.join(os.path.dirname(__file__), "..", "..", "renders")
tag, ref = sys.argv[1], sys.argv[2]
tiles = []
for name in ("ear_flat", "ear_34", "ear_front"):
    im = Image.open(os.path.join(R, f"game_tpl_{tag}_{name}.png")).convert("RGB")
    w = json.load(open(os.path.join(R, f"game_tpl_{tag}_{name}_wire.json")))
    d = ImageDraw.Draw(im)
    W, H = im.size
    for a, b in w["edges"]:
        pa, pb = w["pts"][a], w["pts"][b]
        d.line([(pa[0] * W, pa[1] * H), (pb[0] * W, pb[1] * H)], fill=(25, 25, 25), width=2)
    tiles.append(ImageOps.mirror(im.crop((150, 100, 600, 650))))
r = Image.open(ref).convert("RGB")
r = r.resize((int(r.width * 550 / r.height), 550))
sheet = Image.new("RGB", (r.width + 450 * len(tiles) + 10 * len(tiles), 550), (255, 255, 255))
sheet.paste(r, (0, 0))
for i, t in enumerate(tiles):
    sheet.paste(t, (r.width + 10 + i * 460, 0))
out = os.path.join(R, f"game_tpl_{tag}_ear_compare.png")
sheet.save(out)
print(out)
