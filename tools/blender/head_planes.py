# Big-plane low-poly game head (style: notes/attachments/ref/lowpoly_head_ref.gif): a hexagon face, a wedge jaw,
# a rectangular nose bridge, deep eye sockets, a mouth band, a wide chin, a helmet of hair with a few fringe points, one flat skin colour. ~200 faces, not a sculpt.
#   blender -b --factory-startup -P tools/blender/head_planes.py -- --out output/head-game/template/head_lp_v1.blend
# Template contract (ref_body.py stitches the body to it): object Head_Main, eye level y = 0, chin ~ -0.12,
# a 10-vertex neck tube at the azimuths of body_quad.COLS (0 22 48 90 120 180 + mirror, measured as
# atan2(x, z + 0.01)), loop at y = -0.132, rings below NECK_CUT_Y (-0.142), capped ring at -0.172.
# The head (object Head) is a closed ball; Head_Main is only the neck stick pushed into it.
# Head coords here: x = character's left, y up, z forward. Blender: (x, -z, y).
import argparse
import math
import os
import sys

import bmesh
import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # head_template (ear trace)

COLS = [0, 22, 48, 90, 120, 180]

# Head columns (half, front centre -> back centre). The head is its own object, so it can have more columns than
# the neck: 10 = edge of the nose bridge (cols 0 + 10 make the flat rectangular bridge), 22 = side of the nose /
# inner eye corner / mouth corner, 48 = front corner of the face (cheekbone line), 90 = side (ear line, jaw edge),
# 120 = back corner, 180 = back centre.
HCOLS = [0, 10, 22, 48, 90, 120, 180]
# rows top -> bottom: y, then (x, z) per half column; back columns under the skull carry their own height (x, z, y)
ROWS = [
    (0.100, [(0, 0.040), (0.013, 0.039), (0.026, 0.036), (0.046, 0.022), (0.052, -0.012), (0.044, -0.046), (0, -0.058)]),  # crown
    (0.075, [(0, 0.074), (0.017, 0.072), (0.034, 0.068), (0.062, 0.044), (0.073, -0.010), (0.063, -0.070), (0, -0.090)]),  # skull
    (0.035, [(0, 0.094), (0.014, 0.094), (0.030, 0.090), (0.066, 0.064), (0.077, -0.006), (0.067, -0.076), (0, -0.100)]),  # forehead
    (0.014, [(0, 0.097), (0.009, 0.098), (0.024, 0.100), (0.064, 0.078), (0.076, -0.002), (0.066, -0.074), (0, -0.098)]),  # brow ridge
    (-0.004, [(0, 0.095), (0.008, 0.095), (0.019, 0.081), (0.058, 0.066), (0.071, 0.000), (0.064, -0.070), (0, -0.092)]),  # eye: socket 19 mm under the brow
    (-0.028, [(0, 0.110), (0.008, 0.109), (0.018, 0.088), (0.060, 0.075), (0.069, -0.004), (0.058, -0.062), (0, -0.080)]),  # bridge, cheekbone forward
    (-0.046, [(0, 0.122), (0.010, 0.118), (0.017, 0.094), (0.056, 0.073), (0.066, -0.008), (0.052, -0.056), (0, -0.070)]),  # nose tip
    (-0.058, [(0, 0.098), (0.010, 0.098), (0.020, 0.097), (0.052, 0.075), (0.059, -0.012), (0.048, -0.050), (0, -0.066)]),  # under nose; 90 = jaw angle
    # mouth: upper lip edge -> mouth bottom is a 5 mm recessed band (dark), then the lower lip
    (-0.073, [(0, 0.101), (0.012, 0.100), (0.024, 0.094), (0.049, 0.078), (0.055, 0.004), (0.045, -0.044, -0.066), (0, -0.060, -0.064)]),
    (-0.078, [(0, 0.095), (0.012, 0.094), (0.024, 0.091), (0.047, 0.079), (0.053, 0.012), (0.042, -0.036, -0.072), (0, -0.054, -0.068)]),
    (-0.090, [(0, 0.099), (0.012, 0.098), (0.025, 0.093), (0.043, 0.082), (0.048, 0.030), (0.039, -0.026, -0.082), (0, -0.046, -0.076)]),
    # chin: a wide flat front (cols 0..22) and a bevel row under it, not a point
    (-0.112, [(0, 0.101), (0.014, 0.100), (0.028, 0.095), (0.037, 0.087), (0.040, 0.060), (0.034, -0.008, -0.098), (0, -0.034, -0.086)]),
    (-0.122, [(0, 0.091), (0.014, 0.090), (0.028, 0.086), (0.035, 0.079), (0.036, 0.054), (0.030, 0.004, -0.108), (0, -0.026, -0.092)]),
]
ROW_SOCKET, ROW_MOUTH, ROW_LIP = 3, 8, 9  # face bands (row i -> i + 1)
HEAD_X = 0.92  # skull + face narrower than the old template: a tall head, not a ball (jaw rows: 0.96)
hx = lambda y: HEAD_X if y >= -0.06 else 0.96 if y <= -0.10 else HEAD_X + (0.96 - HEAD_X) * (-0.06 - y) / 0.04
NECK = dict(a=0.036, front=0.042, back=0.040)  # neck stick: ellipse around z = -0.01: half width, front / back reach
NECK_Y = [-0.050, -0.132, -0.152, -0.172]  # top cap (inside the head), loop (kept by ref_body), tube, capped ring (cut off by ref_body)

# hair helmet: per column the hairline height, thickness at the crown / at the rim
HAIRLINE = {0: 0.066, 10: 0.065, 22: 0.060, 48: 0.040, 90: 0.016, 120: -0.012, 180: -0.060}  # arch over the ear, back down to the skull base
HAIR_TOP, HAIR_IN = 0.032, 0.002
HAIR_TH = [0.032, 0.026, 0.015, 0.005]  # thickness per hair row (crown -> rim): volume on top, close at the rim
HAIR_FRONT = [0.004, 0.006, 0.002, 0.0]  # extra at the front columns (0, 22): a raised front, not a bowl
HAIR_BACK = [0.002, 0.012, 0.012, 0.004]  # extra at the back columns (120, 180): the bulge over the skull base
HAIR_ROWS = 4
# hair points on the rim: (from col, to col) of a rim segment -> drop below the rim (m), sideways lean (+x), position
# along the segment (0 = from col, 1 = to col). Tips lie on the skin (projected), not in the air.
TEETH = {
    # fringe: falls to the character's right
    (-10, 0): (0.016, -0.010, 0.5), (0, 10): (0.012, -0.012, 0.5), (10, 22): (0.010, -0.008, 0.5),
    (22, 48): (0.008, -0.004, 0.5), (-22, -10): (0.016, -0.008, 0.5), (-48, -22): (0.012, -0.008, 0.5),
    # sideburns: a point down in front of the ear
    (48, 90): (0.046, 0.0, 0.8), (-48, -90): (0.046, 0.0, 0.8),
    # nape: the back panel ends in points at the neck
    (120, 180): (0.010, 0.0, 0.8), (-120, 180): (0.010, 0.0, 0.8),
}
SKIN = (0.80, 0.58, 0.45)
SOCKET = (0.60, 0.42, 0.34)
HAIR_COL = (0.27, 0.18, 0.11)
BROW_COL = (0.16, 0.10, 0.06)
HEAD_GEO = []  # head() fills (verts, faces) in head coords: ears are placed on it

# ears: the approved v13 trace (notes/parts/ear.md, head_template.EAR_TRACE / EAR_FACES), placed on this head with
# ray casts instead of the old head's SDF. Root just behind the jaw edge (col 90), top at the brow, lobe at the nose.
EAR_C = (0.0, -0.016, -0.040)  # ear frame centre start (x is found on the skin), head coords
EAR_ROOT_Z = -0.004  # root edge just behind the jaw edge (col 90)
EAR_SCALE = 0.92
EAR_FLARE = 28  # deg (v13 on the old head: 15): the planar head is flatter at the side, the ear must stand off more


def opts():
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="output/head-game/template/head_lp_v1.blend")
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    return p.parse_args(argv)


def bl(p):
    return (p[0], -p[2], p[1])


def full_ring(half):
    """Half points (col 0..180) -> the full ring: 0, L.., 180, R.. (mirror). Points (x, z) or (x, z, y)."""
    return half + [(-p[0],) + tuple(p[1:]) for p in half[-2:0:-1]]


def neck_half(y):
    out = []
    for c in COLS:
        t = math.radians(c)
        b = NECK["front"] if c < 90 else NECK["back"]
        out.append((NECK["a"] * math.sin(t), -0.01 + b * math.cos(t)))
    return out


def cap_faces(m, n):
    """Strip of quads closing a ring of n = 2 (m - 1) points (m half columns): tri, quads, tri."""
    return [[0, n - 1, 1]] + [[j, n - j, n - j - 1, j + 1] for j in range(1, m - 2)] + [[m - 2, n - m + 2, m - 1]]


def lin(c):
    return tuple(ch ** 2.2 for ch in c) + (1.0,)


def face_col(me, cols):
    a = me.color_attributes.new("Col", "FLOAT_COLOR", "FACE")
    for i, c in enumerate(cols):
        a.data[i].color = lin(c)
    me.color_attributes.active_color = a


def make(name, verts, faces, cols=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata([bl(v) for v in verts], [], faces)
    me.validate()
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(me)
    bm.free()
    if cols:
        face_col(me, cols(me))
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    for p in me.polygons:
        p.use_smooth = False
    return ob


def head():
    """Closed head (object Head): rows + crown cap + under-jaw cap. Rigid: 100 % on the head bone.
    Face zones: 1 eye socket, 2 mouth, 3 lower lip (colours: head_paint)."""
    rows = [(y, [(p[0] * hx(p[2] if len(p) > 2 else y),) + tuple(p[1:]) for p in h]) for y, h in ROWS]
    rings = [(y, full_ring(h)) for y, h in rows]
    verts, faces, zone = [], [], []
    for y, r in rings:
        verts += [(p[0], p[2] if len(p) > 2 else y, p[1]) for p in r]
    m = len(HCOLS)
    n = 2 * (m - 1)
    i22 = HCOLS.index(22)
    for i in range(len(rings) - 1):
        for k in range(n):
            a, b = i * n + k, i * n + (k + 1) % n
            faces.append([a, b, b + n, a + n])
            kl = min(k, n - 1 - k)  # left-side index of this face or of its mirror
            z = 0
            if i == ROW_SOCKET and kl == i22:
                z = 1
            elif i == ROW_MOUTH and kl < i22:
                z = 2
            elif i == ROW_LIP and kl < i22:
                z = 3
            zone.append(z)
    cap = cap_faces(m, n)
    faces += cap  # crown
    last = (len(rings) - 1) * n
    faces += [[last + i for i in f] for f in cap]  # under the jaw and the skull base
    zone += [0] * (2 * len(cap))
    pal = {0: SKIN, 1: SOCKET, 2: (0.30, 0.15, 0.13), 3: (0.70, 0.45, 0.39)}
    HEAD_GEO[:] = [verts, faces]
    ob = make("Head", verts, faces, lambda me: [pal[z] for z in zone])
    za = ob.data.attributes.new("zone", "INT", "FACE")  # read by head_paint
    for i, z in enumerate(zone):
        za.data[i].value = z
    return ob, rings


def neck():
    """The stick (template object Head_Main): a 10-vertex tube from inside the head down to the body contract
    (loop at -0.132, tube cut by ref_body below -0.142, capped ring at -0.172)."""
    n = 10
    verts, faces = [], []
    for y in NECK_Y:
        verts += [(x, y, z) for x, z in full_ring(neck_half(y))]
    for i in range(len(NECK_Y) - 1):
        for k in range(n):
            a, b = i * n + k, i * n + (k + 1) % n
            faces.append([a, b, b + n, a + n])
    faces += cap_faces(len(COLS), n)  # top, inside the head
    last = (len(NECK_Y) - 1) * n
    faces.append([last + k for k in range(n)])  # bottom (removed by ref_body: remove_neck_cap)
    return make("Head_Main", verts, faces, lambda me: [SKIN] * len(me.polygons))


def surface(rings, col_i, y):
    """Point on the head at ring index col_i and height y, linear between rows."""
    ys = [r[0] for r in rings]
    for i in range(len(ys) - 1):
        if ys[i] >= y >= ys[i + 1]:
            t = (ys[i] - y) / (ys[i] - ys[i + 1])
            (x0, z0), (x1, z1) = rings[i][1][col_i][:2], rings[i + 1][1][col_i][:2]
            return (x0 + (x1 - x0) * t, y, z0 + (z1 - z0) * t)
    x, z = rings[0][1][col_i][:2]
    return (x, ys[0], z)


def hair(rings):
    """Helmet: HAIR_ROWS rings from the crown to the hairline per column, pushed out from the head axis; inner wall
    2 mm into the skull, rim quads close it; front rim segments get a pointed fringe tip (closed wedge)."""
    ang = HCOLS + [-c for c in HCOLS[-2:0:-1]]
    n = len(ang)
    y_top = rings[0][0]

    def out_pt(p, th):
        x, y, z = p
        zc = -0.01
        d = math.hypot(x, z - zc) or 1.0
        return (x + x / d * th, y, z + (z - zc) / d * th)

    outer, inner = [], []
    for r in range(HAIR_ROWS):
        t = r / (HAIR_ROWS - 1)
        o_row, i_row = [], []
        for k in range(n):
            line = HAIRLINE[abs(ang[k])]
            y = y_top + (line - y_top) * t
            p = surface(rings, k, y)
            th = HAIR_TH[r] + (HAIR_FRONT[r] if abs(ang[k]) <= 22 else HAIR_BACK[r] if abs(ang[k]) >= 120 else 0.0)
            o_row.append(out_pt(p, th))
            i_row.append(out_pt(p, -HAIR_IN))
        outer.append(o_row)
        inner.append(i_row)
    # crown cap points: above the top ring
    verts, faces = [], []
    idx = {}

    def v(key, p):
        idx[key] = len(verts)
        verts.append(p)
        return idx[key]

    for r in range(HAIR_ROWS):
        for k in range(n):
            v(("o", r, k), outer[r][k])
            v(("i", r, k), inner[r][k])
    co = (0.0, y_top + HAIR_TOP - 0.002, -0.004)  # flat top
    ci = (0.0, y_top - HAIR_IN, -0.010)
    v("oc", co)
    v("ic", ci)
    for k in range(n):
        k2 = (k + 1) % n
        faces.append([idx["oc"], idx[("o", 0, k)], idx[("o", 0, k2)]])
        faces.append([idx["ic"], idx[("i", 0, k2)], idx[("i", 0, k)]])
        for r in range(HAIR_ROWS - 1):
            faces.append([idx[("o", r, k)], idx[("o", r + 1, k)], idx[("o", r + 1, k2)], idx[("o", r, k2)]])
            faces.append([idx[("i", r, k)], idx[("i", r, k2)], idx[("i", r + 1, k2)], idx[("i", r + 1, k)]])
        b = HAIR_ROWS - 1
        tip = TEETH.get((ang[k], ang[k2]))
        if tip is None and (ang[k2], ang[k]) in TEETH:
            d_, l_, t_ = TEETH[(ang[k2], ang[k])]
            tip = (d_, l_, 1 - t_)
        if tip:
            drop, lean, t = tip
            y_tip = (1 - t) * HAIRLINE[abs(ang[k])] + t * HAIRLINE[abs(ang[k2])] - drop
            pa, pb = surface(rings, k, y_tip), surface(rings, k2, y_tip)
            ps = tuple((1 - t) * pa[j] + t * pb[j] for j in range(3))
            po, pi = out_pt(ps, 0.004), out_pt(ps, -HAIR_IN)
            to = v(("to", k), (po[0] + lean, po[1], po[2]))
            ti = v(("ti", k), (pi[0] + lean, pi[1], pi[2]))
            faces.append([idx[("o", b, k)], to, idx[("o", b, k2)]])
            faces.append([idx[("i", b, k2)], ti, idx[("i", b, k)]])
            faces.append([idx[("o", b, k)], idx[("i", b, k)], ti, to])
            faces.append([to, ti, idx[("i", b, k2)], idx[("o", b, k2)]])
        else:
            faces.append([idx[("o", b, k)], idx[("i", b, k)], idx[("i", b, k2)], idx[("o", b, k2)]])
    ob = make("Hair", verts, faces, lambda me: [HAIR_COL] * len(me.polygons))
    ob["qa_asym"] = True
    ob["qa_tris_ok"] = True
    ob["paint_keep"] = True
    return ob


def box(name, corners_front, depth, cols):
    """Closed slab from 4 front corners (head coords), pushed back by depth along -z."""
    vs = list(corners_front) + [(x, y, z - depth) for x, y, z in corners_front]
    fs = [[0, 1, 2, 3], [7, 6, 5, 4], [0, 4, 5, 1], [1, 5, 6, 2], [2, 6, 7, 3], [3, 7, 4, 0]]
    return make(name, vs, fs, lambda me: [cols] * len(me.polygons))


def ears(rings):
    """v13 traced ears (half heart: rim, plateau, bowl, tragus block; n-gons kept whole) on both sides.
    The ear plane turns T.EAR_ANGLE forward; the root edge sits T.EAR_ROOT_SINK inside the skin; glued points
    (T.EAR_GLUE, back rings) are measured from the skin, hollows stay in front of it."""
    import numpy as np
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    import head_template as T
    verts, faces = HEAD_GEO
    bvh = BVHTree.FromPolygons([Vector(v) for v in verts], faces)
    a = math.radians(EAR_FLARE)
    nvec = np.array([math.cos(a), 0.0, math.sin(a)])
    tvec = np.array([-math.sin(a), 0.0, math.cos(a)])
    yvec = np.array([0.0, 1.0, 0.0])

    def surface(base):  # distance along nvec from each base point to the skin (ray from inside the head)
        out = []
        for b in base:
            o = b - 0.05 * nvec
            hit = bvh.ray_cast(Vector(o), Vector(nvec), 0.2)
            out.append((hit[3] - 0.05) if hit[0] is not None else 0.0)
        return np.array(out)

    c = np.array(EAR_C, dtype=float)
    for _ in range(4):  # push onto the skin, then slide so the root edge sits at EAR_ROOT_Z (pushing moves it)
        roots = np.array([c + T.EAR_U0 * tvec + v / 1000 * yvec for v in (20, 4, -14)])
        c = c + (float(surface(roots).mean()) - T.EAR_ROOT_SINK) * nvec
        c[2] += EAR_ROOT_Z - (c + T.EAR_U0 * tvec)[2]
    roots = np.array([c + T.EAR_U0 * tvec + v / 1000 * yvec for v in (20, 4, -14)])
    c = c + (float(surface(roots).mean()) - T.EAR_ROOT_SINK) * nvec

    def place(pts, front=True, skin=()):
        q = np.array(pts, dtype=float) / 1000
        q[:, :2] *= EAR_SCALE
        base = c + np.outer(T.EAR_U0 + q[:, 0], tvec) + np.outer(q[:, 1], yvec)
        sd = surface(base)
        n = q[:, 2] + np.maximum(0.0, sd - T.EAR_ROOT_SINK)
        if front:
            n = np.maximum(n, sd + T.EAR_FLOOR_MIN)
        for i in skin:
            n[i] = sd[i] + q[i, 2]
        return base + np.outer(n, nvec)

    names = list(T.EAR_TRACE)
    front = place([T.ear_uv(k) for k in names], skin=[names.index(k) for k in T.EAR_GLUE])
    out = np.array([T.ear_uv(k) for k in T.EAR_OUTLINE])
    mid = out[:, :2].mean(axis=0)
    m = len(T.EAR_OUTLINE)
    back = [place([(mid[0] + (u - mid[0]) * sc, mid[1] + (v - mid[1]) * sc, nn) for u, v, _ in out], False,
                  range(m) if i in T.EAR_SKIN_BACK else ()) for i, (sc, nn) in enumerate(T.EAR_BACK)]
    back_c = place([(mid[0], mid[1], T.EAR_BACK_C)], False, (0,))[0]
    at = {k: i for i, k in enumerate(names)}
    one_v = [tuple(p) for p in front]
    one_f, one_z = [], []
    for z, f in T.EAR_FACES:
        one_f.append([at[k] for k in f.split()])
        one_z.append(z)
    chain = [[at[k] for k in T.EAR_OUTLINE]]
    for r in back:
        chain.append(list(range(len(one_v), len(one_v) + m)))
        one_v += [tuple(p) for p in r]
    bci = len(one_v)
    one_v.append(tuple(back_c))
    for i in range(len(chain) - 1):
        for k in range(m):
            one_f.append([chain[i][(k + 1) % m], chain[i][k], chain[i + 1][k], chain[i + 1][(k + 1) % m]])
            one_z.append(0)
    for k in range(m):
        one_f.append([chain[-1][(k + 1) % m], chain[-1][k], bci])
        one_z.append(0)
    vs, fs, zs = [], [], []
    for sgn in (1, -1):
        o = len(vs)
        vs += [(sgn * x, y, z) for x, y, z in one_v]
        fs += [[o + i for i in f] for f in one_f]
        zs += one_z
    pal = {0: (0.80, 0.55, 0.43), 1: (0.86, 0.57, 0.45), 2: (0.82, 0.56, 0.44), 3: (0.70, 0.44, 0.36)}
    ob = make("Ears", vs, fs, lambda me: [pal[z] for z in zs])
    za = ob.data.attributes.new("ear_zone", "INT", "FACE")  # head_paint EAR_ZONE colours
    for i, z in enumerate(zs):
        za.data[i].value = z
    return ob


def brows(rings):
    out = []
    for s, nm in ((1, "Eyebrow_L"), (-1, "Eyebrow_R")):
        # on the brow row, inner end higher toward the nose bridge
        pts = [(0.012, 0.024, 0.104), (0.052, 0.022, 0.089), (0.054, 0.017, 0.088), (0.012, 0.018, 0.104)]
        out.append(box(nm, [(s * x * HEAD_X, y, z) for x, y, z in pts], 0.006, BROW_COL))
    return out


def main():
    a = opts()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    h, rings = head()
    neck()
    hair(rings)
    ears(rings)
    brows(rings)
    out = os.path.abspath(a.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=out)
    print("HEAD_LP", len(h.data.polygons), "faces", out)


if __name__ == "__main__":
    main()
