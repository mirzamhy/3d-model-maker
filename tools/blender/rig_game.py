# Game skeleton for a ref_body character: deform bones only (fits three.js / Unity / Godot through glb), placed
# from the joint centres ref_body.py writes (joints_<tag>.json), spine and head from slices of the mesh.
#   blender -b <character.blend> --factory-startup -P tools/blender/rig_game.py -- --joints <joints.json> --out <rigged.blend>
# Bones (left side mirrored to .R): root > hips > spine > chest > upper_chest > neck > head;
# upper_chest > shoulder > upper_arm > forearm > hand > thumb/index/middle/ring/pinky .01-.03;
# hips > thigh > shin > foot > toe.  Rolls: arm and finger bones Z up, leg bones Z forward.
# Weights (--weights rings, default): every vertex goes to the bone with the smallest distance / bone radius,
# then the weights are smoothed over the mesh edges (SMOOTH passes: a blend over ~2 rings at every joint), the right
# side is copied from the left (exact symmetry), at most 4 bones per vertex (game engines), small weights dropped.
# --weights heat: Blender's automatic weights (bone heat); in the survivor test they came out asymmetric (elbow
# 0.69/0.31 left vs 0.19/0.81 right) and leaked between fingers. Hair, ears, eyebrows: 100 % on "head".
import argparse
import json
import os
import sys

import bpy
import numpy as np
from mathutils import Vector

FINGER_NAMES = ["pinky", "ring", "middle", "index"]  # joints json: finger0 = little ... finger3 = index
RIGID_HEAD = ("Hair", "Ears", "Eyebrow_L", "Eyebrow_R")
# bone radius as a share of the stature: the distance score is distance / radius, so the wide torso wins its own
# side verts against the arm root next to them
# Bones of one limb share a radius: different radii move the 50/50 line off the joint toward the thinner bone
# (survivor v11: thigh 0.05 vs shin 0.035 put it 8 cm under the knee and the back of the knee flipped at 90 deg).
RADIUS = {"hips": 0.08, "spine": 0.08, "chest": 0.085, "upper_chest": 0.085, "neck": 0.055, "head": 0.06,
          "shoulder": 0.035, "upper_arm": 0.03, "forearm": 0.025, "hand": 0.018, "thigh": 0.045, "shin": 0.045,
          "foot": 0.04, "toe": 0.04}
FINGER_R = 0.007
# (parent, child, crease direction in the rest pose, half width outer side, inner side) as share of the stature;
# inner width 0 = keep the smoothed weights. Knee crease = back (+y).
# Survivor v11 sweep (thigh 90 deg, shin bent): smoothed weights flip from 100 deg; 0.04 / 0.12 none up to 130 deg,
# knee volume 0.77 (was 0.79). Elbow crease = front (-y, the T-pose arm bends forward).
HINGES = [("thigh.L", "shin.L", (0, 1, 0), float(os.environ.get("RIG_KNEE_OUT", "0.04")),
           float(os.environ.get("RIG_KNEE_IN", "0.12"))),
          ("upper_arm.L", "forearm.L", (0, -1, 0), float(os.environ.get("RIG_ELBOW_OUT", "0.03")),
           float(os.environ.get("RIG_ELBOW_IN", "0")))]
SMOOTH = int(os.environ.get("RIG_SMOOTH", "3"))
MAX_INF = 4
MIN_W = 0.03


def opts():
    p = argparse.ArgumentParser()
    p.add_argument("--joints", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--body", default="Character")
    p.add_argument("--weights", default="rings", choices=["rings", "heat"])
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    return p.parse_args(argv)


def slice_y(co, z, half_x=0.1, dz=0.015):
    """Front/back centre (Blender y) of the mesh slice at height z near the centre line."""
    sel = co[(np.abs(co[:, 2] - z) < dz) & (np.abs(co[:, 0]) < half_x)]
    return float((sel[:, 1].min() + sel[:, 1].max()) / 2) if len(sel) else 0.0


def skeleton(J, co):
    """Left + centre bones: name -> (head, tail, parent, roll axis or None)."""
    V = lambda p: Vector(p)
    up, fwd = Vector((0, 0, 1)), Vector((0, -1, 0))
    hip_z, neck_z = J["hip"][2] + 0.02, J["neck_base_y"]
    spine_z = [hip_z + t * (neck_z - hip_z) for t in (0.0, 0.22, 0.5, 0.78, 1.0)]
    spine_p = [V((0, slice_y(co, z, 0.08), z)) for z in spine_z]
    head_z = J["chin_y"] - 0.02  # head pivot: under the chin, at the skull base height of a big low-poly head
    head_p = V((0, slice_y(co, head_z, 0.05), head_z))
    crown = V((0, head_p.y, J["crown_y"] - 0.035))  # crown_y includes the hair
    B = {"root": (V((0, 0, 0)), V((0, -0.25, 0)), None, up)}
    names = ["hips", "spine", "chest", "upper_chest"]
    for i, n in enumerate(names):
        B[n] = (spine_p[i], spine_p[i + 1], "root" if i == 0 else names[i - 1], fwd)
    B["neck"] = (spine_p[-1], head_p, "upper_chest", fwd)
    B["head"] = (head_p, crown, "neck", fwd)
    arm = V(J["arm_root"])
    sh0 = V((0.025, arm.y, arm.z + 0.02))
    B["shoulder.L"] = (sh0, arm, "upper_chest", up)
    B["upper_arm.L"] = (arm, V(J["elbow"]), "shoulder.L", up)
    B["forearm.L"] = (V(J["elbow"]), V(J["wrist"]), "upper_arm.L", up)
    B["hand.L"] = (V(J["wrist"]), V(J["knuckles"]), "forearm.L", up)
    for i, nm in enumerate(FINGER_NAMES):
        pts = [V(p) for p in J[f"finger{i}"]]
        for s in range(3):
            B[f"{nm}.0{s + 1}.L"] = (pts[s], pts[s + 1], "hand.L" if s == 0 else f"{nm}.0{s}.L", up)
    pts = [V(p) for p in J["thumb"]]
    for s in range(3):
        B[f"thumb.0{s + 1}.L"] = (pts[s], pts[s + 1], "hand.L" if s == 0 else f"thumb.0{s}.L", up)
    B["thigh.L"] = (V(J["hip"]), V(J["knee"]), "hips", fwd)
    B["shin.L"] = (V(J["knee"]), V(J["ankle"]), "thigh.L", fwd)
    B["foot.L"] = (V(J["ankle"]), V(J["ball"]), "shin.L", up)
    B["toe.L"] = (V(J["ball"]), V(J["toe"]), "foot.L", up)
    return B


def mirror(B):
    out = dict(B)
    for n, (h, t, par, roll) in B.items():
        if n.endswith(".L"):
            m = lambda v: Vector((-v.x, v.y, v.z))
            p2 = par[:-2] + ".R" if par and par.endswith(".L") else par
            out[n[:-2] + ".R"] = (m(h), m(t), p2, roll)
    return out


def build_armature(B):
    arm_d = bpy.data.armatures.new("Rig")
    rig = bpy.data.objects.new("Rig", arm_d)
    bpy.context.scene.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm_d.edit_bones
    for n, (h, t, _, _) in B.items():
        b = eb.new(n)
        b.head, b.tail = h, t
    for n, (h, t, par, roll) in B.items():
        b = eb[n]
        if par:
            b.parent = eb[par]
            b.use_connect = (eb[par].tail - h).length < 1e-4
        if roll is not None:
            b.align_roll(roll)
        b.use_deform = n != "root"
    bpy.ops.object.mode_set(mode="OBJECT")
    arm_d.display_type = "STICK"
    rig.show_in_front = True
    return rig


def seg_dist(P, h, t):
    d = t - h
    u = np.clip(((P - h) @ d) / (d @ d), 0, 1)
    return np.linalg.norm(P - (h + np.outer(u, d)), axis=1)


def ring_weights(body, B):
    """Distance / radius -> nearest bone, smoothed over the edges, mirrored left -> right, <= MAX_INF bones."""
    me = body.data
    co = np.array([body.matrix_world @ v.co for v in me.vertices])
    H = co[:, 2].max() - co[:, 2].min()
    names = [n for n in B if n != "root"]
    rad = lambda n: FINGER_R * H if n.split(".")[0] not in RADIUS else RADIUS[n.split(".")[0]] * H
    score = np.stack([seg_dist(co, np.array(B[n][0]), np.array(B[n][1])) / rad(n) for n in names], 1)
    W = np.zeros_like(score)
    W[np.arange(len(co)), score.argmin(1)] = 1.0
    # neck: the short band between the neck base and the head pivot (the torso and head radii would split it)
    nz0, nz1 = B["neck"][0][2], B["neck"][1][2]
    band = (co[:, 2] > nz0 - 0.005) & (co[:, 2] < nz1) & (np.abs(co[:, 0]) < 0.07 * H)
    W[band] = 0
    W[band, names.index("neck")] = 1.0
    nb = [[] for _ in co]
    for e in me.edges:
        a, b = e.vertices
        nb[a].append(b)
        nb[b].append(a)
    for _ in range(SMOOTH):
        W = 0.5 * W + 0.5 * np.array([W[n].mean(0) for n in nb])
    # hinge joints: parent/child share set by the position along the limb (smoothstep across the joint), wide on the
    # inner (crease) side and narrow on the outer side. Replaces the smoothed split there.
    for par, ch, inner, w_out, w_in in HINGES:
        if not w_in:
            continue
        ip, ic = names.index(par), names.index(ch)
        j = np.array(B[ch][0])
        ax = np.array(B[ch][1]) - j
        ax /= np.linalg.norm(ax)
        tot = W[:, ip] + W[:, ic]
        sel = tot > 0.5
        rel = co[sel] - j
        along = rel @ ax
        rad_v = rel - np.outer(along, ax)
        rn = np.linalg.norm(rad_v, axis=1) + 1e-9
        side = (rad_v @ np.array(inner)) / rn  # +1 = crease side
        width = w_out + (w_in - w_out) * np.clip(side, 0, 1)
        t = np.clip((along / (width * H) + 1) / 2, 0, 1)
        share = t * t * (3 - 2 * t)
        W[sel, ic] = tot[sel] * share
        W[sel, ip] = tot[sel] * (1 - share)
    # mirror: right side (x < 0) takes the weights of its left twin with .L <-> .R swapped
    swap = [names.index(n[:-2] + (".R" if n.endswith(".L") else ".L")) if n[-2:] in (".L", ".R") else i
            for i, n in enumerate(names)]
    from mathutils.kdtree import KDTree
    kd = KDTree(len(co))
    for i, p in enumerate(co):
        kd.insert(p, i)
    kd.balance()
    for i, p in enumerate(co):
        if p[0] < -1e-5:
            _, j, dist = kd.find((-p[0], p[1], p[2]))
            if dist < 1e-3:
                W[i] = W[j][swap]
    # game limits: MAX_INF strongest, drop tiny, normalise
    keep = np.argsort(-W, 1)[:, :MAX_INF]
    out = np.zeros_like(W)
    rows = np.arange(len(co))[:, None]
    out[rows, keep] = W[rows, keep]
    out[out < MIN_W] = 0
    out /= out.sum(1, keepdims=True)
    for n in names:
        body.vertex_groups.new(name=n)
    for k, n in enumerate(names):
        g = body.vertex_groups[n]
        for i in np.nonzero(out[:, k])[0]:
            g.add([int(i)], float(out[i, k]), "REPLACE")


def skin(rig, body_name, mode, B):
    body = bpy.data.objects[body_name]
    if mode == "heat":
        for o in bpy.context.view_layer.objects:
            o.select_set(False)
        body.select_set(True)
        rig.select_set(True)
        bpy.context.view_layer.objects.active = rig
        bpy.ops.object.parent_set(type="ARMATURE_AUTO")
    else:
        ring_weights(body, B)
        mw = body.matrix_world.copy()
        body.parent = rig
        body.matrix_world = mw
        m = body.modifiers.new("Armature", "ARMATURE")
        m.object = rig
    empty = [v.index for v in body.data.vertices if not v.groups]
    for name in RIGID_HEAD:
        ob = bpy.data.objects.get(name)
        if ob is None:
            continue
        g = ob.vertex_groups.new(name="head")
        g.add(list(range(len(ob.data.vertices))), 1.0, "REPLACE")
        mw = ob.matrix_world.copy()
        ob.parent = rig
        ob.matrix_world = mw
        m = ob.modifiers.new("Armature", "ARMATURE")
        m.object = rig
    return body, empty


def main():
    a = opts()
    J = json.load(open(a.joints))
    body = bpy.data.objects[a.body]
    co = np.array([body.matrix_world @ v.co for v in body.data.vertices])
    B = mirror(skeleton(J, co))
    rig = build_armature(B)
    body, empty = skin(rig, a.body, a.weights, B)
    groups = {g.index: g.name for g in body.vertex_groups}
    used = {}
    for v in body.data.vertices:
        for g in v.groups:
            if g.weight > 0.01:
                used[groups[g.group]] = used.get(groups[g.group], 0) + 1
    st = {"weights": a.weights, "bones": len(B), "deform_bones": len(B) - 1, "unweighted_vertices": len(empty),
          "bones_without_vertices": sorted(n for n in B if n != "root" and n not in used)}
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(a.out))
    print("RIG_STATS", json.dumps(st))


if __name__ == "__main__":
    main()
