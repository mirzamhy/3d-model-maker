# Very simple low-poly head (old-school game style, ~200 triangles) built point by point in Blender:
#   blender -b --factory-startup -P tools/blender/head_simple.py
# Head: 9 rings of 10 points (chin/jaw, cheeks, brow, skull) placed by hand, one crown point.
# Nose: a 5-point wedge. Eyes and brows: flat dark shapes laid on the skin (like painted texture).
# Hair: the upper skull faces copied and thickened, plus an optional ponytail.
# Writes output/head-simple/head.blend and renders/head_s_*.png.
# Head coordinates: x to the character's left, y up, z forward, metres, y = 0 at eye level.
import bpy
import bmesh
import math
import os
import numpy as np
from mathutils import Vector

ROOT = r"C:\Mirza Personal\model 3d maker"
OUT = os.path.join(ROOT, "output", "head-simple")
REN = os.path.join(ROOT, "renders")
os.makedirs(OUT, exist_ok=True)
TAG = os.environ.get("HEAD_TAG", "head_s")
PONYTAIL = os.environ.get("PONYTAIL", "1") == "1"
WIRE = os.environ.get("HEAD_WIRE", "0") == "1"

# Each ring: right-half points c0 (front centre) .. c5 (back centre), as (x, y, z).
RINGS = {
    "neck":  [(0, -0.16, 0.035), (0.03, -0.16, 0.03), (0.047, -0.16, 0.0), (0.045, -0.16, -0.03), (0.028, -0.16, -0.05), (0, -0.16, -0.055)],
    "throat": [(0, -0.108, 0.04), (0.03, -0.104, 0.034), (0.047, -0.092, 0.0), (0.046, -0.08, -0.033), (0.029, -0.077, -0.054), (0, -0.077, -0.058)],
    "jaw":   [(0, -0.118, 0.07), (0.024, -0.114, 0.064), (0.056, -0.083, 0.004), (0.056, -0.058, -0.042), (0.036, -0.054, -0.072), (0, -0.054, -0.077)],
    "mouth": [(0, -0.074, 0.087), (0.03, -0.072, 0.076), (0.062, -0.055, 0.02), (0.069, -0.03, -0.048), (0.046, -0.026, -0.086), (0, -0.026, -0.093)],
    "nose":  [(0, -0.038, 0.09), (0.035, -0.034, 0.08), (0.068, -0.026, 0.027), (0.074, 0.002, -0.052), (0.05, 0.006, -0.094), (0, 0.006, -0.101)],
    "eye":   [(0, 0.004, 0.087), (0.036, 0.002, 0.078), (0.07, 0.006, 0.03), (0.075, 0.032, -0.05), (0.051, 0.036, -0.091), (0, 0.036, -0.099)],
    "brow":  [(0, 0.03, 0.092), (0.038, 0.03, 0.085), (0.069, 0.032, 0.033), (0.072, 0.062, -0.046), (0.049, 0.066, -0.086), (0, 0.066, -0.094)],
    "fore":  [(0, 0.07, 0.085), (0.036, 0.07, 0.078), (0.064, 0.068, 0.03), (0.064, 0.09, -0.04), (0.044, 0.094, -0.075), (0, 0.094, -0.082)],
    "top":   [(0, 0.105, 0.055), (0.03, 0.106, 0.05), (0.05, 0.108, 0.008), (0.048, 0.112, -0.032), (0.031, 0.113, -0.056), (0, 0.113, -0.062)],
}
ORDER = list(RINGS)
CROWN = (0, 0.124, -0.002)
COLS = 10  # c0, c1..c4 on +x, c5, c4..c1 on -x


def ring_points(name):
    r = RINGS[name]
    right = [r[i] for i in range(6)]
    left = [(-r[i][0], r[i][1], r[i][2]) for i in (4, 3, 2, 1)]
    return right + left


def bl(p):
    """head (x, y up, z forward) -> Blender (x, -y forward, z up)"""
    return (p[0], -p[2], p[1])


def make(name, verts, faces, color):
    me = bpy.data.meshes.new(name)
    me.from_pydata([bl(v) for v in verts], [], faces)
    me.update()
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    mat = bpy.data.materials.new(name + "_mat")
    mat.diffuse_color = color
    me.materials.append(mat)
    for p in me.polygons:
        p.use_smooth = False
    # outward normals
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    return ob


bpy.ops.wm.read_factory_settings(use_empty=True)
SKIN = (0.92, 0.66, 0.47, 1)
HAIR = (0.20, 0.12, 0.07, 1)
DARK = (0.04, 0.03, 0.03, 1)

# ---------- head ----------
verts, faces = [], []
idx = {}
for k, name in enumerate(ORDER):
    for c, p in enumerate(ring_points(name)):
        idx[k, c] = len(verts)
        verts.append(p)
crown = len(verts)
verts.append(CROWN)
bottom = len(verts)
verts.append((0, -0.16, -0.01))
for k in range(len(ORDER) - 1):
    for c in range(COLS):
        c1 = (c + 1) % COLS
        faces.append((idx[k, c], idx[k, c1], idx[k + 1, c1], idx[k + 1, c]))
top = len(ORDER) - 1
for c in range(COLS):
    faces.append((idx[top, c], idx[top, (c + 1) % COLS], crown))
    faces.append((idx[0, (c + 1) % COLS], idx[0, c], bottom))
head = make("Head", verts, faces, SKIN)

# ---------- nose: a wedge standing on the face ----------
nose_v = [(0, 0.004, 0.086), (0, -0.033, 0.109), (0.013, -0.038, 0.091), (-0.013, -0.038, 0.091), (0, -0.016, 0.078)]
nose_f = [(0, 1, 2), (0, 3, 1), (1, 3, 2), (0, 2, 4), (0, 4, 3), (2, 3, 4)]
nose = make("Nose", nose_v, nose_f, SKIN)


# ---------- flat shapes laid on the skin (eyes, brows) ----------
def decal(name, outline, color, lift=0.002):
    """outline: (x, y) points on the face; each is dropped onto the head surface from the front."""
    vs, fs = [], []
    cx = sum(p[0] for p in outline) / len(outline)
    cy = sum(p[1] for p in outline) / len(outline)
    for side in (1, -1):
        base = len(vs)
        # outline plus a centre point, all dropped onto the skin; a fan from the centre follows the skin's curve
        for x, y in list(outline) + [(cx, cy)]:
            hit, loc, nrm, _ = head.ray_cast(Vector(bl((side * x, y, 0.2))), Vector((0, 1, 0)))  # Blender +y is backward
            if not hit:
                raise RuntimeError(f"decal {name} missed the head at {(side * x, y)}")
            q = loc + nrm * lift
            vs.append((q.x, q.z, -q.y))  # back to head coords
        n = len(outline)
        for i in range(n):
            fs.append((base + i, base + (i + 1) % n, base + n))
    ob = make(name, vs, fs, color)
    # cut the shape finer and lay every point on the skin, so it follows the head's folds instead of cutting through
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=3, use_grid_fill=True)
    for v in bm.verts:
        ok, loc, nrm, _ = head.closest_point_on_mesh(v.co)  # both meshes are in Blender coordinates
        if ok:
            v.co = loc + nrm * lift
    bm.to_mesh(ob.data)
    bm.free()
    for p in ob.data.polygons:
        p.use_smooth = False
    # make() points the faces away from the centre; for a flat shape that can pick either side, so face them forward
    for p in ob.data.polygons:
        if p.normal.y > 0:
            p.flip()
    return ob


eyes = decal("Eyes", [(0.017, 0.001), (0.026, 0.008), (0.037, 0.009), (0.045, 0.004), (0.036, -0.003), (0.025, -0.004)], DARK)
brows = decal("Brows", [(0.013, 0.017), (0.03, 0.023), (0.047, 0.021), (0.047, 0.015), (0.03, 0.017), (0.014, 0.012)], HAIR)

# ---------- hair: upper skull faces copied outward and thickened ----------
HAIRLINE = {0: "fore", 1: "fore", 2: "fore", 3: "nose", 4: "mouth", 5: "mouth"}  # lowest ring with hair, per column
hv, hf, hidx = [], [], {}
lift = 0.006
for k, name in enumerate(ORDER):
    for c, p in enumerate(ring_points(name)):
        cc = min(c, COLS - c)
        if ORDER.index(HAIRLINE[cc]) <= k:
            v = np.array(p) - np.array([0, -0.01, -0.01])
            n = v / np.linalg.norm(v)
            hidx[k, c] = len(hv)
            hv.append(tuple(np.array(p) + n * lift))
hcrown = len(hv)
hv.append((CROWN[0], CROWN[1] + lift, CROWN[2]))
for k in range(len(ORDER) - 1):
    for c in range(COLS):
        c1 = (c + 1) % COLS
        q = [(k, c), (k, c1), (k + 1, c1), (k + 1, c)]
        have = [x for x in q if x in hidx]
        if len(have) >= 3:  # a triangle where the hairline steps down
            hf.append(tuple(hidx[x] for x in have))
for c in range(COLS):
    hf.append((hidx[top, c], hidx[top, (c + 1) % COLS], hcrown))
hair = make("Hair", hv, hf, HAIR)
sol = hair.modifiers.new("thick", "SOLIDIFY")
sol.thickness = 0.008
sol.offset = -1
dg = bpy.context.evaluated_depsgraph_get()
me = bpy.data.meshes.new_from_object(hair.evaluated_get(dg))
hair.modifiers.clear()
hair.data = me
for p in me.polygons:
    p.use_smooth = False

parts = [head, nose, eyes, brows, hair]
if PONYTAIL:
    # a 4-sided tapering tube from the back of the head, hanging down
    rings = [((0, 0.045, -0.1), 0.02), ((0, 0.01, -0.13), 0.017), ((0, -0.04, -0.14), 0.013), ((0, -0.085, -0.13), 0.006)]
    pv, pf = [], []
    for (x, y, z), r in rings:
        for a in range(4):
            ang = a * math.pi / 2 + math.pi / 4
            pv.append((x + math.cos(ang) * r, y, z + math.sin(ang) * r))
    for i in range(len(rings) - 1):
        for a in range(4):
            b = (a + 1) % 4
            pf.append((i * 4 + a, i * 4 + b, (i + 1) * 4 + b, (i + 1) * 4 + a))
    pf.append((0, 1, 2, 3))
    tip = len(pv)
    pv.append((0, -0.1, -0.125))
    last = (len(rings) - 1) * 4
    for a in range(4):
        pf.append((last + a, last + (a + 1) % 4, tip))
    parts.append(make("Ponytail", pv, pf, HAIR))

tris = sum(len(p.vertices) - 2 for ob in parts for p in ob.data.polygons)

# ---------- render ----------
scene = bpy.context.scene
world = bpy.data.worlds.new("w")
world.color = (0.035, 0.037, 0.04)
scene.world = world
scene.render.engine = "BLENDER_WORKBENCH"
sh = scene.display.shading
sh.light = "STUDIO"
sh.color_type = "MATERIAL"
scene.render.resolution_x = 700
scene.render.resolution_y = 820

wires = []
if WIRE:
    for ob in parts:
        w = ob.copy()
        w.data = ob.data.copy()
        bpy.context.collection.objects.link(w)
        m = w.modifiers.new("wire", "WIREFRAME")
        m.thickness = 0.0003
        m.use_replace = True
        edge = bpy.data.materials.new("edge")
        edge.diffuse_color = (0.1, 0.1, 0.1, 1)
        w.data.materials.clear()
        w.data.materials.append(edge)
        wires.append(w)

cam_data = bpy.data.cameras.new("cam")
cam_data.lens = 85
cam = bpy.data.objects.new("cam", cam_data)
bpy.context.collection.objects.link(cam)
scene.camera = cam
target = np.array([0.0, 0.0, -0.035])
views = {"front": 0, "34": 38, "side": 90}
for name, deg in views.items():
    a = math.radians(deg)
    pos = target + np.array([math.sin(a) * 0.8, -math.cos(a) * 0.8, 0.03])
    cam.location = pos.tolist()
    fwd = target - pos
    cam.rotation_euler = (math.atan2(math.hypot(fwd[0], fwd[1]), -fwd[2]), 0, math.atan2(-fwd[0], fwd[1]))
    scene.render.filepath = os.path.join(REN, f"{TAG}_{name}.png")
    bpy.ops.render.render(write_still=True)

imgs = [bpy.data.images.load(os.path.join(REN, f"{TAG}_{n}.png")) for n in views]
w, h = imgs[0].size
sheet = np.zeros((h, w * len(imgs), 4), dtype=np.float32)
for i, im in enumerate(imgs):
    sheet[:, i * w:(i + 1) * w] = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)
out = bpy.data.images.new("sheet", w * len(imgs), h, alpha=True)
out.pixels = sheet.ravel()
out.filepath_raw = os.path.join(REN, f"{TAG}_sheet.png")
out.file_format = "PNG"
out.save()

for wob in wires:
    bpy.data.objects.remove(wob)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "head.blend"))
print(f"HEAD_REPORT tris={tris}")
