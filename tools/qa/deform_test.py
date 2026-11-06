# E4: deformation test. Puts the rig in standard test poses and measures the skinned mesh in each one.
#   blender -b <rigged.blend> --factory-startup -P tools/qa/deform_test.py -- [--tag NAME] [--size 360]
# Needs the bone names of tools/blender/rig_game.py (missing bones are skipped).
# Per pose:
#   flipped faces: posed face normal points away (> 90 deg) from the rest normal turned by the face's own bones
#   collapsed faces: posed area < 25 % of the rest area
#   joint volume: verts in the joint's slab at rest, mean distance to the joint centre posed / rest (elbow, knee,
#     wrist, shoulder, hip); the gate wants >= 0.7 (pipeline E4)
# Output: output/qa/<tag>_deform.json and <tag>_deform.png (one row per pose: front, 3/4, close-up of the joint).
import math
import os
import sys
import tempfile

import bpy
import numpy as np
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(__file__))
import qa_common as Q  # noqa: E402
import export_glb as X  # noqa: E402
import sheet as SH  # noqa: E402

DOWN, UP, FWD, BACK = (0, 0, -1), (0, 0, 1), (0, -1, 0), (0, 1, 0)
SIDES = (".L", ".R")
FINGERS = ("index", "middle", "ring", "pinky")
# pose: list of (bone, "bend", toward world dir, degrees) or (bone, "turn", world axis, degrees); "*" = both sides
POSES = {
    "rest": [],
    "a_pose": [("upper_arm*", "bend", DOWN, 45)],
    "arms_up": [("upper_arm*", "bend", UP, 70), ("shoulder*", "bend", UP, 15)],
    "elbow": [("upper_arm*", "bend", FWD, 30), ("forearm*", "bend", FWD, 120)],
    "fist": [("upper_arm*", "bend", DOWN, 30)] + [(f"{f}.0{s}*", "bend", DOWN, d) for f in FINGERS
                                                  for s, d in ((1, 70), (2, 95), (3, 60))]
            + [("thumb.01*", "bend", DOWN, 25), ("thumb.02*", "bend", DOWN, 35), ("thumb.03*", "bend", DOWN, 35)],
    "squat": [("thigh*", "bend", FWD, 100), ("shin*", "bend", BACK, 120), ("foot*", "bend", UP, 15),
              ("upper_arm*", "bend", FWD, 60)],
    "run": [("thigh.L", "bend", FWD, 60), ("shin.L", "bend", BACK, 80), ("thigh.R", "bend", BACK, 30),
            ("shin.R", "bend", BACK, 40), ("upper_arm*", "bend", DOWN, 65), ("forearm*", "bend", FWD, 80)],
    "torso": [("spine", "bend", FWD, 20), ("chest", "bend", FWD, 15), ("upper_chest", "turn", UP, 25),
              ("neck", "turn", UP, 25), ("head", "turn", UP, 35), ("upper_arm*", "bend", DOWN, 45)],
}
# joint -> (bone whose head is the joint, slab half width m, radius m)
JOINTS = {"elbow": ("forearm", 0.03, 0.09), "knee": ("shin", 0.04, 0.12), "wrist": ("hand", 0.02, 0.07),
          "shoulder": ("upper_arm", 0.03, 0.12), "hip": ("thigh", 0.04, 0.15)}
FOCUS = {"elbow": "forearm.L", "fist": "hand.L", "squat": "shin.L", "run": "shin.L", "arms_up": "upper_arm.L",
         "a_pose": "upper_arm.L", "torso": "neck", "rest": "hand.L"}


def opts(p):
    p.add_argument("--tag", default="")
    p.add_argument("--size", type=int, default=360)
    p.add_argument("--body", default="Character")
    p.add_argument("--min-volume", type=float, default=0.7)


def expand(name, pb):
    if name.endswith("*"):
        return [name[:-1] + s for s in SIDES if name[:-1] + s in pb]
    return [name] if name in pb else []


def set_pose(rig, ops):
    """Rotate pose bones about world axes through their heads, parents before children."""
    pb = rig.pose.bones
    for b in pb:
        b.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()
    order = {b.name: len(b.parent_recursive) for b in pb}
    todo = sorted([(n, kind, Vector(d), deg) for name, kind, d, deg in ops for n in expand(name, pb)],
                  key=lambda t: order[t[0]])
    for n, kind, d, deg in todo:
        b = pb[n]
        m = rig.matrix_world @ b.matrix
        head = m.translation.copy()
        if kind == "bend":
            bone_dir = (m.to_3x3() @ Vector((0, 1, 0))).normalized()
            axis = bone_dir.cross(d.normalized())
            if axis.length < 1e-6:
                continue
            axis.normalize()
        else:
            axis = d.normalized()
        R = Matrix.Rotation(math.radians(deg), 4, axis)
        new = Matrix.Translation(head) @ R @ Matrix.Translation(-head) @ m
        b.matrix = rig.matrix_world.inverted() @ new
        bpy.context.view_layer.update()


def posed_coords(body):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = body.evaluated_get(dg)
    me = ev.to_mesh()
    co = np.array([body.matrix_world @ v.co for v in me.vertices])
    ev.to_mesh_clear()
    return co


def face_data(co, faces):
    n, area = [], []
    for f in faces:
        p = co[f]
        c = np.zeros(3)
        for i in range(len(f)):  # Newell normal: fine for quads and n-gons
            a, b = p[i], p[(i + 1) % len(f)]
            c += np.cross(a, b)
        l = np.linalg.norm(c)
        n.append(c / l if l > 1e-12 else c)
        area.append(l / 2)
    return np.array(n), np.array(area)


def weights(body):
    gname = {g.index: g.name for g in body.vertex_groups}
    W = []
    for v in body.data.vertices:
        W.append({gname[g.group]: g.weight for g in v.groups if g.weight > 0})
    return W


def bone_rot(rig):
    """World 3x3 deformation rotation of every bone (pose relative to rest)."""
    out = {}
    for b in rig.pose.bones:
        M = rig.matrix_world @ b.matrix @ b.bone.matrix_local.inverted() @ rig.matrix_world.inverted()
        out[b.name] = np.array(M.to_3x3())
    return out


def measure(rig, body, rest, faces, n0, a0, W, slabs):
    co = posed_coords(body)
    n1, a1 = face_data(co, faces)
    R = bone_rot(rig)
    flipped = collapsed = 0
    bad = []
    for fi, f in enumerate(faces):
        M = np.zeros((3, 3))
        tw = 0.0
        for vi in f:
            for g, w in W[vi].items():
                if g in R:
                    M += R[g] * w
                    tw += w
        exp = (M / tw) @ n0[fi] if tw else n0[fi]
        if np.dot(exp, n1[fi]) < 0:
            flipped += 1
            bad.append(fi)
        if a0[fi] > 1e-9 and a1[fi] / a0[fi] < 0.25:
            collapsed += 1
            bad.append(fi)
    vol = {}
    for jn, (bn, idx, d0) in slabs.items():
        head = np.array(rig.matrix_world @ rig.pose.bones[bn].head)
        d1 = np.linalg.norm(co[idx] - head, axis=1)
        vol[jn] = round(float(d1.mean() / d0.mean()), 3)
    return {"flipped_faces": flipped, "collapsed_faces": collapsed, "joint_volume": vol}, co, sorted(set(bad))


def joint_slabs(rig, rest):
    out = {}
    for jn, (bone, half, rad) in JOINTS.items():
        for s in SIDES:
            bn = bone + s
            if bn not in rig.pose.bones:
                continue
            b = rig.data.bones[bn]
            head = np.array(rig.matrix_world @ b.head_local)
            d = np.array((rig.matrix_world.to_3x3() @ (b.tail_local - b.head_local)).normalized())
            rel = rest - head
            along = rel @ d
            radial = np.linalg.norm(rel - np.outer(along, d), axis=1)
            idx = np.nonzero((np.abs(along) < half) & (radial < rad))[0]
            if len(idx) >= 4:
                out[jn + s] = (bn, idx, np.linalg.norm(rest[idx] - head, axis=1))
    return out


def mark_bad(body, bad):
    """Red corner colour on flipped / collapsed faces for the picture."""
    me = body.data
    lay = me.color_attributes.get("Color") or me.color_attributes.get("Col")
    if lay is None or lay.domain != "CORNER":
        return
    for fi in bad:
        for li in me.polygons[fi].loop_indices:
            lay.data[li].color = (1.0, 0.05, 0.05, 1.0)


def shots(rig, body, pose, size, tmp, co):
    cam = Q.ortho_camera()
    cam.data.clip_end = 100
    lo, hi = co.min(0), co.max(0)
    c = (lo + hi) / 2
    span = float(max(hi - lo)) * 1.08
    out = []
    for view in ("front", "34"):
        cam.data.ortho_scale = span
        d = np.array(Q.VIEWS[view])
        Q.aim(cam, c + d * 10, c)
        out.append(Q.load_png(Q.render_to(os.path.join(tmp, f"{pose}_{view}.png"), size, size)))
    b = rig.pose.bones.get(FOCUS.get(pose, "hand.L"))
    fc = np.array(rig.matrix_world @ b.head) if b else c
    cam.data.ortho_scale = 0.38
    d = np.array(Q.VIEWS["34"]) + np.array([0, 0, 0.35])
    Q.aim(cam, fc + d * 10, fc)
    out.append(Q.load_png(Q.render_to(os.path.join(tmp, f"{pose}_close.png"), size, size)))
    return np.concatenate(out, 1)


def main():
    a = Q.args("E4 deformation test", opts)
    tag = Q.tag_of(a)
    rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    body = bpy.data.objects[a.body]
    X.corner_colours()
    SH.setup_scene()
    for ob in Q.meshes():
        for p in ob.data.polygons:
            p.use_smooth = False
    faces = [list(p.vertices) for p in body.data.polygons]
    set_pose(rig, [])
    rest = posed_coords(body)
    n0, a0 = face_data(rest, faces)
    W = weights(body)
    slabs = joint_slabs(rig, rest)
    base_col = None
    lay = body.data.color_attributes.get("Color")
    if lay is not None:
        base_col = [c.color[:] for c in lay.data]
    tmp = tempfile.mkdtemp(prefix="qa_deform_")
    res, rows = {}, []
    for pose, ops in POSES.items():
        set_pose(rig, ops)
        m, co, bad = measure(rig, body, rest, faces, n0, a0, W, slabs)
        res[pose] = m
        if base_col is not None:
            for i, c in enumerate(base_col):
                lay.data[i].color = c
        mark_bad(body, bad)
        rows.append(shots(rig, body, pose, a.size, tmp, co))
        print(f"QA_POSE {pose}: flipped {m['flipped_faces']} collapsed {m['collapsed_faces']} volume {m['joint_volume']}")
    set_pose(rig, [])
    worst = {}
    for m in res.values():
        for j, v in m["joint_volume"].items():
            worst[j] = min(worst.get(j, 9), v)
    gates = [("no flipped faces", sum(m["flipped_faces"] for m in res.values()) == 0,
              {p: m["flipped_faces"] for p, m in res.items() if m["flipped_faces"]}, "0"),
             ("no collapsed faces", sum(m["collapsed_faces"] for m in res.values()) == 0,
              {p: m["collapsed_faces"] for p, m in res.items() if m["collapsed_faces"]}, "0"),
             ("joint volume", min(worst.values()) >= a.min_volume, worst, f">= {a.min_volume}")]
    out = {"poses": res, "worst_joint_volume": worst,
           "gates": [{"gate": g, "result": "PASS" if ok else "FAIL", "value": v, "need": n} for g, ok, v, n in gates]}
    out["passed"] = all(ok for _, ok, _, _ in gates)
    gap = np.ones((4, rows[0].shape[1], 4), np.float32)
    grid = rows[0]
    for r in rows[1:]:
        grid = np.concatenate([grid, gap, r], 0)
    os.makedirs(Q.QA_OUT, exist_ok=True)
    png = os.path.join(Q.QA_OUT, f"{tag}_deform.png")
    Q.save_png(grid, png)
    path = Q.save_json(out, f"{tag}_deform.json")
    for g in out["gates"]:
        print(f"QA {g['result']:4}  {g['gate']}: {g['value']}  (need {g['need']})")
    print("QA_DONE", path, png, "rows:", list(POSES))


if __name__ == "__main__":
    main()
