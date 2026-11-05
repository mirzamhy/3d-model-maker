# Clean all-quad body for the template head, shaped by the F2 body and rigged with its 73 bones.
#   blender -b --factory-startup -P tools/blender/body_quad.py        (BODY_HEAD, BODY_TAG override)
# Why: F2 is built from rings but stored as triangles; joining them back gives quads except at the joints, where F2
# zips rings with triangle fans (neck -> shoulders star, cracked armpit, crotch V, fingers, toes). Here the layout is
# designed, every vertex is cast onto the F2 surface (BVH ray from the bone axis), and F2's skin weights are copied
# from the nearest F2 surface point. Head coordinates throughout: x = character's left, y up (eye level 0), z forward.
#
# Layout (one side, mirrored; x = 0 vertices are shared):
#   trunk  : 10 columns (0, 22, 48, 90, 120, 180 deg on each half) = the head's neck ring, so the neck seam is all quads.
#            Rows: neck ring, trapezius, 3 shoulder rows, chest, ribs, waist, belly, hips, crotch.
#   arm    : the 4 trunk quads around column 90 of the 3 shoulder rows are left out, giving an 8-vertex hole that is the
#            arm's first ring (up, up-front, front, down-front, down, down-back, back, up-back). Arm rings follow the
#            bones with three rings around the elbow (above, on, below, like F2's helper bones).
#   hand   : mitten (wrist, palm, knuckles, finger middle, tip; box-like rings) with an 8-gon tip closed by 3 quads,
#            and a thumb grown from the palm face that points along the thumb bone (2 rings + cap).
#   legs   : the crotch row splits into two 8-vertex loops (front centre, 22, 48, 90, 120, back centre, inner-back,
#            inner-front); two quads across the crotch share the centre edge. Three rings around the knee.
#   foot   : the leg tube bends forward (ankle, heel, mid foot, ball, toes) and the toe 8-gon is closed by 3 quads.
import bpy
import bmesh
import json
import math
import os
import sys
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, os.path.dirname(__file__))
import head_game as G  # noqa: E402
import head_topo_lab as L  # noqa: E402
import f2_assemble as F  # noqa: E402

ROOT = F.ROOT
HEAD_SRC = os.path.join(ROOT, os.environ.get("BODY_HEAD", "output/head-game/template/head_nose_v2.blend"))
TAG = os.environ.get("BODY_TAG", "body_quad_v1")
OUT = os.path.join(ROOT, "output", "head-game", "body")

COLS = [0, 22, 48, 90, 120, 180]  # half ring, degrees from the front toward +x (= head NECK_COLS)
# trunk rows below the neck ring (head y, m); "crotch" is set from the F2 crotch height
ROWS = [("trap", -0.200), ("sh_top", -0.228), ("sh_mid", -0.268), ("sh_low", -0.315), ("chest", -0.380),
        ("ribs", -0.470), ("waist", -0.560), ("belly", -0.660), ("hips", -0.760), ("crotch", None)]
HOLE_ROWS = (2, 3, 4)  # sh_top, sh_mid, sh_low (index in the full row list, 0 = neck ring)
ARM_ROOT_X = 0.19
ARM_X = [0.26, 0.34, 0.395, 0.428, 0.462, 0.55, 0.625, 0.673]  # ring stations along the arm (x), last = wrist
# hand rings: (station along the hand path 0 = wrist .. 1 = fingertip, half width (front), half thickness (up))
HAND = [(0.22, 0.043, 0.017), (0.58, 0.045, 0.014), (0.80, 0.040, 0.011), (0.96, 0.030, 0.008)]
LEG_Y = [-0.95, -1.06, -1.13, -1.171, -1.21, -1.31, -1.43, -1.53]  # thigh .. knee (3) .. ankle
ARM_ANG = [0, 45, 90, 135, 180, 225, 270, 315]  # around the arm: from up toward front
CROTCH_IN = (-110.0, -70.0)  # leg loop inner-back / inner-front directions (deg from front toward outer)


def to_bl(p):
    return Vector((p[0], -p[2], p[1]))


def to_hd(v):
    return np.array([v.x, v.z, -v.y])


def unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


class Body:
    def __init__(self):
        d = json.load(open(F.JSON))
        self.d = d
        P = np.array([F.body_to_head(p) for p in d["pos"]])
        self.P = P
        self.tris = d["tris"]
        self.bvh = BVHTree.FromPolygons([Vector(p) for p in P], d["tris"])
        self.bone = {b["name"]: (np.array(F.body_to_head(b["head"])), np.array(F.body_to_head(b["tail"])))
                     for b in d["bones"]}
        self.names = [b["name"] for b in d["bones"]]

    def ray(self, o, dirn, fallback=0.03, maxd=0.25):
        hit = self.bvh.ray_cast(Vector(o), Vector(unit(dirn)), maxd)
        if hit[0] is None:
            return np.asarray(o) + unit(dirn) * fallback
        return np.array(hit[0][:])

    def weights(self, p):
        """F2 skin weights at the nearest F2 surface point (barycentric over the triangle), top 4."""
        loc, _, fi, _ = self.bvh.find_nearest(Vector(p))
        tri = self.tris[fi]
        a, b, c = (self.P[i] for i in tri)
        q = np.array(loc[:])
        v0, v1, v2 = b - a, c - a, q - a
        d00, d01, d11, d20, d21 = v0 @ v0, v0 @ v1, v1 @ v1, v2 @ v0, v2 @ v1
        den = d00 * d11 - d01 * d01
        w1 = (d11 * d20 - d01 * d21) / den if den else 0.0
        w2 = (d00 * d21 - d01 * d20) / den if den else 0.0
        bc = np.clip([1 - w1 - w2, w1, w2], 0, 1)
        acc = {}
        for k, vi in enumerate(tri):
            for bi, w in self.d["weights"][vi]:
                acc[bi] = acc.get(bi, 0.0) + w * bc[k]
        top = sorted(acc.items(), key=lambda t: -t[1])[:4]
        s = sum(w for _, w in top) or 1.0
        return [(self.names[bi], w / s) for bi, w in top if w / s > 1e-3]


def frames(points, tangents, e1):
    """Parallel-transported ring frames: (centre, t, e1, e2) with e2 = the 'sideways' axis kept continuous."""
    out = []
    e2_prev = None
    for c, t in zip(points, tangents):
        t = unit(t)
        e1 = unit(e1 - (e1 @ t) * t)
        e2 = np.cross(t, e1)
        if e2_prev is not None and e2 @ e2_prev < 0:
            e2 = -e2
        out.append((np.asarray(c, float), t, e1, e2))
        e1, e2_prev = e1, e2
    return out


def ring_dirs(fr, angles):
    _, _, e1, e2 = fr
    return [math.cos(math.radians(a)) * e1 + math.sin(math.radians(a)) * e2 for a in angles]


def polyline(pts, s):
    """Point and tangent at arc fraction s along a polyline."""
    pts = [np.asarray(p, float) for p in pts]
    seg = [np.linalg.norm(b - a) for a, b in zip(pts, pts[1:])]
    total = sum(seg)
    d = s * total
    for (a, b), l in zip(zip(pts, pts[1:]), seg):
        if d <= l or l == seg[-1]:
            k = min(d / l, 1.0) if l else 0.0
            return a + (b - a) * k, unit(b - a)
        d -= l
    return pts[-1], unit(pts[-1] - pts[-2])


def build(body, head_ring):
    """Left half + centre. Returns pos {key: xyz}, faces [keys]. Keys: ('M'|'L', part, i, j)."""
    pos, faces = {}, []
    side = lambda col: "M" if col in (0, 180) else "L"
    B = body.bone
    spine = [B["Hips"][0], B["Spine"][0], B["Spine1"][0], B["Spine2"][0], B["Neck"][0], B["Neck"][1]]
    spine_z = lambda y: float(np.interp(y, [p[1] for p in spine], [p[2] for p in spine]))
    # crotch: first F2 surface straight up from between the feet
    y_c = body.ray((0.0, -1.3, 0.0), (0, 1, 0), maxd=1.0)[1]
    rows = [(n, y if y is not None else y_c + 0.018) for n, y in ROWS]
    tk = lambda r, col: (side(col), "t", r, col)
    for col, v in head_ring.items():
        pos[tk(0, col)] = v
    for r, (name, y) in enumerate(rows, start=1):
        o = np.array([0.0, y, spine_z(y)])
        for col in COLS:
            if r in HOLE_ROWS and col in (48, 90, 120):
                continue  # arm root ring (below)
            a = math.radians(col)
            p = body.ray(o, (math.sin(a), 0, math.cos(a)), fallback=0.12)
            if col in (0, 180):
                p[0] = 0.0
            pos[tk(r, col)] = p
    # ---- arm: root ring = hole ----
    arm_path = [B["LeftArm"][0], B["LeftForeArm"][0], B["LeftHand"][0]]
    xs = [ARM_ROOT_X] + ARM_X
    pts, tans = [], []
    for x in xs:
        s = (x - arm_path[0][0]) / (arm_path[-1][0] - arm_path[0][0])
        c, t = polyline(arm_path, min(max(s, 0), 1))
        pts.append(c)
        tans.append(t)
    afr = frames(pts, tans, np.array([0, 1.0, 0]))
    hole = {0: (2, 90), 1: (2, 48), 2: (3, 48), 3: (4, 48), 4: (4, 90), 5: (4, 120), 6: (3, 120), 7: (2, 120)}
    ak = lambda i, k: tk(*hole[k]) if i == 0 else ("L", "a", i, k)
    for i, fr in enumerate(afr):
        for k, dv in enumerate(ring_dirs(fr, ARM_ANG)):
            pos[ak(i, k)] = body.ray(fr[0], dv, fallback=0.04)
    # ---- hand: box rings along wrist -> middle finger tip ----
    # F2's middle finger curls down; a mitten reads better nearly straight: keep half the droop below the knuckle
    k1 = B["LeftHandMiddle1"][0]
    flat = lambda p: np.array([p[0], k1[1] + (p[1] - k1[1]) * 0.5, p[2]])
    hand_path = [B["LeftHand"][0], k1, flat(B["LeftHandMiddle3"][0]), flat(B["LeftHandMiddle_End"][0])]
    hpts, htans = [], []
    for s, _, _ in HAND:
        c, t = polyline(hand_path, s)
        hpts.append(c)
        htans.append(t)
    hfr = frames(hpts, htans, afr[-1][2])
    n_arm = len(afr)
    for j, (fr, (_, hw, ht)) in enumerate(zip(hfr, HAND)):
        c, _, e1, e2 = fr
        for k, a in enumerate(ARM_ANG):
            ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
            ex = 2 / 3.0  # superellipse n = 3: box-like with soft corners
            u = math.copysign(abs(ca) ** ex, ca) * ht
            w = math.copysign(abs(sa) ** ex, sa) * hw
            pos[ak(n_arm + j, k)] = c + e1 * u + e2 * w
    n_ring = n_arm + len(HAND)
    for i in range(n_ring - 1):
        for k in range(8):
            k2 = (k + 1) % 8
            faces.append([ak(i, k), ak(i, k2), ak(i + 1, k2), ak(i + 1, k)])
    last = n_ring - 1
    faces += [[ak(last, k) for k in q] for q in ((0, 1, 2, 3), (4, 5, 6, 7), (0, 3, 4, 7))]
    # thumb: replace the wrist->palm face that points most along the thumb root
    # thumb: F2's thumb bones point steeply down; lay it along the palm side instead (forward + toward the fingers)
    th0 = B["LeftHandThumb1"][0]
    hdir = unit(hand_path[1] - hand_path[0])
    tip = th0 + hdir * 0.05 + np.array([0, -0.012, 0.03])
    th1, th2 = th0 + (tip - th0) * 0.5, tip
    i_w = n_arm - 1  # wrist ring
    best, best_d = None, -9
    for k in range(8):
        f = [ak(i_w, k), ak(i_w, (k + 1) % 8), ak(i_w + 1, (k + 1) % 8), ak(i_w + 1, k)]
        cen = np.mean([pos[q] for q in f], 0)
        dd = unit(cen - (hfr[0][0] + afr[-1][0]) / 2) @ unit(th1 - afr[-1][0])
        if dd > best_d:
            best, best_d = f, dd
    faces.remove(best)
    base = np.mean([pos[q] for q in best], 0)
    tdir = unit(th2 - th0)
    prev = best
    for j, (c, size) in enumerate(((th1, 0.015), (th2, 0.011))):
        ring = []
        for m, q in enumerate(best):
            off = pos[q] - base
            off = unit(off - (off @ tdir) * tdir) * size
            key = ("L", "th", j, m)
            pos[key] = np.asarray(c) + off
            ring.append(key)
        for m in range(4):
            faces.append([prev[m], prev[(m + 1) % 4], ring[(m + 1) % 4], ring[m]])
        prev = ring
    faces.append(prev[::-1])
    # ---- trunk faces ----
    nrows = len(rows) + 1
    for r in range(nrows - 1):
        for a, b in zip(COLS, COLS[1:]):
            if r in (2, 3) and (a, b) in ((48, 90), (90, 120)):
                continue  # arm hole (row 3 has no column-90 vertex)
            faces.append([tk(r, a), tk(r, b), tk(r + 1, b), tk(r + 1, a)])
    # ---- legs ----
    rc = nrows - 1  # crotch row index
    y_in = y_c - 0.012
    leg_path = [B["LeftUpLeg"][0], B["LeftLeg"][0], B["LeftFoot"][0]]
    leg_x = lambda y: float(np.interp(-y, [-p[1] for p in leg_path], [p[0] for p in leg_path]))
    leg_z = lambda y: float(np.interp(-y, [-p[1] for p in leg_path], [p[2] for p in leg_path]))
    c_in = np.array([leg_x(y_in), y_in, leg_z(y_in)])
    front, outer = np.array([0, 0, 1.0]), np.array([1.0, 0, 0])
    for m, a in enumerate(CROTCH_IN):
        dv = math.cos(math.radians(a)) * front + math.sin(math.radians(a)) * outer
        pos[("L", "ci", 0, m)] = body.ray(c_in, dv, fallback=0.05)
    loop = [tk(rc, 0), tk(rc, 22), tk(rc, 48), tk(rc, 90), tk(rc, 120), tk(rc, 180), ("L", "ci", 0, 0), ("L", "ci", 0, 1)]
    faces.append([tk(rc, 0), ("L", "ci", 0, 1), ("L", "ci", 0, 0), tk(rc, 180)])
    c0 = np.array([leg_x(rows[-1][1]), rows[-1][1], leg_z(rows[-1][1])])
    ang = [math.degrees(math.atan2((pos[q] - c0) @ outer, (pos[q] - c0) @ front)) for q in loop]
    lk = lambda i, k: loop[k] if i == 0 else ("L", "l", i, k)
    # leg + foot stations
    foot, toe, toe_end = B["LeftFoot"][0], B["LeftToeBase"][0], B["LeftToe_End"][0]
    ground = body.P[:, 1].min()
    stations = [(np.array([leg_x(y), y, leg_z(y)]), unit(B["LeftLeg"][0] - B["LeftUpLeg"][0]) if y > -1.171
                 else unit(foot - B["LeftLeg"][0])) for y in LEG_Y]
    fwd = np.array([0, 0, 1.0])
    down = unit(foot - B["LeftLeg"][0])
    foot_st = [
        (foot + np.array([0, -0.035, -0.01]), unit(down + fwd)),  # heel bend
        (np.array([foot[0] + 0.004, ground + 0.032, (foot[2] + toe[2]) / 2]), fwd),  # mid foot
        (np.array([toe[0], ground + 0.024, toe[2]]), fwd),  # ball
        (np.array([toe[0], ground + 0.016, (toe[2] + toe_end[2]) / 2 + 0.01]), fwd),  # toes
    ]
    st = stations + foot_st
    lfr = frames([s[0] for s in st], [s[1] for s in st], front)
    for i, fr in enumerate(lfr, start=1):
        _, _, e1, e2 = fr
        if e2 @ outer < 0:
            e2 = -e2
        for k, a in enumerate(ang):
            dv = math.cos(math.radians(a)) * e1 + math.sin(math.radians(a)) * e2
            pos[lk(i, k)] = body.ray(fr[0], dv, fallback=0.03)
    nl = len(lfr) + 1
    for i in range(nl - 1):
        for k in range(8):
            k2 = (k + 1) % 8
            faces.append([lk(i, k), lk(i, k2), lk(i + 1, k2), lk(i + 1, k)])
    faces += [[lk(nl - 1, k) for k in q] for q in ((0, 1, 2, 3), (4, 5, 6, 7), (0, 3, 4, 7))]
    return pos, faces, y_c


def head_neck_ring(head):
    co = np.array([v.co[:] for v in head.data.vertices])
    idx = np.nonzero(np.abs(co[:, 2] - F.HEAD_NECK_Y) < 0.0015)[0]
    assert len(idx) == 10, len(idx)
    ring = {}
    for i in idx:
        p = to_hd(head.data.vertices[i].co)
        t = math.degrees(math.atan2(p[0], p[2] + 0.01)) % 360
        col = min(COLS + [360 - c for c in COLS[1:-1]], key=lambda c: min(abs(c - t), 360 - abs(c - t)))
        ring[(col, int(i))] = p
    return ring


def main():
    bpy.ops.wm.open_mainfile(filepath=HEAD_SRC)
    head = bpy.data.objects["Head_Main"]
    F.remove_neck_cap(head)
    body = Body()
    raw = head_neck_ring(head)
    left = {c: p for (c, _), p in raw.items() if c <= 180}
    vidx = {}  # key -> head vertex index for the neck ring
    for (c, i), p in raw.items():
        if c <= 180:
            vidx[("M" if c in (0, 180) else "L", "t", 0, c)] = i
        else:
            vidx[("R", "t", 0, 360 - c)] = i
    pos, faces, y_c = build(body, left)
    n_head = len(head.data.vertices)
    bm = bmesh.new()
    bm.from_mesh(head.data)
    bm.verts.ensure_lookup_table()
    head_v = list(bm.verts)  # indices go stale once new verts are added
    verts = {}

    def vert(key):
        if key in verts:
            return verts[key]
        if key in vidx:
            v = head_v[vidx[key]]
        else:
            if key[0] == "R":
                p = pos[("L",) + key[1:]].copy()
                p[0] = -p[0]
            else:
                p = pos[key]
            v = bm.verts.new(to_bl(p))
        verts[key] = v
        return v

    mirror = lambda k: ("R",) + k[1:] if k[0] == "L" else k
    for f in faces:
        bm.faces.new([vert(k) for k in f])
        if any(k[0] == "L" for k in f):
            bm.faces.new([vert(mirror(k)) for k in f][::-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(head.data)
    bm.free()
    head.name = "Character"
    G.flat(head)
    # weights: head rule above the neck ring, F2 transfer below
    for nm in ("Head", "Neck"):
        head.vertex_groups.get(nm) or head.vertex_groups.new(name=nm)
    for nm in body.names:
        head.vertex_groups.get(nm) or head.vertex_groups.new(name=nm)
    for v in head.data.vertices:
        if v.index < n_head:
            hs = F.head_share(v.co.z)
            head.vertex_groups["Head"].add([v.index], hs, "REPLACE")
            if hs < 1:
                head.vertex_groups["Neck"].add([v.index], 1 - hs, "REPLACE")
        else:
            for nm, w in body.weights(to_hd(v.co)):
                head.vertex_groups[nm].add([v.index], w, "REPLACE")
    rig = F.build_armature(body.d)
    for ob in [o for o in bpy.data.objects if o.type == "MESH"]:
        if ob is not head:
            g = ob.vertex_groups.get("Head") or ob.vertex_groups.new(name="Head")
            g.add([v.index for v in ob.data.vertices], 1.0, "REPLACE")
        ob.parent = rig
        ob.modifiers.new("Rig", "ARMATURE").object = rig
    sizes = {}
    for p in head.data.polygons:
        sizes[len(p.vertices)] = sizes.get(len(p.vertices), 0) + 1
    st = {"character": G.stats(head), "faces_by_sides": sizes, "closed": G.closed(head), "symmetry": G.symmetry(head),
          "crotch_y": round(float(y_c), 4), "body_verts": len(head.data.vertices) - n_head}
    os.makedirs(OUT, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, f"{TAG}.blend"))
    json.dump(st, open(os.path.join(OUT, f"stats_{TAG}.json"), "w"), indent=1)
    print("BODY_STATS", json.dumps(st))


if __name__ == "__main__":
    main()
