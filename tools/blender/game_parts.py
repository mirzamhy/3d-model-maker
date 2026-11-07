# Low-poly parts for the DEADZONE game (tiktok/game): the game poses rigid parts per bone (one InstancedMesh per
# part, tinted per character), so a character is a set of part meshes, each in its bone's local frame:
#   limbs (upperArm, forearm, thigh, shin, neck): +y from the joint along the bone (lengths = game BONES), symmetric
#     in x (left and right share the mesh), local -z = front of the knee / elbow side as the game rig turns it
#   torso: waist at y 0 up to the neck base at y 0.5, +z forward (scaled per character by bodyW / bodyD)
#   pelvis: waist at y 0 down to the crotch (-0.13); hips at y -0.05, x +-0.095
#   hand: wrist at y 0, fingers +y; boot: ankle at the origin, +z toward the toe, sole at y -0.08
#   head / face / hair: head frame, origin at the top of the neck
# Colours are vertex colours multiplied by the instance tint: tinted parts are white with darker details.
# The head is the approved big-plane head (head_lp_v6, head_planes.py), scaled into the head frame; its skin colours
# are divided by the skin colour so the tint gives each character its own skin.
# Writes flat (non-indexed) triangles with face normals as JSON for the game, plus a .blend to look at.
#   blender -b --factory-startup -P tools/blender/game_parts.py -- --head output/head-game/template/head_lp_v6.blend
#       --json <tiktok>/game/src/render/lowpoly/survivor_parts.json --blend output/game/parts_v1.blend
import argparse
import json
import math
import os
import sys

import bpy
import numpy as np

HEAD_S = 1.35  # template head (0.22 m chin to crown) -> game head frame (big readable heads, hats fit)
HEAD_OFF = (0.0, 0.06, 0.01)  # template neck top (y -0.06, z -0.01) -> head frame origin
SKIN = (0.80, 0.58, 0.45)
HAIR_COL = (0.27, 0.18, 0.11)


def lin(c):
    return np.array([ch ** 2.2 for ch in c])


def opts():
    p = argparse.ArgumentParser()
    p.add_argument("--head", required=True)
    p.add_argument("--json", required=True)
    p.add_argument("--blend", default="")
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    return p.parse_args(argv)


# ---------------------------------------------------------------- mesh helpers (game coords: x, y up, z forward)
class Mesh:
    def __init__(self):
        self.v, self.f, self.c = [], [], []

    def add(self, verts, faces, col=(1, 1, 1)):
        o = len(self.v)
        self.v += [tuple(map(float, p)) for p in verts]
        for f in faces:
            self.f.append([o + i for i in f])
            self.c.append(tuple(col) if not callable(col) else col(f))
        return self


def ring_pts(y, rx, rzf, rzb, angles, cx=0.0, cz=0.0, ex=2.6):
    """Superellipse cross-section (boxy at ex > 2): angle 0 = front (+z), 90 = +x."""
    pts = []
    for a in angles:
        t = math.radians(a)
        s, c = math.sin(t), math.cos(t)
        sx = math.copysign(abs(s) ** (2 / ex), s)
        cz_ = math.copysign(abs(c) ** (2 / ex), c)
        rz = rzf if c >= 0 else rzb
        pts.append((cx + rx * sx, y, cz + rz * cz_))
    return pts


def loft(m, rings, angles, col=(1, 1, 1), cap0=True, cap1=True, ex=2.6, band=()):
    """rings: [(y, rx, rz_front, rz_back[, cx, cz])]; faces between rings; flat caps (fans) at both ends.
    band: ring indices i whose segment i -> i + 1 gets the darker band colour."""
    n = len(angles)
    verts = []
    for r in rings:
        verts += ring_pts(r[0], r[1], r[2], r[3], angles, *(r[4:6] if len(r) > 4 else (0.0, 0.0)), ex=ex)
    faces, cols = [], []
    for i in range(len(rings) - 1):
        for k in range(n):
            k2 = (k + 1) % n
            faces.append([i * n + k, (i + 1) * n + k, (i + 1) * n + k2, i * n + k2])
            cols.append(BAND if i in band else col)
    o = len(m.v)
    m.v += verts
    for f, c in zip(faces, cols):
        m.f.append([o + i for i in f])
        m.c.append(c)
    for end, last in ((cap0, False), (cap1, True)):
        if not end:
            continue
        base = (len(rings) - 1) * n if last else 0
        ring = list(range(o + base, o + base + n))
        m.f.append(ring if last else ring[::-1])
        m.c.append(col)
    return m


BAND = (0.86, 0.86, 0.86)  # hem / cuff / collar bands: a little darker than the tint
H6 = [30, 90, 150, 210, 270, 330]  # 6 sides, flat front and back
H8 = [22.5 + 45 * k for k in range(8)]
T10 = [15, 50, 90, 130, 165, 195, 230, 270, 310, 345]  # torso: flat front / back planes, chest corners


def limb(rings, angles=H6, dome=0.03, col=(1, 1, 1), ex=2.2, band=()):
    """Limb along +y with pointed (faceted) end domes so a rotating joint never shows a hole."""
    y0, y1 = rings[0], rings[-1]
    rr = [(y0[0] - dome, y0[1] * 0.45, y0[2] * 0.45, y0[3] * 0.45)] + rings + \
         [(y1[0] + dome, y1[1] * 0.45, y1[2] * 0.45, y1[3] * 0.45)]
    return loft(Mesh(), rr, angles, col, ex=ex, band=tuple(b + 1 for b in band))


def parts_body():
    P = {}
    # upper arm = sleeve (tinted by the top colour); cuff band just above the elbow
    P["upperArm"] = limb([(0.0, 0.064, 0.060, 0.060), (0.10, 0.066, 0.058, 0.060), (0.215, 0.060, 0.054, 0.054),
                          (0.215, 0.066, 0.060, 0.060), (0.255, 0.066, 0.060, 0.060), (0.255, 0.052, 0.048, 0.048),
                          (0.29, 0.048, 0.044, 0.044)], dome=0.035, band=(3,))
    P["forearm"] = limb([(0.0, 0.048, 0.046, 0.046), (0.09, 0.052, 0.046, 0.044), (0.25, 0.036, 0.030, 0.030),
                         (0.27, 0.034, 0.028, 0.028)], dome=0.025)
    # mitten hand: palm block widening to the knuckles, fingers taper (flat palm, thin side to side in z)
    P["hand"] = limb([(0.0, 0.032, 0.022, 0.022), (0.035, 0.042, 0.026, 0.026), (0.07, 0.044, 0.024, 0.024),
                      (0.10, 0.034, 0.018, 0.018)], angles=H6, dome=0.015, ex=3.0)
    # cargo trousers: straight thigh, knee, leg slightly wider at the boot top
    P["thigh"] = limb([(0.0, 0.094, 0.090, 0.092), (0.16, 0.090, 0.086, 0.088), (0.32, 0.080, 0.076, 0.078),
                       (0.42, 0.072, 0.068, 0.070)], angles=H8, dome=0.04)
    P["shin"] = limb([(0.0, 0.070, 0.068, 0.068), (0.16, 0.068, 0.066, 0.066), (0.30, 0.066, 0.062, 0.064),
                      (0.41, 0.060, 0.056, 0.058)], angles=H8, dome=0.03)
    P["neck"] = limb([(0.0, 0.047, 0.045, 0.045), (0.09, 0.044, 0.042, 0.042)], dome=0.02)
    # torso = t-shirt: hem band (step out), waist, chest, shoulder yoke, collar rib; waist at y 0
    tr = [(-0.035, 0.152, 0.118, 0.112), (-0.005, 0.152, 0.118, 0.112), (-0.005, 0.140, 0.106, 0.100),
          (0.08, 0.140, 0.104, 0.100), (0.24, 0.160, 0.120, 0.112), (0.36, 0.166, 0.118, 0.112),
          (0.43, 0.140, 0.098, 0.096), (0.475, 0.090, 0.070, 0.074), (0.475, 0.078, 0.064, 0.068),
          (0.505, 0.072, 0.060, 0.064)]
    P["torso"] = loft(Mesh(), tr, T10, ex=2.8, band=(0, 7))
    # pelvis = trouser top: waist (under the belt) -> hips -> crotch
    pl = [(0.05, 0.132, 0.098, 0.100), (0.0, 0.140, 0.102, 0.104), (-0.06, 0.146, 0.104, 0.112),
          (-0.11, 0.110, 0.084, 0.092), (-0.135, 0.060, 0.050, 0.060)]
    P["pelvis"] = loft(Mesh(), pl, T10, ex=2.6)
    # boot: shaft ring at the ankle, foot along +z, darker sole slab
    shaft = Mesh()
    loft(shaft, [(-0.045, 0.058, 0.062, 0.062, 0, -0.005), (0.035, 0.060, 0.064, 0.064, 0, -0.005),
                (0.075, 0.064, 0.068, 0.068, 0, -0.005), (0.09, 0.056, 0.060, 0.060, 0, -0.005)], H8, ex=2.4, band=(1,))
    # foot as a loft along z: cross-sections (x half width, y bottom, y top)
    secs = [(-0.07, 0.050, -0.075, 0.000), (-0.03, 0.056, -0.075, 0.020), (0.04, 0.056, -0.075, 0.000),
            (0.11, 0.052, -0.075, -0.030), (0.145, 0.040, -0.075, -0.052)]
    vs, fs = [], []
    for z, hw, yb, yt in secs:  # 6 points per section: bottom pair, side pair, top pair
        vs += [(-hw, yb, z), (hw, yb, z), (hw * 1.05, (yb + yt) / 2, z), (hw * 0.85, yt, z), (-hw * 0.85, yt, z),
               (-hw * 1.05, (yb + yt) / 2, z)]
    n = 6
    for i in range(len(secs) - 1):
        for k in range(n):
            k2 = (k + 1) % n
            fs.append([i * n + k, i * n + k2, (i + 1) * n + k2, (i + 1) * n + k])
    fs.append(list(range(n))[::-1])
    fs.append([(len(secs) - 1) * n + k for k in range(n)])
    foot = Mesh().add(vs, fs)
    sole = [(-0.06, 0.054), (0.04, 0.060), (0.11, 0.056), (0.155, 0.040)]
    sv, sf = [], []
    for z, hw in sole:
        sv += [(-hw, -0.088, z), (hw, -0.088, z), (hw, -0.074, z), (-hw, -0.074, z)]
    for i in range(len(sole) - 1):
        for k in range(4):
            k2 = (k + 1) % 4
            sf.append([i * 4 + k, i * 4 + k2, (i + 1) * 4 + k2, (i + 1) * 4 + k])
    sf.append([3, 2, 1, 0])
    sf.append([(len(sole) - 1) * 4 + k for k in range(4)])
    slab = Mesh().add(sv, sf, (0.42, 0.40, 0.38))
    fix_winding(shaft, lambda c: np.array([0.0, c[1], -0.005]))
    fix_winding(foot, lambda c: np.array([0.0, -0.04, c[2]]))
    fix_winding(slab, lambda c: np.array([0.0, -0.081, c[2]]))
    boot = Mesh()
    for part in (shaft, foot, slab):
        o = len(boot.v)
        boot.v += part.v
        boot.f += [[o + i for i in f] for f in part.f]
        boot.c += part.c
    P["boot"] = boot
    return P


# ---------------------------------------------------------------- head from the approved template
def head_parts(path):
    bpy.ops.wm.open_mainfile(filepath=path)
    out = {"headLP": Mesh(), "faceLP": Mesh(), "hairLP": Mesh()}
    skin_l, hair_l = lin(SKIN), lin(HAIR_COL)
    for ob in bpy.data.objects:
        if ob.type != "MESH" or ob.name == "Head_Main":
            continue
        me = ob.data
        mw = ob.matrix_world
        col = me.attributes.get("Col")
        key = {"Head": "headLP", "Ears": "headLP", "Hair": "hairLP"}.get(ob.name, "faceLP")
        verts = []
        for v in me.vertices:
            b = mw @ v.co
            h = np.array([b.x, b.z, -b.y]) + HEAD_OFF  # Blender -> head coords -> head frame
            verts.append(tuple(h * HEAD_S))
        faces, cols = [], []
        for p in me.polygons:
            c = np.array(col.data[p.index].color[:3]) if col is not None and col.domain == "FACE" else np.ones(3)
            if key == "headLP":
                c = np.clip(c / skin_l, 0, 1)  # skin -> white, darker zones keep their ratio
            elif key == "hairLP":
                c = np.clip(c / hair_l, 0, 1)
            faces.append(list(p.vertices))
            cols.append(tuple(c))
        o = len(out[key].v)
        out[key].v += verts
        for f, c in zip(faces, cols):
            out[key].f.append([o + i for i in f])
            out[key].c.append(c)
    return out


# ---------------------------------------------------------------- export
def triangles(m):
    """Flat triangles: (positions, normals, colours) arrays, outward winding kept from the face order."""
    pos, nrm, col = [], [], []
    v = np.array(m.v)
    for f, c in zip(m.f, m.c):
        # one normal per polygon (Newell), as Blender shades it: a slightly bent quad stays one plane, not two
        pts = v[f]
        n = np.zeros(3)
        for j in range(len(pts)):
            p0, p1 = pts[j], pts[(j + 1) % len(pts)]
            n += np.array([(p0[1] - p1[1]) * (p0[2] + p1[2]), (p0[2] - p1[2]) * (p0[0] + p1[0]),
                           (p0[0] - p1[0]) * (p0[1] + p1[1])])
        ln = np.linalg.norm(n)
        if ln < 1e-12:
            continue
        n /= ln
        for i in range(1, len(f) - 1):
            a, b, d = v[f[0]], v[f[i]], v[f[i + 1]]
            if np.linalg.norm(np.cross(b - a, d - a)) < 1e-12:
                continue
            for p in (a, b, d):
                pos += list(p)
                nrm += list(n)
                col += list(c)
    return pos, nrm, col


def fix_winding(m, centre_fn):
    """Faces whose normal points toward the part's own axis are reversed (lofts are built one way)."""
    v = np.array(m.v)
    for i, f in enumerate(m.f):
        pts = v[f]
        n = np.cross(pts[1] - pts[0], pts[2] - pts[0])
        if np.linalg.norm(n) < 1e-12 and len(f) > 3:
            n = np.cross(pts[2] - pts[0], pts[3] - pts[0])
        c = pts.mean(0)
        out = c - centre_fn(c)
        if np.linalg.norm(out) < 0.4 * np.linalg.norm(pts - c, axis=1).max():  # cap on the axis: away from the middle
            out = c - v.mean(0)
        if np.dot(n, out) < 0:
            m.f[i] = f[::-1]


def to_blend(name, m):
    me = bpy.data.meshes.new(name)
    me.from_pydata([(p[0], -p[2], p[1]) for p in m.v], [], m.f)
    me.validate()
    a = me.color_attributes.new("Col", "FLOAT_COLOR", "FACE")
    for i, c in enumerate(m.c[:len(me.polygons)]):
        a.data[i].color = tuple(c) + (1.0,)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def main():
    a = opts()
    H = head_parts(a.head)
    P = parts_body()
    axis_y = lambda c: np.array([0.0, c[1], 0.0])  # limbs, torso, pelvis: axis is the local y line
    for k, m in P.items():
        if k != "boot":
            fix_winding(m, axis_y)
    P.update(H)
    data, stats = {}, {}
    for k, m in P.items():
        pos, nrm, col = triangles(m)
        data[k] = {"position": [round(x, 5) for x in pos], "normal": [round(x, 4) for x in nrm],
                   "color": [round(x, 4) for x in col]}
        stats[k] = len(pos) // 9
    os.makedirs(os.path.dirname(os.path.abspath(a.json)), exist_ok=True)
    with open(a.json, "w") as fh:
        json.dump({"version": "lp1", "source": "model 3d maker/tools/blender/game_parts.py", "tris": stats, "parts": data}, fh,
                  separators=(",", ":"))
    if a.blend:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        for i, (k, m) in enumerate(P.items()):
            ob = to_blend(k, m)
            ob.location.x = (i % 6) * 0.45
            ob.location.y = (i // 6) * 0.6
        os.makedirs(os.path.dirname(os.path.abspath(a.blend)), exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(a.blend))
    print("GAME_PARTS", json.dumps(stats), "total", sum(stats.values()))


if __name__ == "__main__":
    main()
