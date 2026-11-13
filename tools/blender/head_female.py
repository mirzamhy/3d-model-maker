"""Female heads: v17 traced head with female landmark offsets, variants with their own face, hair style and colours.

Reference: notes/attachments/ref/survivor_f/ (front, head wire, turn sheet). Style kept close to the male v17:
same big planes, same lips / eye slits / ears; only the landmarks move (narrow pointed chin, slim jaw, smaller
nose, thin neck). Hair = the traced mass (head_trace.build_hair) + pieces: bun, ponytail, bob with fringe, long
loose curtain, braid, pigtails, front locks. Hair detail stays big planes: ridged tubes (strand clumps), alternating
lit / shaded strand faces, cut tips, hair ties.

blender -b --factory-startup -P tools/blender/head_female.py -- --ears output/head-game/template/head_lp_v6.blend \
    --out output/head-game/template/head_f1.blend --sheet notes/attachments/qa/female_head_v1.png [--variant v1]
    [--all notes/attachments/qa/female_heads_all.png]   (every variant: rows x 4 views, .blend per variant)
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

# hair combed back tight: thin smooth mass, no spikes
HP_F = {
    "top": (0.0, 0.25, -1.0), "side": (0.0, 0.6, -0.8), "back": (0.0, 0.7, -0.7),
    "thick": (0.006, 0.006, 0.005, 0.007), "lump": 0.12, "keep": 0.0, "nape": (0.0, 0.0),
}

SKIN_F = np.array([0.86, 0.66, 0.50]) ** 2.2
HAIR_F = np.array([0.36, 0.22, 0.13]) ** 2.2

# variants (user: "coba bikin variasi lain yang cewek", then "perbanyak model muka cewe dan rambutnya kemudian
# warnanya"). tone = skin factor (same as head_paint PAINT_TONE), hair_col / tie in sRGB, face = extra landmark
# offsets on top of FEMALE, hp = hair mass parameters on top of HP_F.
VARIANTS = {
    "v1": dict(hair="bun", locks=True, tone=(1, 1, 1), hair_col=(0.36, 0.22, 0.13), face={}),
    # v2: high ponytail, black hair, front locks (without them the square hairline read male), darker skin, fuller
    # cheek and rounder chin
    "v2": dict(hair="ponytail", locks=True, tone=(0.72, 0.67, 0.64), hair_col=(0.15, 0.12, 0.10), tie=(0.45, 0.10, 0.09),
               face={"CH_SIDE": (8, 0, 0), "CH_TOP": (6, 0, 0), "J_MID": (8, 0, 0), "M_CHB": (0, 2, 0),
                     "M_CHIN": (0, 0, 1), "MC_OUT": (6, 0, -2), "C_BONE": (4, 0, 0), "N_WING": (3, 0, 0),
                     "L_CORNER": (3, 0, 0)}),
    # v3: auburn bob to the jaw with a fringe, light skin, round face
    "v3": dict(hair="bob", locks=False, tone=(1.05, 1.0, 0.96), hair_col=(0.50, 0.22, 0.11),
               face={"CH_SIDE": (10, 0, 0), "CH_TOP": (6, 0, 0), "J_MID": (12, 0, 0), "MC_OUT": (8, 0, -2),
                     "M_CHB": (0, 4, 0), "M_CHIN": (0, 2, 0), "C_BONE": (2, 4, 0), "M_TIP": (0, 2, -3)}),
    # v4: long loose dirty blonde hair, middle parting, long narrow face, high cheekbones
    "v4": dict(hair="long", locks=True, tone=(0.95, 0.92, 0.88), hair_col=(0.64, 0.50, 0.30), hp={"mid": 1.0},
               face={"C_BONE": (6, -6, 0), "CH_SIDE": (-4, 4, 0), "M_CHB": (0, 8, 0), "M_CHIN": (0, 6, 0),
                     "CH_TOP": (-2, 4, 0), "J_MID": (-4, 4, 0), "N_WING": (-2, 0, 0)}),
    # v5: one braid down the back, near black hair, red tie, tan skin, wide cheek, small flat nose
    "v5": dict(hair="braid", locks=True, tone=(0.84, 0.76, 0.66), hair_col=(0.11, 0.09, 0.08), tie=(0.55, 0.12, 0.10),
               face={"C_BONE": (8, 0, 0), "M_TIP": (0, 0, 6), "N_TIPS": (0, 0, 5), "N_WING": (3, 0, 2),
                     "MC_OUT": (4, 0, 0), "B_TOP_MID": (0, 2, 2), "J_MID": (4, 0, 0)}),
    # v6: pixie undercut (sides shaved, top swept with short spikes), ash hair, dark skin, stronger jaw
    "v6": dict(hair="pixie", locks=False, tone=(0.52, 0.43, 0.38), hair_col=(0.70, 0.68, 0.64),
               hp={"top": (0.8, 0.3, 0.5), "thick": (0.008, 0.018, 0.006, 0.006), "lump": 0.3, "keep": 0.8,
                   "spike": {"quiff": (0.030, 0.6), "crown": (0.024, 0.5), "side": (0.014, 0.3), "back": (0.012, 0.2)},
                   "nape": (0.008, 0.004), "cut_y": 0.03, "cut_k": 0.15},
               face={"J_ANG": (6, 0, 0), "CH_SIDE": (4, 0, 0), "J_MID": (6, 0, 0), "C_BONE": (2, -2, 0)}),
    # v7: two low pigtails behind the ears, chestnut, light warm skin, small chin
    "v7": dict(hair="pigtails", locks=True, tone=(0.98, 0.93, 0.88), hair_col=(0.34, 0.20, 0.11),
               tie=(0.12, 0.12, 0.14),
               face={"CH_SIDE": (-2, 0, 0), "M_CHB": (0, -2, 0), "MC_OUT": (4, 0, 0), "C_BONE": (2, 0, 0),
                     "L_CORNER": (-2, 0, 0)}),
}

# per-face colour of the added hair pieces, in creation order: float = hair colour factor, tuple = own sRGB colour
TONES = []


def F(bm, vs, tone=1.0):
    TONES.append(tone)
    return bm.faces.new(vs)


def tube(bm, path, rad, sides=6, ridge=0.12, wobble=0.0, twist=0.0, tone=1.0, cap=True):
    """Tube of rings along a path (head coords: x, y up, z forward), tip where rad = 0. Detail: ridge = every other
    ring corner pushed out (strand clumps, alternating lit / shaded planes); wobble + twist = rings shifted side to
    side and turned (braid lumps)."""
    rings = []
    for i, (p, r) in enumerate(zip(path, rad)):
        p = np.array(p, float)
        if r == 0:
            rings.append([bm.verts.new(ht.blender_co(p))])
            continue
        q = np.array(path[min(i + 1, len(path) - 1)], float) - np.array(path[max(i - 1, 0)], float)
        t = q / np.linalg.norm(q)
        ref = np.array([1.0, 0, 0]) if abs(t[0]) < 0.9 else np.array([0, 1.0, 0])
        u = np.cross(t, ref); u /= np.linalg.norm(u)
        w = np.cross(t, u)
        c = p + u * wobble * r * (1 if i % 2 else -1)
        ring = []
        for k in range(sides):
            an = 2 * math.pi * k / sides + 0.26 + twist * i
            rr = r * (1 + ridge * (1 if k % 2 else -1)) * (0.95 + 0.1 * ht._hash(p * 7.1 + k))
            ring.append(bm.verts.new(ht.blender_co(c + (u * math.cos(an) + w * math.sin(an)) * rr)))
        rings.append(ring)
    if cap and len(rings[0]) > 1:
        F(bm, rings[0][::-1], tone)
    for a, b in zip(rings, rings[1:]):
        n = len(a)
        for k in range(n):
            k2 = (k + 1) % n
            tk = tone if isinstance(tone, tuple) else tone * (1.0 if k % 2 else 0.82)
            if len(b) == 1:
                F(bm, [a[k], a[k2], b[0]], tk)
            else:
                F(bm, [a[k], a[k2], b[k2], b[k]], tk)
    if len(rings[-1]) > 1:
        F(bm, rings[-1], tone)


def tie(bm, p, d, r, col):
    """Hair tie: a short ring band around a strand at p along d."""
    p, d = np.array(p, float), np.array(d, float) / np.linalg.norm(d)
    tube(bm, [p - d * 0.006, p + d * 0.006], [r, r], sides=6, ridge=0.0, tone=tuple(col))


def curtain(bm, y_rows, rx, rz, th_max, tips=0.022, curl=1.0, cz=-0.015, cols=9):
    """Loose hair hanging round the back and sides of the head: rows of points on ellipses (rx, rz per row) round a
    vertical axis, theta 0 = back, +-th_max at the sides. Strand detail: every other column pushed out (ridge) and
    the bottom edge cut in alternating lengths (tips). Closed slab, wall ~7 mm."""
    th = np.radians(np.linspace(-th_max, th_max, cols))
    n_rows = len(y_rows)
    outer, inner = [], []
    for i, y in enumerate(y_rows):
        ro, ri = [], []
        for j, a in enumerate(th):
            ridge = 1.0 + (0.06 if j % 2 else 0.0)
            yy = y - (tips * (1 if j % 2 == 0 else 0.35) if i == n_rows - 1 else 0.0)
            k = curl if i == n_rows - 1 else 1.0
            px, pz = rx[i] * ridge * k * math.sin(a), cz - rz[i] * ridge * k * math.cos(a)
            ro.append(bm.verts.new(ht.blender_co((px, yy, pz))))
            ri.append(bm.verts.new(ht.blender_co((px * 0.92, yy, cz + (pz - cz) * 0.93))))
        outer.append(ro)
        inner.append(ri)
    for i in range(n_rows - 1):
        for j in range(cols - 1):
            F(bm, [outer[i][j], outer[i + 1][j], outer[i + 1][j + 1], outer[i][j + 1]], 1.0 if j % 2 else 0.86)
            F(bm, [inner[i][j], inner[i][j + 1], inner[i + 1][j + 1], inner[i + 1][j]], 0.7)
        for j in (0, cols - 1):
            F(bm, [outer[i][j], inner[i][j], inner[i + 1][j], outer[i + 1][j]], 0.8)
    for i in (0, n_rows - 1):
        for j in range(cols - 1):
            F(bm, [outer[i][j], outer[i][j + 1], inner[i][j + 1], inner[i][j]], 0.8)


def strand(bm, path, width, thick=0.006, tone=1.0):
    """Flat tapering strand (fringe) along a path in front of the face: diamond section, ridge in the middle."""
    rows = []
    for p, w in zip(path, width):
        p = np.array(p, float)
        if w == 0:
            rows.append([bm.verts.new(ht.blender_co(p))])
            continue
        rows.append([bm.verts.new(ht.blender_co(p + np.array([-w / 2, 0, 0]))),
                     bm.verts.new(ht.blender_co(p + np.array([0, 0, thick]))),
                     bm.verts.new(ht.blender_co(p + np.array([w / 2, 0, 0]))),
                     bm.verts.new(ht.blender_co(p + np.array([0, 0, -thick * 0.4])))])
    for a, b in zip(rows, rows[1:]):
        for k in range(4):
            k2 = (k + 1) % 4
            tk = tone * (1.0 if k in (0, 3) else 0.85)
            if len(b) == 1:
                F(bm, [a[k], a[k2], b[0]], tk)
            else:
                F(bm, [a[k], a[k2], b[k2], b[k]], tk)
    F(bm, rows[0][::-1], tone)
    if len(rows[-1]) > 1:
        F(bm, rows[-1], tone * 0.9)   # blunt cut end


def bun(bm, V=None):
    """Faceted bun on the top of the back of the head (icosphere, one subdivision = 80 tris), squashed a little;
    faces alternately lit / shaded (twisted strands in the knot)."""
    res = bmesh.ops.create_icosphere(bm, subdivisions=1, radius=1.0)
    c = np.array([0.0, 0.118, -0.062])        # head coords (crown top y 0.103 at z 0.008); v1 0.098 sat too low
    r = np.array([0.056, 0.052, 0.056])       # reference bun ~ half the skull width
    for v in res["verts"]:
        p = np.array([v.co.x, v.co.y, v.co.z])   # unit sphere (treated as head coords)
        jitter = 0.92 + 0.16 * ht._hash(p * 3.3)
        h = c + p * r * jitter
        v.co = ht.blender_co(h)
    n = len({f for v in res["verts"] for f in v.link_faces})
    TONES.extend(1.0 if ht._hash(np.array([i * 0.37, 1.3, 2.1])) > 0.4 else 0.84 for i in range(n))
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
                F(bm, [a[k], a[k2], b[0]], 1.0 if k % 2 else 0.86)
            else:
                F(bm, [a[k], a[k2], b[k2], b[k]], 1.0 if k % 2 else 0.86)
    F(bm, verts[0][::-1])


def ponytail(bm, V=None):
    """High ponytail: a gathered knot at the back of the crown, then a tapering ridged tail down the back of the
    head (big planes, 5 rings + tip), hair tie at the knot."""
    path = [(0.0, 0.090, -0.078), (0.0, 0.075, -0.112), (0.0, 0.020, -0.128), (0.0, -0.050, -0.122),
            (0.0, -0.110, -0.104), (0.0, -0.150, -0.090)]
    tube(bm, path, [0.024, 0.030, 0.030, 0.024, 0.014, 0.0], sides=6, ridge=0.14)
    if V and V.get("tie"):
        tie(bm, (0.0, 0.084, -0.094), (0, -0.4, -1), 0.026, V["tie"])


def bob(bm, V):
    """Jaw-length bob, wraps forward to the cheeks, ends curled in a little; fringe of five strands."""
    curtain(bm, [0.05, 0.0, -0.05, -0.095], rx=[0.074, 0.090, 0.094, 0.094], rz=[0.100, 0.118, 0.118, 0.112],
            th_max=118, tips=0.012, curl=0.9, cols=11)
    for x in (-0.040, -0.020, 0.0, 0.020, 0.040):
        top = (x * 0.9, 0.080, 0.080 - abs(x) * 0.3)
        mid = (x, 0.050, 0.110 - abs(x) * 0.35)
        # blunt cut ends at slightly different heights (pointed tips read as a saw)
        end = (x * 1.05, 0.024 - 0.005 * ht._hash(np.array([x * 50, 1, 2])), 0.114 - abs(x) * 0.4)
        strand(bm, [top, mid, end], [0.026, 0.025, 0.021])


def long_hair(bm, V):
    """Loose hair to the shoulder blades, behind the ears, cut tips."""
    curtain(bm, [0.05, 0.0, -0.08, -0.16, -0.235], rx=[0.074, 0.090, 0.094, 0.100, 0.104],
            rz=[0.100, 0.118, 0.115, 0.112, 0.108], th_max=100, tips=0.03, cols=11)


def braid(bm, V):
    """Single braid from the back of the head down the back: lumpy twisted tube, tie, short tuft."""
    path = [(0.0, 0.03, -0.100), (0.0, -0.03, -0.118), (0.0, -0.09, -0.124), (0.0, -0.15, -0.128),
            (0.0, -0.21, -0.130), (0.0, -0.265, -0.130)]
    tube(bm, path, [0.030, 0.026, 0.024, 0.022, 0.019, 0.015], sides=5, ridge=0.18, wobble=0.25, twist=0.63)
    tie(bm, (0.0, -0.272, -0.130), (0, 1, 0), 0.016, V["tie"])
    tube(bm, [(0.0, -0.278, -0.130), (0.0, -0.30, -0.131), (0.0, -0.325, -0.128)], [0.012, 0.018, 0.0], sides=5,
         ridge=0.25)


def pigtails(bm, V):
    """Two low pigtails behind the ears, tied at the root."""
    for sx in (1, -1):
        # hang down behind the ear, close to the neck (further out they read as wings from the front)
        path = [(sx * 0.060, -0.010, -0.080), (sx * 0.072, -0.035, -0.084), (sx * 0.078, -0.08, -0.080),
                (sx * 0.080, -0.13, -0.072), (sx * 0.080, -0.175, -0.066)]
        tube(bm, path, [0.022, 0.026, 0.024, 0.016, 0.0], sides=6, ridge=0.16)
        tie(bm, (sx * 0.068, -0.026, -0.083), (sx * 0.4, -1, 0), 0.020, V["tie"])


STYLES = {"bun": bun, "ponytail": ponytail, "bob": bob, "long": long_hair, "braid": braid, "pigtails": pigtails,
          "pixie": lambda bm, V: None}


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
    ht.HP.update(V.get("hp", {}))
    head = ht.build_head()
    hair = ht.build_hair(head)
    eyes = ht.eye_slits()
    ears = ears_base.copy(); ears.data = ears_base.data.copy(); ears.hide_render = False
    bpy.context.scene.collection.objects.link(ears)
    bpy.data.objects.remove(ears_base)
    # hair pieces added to the hair mesh
    bm = bmesh.new(); bm.from_mesh(hair.data)
    n0 = len(bm.faces)
    TONES.clear()
    STYLES[V["hair"]](bm, V)
    if V["locks"]:
        for sx in (1, -1):
            lock(bm, sx)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(hair.data); bm.free()
    for p in hair.data.polygons:
        p.use_smooth = False
    for ob, nm in ((head, "Head"), (hair, "Hair"), (eyes, "Eyes"), (ears, "Ears")):
        ob.name = nm; ob.data.name = nm
    # colours (FACE Col, ratios kept for the game: skin zones = skin x ratio)
    tone = np.array(V["tone"]) ** 2.2
    hair_f = np.array(V["hair_col"]) ** 2.2
    tones = list(TONES)

    def hair_col(i, old):
        if i < n0:   # traced mass: small per-face jitter, the strand planes read apart instead of one flat shell
            return hair_f * (0.93 + 0.12 * ht._hash(np.array([i * 0.731, 0.29, 1.7])))
        t = tones[i - n0] if i - n0 < len(tones) else 0.9
        return np.array(t) ** 2.2 if isinstance(t, tuple) else hair_f * 0.95 * t
    hm.set_col(head, lambda i, old: old / ht.SKIN * SKIN_F * tone)
    hm.set_col(ears, lambda i, old: SKIN_F * tone)
    hm.set_col(hair, hair_col)
    print("FEMALE", variant, "head tris", len(head.data.polygons), "hair faces", len(hair.data.polygons),
          "hair tris", sum(len(p.vertices) - 2 for p in hair.data.polygons))
    return head, hair, eyes, ears


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--ears", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--sheet", default="")
    ap.add_argument("--variant", default="v1", choices=sorted(VARIANTS))
    ap.add_argument("--all", default="", help="sheet of every variant (rows) x 4 views; --out is then a folder")
    a = ap.parse_args(argv)
    if a.all:
        tiles = []
        os.makedirs(os.path.abspath(a.out), exist_ok=True)
        tmp = os.path.abspath(a.all) + ".tmp.png"
        for v in sorted(VARIANTS):
            build(a.ears, v)
            bpy.ops.wm.save_as_mainfile(filepath=os.path.join(os.path.abspath(a.out), f"head_f_{v}.blend"))
            sc, cam = hm.setup_render(320)
            tiles += [hm.render_view(sc, cam, ang, tmp) for ang in (0, 35, 90, 160)]
        os.remove(tmp)
        hm.save_sheet(tiles, 4, os.path.abspath(a.all))
        print("SAVED", a.all)
        return
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
