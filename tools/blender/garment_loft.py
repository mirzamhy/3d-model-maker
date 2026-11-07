# Garments with their own shape (not a copy of the skin): a loft of rings around the body, each ring from rays cast
# out of the body axis. Below the chest the radius is the largest body radius from the chest down to that ring
# ("drape": cloth hangs straight from the widest point, it does not follow the waist), plus an ease that grows
# toward the hem. Edges (collar rib, hem band, cuffs) are a step outward: a ledge that shows the cloth layer.
# Sleeves are their own tubes whose root sits inside the trunk shell (overlap, no weld), as in game low-poly.
# Weights come from the nearest body vertices (inverse distance), so loose cloth follows the bones under it.
# Used by clothes.py (garment spec with "builder": "shirt_loft").
import math

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

TRUNK, NECK, ARM, CROTCH = 1, 2, 3, 8
WALL = 0.004

# trunk columns: polar angle around the body axis, 0 = front (-y), 90 = character's left (+x)
TCOLS = [0, 25, 50, 90, 130, 155, 180]
ACOLS = [0, 45, 90, 135, 180, 225, 270, 315]  # sleeve: around the arm axis, 0 = up

SHIRT = dict(
    hem_z=0.955,        # hem bottom (world z): over the pants waist (pants top z 1.086)
    chest_z=1.245,      # drape starts here: below it the radius never shrinks
    armpit_z=1.30,
    belly_z=1.12,
    collar_ease=0.015, collar_rib=0.016, collar_step=0.004,
    shoulder_ease=0.007, chest_ease=0.012, belly_ease=0.020, hem_ease=0.026, hem_band=0.028, hem_step=0.006,
    sleeve_x=(0.12, 0.215, 0.265, 0.292, 0.318),  # root (inside trunk), cap, mid, cuff top, cuff bottom
    sleeve_ease=(0.0, 0.020, 0.018, 0.018), cuff_step=0.005,
    colour=(0.36, 0.38, 0.26), band=(0.29, 0.31, 0.21),
)


def lin(c):
    return tuple(ch ** 2.2 for ch in c) + (1.0,)


def full_cols(half):
    return half + [360 - c for c in half[-2:0:-1]]


def body_data(body):
    me = body.data
    mw = body.matrix_world
    co = np.array([mw @ v.co for v in me.vertices])
    part = np.array([d.value for d in me.attributes["part"].data])
    ring = np.array([d.value for d in me.attributes["ring"].data])
    return me, co, part, ring


def bvh(co, me, part, keep):
    polys = [list(p.vertices) for p in me.polygons if part[p.index] in keep]
    return BVHTree.FromPolygons([Vector(c) for c in co], polys)


def trunk_rows(me, part, ring):
    """Vertex sets of trunk rows 0 (neck base) and 1 (trapezius / shoulder top) from the band labels."""
    band = {}
    for p in me.polygons:
        if part[p.index] == TRUNK:
            band.setdefault(ring[p.index], set()).update(p.vertices)
    row1 = band[0] & band[1]
    return band[0] - row1, row1


def shirt(body, rig, mat, spec=None):
    S = dict(SHIRT, **(spec or {}))
    me, co, part, ring = body_data(body)
    trunk_v = np.array(sorted({v for p in me.polygons if part[p.index] == TRUNK for v in p.vertices}))

    def yc(z):  # body axis: middle of front and back of the trunk near this height
        near = trunk_v[np.abs(co[trunk_v, 2] - z) < 0.03]
        if not len(near):
            near = trunk_v
        return float((co[near, 1].min() + co[near, 1].max()) / 2)

    tb = bvh(co, me, part, (TRUNK, CROTCH))

    def ray(z, th):
        o = Vector((0.0, yc(z), z))
        d = Vector((math.sin(math.radians(th)), -math.cos(math.radians(th)), 0.0))
        hit = tb.ray_cast(o, d, 0.4)
        return hit[3] if hit[0] is not None else None

    # rows 0 / 1 as polar curves: (angle -> z, radius) on the left half, interpolated per column
    row0, row1 = trunk_rows(me, part, ring)

    def polar(vs):
        vs = list(vs)
        out = []
        for v in vs:
            x, y, z = co[v]
            c = yc(z)
            th = math.degrees(math.atan2(abs(x), -(y - c)))
            out.append((th, z, math.hypot(x, y - c)))
        out.sort()
        a = np.array(out)
        return lambda th: (float(np.interp(th, a[:, 0], a[:, 1])), float(np.interp(th, a[:, 0], a[:, 2])))

    p0_, p1 = polar(row0), polar(row1)
    nb = bvh(co, me, part, (NECK,))

    def p0(th):  # neck base, widened where the neck above it (up to the rib top) leans out further (front)
        z, r = p0_(th)
        a = math.radians(th)
        d = Vector((math.sin(a), -math.cos(a), 0.0))
        for zz in (z, z + S["collar_rib"] * 0.5, z + S["collar_rib"]):
            hit = nb.ray_cast(Vector((0.0, yc(z), zz)), d, 0.3)
            if hit[0] is not None:
                r = max(r, hit[3])
        return z, r


    # body radius samples from the hem up to the armpit (misses: arm hole -> nan)
    zs = np.arange(S["hem_z"] - 0.01, S["armpit_z"] + 0.001, 0.01)
    rb = {th: np.array([ray(z, th) or np.nan for z in zs]) for th in TCOLS}

    def drape(z, th):  # largest body radius from the chest down to z
        m = (zs >= z - 1e-6) & (zs <= S["chest_z"] + 1e-6)
        return float(np.nanmax(rb[th][m]))

    rings, band_rows = [], []  # each ring: {th: (z, r)}

    def add(fn, is_band=False):
        rings.append({th: fn(th) for th in TCOLS})
        band_rows.append(is_band)

    ce, rib, cs = S["collar_ease"], S["collar_rib"], S["collar_step"]
    add(lambda th: (p0(th)[0] + rib, p0(th)[1] + ce), True)   # rib top
    add(lambda th: (p0(th)[0] - 0.004, p0(th)[1] + ce + cs), False)    # rib bottom, outer
    add(lambda th: (p0(th)[0] - 0.004, p0(th)[1] + ce), False)         # ledge back onto the shirt
    def shoulder(th):  # trapezius row; the ray catches skin that bulges past the chord between row vertices
        z, r = p1(th)
        return z, max(r, ray(z, th) or 0.0) + S["shoulder_ease"]

    add(shoulder)  # shoulder line

    def armpit(th):
        r = ray(S["armpit_z"], th)
        if r is None:  # arm hole: between the shoulder line and the chest ring
            z1, r1 = p1(th)
            r2 = drape(S["chest_z"], th)
            t = (z1 - S["armpit_z"]) / max(1e-3, z1 - S["chest_z"])
            r = r1 + (r2 - r1) * t
        return S["armpit_z"], r + S["chest_ease"] * 0.8

    add(armpit)
    add(lambda th: (S["chest_z"], drape(S["chest_z"], th) + S["chest_ease"]))
    add(lambda th: (S["belly_z"], drape(S["belly_z"], th) + S["belly_ease"]))
    hb, hz = S["hem_band"], S["hem_z"]
    add(lambda th: (hz + hb, drape(hz + hb, th) + S["hem_ease"]), True)
    add(lambda th: (hz + hb, drape(hz + hb, th) + S["hem_ease"] + S["hem_step"]), True)
    add(lambda th: (hz, drape(hz, th) + S["hem_ease"] + S["hem_step"]), False)
    # hem band: the hem ring takes the larger of its own and the band-top radius (a straight band)
    for th in TCOLS:
        z, r = rings[-1][th]
        rings[-1][th] = (z, max(r, rings[-2][th][1]))
        rings[-2][th] = (rings[-2][th][0], max(r, rings[-2][th][1]))

    verts, faces, fband = [], [], []
    cols = full_cols(TCOLS)
    n = len(cols)
    for rg in rings:
        for c in cols:
            th = c if c <= 180 else 360 - c
            z, r = rg[th]
            s = 1 if c <= 180 else -1
            a = math.radians(th)
            verts.append((s * r * math.sin(a), yc(z) - r * math.cos(a), z))
    for i in range(len(rings) - 1):
        for k in range(n):
            k2 = (k + 1) % n
            faces.append([i * n + k, i * n + k2, (i + 1) * n + k2, (i + 1) * n + k])
            fband.append(band_rows[i])
    n_trunk_v = len(verts)

    # sleeves: rings around the upper-arm bone axis
    ub = rig.data.bones["upper_arm.L"]
    h0 = np.array(rig.matrix_world @ ub.head_local)
    t0 = np.array(rig.matrix_world @ ub.tail_local)
    u = (t0 - h0) / np.linalg.norm(t0 - h0)
    up = np.array([0.0, 0.0, 1.0]) - u * u[2]
    up /= np.linalg.norm(up)
    fw = np.cross(u, up)
    ab = bvh(co, me, part, (ARM, TRUNK))
    sx = S["sleeve_x"]

    def axis_at(x):
        return h0 + u * (x - h0[0]) / u[0]

    def arm_r(x, phi):
        a = math.radians(phi)
        d = up * math.cos(a) + fw * math.sin(a)
        hit = ab.ray_cast(Vector(axis_at(x)), Vector(d), 0.15)
        return hit[3] if hit[0] is not None else None

    xs_s = np.arange(sx[1], sx[-1] + 0.001, 0.01)
    ar = {phi: np.array([arm_r(x, phi) or np.nan for x in xs_s]) for phi in ACOLS}

    def sdrape(x, phi):
        m = xs_s <= x + 1e-6
        return float(np.nanmax(ar[phi][m]))

    se = S["sleeve_ease"]
    srings = [  # (x, {phi: r}, band)
        (sx[1], {p: sdrape(sx[1] + 0.02, p) + se[1] for p in ACOLS}, False),  # cap: also clears the armpit just outside it
        (sx[2], {p: sdrape(sx[2], p) + se[2] for p in ACOLS}, False),
        (sx[3], {p: sdrape(sx[3], p) + se[3] for p in ACOLS}, True),
        (sx[3], {p: sdrape(sx[3], p) + se[3] + S["cuff_step"] for p in ACOLS}, True),
        (sx[4], {p: sdrape(sx[4], p) + se[3] + S["cuff_step"] for p in ACOLS}, False),
    ]
    # root: the cap ring moved into the trunk shell under the shoulder line, smaller (hidden overlap): the sleeve
    # comes out of the trunk side wall like a set-in sleeve
    srings.insert(0, (sx[0], {p: srings[0][1][p] * 0.85 for p in ACOLS}, False))
    for s in (1, -1):
        base = len(verts)
        for x, rr, _ in srings:
            c = axis_at(x)
            for phi in ACOLS:
                a = math.radians(phi)
                p = c + (up * math.cos(a) + fw * math.sin(a)) * rr[phi]
                verts.append((s * p[0], p[1], p[2]))
        m = len(ACOLS)
        for i in range(len(srings) - 1):
            for k in range(m):
                k2 = (k + 1) % m
                f = [base + i * m + k, base + i * m + k2, base + (i + 1) * m + k2, base + (i + 1) * m + k]
                faces.append(f if s == 1 else f[::-1])
                fband.append(srings[i][2])

    # mesh, outward normals (each shell checked against its own centre line)
    bm = bmesh.new()
    bv = [bm.verts.new(v) for v in verts]
    bfs = []
    for f in faces:
        bfs.append(bm.faces.new([bv[i] for i in f]))
    bm.verts.index_update()
    bm.normal_update()
    # each shell is wound one way by construction: flip the whole shell if it mostly faces inward
    # (per face would be wrong on the ledges, whose normals are along the axis)
    shells = {"trunk": [], 1: [], -1: []}
    for f in bm.faces:
        c = f.calc_center_median()
        if f.verts[0].index < n_trunk_v:
            out = Vector((c.x, c.y - yc(c.z), 0.0))
            key = "trunk"
        else:
            ax = Vector(axis_at(abs(c.x)))
            ax.x *= 1 if c.x >= 0 else -1
            out = c - ax
            key = 1 if c.x >= 0 else -1
        shells[key].append((f, f.normal.dot(out) * f.calc_area()))
    for fs in shells.values():
        if sum(d for _, d in fs) < 0:
            for f, _ in fs:
                f.normal_flip()
    hidden = set()  # sleeve root ring: inside the trunk shell and the body on purpose
    for s_i in range(2):
        b0 = n_trunk_v + s_i * len(srings) * len(ACOLS)
        hidden.update(range(b0, b0 + len(ACOLS)))
    gm = bpy.data.meshes.new("Shirt")
    bm.to_mesh(gm)
    bm.free()
    band_attr = gm.attributes.new("band", "INT", "FACE")
    for i, b in enumerate(fband):
        band_attr.data[i].value = int(b)
    ob = bpy.data.objects.new("Shirt", gm)
    bpy.context.scene.collection.objects.link(ob)

    # weights + "src" (nearest body vertex) before the wall, so the inner wall carries them
    def kd(parts):
        idx = np.array([v for v in range(len(co)) if any(part_of_v[v] == q for q in parts)])
        t = KDTree(len(idx))
        for j, v in enumerate(idx):
            t.insert(Vector(co[v]), int(v))
        t.balance()
        return t

    part_of_v = np.zeros(len(co), dtype=int)
    for p in me.polygons:
        for v in p.vertices:
            if part_of_v[v] in (0, NECK) or part[p.index] in (ARM, TRUNK):
                part_of_v[v] = part[p.index]
    kt, ka, karm = kd((TRUNK, NECK, CROTCH)), kd((ARM, TRUNK)), kd((ARM,))
    names = {g.index: g.name for g in body.vertex_groups}
    groups = {}
    src = gm.attributes.new("src", "INT", "POINT")
    for v in gm.vertices:
        # sleeve past the root: arm skin only (trunk weights at the cap let the skin of the lifted arm through)
        tree = kt if v.index < n_trunk_v else (ka if v.index in hidden else karm)
        near = tree.find_n(v.co, 6)
        # "src" (deform_test poke check): the nearest body vertex that lies under this point (its normal points at
        # it). The plain nearest one can be a neck-base corner whose normal points up, over a collar that is fine.
        under = [vi for _, vi, _ in tree.find_n(v.co, 10)
                 if (v.co - Vector(co[vi])).normalized().dot(me.vertices[vi].normal) > 0.2]
        src.data[v.index].value = -1 if v.index in hidden else (under[0] if under else near[0][1])
        acc = {}
        # weights: 6 nearest body vertices, inverse distance (smooth; only the skin right under it gave folded cloth)
        pick = [(vi, d_) for _, vi, d_ in near]
        for vi, dist in pick:
            w = 1.0 / max(dist, 1e-3) ** 2
            for g in me.vertices[vi].groups:
                acc[names[g.group]] = acc.get(names[g.group], 0.0) + g.weight * w
        top = sorted(acc.items(), key=lambda kv: -kv[1])[:4]  # game engines: 4 influences
        top = [(g_, w_) for g_, w_ in top if w_ > 0.02 * top[0][1]]
        s_ = sum(w_ for _, w_ in top) or 1.0
        for gname, w in top:
            if gname not in groups:
                groups[gname] = ob.vertex_groups.new(name=gname)
            groups[gname].add([v.index], w / s_, "REPLACE")

    m = ob.modifiers.new("wall", "SOLIDIFY")
    m.thickness = WALL
    m.offset = -1.0
    m.use_rim = True
    m.use_even_offset = False
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.modifier_apply(modifier="wall")
    col = gm.color_attributes.new("Col", "FLOAT_COLOR", "FACE")
    rnd = np.random.default_rng(7)
    ba = gm.attributes["band"].data
    for p in gm.polygons:
        base = S["band"] if ba[p.index].value else S["colour"]
        k = 1 + rnd.uniform(-0.03, 0.03)
        col.data[p.index].color = lin(tuple(min(1.0, c * k) for c in base))
        p.use_smooth = False
    gm.color_attributes.active_color = col
    if mat:
        gm.materials.append(mat)
    ob["qa_wall"] = WALL
    ob.parent = rig
    am = ob.modifiers.new("Armature", "ARMATURE")
    am.object = rig

    # skin under the shirt: trunk faces above the hem band, arm faces inside the sleeve; faces touching the
    # hem / cuff stay (no hole visible from outside). The neck base band goes too: the collar rib stands over it.
    covered = {p.index for p in me.polygons if part[p.index] in (TRUNK, ARM)}
    edge = set()
    edge |= {v for v in range(len(co)) if co[v, 2] < hz + 0.03}
    edge |= {v for v in range(len(co)) if abs(co[v, 0]) > sx[-1] - 0.03 and part_of_v[v] == ARM}
    tris = sum(len(p.vertices) - 2 for p in gm.polygons)
    return ob, {"loft_rings": len(rings), "sleeve_rings": len(srings), "triangles": tris}, (covered, edge)
