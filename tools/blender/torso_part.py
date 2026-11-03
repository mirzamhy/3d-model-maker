# Torso part: neck base, shoulders, chest, waist, hips, stitched to the approved head at its 10-vertex neck ring.
#   blender -b --factory-startup -P tools/blender/torso_part.py        (TORSO_SRC, TORSO_TAG override)
# Part rules (notes/konsep-part-modular.md): skin parts are stitched into one closed mesh; the neck connector is the
# head's 10-vertex ring (NECK_COLS), so the head is not changed. Head coordinates: metres, x left, y up (eye level
# = 0), z forward. Cross-sections come from src/zombie/lowbody/refBody.json (male, stature 1.729 m): its chin
# height matches our chin, so world y = head y + 1.625 and the sizes are used 1:1.
#
# Topology: 16-vertex rings (all neck columns plus 70, 110 and 150 deg). The neck -> first ring transition makes
# 5-sided faces where the extra columns start. Connectors that the next parts will open:
#   arm  = the 4 quads around the side vertex of ring 2 (8-vertex boundary loop, like body F2), tagged 5
#   legs = the bottom cap of the last ring, tagged 6
import bpy
import bmesh
import json
import math
import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import head_game as G  # noqa: E402

ROOT = r"C:\Mirza Personal\model 3d maker"
SRC = os.path.join(ROOT, os.environ.get("TORSO_SRC", r"output\head-game\template\head_baseline.blend"))
TAG = os.environ.get("TORSO_TAG", "bust_v1")
OUT = os.path.join(ROOT, r"output\head-game\template")

NECK_Y = -0.172  # head neck ring height (head_template.NECK_ROWS[-1])
Z0 = -0.010  # body axis (neck centre) in head z
TORSO_COLS = [0, 22, 48, 70, 90, 110, 120, 150, 180]  # half ring, degrees from the front toward +x
# rings: name, y front / side / back (head y, m), front, back, half (m), superellipse exponent (2 = ellipse)
# values from refBody.json male rows (frac -> y = frac * 1.729 - 1.625); the shoulder rows use a narrower half
# than the reference, which includes the arm.
TORSO_RINGS = [
    ("trap", -0.183, -0.189, -0.177, 0.050, 0.070, 0.092, 2.2),  # trapezius rises up the neck sides
    ("shoulder", -0.204, -0.224, -0.196, 0.072, 0.094, 0.186, 3.0),  # shoulder line, slopes down to the tips
    ("armpit_top", -0.262, -0.262, -0.255, 0.102, 0.120, 0.182, 2.6),  # chest top, shoulder joint (arm connector)
    ("armpit", -0.330, -0.330, -0.330, 0.126, 0.136, 0.168, 2.2),  # pecs and scapula
    ("chest_low", -0.420, -0.420, -0.420, 0.124, 0.122, 0.155, 2.3),  # ribcage bottom
    ("waist", -0.540, -0.540, -0.540, 0.110, 0.098, 0.140, 2.3),  # narrowest: V taper
    ("belly", -0.650, -0.650, -0.650, 0.116, 0.112, 0.152, 2.3),
    ("hips", -0.760, -0.760, -0.760, 0.112, 0.126, 0.166, 2.4),  # glutes at the back
]
ARM_RING, ARM_COL = 3, 90  # ring index (0 = neck ring) and column of the arm connector centre


def to_bl(p):
    return np.stack([p[:, 0], -p[:, 2], p[:, 1]], axis=1)


def to_head(co):
    return np.stack([co[:, 0], co[:, 2], -co[:, 1]], axis=1)


def full(cols):
    return sorted({c % 360 for c in cols} | {(-c) % 360 for c in cols})


def ring_point(spec, t):
    _, yf, ys, yb, front, back, half, n = spec
    a = math.radians(t)
    s, c = math.sin(a), math.cos(a)
    e = 2.0 / n
    x = half * math.copysign(abs(s) ** e, s)
    z = (front if c >= 0 else back) * math.copysign(abs(c) ** e, c) + Z0
    y = ys + (yf - ys) * max(c, 0) ** 2 + (yb - ys) * max(-c, 0) ** 2
    return (x, y, z)


def neck_ring(head):
    """The head's neck ring vertices (head coords) keyed by azimuth, and the cap face to remove."""
    co = to_head(np.array([v.co[:] for v in head.data.vertices]))
    idx = np.nonzero(np.abs(co[:, 1] - NECK_Y) < 0.0015)[0]
    ang = {}
    for i in idx:
        t = round(math.degrees(math.atan2(co[i, 0], co[i, 2] - Z0))) % 360
        ang[t] = int(i)
    # the cap is split in two halves by the mirror weld: take every face that lies wholly on the ring
    cap = [p.index for p in head.data.polygons if set(p.vertices) <= set(idx.tolist())]
    return ang, co, cap


def snap_cols(ang):
    """Head neck azimuths are not exact; map each to the nearest design column."""
    want = full([0, 22, 48, 90, 120, 180])
    out = {}
    for t, i in ang.items():
        w = min(want, key=lambda k: min(abs(k - t), 360 - abs(k - t)))
        out[w] = i
    assert len(out) == 10, out
    return out


def build_torso(head):
    ang, hco, cap = neck_ring(head)
    neck = snap_cols(ang)
    thetas = full(TORSO_COLS)
    verts, vid, row_cols = [], {}, []
    # row 0: copies of the head neck ring (merged into the head after the join)
    row_cols.append(sorted(neck))
    for t in row_cols[0]:
        vid[(0, t)] = len(verts)
        verts.append(tuple(hco[neck[t]]))
    for r, spec in enumerate(TORSO_RINGS, start=1):
        row_cols.append(thetas)
        for t in thetas:
            vid[(r, t)] = len(verts)
            verts.append(ring_point(spec, t))
    order = {t: i for i, t in enumerate(thetas)}
    faces, zone = [], []
    arm_quads = set()
    for side in (ARM_COL, 360 - ARM_COL):
        i = order[side]
        for dr in (-1, 0):
            for di in (-1, 0):
                arm_quads.add((ARM_RING + dr, thetas[(i + di) % len(thetas)]))
    for r in range(len(row_cols) - 1):
        top_cols, bot_cols = row_cols[r], row_cols[r + 1]
        small = top_cols if len(top_cols) <= len(bot_cols) else bot_cols
        for a, b in zip(small, small[1:] + small[:1]):
            ia, ib = order[a], order[b]
            span = [thetas[(ia + k) % len(thetas)] for k in range(((ib - ia) % len(thetas)) + 1)]
            top = [vid[(r, t)] for t in span if t in top_cols]
            bot = [vid[(r + 1, t)] for t in reversed(span) if t in bot_cols]
            faces.append(tuple(top + bot))
            zone.append(5 if (r, a) in arm_quads and len(top) == 2 else (1 if r == 0 else 2))
    last = len(row_cols) - 1
    faces.append(tuple(vid[(last, t)] for t in reversed(thetas)))
    zone.append(6)
    me = bpy.data.meshes.new("Torso")
    me.from_pydata([tuple(p) for p in to_bl(np.array(verts))], [], faces)
    za = me.attributes.new("body_zone", "INT", "FACE")
    for i, z in enumerate(zone):
        za.data[i].value = z
    ob = bpy.data.objects.new("Torso", me)
    bpy.context.collection.objects.link(ob)
    return ob, cap, [neck[t] for t in row_cols[0]]


def stitch(head, torso, cap):
    """Remove the head's neck cap, join the torso and weld the 10 seam vertex pairs."""
    bm = bmesh.new()
    bm.from_mesh(head.data)
    bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[bm.faces[i] for i in cap], context="FACES")  # also drops the loose edge between the two cap halves
    bm.to_mesh(head.data)
    bm.free()
    bpy.ops.object.select_all(action="DESELECT")
    head.select_set(True)
    torso.select_set(True)
    bpy.context.view_layer.objects.active = head
    bpy.ops.object.join()
    bm = bmesh.new()
    bm.from_mesh(head.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(head.data)
    bm.free()


def main():
    bpy.ops.wm.open_mainfile(filepath=SRC)
    head = bpy.data.objects["Head_Main"]
    before = len(head.data.vertices)
    torso, cap, _ = build_torso(head)
    torso_tris = G.stats(torso)["triangles"]
    stitch(head, torso, cap)
    G.flat(head)
    st = {"head_verts_before": before, "torso_tris": torso_tris, "body": G.stats(head), "closed": G.closed(head),
          "symmetry": G.symmetry(head), "neck_cap_removed": len(cap)}
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, f"head_{TAG}.blend"))
    json.dump(st, open(os.path.join(OUT, f"stats_{TAG}.json"), "w"), indent=1)
    print("TORSO_STATS", json.dumps(st))


if __name__ == "__main__":
    main()
