# Pose test for the assembled character: rotate a few bones and render, to check the skin follows without tearing.
#   POSE_SRC=output/head-game/f2/head_f2_male_v1_color.blend POSE_TAG=f2_male_v1 blender -b -P tools/blender/pose_test.py
import bpy, os, math, json
from mathutils import Matrix, Vector
ROOT = r"C:\Mirza Personal\model 3d maker"
SRC = os.path.join(ROOT, os.environ["POSE_SRC"])
TAG = os.environ.get("POSE_TAG", "pose")
bpy.ops.wm.open_mainfile(filepath=SRC)
rig = bpy.data.objects["F2_Rig"]
sc = bpy.context.scene
cam = sc.camera
POSES = {  # bone: (world axis, degrees); world axes in Blender: x = character's left, -y = forward, z = up
    "relaxed": {"LeftArm": ("Y", 68), "RightArm": ("Y", -68), "Neck": ("X", 10), "Head": ("Z", 30)},
    "look_up": {"LeftArm": ("Y", 40), "RightArm": ("Y", -40), "Neck": ("X", -18), "Head": ("X", -15)},
}


def rotate(pb, axis, deg):
    bpy.context.view_layer.update()
    head = (rig.matrix_world @ pb.head)
    R = Matrix.Rotation(math.radians(deg), 4, axis)
    w = rig.matrix_world @ pb.matrix
    w = Matrix.Translation(head) @ R @ Matrix.Translation(-head) @ w
    pb.matrix = rig.matrix_world.inverted() @ w


views = {"front": ((0, -2.4, -0.45), (0, 0, -0.45)), "34": ((1.5, -1.9, -0.35), (0, 0, -0.42)),
         "face": ((0.35, -0.75, 0.0), (0, 0, -0.05))}
out = []
for pose, rot in POSES.items():
    for pb in rig.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    order = [b.name for b in rig.data.bones]  # parents come before children
    for name in order:
        if name in rot:
            rotate(rig.pose.bones[name], *rot[name])
    bpy.context.view_layer.update()
    sc.render.resolution_x, sc.render.resolution_y = 700, 820
    for v, (pos, t) in views.items():
        cam.location = Vector(pos)
        cam.rotation_euler = (Vector(t) - Vector(pos)).to_track_quat("-Z", "Y").to_euler()
        sc.render.filepath = os.path.join(ROOT, "renders", f"game_{TAG}_pose_{pose}_{v}.png")
        bpy.ops.render.render(write_still=True)
        out.append(sc.render.filepath)
print("POSE_DONE", len(out))
