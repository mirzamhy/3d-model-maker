# Low-poly human head built in Blender (run headless):
#   blender -b --factory-startup -P tools/blender/head_lowpoly.py
# The head is described as a smooth signed-distance shape (skull, face, jaw line, cheekbones, brow, eye sockets,
# eyeballs, nose, lips, neck, ears). It is sampled densely by casting rays from inside, merged with a voxel remesh,
# then decimated (mirrored) to the triangle budget, so triangles gather at the nose, eyes, lips and ears and the
# flat areas become large planes. Writes output/head-lowpoly/head.blend and renders/head_b_*.png.
# Head coordinates in this file: x to the character's left, y up, z forward, metres, y = 0 at eye level.
import bpy
import math
import os
import numpy as np

ROOT = r"C:\Mirza Personal\model 3d maker"
OUT = os.path.join(ROOT, "output", "head-lowpoly")
REN = os.path.join(ROOT, "renders")
os.makedirs(OUT, exist_ok=True)
TARGET_TRIS = int(os.environ.get("HEAD_TRIS", "1600"))
TAG = os.environ.get("HEAD_TAG", "head_b")

V = lambda *a: np.array(a, dtype=float)


# ---------- distance functions (p: N x 3) ----------
def ellipsoid(p, c, r):
    q = (p - c) / r
    k0 = np.linalg.norm(q, axis=1)
    k1 = np.linalg.norm(q / r, axis=1)
    return k0 * (k0 - 1.0) / np.maximum(k1, 1e-9)


def capsule(p, a, b, r):
    pa, ba = p - a, b - a
    h = np.clip((pa @ ba) / (ba @ ba), 0.0, 1.0)
    return np.linalg.norm(pa - h[:, None] * ba, axis=1) - r


def sphere(p, c, r):
    return np.linalg.norm(p - c, axis=1) - r


def smin(a, b, k):
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0.0, 1.0)
    return b + (a - b) * h - k * h * (1.0 - h)


def smax(a, b, k):
    return -smin(-a, -b, k)


def hull(points):
    """Distance-like function of the convex hull of `points` (x >= 0 points are mirrored): flat planes, sharp edges."""
    import bmesh
    pts = [V(*p) for p in points]
    pts += [V(-p[0], p[1], p[2]) for p in pts if p[0] > 1e-6]
    bm = bmesh.new()
    for p in pts:
        bm.verts.new(p.tolist())
    bmesh.ops.convex_hull(bm, input=bm.verts)
    cen = np.mean(pts, axis=0)
    N, D = [], []
    for f in bm.faces:
        if not f.is_valid:
            continue
        a, b, c = (np.array(v.co) for v in f.verts[:3])
        n = np.cross(b - a, c - a)
        if np.linalg.norm(n) < 1e-12:
            continue
        n /= np.linalg.norm(n)
        if n @ (a - cen) < 0:
            n = -n
        N.append(n)
        D.append(n @ a)
    bm.free()
    N, D = np.array(N), np.array(D)
    # hull is evaluated on mirrored q (x >= 0), which is fine because the hull is symmetric
    return lambda q: np.max(q @ N.T - D, axis=1)


ANGULAR = os.environ.get("HEAD_STYLE", "angular") == "angular"
# lower face: cheekbone, jaw angle under the ear, square chin, mouth front (one block with flat sides)
JAW = hull([(0.058, -0.012, 0.03), (0.047, -0.012, 0.062), (0.06, -0.03, -0.02), (0.058, -0.082, -0.004),
            (0.05, -0.05, 0.05), (0.03, -0.072, 0.073), (0.02, -0.098, 0.08), (0.019, -0.118, 0.071),
            (0.0, -0.075, 0.083), (0.0, -0.12, 0.07), (0.034, -0.108, 0.035), (0.0, -0.012, 0.075)])
NOSE = hull([(0.006, 0.008, 0.086), (0.0, -0.037, 0.107), (0.008, -0.038, 0.102), (0.016, -0.045, 0.09),
             (0.013, -0.028, 0.091), (0.0, -0.048, 0.094), (0.01, 0.002, 0.078), (0.016, -0.046, 0.08)])
BROW = hull([(0.0, 0.019, 0.089), (0.0, 0.034, 0.087), (0.026, 0.035, 0.084), (0.026, 0.016, 0.086),
             (0.052, 0.024, 0.062), (0.05, 0.038, 0.062), (0.0, 0.02, 0.07), (0.052, 0.02, 0.048)])
CHEEK = hull([(0.052, -0.004, 0.058), (0.062, -0.008, 0.03), (0.054, -0.03, 0.05), (0.04, -0.022, 0.068),
              (0.045, -0.01, 0.045)])


def head_sdf(p, eyeball=True, neck_cut=-0.19, eyeless=False):
    q = p.copy()
    q[:, 0] = np.abs(q[:, 0])  # every feature is defined for x >= 0 and mirrored
    d = ellipsoid(q, V(0, 0.031, -0.014), V(0.073, 0.086, 0.1))  # cranium
    if ANGULAR:
        d = smin(d, ellipsoid(q, V(0, -0.005, 0.03), V(0.06, 0.05, 0.06)), 0.01)  # forehead to cheek fill
        d = smin(d, JAW(q), 0.004)
        d = smin(d, CHEEK(q), 0.004)
        d = smin(d, BROW(q), 0.003)
    else:
        d = smin(d, ellipsoid(q, V(0, -0.025, 0.02), V(0.063, 0.07, 0.07)), 0.02)  # face mass
        d = smin(d, ellipsoid(q, V(0, -0.066, 0.042), V(0.034, 0.03, 0.043)), 0.014)  # muzzle (teeth arch)
        d = smin(d, capsule(q, V(0.052, -0.068, -0.018), V(0.018, -0.11, 0.058), 0.009), 0.02)  # jaw line
        d = smin(d, ellipsoid(q, V(0, -0.105, 0.062), V(0.021, 0.016, 0.017)), 0.016)  # chin
        d = smin(d, ellipsoid(q, V(0.045, -0.014, 0.052), V(0.019, 0.012, 0.02)), 0.014)  # cheekbone
        d = smin(d, capsule(q, V(0.0, 0.025, 0.083), V(0.047, 0.03, 0.064), 0.0105), 0.012)  # brow ridge
    if eyeless:
        # no eye at all: only a shallow, soft hollow under the brow where the eye would be
        d = smax(d, -ellipsoid(q, V(0.031, 0.003, 0.088), V(0.024, 0.015, 0.02)), 0.003)
        # sunken cheek under the cheekbone, above the jaw line
        d = smax(d, -ellipsoid(q, V(0.054, -0.05, 0.06), V(0.016, 0.018, 0.014)), 0.004)
    else:
        d = smax(d, -ellipsoid(q, V(0.031, 0.003, 0.09), V(0.024, 0.014, 0.02)), 0.003)  # eye socket
        if eyeball:  # off when the eyeballs are separate meshes
            d = smin(d, sphere(q, V(0.031, 0.002, 0.07), 0.0135), 0.0015)  # eyeball, mostly hidden by the lids
        d = smin(d, capsule(q, V(0.015, 0.006, 0.081), V(0.048, 0.01, 0.074), 0.0048), 0.002)  # upper lid
        d = smin(d, capsule(q, V(0.016, -0.007, 0.08), V(0.047, -0.004, 0.074), 0.0034), 0.002)  # lower lid
    if ANGULAR:
        d = smin(d, NOSE(q), 0.003)
    else:
        nose = capsule(q, V(0, 0.008, 0.086), V(0, -0.035, 0.105), 0.0072)  # bridge
        nose = smin(nose, sphere(q, V(0, -0.036, 0.103), 0.0102), 0.007)  # tip
        nose = smin(nose, ellipsoid(q, V(0.0105, -0.042, 0.092), V(0.0085, 0.0075, 0.0095)), 0.005)  # wing
        d = smin(d, nose, 0.006)
    d = smin(d, ellipsoid(q, V(0, -0.066, 0.082), V(0.023, 0.006, 0.0085)), 0.004)  # upper lip
    d = smin(d, ellipsoid(q, V(0, -0.0785, 0.079), V(0.02, 0.0066, 0.0085)), 0.004)  # lower lip
    d = smax(d, -ellipsoid(q, V(0, -0.0722, 0.091), V(0.024, 0.0016, 0.015)), 0.0015)  # mouth line
    neck = capsule(q, V(0, -0.24, -0.012), V(0, -0.06, -0.008), 0.046)
    neck = smin(neck, capsule(q, V(0, -0.2, 0.026), V(0, -0.105, 0.036), 0.016), 0.012)  # throat
    # the two neck muscles from behind the ear to the collarbone notch
    neck = smin(neck, capsule(q, V(0.036, -0.075, -0.022), V(0.012, -0.2, 0.036), 0.0095), 0.01)
    d = smin(d, neck, 0.012)
    return d if neck_cut is None else np.maximum(d, -(q[:, 1] - neck_cut))  # neck cut


EAR_C = V(0.071, -0.008, -0.02)


def ear_sdf(p):
    q = p.copy()
    q[:, 0] = np.abs(q[:, 0])
    c = EAR_C
    a = math.radians(30)  # back edge flares out
    rel = q - c
    lx = rel[:, 0] * math.cos(a) + rel[:, 2] * math.sin(a)
    lz = -rel[:, 0] * math.sin(a) + rel[:, 2] * math.cos(a)
    L = np.stack([lx, rel[:, 1], lz], axis=1)
    d = ellipsoid(L, V(0, 0.003, -0.002), V(0.0065, 0.027, 0.016))
    d = smin(d, ellipsoid(L, V(-0.002, -0.02, 0.003), V(0.0055, 0.009, 0.008)), 0.003)  # lobe
    d = smax(d, -ellipsoid(L, V(0.0075, 0.0, 0.0), V(0.005, 0.016, 0.0095)), 0.0025)  # bowl
    return d


# ---------- surface by casting rays from an inside point ----------
def ray_shell(sdf, center, subdiv, tmax, step=0.0008):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=subdiv, radius=1.0)
    ob = bpy.context.active_object
    me = ob.data
    n = len(me.vertices)
    dirs = np.empty(n * 3)
    me.vertices.foreach_get("co", dirs)
    dirs = dirs.reshape(n, 3)
    dirs /= np.linalg.norm(dirs, axis=1)[:, None]
    t_in = np.zeros(n)
    t_out = np.full(n, tmax)
    open_ = np.ones(n, bool)
    t = step
    while t < tmax and open_.any():
        idx = np.nonzero(open_)[0]
        out = sdf(center + dirs[idx] * t) > 0
        hit = idx[out]
        t_out[hit] = t
        open_[hit] = False
        t_in[idx[~out]] = t
        t += step
    for _ in range(14):
        mid = (t_in + t_out) / 2
        out = sdf(center + dirs * mid[:, None]) > 0
        t_out = np.where(out, mid, t_out)
        t_in = np.where(out, t_in, mid)
    pts = center + dirs * ((t_in + t_out) / 2)[:, None]
    blender = np.stack([pts[:, 0], -pts[:, 2], pts[:, 1]], axis=1)  # head (x, y up, z fwd) -> Blender (x, -y fwd, z up)
    me.vertices.foreach_set("co", blender.ravel())
    me.update()
    return ob


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    head = ray_shell(head_sdf, V(0, -0.02, 0.0), 6, 0.3)
    ear = ray_shell(ear_sdf, EAR_C, 4, 0.06)


    def apply(ob, mod):
        dg = bpy.context.evaluated_depsgraph_get()
        me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
        ob.modifiers.remove(mod)
        old = ob.data
        ob.data = me
        bpy.data.meshes.remove(old)


    def decimate(ob, n_tris, sym=True, face_weight=False):
        tris = sum(len(p.vertices) - 2 for p in ob.data.polygons)
        dec = ob.modifiers.new("decimate", "DECIMATE")
        dec.decimate_type = "COLLAPSE"
        dec.ratio = min(1.0, n_tris / tris)
        dec.use_symmetry = sym
        dec.symmetry_axis = "X"
        dec.use_collapse_triangulate = True
        if face_weight:
            # spend the budget on the face: front of the head between chin and brow keeps its detail
            vg = ob.vertex_groups.new(name="detail")
            for v in ob.data.vertices:
                x, y, z = v.co  # Blender coords: -y is forward, z up
                fwd = min(1.0, max(0.0, (-y - 0.02) / 0.04))
                band = min(1.0, max(0.0, (z + 0.135) / 0.02)) * min(1.0, max(0.0, (0.05 - z) / 0.02))
                vg.add([v.index], 0.15 + 0.85 * fwd * band, "REPLACE")
            dec.vertex_group = "detail"
            dec.invert_vertex_group = True  # in collapse mode a high weight collapses first; the face must collapse last
            dec.vertex_group_factor = float(os.environ.get("HEAD_VGF", "6"))
        apply(ob, dec)


    def to_quads(ob):
        # join triangle pairs that lie nearly in one plane, like the quads of a hand-made low-poly
        bpy.ops.object.select_all(action="DESELECT")
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.mesh.tris_convert_to_quads(face_threshold=math.radians(25), shape_threshold=math.radians(50))
        bpy.ops.object.mode_set(mode="OBJECT")


    def mirror_half(ob, half_tris):
        """Exactly symmetric result: keep the right half, simplify it, pin the centre seam to x = 0, mirror it."""
        import bmesh
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(0, 0, 0), plane_no=(-1, 0, 0), clear_outer=True)
        bm.to_mesh(ob.data)
        bm.free()
        decimate(ob, half_tris, sym=False)
        to_quads(ob)
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        for v in bm.verts:
            if v.is_boundary:
                v.co.x = 0.0
        bm.to_mesh(ob.data)
        bm.free()
        mm = ob.modifiers.new("mirror", "MIRROR")
        mm.use_axis = (True, False, False)
        mm.use_clip = True
        mm.use_mirror_merge = True
        mm.merge_threshold = 1e-5
        apply(ob, mm)

    def quadriflow(ob, faces, sym):
        # quads that follow the shape's curvature, like a hand-made low-poly
        bpy.ops.object.select_all(action="DESELECT")
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        ob.data.use_mirror_x = sym
        r = bpy.ops.object.quadriflow_remesh(mode="FACES", target_faces=faces, use_mesh_symmetry=sym,
                                             use_preserve_sharp=False, use_preserve_boundary=False, smooth_normals=False, seed=3)
        print("HEAD_QF", ob.name, r, len(ob.data.polygons))


    EAR_TRIS = int(os.environ.get("EAR_TRIS", "140"))
    if os.environ.get("HEAD_MODE", "tri") == "quad":
        quadriflow(head, (TARGET_TRIS - 2 * EAR_TRIS) // 2, True)
        quadriflow(ear, EAR_TRIS // 2, False)
    else:
        if os.environ.get("HEAD_SYM", "1") == "1":
            mirror_half(head, (TARGET_TRIS - 2 * EAR_TRIS) // 2)
        else:
            decimate(head, TARGET_TRIS - 2 * EAR_TRIS, face_weight=os.environ.get("HEAD_VGF") is not None)
            to_quads(head)
        decimate(ear, EAR_TRIS, False)
        to_quads(ear)

    # mirror the ear to the right side and join (the ears are their own shells, sunk into the head)
    right = ear.copy()
    right.data = ear.data.copy()
    bpy.context.collection.objects.link(right)
    right.scale.x = -1
    bpy.ops.object.select_all(action="DESELECT")
    for ob in [head, ear, right]:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = head
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bpy.ops.object.join()
    head.name = "Head"
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(head.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(head.data)
    bm.free()
    for p in head.data.polygons:
        p.use_smooth = False
    final_tris = sum(len(p.vertices) - 2 for p in head.data.polygons)
    from mathutils import kdtree
    vs = head.data.vertices
    kd = kdtree.KDTree(len(vs))
    for v in vs:
        kd.insert(v.co, v.index)
    kd.balance()
    miss = sum(1 for v in vs if kd.find((-v.co.x, v.co.y, v.co.z))[2] > 1e-6)
    tri_r = sum(len(p.vertices) - 2 for p in head.data.polygons if p.center.x > 1e-6)
    tri_l = sum(len(p.vertices) - 2 for p in head.data.polygons if p.center.x < -1e-6)
    print(f"HEAD_SYM unmatched_vertices={miss} tris_right={tri_r} tris_left={tri_l}")

    # ---------- colours by region (skin, lips, brows, eye white, iris); the mesh is mirrored, so are they ----------
    COL = {"skin": (0.92, 0.66, 0.47, 1), "lip": (0.78, 0.46, 0.4, 1), "brow": (0.22, 0.13, 0.08, 1),
           "white": (0.95, 0.94, 0.9, 1), "iris": (0.1, 0.07, 0.05, 1)}
    names = list(COL)
    for n in names:
        m = bpy.data.materials.new(n)
        m.diffuse_color = COL[n]
        head.data.materials.append(m)

    def region(c):
        x, y, z = abs(c.x), c.z, -c.y  # Blender -> head coordinates (mirrored to the right side)
        if x < 0.024 and -0.087 < y < -0.06 and z > 0.075:
            return "lip"
        return "skin"

    for p in head.data.polygons:
        p.material_index = names.index(region(p.center))

    # eyeballs and brows are their own small pieces (like a game model): built on the right, mirrored exactly
    def surface_z(x, y):
        """Front surface depth of the head shape at (x, y)."""
        z = 0.0
        while head_sdf(np.array([[x, y, z]]))[0] < 0 and z < 0.2:
            z += 0.0003
        return z

    def part(name, verts, faces, mats):
        me = bpy.data.meshes.new(name)
        me.from_pydata([(v[0], -v[2], v[1]) for v in verts], [], faces)
        for n in names:
            me.materials.append(bpy.data.materials[n])
        for p, m in zip(me.polygons, mats):
            p.material_index = names.index(m)
        ob = bpy.data.objects.new(name, me)
        bpy.context.collection.objects.link(ob)
        twin = ob.copy()
        twin.data = me.copy()
        bpy.context.collection.objects.link(twin)
        twin.scale.x = -1
        return [ob, twin]

    # eyeball: a low sphere looking forward, iris = the front cap
    ec, er = np.array([0.031, 0.002, 0.067]), 0.0128
    seg, rings = 8, [math.radians(a) for a in (34, 90, 140)]
    ev = [tuple(ec + [0, 0, er])]
    for t in rings:
        for s in range(seg):
            a = 2 * math.pi * s / seg
            ev.append(tuple(ec + er * np.array([math.sin(t) * math.cos(a), math.sin(t) * math.sin(a), math.cos(t)])))
    ev.append(tuple(ec - [0, 0, er]))
    ef, em = [], []
    for s in range(seg):
        ef.append((0, 1 + s, 1 + (s + 1) % seg))
        em.append("iris")
    for k in range(len(rings) - 1):
        for s in range(seg):
            a0, a1 = 1 + k * seg + s, 1 + k * seg + (s + 1) % seg
            ef.append((a0, a0 + seg, a1 + seg, a1))
            em.append("white")
    back = len(ev) - 1
    for s in range(seg):
        ef.append((1 + (len(rings) - 1) * seg + (s + 1) % seg, 1 + (len(rings) - 1) * seg + s, back))
        em.append("white")
    pieces = part("Eye", ev, ef, em)

    # brow: a thin block strip lying on the brow ridge, thick at the inner end
    st = [(0.016, 0.024, 0.0048), (0.033, 0.029, 0.0042), (0.051, 0.025, 0.0026)]
    bv = []
    for x, y, h in st:
        z = surface_z(x, y)
        for dz in (0.0025, -0.003):
            bv += [(x, y + h / 2, z + dz), (x, y - h / 2, z + dz)]  # top, bottom
    bf = []
    for i in range(len(st) - 1):
        a, b = 4 * i, 4 * (i + 1)
        bf += [(a, b, b + 1, a + 1), (a + 2, a, b, b + 2), (a + 1, b + 1, b + 3, a + 3), (a + 3, b + 3, b + 2, a + 2)]
    bf += [(0, 1, 3, 2), (4 * (len(st) - 1), 4 * (len(st) - 1) + 2, 4 * (len(st) - 1) + 3, 4 * (len(st) - 1) + 1)]
    pieces += part("Brow", bv, bf, ["brow"] * len(bf))

    bpy.ops.object.select_all(action="DESELECT")
    for ob in [head] + pieces:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = head
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bpy.ops.object.join()
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(head.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(head.data)
    bm.free()
    for p in head.data.polygons:
        p.use_smooth = False
    vs = head.data.vertices
    kd = kdtree.KDTree(len(vs))
    for v in vs:
        kd.insert(v.co, v.index)
    kd.balance()
    miss = sum(1 for v in vs if kd.find((-v.co.x, v.co.y, v.co.z))[2] > 1e-6)
    tri_r = sum(len(p.vertices) - 2 for p in head.data.polygons if p.center.x > 1e-6)
    tri_l = sum(len(p.vertices) - 2 for p in head.data.polygons if p.center.x < -1e-6)
    final_tris = sum(len(p.vertices) - 2 for p in head.data.polygons)
    print(f"HEAD_SYM with eyes and brows: unmatched_vertices={miss} tris_right={tri_r} tris_left={tri_l}")

    # ---------- render: colour sheet, then grey clay with dark edges like the reference sheet ----------
    scene = bpy.context.scene
    world = bpy.data.worlds.new("w")
    world.color = (0.035, 0.037, 0.04)
    scene.world = world
    scene.render.engine = "BLENDER_WORKBENCH"
    sh = scene.display.shading
    sh.light = "STUDIO"
    sh.color_type = "MATERIAL"
    sh.show_cavity = False
    scene.render.resolution_x = 700
    scene.render.resolution_y = 820
    scene.render.film_transparent = False

    cam_data = bpy.data.cameras.new("cam")
    cam_data.lens = 85
    cam = bpy.data.objects.new("cam", cam_data)
    bpy.context.collection.objects.link(cam)
    scene.camera = cam
    target = np.array([0.0, 0.0, -0.04])
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

    shoot(TAG + "_color")
    wire = head.copy()
    wire.data = head.data.copy()
    bpy.context.collection.objects.link(wire)
    wm = wire.modifiers.new("wire", "WIREFRAME")
    wm.thickness = 0.00035
    wm.use_replace = True
    dark = bpy.data.materials.new("edge")
    dark.diffuse_color = (0.18, 0.18, 0.19, 1)
    wire.data.materials.clear()
    wire.data.materials.append(dark)
    wire.color = (0.18, 0.18, 0.19, 1)
    sh.color_type = "OBJECT"
    head.color = (0.62, 0.62, 0.63, 1)
    shoot(TAG)
    bpy.data.objects.remove(wire)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "head.blend"))
    print(f"HEAD_REPORT tris={final_tris} verts={len(head.data.vertices)}")


if __name__ == "__main__":
    main()
