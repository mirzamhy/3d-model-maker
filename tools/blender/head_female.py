"""Female head (f1): v17 traced head with female landmark offsets + hair bun.

Reference: notes/attachments/ref/survivor_f/ (front, head wire, turn sheet). Style kept close to the male v17:
same big planes, same lips / eye slits / ears; only the landmarks move (narrow pointed chin, slim jaw, smaller
nose, thin neck) and the hair is combed back into a bun with two front locks framing the face.

blender -b --factory-startup -P tools/blender/head_female.py -- --ears output/head-game/template/head_lp_v6.blend \
    --out output/head-game/template/head_f1.blend --sheet notes/attachments/qa/female_head_v1.png
"""
import sys, os, math, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh
import numpy as np
from mathutils import Vector
import head_trace as ht
import head_mix as hm

# landmark offsets in trace px (dx, dy, dd; dd smaller = more forward)
FEMALE = {
    # slim jaw, small pointed chin
    "CH_SIDE": (-24, -6, 0), "CH_TOP": (-16, 0, 0), "J_MID": (-24, -6, 4), "J_ANG": (-12, 0, 0),
    "M_CHB": (0, -6, 0), "M_CHIN": (0, -2, 2), "M_CHG": (0, 0, 2), "MC_OUT": (-10, 0, 0), "MC_UP": (-4, 0, 0),
    # smaller nose, softer brow shelf
    "N_WING": (-8, 0, 0), "N_SIDE_TOP": (-6, 0, 0), "N_BR_TOP": (-7, 0, 0), "N_BR_BOT": (-7, 0, 4),
    "M_TIP": (0, -6, 10), "N_TIPS": (-4, -6, 8), "M_SUB": (0, -6, 4),
    "B_TOP_MID": (0, -4, 4), "B_TOP_IN": (0, 0, 3), "M_GLAB": (0, 0, 3),
    # smaller mouth
    "L_CORNER": (-12, 0, 0), "L_UOUT": (-6, 0, 0), "L_LINE": (-4, 0, 0), "L_LMID": (-4, 0, 0), "L_LBOT": (-4, 0, 0),
    # thin neck
    "NK_F": (-28, 0, 0), "N1": (-34, 0, 0), "NK_EAR": (-24, 0, 0), "N2": (-38, 0, 0), "N3": (-30, 0, 0),
    "NK_BACK": (-24, 0, 0),
}

# hair combed back tight to the bun: thin smooth mass, no spikes
HP_F = {
    "top": (0.0, 0.25, -1.0), "side": (0.0, 0.6, -0.8), "back": (0.0, 0.7, -0.7),
    "thick": (0.006, 0.006, 0.005, 0.007), "lump": 0.12, "keep": 0.0, "nape": (0.0, 0.0),
}

SKIN_F = np.array([0.86, 0.66, 0.50]) ** 2.2
HAIR_F = np.array([0.36, 0.22, 0.13]) ** 2.2

# variants (user: "coba bikin variasi lain yang cewek"). tone = skin factor, same as head_paint PAINT_TONE.
VARIANTS = {
    "v1": dict(hair="bun", locks=True, tone=(1, 1, 1), hair_col=(0.36, 0.22, 0.13), face={}),
    # v2: high ponytail, black hair, front locks (without them the square hairline read male), darker skin, fuller cheek and rounder chin
    "v2": dict(hair="ponytail", locks=True, tone=(0.72, 0.67, 0.64), hair_col=(0.15, 0.12, 0.10), face={
        "CH_SIDE": (8, 0, 0), "CH_TOP": (6, 0, 0), "J_MID": (8, 0, 0), "M_CHB": (0, 2, 0), "M_CHIN": (0, 0, 1),
        "MC_OUT": (6, 0, -2), "C_BONE": (4, 0, 0), "N_WING": (3, 0, 0), "L_CORNER": (3, 0, 0)}),
}


def bun(bm):
    """Faceted bun on the top of the back of the head (icosphere, one subdivision = 80 tris), squashed a little."""
    res = bmesh.ops.create_icosphere(bm, subdivisions=1, radius=1.0)
    c = np.array([0.0, 0.118, -0.062])        # head coords (crown top y 0.103 at z 0.008); v1 0.098 sat too low
    r = np.array([0.056, 0.052, 0.056])       # reference bun ~ half the skull width
    for v in res["verts"]:
        p = np.array([v.co.x, v.co.y, v.co.z])   # unit sphere (treated as head coords)
        jitter = 0.92 + 0.16 * ht._hash(p * 3.3)
        h = c + p * r * jitter
        v.co = ht.blender_co(h)
    # band where the bun meets the head: a short ring (gathered hair) under the ball
    return res


def lock(bm, sx):
    """Front lock: a flat tapering strand from the temple down past the cheek to jaw height (front of the ear)."""
    path = [np.array(p) for p in ((0.058, 0.040, 0.050), (0.068, 0.000, 0.048), (0.069, -0.040, 0.046),
                                  (0.062, -0.088, 0.050))]
    width = [0.026, 0.022, 0.014, 0.0]
    thick = 0.007
    verts = []
    for i, (p, w) in enumerate(zip(path, width)):
        p = p * np.array([sx, 1, 1])
        out = np.array([sx * 1.0, 0, 0.25]); out /= np.linalg.norm(out)
        fwd = np.array([0, 0, 1.0])
        if w == 0:
            verts.append([bm.verts.new(ht.blender_co(p))])
            continue
        verts.append([bm.verts.new(ht.blender_co(p + fwd * w / 2)), bm.verts.new(ht.blender_co(p + out * thick)),
                      bm.verts.new(ht.blender_co(p - fwd * w / 2)), bm.verts.new(ht.blender_co(p - out * thick * 0.3))])
    for i in range(len(verts) - 1):
        a, b = verts[i], verts[i + 1]
        for k in range(4):
            k2 = (k + 1) % 4
            if len(b) == 1:
                bm.faces.new([a[k], a[k2], b[0]])
            else:
                bm.faces.new([a[k], a[k2], b[k2], b[k]])
    bm.faces.new(verts[0][::-1])


def ponytail(bm):
    """High ponytail: a gathered knot at the back of the crown, then a tapering six-sided tail down the back of the
    head (big planes, 5 rings + tip)."""
    path = [(0.0, 0.090, -0.078), (0.0, 0.075, -0.112), (0.0, 0.020, -0.128), (0.0, -0.050, -0.122),
            (0.0, -0.110, -0.104), (0.0, -0.150, -0.090)]
    rad = [0.024, 0.030, 0.030, 0.024, 0.014, 0.0]
    rings = []
    for i, (p, r) in enumerate(zip(path, rad)):
        p = np.array(p)
        if r == 0:
            rings.append([bm.verts.new(ht.blender_co(p))])
            continue
        q = np.array(path[min(i + 1, len(path) - 1)]) - np.array(path[max(i - 1, 0)])
        t = q / np.linalg.norm(q)
        u = np.array([1.0, 0, 0])
        w = np.cross(t, u)
        ring = []
        for k in range(6):
            an = 2 * math.pi * k / 6 + 0.26
            jit = 0.9 + 0.2 * ht._hash(p * 7.1 + k)
            ring.append(bm.verts.new(ht.blender_co(p + (u * math.cos(an) * 1.15 + w * math.sin(an)) * r * jit)))
        rings.append(ring)
    bm.faces.new(rings[0][::-1])
    for a, b in zip(rings, rings[1:]):
        for k in range(6):
            k2 = (k + 1) % 6
            if len(b) == 1:
                bm.faces.new([a[k], a[k2], b[0]])
            else:
                bm.faces.new([a[k], a[k2], b[k2], b[k]])


def build(ears_path, variant="v1"):
    V = VARIANTS[variant]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    ears_base = hm.make_ears(ears_path)
    trace = {}
    for n, (x, y, d) in hm.BASE_TRACE.items():
        dx, dy, dd = FEMALE.get(n, (0, 0, 0))
        ex, ey, ed = V["face"].get(n, (0, 0, 0))
        dx, dy, dd = dx + ex, dy + ey, dd + ed
        trace[n] = (x + (dx if x else 0), y + dy, d + dd)
    ht.TRACE.clear(); ht.TRACE.update(trace)
    ht.HP.clear(); ht.HP.update(hm.blend(hm.BASE_HP, [HP_F], [1.0]))
    head = ht.build_head()
    hair = ht.build_hair(head)
    eyes = ht.eye_slits()
    ears = ears_base.copy(); ears.data = ears_base.data.copy(); ears.hide_render = False
    bpy.context.scene.collection.objects.link(ears)
    bpy.data.objects.remove(ears_base)
    # bun + locks added to the hair mesh
    bm = bmesh.new(); bm.from_mesh(hair.data)
    n0 = len(bm.faces)
    (bun if V["hair"] == "bun" else ponytail)(bm)
    if V["locks"]:
        for sx in (1, -1):
            lock(bm, sx)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:] if False else list(bm.faces))
    bm.to_mesh(hair.data); bm.free()
    for p in hair.data.polygons:
        p.use_smooth = False
    for ob, nm in ((head, "Head"), (hair, "Hair"), (eyes, "Eyes"), (ears, "Ears")):
        ob.name = nm; ob.data.name = nm
    # colours (FACE Col, ratios kept for the game: skin zones = skin x ratio)
    tone = np.array(V["tone"]) ** 2.2
    hair_f = np.array(V["hair_col"]) ** 2.2
    hm.set_col(head, lambda i, old: old / ht.SKIN * SKIN_F * tone)
    hm.set_col(ears, lambda i, old: SKIN_F * tone)
    hm.set_col(hair, lambda i, old: hair_f * (0.9 if i >= n0 else 1.0))
    print("FEMALE head tris", len(head.data.polygons), "hair faces", len(hair.data.polygons))
    return head, hair, eyes, ears


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--ears", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--sheet", default="")
    ap.add_argument("--variant", default="v1", choices=sorted(VARIANTS))
    a = ap.parse_args(argv)
    build(a.ears, a.variant)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(a.out))
    if a.sheet:
        sc, cam = hm.setup_render(420)
        tmp = os.path.abspath(a.sheet) + ".tmp.png"
        tiles = [hm.render_view(sc, cam, ang, tmp) for ang in (0, 35, 90, 160)]
        os.remove(tmp)
        hm.save_sheet([np.concatenate(tiles, axis=1)], 1, os.path.abspath(a.sheet))
    print("SAVED", a.out)


if __name__ == "__main__":
    main()
