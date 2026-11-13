"""Line-up sheet of several rigid-part characters: one row per .blend, relaxed pose, given view angles.
  blender -b --factory-startup -P tools/blender/parts_lineup.py -- --out <png> [--angs 20,160,270] a.blend b.blend ...
"""
import sys, os, math, argparse
import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import head_mix as hm
import parts_pose as pp


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--angs", default="20,160")
    ap.add_argument("--pose", default="relaxed")
    ap.add_argument("--zoom", type=float, default=0.0, help="ortho scale round the head (e.g. 0.6); 0 = full body")
    ap.add_argument("files", nargs="+")
    a = ap.parse_args(argv)
    angs = [float(x) for x in a.angs.split(",")]
    tmp = os.path.abspath(a.out) + ".tmp.png"
    tiles = []
    for f in a.files:
        bpy.ops.wm.open_mainfile(filepath=os.path.abspath(f))
        rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")
        for o in bpy.data.objects:
            if o.type == "MESH" and "Col" in o.data.attributes:
                cols = [tuple(o.data.attributes["Col"].data[i].color) for i in range(len(o.data.polygons))]
                hm.set_col(o, lambda i, old, cols=cols: cols[i][:3])
        for o in [o for o in bpy.data.objects if o.type in ("CAMERA", "LIGHT")]:
            bpy.data.objects.remove(o)
        sc, cam = hm.setup_render(640)
        sc.render.resolution_x = 360
        cam.data.ortho_scale = a.zoom or 2.0
        pp.pose(rig, a.pose)
        if a.zoom:
            sc.render.resolution_x = sc.render.resolution_y = 400
            bpy.context.view_layer.update()
            c = rig.matrix_world @ rig.pose.bones["head"].head + Vector((0, 0, 0.02))
        else:
            c = Vector((0, 0, 0.95))
        for ang in angs:
            t = math.radians(ang)
            cam.location = c + Vector((math.sin(t), -math.cos(t), 0.0)) * 8
            cam.rotation_euler = (c - cam.location).to_track_quat("-Z", "Y").to_euler()
            sc.render.filepath = tmp
            bpy.ops.render.render(write_still=True)
            img = bpy.data.images.load(tmp)
            tiles.append(np.array(img.pixels[:]).reshape(img.size[1], img.size[0], 4))
            bpy.data.images.remove(img)
    os.remove(tmp)
    # columns = files, rows = angles
    n = len(a.files)
    order = [tiles[i * len(angs) + k] for k in range(len(angs)) for i in range(n)]
    hm.save_sheet(order, n, os.path.abspath(a.out))
    print("SAVED", a.out)


if __name__ == "__main__":
    main()
