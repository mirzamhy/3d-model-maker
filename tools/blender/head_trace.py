"""Head v17: traced vertex by vertex from the survivor reference (no ring loft).

Every vertex = one landmark read off two frames of the turntable video:
  front f01 (notes/attachments/ref/survivor_ref/full2/f01.jpg, crop x 650.., grid 50 px): half-width xpx from the
      nose line, height ypx;
  side  f06 (same folder, crop x 550..): depth dpx (smaller = more forward). Side heights were mapped to front
      heights with yf = 470 + (ys - 490) * 1.085 (brow and chin line up).
Faces are triangles placed along the anatomy lines of the reference wire (brow shelf, nose bridge, cheekbone
diagonal, nasolabial fan, lip lines, jaw line, under-jaw plane). Half head is listed, the other half mirrored.

blender -b --factory-startup -P head_trace.py -- --ears <head_lp_v6.blend> --out <head_lp_v17.blend>
Output objects (head coords x, y up, z fwd -> Blender (x, -z, y)): Head (skin + zones, Col face colour),
Ears (from v16f, moved to the traced place), Eyes (dark slits, faceLP).
"""
import sys, argparse
import bpy, bmesh
import numpy as np
from mathutils import Vector

S = 0.0003            # m per front px (skull top..chin 745 px = 0.222 m, same size as v16f)
SD = 0.000325         # m per side px (side frame is ~8 % smaller)
Y0, D0 = 915, 444     # chin bottom (front px) -> y -0.122 ; neck centre (side px) -> z -0.01


def to_m(xpx, ypx, dpx):
    return (xpx * S, (Y0 - ypx) * S - 0.122, (D0 - dpx) * SD)


# name: (half-width px, height px, depth px)
TRACE = {
    # midline profile (side f06)
    "M_HAIR": (0, 331, 140), "M_FORE": (0, 400, 125), "M_GLAB": (0, 474, 117), "M_ROOT": (0, 493, 122),
    "M_TIP": (0, 650, 65), "M_SUB": (0, 687, 112), "M_CUPID": (0, 741, 100), "M_MOUTH": (0, 767, 125),
    "M_LLIP": (0, 790, 108), "M_LLB": (0, 805, 124), "M_CHG": (0, 825, 136), "M_CHIN": (0, 870, 132),
    "M_CHB": (0, 917, 150), "M_THROAT": (0, 925, 295), "N0": (0, 1010, 305),
    "M_FTOP": (0, 250, 185), "M_CROWN": (0, 165, 420), "M_BTOP": (0, 230, 680), "M_OCC": (0, 430, 790),
    "M_BLOW": (0, 675, 750), "M_NAPE": (0, 790, 670), "N4": (0, 1010, 690),
    # forehead, brow shelf (front f01: brow top edge y 457-476, eye groove y 493)
    "F_TOP1": (110, 305, 195), "F_TOP2": (185, 320, 255), "F_TEMPLE": (213, 424, 320),
    "B_TOP_IN": (35, 476, 118), "B_TOP_MID": (114, 466, 138), "B_TOP_OUT": (186, 457, 200),
    "E_MID": (115, 494, 168), "E_OUT": (202, 493, 250),
    # nose: flat bridge plane 2 x 22 px, sides to 44 px, wing 41 px
    "N_BR_TOP": (22, 500, 122), "N_BR_BOT": (22, 640, 74), "N_SIDE_TOP": (42, 502, 142),
    "N_WING": (41, 668, 127), "N_TIPS": (18, 666, 88),
    # cheek: cheekbone fan point, side plane, nasolabial
    "C_BONE": (187, 642, 240), "C_BACK": (210, 608, 380), "MC_UP": (105, 745, 175), "MC_OUT": (131, 780, 205),
    # lips (upper lip M, lower lip thicker)
    "L_CUP": (22, 732, 100), "L_UOUT": (50, 745, 110), "L_LINE": (45, 768, 128), "L_CORNER": (93, 769, 165),
    "L_LMID": (45, 787, 114), "L_LBOT": (45, 803, 125),
    # chin (square, 2 x 80 px) and jaw line to the angle under the ear
    "CH_TOP": (50, 832, 140), "CH_SIDE": (80, 902, 158), "J_MID": (140, 855, 300), "J_ANG": (206, 800, 440),
    # side of head, ear area, under jaw, neck (thick: 182 px half-width)
    "SB_TOP": (215, 475, 365), "EAR_C": (232, 560, 530), "LOBE": (220, 690, 460), "NK_F": (120, 905, 330),
    "NK_EAR": (182, 806, 470), "NK_BACK": (140, 770, 640),
    "N1": (130, 1010, 335), "N2": (182, 1010, 490), "N3": (130, 1010, 645),
    # skull under the hair (round, full at the back)
    "SK_FT": (110, 220, 250), "SK_TS": (150, 185, 430), "SK_SH": (215, 285, 430), "SK_SIDE": (230, 420, 500),
    "SK_BH": (150, 255, 685), "SK_BK": (195, 440, 745), "SK_BEHIND": (220, 622, 588), "SK_BACK_LO": (165, 685, 715),
    # hair line around the ear (side f06): sideburn strip in front, over the ear top, down behind it
    "SB_BACK": (227, 590, 476), "E_TOP_F": (230, 492, 478), "E_TOP_B": (229, 492, 590), "E_BACK_LO": (212, 690, 598),
    # ^ hair edge sits right on the ear (ear spans depth 471-608, height 468-702): no skin strip, top of the ear tucked under
}

FACES = [
    # forehead: big planes from hairline points down to the brow shelf
    ("M_HAIR", "F_TOP1", "M_FORE"), ("M_FORE", "F_TOP1", "B_TOP_IN"), ("M_FORE", "B_TOP_IN", "M_GLAB"),
    ("F_TOP1", "B_TOP_MID", "B_TOP_IN"), ("F_TOP1", "F_TOP2", "B_TOP_MID"), ("F_TOP2", "B_TOP_OUT", "B_TOP_MID"),
    ("F_TOP2", "F_TEMPLE", "B_TOP_OUT"),
    # glabella + nose root
    ("M_GLAB", "B_TOP_IN", "M_ROOT"), ("B_TOP_IN", "N_BR_TOP", "M_ROOT"), ("B_TOP_IN", "N_SIDE_TOP", "N_BR_TOP"),
    # brow underside (eye groove, faces down)
    ("B_TOP_IN", "B_TOP_MID", "E_MID"), ("B_TOP_IN", "E_MID", "N_SIDE_TOP"),
    ("B_TOP_MID", "B_TOP_OUT", "E_OUT"), ("B_TOP_MID", "E_OUT", "E_MID"),
    ("F_TEMPLE", "E_OUT", "B_TOP_OUT"), ("F_TEMPLE", "SB_TOP", "E_OUT"),
    # nose bridge plane, sides, tip and underside
    ("M_ROOT", "N_BR_TOP", "N_BR_BOT"), ("M_ROOT", "N_BR_BOT", "M_TIP"),
    ("N_BR_TOP", "N_SIDE_TOP", "N_WING"), ("N_BR_TOP", "N_WING", "N_BR_BOT"),
    ("M_TIP", "N_BR_BOT", "N_TIPS"), ("N_BR_BOT", "N_WING", "N_TIPS"), ("M_TIP", "N_TIPS", "M_SUB"),
    ("N_TIPS", "N_WING", "M_SUB"),
    # eye plane + cheek fan from the cheekbone point
    ("N_SIDE_TOP", "E_MID", "C_BONE"), ("E_MID", "E_OUT", "C_BONE"), ("N_SIDE_TOP", "C_BONE", "N_WING"),
    ("N_WING", "C_BONE", "MC_UP"), ("C_BONE", "MC_OUT", "MC_UP"), ("MC_UP", "MC_OUT", "L_CORNER"),
    ("E_OUT", "SB_TOP", "C_BACK"), ("E_OUT", "C_BACK", "C_BONE"), ("C_BONE", "C_BACK", "MC_OUT"),
    # philtrum + upper lip
    ("M_SUB", "N_WING", "L_CUP"), ("M_SUB", "L_CUP", "M_CUPID"), ("N_WING", "L_UOUT", "L_CUP"),
    ("N_WING", "MC_UP", "L_UOUT"), ("MC_UP", "L_CORNER", "L_UOUT"),
    ("M_CUPID", "L_CUP", "L_LINE"), ("M_CUPID", "L_LINE", "M_MOUTH"), ("L_CUP", "L_UOUT", "L_LINE"),
    ("L_UOUT", "L_CORNER", "L_LINE"),
    # lower lip
    ("M_MOUTH", "L_LINE", "L_LMID"), ("M_MOUTH", "L_LMID", "M_LLIP"), ("L_LINE", "L_CORNER", "L_LMID"),
    ("M_LLIP", "L_LMID", "L_LBOT"), ("M_LLIP", "L_LBOT", "M_LLB"), ("L_LMID", "L_CORNER", "L_LBOT"),
    # chin plane + fan from the mouth corner
    ("M_LLB", "L_LBOT", "CH_TOP"), ("M_LLB", "CH_TOP", "M_CHG"), ("M_CHG", "CH_TOP", "M_CHIN"),
    ("CH_TOP", "CH_SIDE", "M_CHIN"), ("M_CHIN", "CH_SIDE", "M_CHB"),
    ("L_CORNER", "CH_TOP", "L_LBOT"), ("L_CORNER", "MC_OUT", "CH_TOP"), ("MC_OUT", "CH_SIDE", "CH_TOP"),
    ("MC_OUT", "J_MID", "CH_SIDE"),
    # jaw side
    ("C_BACK", "J_ANG", "MC_OUT"), ("MC_OUT", "J_ANG", "J_MID"), ("C_BACK", "LOBE", "J_ANG"),
    # under jaw (one long dark plane chin -> neck)
    ("M_CHB", "CH_SIDE", "M_THROAT"), ("CH_SIDE", "NK_F", "M_THROAT"), ("CH_SIDE", "J_MID", "NK_F"),
    ("J_MID", "J_ANG", "NK_F"), ("J_ANG", "NK_EAR", "NK_F"),
    # neck stub
    ("N0", "M_THROAT", "NK_F"), ("N0", "NK_F", "N1"), ("N1", "NK_F", "NK_EAR"), ("N1", "NK_EAR", "N2"),
    ("N2", "NK_EAR", "NK_BACK"), ("N2", "NK_BACK", "N3"), ("N3", "NK_BACK", "M_NAPE"), ("N3", "M_NAPE", "N4"),
    ("N0", "N1", "N2"), ("N0", "N2", "N3"), ("N0", "N3", "N4"),
    # side of head: hair line goes round the ear (sideburn strip, over the top, down behind)
    ("F_TEMPLE", "SK_SIDE", "SB_TOP"), ("SB_TOP", "SK_SIDE", "E_TOP_F"), ("SB_TOP", "E_TOP_F", "SB_BACK"),
    ("SB_TOP", "SB_BACK", "C_BACK"), ("SK_SIDE", "E_TOP_B", "E_TOP_F"), ("SK_SIDE", "SK_BK", "E_TOP_B"),
    ("E_TOP_B", "SK_BK", "SK_BEHIND"), ("SK_BEHIND", "SK_BACK_LO", "E_BACK_LO"),
    # skin under the ear
    ("C_BACK", "SB_BACK", "EAR_C"), ("SB_BACK", "E_TOP_F", "EAR_C"), ("E_TOP_F", "E_TOP_B", "EAR_C"),
    ("E_TOP_B", "SK_BEHIND", "EAR_C"), ("EAR_C", "SK_BEHIND", "E_BACK_LO"), ("EAR_C", "E_BACK_LO", "LOBE"),
    ("C_BACK", "EAR_C", "LOBE"),
    # behind the ear, nape
    ("LOBE", "NK_EAR", "J_ANG"), ("LOBE", "E_BACK_LO", "NK_EAR"), ("E_BACK_LO", "NK_BACK", "NK_EAR"),
    ("E_BACK_LO", "SK_BACK_LO", "NK_BACK"), ("SK_BACK_LO", "M_NAPE", "NK_BACK"), ("SK_BACK_LO", "M_BLOW", "M_NAPE"),
    # skull
    ("M_HAIR", "M_FTOP", "F_TOP1"), ("M_FTOP", "SK_FT", "F_TOP1"), ("M_FTOP", "M_CROWN", "SK_FT"),
    ("SK_FT", "M_CROWN", "SK_TS"), ("F_TOP1", "SK_FT", "F_TOP2"), ("SK_FT", "SK_TS", "F_TOP2"),
    ("F_TOP2", "SK_TS", "SK_SH"), ("F_TOP2", "SK_SH", "F_TEMPLE"), ("F_TEMPLE", "SK_SH", "SK_SIDE"),
    ("M_CROWN", "M_BTOP", "SK_TS"), ("SK_TS", "M_BTOP", "SK_BH"), ("SK_TS", "SK_BH", "SK_SH"),
    ("SK_SH", "SK_BH", "SK_BK"), ("SK_SH", "SK_BK", "SK_SIDE"), ("M_BTOP", "M_OCC", "SK_BH"),
    ("SK_BH", "M_OCC", "SK_BK"), ("M_OCC", "M_BLOW", "SK_BK"), ("SK_BK", "M_BLOW", "SK_BACK_LO"),
    ("SK_BK", "SK_BACK_LO", "SK_BEHIND"),
]

SKIN = np.array([0.80, 0.58, 0.45]) ** 2.2
# face colour = skin x ratio (game divides by skin again, so ratios survive the per-actor tint)
ZONES = {
    "groove": (0.62, {("B_TOP_IN", "B_TOP_MID", "E_MID"), ("B_TOP_IN", "E_MID", "N_SIDE_TOP"),
                      ("B_TOP_MID", "B_TOP_OUT", "E_OUT"), ("B_TOP_MID", "E_OUT", "E_MID")}),
    "nostril": (0.55, {("M_TIP", "N_TIPS", "M_SUB"), ("N_TIPS", "N_WING", "M_SUB")}),
    "lip": (None, {("M_CUPID", "L_CUP", "L_LINE"), ("M_CUPID", "L_LINE", "M_MOUTH"), ("L_CUP", "L_UOUT", "L_LINE"),
                   ("L_UOUT", "L_CORNER", "L_LINE"), ("M_MOUTH", "L_LINE", "L_LMID"), ("M_MOUTH", "L_LMID", "M_LLIP"),
                   ("L_LINE", "L_CORNER", "L_LMID"), ("M_LLIP", "L_LMID", "L_LBOT"), ("M_LLIP", "L_LBOT", "M_LLB"),
                   ("L_LMID", "L_CORNER", "L_LBOT")}),
}
LIP = np.array([0.681, 0.279, 0.173])
MOUTH_LINE = np.array([0.456, 0.173, 0.126])


def face_col(tri):
    for zone, (k, tris) in ZONES.items():
        if tri in tris:
            if zone == "lip":
                return MOUTH_LINE if "L_LINE" in tri and "M_MOUTH" in tri else LIP
            return SKIN * k
    return SKIN


def blender_co(p):
    return Vector((p[0], -p[2], p[1]))


def build_head():
    names = list(TRACE)
    pos, idx = [], {}
    for n in names:
        idx[(n, 1)] = len(pos)
        pos.append(to_m(*TRACE[n]))
    for n in names:
        if TRACE[n][0] == 0:
            idx[(n, -1)] = idx[(n, 1)]
        else:
            idx[(n, -1)] = len(pos)
            x, y, z = to_m(*TRACE[n])
            pos.append((-x, y, z))
    faces, cols = [], []
    for tri in FACES:
        c = face_col(tri)
        faces.append([idx[(n, 1)] for n in tri]); cols.append(c)
        faces.append([idx[(n, -1)] for n in reversed(tri)]); cols.append(c)
    me = bpy.data.meshes.new("Head")
    me.from_pydata([blender_co(p) for p in pos], [], faces)
    me.update()
    a = me.attributes.new("Col", "FLOAT_COLOR", "FACE")
    for i, c in enumerate(cols):
        a.data[i].color = (*c, 1.0)
    ob = bpy.data.objects.new("Head", me)
    bpy.context.scene.collection.objects.link(ob)
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bad_e = [e for e in bm.edges if len(e.link_faces) != 2]
    bm.to_mesh(me); bm.free()
    for p in me.polygons:
        p.use_smooth = False
    print("HEAD verts", len(me.vertices), "tris", len(me.polygons), "non-manifold edges", len(bad_e))
    for e in bad_e[:20]:
        print("  open", [tuple(round(c, 3) for c in v.co) for v in e.verts], len(e.link_faces))
    return ob


def place_ears(src):
    import os
    with bpy.data.libraries.load(os.path.abspath(src)) as (fr, to):
        to.objects = ["Ears"]
    ob = to.objects[0]
    bpy.context.scene.collection.objects.link(ob)
    # traced ear (side f06): top at brow height y +0.008, bottom at nose base y -0.057, front z -0.012, back z -0.051
    s = 1.35
    me = ob.data
    co = np.array([tuple(ob.matrix_world @ v.co) for v in me.vertices])  # Blender coords
    h = np.stack([co[:, 0], co[:, 2], -co[:, 1]], 1)
    c_old = np.array([0.0, (h[:, 1].min() + h[:, 1].max()) / 2, (h[:, 2].min() + h[:, 2].max()) / 2])
    c_new = np.array([0.0, -0.0245, -0.031])
    out = []
    for p in h:
        q = (p - c_old) * s + c_new
        root = 0.0574 * np.sign(p[0])  # keep the root depth into the head
        q[0] = root + (p[0] - root) * 1.0  # bigger ear, same stick-out (reference ear lies close to the head)
        out.append(q)
    ob.matrix_world.identity()
    for v, q in zip(me.vertices, out):
        v.co = blender_co(q)
    me.update()
    return ob


def eye_slits():
    """Dark slit in the eye groove (the reference has no eyeballs: the eye reads as a shadow line)."""
    pos, faces = [], []
    for sx in (1, -1):
        e_mid, e_out = np.array(to_m(*TRACE["E_MID"])), np.array(to_m(*TRACE["E_OUT"]))
        n_side = np.array(to_m(*TRACE["N_SIDE_TOP"]))
        inner = n_side + (e_mid - n_side) * 0.45
        outer = e_mid + (e_out - e_mid) * 0.55
        mid = (inner + outer) / 2
        pts = [inner, mid + np.array([0, 0.0022, 0.0]), outer, mid + np.array([0, -0.0016, 0.0])]
        o = len(pos)
        for p in pts:
            p = p + np.array([0, -0.0006, 0.0012])  # just in front of the groove plane
            pos.append((p[0] * sx, p[1], p[2]))
        faces.append([o, o + 1, o + 2, o + 3] if sx > 0 else [o + 3, o + 2, o + 1, o])
    me = bpy.data.meshes.new("Eyes")
    me.from_pydata([blender_co(p) for p in pos], [], faces)
    a = me.attributes.new("Col", "FLOAT_COLOR", "FACE")
    for d in a.data:
        d.color = (0.02, 0.012, 0.01, 1)
    ob = bpy.data.objects.new("Eyes", me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


HAIR_ZONE = {"M_HAIR", "M_FTOP", "M_CROWN", "M_BTOP", "M_OCC", "M_BLOW", "F_TOP1", "F_TOP2", "F_TEMPLE", "SB_TOP",
             "SK_FT", "SK_TS", "SK_SH", "SK_SIDE", "SK_BH", "SK_BK", "SK_BEHIND", "SK_BACK_LO",
             "SB_BACK", "E_TOP_F", "E_TOP_B", "E_BACK_LO",
             "EAR_C"}  # thin hair tucked under the ear: no skin between ear and hair seen from behind
HAIR = np.array([0.27, 0.18, 0.11]) ** 2.2


def _hash(c):
    v = np.sin(c[0] * 91.7 + c[1] * 47.3 + c[2] * 13.1) * 43758.5453
    return v - np.floor(v)


def _hc(v):
    """Blender co -> head coords (x, y up, z fwd)."""
    return np.array([v.x, v.z, -v.y])


def _smooth(x, a, b):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


EAR_C3 = np.array([0.07, -0.0245, -0.031])   # ear centre (head coords), see place_ears


def ear_near(h):
    """1 at the ear, 0 from ~6 cm away (ear is taller than wide: scale y down)."""
    d = (np.abs(np.asarray(h)) * np.array([1, 1, 1]) - EAR_C3 * np.array([1, 0, 0]) - np.array([0, EAR_C3[1], EAR_C3[2]]))
    d = np.array([abs(h[0]) - EAR_C3[0], (h[1] - EAR_C3[1]) * 0.7, h[2] - EAR_C3[2]])
    return 1.0 - _smooth(np.linalg.norm(d), 0.038, 0.06)


def hair_flow(h):
    """One flow for the whole hair (user notes on the colour reference):
    top/crown flows FORWARD to the face, tips up-forward and leaning to the character's left (parting);
    sides rise; back falls. Zones blend smoothly so neighbouring spikes stay almost parallel (no crossing)."""
    x, y, z = h
    top = np.array(HP["top"], float)
    if HP["mid"]:
        top[0] = top[0] * (1 - HP["mid"]) + HP["mid"] * 0.8 * (np.sign(x) or 1.0)
    side = np.array(HP["side"], float) * np.array([np.sign(x) or 1.0, 1, 1])
    back = np.array(HP["back"], float)
    a = _smooth(y, 0.035, 0.075)
    b = _smooth(-z, 0.02, 0.07) * (1 - a)
    c = 1 - a - b
    f = a * top / np.linalg.norm(top) + b * back / np.linalg.norm(back) + c * side / np.linalg.norm(side)
    return f / np.linalg.norm(f)


# hair style parameters (defaults = approved v17r); head_mix.py blends several sets per seed
HP = {
    "top": (0.35, 0.45, 0.82),        # flow of the top hair (x>0 = parting lean to the character's left)
    "side": (0.35, 0.9, -0.25),        # side flow (x sign added)
    "back": (0.1, -0.55, -0.83),       # back flow
    "thick": (0.010, 0.016, 0.015, 0.012),   # mass: base, + crown, + side, + back
    "lump": 0.44,                       # silhouette lumpiness
    "spike": {"quiff": (0.048, 0.75), "crown": (0.042, 0.70), "side": (0.030, 0.55), "back": (0.022, 0.30)},
    "nape": (0.017, 0.012),             # edge tooth length base + random
    "keep": 1.0,                        # share of candidate spikes that are pulled
    "mask_w": 1.0,      # mohawk: hair mass only where |x| < mask_w (m); 1.0 = everywhere
    "cut_y": -1.0,      # undercut / fade: below this height (m) the mass is shaved to cut_k
    "cut_k": 1.0,
    "drop": (0.0, 0.0), # long hair: hair edge pulled down (side behind the ear, back) in m
    "curl": 0.0,        # 0 straight flow .. 1 random direction per spike (curly / messy)
    "mid": 0.0,         # 1 = middle parting (top flow splits left/right)
    "tone": 0.0,        # 0 hair colour .. 1 skin colour (buzz cut / stubble reads half skin)
}
CUT = {}   # hair vertex index -> shaved factor (0 hair .. 1 skin), filled by build_hair for colouring

CLUMPS = False   # secondary locks (v17m). Off: user preferred the clean big-plane mass with pulled spikes
CLUMPS_MADE = [0]


def flow_dir(h):
    """Global hair direction (head coords): front tuft rises, top goes back, sides and back fall."""
    x, y, z = h
    if z > 0.06 and y > 0.03:
        return np.array([0.25, 1.0, -0.15])
    down = np.clip((0.07 - y) / 0.07, 0, 1.6)
    return np.array([np.sign(x) * 0.25 * min(down, 1.0), -down, -1.0])


def add_clumps(bm):
    """Secondary forms: tapered locks lying on the hair mass, following the flow, varied size, overlapping.
    Each lock = root section (left, ridge, right) -> mid section -> tip; the ridge gives a lit and a shaded plane."""
    from mathutils.bvhtree import BVHTree
    n_old = len(bm.faces)
    tree = BVHTree.FromBMesh(bm)

    def surf(h):
        loc, nrm, _, _ = tree.find_nearest(blender_co(h))
        hh = _hc(loc); n = _hc(nrm); n = n / np.linalg.norm(n)
        if np.dot(n, hh - np.array([0, 0.0, -0.01])) < 0:
            n = -n
        return hh, n

    # candidate roots: hair-mass faces away from the hair edge, spaced out (largest first by hash = varied)
    cands = []
    for f in bm.faces:
        c = _hc(f.calc_center_median())
        if c[1] < -0.035 or any(v.is_boundary for v in f.verts):
            continue
        cands.append(c)
    cands.sort(key=lambda c: _hash(c * np.array([1.9, 1.3, 0.7])))
    roots = []
    for c in cands:
        if all(np.linalg.norm(c - r) > 0.046 for r in roots):
            roots.append(c)
    shade = {}
    for i, r0 in enumerate(roots):
        rnd = _hash(r0 * 5.3)
        p0, n0 = surf(r0)
        d = flow_dir(p0); d = d - n0 * np.dot(d, n0)
        if np.linalg.norm(d) < 0.35:      # flow almost along the normal (top of the head): go back
            d = np.array([0, 0, -1.0]) - n0 * n0[2] * -1.0
        d /= np.linalg.norm(d)
        top = p0[1] > 0.05
        front = p0[2] > 0.045 and p0[1] > 0.03
        L = 0.060 + 0.040 * rnd + (0.012 if front else 0.0)
        w = 0.036 + 0.020 * _hash(r0 * 2.7)
        th = 0.008 + 0.006 * rnd
        crown = p0[1] > 0.075
        lift = (0.036 if front else 0.034 if crown else 0.020 if top else 0.007) * (0.6 + 0.8 * rnd)
        p1, n1 = surf(p0 + d * L * 0.5)            # walk on the surface in two steps, re-aiming at the middle
        dm = d - n1 * np.dot(d, n1); dm /= (np.linalg.norm(dm) + 1e-9)
        p2, n2 = surf(p1 + dm * L * 0.5)
        side0 = np.cross(n0, d); side0 /= np.linalg.norm(side0)
        d1 = p2 - p1; d1 = d1 - n1 * np.dot(d1, n1); d1 /= (np.linalg.norm(d1) + 1e-9)
        side1 = np.cross(n1, d1); side1 /= (np.linalg.norm(side1) + 1e-9)
        if np.dot(side1, side0) < 0:   # keep the lock untwisted
            side1 = -side1
        sink = -0.004
        pts = [p0 + side0 * w / 2 + n0 * sink, p0 + n0 * th, p0 - side0 * w / 2 + n0 * sink,
               p1 + side1 * w * 0.33 + n1 * (0.001 + lift * 0.35), p1 + n1 * (th * 0.8 + lift * 0.45),
               p1 - side1 * w * 0.33 + n1 * (0.001 + lift * 0.35),
               p2 + n2 * (0.002 + lift)]
        vs = [bm.verts.new(blender_co(q)) for q in pts]
        L0, T0, R0, L1, T1, R1, TIP = vs
        quads = [(L0, L1, T1, T0), (T0, T1, R1, R0), (R0, R1, L1, L0)]
        tris = [(L1, TIP, T1), (T1, TIP, R1), (R1, TIP, L1), (L0, T0, R0)]
        tone = 0.93 + 0.12 * _hash(r0 * 9.1)
        for fv in quads + tris:
            try:
                f = bm.faces.new(fv)
            except ValueError:
                continue
            # outward = away from the clump centre
            cen = sum((v.co for v in vs), Vector()) / 7
            f.normal_update()
            if f.normal.dot(f.calc_center_median() - cen) < 0:
                f.normal_flip()
    bm.faces.index_update()
    for f in bm.faces:
        if f.index >= n_old:
            pass
    # tone per clump: faces were appended in clump order, 7 faces each
    idx = n_old
    for i, r0 in enumerate(roots):
        tone = 0.93 + 0.12 * _hash(r0 * 9.1)
        for k in range(7):
            shade[idx + k] = tone
        idx += 7
    CLUMPS_MADE[0] = len(roots)
    return shade


def build_hair(head):
    """Hair = thick mass of big planes (reference: 2-3 cm over top and back), spikes only where the reference has them.
    1. cap = head faces above the hairline, subdivided once (more points to pull);
    2. volume: every point pushed out from the skull, thin at the hairline, thick over crown and back;
    3. spikes = single surface points pulled far out (their fan of triangles becomes one shard):
       crown row (up + back), front quiff (up + back), side flicks above/behind the ear (back), nape teeth (down);
       a picked point blocks its neighbours, so shards stay separate;
    4. skirt from the hair edge down to the skin, so the edge has a visible thickness."""
    CUT.clear()
    zone = set()
    for n in HAIR_ZONE:
        x, y, z = to_m(*TRACE[n])
        for sx in (1, -1):
            zone.add(tuple(np.round(blender_co((x * sx, y, z)), 5)))
    bm = bmesh.new(); bm.from_mesh(head.data)
    inz = lambda v: tuple(np.round(v.co, 5)) in zone
    ear_c = to_m(*TRACE["EAR_C"])
    ear_keys = {tuple(np.round(blender_co((ear_c[0] * sx, ear_c[1], ear_c[2])), 5)) for sx in (1, -1)}

    def front_of_ear(f):  # under-ear hair only behind the ear root, never over its front (it covered the bowl)
        if not any(tuple(np.round(v.co, 5)) in ear_keys for v in f.verts):
            return False
        return _hc(f.calc_center_median())[2] > ear_c[2] - 0.004
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if not all(inz(v) for v in f.verts) or front_of_ear(f)],
                     context="FACES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bmesh.ops.subdivide_edges(bm, edges=list(bm.edges), cuts=1, use_grid_fill=True)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    bm.normal_update()
    centre = np.array([0.0, 0.0, -0.01])
    boundary = {v for v in bm.verts if v.is_boundary}
    base = {}
    for v in bm.verts:
        h = _hc(v.co)
        r = h - centre; r /= np.linalg.norm(r)
        n = _hc(v.normal); n /= np.linalg.norm(n)
        d = r * 0.5 + n * 0.5; d /= np.linalg.norm(d)
        up = np.clip((h[1] + 0.02) / 0.11, 0, 1)            # 0 low .. 1 crown
        back = np.clip(-h[2] / 0.10, 0, 1)                 # 0 face side .. 1 back
        side = np.clip((abs(h[0]) - 0.03) / 0.04, 0, 1)  # 0 middle .. 1 temple / over the ear
        # colour turntable: side panels bulge out past the face (hair 1.45 x face width), back mass wider than the skull
        lump = 1.0 - HP["lump"] / 2 + HP["lump"] * _hash(h * 7.7)       # lumpy mass: silhouette not smooth
        k0, k1, k2, k3 = HP["thick"]
        t = lump * (k0 + k1 * up + k2 * side * (1 - 0.4 * up) + k3 * back)
        # thin out towards the side/back hair edge, so the hair lies on the skin round the ear
        # (a thick mass that stops at the edge made a hanging roof over the ear); the forehead fringe keeps its edge
        side_edge = [b for b in boundary if _hc(b.co)[2] < 0.04]
        if side_edge:
            dist = min((v.co - b.co).length for b in side_edge)
            t *= 0.45 + 0.55 * _smooth(dist, 0.0, 0.035)
        # round the ear the hair lies almost flat on the skin (reference): a lifted layer there shows a dark
        # underside that reads as a gap / hanging roof in front of and behind the ear
        t *= 1.0 - 0.85 * ear_near(h)
        if v in boundary:
            t = 0.005 if h[2] > 0.04 else 0.002
        cut = 0.0
        if HP["mask_w"] < 1.0:
            cut = max(cut, _smooth(abs(h[0]), HP["mask_w"], HP["mask_w"] + 0.012))
        if HP["cut_y"] > -1.0:
            cut = max(cut, (1 - _smooth(h[1], HP["cut_y"] - 0.006, HP["cut_y"] + 0.006)) * (1 - HP["cut_k"]))
        t = t * (1 - cut) + 0.0015 * cut
        base[v] = (h, d, t)
        CUT[v] = cut
    # skirt: the boundary copy stays on the skin
    ext = bmesh.ops.extrude_edge_only(bm, edges=[e for e in bm.edges if e.is_boundary])
    skirt = [v for v in ext["geom"] if isinstance(v, bmesh.types.BMVert)]
    skin_of = {}
    for s in skirt:
        best = min(boundary, key=lambda b: (b.co - s.co).length)
        skin_of[best] = s
    for v, (h, d, t) in base.items():
        v.co = blender_co(h + d * t)
    # long hair: the edge (and its skirt) is pulled down behind the ear front and at the back -> a hanging curtain
    ds, db = HP["drop"]
    shift = {}
    if ds or db:
        for b in boundary:
            h = _hc(b.co)
            if h[2] > 0.0 and h[1] > -0.06:
                continue   # sideburn / fringe stay
            w_back = _smooth(-h[2], 0.0, 0.06)
            amt = ds * (1 - w_back) + db * w_back
            amt *= 1 - CUT.get(b, 0.0)
            out = np.array([np.sign(h[0]) * 0.25 * (1 - w_back), 0, -0.25 * w_back])
            sh = np.array([0, -amt, 0]) + out * amt
            b.co = blender_co(h + sh)
            shift[b] = sh
            if b in skin_of:
                s = skin_of[b]; s.co = blender_co(_hc(s.co) + sh)
    # spikes
    picked, blocked = [], set()
    def kind(h):
        x, y, z = h
        if z > 0.04 and y > 0.045 and abs(x) < 0.035:
            return "quiff"   # centre front only: at the head's corner it stood alone on the silhouette
        if abs(x) > 0.058 and 0.02 < y < 0.07 and -0.025 < z < 0.04:
            return "side"   # temple flicks only; further back they became long horizontal spikes
        if y > 0.045:
            return "crown"
        if z < 0.035 and y < 0.03:
            return "nape"   # edge teeth: whole side + back hair edge (around the ear, nape)
        if abs(x) > 0.05 and z < 0.04:
            return "side"
        if z < -0.05:
            return "back"
        return None
    order = sorted(base, key=lambda v: _hash(base[v][0] * np.array([1.7 if base[v][0][0] > 0 else 1.0, 1, 1])))
    for v in order:
        h, d, t = base[v]
        k = kind(h)
        if k is None or v in blocked:
            continue
        if CUT.get(v, 0.0) > 0.4:
            continue   # no spikes on shaved parts
        if k == "nape" and v not in boundary:
            continue
        if k in ("nape", "side") and ear_near(h) > 0.3:
            continue   # no teeth / flicks right at the ear
        if k != "nape" and v in boundary:
            continue
        if _hash(h * 5.3) > HP["keep"]:
            continue
        picked.append((v, k))
        blocked.add(v)
        for e in v.link_edges:
            blocked.add(e.other_vert(v))
    for v, k in picked:
        h, d, t = base[v]
        r = _hash(h * 3.1)
        m = 0.7 + 0.65 * _hash(h * 4.9) ** 1.5     # length variety only; direction comes from the flow field
        nn = d / np.linalg.norm(d)
        if k == "nape":
            f = np.array([np.sign(h[0]) * 0.2, -0.85, -0.5])
            f = f - nn * np.dot(f, nn)                # tooth slides along the skin, does not stick out
            pull = f / np.linalg.norm(f) * (HP["nape"][0] + HP["nape"][1] * r) * (0.7 + 0.3 * m) - nn * 0.002
        else:
            f = hair_flow(h)
            if HP["curl"]:
                rnd = np.array([_hash(h * 6.1), _hash(h * 7.3), _hash(h * 8.7)]) * 2 - 1
                f = f * (1 - HP["curl"]) + rnd / (np.linalg.norm(rnd) + 1e-9) * HP["curl"]
            f = f - nn * np.dot(f, nn)                 # along the surface ...
            f /= np.linalg.norm(f)
            base_len, lift = HP["spike"][k]
            ln = base_len * (0.8 + 0.4 * r) * m
            if k in ("quiff", "crown"):   # shorter towards the sides of the head: no lone horn on the corner
                ln *= 1.0 - 0.45 * _smooth(abs(h[0]), 0.025, 0.07)
            up = nn if k in ("side", "back") else (0.35 * nn + np.array([0, 1.0, 0]))
            up = up / np.linalg.norm(up)              # top spikes rise up, not out sideways (no horns)
            pull = (f + up * lift) * ln                # ... and lifted off it, so tips break the silhouette
        v.co = blender_co(h + d * t + pull + shift.get(v, 0.0))
        if v in skin_of:   # nape tooth: its skirt point follows, so the tooth keeps its thickness
            s = skin_of[v]
            s.co = blender_co(_hc(s.co) + pull * 0.85)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    shade = add_clumps(bm) if CLUMPS else {}
    bm.verts.index_update()
    cut_idx = {v.index: c for v, c in CUT.items() if v.is_valid}
    for s_ in skirt:
        if s_.is_valid and s_.index not in cut_idx:
            src = [b for b, sk in skin_of.items() if sk is s_]
            cut_idx[s_.index] = CUT.get(src[0], 0.0) if src else 0.0
    CUT.clear(); CUT.update(cut_idx)
    me = bpy.data.meshes.new("Hair"); bm.to_mesh(me); bm.free()
    a = me.attributes.new("Col", "FLOAT_COLOR", "FACE")
    for i, d_ in enumerate(a.data):
        d_.color = (*(HAIR * shade.get(i, 1.0)), 1)
    for p in me.polygons:
        p.use_smooth = False
    ob = bpy.data.objects.new("Hair", me)
    bpy.context.scene.collection.objects.link(ob)
    print("HAIR faces", len(me.polygons), "clumps", CLUMPS_MADE[0], "spikes", {k: sum(1 for _, kk in picked if kk == k) for k in ("quiff", "crown", "side", "back", "nape")})
    return ob


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--ears", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    head = build_head()
    build_hair(head)
    place_ears(a.ears)
    eye_slits()
    import os
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(a.out))
    print("SAVED", a.out)


if __name__ == "__main__":
    main()
