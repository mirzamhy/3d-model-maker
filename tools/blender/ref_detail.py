# Muscle pass on the reference body: "sculpt dense, then decimate" (the usual low-poly trick).
#   blender -b --factory-startup -P tools/blender/ref_detail.py      (after ref_body.py; RD_SRC, RD_TAG, RD_TRIS)
# 1. body faces only (the head stays as built) are subdivided twice with interpolating smoothing: the original
#    vertices stay on the silhouette, new ones round the 8-sided rings out;
# 2. muscles = displacement along the vertex normal, sum of soft bumps (+) and grooves (-), placed in landmark
#    coordinates: torso by (|x|, y) and facing (front/back from the normal), arms and legs by (position along the
#    limb, angle around it);
# 3. collapse decimate back to a low-poly budget: the edges that survive follow the muscle shapes, which gives the
#    triangle-faceted look of the reference. The neck ring and the head are pinned (vertex group weight 0).
import bpy
import bmesh
import json
import math
import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import head_game as G  # noqa: E402
import ref_body as RB  # noqa: E402

ROOT = RB.ROOT
OUT = RB.OUT
SRC = os.path.join(ROOT, os.environ.get("RD_SRC", "output/ref/survivor/ref_body_v1.blend"))
TAG = os.environ.get("RD_TAG", "ref_body_v2")
TRIS = int(os.environ.get("RD_TRIS", "5200"))
SMOOTH = float(os.environ.get("RD_SMOOTH", "0.7"))
GAIN = float(os.environ.get("RD_GAIN", "1.8"))  # 1.0 is anatomically sized but reads too faint at low poly


def g(a, b, ca, cb, ra, rb):
    return math.exp(-((a - ca) / ra) ** 2 - ((b - cb) / rb) ** 2)


def seg(px, py, ax, ay, bx, by, w):
    """Gaussian of the distance from (px, py) to segment a-b."""
    dx, dy = bx - ax, by - ay
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    d = math.hypot(px - ax - t * dx, py - ay - t * dy)
    return math.exp(-(d / w) ** 2)


def adiff(a, b):
    return (a - b + 180.0) % 360.0 - 180.0


def ga(a, b, ca, cb, ra, rb):
    """Like g, b is an angle in degrees."""
    return math.exp(-((a - ca) / ra) ** 2 - (adiff(b, cb) / rb) ** 2)


def smoothstep(e0, e1, x):
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def torso_front(ax, y):
    d = 0.011 * g(ax, y, 0.085, 1.31, 0.065, 0.045)  # pectoral
    d -= 0.008 * seg(ax, y, 0.0, 1.255, 0.15, 1.28, 0.011)  # lower pec edge
    d -= 0.005 * g(ax, y, 0.0, 1.31, 0.012, 0.07)  # sternum
    for yc, amp in ((1.19, 0.006), (1.12, 0.006), (1.05, 0.0055), (0.98, 0.004)):  # six-pack + lower pair
        d += amp * g(ax, y, 0.037, yc, 0.021, 0.026)
    d -= 0.004 * g(ax, y, 0.0, 1.06, 0.010, 0.16)  # linea alba
    d -= 0.004 * seg(ax, y, 0.03, 1.215, 0.13, 1.16, 0.010)  # rib cage edge
    d += 0.005 * g(ax, y, 0.12, 1.04, 0.028, 0.07)  # obliques
    d -= 0.006 * seg(ax, y, 0.115, 0.99, 0.045, 0.85, 0.012)  # inguinal "V" line
    return d


def torso_back(ax, y):
    d = -0.007 * g(ax, y, 0.0, 1.15, 0.014, 0.25)  # spine
    d += 0.008 * g(ax, y, 0.085, 1.31, 0.045, 0.06)  # shoulder blade
    d += 0.004 * g(ax, y, 0.035, 1.26, 0.035, 0.07)  # lower trapezius
    d += 0.003 * g(ax, y, 0.125, 1.17, 0.035, 0.08)  # lats (outer edge is in the front silhouette)
    d += 0.005 * g(ax, y, 0.03, 1.03, 0.022, 0.08)  # spinal erectors
    d -= 0.012 * g(ax, y, 0.0, 0.88, 0.012, 0.08)  # glute cleft
    return d


def arm(ax, th):
    """th: angle around the arm, 0 = front (z+), 90 = up."""
    d = 0.008 * ga(ax, th, 0.27, 0, 0.05, 50)  # biceps
    d += 0.007 * ga(ax, th, 0.26, 180, 0.06, 55)  # triceps
    d += 0.0035 * ga(ax, th, 0.44, 60, 0.08, 60)  # forearm extensors near the elbow
    d += 0.002 * ga(ax, th, 0.44, -60, 0.07, 50)  # forearm flexors underneath
    d -= 0.003 * math.exp(-((ax - 0.375) / 0.015) ** 2)  # elbow
    return d


def leg(y, th):
    """th: angle around the leg, 0 = front, +90 = outside.
    The side and front silhouettes already hold the thigh, calf and glute bulges: adding them again doubles them
    (v2 calf kink). So only grooves (inside the silhouette) and small bumps where no silhouette sees them."""
    d = 0.006 * ga(y, th, 0.57, -45, 0.04, 35)  # vastus medialis (tear drop), front-inner
    d -= 0.004 * ga(y, th, 0.535, 0, 0.012, 50)  # above the knee cap
    d += 0.004 * ga(y, th, 0.50, 0, 0.025, 30)  # knee cap
    d -= 0.004 * ga(y, th, 0.80, 180, 0.012, 60)  # under the glute
    d -= 0.003 * ga(y, th, 0.66, -100, 0.12, 15)  # inner thigh: quad / adductor split
    d -= 0.003 * ga(y, th, 0.38, -115, 0.07, 15)  # calf / shin split, inner
    d -= 0.003 * ga(y, th, 0.38, 115, 0.07, 15)  # calf / shin split, outer
    return d


def limb_centres(pts, axis, other, lo, hi, step=0.01):
    """Per bin along `axis`: centre of the bounding box in the two other coordinates."""
    bins = {}
    for p in pts:
        if lo <= p[axis] <= hi:
            bins.setdefault(int(p[axis] / step), []).append(p)
    out = {}
    for k, ps in bins.items():
        a = np.array(ps)
        out[k] = tuple((a[:, c].min() + a[:, c].max()) / 2 for c in other)
    keys = sorted(out)
    return lambda v: tuple(np.interp(v / step, keys, [out[k][i] for k in keys]) for i in range(len(other)))


def main():
    sil = RB.Sil()
    L = RB.landmarks(sil)
    bpy.ops.wm.open_mainfile(filepath=SRC)
    ob = bpy.data.objects["Character"]
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    W = lambda v: np.array([v.co.x, v.co.z, -v.co.y])
    lay = bm.verts.layers.int.get("pin")
    if lay is not None:  # ref_body marks what stays as built: head, neck, foot
        y_neck = L["chin"] - RB.NECK_BASE_DROP
        ring = {v for v in bm.verts if v[lay]}
        body = lambda f: not all(v in ring for v in f.verts)
    else:  # older bases: head above the neck ring height, foot below the ankle
        st = json.load(open(os.path.join(OUT, f"stats_{os.environ.get('RD_BASE', 'ref_body_v1')}.json")))
        r0, r1 = st["trunk_rows_y"][:2]
        y_neck = (r0 - 0.45 * r1) / 0.55  # ref_body: rows[0] = y_neck - 0.45 (y_neck - rt)
        body = lambda f: max(v.co.z for v in f.verts) <= y_neck + 1e-4
        ring = {v for f in bm.faces if body(f) for v in f.verts if abs(v.co.z - y_neck) < 1e-3}
        ring |= {v for v in bm.verts if v.co.z < L["ankle"] + 1e-3}
    # pinned vertices never move: recognise them by position. (BMVert identity is not stable across bmesh ops
    # once the mesh has an int layer: a set of BMVerts silently stopped matching and the head got decimated.)
    ck = lambda v: (round(v.co.x, 6), round(v.co.y, 6), round(v.co.z, 6))
    pin_co = {ck(v) for v in ring}
    pinned = lambda v: ck(v) in pin_co
    body = lambda f: not all(pinned(v) for v in f.verts)
    n_head = sum(1 for f in bm.faces if not body(f))
    for _ in range(2):
        edges = {e for f in bm.faces if body(f) for e in f.edges if not all(pinned(v) for v in e.verts)}
        bmesh.ops.subdivide_edges(bm, edges=list(edges), cuts=1, use_grid_fill=True, smooth=SMOOTH)
    bm.normal_update()
    bverts = [v for v in {v for f in bm.faces if body(f) for v in f.verts} if not pinned(v)]
    pts = [W(v) for v in bverts]
    # limb axes from the dense mesh
    crotch = L["crotch"]
    legc = limb_centres([p for p in pts if p[0] > 0.01 and p[1] < crotch - 0.01], 1, (0, 2), 0.0, crotch)
    armc = limb_centres([p for p in pts if p[0] > 0.2], 0, (1, 2), 0.2, L["wrist"])
    disp = []
    for v, p in zip(bverts, pts):
        x, y, z = p
        ax = abs(x)
        n = np.array([v.normal.x, v.normal.z, -v.normal.y])
        fade = smoothstep(y_neck, y_neck - 0.05, y)
        # region weights: arm beyond the shoulder, leg below the crotch, torso the rest
        w_arm = smoothstep(0.17, 0.21, ax) * (y > 1.1)
        w_leg = smoothstep(crotch + 0.01, crotch - 0.03, y) * (ax > 0.005)
        w_tor = max(0.0, 1.0 - w_arm - w_leg)
        d = 0.0
        if w_tor:
            wf, wb = min(1.0, max(0.0, n[2] * 1.6)), min(1.0, max(0.0, -n[2] * 1.6))
            d += w_tor * (wf * torso_front(ax, y) + wb * torso_back(ax, y))
        d += 0.010 * math.exp(-((ax - 0.185) ** 2 + (y - 1.355) ** 2 + z ** 2) / 0.05 ** 2)  # deltoid
        if w_arm and ax < L["wrist"]:
            yc, zc = armc(ax)
            d += w_arm * arm(ax, math.degrees(math.atan2(y - yc, z - zc)))
        if w_leg and y > L["ankle"] + 0.02:
            xc, zc = legc(y)
            d += w_leg * leg(y, math.degrees(math.atan2((x - xc) * np.sign(x), z - zc)))
        disp.append(GAIN * fade * d)
    for v, d in zip(bverts, disp):
        v.co += v.normal * d
    # pin: head + neck ring weight 0, body 1 (decimate only touches weighted vertices)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if body(f)])
    bm.verts.index_update()
    pin = [v.index for v in bm.verts if not pinned(v)]  # (vertex group of the vertices decimate may touch)
    n_keep = len(bm.verts) - len(pin)
    bm.to_mesh(ob.data)
    bm.free()
    vg = ob.vertex_groups.new(name="decimate")
    vg.add(pin, 1.0, "REPLACE")
    tris_now = sum(len(p.vertices) - 2 for p in ob.data.polygons)
    head_tris = sum(len(p.vertices) - 2 for p in ob.data.polygons if all(i not in set(pin) for i in p.vertices))
    mod = ob.modifiers.new("dec", "DECIMATE")
    mod.decimate_type = "COLLAPSE"
    mod.vertex_group = "decimate"
    mod.vertex_group_factor = 1000.0
    mod.use_symmetry = True
    mod.symmetry_axis = "X"
    mod.ratio = min(1.0, TRIS / tris_now)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.modifier_apply(modifier="dec")
    # decimate's symmetry is not exact: keep the character's left half (x > 0) and mirror it
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.symmetrize(bm, input=bm.verts[:] + bm.edges[:] + bm.faces[:], direction=os.environ.get("RD_SYM", "X"),
                         dist=1e-4)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
    bm.to_mesh(ob.data)
    bm.free()
    # check the head survived: same count of vertices above the neck ring
    above = sum(1 for v in ob.data.vertices if v.co.z > y_neck + 1e-3)
    G.flat(ob)
    s = {"character": G.stats(ob), "dense_tris": tris_now, "head_tris_before": head_tris, "keep_verts": n_keep,
         "verts_above_neck_after": above, "head_faces_before": n_head, "closed": G.closed(ob),
         "symmetry": G.symmetry(ob), "disp_mm": [round(1000 * min(disp), 1), round(1000 * max(disp), 1)]}
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, f"{TAG}.blend"))
    json.dump(s, open(os.path.join(OUT, f"stats_{TAG}.json"), "w"), indent=1)
    print("RD_STATS", json.dumps(s))


if __name__ == "__main__":
    main()
