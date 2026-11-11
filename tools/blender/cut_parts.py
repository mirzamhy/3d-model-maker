"""Cut a rigged, dressed character (ref_body -> rig_game -> clothes) into rigid parts, one per game bone.

User plan (sketch 2026-11-10): head (C), neck (D), torso, pelvis, upper arm, forearm, hand, thigh, shin, foot.
Each face goes to the part whose bones hold most of its vertex weight; the head objects (Head, Hair, Eyes, Ears) are
the head part; the neck stick in the body (part codes 0 + 2) is the neck part. Every part is parented to its bone
(rigid, no skinning) and its open cuts are capped, so a bent joint shows a cap, not a hole.
  blender -b <dressed.blend> --factory-startup -P tools/blender/cut_parts.py -- --out <parts.blend> [--sheet <png>]
"""
import sys, os, argparse, math
import bpy, bmesh
import numpy as np
from mathutils import Vector

PART_OF_BONE = {"hips": "pelvis", "spine": "torso", "chest": "torso", "upper_chest": "torso", "neck": "neck",
                "head": "head"}
for s in ("L", "R"):
    PART_OF_BONE.update({f"shoulder.{s}": "torso", f"upper_arm.{s}": f"upperArm.{s}", f"forearm.{s}": f"forearm.{s}",
                         f"hand.{s}": f"hand.{s}", f"thigh.{s}": f"thigh.{s}", f"shin.{s}": f"shin.{s}",
                         f"foot.{s}": f"foot.{s}", f"toe.{s}": f"foot.{s}"})
    for fn in ("thumb", "index", "middle", "ring", "pinky"):
        for k in (1, 2, 3):
            PART_OF_BONE[f"{fn}.0{k}.{s}"] = f"hand.{s}"
# bone each rigid part hangs on
BONE_OF_PART = {"head": "head", "neck": "neck", "torso": "chest", "pelvis": "hips"}
for s in ("L", "R"):
    BONE_OF_PART.update({f"upperArm.{s}": f"upper_arm.{s}", f"forearm.{s}": f"forearm.{s}", f"hand.{s}": f"hand.{s}",
                         f"thigh.{s}": f"thigh.{s}", f"shin.{s}": f"shin.{s}", f"foot.{s}": f"foot.{s}"})
HEAD_OBJS = ("Head", "Hair", "Eyes", "Ears")
NECK_CODES = (0, 2)    # ref_body face "part": 0 = neck stick inside the head, 2 = neck below the jaw
NECK_SINK = 0.03
NECK_STUB_BOTTOM = 1.38  # head template neck stub bottom cap (f2: z 1.376)
ARM_CODE = 3
# Shoulder (user: "rapikan bahu"). f2's arm joint sat at the sleeve edge (x 0.246): the arm swung around a point
# outside the shoulder, the tucked sleeve root rose like a shoulder pad and the torso's shoulder corner stuck out.
# The joint moves in to SHOULDER_X and everything of the upper arm inside it becomes a dome around the joint (a dome
# turned about its own centre keeps its shape, so lowering the arm changes nothing at the shoulder); the torso's
# shoulder is pulled inside that dome.
SHOULDER_X = float(os.environ.get("CP_SHOULDER_X", "0.20"))
SLEEVE_CUT = 0.0     # v4 without the dome: sleeve faces inside |x| 0.19 cut (0.14 = pad, 0.215 = armband)


def face_parts(ob):
    """Part name per face of a skinned mesh."""
    me = ob.data
    if ob.name in HEAD_OBJS:
        if ob.name != "Head":
            return ["head"] * len(me.polygons)
        # the head template's own thin neck stub (sides under the jaw + bottom cap) goes: the head ends at the jaw
        # (sketch C) and the neck is the body's neck stick (sketch D), which reaches up inside the skull
        out = []
        for p in me.polygons:
            c, n = ob.matrix_world @ p.center, p.normal
            stub = (c.z < 1.424 and abs(n.z) < 0.5 and c.y > -0.035) or c.z < NECK_STUB_BOTTOM
            out.append("drop" if stub else "head")
        return out
    if ob.name == "Shirt":
        # body shell -> torso; each sleeve shell (own island, root tucked inside the body shell) -> upper arm
        out = [isl_part(ob, i) for i in range(len(me.polygons))]
        # the sleeve root tucked inside the body swings out as a shoulder pad when the arm comes down: cut it
        return ["drop" if n.startswith("upperArm") and abs((ob.matrix_world @ p.center).x) < SLEEVE_CUT else n
                for n, p in zip(out, me.polygons)]
    gname = {g.index: g.name for g in ob.vertex_groups}
    vw = []
    for v in me.vertices:
        d = {}
        for g in v.groups:
            p = PART_OF_BONE.get(gname[g.group])
            if p:
                d[p] = d.get(p, 0.0) + g.weight
        vw.append(d)
    code = me.attributes["part"].data if "part" in me.attributes else None
    out = []
    for p in me.polygons:
        if code is not None and code[p.index].value in NECK_CODES:
            out.append("neck")
            continue
        tot = {}
        for vi in p.vertices:
            for k, w in vw[vi].items():
                tot[k] = tot.get(k, 0.0) + w
        best = max(tot, key=tot.get) if tot else "torso"
        if code is not None and code[p.index].value == ARM_CODE and best == "torso":
            best = "upperArm." + ("L" if p.center.x > 0 else "R")   # bare arm skin never on the torso
        best = leg_part(chain_part(best, ob.matrix_world @ p.center), ob.matrix_world @ p.center)
        if best in ("neck", "head"):   # body faces under the jaw / shirt collar: torso (the neck is the stick only)
            best = "torso"
        out.append(best)
    return out


CHAIN = {}   # side -> (axis origin, unit axis, [(cut position, part), ...])


def set_chain(rig):
    """Arm cut positions along the arm axis = the joints (elbow, wrist). The skin weights blend over the joint (hinge
    weights for a smooth bend) and put the weight cut 8 cm past the elbow: the forearm then turned about a point
    inside the upper arm part and came off it."""
    mw = rig.matrix_world
    for s in ("L", "R"):
        b = rig.data.bones
        o = mw @ b[f"upper_arm.{s}"].head_local
        ax = ((mw @ b[f"hand.{s}"].tail_local) - o).normalized()
        cuts = [(0.0, f"upperArm.{s}"), ((mw @ b[f"forearm.{s}"].head_local - o).dot(ax), f"forearm.{s}"),
                ((mw @ b[f"hand.{s}"].head_local - o).dot(ax), f"hand.{s}")]
        CHAIN[s] = (o, ax, cuts)


# user sketch (2026-11-10): pelvis (10) is a narrow briefs band, V down to the crotch; the thighs (11/12) start right
# under it and carry the hip side and the buttock. The cut follows the briefs line: crotch height in the middle,
# rising to HIP_SIDE_Z at the hip side. The thigh above its pivot becomes a dome around the pivot (as the shoulder).
HIP_CROTCH = float(os.environ.get("CP_HIP_CROTCH", "0.77"))
HIP_SIDE_Z = float(os.environ.get("CP_HIP_SIDE_Z", "0.80"))
HIP_SIDE_X = 0.15


def leg_part(best, c):
    """Pelvis / thigh face by the briefs line. The skin weights alone let the thigh reach the waist unevenly; the
    earlier shorts cut (pelvis hanging to the buttock fold) looked like a skirt and the thigh like a broken stub."""
    if best not in ("pelvis", "thigh.L", "thigh.R"):
        return best
    s = "L" if c.x > 0 else "R"
    k = min(1.0, abs(c.x) / HIP_SIDE_X)
    zc = HIP_CROTCH + (HIP_SIDE_Z - HIP_CROTCH) * k
    return "pelvis" if c.z > zc else f"thigh.{s}"


def dome_axis(ob, P, a):
    """Vertices above the pivot along the thigh axis a (pointing down the leg): onto a dome around the pivot, each at
    its own distance from the axis. A dome turned about its centre keeps its shape, so the hip stays round."""
    mw, mi = ob.matrix_world, ob.matrix_world.inverted()
    n = 0
    for v in ob.data.vertices:
        w = mw @ v.co
        d = w - P
        ax = d.dot(a)
        if ax >= 0 or d.length < 1e-6:
            continue
        r = (d - a * ax).length
        v.co = mi @ (P + d.normalized() * r)
        n += 1
    return n


def chain_part(best, c):
    """Upper arm / forearm / hand face: the part whose segment of the arm axis holds the face centre."""
    if not best.startswith(("upperArm", "forearm", "hand")):
        return best
    o, ax, cuts = CHAIN[best[-1]]
    t = (c - o).dot(ax)
    out = cuts[0][1]
    for pos, name in cuts:
        if t >= pos:
            out = name
    return out


ISL = {}


def isl_part(ob, i):
    """Part of face i by its mesh island: |x| of the island centre > 0.15 = sleeve."""
    if ob.name not in ISL:
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        bm.faces.ensure_lookup_table()
        lab = [None] * len(bm.faces)
        for f in bm.faces:
            if lab[f.index] is not None:
                continue
            st, fs = [f], []
            lab[f.index] = -1
            while st:
                g = st.pop()
                fs.append(g.index)
                for e in g.edges:
                    for h in e.link_faces:
                        if lab[h.index] is None:
                            lab[h.index] = -1
                            st.append(h)
            cx = float(np.mean([bm.faces[k].calc_center_median().x for k in fs]))
            name = "torso" if abs(cx) < 0.15 else "upperArm." + ("L" if cx > 0 else "R")
            for k in fs:
                lab[k] = name
        ISL[ob.name] = lab
        bm.free()
    return ISL[ob.name][i]


def split(ob, parts):
    """One new object per part (copy of ob with the other faces removed)."""
    made = {}
    for name in sorted(set(parts) - {"drop"}):
        me = ob.data.copy()
        bm = bmesh.new()
        bm.from_mesh(me)
        bm.faces.ensure_lookup_table()
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if parts[f.index] != name], context="FACES")
        bm.to_mesh(me)
        bm.free()
        o = bpy.data.objects.new(f"{name}|{ob.name}", me)
        o.matrix_world = ob.matrix_world
        bpy.context.scene.collection.objects.link(o)
        made[name] = o
    return made


def cap(ob, centre):
    """Fill every open boundary loop; the cap faces away from the part centre."""
    me = ob.data
    bm = bmesh.new()
    bm.from_mesh(me)
    n0 = len(bm.faces)
    bmesh.ops.holes_fill(bm, edges=[e for e in bm.edges if e.is_boundary], sides=0)
    bm.faces.ensure_lookup_table()
    # fan from the centre: a long non-planar cap loop (shirt arm hole) triangulated corner to corner folds outside
    # its own outline and leaves a see-through hole
    bmesh.ops.poke(bm, faces=[f for f in bm.faces[n0:] if len(f.verts) > 4])
    bm.faces.ensure_lookup_table()
    new = bm.faces[n0:]
    col = bm.faces.layers.float_color.get("Col")
    for f in new:
        c = f.calc_center_median()
        if f.normal.dot(c - centre) < 0:
            f.normal_flip()
        if col is not None:
            # cap colour = the face it touches (skin cap on skin, cloth cap on cloth)
            nb = [g for e in f.edges for g in e.link_faces if g is not f and g.index < n0]
            if nb:
                f[col] = nb[0][col]
    bm.to_mesh(me)
    bm.free()
    return len(new)


def move_shoulders(rig):
    """upper_arm head (and the shoulder bone's tail) to x = SHOULDER_X on the arm axis; returns {side: pivot}."""
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    piv = {}
    for s, sg in (("L", 1), ("R", -1)):
        ua = rig.data.edit_bones[f"upper_arm.{s}"]
        a, b = ua.head.copy(), ua.tail.copy()
        t = (sg * SHOULDER_X - a.x) / (b.x - a.x)
        p = a + (b - a) * t
        ua.head = p
        rig.data.edit_bones[f"shoulder.{s}"].tail = p
        piv[s] = rig.matrix_world @ p
    bpy.ops.object.mode_set(mode="OBJECT")
    return piv


def dome(ob, pivot, sg):
    """Upper arm vertices inside the joint (sg * x < pivot x): onto a dome around the joint, each at its own distance
    from the arm axis (sleeve wall, skin), so the shell becomes a closed rounded cap."""
    mw, mi = ob.matrix_world, ob.matrix_world.inverted()
    n = 0
    for v in ob.data.vertices:
        w = mw @ v.co
        dx = sg * (w.x - pivot.x)
        if dx >= 0:
            continue
        r = math.hypot(w.y - pivot.y, w.z - pivot.z)   # distance from the arm axis
        d = w - pivot
        if d.length < 1e-6:
            continue
        v.co = mi @ (pivot + d.normalized() * r)
        n += 1
    return n


def torso_shoulder(ob, piv, R):
    """Torso vertices outside the joint and outside the dome come in to 0.95 x the dome radius."""
    mw, mi = ob.matrix_world, ob.matrix_world.inverted()
    n = 0
    for v in ob.data.vertices:
        w = mw @ v.co
        for s, sg in (("L", 1), ("R", -1)):
            p = piv[s]
            if sg * (w.x - p.x) > -0.01:
                d = w - p
                if d.length > 0.95 * R:
                    w = p + d.normalized() * 0.95 * R
                    v.co = mi @ w
                    n += 1
    return n


# Ball joints (user: "lengannya ga nyambung"). A flat cap at the elbow / wrist / knee opens a notch as soon as the
# joint bends. Both parts of the joint end in a half ball around the joint pivot (the child bone's head), each vertex
# at its own distance from the bone axis: a ball turned about its own centre keeps its outline, so the two ends stay
# closed at any angle (same idea as the shoulder dome).
BALL_JOINTS = []   # (child bone, parent part, child part)
for s_ in ("L", "R"):
    BALL_JOINTS += [(f"forearm.{s_}", f"upperArm.{s_}", f"forearm.{s_}"),
                    (f"hand.{s_}", f"forearm.{s_}", f"hand.{s_}"),
                    (f"shin.{s_}", f"thigh.{s_}", f"shin.{s_}")]
BALL_NEAR = 0.07
BALL_LAT = math.radians(50)
BALL_RINGS = tuple(int(x) for x in os.environ.get("CP_BALL_RINGS", "35,70").split(","))   # latitude of the rings above the equator; the pole ring is closed flat


def ball_caps(ob, joints, taken=None):
    """Close each open loop near a joint (pivot P, unit axis a pointing out of this part) with a band to the joint's
    equator, one ring at BALL_LAT and a tip: a half ball. Returns the number of loops closed."""
    mi = ob.matrix_world.inverted()
    m3 = mi.to_3x3()
    loc = [(mi @ jt[0], (m3 @ jt[1]).normalized(), jt[2], jt[3], (m3 @ jt[4]).normalized() if len(jt) > 4 else None)
           for jt in joints]
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    col = bm.faces.layers.float_color.get("Col")
    bnd = [e for e in bm.edges if e.is_boundary]
    adj = {}
    for e in bnd:
        for v in e.verts:
            adj.setdefault(v, []).append(e)
    seen, n, cand = set(), 0, []
    for e0 in bnd:
        if e0 in seen:
            continue
        # walk the loop
        loop, e, v = [], e0, e0.verts[0]
        while True:
            seen.add(e)
            loop.append(v)
            v = e.other_vert(v)
            nxt = [f for f in adj[v] if f not in seen]
            if not nxt:
                break
            e = nxt[0]
        if len(loop) < 3:
            continue
        c = sum((x.co for x in loop), Vector()) / len(loop)
        hit = [i for i, (P, a, near, rmax, _) in enumerate(loc) if (c - P).length < near]
        if os.environ.get("CP_DEBUG"):
            print("LOOP", ob.name, len(loop), [round((c - P).length, 3) for P, *_ in loc])
        if not hit:
            continue
        P, a = loc[hit[0]][:2]
        r_out = sum((x.co - P - a * (x.co - P).dot(a)).length for x in loop) / len(loop)
        cand.append((hit[0], r_out, loop, e0))
    # one ball per joint: the outermost loop (clothes have an inner and an outer shell; the skin sits under them)
    best = {}
    for ji, r_out, loop, e0 in cand:
        if taken is not None and ji in taken:
            continue
        if ji not in best or r_out > best[ji][0]:
            best[ji] = (r_out, loop, e0)
    for ji, (_, loop, e0) in best.items():
        if taken is not None:
            taken.add(ji)
        P, a, _, rmax, X = loc[ji]
        fcol = None
        if col is not None:
            fcol = tuple(e0.link_faces[0][col])
        rad = []
        for x in loop:
            d = x.co - P
            rv = d - a * d.dot(a)
            if rv.length > rmax:   # hip: the ball stays inside the pelvis (thigh top is wider than the socket)
                rv = rv * (rmax / rv.length)
            rad.append(rv)
        rm = sum(r.length for r in rad) / len(rad)
        eq = [bm.verts.new(P + rv) for rv in rad]
        # rings toward the pole get rounder (radius blends to the mean), the pole is a flat n-gon: no spike tip
        # (a single tip over an uneven cuff loop came out as a spike when the knee bent)
        rings = [eq]
        for lat in BALL_RINGS:
            t = lat / 90.0
            cl, sl = math.cos(math.radians(lat)), math.sin(math.radians(lat))
            ring = []
            for rv in rad:
                if X is not None:
                    # hinge (knee, elbow, ankle): each point swings on a circle around the hinge axis, so the cap is a
                    # surface of revolution about that axis and keeps its outline at any bend. A round ball over an
                    # oval cuff (knee 5.7 x 9.6 cm) turned its long side out as a lip when the knee bent.
                    h = rv.dot(X)
                    q = rv - X * h
                    ring.append(bm.verts.new(P + X * h + q * cl + a * q.length * sl))
                else:
                    r = rv.length + (rm - rv.length) * t
                    ring.append(bm.verts.new(P + rv.normalized() * r * cl + a * r * sl))
            rings.append(ring)
        new = []
        k = len(loop)
        for i in range(k):
            j = (i + 1) % k
            quads = [(loop[i], loop[j], eq[j], eq[i])]
            quads += [(r0[i], r0[j], r1[j], r1[i]) for r0, r1 in zip(rings, rings[1:])]
            for q in quads:
                try:
                    new.append(bm.faces.new(q))
                except ValueError:
                    pass
        try:
            new.append(bm.faces.new(rings[-1]))
        except ValueError:
            pass
        for f in new:
            fc = f.calc_center_median()
            out = fc - P - a * min(0.0, (fc - P).dot(a))
            f.normal_update()
            if f.normal.dot(out) < 0:
                f.normal_flip()
            if fcol is not None:
                f[col] = fcol
        n += 1
    bm.to_mesh(ob.data)
    bm.free()
    return n


def neck_sink(ob):
    """Lowest ring of the neck stick moves NECK_SINK down so it reaches inside the torso."""
    me = ob.data
    z = np.array([v.co.z for v in me.vertices])
    lo = z.min()
    for v in me.vertices:
        if v.co.z < lo + 0.015:
            v.co.z -= NECK_SINK
            v.co.x *= 0.95
            v.co.y *= 0.95


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    srcs = [o for o in bpy.data.objects if o.type == "MESH" and o.parent == rig]
    piv = move_shoulders(rig)
    set_chain(rig)
    pieces = {}
    for ob in srcs:
        ob.modifiers.clear()   # rest pose: the mesh as it is
        for name, o in split(ob, face_parts(ob)).items():
            pieces.setdefault(name, []).append(o)
    for ob in srcs:
        bpy.data.objects.remove(ob)
    # dome radius = the sleeve's outer radius at the joint
    sl = next(o for o in pieces["upperArm.L"] if o.name.endswith("Shirt"))
    p = piv["L"]
    rr = [math.hypot(w.y - p.y, w.z - p.z) for w in (sl.matrix_world @ v.co for v in sl.data.vertices)
          if abs(w.x - p.x) < 0.07]
    SLEEVE_R = max(rr)
    print("PIVOT", tuple(round(x, 3) for x in p), "dome r", round(SLEEVE_R, 3))
    stats = {}
    for name, obs in sorted(pieces.items()):
        bone = rig.data.bones[BONE_OF_PART[name]]
        mid = (rig.matrix_world @ ((bone.head_local + bone.tail_local) / 2))
        n_cap = 0
        for o in obs:
            if name == "neck" and o.name.endswith("Character"):
                neck_sink(o)
            if name.startswith("thigh"):
                b = rig.data.bones[BONE_OF_PART[name]]
                P = rig.matrix_world @ b.head_local
                ax = (rig.matrix_world.to_3x3() @ (b.tail_local - b.head_local)).normalized()
                print("HIP_DOME", o.name, dome_axis(o, P, ax))
            if name.startswith("upperArm"):
                print("DOME", o.name, dome(o, piv[name[-1]], 1 if name.endswith("L") else -1))
            jt = []
            for cb, pp, cp in BALL_JOINTS:
                b = rig.data.bones[cb]
                P = rig.matrix_world @ b.head_local
                ax = (rig.matrix_world.to_3x3() @ (b.tail_local - b.head_local)).normalized()
                near, rmax = BALL_NEAR, 1.0
                if name == pp:
                    jt.append((P, ax, near, rmax))
                elif name == cp:
                    jt.append((P, -ax, near, rmax))
            if jt and o.name.split("|")[1] not in ("Eyes", "Hair", "Ears"):
                print("BALL", o.name, ball_caps(o, jt))
            if name == "torso":
                print("TORSO_SHOULDER", o.name, torso_shoulder(o, piv, SLEEVE_R))
            if not o.name.split("|")[1] in ("Eyes", "Hair", "Ears"):
                n_cap += cap(o, mid)
        # one object per part
        bpy.ops.object.select_all(action="DESELECT")
        for o in obs:
            o.select_set(True)
        bpy.context.view_layer.objects.active = obs[0]
        if len(obs) > 1:
            bpy.ops.object.join()
        o = bpy.context.view_layer.objects.active
        o.name = o.data.name = name
        o.vertex_groups.clear()
        mw = o.matrix_world.copy()
        o.parent, o.parent_type, o.parent_bone = rig, "BONE", BONE_OF_PART[name]
        o.matrix_world = mw
        for p in o.data.polygons:
            p.use_smooth = False
        tris = sum(len(p.vertices) - 2 for p in o.data.polygons)
        stats[name] = (tris, n_cap)
    for k, (t, c) in stats.items():
        print(f"PART {k:12s} tris {t:4d} caps {c}")
    print("TOTAL tris", sum(t for t, _ in stats.values()))
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(a.out))


if __name__ == "__main__":
    main()
