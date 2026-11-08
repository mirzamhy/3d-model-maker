"""Seed mix of traced head styles (prototype).

Every style is a set of offsets on the v17 landmarks (same vertices, same faces), so styles blend by weight.
Hair styles are parameter sets for head_trace.build_hair (HP), blended the same way.
seed -> weights (one style usually dominates) + skin / hair colour.

blender -b --factory-startup -P tools/blender/head_mix.py -- --ears output/head-game/template/head_lp_v6.blend \
    --sheet notes/attachments/qa/mix_sheet.png --seeds 1-16 [--save output/head-mix]
"""
import sys, os, math, argparse, copy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import numpy as np
from mathutils import Vector
import head_trace as ht

BASE_TRACE = copy.deepcopy(ht.TRACE)
BASE_HP = copy.deepcopy(ht.HP)

# face styles: landmark -> (dx, dy, dd) in trace px (dd smaller = more forward). Hair / ear area untouched.
FACE = {
    "ref": {},
    "kotak": {   # square heavy jaw, brow shelf forward, wide nose, thick neck
        "CH_TOP": (12, 0, 0), "CH_SIDE": (22, 5, 0), "J_MID": (22, 5, 0), "J_ANG": (8, 8, 0),
        "M_CHB": (0, 5, 0), "M_CHIN": (0, 3, -4), "MC_OUT": (8, 0, 0),
        "B_TOP_IN": (0, 0, -6), "B_TOP_MID": (0, 3, -8), "B_TOP_OUT": (4, 3, -6), "M_GLAB": (0, 0, -5),
        "N_WING": (8, 0, 0), "N_SIDE_TOP": (4, 0, 0), "N_BR_TOP": (4, 0, 0), "N_BR_BOT": (5, 0, 0),
        "NK_F": (15, 0, 0), "N1": (15, 0, 0), "NK_EAR": (8, 0, 0), "N2": (8, 0, 0),
    },
    "kurus": {   # long gaunt face: sharp cheekbone, hollow cheek, narrow long chin, longer nose
        "C_BONE": (10, -5, 0), "MC_OUT": (-14, 5, 12), "MC_UP": (-6, 0, 8),
        "J_MID": (-18, 12, 0), "CH_SIDE": (-14, 15, 0), "CH_TOP": (-8, 10, 0),
        "M_CHIN": (0, 16, -6), "M_CHB": (0, 18, 0), "M_CHG": (0, 10, 0), "M_THROAT": (0, 12, 0),
        "NK_F": (-12, 6, 0), "N1": (-15, 0, 0), "N2": (-10, 0, 0),
        "N_BR_BOT": (-3, 4, -6), "M_TIP": (0, 6, -8), "N_TIPS": (0, 6, -6), "N_WING": (-4, 6, 0), "M_SUB": (0, 6, 0),
    },
}

FACE_AMP = 1.8   # v1 sheet: offsets x1 were too subtle to read at game size

# hair styles: overrides of head_trace.HP (default = approved v17r "jambul").
# list from barber / game-pack references: crop, buzz, mohawk, slick-back undercut, faux hawk, curtains (middle
# parting), curly, shoulder length, mullet, bald, messy
HAIR = {
    "jambul": {},
    "cepak": {          # short crop: thin mass, stubby tips
        "thick": (0.005, 0.006, 0.006, 0.005), "lump": 0.2,
        "spike": {"quiff": (0.012, 0.4), "crown": (0.010, 0.4), "side": (0.008, 0.3), "back": (0.007, 0.2)},
        "nape": (0.006, 0.004), "keep": 0.8,
    },
    "gondrong": {       # messy longer hair: fringe falls forward, sides and back hang down
        "top": (0.25, -0.35, 0.9), "side": (0.25, -0.6, -0.35), "back": (0.05, -0.9, -0.45),
        "thick": (0.012, 0.014, 0.020, 0.018), "lump": 0.5,
        "spike": {"quiff": (0.040, 0.15), "crown": (0.042, 0.25), "side": (0.040, 0.10), "back": (0.045, 0.05)},
        "nape": (0.026, 0.016), "keep": 0.9,
    },
    "buzz": {           # clipper cut: skin-tight, no tips, half skin colour
        "thick": (0.002, 0.001, 0.001, 0.001), "lump": 0.0, "keep": 0.0, "nape": (0.0, 0.0), "tone": 0.45,
    },
    "mohawk": {         # centre strip only, tall tips standing up, sides shaved
        "mask_w": 0.022, "top": (0.0, 1.0, 0.25), "thick": (0.012, 0.012, 0.0, 0.006), "lump": 0.3,
        "spike": {"quiff": (0.050, 1.2), "crown": (0.055, 1.3), "side": (0.0, 0.0), "back": (0.035, 0.6)},
        "nape": (0.0, 0.0),
    },
    "slickback": {      # undercut, top combed straight back, flat
        "cut_y": 0.035, "cut_k": 0.08, "top": (0.0, 0.1, -1.0), "thick": (0.012, 0.012, 0.004, 0.004), "lump": 0.1,
        "spike": {"quiff": (0.018, 0.05), "crown": (0.026, 0.05), "side": (0.0, 0.0), "back": (0.02, 0.0)},
        "nape": (0.0, 0.0), "keep": 0.7,
    },
    "fauxhawk": {       # faded sides, quiff and crown pushed to the middle and up
        "cut_y": 0.03, "cut_k": 0.25, "top": (0.0, 0.8, 0.6), "thick": (0.012, 0.016, 0.006, 0.006),
        "spike": {"quiff": (0.050, 1.0), "crown": (0.045, 0.9), "side": (0.010, 0.2), "back": (0.015, 0.2)},
        "nape": (0.004, 0.002),
    },
    "belahtengah": {    # curtains: middle parting, fringe falls to both sides of the face
        "mid": 1.0, "top": (0.0, -0.45, 0.9), "side": (0.2, -0.5, -0.2), "thick": (0.012, 0.012, 0.016, 0.012),
        "spike": {"quiff": (0.035, 0.05), "crown": (0.030, 0.1), "side": (0.030, 0.05), "back": (0.025, 0.05)},
        "nape": (0.014, 0.008), "lump": 0.25,
    },
    "keriting": {       # curly / afro: big round mass, short tips in every direction
        "thick": (0.022, 0.020, 0.020, 0.020), "lump": 0.7, "curl": 0.85,
        "spike": {"quiff": (0.016, 0.4), "crown": (0.016, 0.4), "side": (0.014, 0.4), "back": (0.014, 0.4)},
        "nape": (0.006, 0.004),
    },
    "panjang": {        # shoulder length: curtain down the sides and back
        "drop": (0.055, 0.085), "top": (0.2, -0.3, 0.9), "side": (0.1, -1.0, -0.1), "back": (0.0, -1.0, -0.2),
        "thick": (0.012, 0.012, 0.016, 0.016), "lump": 0.3,
        "spike": {"quiff": (0.030, 0.05), "crown": (0.030, 0.1), "side": (0.030, 0.0), "back": (0.030, 0.0)},
        "nape": (0.020, 0.012),
    },
    "mullet": {         # short top and sides, long back
        "drop": (0.0, 0.07), "thick": (0.008, 0.010, 0.006, 0.014), "back": (0.0, -1.0, -0.3),
        "spike": {"quiff": (0.025, 0.5), "crown": (0.025, 0.5), "side": (0.010, 0.2), "back": (0.030, 0.0)},
        "nape": (0.022, 0.012),
    },
    "botak": {          # bald: hair shaved everywhere (skin colour)
        "cut_y": 0.3, "cut_k": 0.0, "keep": 0.0, "nape": (0.0, 0.0),
    },
}
DISCRETE = {"mask_w", "cut_y"}   # zone switches come from the main style only (a blend would half-apply them)

SKINS = [(0.80, 0.58, 0.45), (0.86, 0.68, 0.55), (0.62, 0.42, 0.30), (0.45, 0.30, 0.21), (0.74, 0.55, 0.40)]
HAIRS = [(0.27, 0.18, 0.11), (0.10, 0.08, 0.07), (0.45, 0.30, 0.15), (0.55, 0.45, 0.30), (0.35, 0.12, 0.06)]


def weights(rng, n, sharp=2.5):
    """Random blend weights; sharp > 1 makes one style dominate, the others only tint it."""
    w = rng.random(n) ** sharp
    return w / w.sum()


def blend(base, sets, w):
    """Weighted sum of parameter sets (each set = overrides of base)."""
    if isinstance(base, dict):
        return {k: blend(base[k], [s.get(k, base[k]) if isinstance(s, dict) else s for s in sets], w) for k in base}
    if isinstance(base, (tuple, list)):
        return tuple(blend(base[i], [s[i] for s in sets], w) for i in range(len(base)))
    return float(sum(wi * s for wi, s in zip(w, sets)))


def variant(seed, pure=None):
    rng = np.random.default_rng(seed)
    fw = weights(rng, len(FACE))
    trace = {}
    for n, (x, y, d) in BASE_TRACE.items():
        off = np.zeros(3)
        for wi, st in zip(fw, FACE.values()):
            off += wi * FACE_AMP * np.array(st.get(n, (0, 0, 0)), float)
        if x == 0:
            off[0] = 0
        trace[n] = (x + off[0], y + off[1], d + off[2])
    names = list(HAIR)
    i, j = rng.choice(len(names), 2, replace=False)
    sec = 0.35 * rng.random()
    hw = np.zeros(len(names)); hw[i] += 1 - sec; hw[j] += sec
    hp = blend(BASE_HP, [HAIR[names[i]], HAIR[names[j]]], [1 - sec, sec])
    for k in DISCRETE:
        hp[k] = HAIR[names[i]].get(k, BASE_HP[k])
    if pure:   # style sheet: one hair style, reference face
        fw = np.eye(len(FACE))[0]
        hw = np.array([1.0 if n == pure else 0.0 for n in names])
        hp = blend(BASE_HP, [HAIR[pure]], [1.0])
        trace = dict(BASE_TRACE)
    flip = rng.random() < 0.5        # parting side
    if flip:
        hp["top"] = (-hp["top"][0], *hp["top"][1:])
    skin = np.array(SKINS[0 if pure else rng.integers(len(SKINS))]) ** 2.2   # sRGB picks -> linear material colour
    hair = np.array(HAIRS[0 if pure else rng.integers(len(HAIRS))]) ** 2.2
    return dict(trace=trace, hp=hp, fw=fw, hw=hw, skin=skin, hair=hair, flip=flip)


def tri_normals(ob):
    me = ob.data
    return np.array([tuple(p.normal) for p in me.polygons])


def make_ears(path):
    ob = ht.place_ears(path)
    ob.name = "EarsBase"
    ob.hide_render = True
    return ob


def set_col(ob, fn):
    me = ob.data
    a = me.attributes.get("Col")
    if a is None or a.domain != "FACE":
        if a is not None:
            me.attributes.remove(a)
        a = me.attributes.new("Col", "FLOAT_COLOR", "FACE")
        old = None
    else:
        old = [tuple(d.color)[:3] for d in a.data]
    for i, d in enumerate(a.data):
        d.color = (*fn(i, None if old is None else np.array(old[i])), 1)
    # face colours are not colour attributes for the viewport: copy to a CORNER layer for the render
    c = me.attributes.get("ColC") or me.attributes.new("ColC", "FLOAT_COLOR", "CORNER")
    for p in me.polygons:
        col = a.data[p.index].color
        for li in p.loop_indices:
            c.data[li].color = col
    me.color_attributes.active_color = me.color_attributes["ColC"]
    me.color_attributes.render_color_index = [x.name for x in me.color_attributes].index("ColC")


def build(seed, ears_base, ref_normals, pure=None):
    v = variant(seed, pure)
    ht.TRACE.clear(); ht.TRACE.update(v["trace"])
    ht.HP.clear(); ht.HP.update(copy.deepcopy(v["hp"]))
    head = ht.build_head()
    hair = ht.build_hair(head)
    eyes = ht.eye_slits()
    ears = ears_base.copy(); ears.data = ears_base.data.copy(); ears.hide_render = False
    bpy.context.scene.collection.objects.link(ears)
    # checks: manifold head, no flipped face vs the reference build
    n = tri_normals(head)
    flips = int((np.einsum("ij,ij->i", n, ref_normals) < 0.2).sum()) if ref_normals is not None else 0
    obs = {"Head": head, "Hair": hair, "Eyes": eyes, "Ears": ears}
    for k, o in obs.items():
        o.name = "%s_%d" % (k, seed)
    skin, hcol = v["skin"], v["hair"]
    set_col(head, lambda i, old: old / ht.SKIN * skin)
    set_col(ears, lambda i, old: skin)
    tone = v["hp"]["tone"]
    base_h = hcol * (1 - tone) + skin * 0.8 * tone
    cut = ht.CUT
    fcut = [np.mean([cut.get(vi, 0.0) for vi in p.vertices]) for p in hair.data.polygons]
    set_col(hair, lambda i, old: base_h * (1 - fcut[i]) + skin * 0.85 * fcut[i])
    names = list(FACE); hnames = list(HAIR)
    label = " ".join("%s%.0f" % (names[i][:2], 100 * v["fw"][i]) for i in np.argsort(-v["fw"]) if v["fw"][i] > 0.08)
    label += " | " + " ".join("%s%.0f" % (hnames[i][:2], 100 * v["hw"][i]) for i in np.argsort(-v["hw"]) if v["hw"][i] > 0.08)
    print("SEED", seed, label, "flipped", flips, "hair tris", len(hair.data.polygons))
    return obs, flips, label


def setup_render(res):
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sh = sc.display.shading; sh.light = "STUDIO"
    ok = [i.identifier for i in type(sh).bl_rna.properties["color_type"].enum_items]
    sh.color_type = "VERTEX" if "VERTEX" in ok else "ATTRIBUTE"
    sc.world = sc.world or bpy.data.worlds.new("w"); sc.world.color = (0.93, 0.93, 0.93)
    sc.view_settings.view_transform = "Standard"
    sc.render.resolution_x = sc.render.resolution_y = res
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    sc.collection.objects.link(cam); sc.camera = cam
    cam.data.type = "ORTHO"; cam.data.ortho_scale = 0.36
    return sc, cam


def render_view(sc, cam, ang, path):
    c = Vector((0, 0, 0.0))
    t = math.radians(ang)
    cam.location = c + Vector((math.sin(t), -math.cos(t), 0.08)).normalized() * 5
    cam.rotation_euler = (c - cam.location).to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(path)
    px = np.array(img.pixels[:]).reshape(img.size[1], img.size[0], 4)
    bpy.data.images.remove(img)
    return px


def save_sheet(tiles, cols, path):
    rows = math.ceil(len(tiles) / cols)
    h, w = tiles[0].shape[:2]
    sheet = np.ones((rows * h, cols * w, 4))
    for i, t in enumerate(tiles):
        r, c = divmod(i, cols)
        y0 = (rows - 1 - r) * h      # Blender pixel rows start at the bottom
        sheet[y0:y0 + h, c * w:(c + 1) * w] = t
    img = bpy.data.images.new("sheet", cols * w, rows * h, alpha=True)
    img.pixels = sheet.ravel()
    img.filepath_raw = path; img.file_format = "PNG"
    img.save()


def parse_seeds(s):
    out = []
    for part in s.split(","):
        if "-" in part:
            a, b = part.split("-"); out += list(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return out


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--ears", required=True)
    ap.add_argument("--sheet", required=True)
    ap.add_argument("--seeds", default="1-16")
    ap.add_argument("--res", type=int, default=320)
    ap.add_argument("--save", default="")
    ap.add_argument("--styles", action="store_true", help="one tile per hair style (pure), reference face")
    a = ap.parse_args(argv)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    ears_base = make_ears(a.ears)
    # reference normals from the unmixed head
    ref = ht.build_head(); ref_n = tri_normals(ref)
    bpy.data.objects.remove(ref)
    sc, cam = setup_render(a.res)
    tmp = os.path.join(os.path.dirname(os.path.abspath(a.sheet)), "_mix_tmp.png")
    tiles, report = [], []
    jobs = [(i + 1, n) for i, n in enumerate(HAIR)] if a.styles else [(s_, None) for s_ in parse_seeds(a.seeds)]
    for seed, pure in jobs:
        obs, flips, label = build(seed, ears_base, ref_n, pure)
        pair = [render_view(sc, cam, ang, tmp) for ang in (0, 40)]
        tiles.append(np.concatenate(pair, axis=1))
        report.append((seed, flips, label))
        if a.save:
            os.makedirs(a.save, exist_ok=True)
            for o in list(bpy.data.objects):
                if o.type == "MESH" and o.name.split("_")[-1] != str(seed) and o is not ears_base:
                    o.hide_render = True
            bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(os.path.join(a.save, "seed_%d.blend" % seed)), copy=True)
        for o in obs.values():
            bpy.data.objects.remove(o)
    os.remove(tmp)
    save_sheet(tiles, 4, os.path.abspath(a.sheet))
    print("SHEET", a.sheet)
    for r in report:
        print("REPORT seed %d flipped %d  %s" % r)


main()
