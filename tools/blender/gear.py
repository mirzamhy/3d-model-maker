"""Survivor gear on the rigid parts (cut_rigid.py output): each piece is a few big planes joined into the part it
rides on, so it moves with that bone.

References (web search "post apocalyptic female survivor"): backpack + shoulder straps, bandana at the neck, belt with
pouches, knee pads, fingerless gloves, thigh pouch. Shells are built from surface points found by ray casts from
outside, pushed out by an offset, given a wall thickness and closed (grid_shell).
  blender -b <parts.blend> --factory-startup -P tools/blender/gear.py -- --out <geared.blend> [--set scav]
"""
import sys, os, math, argparse
import bpy, bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree

GEAR = {
    "scav": dict(pack=(0.50, 0.42, 0.28), pack_dark=(0.36, 0.30, 0.20), strap=(0.20, 0.18, 0.15),
                 bandana=(0.55, 0.12, 0.10), belt=(0.14, 0.12, 0.10), buckle=(0.55, 0.53, 0.48),
                 pouch=(0.30, 0.31, 0.22), pad=(0.13, 0.13, 0.14), glove=(0.12, 0.11, 0.11)),
}


def lin(c):
    return tuple(ch ** 2.2 for ch in c) + (1.0,)


def bvh(obs):
    """One BVH over several objects (world coords)."""
    bm = bmesh.new()
    for o in obs:
        t = bmesh.new()
        t.from_mesh(o.data)
        t.transform(o.matrix_world)
        me = bpy.data.meshes.new("_t")
        t.to_mesh(me)
        t.free()
        bm.from_mesh(me)
        bpy.data.meshes.remove(me)
    tree = BVHTree.FromBMesh(bm)
    bm.free()
    return tree


def hit_in(tree, target, d, far=0.6):
    """Outermost surface point on the line through target along d (cast from outside toward target)."""
    d = d.normalized()
    loc, _, _, _ = tree.ray_cast(target + d * far, -d, far * 2)
    return loc


def grid_shell(bm, P, N, off, t, closed=False):
    """Closed slab over a grid of surface points P[row][col] with outward normals N: inner face at off, outer at
    off + t. closed: the columns wrap (ring)."""
    rows, cols = len(P), len(P[0])
    vin = [[bm.verts.new(P[r][c] + N[r][c] * off) for c in range(cols)] for r in range(rows)]
    vout = [[bm.verts.new(P[r][c] + N[r][c] * (off + t)) for c in range(cols)] for r in range(rows)]
    cr = range(cols) if closed else range(cols - 1)
    fs = []
    for r in range(rows - 1):
        for c in cr:
            c2 = (c + 1) % cols
            fs.append(bm.faces.new([vout[r][c], vout[r][c2], vout[r + 1][c2], vout[r + 1][c]]))
            fs.append(bm.faces.new([vin[r][c], vin[r + 1][c], vin[r + 1][c2], vin[r][c2]]))
    # walls: top and bottom rows; side columns when open
    for r in (0, rows - 1):
        for c in cr:
            c2 = (c + 1) % cols
            fs.append(bm.faces.new([vin[r][c], vin[r][c2], vout[r][c2], vout[r][c]]))
    if not closed:
        for c in (0, cols - 1):
            for r in range(rows - 1):
                fs.append(bm.faces.new([vin[r][c], vout[r][c], vout[r + 1][c], vin[r + 1][c]]))
    return fs


def box(bm, lo, hi, taper=0.0):
    """Axis box lo..hi (world); taper shrinks the top face in x/y by that fraction (rounder pack top)."""
    lo, hi = Vector(lo), Vector(hi)
    c = (lo + hi) / 2
    vs = []
    for z in (lo.z, hi.z):
        k = 1 - taper if z == hi.z else 1.0
        for x, y in ((lo.x, lo.y), (hi.x, lo.y), (hi.x, hi.y), (lo.x, hi.y)):
            vs.append(bm.verts.new((c.x + (x - c.x) * k, c.y + (y - c.y) * k, z)))
    idx = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    return [bm.faces.new([vs[i] for i in f]) for f in idx]


class Piece:
    """Faces with colours, built into one bmesh, later joined into a part object."""

    def __init__(self):
        self.bm = bmesh.new()
        self.cols = []

    def add(self, faces, colour):
        self.cols += [lin(colour)] * len(faces)

    def join_into(self, part):
        bm = self.bm
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        # faces keep creation order through to_mesh (no ops that reorder them)
        me = bpy.data.meshes.new("gear")
        bm.to_mesh(me)
        bm.free()
        a = me.attributes.new("Col", "FLOAT_COLOR", "FACE")
        for i, d in enumerate(a.data):
            d.color = self.cols[i]
        for m in part.data.materials:
            me.materials.append(m)
        ob = bpy.data.objects.new("gear", me)
        bpy.context.scene.collection.objects.link(ob)
        bpy.ops.object.select_all(action="DESELECT")
        ob.select_set(True)
        part.select_set(True)
        bpy.context.view_layer.objects.active = part
        bpy.ops.object.join()
        for p in part.data.polygons:
            p.use_smooth = False
        return len(me.polygons) if me.name in bpy.data.meshes else None


def ring(tree, z, centre, n, start=0.0):
    """Surface points around a horizontal ring (x, y plane) at height z; normals radial."""
    P, N = [], []
    for k in range(n):
        an = start + 2 * math.pi * k / n
        d = Vector((math.sin(an), -math.cos(an), 0))   # k 0 = front (-y)
        p = hit_in(tree, Vector((centre.x, centre.y, z)), d)
        P.append(p if p else Vector((centre.x, centre.y, z)) + d * 0.08)
        N.append(d)
    return P, N


def backpack(pc, tree, C):
    # back surface (+y) over the pack area, centre column
    ys = [hit_in(tree, Vector((x, 0.0, z)), Vector((0, 1, 0))) for x in (-0.08, 0, 0.08) for z in (1.05, 1.15, 1.25)]
    back = max(p.y for p in ys if p)
    y0 = back - 0.012
    pc.add(box(pc.bm, (-0.125, y0, 1.03), (0.125, y0 + 0.12, 1.31), taper=0.12), C["pack"])
    pc.add(box(pc.bm, (-0.115, y0 + 0.04, 1.27), (0.115, y0 + 0.125, 1.335), taper=0.1), C["pack_dark"])  # top flap
    pc.add(box(pc.bm, (-0.09, y0 + 0.11, 1.06), (0.09, y0 + 0.155, 1.18)), C["pack_dark"])                 # pocket
    for x0, x1 in ((-0.155, -0.125), (0.125, 0.155)):                                                       # side pockets
        pc.add(box(pc.bm, (x0, y0 + 0.03, 1.05), (x1, y0 + 0.09, 1.17)), C["pack_dark"])
    return back


def straps(pc, tree, C):
    """Shoulder straps: from the pack top over the shoulder down the chest (rays in the y, z plane)."""
    centre_z, centre_y = 1.20, 0.02
    for sx in (-1, 1):
        P, N = [], []
        for deg in range(-20, 236, 16):
            a = math.radians(deg)
            d = Vector((0, math.cos(a), math.sin(a)))   # 0 = back, 90 = up, 180 = front
            row, nrow = [], []
            for dx in (-0.019, 0.019):
                x = sx * 0.088 + dx
                p = hit_in(tree, Vector((x, centre_y, centre_z)), d)
                row.append(p if p else Vector((x, centre_y, centre_z)) + d * 0.1)
                nrow.append(d)
            P.append(row)
            N.append(nrow)
        pc.add(grid_shell(pc.bm, P, N, 0.004, 0.008), C["strap"])


def bandana(pc, tree, C):
    P0, N0 = ring(tree, 1.368, Vector((0, 0.035, 0)), 10)
    P1, N1 = ring(tree, 1.402, Vector((0, 0.035, 0)), 10)
    pc.add(grid_shell(pc.bm, [P0, P1], [N0, N1], 0.008, 0.008, closed=True), C["bandana"])
    # knot triangle on the chest, under the ring front
    F = Vector((0, -1, 0))
    top = [hit_in(tree, Vector((x, 0.0, 1.372)), F) for x in (-0.05, 0.0, 0.05)]
    bot = [hit_in(tree, Vector((x, 0.0, 1.30)), F) for x in (-0.012, 0.0, 0.012)]
    pc.add(grid_shell(pc.bm, [top, bot], [[F] * 3, [F] * 3], 0.010, 0.007), C["bandana"])


def belt(pc, tree, C):
    P0, N0 = ring(tree, 0.885, Vector((0, 0.02, 0)), 14)
    P1, N1 = ring(tree, 0.922, Vector((0, 0.02, 0)), 14)
    pc.add(grid_shell(pc.bm, [P0, P1], [N0, N1], 0.006, 0.007, closed=True), C["belt"])
    f = hit_in(tree, Vector((0, 0, 0.903)), Vector((0, -1, 0)))
    pc.add(box(pc.bm, (-0.025, f.y - 0.022, 0.880), (0.025, f.y - 0.010, 0.927)), C["buckle"])
    for sx in (-1, 1):   # pouches at the hip, slightly back
        s = hit_in(tree, Vector((0, 0.03, 0.90)), Vector((sx, 0.35, 0)))
        x0 = s.x + sx * 0.008
        lo = (min(x0, x0 + sx * 0.045), s.y - 0.04, 0.845)
        hi = (max(x0, x0 + sx * 0.045), s.y + 0.04, 0.93)
        pc.add(box(pc.bm, lo, hi), C["pouch"])


def knee_pad(pc, tree, C, sx, knee):
    F = Vector((0, -1, 0))
    rows = []
    for z in (knee.z - 0.06, knee.z - 0.02, knee.z + 0.02, knee.z + 0.055):
        rows.append([hit_in(tree, Vector((knee.x + dx, knee.y, z)), F + Vector((dx * 6, 0, 0)))
                     for dx in (-0.045, -0.015, 0.015, 0.045)])
    for r, row in enumerate(rows):   # missing hits (above the shin top): copy the row below, moved up
        for c, p in enumerate(row):
            if p is None:
                row[c] = rows[r - 1][c] + Vector((0, 0, 0.035))
    N = [[(F + Vector((dx * 6, 0, 0))).normalized() for dx in (-0.045, -0.015, 0.015, 0.045)]] * 4
    pc.add(grid_shell(pc.bm, rows, N, 0.006, 0.012), C["pad"])
    # strap ring under the pad
    P, Nn = ring(tree, knee.z - 0.07, Vector((knee.x, knee.y, 0)), 8)
    Q, Nq = ring(tree, knee.z - 0.05, Vector((knee.x, knee.y, 0)), 8)
    pc.add(grid_shell(pc.bm, [P, Q], [Nn, Nq], 0.003, 0.005, closed=True), C["strap"])


def thigh_pouch(pc, tree, C, sx, z):
    s = hit_in(tree, Vector((sx * 0.11, 0.015, z)), Vector((sx, 0, 0)))
    x0 = s.x + sx * 0.004
    pc.add(box(pc.bm, (min(x0, x0 + sx * 0.04), s.y - 0.045, z - 0.05), (max(x0, x0 + sx * 0.04), s.y + 0.045, z + 0.05)),
           C["pouch"])
    for zz in (z + 0.035, z - 0.035):
        P, N = ring(tree, zz - 0.009, Vector((sx * 0.11, 0.015, 0)), 8)
        Q, Nq = ring(tree, zz + 0.009, Vector((sx * 0.11, 0.015, 0)), 8)
        pc.add(grid_shell(pc.bm, [P, Q], [N, Nq], 0.003, 0.005, closed=True), C["strap"])


def gloves(part, C, wrist, axis):
    """Fingerless glove: hand faces from the wrist to the knuckles (along the arm axis) get the glove colour."""
    me = part.data
    a = me.attributes["Col"]
    n = 0
    for p in me.polygons:
        c = part.matrix_world @ p.center
        if (c - wrist).dot(axis) < 0.075:
            a.data[p.index].color = lin(C["glove"])
            n += 1
    return n


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--set", default="scav")
    a = ap.parse_args(argv)
    C = GEAR[a.set]
    O = bpy.data.objects
    rig = next(o for o in O if o.type == "ARMATURE")
    bones, mw = rig.data.bones, rig.matrix_world
    before = {o.name: len(o.data.polygons) for o in O if o.type == "MESH"}

    pc = Piece()
    t_torso = bvh([O["torso"]])
    backpack(pc, t_torso, C)
    straps(pc, t_torso, C)
    bandana(pc, bvh([O["torso"], O["neck"]]), C)
    pc.join_into(O["torso"])

    pc = Piece()
    belt(pc, bvh([O["pelvis"]]), C)
    pc.join_into(O["pelvis"])

    for s, sx in (("L", 1), ("R", -1)):
        knee = mw @ bones[f"shin.{s}"].head_local
        pc = Piece()
        knee_pad(pc, bvh([O[f"shin.{s}"]]), C, sx, knee)
        pc.join_into(O[f"shin.{s}"])
        wrist = mw @ bones[f"hand.{s}"].head_local
        axis = (mw @ bones[f"hand.{s}"].tail_local - wrist).normalized()
        gloves(O[f"hand.{s}"], C, wrist, axis)
    pc = Piece()
    thigh_pouch(pc, bvh([O["thigh.R"]]), C, -1, 0.72)
    pc.join_into(O["thigh.R"])

    tot = 0
    for o in O:
        if o.type == "MESH":
            t = sum(len(p.vertices) - 2 for p in o.data.polygons)
            tot += t
            if len(o.data.polygons) != before.get(o.name):
                print(f"GEAR {o.name:10s} +{len(o.data.polygons) - before[o.name]} faces, part tris {t}")
    print("TOTAL tris", tot)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(a.out))


if __name__ == "__main__":
    main()
