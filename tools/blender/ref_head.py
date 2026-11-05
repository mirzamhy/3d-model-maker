# Masculine low-poly head from the template head: one spatial deformation field applied to every head object
# (head, ears, eyebrows), so the parts stay attached. Head coordinates: x left, y up (eye level 0), z forward.
#   blender -b --factory-startup -P tools/blender/ref_head.py        (RH_SRC, RH_TAG override)
# Target (notes/attachments/ref/parts_head.png): square wide jaw, wide chin, boxy skull with a flatter top,
# brow ridge and cheekbones that catch the light as their own planes. The neck ring (y = -0.172) is not moved,
# so the head still plugs into the body the same way.
import bpy
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import head_game as G  # noqa: E402

ROOT = r"C:\Mirza Personal\model 3d maker"
SRC = os.path.join(ROOT, os.environ.get("RH_SRC", "output/head-game/template/head_nose_v2.blend"))
TAG = os.environ.get("RH_TAG", "head_masc_v1")
OUT = os.path.join(ROOT, "output", "head-game", "template")
K = float(os.environ.get("RH_K", "1.0"))  # overall strength


def bump(v, c, r):
    return math.exp(-((v - c) / r) ** 2)


def ramp(e0, e1, v):
    t = max(0.0, min(1.0, (v - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def deform(x, y, z):
    ax = abs(x)
    s = math.copysign(1.0, x) if x else 0.0
    # jaw: wider toward the jaw angle (back/lower), chin wider and squarer at the front
    jaw = bump(y, -0.085, 0.035) * ramp(-0.16, -0.12, y)
    ax *= 1 + K * 0.16 * jaw
    chin = bump(y, -0.105, 0.025) * ramp(0.03, 0.07, z)
    ax *= 1 + K * 0.30 * chin
    z += K * 0.004 * chin  # chin a little forward
    # boxy skull above the cheekbones: push the xz section toward a rounded square
    w = ramp(-0.03, 0.01, y)
    if w:
        cz = -0.0
        dz = z - cz
        r = math.hypot(ax, dz)
        if r > 1e-6:
            c, sn = ax / r, abs(dz) / r
            box = (c ** 4 + sn ** 4) ** -0.25  # 1 on the axes, 1.19 on the diagonals
            k = 1 + K * 0.9 * (box - 1) * w
            ax *= k
            z = cz + dz * k * (1 - K * 0.10 * w if dz < 0 else 1)  # shorter back of the skull
    # flatter top
    if y > 0.07:
        y -= K * 0.22 * (y - 0.07)
    # brow ridge forward, cheekbones out
    front = ramp(0.05, 0.08, z)
    z += K * 0.004 * bump(y, 0.018, 0.012) * front
    ax += K * 0.004 * bump(y, -0.02, 0.015) * bump(ax, 0.055, 0.015) * ramp(0.0, 0.04, z)
    return s * ax, y, z


def main():
    bpy.ops.wm.open_mainfile(filepath=SRC)
    for ob in [o for o in bpy.data.objects if o.type == "MESH"]:
        mw = ob.matrix_world
        inv = mw.inverted()
        for v in ob.data.vertices:
            p = mw @ v.co
            x, y, z = deform(p.x, p.z, -p.y)
            p.x, p.y, p.z = x, -z, y
            v.co = inv @ p
        ob.data.update()
    head = bpy.data.objects["Head_Main"]
    st = {"head": G.stats(head), "closed": G.closed(head), "symmetry": G.symmetry(head)}
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, f"{TAG}.blend"))
    print("RH_STATS", json.dumps(st))


if __name__ == "__main__":
    main()
