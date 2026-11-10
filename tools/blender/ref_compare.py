# Side-by-side check of a model against its turnaround sheet: top row = reference views, bottom row = orthographic
# renders of the model from the same 4 directions at the same scale (feet on the same line).
#   CMP_SRC=output/ref/survivor/head_ref_body_v1_color.blend CMP_TAG=ref_body_v1 blender -b -P tools/blender/ref_compare.py
import bpy
import json
import os
import numpy as np
from mathutils import Vector

ROOT = r"C:\Mirza Personal\model 3d maker"
SRC = os.path.join(ROOT, os.environ["CMP_SRC"])
TAG = os.environ.get("CMP_TAG", "cmp")
REF = os.environ.get("REF_TAG", "survivor")
IMG = os.path.join(ROOT, os.environ.get("REF_IMG", "notes/attachments/ref/survivor_sheet.webp"))
HEIGHT = float(os.environ.get("REF_HEIGHT", "1.78"))
SCALE = 2  # output pixels per reference pixel


def main():
    m = json.load(open(os.path.join(ROOT, "output", "ref", REF, "measure.json")))
    sys_path = os.path.join(ROOT, "tools", "blender")
    import sys
    sys.path.insert(0, sys_path)
    import ref_measure as R
    ref = bpy.data.images.load(IMG)
    w, h = ref.size
    a = np.array(ref.pixels[:], np.float32).reshape(h, w, 4)[::-1]  # row 0 = top
    bpy.ops.wm.open_mainfile(filepath=SRC)
    sc = bpy.context.scene
    cam = sc.camera
    cam.data.type = "ORTHO"
    # even light for the whole body (the head scene's area lights fall off down the body)
    for ob in [o for o in bpy.data.objects if o.type == "LIGHT"]:
        bpy.data.objects.remove(ob)
    for name_, rot, energy in (("Sun", (0.9, 0.0, 0.5), 3.2), ("Fill", (1.2, 0.0, -2.4), 1.0), ("Rim", (-0.6, 0.0, 3.1), 1.4)):
        ld = bpy.data.lights.new(name_, "SUN")
        ld.energy = energy
        ob_ = bpy.data.objects.new(name_, ld)
        bpy.context.collection.objects.link(ob_)
        ob_.rotation_euler = rot
    sc.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 2.5
    tiles_ref, tiles_mod = [], []
    # look directions (Blender: character faces -y); screen right = look x up
    dirs = {"front": Vector((0, 1, 0)), "right": Vector((1, 0, 0)), "back": Vector((0, -1, 0)), "left": Vector((-1, 0, 0))}

    def centre_col(name):
        """Image column of the body axis in a view crop: front x0; side views = torso centre at waist height."""
        if name == "front":
            return m["front"]["x0"]
        mk = np.load(os.path.join(ROOT, "output", "ref", REF, f"mask_{name}.npy"))
        rows = np.nonzero(mk.any(1))[0]
        yw = int(rows[-1] - (rows[-1] - rows[0]) * 1.05 / HEIGHT)
        runs = R.intervals(mk[yw])
        a_, b_ = max(runs, key=lambda t: t[1] - t[0])
        return (a_ + b_ - 1) / 2
    for name, (x0, x1, y0, y1) in R.VIEWS.items():
        crop = a[y0:y1, x0:x1]
        hh, ww = crop.shape[:2]
        tiles_ref.append(np.repeat(np.repeat(crop, SCALE, 0), SCALE, 1))
        # same framing: crop height covers (hh px) * m/px metres; feet at the crop's ground row
        mk = np.load(os.path.join(ROOT, "output", "ref", REF, f"mask_{name}.npy"))
        rows = np.nonzero(mk.any(1))[0]
        bot = rows[-1]
        px = HEIGHT / (rows[-1] - rows[0])
        span_h = hh * px
        ground_from_top = bot * px
        centre_y = ground_from_top - span_h / 2  # height of the crop centre above the ground
        cx = (ww / 2 - centre_col(name)) * px  # crop centre along screen right, from the body axis
        sc.render.resolution_x, sc.render.resolution_y = ww * SCALE, hh * SCALE
        cam.data.ortho_scale = max(ww, hh) * px
        d = dirs[name]
        side = d.cross(Vector((0, 0, 1)))  # screen right
        target = Vector((0, 0, centre_y)) + side * cx
        cam.location = target - d * 6
        cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
        path = os.path.join(ROOT, "renders", f"cmp_{TAG}_{name}.png")
        sc.render.filepath = path
        sc.render.film_transparent = False
        bpy.ops.render.render(write_still=True)
        im = bpy.data.images.load(path)
        tiles_mod.append(np.array(im.pixels[:], np.float32).reshape(im.size[1], im.size[0], 4)[::-1])
    row = lambda tiles: np.concatenate(tiles, 1)
    top, bottom = row(tiles_ref), row(tiles_mod)
    out = np.concatenate([top, bottom], 0)[::-1]
    img = bpy.data.images.new("cmp", out.shape[1], out.shape[0], alpha=True)
    img.pixels = out.ravel()
    img.filepath_raw = os.path.join(ROOT, "renders", f"cmp_{TAG}_sheet.png")
    img.file_format = "PNG"
    img.save()
    print("CMP_DONE", img.filepath_raw)


if __name__ == "__main__":
    main()
