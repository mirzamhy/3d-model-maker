# Full character: the F2 low-poly body (Three.js, rigged) with the approved template head (v7 + ear v13).
#   node tools/f2/out/export_f2.mjs 0 output/head-game/f2/f2_male.json      (see tools/f2/export_f2.ts)
#   blender -b --factory-startup -P tools/blender/f2_assemble.py           (F2_JSON, F2_TAG override)
# Steps:
#   1. F2 mesh + armature from the JSON (shared vertices, skin weights, 73 bones). Three.js and our head use the same
#      axes (x = character's left, y up, z forward); everything is moved into head coordinates (eye level y = 0)
#      so the paint and render tools keep working.
#   2. The F2 head (all vertices above its 12-vertex neck ring) and the neck ring itself are deleted, leaving the
#      12-vertex shoulder-top ring open.
#   3. The template head is placed with its 10-vertex neck ring (y -0.172) at the old F2 neck ring height, its neck
#      cap is removed, and a triangle band zips 10 -> 12 to the shoulder-top ring (built on one half, mirrored).
#   4. Head skin weights: Head above the jaw, blending into Neck down the neck rows; ears and brows follow Head.
import bpy
import bmesh
import json
import math
import os
import sys
import numpy as np
from mathutils import Vector

sys.path.insert(0, os.path.dirname(__file__))
import head_game as G  # noqa: E402

ROOT = r"C:\Mirza Personal\model 3d maker"
JSON = os.path.join(ROOT, os.environ.get("F2_JSON", r"output\head-game\f2\f2_male.json"))
HEAD_SRC = os.path.join(ROOT, os.environ.get("F2_HEAD", r"output\head-game\template\head_baseline.blend"))
TAG = os.environ.get("F2_TAG", "f2_male_v1")
OUT = os.path.join(ROOT, r"output\head-game\f2")

F2_NECK_Y = 1.5064  # F2 neck ring height (world, m)
HEAD_NECK_Y = -0.172  # template neck ring height (head coords)
Y_OFF = F2_NECK_Y - HEAD_NECK_Y  # world y = head y + Y_OFF
DZ = -0.0012  # F2 neck ring centre z minus template neck centre z
# head weights by head-coord height: (y, Head share); Neck takes the rest
HEAD_W = [(-0.120, 1.0), (-0.132, 0.85), (-0.153, 0.6), (-0.172, 0.45)]


def to_bl(p):
    return (p[0], -p[2], p[1])


def body_to_head(p):
    """F2 world position -> head coords."""
    return (p[0], p[1] - Y_OFF, p[2] - DZ)


def head_share(y):
    pts = HEAD_W
    if y >= pts[0][0]:
        return 1.0
    for (y0, w0), (y1, w1) in zip(pts, pts[1:]):
        if y1 <= y <= y0:
            return w0 + (w1 - w0) * (y - y0) / (y1 - y0)
    return pts[-1][1]


def load_f2():
    d = json.load(open(JSON))
    P = np.array(d["pos"])
    head = P[:, 1] > F2_NECK_Y + 2e-4
    neck = np.abs(P[:, 1] - F2_NECK_Y) < 2e-4
    assert neck.sum() == 12, neck.sum()
    drop = head | neck
    keep = np.nonzero(~drop)[0]
    remap = {int(o): i for i, o in enumerate(keep)}
    tris = [[remap[v] for v in t] for t in d["tris"] if all(v in remap for v in t)]
    verts = [to_bl(body_to_head(P[o])) for o in keep]
    weights = [d["weights"][o] for o in keep]
    names = [b["name"] for b in d["bones"]]
    return d, verts, tris, weights, names, len(P) - len(keep)


def build_armature(d):
    arm = bpy.data.armatures.new("F2_Rig")
    ob = bpy.data.objects.new("F2_Rig", arm)
    bpy.context.collection.objects.link(ob)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode="EDIT")
    eb = {}
    for b in d["bones"]:
        e = arm.edit_bones.new(b["name"])
        e.head = Vector(to_bl(body_to_head(b["head"])))
        tail = Vector(to_bl(body_to_head(b["tail"])))
        if (tail - e.head).length < 1e-4:
            tail = e.head + Vector((0, 0, 0.02))
        e.tail = tail
        eb[b["name"]] = e
    for b in d["bones"]:
        if b["parent"]:
            eb[b["name"]].parent = eb[b["parent"]]
    bpy.ops.object.mode_set(mode="OBJECT")
    return ob


def remove_neck_cap(head):
    co = np.array([v.co[:] for v in head.data.vertices])
    ring = set(np.nonzero(np.abs(co[:, 2] - HEAD_NECK_Y) < 0.0015)[0].tolist())
    assert len(ring) == 10, len(ring)
    bm = bmesh.new()
    bm.from_mesh(head.data)
    bm.faces.ensure_lookup_table()
    cap = [f for f in bm.faces if {v.index for v in f.verts} <= ring]
    bmesh.ops.delete(bm, geom=cap, context="FACES")
    bm.to_mesh(head.data)
    bm.free()


def zip_band(bm, a_ring, b_ring):
    """Triangles between two loops (a: 10 head verts, b: 12 body verts), zipped by azimuth on the +x half and
    mirrored, so the band is symmetric. Rings are lists of BMVerts."""
    def az(v):
        return math.degrees(math.atan2(v.co.x, v.co.y * -1 - DZ)) % 360  # blender -y = head z

    def half(ring):
        h = sorted([v for v in ring if az(v) <= 180.0 + 1e-6 or az(v) < 1e-6], key=az)
        return h

    def mirror_of(v, ring):
        return min(ring, key=lambda u: (u.co.x + v.co.x) ** 2 + (u.co.y - v.co.y) ** 2 + (u.co.z - v.co.z) ** 2)

    A, B = half(a_ring), half(b_ring)
    tris = []
    i = j = 0
    while i < len(A) - 1 or j < len(B) - 1:
        if j >= len(B) - 1 or (i < len(A) - 1 and az(A[i + 1]) <= az(B[j + 1])):
            tris.append((A[i], A[i + 1], B[j]))
            i += 1
        else:
            tris.append((A[i], B[j + 1], B[j]))
            j += 1
    made = []
    for t in tris:
        made.append(bm.faces.new(t))
        m = tuple(mirror_of(v, a_ring if v in a_ring else b_ring) for v in t)
        if set(m) != set(t):
            made.append(bm.faces.new(m[::-1]))
    return made


def main():
    bpy.ops.wm.open_mainfile(filepath=HEAD_SRC)
    d, verts, tris, weights, names, dropped = load_f2()
    head = bpy.data.objects["Head_Main"]
    remove_neck_cap(head)
    n_head = len(head.data.vertices)
    # body mesh
    me = bpy.data.meshes.new("F2_Body")
    me.from_pydata(verts, [], tris)
    body = bpy.data.objects.new("F2_Body", me)
    bpy.context.collection.objects.link(body)
    for nm in names:
        body.vertex_groups.new(name=nm)
    for i, w in enumerate(weights):
        for bi, val in w:
            body.vertex_groups[names[bi]].add([i], val, "REPLACE")
    # head weights
    for nm in ("Head", "Neck"):
        head.vertex_groups.new(name=nm)
    for v in head.data.vertices:
        hs = head_share(v.co.z)
        head.vertex_groups["Head"].add([v.index], hs, "REPLACE")
        if hs < 1:
            head.vertex_groups["Neck"].add([v.index], 1 - hs, "REPLACE")
    # join body into the head, then zip the seam
    bpy.ops.object.select_all(action="DESELECT")
    head.select_set(True)
    body.select_set(True)
    bpy.context.view_layer.objects.active = head
    bpy.ops.object.join()
    bm = bmesh.new()
    bm.from_mesh(head.data)
    bm.verts.ensure_lookup_table()
    a_ring = [v for v in bm.verts[:n_head] if abs(v.co.z - HEAD_NECK_Y) < 0.0015]
    b_ring = list({v.index: v for e in bm.edges if e.is_boundary and min(v.index for v in e.verts) >= n_head
                   for v in e.verts}.values())
    assert len(a_ring) == 10 and len(b_ring) == 12, (len(a_ring), len(b_ring))
    band = zip_band(bm, a_ring, b_ring)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(head.data)
    bm.free()
    head.name = "Character"
    G.flat(head)
    # rig
    rig = build_armature(d)
    for ob in [o for o in bpy.data.objects if o.type == "MESH"]:
        if ob is not head:  # ears, brows
            g = ob.vertex_groups.get("Head") or ob.vertex_groups.new(name="Head")
            g.add([v.index for v in ob.data.vertices], 1.0, "REPLACE")
        ob.parent = rig
        m = ob.modifiers.new("Rig", "ARMATURE")
        m.object = rig
    st = {"f2_dropped_head_verts": dropped, "band_tris": len(band), "character": G.stats(head),
          "closed": G.closed(head), "symmetry": G.symmetry(head), "bones": len(d["bones"])}
    os.makedirs(OUT, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, f"{TAG}.blend"))
    json.dump(st, open(os.path.join(OUT, f"stats_{TAG}.json"), "w"), indent=1)
    print("F2_STATS", json.dumps(st))


if __name__ == "__main__":
    main()
