# Fixed-topology game head (eyeless): designed quad layout projected onto the SDF.
#   "/c/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup -P tools/blender/head_template.py
#
# Why: remeshing (collapse, QuadriFlow) never makes the loops a face needs. Here the loops are designed:
#  - columns sit on features (centre, philtrum, nose wing / inner eye, mouth corner, pupil, outer eye, cheek, side, back);
#  - rows sit on features (brow, lids, nose base, upper lip, mouth line, lower lip, chin crease, chin, under chin);
#  - inset rings: a "mask" loop around nose-mouth-chin (nasolabial line), a lip ring, an eye ring;
#  - every vertex is cast from inside onto the SDF, then Newton-snapped after the insets.
# Rules come from notes/topologi-wajah-lowpoly.md. Ears are a separate low mesh; shoulders are not part of v1.
# Output: output/head-game/template/head_tpl.{blend,glb}, stats_tpl.json, renders/game_tpl_*.png
import bpy
import bmesh
import json
import math
import os
import sys
import numpy as np
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("HEAD_EYELESS", "1")
import head_lowpoly as H  # noqa: E402
import head_game as G  # noqa: E402
import head_topo_lab as L  # noqa: E402

OUT = os.path.join(G.OUT, "template")
os.makedirs(OUT, exist_ok=True)
TAG = os.environ.get("TPL_TAG", "tpl")

def tpl_sdf(p):
    """Head with its own neck (radius 46 mm + throat + neck muscles), eyeless sockets, flat cut at y = -0.175.
    head_game's extra 51 mm neck capsule filled the space under the jaw and hid the jaw line."""
    d = H.head_sdf(p, eyeball=False, neck_cut=None, eyeless=True)
    return np.maximum(d, -(p[:, 1] + 0.175))


SDF = tpl_sdf
C = H.V(0, -0.02, 0.0)  # ray origin inside the head

# azimuth of each column for one half, degrees from the front (0) to the back (180)
COLS = [0, 6, 12, 17, 22, 29, 37, 48, 64, 90, 120, 150, 180]
# rows as the height where the front centre ray should land (head coords, y = 0 at eye level)
FRONT_ROWS = [0.05, 0.034, 0.017, 0.003, -0.011, -0.026, -0.037, -0.046, -0.058, -0.072, -0.086, -0.098, -0.112]
CROWN = [22, 42]  # polar angles (deg from straight up) of the two rows above the forehead
# jaw row: one ring that follows the lower edge of the mandible, from under the chin to the jaw angle below the
# ear, then along the nape just under the skull. Target height per column (|theta| -> y); each ray's polar angle is
# solved per column. It is also kept >= 12 mm below the row above, so rows never cross at the back.
JAW_Y = {0: -0.121, 6: -0.121, 12: -0.12, 17: -0.119, 22: -0.117, 29: -0.113, 37: -0.106, 48: -0.097,
         64: -0.088, 90: -0.082, 120: -0.078, 150: -0.076, 180: -0.076}
NECK_ROWS = [-0.132, -0.153, -0.172]  # horizontal rings around the neck axis

# regions: (theta from, theta to) in degrees on one half, (front y top, front y bottom); faces between them
EYE = ((12, 29), (0.017, -0.011))  # two faces wide, two high: almond hollow under the brow
MASK = ((0, 17), (-0.026, -0.098))  # nose middle to chin crease, centre to past the mouth corner
LIPS = ((0, 17), (-0.058, -0.086))  # upper lip top, mouth line, lower lip bottom
SLIT_Y = -0.072


def cast(origins, dirs, tmax=0.3, step=0.0008):
    """First surface hit from inside along each ray (bisection refined)."""
    n = len(dirs)
    t_in = np.zeros(n)
    t_out = np.full(n, tmax)
    open_ = np.ones(n, bool)
    t = step
    while t < tmax and open_.any():
        idx = np.nonzero(open_)[0]
        out = SDF(origins[idx] + dirs[idx] * t) > 0
        t_out[idx[out]] = t
        open_[idx[out]] = False
        t_in[idx[~out]] = t
        t += step
    for _ in range(16):
        mid = (t_in + t_out) / 2
        out = SDF(origins + dirs * mid[:, None]) > 0
        t_out = np.where(out, mid, t_out)
        t_in = np.where(out, t_in, mid)
    return origins + dirs * ((t_in + t_out) / 2)[:, None]


def sph(theta, phi):
    th, ph = math.radians(theta), math.radians(phi)
    return np.array([math.sin(ph) * math.sin(th), math.cos(ph), math.sin(ph) * math.cos(th)])


def phi_for_front_y(y):
    lo, hi = 1.0, 179.0
    for _ in range(40):
        mid = (lo + hi) / 2
        p = cast(C[None], sph(0, mid)[None])[0]
        lo, hi = (mid, hi) if p[1] > y else (lo, mid)
    return (lo + hi) / 2


# Column bands: thin columns exist only where the face needs them, so the skull and neck get big planes.
#   muzzle rows (nose middle .. chin): every column; eye/brow rows: no 6 and 17; forehead/crown/neck: fewer still.
CROWN_COLS = [0, 22, 64, 120, 180]
SKULL_COLS = [0, 12, 22, 37, 64, 90, 120, 150, 180]
EYE_COLS = [0, 12, 22, 29, 37, 48, 64, 90, 120, 150, 180]
NECK_COLS = [0, 22, 48, 90, 120, 180]
MUZZLE_TOP, MUZZLE_BOTTOM = -0.026, -0.112


def jaw_row(thetas, prev, prev_phi):
    """Per-column polar angle so each ray lands on the jaw-line target height (bisection, all columns at once)."""
    target = np.array([min(JAW_Y[abs(t)], prev[i, 1] - 0.012) for i, t in enumerate(thetas)])
    lo = np.full(len(thetas), prev_phi)
    hi = np.full(len(thetas), 175.0)
    o = np.repeat(C[None], len(thetas), 0)
    for _ in range(30):
        mid = (lo + hi) / 2
        dirs = np.array([sph(t, m) for t, m in zip(thetas, mid)])
        y = cast(o, dirs)[:, 1]
        lo, hi = np.where(y > target, mid, lo), np.where(y > target, hi, mid)
    dirs = np.array([sph(t, m) for t, m in zip(thetas, (lo + hi) / 2)])
    return cast(o, dirs)


def full_ring(cols):
    return cols + [-c for c in reversed(cols[1:-1])]


def build_grid():
    thetas = full_ring(COLS)
    nc = len(thetas)
    order = {t: i for i, t in enumerate(thetas)}  # position in the master ring
    phis = [10] + CROWN + [phi_for_front_y(y) for y in FRONT_ROWS]
    fy = [None] * (1 + len(CROWN)) + list(FRONT_ROWS) + [None] * (1 + len(NECK_ROWS))
    sets = {k: set(full_ring(v)) for k, v in
            (("crown", CROWN_COLS), ("skull", SKULL_COLS), ("eye", EYE_COLS), ("full", COLS), ("neck", NECK_COLS))}

    def band(y):
        if y is None or y > 0.04:
            return "skull"
        if y > MUZZLE_TOP + 1e-9:
            return "eye"
        return "full" if y >= MUZZLE_BOTTOM - 1e-9 else "eye"

    names = ["crown", "skull", "skull"] + [band(y) for y in FRONT_ROWS] + ["eye"] + ["neck"] * len(NECK_ROWS)
    row_cols = [sets[n] for n in names]
    assert len(row_cols) == len(phis) + 1 + len(NECK_ROWS)
    rows = []
    for ph in phis:
        dirs = np.array([sph(t, ph) for t in thetas])
        rows.append(cast(np.repeat(C[None], nc, 0), dirs))
    rows.append(jaw_row(thetas, rows[-1], phis[-1]))
    for y in NECK_ROWS:
        o = np.repeat(H.V(0, y, -0.01)[None], nc, 0)
        dirs = np.array([[math.sin(math.radians(t)), 0, math.cos(math.radians(t))] for t in thetas])
        rows.append(cast(o, dirs, tmax=0.15))
    top = cast(C[None], H.V(0, 1, 0)[None])[0]
    verts = [top]
    vid = {}
    for r, (pts, cols) in enumerate(zip(rows, row_cols)):
        for t in thetas:
            if t in cols:
                vid[(r, t)] = len(verts)
                verts.append(pts[order[t]])
    ring = lambda r: [t for t in thetas if t in row_cols[r]]
    faces, meta = [], []
    r0 = ring(0)
    for a, b in zip(r0, r0[1:] + r0[:1]):
        faces.append((0, vid[(0, b)], vid[(0, a)]))
        meta.append(None)
    for r in range(len(rows) - 1):
        small = ring(r) if len(ring(r)) <= len(ring(r + 1)) else ring(r + 1)
        for a, b in zip(small, small[1:] + small[:1]):
            ia, ib = order[a], order[b]
            span = [thetas[(ia + k) % nc] for k in range(((ib - ia) % nc) + 1)]
            top_ = [vid[(r, t)] for t in span if t in row_cols[r]]
            bot = [vid[(r + 1, t)] for t in reversed(span) if t in row_cols[r + 1]]
            faces.append(tuple(top_ + bot))
            meta.append((r, a, b) if len(top_) == 2 and len(bot) == 2 else None)
    last = len(rows) - 1
    faces.append(tuple(vid[(last, t)] for t in ring(last)))  # neck bottom cap
    meta.append(None)
    return verts, faces, meta, fy


def region_faces(bm, fy, region):
    """Quads whose two columns lie in [lo, hi] degrees on one side and whose rows lie between the front heights."""
    (lo, hi), (y_top, y_bot) = region
    lr, la, lb = (bm.faces.layers.int.get(k) for k in ("row", "ta", "tb"))
    out = []
    for f in bm.faces:
        r = f[lr]
        if r < 0 or fy[r] is None or fy[r + 1] is None:
            continue
        if not (fy[r] <= y_top + 1e-9 and fy[r + 1] >= y_bot - 1e-9):
            continue
        a, b = f[la], f[lb]
        same_side = a * b >= 0
        if same_side and lo <= abs(a) <= hi and lo <= abs(b) <= hi:
            out.append(f)
    return out


def to_bl(p):
    return np.stack([p[:, 0], -p[:, 2], p[:, 1]], axis=1)


def snap_ob(ob, keep_seam=True, iters=6):
    """Put every vertex back on the surface along the same kind of ray that placed it: radial from the head
    centre for the head, horizontal from the neck axis for the neck. (Newton snap to the nearest surface
    pulled the philtrum up under the nose.)"""
    co = L.mesh_arrays(ob)
    p = L.to_head(co)
    neck = (p[:, 1] < -0.115) & (p[:, 2] < 0.03)
    o = np.where(neck[:, None], np.column_stack([np.zeros(len(p)), p[:, 1], np.full(len(p), -0.01)]), C[None])
    d = p - o
    d /= np.maximum(np.linalg.norm(d, axis=1), 1e-9)[:, None]
    p = cast(o, d)
    new = to_bl(p)
    if keep_seam:
        new[np.abs(co[:, 0]) < 1e-7, 0] = 0.0
    L.set_co(ob, new)


def build_head():
    verts, faces, meta, fy = build_grid()
    me = bpy.data.meshes.new("Head_Main")
    me.from_pydata([tuple(v) for v in to_bl(np.array(verts))], [], faces)
    ob = bpy.data.objects.new("Head_Main", me)
    bpy.context.collection.objects.link(ob)
    bm = bmesh.new()
    bm.from_mesh(me)
    lr, la, lb = (bm.faces.layers.int.new(k) for k in ("row", "ta", "tb"))
    for f, m in zip(bm.faces, meta):
        f[lr], f[la], f[lb] = m if m else (-1, 0, 0)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    lips_tag = bm.faces.layers.int.new("lips")
    # 1. mask loop around nose, mouth and chin front (the nasolabial line)
    mask = region_faces(bm, fy, MASK)
    bmesh.ops.inset_region(bm, faces=mask, thickness=0.0045, depth=0.0, use_even_offset=True, use_boundary=True)
    # 2. lip ring: lips region inset; the inner faces are the lips
    lips = region_faces(bm, fy, LIPS)
    bmesh.ops.inset_region(bm, faces=lips, thickness=0.0035, depth=0.0, use_even_offset=True)
    # second inset: the new ring is the red lip surface, the faces left inside become the mouth slot
    red = bmesh.ops.inset_region(bm, faces=lips, thickness=0.003, depth=0.0, use_even_offset=True)["faces"]
    for f in lips:
        f[lips_tag] = 1
    for f in red:
        f[lips_tag] = 2
    # 3. eye ring on both sides (separate regions so each gets its own ring)
    eyes = region_faces(bm, fy, EYE)
    for side in (1, -1):
        part = [f for f in eyes if f.calc_center_median().x * side > 0]
        bmesh.ops.inset_region(bm, faces=part, thickness=0.004, depth=0.0, use_even_offset=True)
    bm.to_mesh(me)
    bm.free()
    snap_ob(ob, keep_seam=False)
    # exact symmetry: keep x >= 0, mirror, weld
    L.keep_half(ob)
    L.mirror_weld(ob, triangulate=False)
    snap_ob(ob)
    shape_mouth(ob)
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(ob.data)
    bm.free()
    return ob


MOUTH_W = 0.021  # half width to the mouth corner
UPPER_H, LOWER_H = 0.0074, 0.0086  # lip heights above / below the mouth line at the centre
RING = 0.0042  # skin margin of the lip ring


def cast_front(xy):
    """Project front-view points (x, y) onto the face: march from z = 0.2 toward -z until inside."""
    n = len(xy)
    o = np.column_stack([xy, np.full(n, 0.2)])
    d = np.tile([0.0, 0.0, -1.0], (n, 1))
    t_out, t_in = np.zeros(n), np.full(n, 0.25)
    open_ = np.ones(n, bool)
    t = 0.0
    while t < 0.25 and open_.any():
        idx = np.nonzero(open_)[0]
        inside = SDF(o[idx] + d[idx] * t) < 0
        t_in[idx[inside]] = t
        open_[idx[inside]] = False
        t_out[idx[~inside]] = t
        t += 0.0005
    for _ in range(16):
        mid = (t_in + t_out) / 2
        inside = SDF(o + d * mid[:, None]) < 0
        t_in = np.where(inside, mid, t_in)
        t_out = np.where(inside, t_out, mid)
    return o + d * ((t_in + t_out) / 2)[:, None]


def lip_outline(u, side):
    """Front-view y of the upper / lower lip edge at u = |x| / MOUTH_W (0 centre, 1 corner)."""
    u = np.clip(u, 0, 1)
    up = SLIT_Y + UPPER_H * (1 - u ** 2) ** 0.6 - 0.0012 * np.exp(-(u * MOUTH_W / 0.0035) ** 2)  # cupid's bow
    lo = SLIT_Y - LOWER_H * (1 - u ** 2) ** 0.5
    return up if side > 0 else lo


def shape_mouth(ob):
    """Lips laid out in front view (curved edges, corners joined into one vertex), lip ring as an ellipse."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    lt = bm.faces.layers.int.get("lips")
    slot_f = [f for f in bm.faces if f[lt] == 1]
    red_f = [f for f in bm.faces if f[lt] == 2]
    slot_v = {v for f in slot_f for v in f.verts}
    edge_v = {v for f in red_f for v in f.verts} - slot_v  # outer edge of the red lip
    ring_f = {g for f in red_f for e in f.edges for g in e.link_faces if g[lt] == 0}
    ring_v = {v for f in ring_f for v in f.verts} - slot_v - edge_v
    lip_v = slot_v | edge_v
    hc = lambda v: np.array([v.co.x, v.co.z, -v.co.y])
    plan = {}  # vertex -> (x, y, depth behind the face)

    def norm_u(vs):
        xmax = max(abs(hc(v)[0]) for v in vs)
        return {v: (abs(hc(v)[0]) / xmax if xmax > 0 else 0.0) for v in vs}

    sgn = lambda v: math.copysign(1, hc(v)[0]) if abs(hc(v)[0]) > 1e-7 else 0
    # Corners are pinched, not merged (merging made non-manifold edges): every row's end vertex goes to the
    # mouth corner with a 0.4 mm step per row, so the mesh stays closed.
    # depth > 0 = behind the SDF surface. Lips stand out: red edge 1.2-1.4 mm forward, corners 1.5 mm in.
    corner = lambda v, dy, inset: (sgn(v) * (MOUTH_W - inset), SLIT_Y + dy, 0.0015)
    # red lip outer edge: curved outline above / below, side vertex = the corner
    mid_y = np.mean([hc(v)[1] for v in slot_v if all(f[lt] == 1 for f in v.link_faces)])
    for half in (1, -1):
        vs = [v for v in edge_v if (hc(v)[1] - mid_y) * half > 0.0015]
        for v, u in norm_u(vs).items():
            if u > 0.999:
                plan[v] = corner(v, half * 0.0008, 0.0)
            else:
                k = 0.95
                fwd = (0.0012 if half > 0 else 0.0014) * (1 - u ** 2)
                plan[v] = (sgn(v) * u * MOUTH_W * k, float(lip_outline(u * k, half)), -fwd)
    for v in edge_v:
        if v not in plan:
            plan[v] = corner(v, 0.0, -0.0006)
    # mouth slot: interior vertices = back of the slot; boundary = inner lip edges (top / bottom), ends = corner
    inner = [v for v in slot_v if all(f[lt] == 1 for f in v.link_faces)]
    bound = [v for v in slot_v if v not in inner]
    for v, u in norm_u(inner).items():
        plan[v] = (sgn(v) * u * MOUTH_W * 0.85, SLIT_Y, 0.004)
    ends = [v for v in bound if abs(hc(v)[1] - mid_y) < 0.0015]
    for v in ends:
        plan[v] = corner(v, 0.0, 0.0012)
    for half in (1, -1):
        vs = [v for v in bound if v not in ends and (hc(v)[1] - mid_y) * half > 0]
        for v, u in norm_u(vs).items():
            if u > 0.999:
                plan[v] = corner(v, half * 0.0004, 0.0008)
            else:
                h = 0.0009 * (1 - u ** 2) + 0.0004
                plan[v] = (sgn(v) * u * MOUTH_W * 0.93, SLIT_Y + half * h, 0.0008)
    # lip ring: push the outer border onto an ellipse around the lips
    for v in ring_v:
        x, y, _ = hc(v)
        dx, dy = x, y - SLIT_Y
        b = UPPER_H + RING if dy > 0 else LOWER_H + RING
        a = MOUTH_W + RING
        r = math.hypot(dx / a, dy / b)
        if r > 1e-6:
            plan[v] = (dx / r, SLIT_Y + dy / r, 0.0003)
    vs = list(plan)
    xy = np.array([[plan[v][0], plan[v][1]] for v in vs])
    depth = np.array([plan[v][2] for v in vs])
    pts = cast_front(xy)
    # the SDF mouth line is a thin slot ~14 mm deep: points near it would fall to its bottom. Take the lip
    # surface just above and below the slot instead, then push back by the planned depth.
    near = np.abs(xy[:, 1] - SLIT_Y) < 0.0022
    if near.any():
        up = cast_front(np.column_stack([xy[near, 0], np.full(near.sum(), SLIT_Y + 0.0028)]))
        dn = cast_front(np.column_stack([xy[near, 0], np.full(near.sum(), SLIT_Y - 0.0028)]))
        pts[near, 2] = (up[:, 2] + dn[:, 2]) / 2
    pts[:, 2] -= depth
    for v, p in zip(vs, pts):
        v.co = Vector((p[0], -p[2], p[1]))
    bm.to_mesh(ob.data)
    bm.free()


def paint(ob):
    skin, lip = G.material("Skin", G.SKIN), G.material("Lips", G.LIP)
    ob.data.materials.append(skin)
    ob.data.materials.append(lip)
    lt = ob.data.attributes.get("lips")
    for p in ob.data.polygons:
        p.material_index = 1 if lt and lt.data[p.index].value >= 1 else 0


# ---------------- ear part ----------------
# Low-poly ear with a designed layout (the radial ray shell could not hold the bowl: a ray from the ear centre
# always exits on the outer side). Rings around the ear, outer to inner, each (scale, centre shift u/v, depth):
#   rim edge (helix) -> helix fold -> scapha groove -> antihelix ridge -> concha rim -> concha floor -> ear canal.
# Back side: rim -> back ring -> sunk into the head (ears overlap the head; they are not stitched).
# Ear frame from head_lowpoly.ear_sdf: centre EAR_C, plane turned 30 deg so the back edge flares out.
# u = along the ear plane (+ forward, toward the face), v = up, n = outward from the head.
# v13: traced vertex by vertex from the user's reference picture (simple low-poly ear, 3/4 view render, 322x471 px).
# EAR_TRACE: name -> (x px, y px, n mm). x grows toward the face (the root edge is x = 268), y grows down.
# n = height out of the ear plane; names in EAR_GLUE are measured from the head skin instead (root edge on the head).
#   O outer silhouette, R top of the rim (helix), P inner edge of the plateau (antihelix), X bottom of the bowl,
#   T/B/Q the tragus block (flat face with a step down to the bowl above it), F1 root edge where the tragus meets it.
EAR_TRACE = {
    "O1": (268, 23, -0.5), "O2": (184, 8, 3.0), "O3": (73, 54, 3.0), "O4": (10, 197, 3.0), "O5": (42, 362, 3.0),
    "O6": (180, 451, 2.0), "O7": (268, 441, -0.5), "F1": (268, 213, -0.5),
    "R1": (229, 92, 4.2), "R2": (181, 41, 5.0), "R3": (88, 75, 5.0), "R4": (35, 197, 5.0), "R5": (68, 339, 4.6),
    "R6": (173, 418, 4.0), "R7": (218, 366, 4.6),
    "P1": (222, 126, 1.5), "P2": (183, 101, 2.6), "P3": (119, 114, 3.0), "P4": (95, 198, 3.0), "P5": (101, 314, 3.2),
    "X": (177, 213, 1.0), "B1": (176, 236, 3.8), "T1": (212, 224, 3.8), "Q": (222, 221, 4.4),
    "T2": (151, 245, 3.8), "T3": (151, 323, 4.0), "T4": (173, 338, 4.2), "T5": (173, 357, 3.6), "T6": (198, 351, 4.6),
}
EAR_GLUE = ("O1", "O7", "F1")
EAR_FACES = [  # (zone, face) traced from the wire lines; zone 1 rim, 2 plateau/tragus, 3 bowl
    (1, "O1 O2 R2 R1"), (1, "O2 O3 R3 R2"), (1, "O3 O4 R4 R3"), (1, "O4 O5 R5 R4"), (1, "O5 O6 R6 R5"),
    (1, "O6 O7 R7 R6"),
    (2, "R1 R2 P2 P1"), (2, "R2 R3 P3 P2"), (2, "R3 R4 P4 P3"), (2, "R4 R5 P5 P4"),
    (1, "O1 R1 P1 Q F1"), (1, "F1 Q R7 O7"),  # front wall above and below the tragus
    (3, "P2 P1 Q T1 X"),  # bowl (concha), open toward the front
    (2, "P2 P3 P4 X"),  # broad plateau sloping into the bowl
    (3, "P4 P5 T4 T3 T2 B1 X"),  # lower hollow left of the tragus
    (2, "X B1 T1"),  # step on top of the tragus
    (2, "T2 T3 T4 T6 R7 Q T1 B1"),  # tragus block face
    (1, "R5 P5 T4 T5 R6"), (1, "T5 T6 R7 R6"), (2, "T4 T6 T5"),  # lobe
]
EAR_OUTLINE = "O1 O2 O3 O4 O5 O6 O7 F1".split()
EAR_PX, EAR_ROOT_X, EAR_MID_Y = 0.1287, 268, 230  # mm per px (443 px tall = 57 mm), root column, centre row
EAR_TRACE_US = 1.15  # the picture is a 3/4 view: widen u back to the true width
EAR_U0 = 0.0150  # root position along the ear plane
EAR_BACK = [(0.88, -0.5), (0.50, -3.0)]  # back side: outline shrunk toward its centre (scale, n mm)
EAR_BACK_C = -5.0
EAR_SKIN_BACK = (1,)  # back rings measured from the skin (glued into the head)
EAR_ANGLE = 15  # deg the ear plane turns forward: the back edge stands off the head
EAR_ROOT_SINK = 0.0015  # root sits this far inside the head surface
EAR_FLOOR_MIN = 0.0006  # front points stay at least this far outside the head skin


def ear_uv(name):
    x, y, n = EAR_TRACE[name]
    return ((x - EAR_ROOT_X) * EAR_PX * EAR_TRACE_US, (EAR_MID_Y - y) * EAR_PX, n)


def ear_points(side):
    a = math.radians(EAR_ANGLE)
    nvec = np.array([math.cos(a), 0.0, math.sin(a)])  # outward
    tvec = np.array([-math.sin(a), 0.0, math.cos(a)])  # forward along the ear plane
    yvec = np.array([0.0, 1.0, 0.0])
    c = np.array(H.EAR_C) + np.array([0, 0.003, 0])
    ts = np.linspace(-0.02, 0.04, 601)

    def surface(base):  # distance along nvec from each base point to the head surface
        d = SDF((base[:, None, :] + ts[None, :, None] * nvec[None, None, :]).reshape(-1, 3)).reshape(len(base), -1)
        return ts[np.argmax(d > 0, axis=1)]

    # push the ear plane out so its root sits on the head surface
    roots = np.array([c + EAR_U0 * tvec + v / 1000 * yvec for v in (20, 4, -14)])
    c = c + (float(surface(roots).mean()) - EAR_ROOT_SINK) * nvec

    def place(pts, front=True, skin=()):
        q = np.array(pts, dtype=float) / 1000
        base = c + np.outer(EAR_U0 + q[:, 0], tvec) + np.outer(q[:, 1], yvec)
        s = surface(base)
        # lift where the skull bulges past the ear plane, so the ear never sinks deeper than its root
        n = q[:, 2] + np.maximum(0.0, s - EAR_ROOT_SINK)
        if front:  # hollows stay in front of the head skin, or the skin shows through
            n = np.maximum(n, s + EAR_FLOOR_MIN)
        for i in skin:  # glued points: depth from the skin
            n[i] = s[i] + q[i, 2]
        p = base + np.outer(n, nvec)
        p[:, 0] *= side
        return p

    names = list(EAR_TRACE)
    front = place([ear_uv(k) for k in names], skin=[names.index(k) for k in EAR_GLUE])
    out = np.array([ear_uv(k) for k in EAR_OUTLINE])
    mid = out[:, :2].mean(axis=0)
    m = len(EAR_OUTLINE)
    back = [place([(mid[0] + (u - mid[0]) * sc, mid[1] + (v - mid[1]) * sc, n) for u, v, _ in out], False,
                  range(m) if i in EAR_SKIN_BACK else ()) for i, (sc, n) in enumerate(EAR_BACK)]
    back_c = place([(mid[0], mid[1], EAR_BACK_C)], False, (0,))[0]
    return names, front, back, back_c


def ear_mesh(side, name):
    names, front, back, back_c = ear_points(side)
    at = {k: i for i, k in enumerate(names)}
    verts = [tuple(p) for p in front]
    faces, zone = [], []
    for z, f in EAR_FACES:
        faces.append(tuple(at[k] for k in f.split()))
        zone.append(z)
    m = len(EAR_OUTLINE)
    chain = [[at[k] for k in EAR_OUTLINE]]
    for r in back:
        chain.append(list(range(len(verts), len(verts) + m)))
        verts += [tuple(p) for p in r]
    bci = len(verts)
    verts.append(tuple(back_c))
    for i in range(len(chain) - 1):
        for k in range(m):
            faces.append((chain[i][(k + 1) % m], chain[i][k], chain[i + 1][k], chain[i + 1][(k + 1) % m]))
            zone.append(0)
    for k in range(m):
        faces.append((chain[-1][(k + 1) % m], chain[-1][k], bci))
        zone.append(0)
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(to_bl(np.array([v]))[0]) for v in verts], [], faces)
    za = me.attributes.new("ear_zone", "INT", "FACE")
    for i, z in enumerate(zone):
        za.data[i].value = z
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    # keep the traced n-gons whole: with flat shading each one gets a single normal, like the reference
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    return ob


def ears():
    right, left = ear_mesh(1, "Ears"), ear_mesh(-1, "Ear_R")
    bpy.ops.object.select_all(action="DESELECT")
    right.select_set(True)
    left.select_set(True)
    bpy.context.view_layer.objects.active = right
    bpy.ops.object.join()
    right.data.name = "Ears"
    right.data.materials.append(G.material("Skin", G.SKIN))
    return right


def run():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    head = build_head()
    quads = L.quad_share(head)
    paint(head)
    ear = ears()
    brows = [G.eyebrow("Eyebrow_L", 1, head), G.eyebrow("Eyebrow_R", -1, head)]
    objs = [head, ear, *brows]
    for o in objs:
        G.flat(o)
    co = L.mesh_arrays(head)
    cen = np.array([p.center for p in head.data.polygons])
    d = np.abs(SDF(L.to_head(np.vstack([co, cen])))) * 1000
    st = {"head": G.stats(head), "ears": G.stats(ear), "ears_closed": G.closed(ear), "quad_share": quads, "closed": G.closed(head),
          "symmetry": G.symmetry(head), "dev_mm_mean": round(float(d.mean()), 3),
          "dev_mm_p95": round(float(np.percentile(d, 95)), 3), "aspect_p90": round(L.aspect_p90(head), 2),
          "slivers": L.slivers(head), "dihedral_p95": round(L.dihedral_p95(head), 1)}
    print("TPL_STATS " + json.dumps(st))
    with open(os.path.join(OUT, f"stats_{TAG}.json"), "w") as f:
        json.dump(st, f, indent=2)
    G.render_all(TAG, objs)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, f"head_{TAG}.blend"))
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, f"head_{TAG}.glb"), export_format="GLB")


if __name__ == "__main__":
    run()
