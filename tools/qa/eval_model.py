# E1: automatic gates for a character/prop .blend (see notes/pipeline-karakter-dan-evaluasi.md).
#   blender -b <file.blend> --factory-startup -P tools/qa/eval_model.py -- --budget 3000 --height 1.78
# Options: --budget N (triangles, whole model), --height M (metres), --asym (skip the symmetry gate),
#          --quad-min 0.85, --sliver-max 0.02, --tag NAME, --export (also run the glb round trip).
# Measures the model as it renders: modifiers applied, world space. Writes output/qa/<tag>_eval.json and prints
# one line per gate: PASS / FAIL / INFO.
import math
import os
import sys

import bmesh
import bpy
import numpy as np
from mathutils import kdtree

sys.path.insert(0, os.path.dirname(__file__))
import qa_common as Q  # noqa: E402

SLIVER = 8.0  # longest_edge^2 / (2 * area): 1.15 equilateral, > 8 = needle
FOLD = 5.0  # degrees: a quad whose two triangles differ more than this is folded (the split shows)


def opts(p):
    p.add_argument("--budget", type=int, default=0)
    p.add_argument("--height", type=float, default=0.0)
    p.add_argument("--asym", action="store_true")
    p.add_argument("--quad-min", type=float, default=0.85)
    p.add_argument("--sliver-max", type=float, default=0.02)
    p.add_argument("--tag", default="")
    p.add_argument("--export", action="store_true")


def topology(me, wall=0.0):
    """Counts on one world-space mesh. wall: garment wall thickness (qa_wall): quads that short are rims, not slivers."""
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.normal_update()
    faces = bm.faces
    n_f = len(faces)
    sizes = np.array([len(f.verts) for f in faces]) if n_f else np.zeros(0)
    boundary = sum(1 for e in bm.edges if len(e.link_faces) == 1)
    over = sum(1 for e in bm.edges if len(e.link_faces) > 2)
    loose_e = sum(1 for e in bm.edges if not e.link_faces)
    loose_v = sum(1 for v in bm.verts if not v.link_edges)
    flipped_edges = sum(1 for e in bm.edges if len(e.link_faces) == 2 and not e.is_contiguous)
    interior = sum(1 for f in faces if all(len(e.link_faces) > 2 for e in f.edges))
    zero_area = sum(1 for f in faces if f.calc_area() < 1e-10)
    # signed volume (closed meshes): negative = normals point inside
    vol = 0.0
    for f in faces:
        vs = [v.co for v in f.verts]
        for i in range(1, len(vs) - 1):
            vol += vs[0].dot(vs[i].cross(vs[i + 1])) / 6.0
    # slivers on the triangulated copy (what the game engine sees)
    # Needles. A long flat quad split in two needles is invisible with flat shading, so a needle only counts as a
    # "bad sliver" when it was modelled as a triangle, or when its quad/n-gon is folded (> FOLD deg between parts).
    tri = bm.copy()
    sides = tri.faces.layers.int.new("qa_sides")
    fid = tri.faces.layers.int.new("qa_face")
    rim = set()
    for i, f in enumerate(tri.faces):
        f[sides], f[fid] = len(f.verts), i
        if wall and len(f.verts) == 4 and 0.5 * wall < min(e.calc_length() for e in f.edges) < 1.6 * wall:
            rim.add(i)  # the thin side of a garment wall (Solidify rim): thin by design
    bmesh.ops.triangulate(tri, faces=tri.faces[:])
    groups = {}
    for f in tri.faces:
        groups.setdefault(f[fid], []).append(f)
    sl = sl_bad = sl_rim = 0
    for gi, parts in groups.items():
        n0 = parts[0].normal
        folded = any(n0.angle(p.normal, 0.0) > math.radians(FOLD) for p in parts[1:] if p.normal.length > 0)
        for f in parts:
            a = f.calc_area()
            L = max(e.calc_length() for e in f.edges)
            if a < 1e-12 or L * L / (2 * a) > SLIVER:
                sl += 1
                if gi in rim:
                    sl_rim += 1
                else:
                    sl_bad += f[sides] == 3 or folded
    n_tri = len(tri.faces)
    tri.free()
    # duplicate vertices (closer than 0.01 mm)
    kd = kdtree.KDTree(len(bm.verts))
    for v in bm.verts:
        kd.insert(v.co, v.index)
    kd.balance()
    dup = sum(1 for v in bm.verts if len(kd.find_range(v.co, 1e-5)) > 1) // 2
    bm.free()
    return {
        "vertices": len(me.vertices), "faces": n_f, "triangles": n_tri,
        "quads": int((sizes == 4).sum()), "tris_faces": int((sizes == 3).sum()), "ngons": int((sizes > 4).sum()),
        "boundary_edges": boundary, "nonmanifold_edges": over, "loose_edges": loose_e, "loose_vertices": loose_v,
        "inconsistent_normal_edges": flipped_edges, "interior_faces": interior, "zero_area_faces": zero_area,
        "signed_volume_m3": round(vol, 6), "slivers": sl, "slivers_bad": sl_bad, "slivers_rim": sl_rim, "duplicate_vertices": dup,
    }


def symmetry(me):
    vs = me.vertices
    if not len(vs):
        return 0
    kd = kdtree.KDTree(len(vs))
    for v in vs:
        kd.insert(v.co, v.index)
    kd.balance()
    return sum(1 for v in vs if kd.find((-v.co.x, v.co.y, v.co.z))[2] > 1e-4)


def uv_check(me, res=512):
    """Zero-area UV faces and the share of UV area covered more than once (mirrored halves count as overlap)."""
    if not me.uv_layers:
        return None
    uv = me.uv_layers.active.data
    cover = np.zeros((res, res), np.int16)
    zero = 0
    for p in me.polygons:
        pts = np.array([uv[li].uv[:] for li in p.loop_indices]) * res
        for i in range(1, len(pts) - 1):
            a, b, c = pts[0], pts[i], pts[i + 1]
            area = (b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])
            if abs(area) < 1e-6:
                zero += 1
                continue
            x0, x1 = int(max(0, np.floor(min(a[0], b[0], c[0])))), int(min(res, np.ceil(max(a[0], b[0], c[0]))))
            y0, y1 = int(max(0, np.floor(min(a[1], b[1], c[1])))), int(min(res, np.ceil(max(a[1], b[1], c[1]))))
            if x1 <= x0 or y1 <= y0:
                continue
            X, Y = np.meshgrid(np.arange(x0, x1) + 0.5, np.arange(y0, y1) + 0.5)
            w0 = ((b[0] - X) * (c[1] - Y) - (c[0] - X) * (b[1] - Y)) / area
            w1 = ((c[0] - X) * (a[1] - Y) - (a[0] - X) * (c[1] - Y)) / area
            inside = (w0 >= 0) & (w1 >= 0) & (w0 + w1 <= 1)
            cover[y0:y1, x0:x1] += inside
    used = (cover > 0).sum()
    return {"layer": me.uv_layers.active.name, "zero_area_uv_tris": zero,
            "overlap_share": round(float((cover > 1).sum() / used), 4) if used else 0.0,
            "uv_space_used": round(float(used / res / res), 4)}


def weights(ob):
    """Skin weights on the original mesh: vertices without weight, totals far from 1, more than 4 bones."""
    arm = ob.find_armature()
    if arm is None:
        return None
    bones = {b.name for b in arm.data.bones if b.use_deform}
    gi = {g.index for g in ob.vertex_groups if g.name in bones}
    none = off = many = 0
    for v in ob.data.vertices:
        ws = [g.weight for g in v.groups if g.group in gi and g.weight > 1e-4]
        if not ws:
            none += 1
            continue
        if abs(sum(ws) - 1) > 0.01:
            off += 1
        if len(ws) > 4:
            many += 1
    return {"armature": arm.name, "deform_bones": len(bones), "unweighted_vertices": none,
            "not_normalised": off, "over_4_influences": many}


def joint_rings(me, H):
    """Approximate edge rings at the knee (left leg, z band) and elbow (left arm, x band, T-pose only)."""
    co = np.array([v.co[:] for v in me.vertices]) if len(me.vertices) else np.zeros((0, 3))
    out = {}

    def levels(vals):
        vals = np.sort(vals)
        if not len(vals):
            return 0
        return int(1 + (np.diff(vals) > 0.006).sum())  # distinct levels 6 mm apart
    leg = co[(co[:, 0] > 0.02) & (np.abs(co[:, 2] - 0.285 * H) < 0.035 * H)]
    out["knee"] = levels(leg[:, 2])
    width = np.ptp(co[:, 0]) if len(co) else 0
    if width > 0.8 * H:  # T-pose: arms along x. Elbow = halfway shoulder (0.12 H) -> wrist (tip - 0.11 H)
        tip = co[:, 0].max()
        ex = (0.12 * H + tip - 0.11 * H) / 2
        arm = co[(np.abs(co[:, 0] - ex) < 0.035 * H) & (co[:, 2] > 0.7 * H)]
        out["elbow"] = levels(arm[:, 0])
    return out


def main():
    a = Q.args("E1 gates", opts)
    tag = Q.tag_of(a)
    objs = Q.meshes()
    report = {"file": bpy.data.filepath, "objects": {}}
    gates = []

    def gate(name, ok, value, need):
        gates.append({"gate": name, "result": "PASS" if ok else "FAIL", "value": value, "need": need})

    def info(name, value):
        gates.append({"gate": name, "result": "INFO", "value": value, "need": ""})

    total = {"triangles": 0, "faces": 0, "quads": 0, "slivers": 0, "slivers_bad": 0}
    joined = []
    for ob in objs:
        me = Q.evaluated_mesh(ob)
        t = topology(me, float(ob.get("qa_wall", 0.0)))
        t["asymmetric_on_purpose"] = bool(ob.get("qa_asym", False))
        t["symmetry_unmatched"] = symmetry(me)
        t["uv"] = uv_check(me)
        t["weights"] = weights(ob)
        t["face_colours"] = any(at.domain == "FACE" and at.data_type in ("FLOAT_COLOR", "BYTE_COLOR")
                                for at in ob.data.attributes) or bool(ob.data.color_attributes)
        t["materials"] = [m.name for m in ob.data.materials if m]
        report["objects"][ob.name] = t
        t["triangles_on_purpose"] = bool(ob.get("qa_tris_ok", False))
        for k in total:
            if k in ("faces", "quads") and t["triangles_on_purpose"]:
                continue  # hair clumps etc.: triangles by design, not in the quad share
            total[k] += t[k]
        if not t["asymmetric_on_purpose"]:  # hair etc. (custom property qa_asym) stays out of the symmetry check
            joined.append(np.array([v.co[:] for v in me.vertices]).reshape(-1, 3))
        bpy.data.meshes.remove(me)
    lo, hi = Q.world_bounds(objs)
    H = float(hi[2] - lo[2])
    report["total"] = total
    report["bounds"] = {"min": [round(float(x), 4) for x in lo], "max": [round(float(x), 4) for x in hi],
                        "height_m": round(H, 4)}

    # ---- gates ----
    if a.budget:
        gate("triangles <= budget", total["triangles"] <= a.budget, total["triangles"], a.budget)
    else:
        info("triangles", total["triangles"])
    for name, t in report["objects"].items():
        holes = t["boundary_edges"] + t["nonmanifold_edges"]
        if bpy.data.objects[name].get("qa_open_ok"):
            # skin under clothes removed on purpose (tools/blender/clothes.py): its edges sit inside a garment
            info(f"{name}: open on purpose (covered by clothes), boundary edges", holes)
        else:
            gate(f"{name}: closed", holes == 0, holes, 0)
        gate(f"{name}: normals consistent", t["inconsistent_normal_edges"] == 0, t["inconsistent_normal_edges"], 0)
        if holes == 0:
            gate(f"{name}: normals outward", t["signed_volume_m3"] > 0, t["signed_volume_m3"], "> 0")
        junk = t["duplicate_vertices"] + t["loose_vertices"] + t["loose_edges"] + t["interior_faces"] + t["zero_area_faces"]
        gate(f"{name}: no junk geometry", junk == 0, junk, 0)
        if t["uv"]:
            gate(f"{name}: UV overlap", t["uv"]["overlap_share"] <= 0.02, t["uv"]["overlap_share"], "<= 0.02")
        if t["weights"]:
            w = t["weights"]
            bad = w["unweighted_vertices"] + w["not_normalised"] + w["over_4_influences"]
            gate(f"{name}: skin weights", bad == 0, bad, 0)
    qs = total["quads"] / max(1, total["faces"])
    gate("quad share", qs >= a.quad_min, round(qs, 3), a.quad_min)
    ss = total["slivers_bad"] / max(1, total["triangles"])
    gate("bad sliver share (tri or folded)", ss <= a.sliver_max, round(ss, 4), a.sliver_max)
    info("needles incl. flat quads", total["slivers"])
    gate("feet on the ground", abs(lo[2]) <= 0.005, round(float(lo[2]), 4), "|z| <= 0.005")
    if a.height:
        gate("height", abs(H - a.height) <= 0.01 * a.height, round(H, 4), f"{a.height} +- 1%")
    else:
        info("height_m", round(H, 4))
    allco = np.concatenate(joined) if joined else np.zeros((0, 3))
    me_all = bpy.data.meshes.new("_qa_all")
    me_all.vertices.add(len(allco))
    me_all.vertices.foreach_set("co", allco.ravel())
    rings = joint_rings(me_all, H)
    # symmetry on the whole model: a left part (Eyebrow_L) is matched by its right twin
    report["symmetry_unmatched_all"] = symmetry(me_all)
    if not a.asym:
        gate("symmetric (whole model)", report["symmetry_unmatched_all"] == 0, report["symmetry_unmatched_all"], 0)
    bpy.data.meshes.remove(me_all)
    report["joint_rings"] = rings
    for j, n in rings.items():
        gate(f"rings at {j} (approx.)", n >= 3, n, ">= 3")
    if a.export:
        import export_glb as X
        rt = X.round_trip(os.path.join(Q.QA_OUT, f"{tag}.glb"))
        report["export"] = rt
        gate("glb round trip", rt["ok"], rt["summary"], "reopens, same triangles, colours kept")

    report["gates"] = gates
    report["passed"] = all(g["result"] != "FAIL" for g in gates)
    path = Q.save_json(report, f"{tag}_eval.json")
    for g in gates:
        print(f"QA {g['result']:4}  {g['gate']}: {g['value']}" + (f"  (need {g['need']})" if g["need"] != "" else ""))
    n_fail = sum(g["result"] == "FAIL" for g in gates)
    print(f"QA_DONE {tag}: {len(gates) - n_fail}/{len(gates)} ok, {n_fail} fail -> {path}")


if __name__ == "__main__":
    main()
