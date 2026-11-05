# Low-poly hair for the survivor (reference: notes/attachments/ref/survivor_sheet.webp): a thick shell over the scalp
# with one angular clump per face, the way game artists block hair (Rozi 3D part 3: duplicate head faces, add
# thickness) plus poked tips that follow the combing direction.
#   blender -b --factory-startup -P tools/blender/hair_lowpoly.py      (HAIR_SRC, HAIR_TAG override)
# Steps:
#   1. a COARSE dome (12 sectors x 4 rows + pole), not the dense head faces: one face = one big clump (big planes,
#      not a pine cone). Each grid point is ray cast from the head centre onto the skin. The bottom row follows the
#      hairline: high at the forehead, above the ears at the sides, down to the nape at the back.
#   2. shell: outer = skin point moved out by a thickness that grows toward the crown and the back; inner = skin
#      point 3 mm inside; rim quads at the hairline close it (one closed mesh).
#   3. clumps: every outer face is poked; the new centre vertex goes out + along the combing flow (top and back:
#      backward and down, fringe: forward, down and across to the character's right, sides: down). Tips of the
#      fringe stop above the eyebrows.
# Hair is asymmetric on purpose (custom property qa_asym: the QA symmetry gate skips it).
# Blender axes: x = character's left, -y = forward, z up.
import bpy
import bmesh
import json
import math
import os
import random
import sys

import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, os.path.dirname(__file__))
import head_game as G  # noqa: E402

ROOT = r"C:\Mirza Personal\model 3d maker"
SRC = os.path.join(ROOT, os.environ.get("HAIR_SRC", "output/ref/survivor/head_ref_body_v7base_color.blend"))
TAG = os.environ.get("HAIR_TAG", "survivor_v7")
OUT = os.path.join(ROOT, "output", "ref", "survivor")
SEED = int(os.environ.get("HAIR_SEED", "7"))
COLOUR = (0.27, 0.18, 0.11, 1.0)
NECK_Z = 1.45  # head vertices above this (world m)
# hairline: forward position f (-1 back .. +1 front) -> height share h (0 chin .. 1 crown)
LINE_F = [-1.0, -0.45, -0.15, 0.2, 0.5, 1.0]
LINE_H = [0.2, 0.24, 0.55, 0.62, 0.74, 0.78]
# shell thickness (m) by region, clump length (m)
THICK_TOP, THICK_BACK, THICK_SIDE = 0.016, 0.016, 0.008  # base shell under the clumps
CLUMP_TOP, CLUMP_BACK, CLUMP_SIDE, CLUMP_FRINGE = 0.075, 0.08, 0.05, 0.095  # tip reach along the flow
WEDGE_THICK = 0.018  # clump height at its root ridge
SECTORS = int(os.environ.get("HAIR_SECTORS", "10"))  # dome columns around the head
ROWS = [0.0, 0.28, 0.55, 0.8]  # dome rows: share of the way from the hairline to the top


def smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def main():
    rnd = random.Random(SEED)
    bpy.ops.wm.open_mainfile(filepath=SRC)
    ch = bpy.data.objects["Character"]
    src = bmesh.new()
    src.from_mesh(ch.data)
    src.transform(ch.matrix_world)
    src.normal_update()
    pin = src.verts.layers.int.get("pin")
    head_v = [v for v in src.verts if v[pin] and v.co.z > NECK_Z]
    co = np.array([v.co[:] for v in head_v])
    zmin, zmax = co[:, 2].min(), co[:, 2].max()
    fw = -co[:, 1]
    fmin, fmax = fw.min(), fw.max()
    fc, fh = (fmin + fmax) / 2, (fmax - fmin) / 2
    brow_z = min(min((o.matrix_world @ v.co).z for v in o.data.vertices)
                 for o in bpy.data.objects if o.name.startswith("Eyebrow")) if any(
        o.name.startswith("Eyebrow") for o in bpy.data.objects) else zmin + 0.6 * (zmax - zmin)

    def hf(p):
        return (p.z - zmin) / (zmax - zmin), (-p.y - fc) / fh

    def above_line(p):
        h, f = hf(p)
        return h > float(np.interp(f, LINE_F, LINE_H))

    # coarse dome over the head: SECTORS around x ROWS from the hairline up + a pole vertex. Each grid point is
    # cast from the head centre onto the skin (BVH of the head faces), so the shell hugs the real skull.
    head_faces = [f for f in src.faces if all(v[pin] and v.co.z > NECK_Z for v in f.verts)]
    bvh = BVHTree.FromPolygons([v.co.copy() for v in src.verts], [[v.index for v in f.verts] for f in head_faces])
    centre = Vector((0.0, -fc + 0.012, zmin + 0.58 * (zmax - zmin)))  # a bit behind the middle, ear height

    def skin(a, e):
        d = Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))
        hit = bvh.ray_cast(centre, d, 0.5)
        return (hit[0], d) if hit[0] is not None else (centre + d * 0.09, d)

    def thickness_p(p):
        h, f = hf(p)
        side = abs(p.x) / max(1e-6, abs(co[:, 0]).max())
        t = THICK_SIDE + (THICK_TOP - THICK_SIDE) * smooth((h - 0.55) / 0.4)
        t = max(t, THICK_SIDE + (THICK_BACK - THICK_SIDE) * smooth((-f - 0.2) / 0.5))
        return t * (1 - 0.25 * smooth((side - 0.8) / 0.2) * smooth((0.75 - h) / 0.2))

    bm = bmesh.new()
    grid_out, grid_in = [], []
    for s_ in range(SECTORS):
        a = 2 * math.pi * s_ / SECTORS
        e0 = next((math.radians(e) for e in range(-70, 85) if above_line(skin(a, math.radians(e))[0])),
                  math.radians(60))
        col_o, col_i = [], []
        for t in ROWS:
            e = e0 + (math.radians(84) - e0) * t
            p, d = skin(a, e)
            col_o.append(bm.verts.new(p + d * thickness_p(p)))
            col_i.append(bm.verts.new(p - d * 0.003))
        grid_out.append(col_o)
        grid_in.append(col_i)
    top = skin(0, math.radians(89))[0]
    pole_o = bm.verts.new(top + Vector((0, 0, THICK_TOP)))
    pole_i = bm.verts.new(top - Vector((0, 0, 0.003)))
    out_faces = []
    nr = len(ROWS)
    for s_ in range(SECTORS):
        s2 = (s_ + 1) % SECTORS
        for r in range(nr - 1):
            out_faces.append(bm.faces.new([grid_out[s_][r], grid_out[s2][r], grid_out[s2][r + 1], grid_out[s_][r + 1]]))
            bm.faces.new([grid_in[s_][r + 1], grid_in[s2][r + 1], grid_in[s2][r], grid_in[s_][r]])
        out_faces.append(bm.faces.new([grid_out[s_][nr - 1], grid_out[s2][nr - 1], pole_o]))
        bm.faces.new([pole_i, grid_in[s2][nr - 1], grid_in[s_][nr - 1]])
        bm.faces.new([grid_out[s2][0], grid_out[s_][0], grid_in[s_][0], grid_in[s2][0]])  # rim at the hairline
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.normal_update()
    scalp = out_faces
    # clumps: one closed WEDGE per dome face, lying along the combing flow like a roof tile. Root (2 corners just
    # under the shell + a ridge point lifted off it) at the upstream side of the face, tip far downstream, so each
    # clump covers the root of the next row: layered, swept hair instead of spikes pointing out.
    fwd, down, right = Vector((0, -1, 0)), Vector((0, 0, -1)), Vector((-1, 0, 0))
    n_clump = 0
    for face in out_faces:
        n = face.normal.copy()
        c = face.calc_center_median()
        size = max(e.calc_length() for e in face.edges)
        h, f = hf(c)
        fringe = f > 0.45 and h < 0.9
        if fringe:
            flow, L, lift = fwd * 0.3 + down * 0.55 + right * 1.0, CLUMP_FRINGE, 0.004  # one sweep across
        elif f < -0.2:
            flow, L, lift = -fwd * 0.45 + down * 0.9, CLUMP_BACK, 0.006  # down over the nape: hides the shell lip
        elif h < 0.72:
            flow, L, lift = down * 0.75 - fwd * 0.55, CLUMP_SIDE, 0.004
        else:  # top: swept back, tips flicked up (the spiky crown of the reference)
            flow, L, lift = -fwd * 0.8 + right * 0.25 * math.copysign(1, -c.x), CLUMP_TOP, 0.012
        u = flow - n * flow.dot(n)
        u.normalize()
        sd = n.cross(u)
        k = rnd.uniform(0.75, 1.1)
        w = 0.62 * size * rnd.uniform(0.9, 1.05)  # wider than the face: neighbours overlap sideways
        c0 = c - u * 0.45 * size
        A = bm.verts.new(c0 + sd * w - n * 0.004)
        B = bm.verts.new(c0 - sd * w - n * 0.004)
        R = bm.verts.new(c0 + n * WEDGE_THICK * k + u * 0.2 * size)
        T = bm.verts.new(c + u * L * k + n * lift * k)
        if fringe:
            T.co.z = max(T.co.z, brow_z + 0.01)
        for q in ((A, R, T), (R, B, T), (B, A, T), (A, B, R)):
            bm.faces.new(q)
        n_clump += 1
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.normal_update()
    me = bpy.data.meshes.new("Hair")
    bm.to_mesh(me)
    bm.free()
    src.free()
    hair = bpy.data.objects.new("Hair", me)
    bpy.context.scene.collection.objects.link(hair)
    hair["qa_asym"] = True
    hair["qa_tris_ok"] = True  # clumps are triangles by design: out of the quad share
    hair["qa_parts"] = n_clump + 1  # shell + one closed wedge per clump
    col = me.attributes.new("Col", "FLOAT_COLOR", "FACE")
    for i in range(len(me.polygons)):
        k = 0.93 + 0.14 * rnd.random()  # small per-clump shade so the planes read
        col.data[i].color = (COLOUR[0] * k, COLOUR[1] * k, COLOUR[2] * k, 1)
    mat = bpy.data.materials.get("Hair") or bpy.data.materials.new("Hair")
    mat.diffuse_color = COLOUR
    me.materials.append(mat)
    G.flat(hair)
    st = {"hair": G.stats(hair), "closed": G.closed(hair), "scalp_faces": len(scalp), "clumps": n_clump}
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, f"{TAG}.blend"))
    print("HAIR_STATS", json.dumps(st))


if __name__ == "__main__":
    main()
