# E3: standard look sheet. One row per model: front, right side, back, 3/4, head close-up (3/4), flat shaded with
# a dark wire on top, same camera framing for every row so versions can be compared side by side.
#   blender -b <new.blend> --factory-startup -P tools/qa/sheet.py -- [--compare old.blend ...] [--ref img] [--tag NAME]
# --compare: older versions, drawn as rows under the open file.  --ref: reference picture, drawn as the top row.
# --nowire: shaded only.  --size N: pixels per view (default 600).
# Output: output/qa/<tag>_sheet.png. The .blend files are never saved.
import os
import sys
import tempfile

import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import qa_common as Q  # noqa: E402
import export_glb as X  # noqa: E402

SKIN = (0.78, 0.62, 0.5, 1.0)
WIRE = (0.06, 0.06, 0.07, 1.0)
BG = (0.2, 0.21, 0.23)


def opts(p):
    p.add_argument("--compare", nargs="*", default=[])
    p.add_argument("--ref", default="")
    p.add_argument("--tag", default="")
    p.add_argument("--nowire", action="store_true")
    p.add_argument("--size", type=int, default=600)


def fill_colour(me, rgba):
    lay = me.color_attributes.new("Color", "BYTE_COLOR", "CORNER")
    lay.data.foreach_set("color", list(rgba) * len(me.loops))
    me.color_attributes.active_color = lay


def prepare(nowire):
    """Colours every mesh can show in Workbench, plus wire copies. Returns (objects, wire objects)."""
    X.corner_colours()
    objs = Q.meshes()
    for ob in objs:
        if not ob.data.color_attributes:
            fill_colour(ob.data, SKIN)
        for p in ob.data.polygons:
            p.use_smooth = False
    wires = []
    if not nowire:
        lo, hi = Q.world_bounds(objs)
        th = max(0.0004, 0.0011 * float(hi[2] - lo[2]))
        for ob in objs:
            me = Q.evaluated_mesh(ob)  # world space, modifiers applied
            w = bpy.data.objects.new("_qa_wire_" + ob.name, me)
            bpy.context.scene.collection.objects.link(w)
            m = w.modifiers.new("wire", "WIREFRAME")
            m.thickness = th
            m.use_replace = True
            m.offset = 1.0  # outward, so the shaded surface does not hide it
            dg = bpy.context.evaluated_depsgraph_get()
            flat = bpy.data.meshes.new_from_object(w.evaluated_get(dg), depsgraph=dg)
            w.modifiers.clear()
            w.data = flat
            fill_colour(flat, WIRE)
            wires.append(w)
    return objs, wires


def setup_scene():
    sc = bpy.context.scene
    Q.set_engine(sc)
    sh = sc.display.shading
    sh.light = "STUDIO"
    sh.color_type = "VERTEX" if "VERTEX" in [i.identifier for i in type(sh).bl_rna.properties["color_type"].enum_items] else "ATTRIBUTE"
    sh.show_cavity = False
    sh.show_shadows = False
    if sc.world is None:
        sc.world = bpy.data.worlds.new("_qa_world")
    sc.world.color = BG
    sc.render.film_transparent = False
    try:
        sc.view_settings.view_transform = "Standard"
    except TypeError:
        pass
    return sc


def shots(objs, size, tmp, key):
    """Render the 5 views of the open file. Returns a list of (size, size, 4) arrays."""
    cam = Q.ortho_camera()
    cam.data.clip_end = 100
    lo, hi = Q.world_bounds(objs)
    H = float(hi[2] - lo[2])
    c = (lo + hi) / 2
    out = []
    for name in ("front", "right", "back", "34"):
        d = np.array(Q.VIEWS[name])
        span_side = max(float(hi[0] - lo[0]) * abs(d[1]) + float(hi[1] - lo[1]) * abs(d[0]), 1e-3)
        cam.data.ortho_scale = max(H, span_side) * 1.06
        Q.aim(cam, c + d * 10, c)
        p = Q.render_to(os.path.join(tmp, f"{key}_{name}.png"), size, size)
        out.append(Q.load_png(p))
    # head close-up: top 14 % of the model near the centre line
    co = []
    for ob in objs:
        me = Q.evaluated_mesh(ob)
        co.extend(v.co[:] for v in me.vertices)
        bpy.data.meshes.remove(me)
    co = np.array(co)
    sel = co[(co[:, 2] > hi[2] - 0.14 * H) & (np.abs(co[:, 0]) < 0.12 * H)]
    if len(sel):
        hlo, hhi = sel.min(0), sel.max(0)
        hc = (hlo + hhi) / 2
        cam.data.ortho_scale = float(max(hhi - hlo)) * 1.9
        d = np.array(Q.VIEWS["34"])
        Q.aim(cam, hc + d * 10, hc)
        p = Q.render_to(os.path.join(tmp, f"{key}_head.png"), size, size)
        out.append(Q.load_png(p))
    else:
        out.append(np.zeros((size, size, 4), np.float32))
    return out


def fit_image(path, h, w):
    """Load a picture and fit it into an (h, w) box, nearest neighbour, centred, keeping the aspect."""
    a = Q.load_png(path) if path.lower().endswith(".png") else None
    if a is None:
        img = bpy.data.images.load(path)
        iw, ih = img.size
        a = np.array(img.pixels[:], np.float32).reshape(ih, iw, 4)[::-1]
        bpy.data.images.remove(img)
    ih, iw = a.shape[:2]
    s = min(h / ih, w / iw)
    nh, nw = max(1, int(ih * s)), max(1, int(iw * s))
    ys = (np.arange(nh) / s).astype(int).clip(0, ih - 1)
    xs = (np.arange(nw) / s).astype(int).clip(0, iw - 1)
    box = np.zeros((h, w, 4), np.float32)
    box[..., :3] = BG
    box[..., 3] = 1
    y0, x0 = (h - nh) // 2, (w - nw) // 2
    box[y0:y0 + nh, x0:x0 + nw] = a[ys][:, xs]
    return box


def main():
    a = Q.args("E3 sheet", opts)
    tag = Q.tag_of(a)
    files = [bpy.data.filepath] + [os.path.abspath(f) for f in a.compare]
    tmp = tempfile.mkdtemp(prefix="qa_sheet_")
    rows = []
    for i, f in enumerate(files):
        if i:
            bpy.ops.wm.open_mainfile(filepath=f)
        objs, _ = prepare(a.nowire)
        setup_scene()
        rows.append(np.concatenate(shots(objs, a.size, tmp, f"r{i}"), 1))
    if a.ref:
        rows.insert(0, fit_image(os.path.abspath(a.ref), a.size, rows[0].shape[1]))
    gap = np.ones((6, rows[0].shape[1], 4), np.float32)
    grid = rows[0]
    for r in rows[1:]:
        grid = np.concatenate([grid, gap, r], 0)
    os.makedirs(Q.QA_OUT, exist_ok=True)
    out = os.path.join(Q.QA_OUT, f"{tag}_sheet.png")
    Q.save_png(grid, out)
    print("QA_SHEET", out, "rows:", ["ref"] * bool(a.ref) + [os.path.basename(f) for f in files])


if __name__ == "__main__":
    main()
