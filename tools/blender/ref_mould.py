# Low-poly body shaped by a MakeHuman mould: our clean quad rings (ref_body.py, survivor silhouettes) take the
# CROSS-SECTION SHAPE of the MPFB body (mpfb_body.py, T-pose), ring by ring.
#   blender -b --factory-startup -P tools/blender/ref_mould.py     (RM_SRC, RM_MOULD, RM_TAG, RM_SIZE, RM_SHAPE)
# Per vertex: find its ring centre on our body and the matching centre on the mould (torso/neck: same height,
# legs: same height on the same side, arms: same fraction shoulder -> wrist), cast a ray from the mould centre in
# the vertex's direction, take the hit distance. Size per ring stays the survivor's (RM_SIZE = 1: mean radius
# matched), shape (which directions bulge: chest, shoulder blades, calf) comes from the mould. RM_SHAPE blends.
# Pinned vertices (head, foot: "pin" attribute from ref_body.py) and the hands (mitten vs fingers) are not moved.
# Coordinates: world x = character's left, y up, z forward; Blender = (x, -z, y).
import bpy
import bmesh
import json
import os
import sys
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, os.path.dirname(__file__))
import head_game as G  # noqa: E402
import ref_body as RB  # noqa: E402

ROOT = RB.ROOT
SRC = os.path.join(ROOT, os.environ.get("RM_SRC", "output/ref/survivor/ref_body_v5base.blend"))
MOULD = os.path.join(ROOT, os.environ.get("RM_MOULD", "output/mpfb/mpfb_male_t.blend"))
TAG = os.environ.get("RM_TAG", "ref_body_v6")
SIZE = float(os.environ.get("RM_SIZE", "1.0"))  # 1: ring size from the survivor, 0: from the mould
SHAPE = float(os.environ.get("RM_SHAPE", "1.0"))  # 1: cross-section shape from the mould, 0: unchanged
CLAMP = float(os.environ.get("RM_CLAMP", "0.25"))  # max radius change per vertex (misses, gaps between legs)
W = lambda co: np.array([co.x, co.z, -co.y])
B = lambda p: Vector((p[0], -p[2], p[1]))


def bands(pts, axis, step):
    """Index points by rounded coordinate along `axis` for quick band lookups."""
    idx = {}
    for i, p in enumerate(pts):
        idx.setdefault(int(round(p[axis] / step)), []).append(i)
    return idx


def centre(pts, idx, axis, v, step, keep, other):
    """Bounding-box centre (in the `other` coordinates) of the points near v along `axis` that pass `keep`."""
    k = int(round(v / step))
    sel = [pts[i] for j in (k - 1, k, k + 1) for i in idx.get(j, []) if keep(pts[i])]
    if not sel:
        return None
    a = np.array(sel)
    return np.array([(a[:, c].min() + a[:, c].max()) / 2 for c in other])


def main():
    sil = RB.Sil()
    L = RB.landmarks(sil)
    # ---- mould ----
    bpy.ops.wm.open_mainfile(filepath=MOULD)
    mo = bpy.data.objects["MPFB_Body"]
    MP = np.array([W(v.co) for v in mo.data.vertices])
    tris = [list(p.vertices) for p in mo.data.polygons]
    # ---- our body ----
    bpy.ops.wm.open_mainfile(filepath=SRC)
    ob = bpy.data.objects["Character"]
    me = ob.data
    pin = me.attributes.get("pin")
    OP = np.array([W(v.co) for v in me.vertices])
    # align the mould's torso depth centre to ours at the waist (both 1.78 m, feet on y = 0)
    yw = 1.05
    dz = (np.mean(OP[(np.abs(OP[:, 1] - yw) < 0.06) & (np.abs(OP[:, 0]) < 0.15), 2])
          - np.mean(MP[(np.abs(MP[:, 1] - yw) < 0.06) & (np.abs(MP[:, 0]) < 0.15), 2]))
    MP[:, 2] += dz
    bvh = BVHTree.FromPolygons([Vector(p) for p in MP], tris)
    m_y, o_y = bands(MP, 1, 0.005), bands(OP, 1, 0.005)
    m_x, o_x = bands(MP, 0, 0.005), bands(OP, 0, 0.005)
    crotch, wrist, root = L["crotch"], L["wrist"], L["armpit_x"] + 0.015
    # mould wrist: thinnest arm band between 60 % and 90 % of the hand-tip reach
    tip_m = MP[:, 0].max()
    cand = []
    for x in np.arange(0.6 * tip_m, 0.9 * tip_m, 0.005):
        s = [MP[i] for j in (int(round(x / 0.005)),) for i in m_x.get(j, []) if MP[i][1] > 1.1]
        if s:
            a = np.array(s)
            cand.append((np.ptp(a[:, 1]) + np.ptp(a[:, 2]), x))
    wrist_m = min(cand)[1]
    # heights: map ours -> mould through the crotch (the mould's legs split higher): piecewise linear
    mid = MP[(np.abs(MP[:, 0]) < 0.004) & (MP[:, 1] > 0.5) & (MP[:, 1] < 1.1)]
    crotch_m = float(mid[:, 1].min())
    ymap = lambda y: float(np.interp(y, [0.0, crotch, RB.HEIGHT], [0.0, crotch_m, RB.HEIGHT]))

    def region(p):
        ax = abs(p[0])
        if ax > root - 0.005 and p[1] > 1.15:
            return "hand" if ax > wrist - 0.005 else "arm"
        if p[1] < crotch - 0.005:
            return "leg"
        return "torso"

    # per vertex: (our centre, mould centre, direction, axis-free offset) -> mould radius in that direction
    res = {}
    for i, p in enumerate(OP):
        if pin and pin.data[i].value:
            continue
        r = region(p)
        if r == "hand":
            continue
        if p[0] < -1e-6:
            continue  # right side = mirror of the left (the mould is not exactly symmetric after posing)
        sx = 1.0
        if r == "torso":
            c_o = centre(OP, o_y, 1, p[1], 0.005, lambda q: abs(q[0]) < root, (0, 2))
            ym = ymap(p[1])
            c_m = centre(MP, m_y, 1, ym, 0.005, lambda q: abs(q[0]) < 0.17, (0, 2))
            if c_o is None or c_m is None:
                continue
            co, cm = np.array([0.0, p[1], c_o[1]]), np.array([0.0, ym, c_m[1]])
        elif r == "leg":
            side = lambda q: q[0] * sx > 0.0
            c_o = centre(OP, o_y, 1, p[1], 0.005, side, (0, 2))
            ym = ymap(p[1])
            c_m = centre(MP, m_y, 1, ym, 0.005, side, (0, 2))
            if c_o is None or c_m is None:
                continue
            co, cm = np.array([c_o[0], p[1], c_o[1]]), np.array([c_m[0], ym, c_m[1]])
        else:  # arm: same fraction along shoulder -> wrist
            t = (abs(p[0]) - root) / (wrist - root)
            xm = sx * (root + t * (wrist_m - root))
            arm_side = lambda q: q[0] * sx > 0 and q[1] > 1.1
            c_o = centre(OP, o_x, 0, p[0], 0.005, arm_side, (1, 2))
            c_m = centre(MP, m_x, 0, xm, 0.005, arm_side, (1, 2))
            if c_o is None or c_m is None:
                continue
            co, cm = np.array([p[0], c_o[0], c_o[1]]), np.array([xm, c_m[0], c_m[1]])
        d = p - co
        if r == "arm":
            d[0] = 0.0
        else:
            d[1] = 0.0
        n = np.linalg.norm(d)
        if n < 1e-6:
            continue
        hit = bvh.ray_cast(Vector(cm), Vector(d / n), 0.4)
        if hit[0] is None:
            continue
        res[i] = (r, co, d / n, n, (np.array(hit[0][:]) - cm) @ (d / n))
    # ring groups for the size match: same region + rounded coordinate along the limb
    groups = {}
    for i, (r, co, u, n, rm) in res.items():
        key = (r, np.sign(OP[i][0]) if r != "torso" else 0, int(round((OP[i][0] if r == "arm" else OP[i][1]) / 0.006)))
        groups.setdefault(key, []).append(i)
    moved = 0
    for key, ids in groups.items():
        s_size = np.mean([res[i][3] for i in ids]) / np.mean([res[i][4] for i in ids])
        s = SIZE * s_size + (1 - SIZE)
        for i in ids:
            r, co, u, n, rm = res[i]
            new_n = n + SHAPE * (float(np.clip(rm * s, n * (1 - CLAMP), n * (1 + CLAMP))) - n)
            q = OP[i] + u * (new_n - n)
            me.vertices[i].co = B(q)
            moved += 1
    # mirror: every right-side vertex copies its left partner (matched on the original, symmetric body)
    left = {(round(OP[i][0], 5), round(OP[i][1], 5), round(OP[i][2], 5)): i for i in range(len(OP)) if OP[i][0] > 1e-6}
    for i in range(len(OP)):
        if OP[i][0] < -1e-6:
            j = left.get((round(-OP[i][0], 5), round(OP[i][1], 5), round(OP[i][2], 5)))
            if j is not None:
                c = me.vertices[j].co
                me.vertices[i].co = Vector((-c.x, c.y, c.z))
    me.update()
    G.flat(ob)
    st = {"character": G.stats(ob), "moved": moved, "closed": G.closed(ob), "symmetry": G.symmetry(ob),
          "mould_dz": round(float(dz), 4), "mould_wrist_x": round(float(wrist_m), 3), "groups": len(groups), "crotch_mould": round(crotch_m, 3)}
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(RB.OUT, f"{TAG}.blend"))
    print("RM_STATS", json.dumps(st))


if __name__ == "__main__":
    main()
