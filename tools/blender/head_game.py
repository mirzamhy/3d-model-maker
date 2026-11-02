# Stylized low-poly male head for games, no hair, three levels of detail, exactly mirror-symmetric:
#   blender -b --factory-startup -P tools/blender/head_game.py            (all three levels)
#   HEAD_LODS=mid blender -b --factory-startup -P tools/blender/head_game.py
#
# How it is built:
#  1. The head shape (skull, angular jaw, square chin, cheekbones, brow ridge, eye sockets with lids, nose,
#     lips, neck muscles) comes from head_lowpoly.head_sdf, without the eyeballs. Ears and a shoulder base
#     are their own shapes. Each is sampled densely and the parts are merged into one closed mesh (voxel remesh).
#  2. Only the right half (x >= 0) is kept and decimated to the triangle budget, so the triangles follow the
#     shape: dense at the eyes, nose, mouth and ears, large on the skull. The half is then mirrored and welded
#     on the centre line, so both sides have the same vertices and the same number of triangles.
#  3. Eyeballs (white with a brown iris) and eyebrows (thin slabs on the brow) are separate meshes.
#  4. Every count printed and written to stats_<lod>.json is read from the Blender meshes.
# Output: output/head-game/head_<lod>.blend and .glb, stats_<lod>.json, renders/game_<lod>_*.png.
# Head coordinates in this file: x to the character's left, y up, z forward, metres, y = 0 at eye level.
# Blender coordinates: (x, -z, y), i.e. the face looks toward -Y and Z is up.
import bpy
import bmesh
import json
import math
import os
import sys
import numpy as np
from mathutils import Matrix, Vector, kdtree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import head_lowpoly as H  # noqa: E402  (shape functions only)

ROOT = r"C:\Mirza Personal\model 3d maker"
OUT = os.path.join(ROOT, "output", "head-game")
REN = os.path.join(ROOT, "renders")
os.makedirs(OUT, exist_ok=True)

# triangle budget of Head_Main (head, neck, shoulder base, ears) and eye sphere resolution per level
LODS = {
    "low": {"head": 520, "eye": (8, 5)},
    "mid": {"head": 900, "eye": (10, 6)},
    "high": {"head": 1560, "eye": (12, 8)},
}
SKIN = (0.88, 0.66, 0.5, 1)
LIP = (0.74, 0.47, 0.42, 1)
BROW = (0.2, 0.12, 0.07, 1)
EYE_WHITE = (0.86, 0.85, 0.82, 1)
IRIS = (0.33, 0.2, 0.11, 1)
PUPIL = (0.05, 0.04, 0.03, 1)
EYE_C = H.V(0.031, 0.002, 0.0655)  # eyeball centre (left eye; mirrored for the right), sunk behind the lids
EYE_R = 0.0128


def bl(p):
    return Vector((p[0], -p[2], p[1]))


def head_coords(v):
    return np.array([v[0], v[2], -v[1]])


def shoulders_sdf(p):
    q = p.copy()
    q[:, 0] = np.abs(q[:, 0])
    d = H.ellipsoid(q, H.V(0, -0.2, -0.01), H.V(0.14, 0.042, 0.085))  # top of chest and back
    d = H.smin(d, H.capsule(q, H.V(0.03, -0.15, -0.022), H.V(0.13, -0.19, -0.018), 0.03), 0.03)  # trapezius
    return np.maximum(d, -(q[:, 1] + 0.225))  # flat cut under the shoulder base


EYELESS = os.environ.get("HEAD_EYELESS", "0") == "1"  # no eyes: a shallow hollow under each brow instead
SUFFIX = "_eyeless" if EYELESS else ""


def head_only_sdf(p):
    d = H.head_sdf(p, eyeball=False, neck_cut=None, eyeless=EYELESS)
    q = p.copy()
    q[:, 0] = np.abs(q[:, 0])
    d = H.smin(d, H.capsule(q, H.V(0, -0.2, -0.008), H.V(0, -0.1, -0.012), 0.051), 0.015)  # thicker male neck
    return np.maximum(d, -(q[:, 1] + 0.175))


def apply_modifier(ob, mod):
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    ob.modifiers.remove(mod)
    old = ob.data
    ob.data = me
    bpy.data.meshes.remove(old)


def dense_body():
    """Head + neck + ears + shoulder base as one closed dense mesh (Blender coordinates)."""
    head = H.ray_shell(head_only_sdf, H.V(0, -0.02, 0.0), 6, 0.3)
    ear = H.ray_shell(H.ear_sdf, H.EAR_C, 5, 0.06)
    ear2 = ear.copy()
    ear2.data = ear.data.copy()
    bpy.context.collection.objects.link(ear2)
    ear2.scale.x = -1
    sh = H.ray_shell(shoulders_sdf, H.V(0, -0.195, -0.01), 6, 0.3)  # the ray origin must be inside the shape
    bpy.ops.object.select_all(action="DESELECT")
    for ob in (head, ear, ear2, sh):
        ob.select_set(True)
    bpy.context.view_layer.objects.active = head
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bpy.ops.object.join()
    rm = head.modifiers.new("remesh", "REMESH")
    rm.mode = "VOXEL"
    rm.voxel_size = 0.0011
    apply_modifier(head, rm)
    return head


def half_decimate_mirror(ob, tris_total):
    """Keep x >= 0, decimate it to half the budget, mirror and weld: exact left/right symmetry."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(0, 0, 0), plane_no=(1, 0, 0), clear_inner=True)
    bm.to_mesh(ob.data)
    bm.free()
    tris = sum(len(p.vertices) - 2 for p in ob.data.polygons)
    dec = ob.modifiers.new("decimate", "DECIMATE")
    dec.decimate_type = "COLLAPSE"
    dec.ratio = (tris_total / 2) / tris
    dec.use_collapse_triangulate = True
    apply_modifier(ob, dec)
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    # the open edge on the centre line must stay on x = 0, and nothing may cross it
    seam = {v for e in bm.edges if e.is_boundary for v in e.verts}
    for v in bm.verts:
        if v in seam or v.co.x < 0:
            v.co.x = 0.0
    mirror = bmesh.ops.duplicate(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:])
    mverts = [g for g in mirror["geom"] if isinstance(g, bmesh.types.BMVert)]
    mfaces = [g for g in mirror["geom"] if isinstance(g, bmesh.types.BMFace)]
    for v in mverts:
        v.co.x = -v.co.x
    bmesh.ops.reverse_faces(bm, faces=mfaces)
    bmesh.ops.remove_doubles(bm, verts=[v for v in bm.verts if abs(v.co.x) < 1e-7], dist=1e-6)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(ob.data)
    bm.free()


def material(name, color):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.diffuse_color = color
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Roughness"].default_value = 0.85
    return m


def paint_lips(ob):
    skin, lip = material("Skin", SKIN), material("Lips", LIP)
    ob.data.materials.append(skin)
    ob.data.materials.append(lip)
    for p in ob.data.polygons:
        x, y, z = head_coords(p.center)
        p.material_index = 1 if abs(x) < 0.022 and -0.087 < y < -0.06 and z > 0.072 else 0


def eyeball(name, side, segs):
    u, v = segs
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=u, v_segments=v, radius=EYE_R)
    # poles along the view axis: the front pole fan becomes the iris
    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.pi / 2, 3, "X"))
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    ob.location = bl((side * EYE_C[0], EYE_C[1], EYE_C[2]))
    for m in (material("EyeWhite", EYE_WHITE), material("Iris", IRIS), material("Pupil", PUPIL)):
        me.materials.append(m)
    for p in me.polygons:
        ang = math.degrees(Vector((0, -1, 0)).angle(p.center.normalized()))
        p.material_index = 2 if ang < 11 else 1 if ang < 30 else 0
    tri(ob)
    return ob


def eyebrow(name, side, head):
    """Thin slab following the brow: 5 stations from inner to outer end, lying on the head surface."""
    stations = [(0.012, 0.0215, 0.0085), (0.021, 0.0255, 0.0078), (0.031, 0.0275, 0.0068), (0.041, 0.0268, 0.0055),
                (0.05, 0.0225, 0.0038)]  # (x, centre y, height) in head coordinates
    lift_lo, lift_hi = 0.0006, 0.0028
    rows = {k: [] for k in ("sb", "st", "lb", "lt")}  # skin bottom/top, lifted bottom/top
    for x, y, h in stations:
        for edge, yy in (("b", y - h / 2), ("t", y + h / 2)):
            hit, loc, nrm, _ = head.ray_cast(bl((side * x, yy, 0.2)), Vector((0, 1, 0)))
            if not hit:
                raise RuntimeError(f"eyebrow ray missed at {(x, yy)}")
            rows["s" + edge].append(loc + nrm * lift_lo)
            rows["l" + edge].append(loc + nrm * lift_hi)
    verts, faces = [], []
    idx = {}
    for k, pts in rows.items():
        idx[k] = list(range(len(verts), len(verts) + len(pts)))
        verts += [tuple(p) for p in pts]
    n = len(stations)
    for i in range(n - 1):
        for a, b in (("lb", "lt"), ("lt", "st"), ("st", "sb"), ("sb", "lb")):  # front, top, back, bottom
            faces.append((idx[a][i], idx[a][i + 1], idx[b][i + 1], idx[b][i]))
    for i in (0, n - 1):  # end caps
        faces.append((idx["lb"][i], idx["lt"][i], idx["st"][i], idx["sb"][i]))
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    me.materials.append(material("Eyebrow", BROW))
    return ob


def tri(ob):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bm.to_mesh(ob.data)
    bm.free()


def flat(ob):
    for p in ob.data.polygons:
        p.use_smooth = False


def stats(ob):
    me = ob.data
    return {"vertices": len(me.vertices), "edges": len(me.edges), "faces": len(me.polygons),
            "triangles": sum(len(p.vertices) - 2 for p in me.polygons)}


def closed(ob):
    """True when every edge has exactly two faces (no holes, no overlapping sheets)."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    ok = all(e.is_manifold for e in bm.edges)
    bm.free()
    return ok


def symmetry(ob):
    vs = ob.data.vertices
    kd = kdtree.KDTree(len(vs))
    for v in vs:
        kd.insert(v.co, v.index)
    kd.balance()
    unmatched = sum(1 for v in vs if kd.find((-v.co.x, v.co.y, v.co.z))[2] > 1e-6)
    right = sum(1 for p in ob.data.polygons if p.center.x > 1e-7)
    left = sum(1 for p in ob.data.polygons if p.center.x < -1e-7)
    return {"unmatched_vertices": unmatched, "triangles_x_pos": right, "triangles_x_neg": left}


# ---------------- rendering ----------------
def setup_render():
    scene = bpy.context.scene
    world = bpy.data.worlds.new("w")
    world.color = (0.035, 0.037, 0.04)
    scene.world = world
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    cam.data.lens = 85
    bpy.context.collection.objects.link(cam)
    scene.camera = cam
    return scene, cam


def look(cam, pos, target):
    pos, target = Vector(pos), Vector(target)
    cam.location = pos
    cam.rotation_euler = (target - pos).to_track_quat("-Z", "Y").to_euler()


def shoot(scene, cam, path, pos, target, res=(700, 820)):
    scene.render.resolution_x, scene.render.resolution_y = res
    look(cam, pos, target)
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    return path


def sheet(paths, out):
    imgs = [bpy.data.images.load(p) for p in paths]
    w, h = imgs[0].size
    arr = np.zeros((h, w * len(imgs), 4), dtype=np.float32)
    for i, im in enumerate(imgs):
        arr[:, i * w:(i + 1) * w] = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)
    img = bpy.data.images.new(os.path.basename(out), w * len(imgs), h, alpha=True)
    img.pixels = arr.ravel()
    img.filepath_raw = out
    img.file_format = "PNG"
    img.save()
    for im in imgs:
        bpy.data.images.remove(im)


def wire_overlay(objs, thickness):
    edge = material("WireEdge", (0.1, 0.1, 0.11, 1))
    made = []
    for ob in objs:
        w = ob.copy()
        w.data = ob.data.copy()
        bpy.context.collection.objects.link(w)
        w.data.materials.clear()
        w.data.materials.append(edge)
        m = w.modifiers.new("wire", "WIREFRAME")
        m.thickness = thickness
        m.use_replace = True
        made.append(w)
    return made


def render_all(lod, objs):
    scene, cam = setup_render()
    tgt = (0, 0, -0.06)
    d = 0.95
    views = {"front": (0, -d, -0.03), "34": (d * 0.62, -d * 0.78, -0.02), "side": (d, 0, -0.03), "back": (-d * 0.35, d * 0.94, -0.01)}
    p = lambda n: os.path.join(REN, f"game_{lod}_{n}.png")
    sheet([shoot(scene, cam, p(n), v, tgt) for n, v in views.items()], p("sheet"))
    # wireframe: grey surface with dark edges
    grey = material("Grey", (0.62, 0.62, 0.63, 1))
    saved = {ob.name: list(ob.data.materials) for ob in objs}
    for ob in objs:
        for i in range(len(ob.data.materials)):
            ob.data.materials[i] = grey
    wires = wire_overlay(objs, 0.00028)
    sheet([shoot(scene, cam, p("wire_front"), views["front"], tgt), shoot(scene, cam, p("wire_side"), views["side"], tgt)],
          p("wire_sheet"))
    # close-ups with colour back on and thinner edges
    for w in wires:
        bpy.data.objects.remove(w)
    for ob in objs:
        for i, m in enumerate(saved[ob.name]):
            ob.data.materials[i] = m
    wires = wire_overlay(objs, 0.00012)
    close = {
        "eye": (bl((0.031, 0.002, 0.07)), bl((0.07, 0.01, 0.26))),
        "nose": (bl((0.0, -0.03, 0.095)), bl((0.11, -0.02, 0.24))),
        "mouth": (bl((0.0, -0.075, 0.085)), bl((0.07, -0.07, 0.25))),
        "ear": (bl((0.075, -0.01, -0.02)), bl((0.26, 0.0, -0.05))),
    }
    sheet([shoot(scene, cam, p(f"close_{n}"), pos, t, (600, 600)) for n, (t, pos) in close.items()], p("close_sheet"))
    for w in wires:
        bpy.data.objects.remove(w)
    bpy.data.objects.remove(cam)


def build(lod):
    cfg = LODS[lod]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    head = dense_body()
    head.name = "Head_Main"
    head.data.name = "Head_Main"
    half_decimate_mirror(head, cfg["head"])
    paint_lips(head)
    eyes = [] if EYELESS else [eyeball("Eye_L", 1, cfg["eye"]), eyeball("Eye_R", -1, cfg["eye"])]
    brow_l = eyebrow("Eyebrow_L", 1, head)
    brow_r = eyebrow("Eyebrow_R", -1, head)
    objs = [head, *eyes, brow_l, brow_r]
    lod = lod + SUFFIX
    for ob in objs:
        flat(ob)
    # origins: everything sits around the world origin; the head's origin is at the neck base for rigging later
    st = {ob.name: stats(ob) for ob in objs}
    total = {k: sum(s[k] for s in st.values()) for k in ("vertices", "edges", "faces", "triangles")}
    report = {"lod": lod, "objects": st, "total": total, "head_symmetry": symmetry(head), "head_closed": closed(head)}
    with open(os.path.join(OUT, f"stats_{lod}.json"), "w") as f:
        json.dump(report, f, indent=2)
    print("GAME_STATS " + json.dumps(report))
    render_all(lod, objs)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, f"head_{lod}.blend"))
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, f"head_{lod}.glb"), export_format="GLB")


if __name__ == "__main__":
    for lod in os.environ.get("HEAD_LODS", "low,mid,high").split(","):
        build(lod.strip())
