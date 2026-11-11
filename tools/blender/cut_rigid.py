"""Rigid parts v2: the dressed rig is split with straight planes through the joint pivots (bisect), not face by face.

Rules (references: PS1/N64 segmented characters, Roblox R15, action figure joints; notes/parts/survivor-cewek.md):
  1. ball joint (shoulder, hip): the child part ends in a half ball around the pivot, tucked into the parent
  2. hinge (elbow, wrist, knee, ankle): both parts end in a half ball around the pivot and overlap
  3. every cut is a plane through the pivot, so the cut line is straight wherever the faces lie
User sketch: pelvis = narrow briefs band with a V to the crotch, thighs start under it; arm cut vertically at the
shoulder edge. Head and neck as in cut_parts.py.
  blender -b <dressed.blend> --factory-startup -P tools/blender/cut_rigid.py -- --out <parts.blend>
"""
import sys, os, argparse, math
import bpy, bmesh
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cut_parts as cp

HIP_CROTCH = float(os.environ.get("CR_HIP_CROTCH", "0.77"))   # briefs V: crotch height at x 0
HIP_SLOPE = float(os.environ.get("CR_HIP_SLOPE", "0.2"))      # rise per m of |x| (0.15 m out = +3 cm)
WAIST_OBJ = {"Shirt": "torso", "Pants": "pelvis"}             # shirt hem overlaps the pants top: no waist cut
HIP_RMAX = 0.09
ANKLE_RMAX = 0.05   # ankle pivot 9 cm above the sole: a wider ball comes out under the boot
OUTER_FIRST = ("Boots", "Pants", "Shirt", "Character")   # one ball per joint, from the outermost layer
BODY_OBJS = ("Character", "Shirt", "Pants", "Boots")


def joints(rig):
    """Pivots and axes (world) per side."""
    mw, b = rig.matrix_world, rig.data.bones
    J = {}
    for s, sg in (("L", 1), ("R", -1)):
        h = lambda n: mw @ b[f"{n}.{s}"].head_local
        t = lambda n: mw @ b[f"{n}.{s}"].tail_local
        arm = (t("hand") - h("upper_arm")).normalized()
        thigh = (t("thigh") - h("thigh")).normalized()
        shin = (t("shin") - h("shin")).normalized()
        J[s] = dict(sg=sg, shoulder=h("upper_arm"), elbow=h("forearm"), wrist=h("hand"), arm=arm,
                    hip=h("thigh"), knee=h("shin"), ankle=h("foot"), thigh=thigh, shin=shin,
                    v_co=Vector((0, 0, HIP_CROTCH)), v_no=Vector((-HIP_SLOPE * sg, 0, 1)).normalized())
    return J


def side_of(c):
    return "L" if c.x > 0 else "R"


def leg_of(c, j):
    """thigh / shin / foot below the briefs V, else None."""
    if c.z > 0.95 or (c - j["v_co"]).dot(j["v_no"]) > 0:
        return None
    if (c - j["ankle"]).dot(j["shin"]) > 0:
        return "foot"
    if (c - j["knee"]).dot(j["shin"]) > 0:
        return "shin"
    return "thigh"


def arm_of(c, j):
    """upperArm / forearm / hand beyond the shoulder plane, else None."""
    if c.z < 1.0 or (c - j["shoulder"]).dot(j["arm"]) <= 0:
        return None
    if (c - j["wrist"]).dot(j["arm"]) > 0:
        return "hand"
    if (c - j["elbow"]).dot(j["arm"]) > 0:
        return "forearm"
    return "upperArm"


def part_of(obname, c, J, code=None):
    s = side_of(c)
    j = J[s]
    a = arm_of(c, j)
    if a:
        return f"{a}.{s}"
    leg = leg_of(c, j)
    if leg:
        return f"{leg}.{s}"
    if obname in WAIST_OBJ:
        return WAIST_OBJ[obname]
    if obname == "Boots":
        return f"foot.{s}"
    if code in cp.NECK_CODES:
        return "neck"
    return "torso" if c.z > 0.862 else "pelvis"


def bisect_all(ob, J):
    """Cut the mesh along every joint plane (only the faces in that joint's zone)."""
    mw = ob.matrix_world
    mi = mw.inverted()
    n3 = mi.to_3x3().inverted().transposed()
    me = ob.data
    bm = bmesh.new()
    bm.from_mesh(me)
    for s, j in J.items():
        sg = j["sg"]
        planes = [
            (j["shoulder"], j["arm"], lambda c: c.z > 1.0 and sg * c.x > 0.12),
            (j["elbow"], j["arm"], lambda c: c.z > 1.0 and sg * c.x > 0.3),
            (j["wrist"], j["arm"], lambda c: c.z > 1.0 and sg * c.x > 0.45),
            (j["v_co"], j["v_no"], lambda c: 0.55 < c.z < 0.95 and sg * c.x >= 0),
            (j["knee"], j["shin"], lambda c: 0.3 < c.z < 0.7 and sg * c.x > 0),
            (j["ankle"], j["shin"], lambda c: c.z < 0.25 and sg * c.x > 0),
        ]
        for co, no, zone in planes:
            fs = [f for f in bm.faces if zone(mw @ f.calc_center_median())]
            if not fs:
                continue
            es = list({e for f in fs for e in f.edges})
            vs = list({v for f in fs for v in f.verts})
            bmesh.ops.bisect_plane(bm, geom=vs + es + fs, plane_co=mi @ co,
                                   plane_no=(n3 @ no).normalized(), dist=1e-5)
    bm.to_mesh(me)
    bm.free()


def body_parts(ob, J):
    me = ob.data
    code = me.attributes["part"].data if "part" in me.attributes else None
    out = []
    for p in me.polygons:
        c = ob.matrix_world @ p.center
        k = code[p.index].value if code is not None else None
        out.append(part_of(ob.name, c, J, k))
    return out


def joint_caps(name, J):
    """(pivot, axis out of this part, near, rmax) for the half balls at this part's joint ends."""
    if "." not in name:
        return []
    kind, s = name.split(".")
    j = J[s]
    a, sh = j["arm"], j["shin"]
    up = -j["thigh"]
    return {
        "upperArm": [(j["shoulder"], -a, 0.08, 1.0), (j["elbow"], a, 0.07, 1.0)],
        "forearm": [(j["elbow"], -a, 0.07, 1.0), (j["wrist"], a, 0.07, 1.0)],
        "hand": [(j["wrist"], -a, 0.07, 1.0)],
        "thigh": [(j["hip"], up, 0.12, HIP_RMAX), (j["knee"], sh, 0.08, 1.0)],
        "shin": [(j["knee"], -sh, 0.08, 1.0), (j["ankle"], sh, 0.08, ANKLE_RMAX)],
        "foot": [(j["ankle"], -sh, 0.08, ANKLE_RMAX)],
    }.get(kind, [])


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    srcs = [o for o in bpy.data.objects if o.type == "MESH" and o.parent == rig]
    cp.move_shoulders(rig)
    J = joints(rig)
    pieces = {}
    for ob in srcs:
        ob.modifiers.clear()
        if ob.name in cp.HEAD_OBJS:
            parts = cp.face_parts(ob)
        else:
            bisect_all(ob, J)
            parts = body_parts(ob, J)
        for name, o in cp.split(ob, parts).items():
            pieces.setdefault(name, []).append(o)
    for ob in srcs:
        bpy.data.objects.remove(ob)
    stats = {}
    for name, obs in sorted(pieces.items()):
        bone = rig.data.bones[cp.BONE_OF_PART[name]]
        mid = rig.matrix_world @ ((bone.head_local + bone.tail_local) / 2)
        jc = joint_caps(name, J)
        n_ball = n_cap = 0
        taken = set()
        obs.sort(key=lambda o: OUTER_FIRST.index(o.name.split("|")[1]) if o.name.split("|")[1] in OUTER_FIRST else 9)
        for o in obs:
            src = o.name.split("|")[1]
            if name == "neck" and src == "Character":
                cp.neck_sink(o)
            if jc and src in BODY_OBJS:
                n_ball += cp.ball_caps(o, jc, taken)
            if src not in ("Eyes", "Hair", "Ears"):
                n_cap += cp.cap(o, mid)
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
        o.parent, o.parent_type, o.parent_bone = rig, "BONE", cp.BONE_OF_PART[name]
        o.matrix_world = mw
        for p in o.data.polygons:
            p.use_smooth = False
        stats[name] = (sum(len(p.vertices) - 2 for p in o.data.polygons), n_ball, n_cap)
    for k, (t, b, c) in stats.items():
        print(f"PART {k:12s} tris {t:4d} balls {b} caps {c}")
    print("TOTAL tris", sum(t for t, _, _ in stats.values()))
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(a.out))


if __name__ == "__main__":
    main()
