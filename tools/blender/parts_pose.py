"""Check sheet for rigid parts (cut_parts.py): exploded T-pose, then poses that bend every joint, plus a head / neck
close-up. Rows: front, 3/4. Columns: exploded, arms down + head turned, walk + elbow, crouch + head nod.
  blender -b <parts.blend> --factory-startup -P tools/blender/parts_pose.py -- --sheet <png> [--close <png>]
"""
import sys, os, math, argparse
import bpy
import numpy as np
from mathutils import Vector, Matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import head_mix as hm

# rotations about WORLD axes (x = character's left, y = back, z = up), degrees, applied in each bone's rest frame
POSES = {
    "explode": {},
    "relaxed": {"upper_arm.L": (0, 70, 0), "upper_arm.R": (0, -70, 0), "forearm.L": (0, 0, -20),
                "forearm.R": (0, 0, 20), "head": (0, 0, 35)},
    "walk": {"thigh.L": (-35, 0, 0), "shin.L": (50, 0, 0), "foot.L": (-15, 0, 0), "thigh.R": (25, 0, 0),
             "shin.R": (10, 0, 0), "upper_arm.L": (25, 70, 0), "forearm.L": (0, 0, -70), "upper_arm.R": (-25, -70, 0),
             "forearm.R": (0, 0, 30), "chest": (0, 0, 12)},
    "crouch": {"thigh.L": (-100, 0, 0), "shin.L": (120, 0, 0), "foot.L": (-20, 0, 0), "thigh.R": (-100, 0, 0),
               "shin.R": (120, 0, 0), "foot.R": (-20, 0, 0), "spine": (25, 0, 0), "neck": (-15, 0, 0),
               "head": (25, 0, 0), "upper_arm.L": (0, 30, -60), "upper_arm.R": (0, -30, 60), "forearm.L": (0, 0, -60),
               "forearm.R": (0, 0, 60)},
}


def pose(rig, name):
    for pb in rig.pose.bones:
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.location = (0, 0, 0)
    for b, (x, y, z) in POSES[name].items():
        if b not in rig.pose.bones:
            continue
        R = (Matrix.Rotation(math.radians(z), 4, "Z") @ Matrix.Rotation(math.radians(y), 4, "Y")
             @ Matrix.Rotation(math.radians(x), 4, "X"))
        M = rig.data.bones[b].matrix_local
        rig.pose.bones[b].rotation_quaternion = (M.inverted() @ R @ M).to_quaternion()
    if name == "crouch":
        rig.location.z = -0.30
    else:
        rig.location.z = 0
    bpy.context.view_layer.update()


BASIS = {}


def explode(rig, on):
    """Parts pushed out from the body centre (by their bone's mid point) so the cuts and caps show."""
    c = Vector((0, 0, 1.0))
    for o in bpy.data.objects:
        if o.type != "MESH" or o.parent != rig:
            continue
        if o.name not in BASIS:
            BASIS[o.name] = o.matrix_basis.copy()
        o.matrix_basis = BASIS[o.name]
        if on:
            b = rig.data.bones[o.parent_bone]
            d = (b.head_local + b.tail_local) / 2 - c
            d.y = 0
            o.matrix_world.translation = o.matrix_world.translation + d * 0.45
    bpy.context.view_layer.update()


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--sheet", required=True)
    ap.add_argument("--close", default="")
    ap.add_argument("--arm", default="")
    ap.add_argument("--hip", default="")
    ap.add_argument("--knee", default="")
    ap.add_argument("--angs", default="0,35", help="sheet view angles (deg), e.g. 160,215 for the back (gear)")
    a = ap.parse_args(argv)
    rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    for o in bpy.data.objects:
        if o.type == "MESH" and "Col" in o.data.attributes:
            cols = [tuple(o.data.attributes["Col"].data[i].color) for i in range(len(o.data.polygons))]
            hm.set_col(o, lambda i, old, cols=cols: cols[i][:3])
    for o in [o for o in bpy.data.objects if o.type in ("CAMERA", "LIGHT")]:
        bpy.data.objects.remove(o)
    sc, cam = hm.setup_render(700)
    sc.render.resolution_x = 560
    cam.data.ortho_scale = 2.3
    tmp = os.path.abspath(a.sheet) + ".tmp.png"

    def shot(centre, ang, scale=2.3):
        cam.data.ortho_scale = scale
        t = math.radians(ang)
        cam.location = centre + Vector((math.sin(t), -math.cos(t), 0.0)) * 8
        cam.rotation_euler = (centre - cam.location).to_track_quat("-Z", "Y").to_euler()
        sc.render.filepath = tmp
        bpy.ops.render.render(write_still=True)
        img = bpy.data.images.load(tmp)
        px = np.array(img.pixels[:]).reshape(img.size[1], img.size[0], 4)
        bpy.data.images.remove(img)
        return px
    tiles = []
    for ang in [float(x) for x in a.angs.split(",")]:
        for name in POSES:
            pose(rig, name)
            explode(rig, name == "explode")
            tiles.append(shot(Vector((0, 0, 0.95)), ang))
    explode(rig, False)
    hm.save_sheet(tiles, len(POSES), os.path.abspath(a.sheet))
    if a.close:
        sc.render.resolution_x = sc.render.resolution_y = 560
        tiles = []
        for name in ("explode", "relaxed", "crouch"):
            pose(rig, name)
            explode(rig, name == "explode")
            head = rig.matrix_world @ rig.pose.bones["neck"].head
            for ang in (0, 90):
                tiles.append(shot(head + Vector((0, 0, 0.08)), ang, 0.55))
        hm.save_sheet(tiles, 2, os.path.abspath(a.close))
    if a.arm:
        # left arm joints: shoulder, elbow, wrist; front + back-side (arm faces the camera)
        sc.render.resolution_x = sc.render.resolution_y = 560
        tiles = []
        for name in ("explode", "relaxed", "walk", "crouch"):
            pose(rig, name)
            explode(rig, False)
            pb = rig.pose.bones
            c = rig.matrix_world @ ((pb["upper_arm.L"].head + pb["forearm.L"].tail) / 2)
            for ang in (0, 90, 180):
                tiles.append(shot(c, ang, 0.75))
        hm.save_sheet(tiles, 3, os.path.abspath(a.arm))
    if a.hip:
        # hips: front, side, back, 3/4 back
        sc.render.resolution_x = sc.render.resolution_y = 560
        tiles = []
        for name in ("explode", "relaxed", "walk", "crouch"):
            pose(rig, name)
            explode(rig, False)
            c = rig.matrix_world @ rig.pose.bones["hips"].head + Vector((0, 0, -0.12))
            for ang in (0, 90, 180, 230):
                tiles.append(shot(c, ang, 0.8))
        hm.save_sheet(tiles, 4, os.path.abspath(a.hip))
    if a.knee:
        # left knee: front, side, back, 3/4
        sc.render.resolution_x = sc.render.resolution_y = 560
        tiles = []
        for name in ("relaxed", "walk", "crouch"):
            pose(rig, name)
            explode(rig, False)
            c = rig.matrix_world @ rig.pose.bones["shin.L"].head
            for ang in (0, 90, 180, 40):
                tiles.append(shot(c, ang, 0.45))
        hm.save_sheet(tiles, 4, os.path.abspath(a.knee))
    os.remove(tmp)
    print("SHEET", a.sheet)


if __name__ == "__main__":
    main()
