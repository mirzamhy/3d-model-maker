# Stylized low-poly head, no hair, exactly mirror-symmetric (~700 triangles):
#   blender -b --factory-startup -P tools/blender/head_mid.py
# Topology is laid out by hand as rows (elevation) and columns (azimuth) seen from a point inside the head, with
# rows placed on the brow, lids, eye, nose tip, nose base, lips, mouth line, chin and jaw. Each eye is a patch of
# that grid replaced by inset rings (lid, white, iris). Vertex positions come from the angular head shape in
# head_lowpoly.py. Only the right half is computed; the left half is its exact mirror, and the script checks it.
# Writes output/head-mid/head.blend and renders/head_h_*.png (colour) and head_h_wire_*.png.
import bpy
import bmesh
import math
import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import head_lowpoly as H  # noqa: E402  (shape functions only)

ROOT = r"C:\Mirza Personal\model 3d maker"
OUT = os.path.join(ROOT, "output", "head-mid")
REN = os.path.join(ROOT, "renders")
os.makedirs(OUT, exist_ok=True)
TAG = os.environ.get("HEAD_TAG", "head_h")
EAR_TRIS = int(os.environ.get("EAR_TRIS", "40"))

CENTER = np.array([0.0, 0.005, -0.01])
FRONT_DIST = 0.1  # distance from CENTER to the face, front to back


def at(y):
    """Elevation (degrees) of the ray that meets the face at height y (metres, eye level = 0)."""
    return -math.degrees(math.atan2(CENTER[1] - y, FRONT_DIST))


# rows aimed at the face landmarks of head_lowpoly's shape
ROWS = [82, 60, 40, 28, at(0.034), at(0.022), at(0.009), at(0.001), at(-0.007), at(-0.022), at(-0.036), at(-0.046),
        at(-0.06), at(-0.0722), at(-0.086), at(-0.098), at(-0.118), -66, -76]
R = {name: i for i, name in enumerate(
    ["skull1", "skull2", "skull3", "forehead", "browTop", "browLow", "lidTop", "eye", "lidLow", "cheek", "noseTip",
     "noseBase", "lipTop", "mouth", "lipLow", "chinTop", "chinLow", "jawUnder", "neck"])}
# rows that only matter on the face: behind the ears they fold into the nearest main row, so the back of the head
# is not striped with thin bands (the folded quads become triangles, like a hand-made low-poly)
FACE_ROWS = {"lidTop": "browLow", "eye": "cheek", "lidLow": "cheek", "noseTip": "cheek", "noseBase": "cheek",
             "lipTop": "chinTop", "mouth": "chinTop", "lipLow": "chinTop"}
BACK_FROM = 110  # azimuth from which face rows fold
HALF = [0, 10, 17, 24, 33, 45, 60, 80, 120, 180]  # azimuth of the right-half columns (0 = front centre)
COLS = HALF + [-u for u in HALF[-2:0:-1]]  # full loop: 0 .. 180 on the right, then back on the left
NC = len(COLS)
EYE_COLS = (1, 4)  # right-half column indices: the eye patch spans HALF[1]..HALF[4]
EYE_ROWS = (R["lidTop"], R["lidLow"])

SKIN = (0.92, 0.66, 0.47, 1)
LIP = (0.78, 0.46, 0.4, 1)
BROW = (0.22, 0.13, 0.08, 1)
WHITE = (0.95, 0.94, 0.9, 1)
IRIS = (0.1, 0.07, 0.05, 1)


def ray_dir(u, v):
    a, e = math.radians(u), math.radians(v)
    return (math.cos(e) * math.sin(a), math.sin(e), math.cos(e) * math.cos(a))


def first_exit(sdf, origin, dirs, tmax=0.3, step=0.0005):
    n = len(dirs)
    t_in, t_out = np.zeros(n), np.full(n, tmax)
    open_ = np.ones(n, bool)
    t = step
    while t < tmax and open_.any():
        idx = np.nonzero(open_)[0]
        out = sdf(origin + dirs[idx] * t) > 0
        t_out[idx[out]] = t
        open_[idx[out]] = False
        t_in[idx[~out]] = t
        t += step
    for _ in range(16):
        mid = (t_in + t_out) / 2
        out = sdf(origin + dirs * mid[:, None]) > 0
        t_out = np.where(out, mid, t_out)
        t_in = np.where(out, t_in, mid)
    return origin + dirs * ((t_in + t_out) / 2)[:, None]


# ---------- the eye: boundary of the grid patch, then two inset rings, in (azimuth, elevation) ----------
u0, u1 = HALF[EYE_COLS[0]], HALF[EYE_COLS[1]]
vt, vb = ROWS[EYE_ROWS[0]], ROWS[EYE_ROWS[1]]
vm = ROWS[R["eye"]]
eye_border = ([(HALF[c], vt) for c in range(EYE_COLS[0], EYE_COLS[1] + 1)] + [(u1, vm)]
              + [(HALF[c], vb) for c in range(EYE_COLS[1], EYE_COLS[0] - 1, -1)] + [(u0, vm)])
ec_u, ec_v = (u0 + u1) / 2, vm + 0.5


def almond(scale_u, scale_v, pinch):
    """Inset ring through the border points: corners pulled to the middle height (an almond), outer corner up."""
    ring = []
    for u, v in eye_border:
        du, dv = (u - ec_u) * scale_u, (v - ec_v) * scale_v
        edge = abs(u - ec_u) / ((u1 - u0) / 2)  # 1 at the corners
        dv *= 1 - pinch * edge ** 2
        lift = 1.2 * (u - ec_u) / ((u1 - u0) / 2)  # outer corner sits higher
        ring.append((ec_u + du, ec_v + dv + lift * scale_v))
    return ring


eye_lid = almond(0.86, 0.9, 0.6)
eye_iris = almond(0.3, 0.5, 0.25)

# ---------- positions (right half by ray, left half mirrored) ----------
keys, dirs = [], []
for r, v in enumerate(ROWS):
    for c, u in enumerate(HALF):
        keys.append(("g", r, c))
        dirs.append(ray_dir(u, v))
for i, (u, v) in enumerate(eye_lid):
    keys.append(("lid", i))
    dirs.append(ray_dir(u, v))
for i, (u, v) in enumerate(eye_iris):
    keys.append(("iris", i))
    dirs.append(ray_dir(u, v))
keys += [("top",), ("bottom",)]
dirs += [(0, 1, 0), (0, -1, 0)]
NECK_CUT = -0.165


def shape(p):
    return np.maximum(H.head_sdf(p), -(p[:, 1] - NECK_CUT))  # shorter neck than head_lowpoly's


pts = first_exit(shape, CENTER, np.array(dirs, dtype=float))
P = dict(zip(keys, pts))

# mouth line pressed in between the lips
for c in range(3):
    p = P["g", R["mouth"], c]
    P["g", R["mouth"], c] = p - (p - CENTER) / np.linalg.norm(p - CENTER) * 0.0025
# the iris sits slightly behind the white
for i in range(len(eye_iris)):
    p = P["iris", i]
    P["iris", i] = p - (p - CENTER) / np.linalg.norm(p - CENTER) * 0.0008

verts, index = [], {}


def vid(key, side):
    """Vertex index of a right-half key on side +1 or its mirror on side -1 (centre-line points are shared)."""
    p = P[key]
    on_line = abs(p[0]) < 1e-9 or (key[0] == "g" and HALF[key[2]] in (0, 180)) or key[0] in ("top", "bottom")
    s = 1 if on_line else side
    k = (key, s)
    if k not in index:
        index[k] = len(verts)
        verts.append((s * p[0], p[1], p[2]))
    return index[k]


def gcol(ci):
    """Full-loop column index -> (right-half column, side)."""
    u = COLS[ci]
    return (HALF.index(abs(u)), 1 if u >= 0 else -1)


faces, colors = [], []


def face(ids, col=SKIN):
    out = []
    for i in ids:  # drop repeated corners (folded rows): a quad with one folded edge becomes a triangle
        if not out or out[-1] != i:
            out.append(i)
    if len(out) > 1 and out[0] == out[-1]:
        out.pop()
    if len(out) >= 3:
        faces.append(out)
        colors.append(col)


ROW_NAME = {i: n for n, i in R.items()}


def gk(r, hc):
    """Grid key of row r, right-half column hc, after folding face rows at the back."""
    name = ROW_NAME[r]
    if HALF[hc] >= BACK_FROM and name in FACE_ROWS:
        r = R[FACE_ROWS[name]]
    return ("g", r, hc)


def in_eye(r, hc):
    return EYE_ROWS[0] <= r < EYE_ROWS[1] and EYE_COLS[0] <= hc < EYE_COLS[1]


for r in range(len(ROWS) - 1):
    for ci in range(NC):
        cj = (ci + 1) % NC
        (ha, sa), (hb, sb) = gcol(ci), gcol(cj)
        side = sa if HALF[ha] not in (0, 180) else sb
        hc = min(ha, hb)  # right-half quad index
        if in_eye(r, hc) and abs(ha - hb) == 1:
            continue
        col = SKIN
        if r == R["browTop"] and 1 <= hc < 4:  # band from browTop down to browLow
            col = BROW
        if r in (R["lipTop"], R["mouth"]) and hc < 2:
            col = LIP
        face([vid(gk(r, ha), side), vid(gk(r, hb), side), vid(gk(r + 1, hb), side), vid(gk(r + 1, ha), side)], col)
for ci in range(NC):
    cj = (ci + 1) % NC
    (ha, sa), (hb, sb) = gcol(ci), gcol(cj)
    side = sa if HALF[ha] not in (0, 180) else sb
    face([vid(("top",), 1), vid(("g", 0, hb), side), vid(("g", 0, ha), side)])
    last = len(ROWS) - 1
    face([vid(("g", last, ha), side), vid(("g", last, hb), side), vid(("bottom",), 1)])

# eyes on both sides: border -> lid ring (skin), lid -> iris ring (white), iris -> centre fan (iris)
border_keys = []
for u, v in eye_border:
    r = ROWS.index(v)
    border_keys.append(("g", r, HALF.index(u)))
for side in (1, -1):
    n = len(eye_border)
    b = [vid(k, side) for k in border_keys]
    l = [vid(("lid", i), side) for i in range(n)]
    ir = [vid(("iris", i), side) for i in range(n)]
    for i in range(n):
        j = (i + 1) % n
        face([b[i], b[j], l[j], l[i]])
        face([l[i], l[j], ir[j], ir[i]], WHITE)
    face(ir, IRIS)  # one polygon, split into triangles below

bpy.ops.wm.read_factory_settings(use_empty=True)
me = bpy.data.meshes.new("Head")
me.from_pydata([(p[0], -p[2], p[1]) for p in verts], [], faces)
me.update()
mats = {}
for col in (SKIN, LIP, BROW, WHITE, IRIS):
    m = bpy.data.materials.new(f"m{len(mats)}")
    m.diffuse_color = col
    me.materials.append(m)
    mats[col] = len(mats)
for p, col in zip(me.polygons, colors):
    p.material_index = mats[col]
head = bpy.data.objects.new("Head", me)
bpy.context.collection.objects.link(head)

# ears: one ear shape, decimated, and its exact mirror
ear = H.ray_shell(H.ear_sdf, H.EAR_C, 4, 0.06)
dec = ear.modifiers.new("d", "DECIMATE")
dec.ratio = EAR_TRIS / len(ear.data.polygons)
dg = bpy.context.evaluated_depsgraph_get()
em = bpy.data.meshes.new_from_object(ear.evaluated_get(dg))
ear.modifiers.clear()
ear.data = em
ear.data.materials.append(me.materials[0])
right = ear.copy()
right.data = ear.data.copy()
bpy.context.collection.objects.link(right)
right.scale.x = -1
bpy.ops.object.select_all(action="DESELECT")
for ob in (head, ear, right):
    ob.select_set(True)
bpy.context.view_layer.objects.active = head
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
bpy.ops.object.join()
head.name = "Head"
bm = bmesh.new()
bm.from_mesh(head.data)
bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
bm.to_mesh(head.data)
bm.free()
for p in head.data.polygons:
    p.use_smooth = False

# ---------- symmetry check ----------
from mathutils import kdtree  # noqa: E402
vs = head.data.vertices
kd = kdtree.KDTree(len(vs))
for v in vs:
    kd.insert(v.co, v.index)
kd.balance()
miss = sum(1 for v in vs if kd.find((-v.co.x, v.co.y, v.co.z))[2] > 1e-6)
tri_r = sum(len(p.vertices) - 2 for p in head.data.polygons if p.center.x > 1e-6)
tri_l = sum(len(p.vertices) - 2 for p in head.data.polygons if p.center.x < -1e-6)
tris = sum(len(p.vertices) - 2 for p in head.data.polygons)
print(f"HEAD_SYM unmatched_vertices={miss} tris_right={tri_r} tris_left={tri_l}")

# ---------- render: colour sheet and wire sheet ----------
scene = bpy.context.scene
world = bpy.data.worlds.new("w")
world.color = (0.035, 0.037, 0.04)
scene.world = world
scene.render.engine = "BLENDER_WORKBENCH"
scene.display.shading.light = "STUDIO"
scene.display.shading.color_type = "MATERIAL"
scene.render.resolution_x = 700
scene.render.resolution_y = 820
cam_data = bpy.data.cameras.new("cam")
cam_data.lens = 85
cam = bpy.data.objects.new("cam", cam_data)
bpy.context.collection.objects.link(cam)
scene.camera = cam
target = np.array([0.0, 0.0, -0.035])
views = {"front": 0, "34": 38, "side": 90}


def shoot(tag):
    for name, deg in views.items():
        a = math.radians(deg)
        pos = target + np.array([math.sin(a) * 0.8, -math.cos(a) * 0.8, 0.03])
        cam.location = pos.tolist()
        fwd = target - pos
        cam.rotation_euler = (math.atan2(math.hypot(fwd[0], fwd[1]), -fwd[2]), 0, math.atan2(-fwd[0], fwd[1]))
        scene.render.filepath = os.path.join(REN, f"{tag}_{name}.png")
        bpy.ops.render.render(write_still=True)
    imgs = [bpy.data.images.load(os.path.join(REN, f"{tag}_{n}.png")) for n in views]
    w, h = imgs[0].size
    sheet = np.zeros((h, w * len(imgs), 4), dtype=np.float32)
    for i, im in enumerate(imgs):
        sheet[:, i * w:(i + 1) * w] = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)
    out = bpy.data.images.new(tag, w * len(imgs), h, alpha=True)
    out.pixels = sheet.ravel()
    out.filepath_raw = os.path.join(REN, f"{tag}_sheet.png")
    out.file_format = "PNG"
    out.save()


shoot(TAG)
wire = head.copy()
wire.data = head.data.copy()
bpy.context.collection.objects.link(wire)
wm = wire.modifiers.new("wire", "WIREFRAME")
wm.thickness = 0.00035
wm.use_replace = True
edge = bpy.data.materials.new("edge")
edge.diffuse_color = (0.15, 0.15, 0.16, 1)
wire.data.materials.clear()
wire.data.materials.append(edge)
grey = bpy.data.materials.new("grey")
grey.diffuse_color = (0.62, 0.62, 0.63, 1)
saved = [m for m in head.data.materials]
for i in range(len(head.data.materials)):
    head.data.materials[i] = grey
shoot(TAG + "_wire")
for i, m in enumerate(saved):
    head.data.materials[i] = m
bpy.data.objects.remove(wire)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "head.blend"))
print(f"HEAD_REPORT tris={tris}")
