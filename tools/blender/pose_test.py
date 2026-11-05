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
    # deep joints: knees, hips and elbows bend far, so the helper bones and the joint rings are tested
    "squat": {"LeftUpLeg": ("X", -95), "RightUpLeg": ("X", -95), "LeftLeg": ("X", 120), "RightLeg": ("X", 120),
              "LeftFoot": ("X", -25), "RightFoot": ("X", -25), "LeftArm": ("Z", -70), "RightArm": ("Z", 70),
              "LeftForeArm": ("Z", -90), "RightForeArm": ("Z", 90), "Spine1": ("X", 20)},
}
POSES = {k: v for k, v in POSES.items() if k in os.environ.get("POSE_SET", "relaxed,look_up").split(",")}
HALF = [("ArmHelper", "Arm"), ("ElbowHelper", "ForeArm"), ("KneeHelper", "Leg"), ("HipHelper", "UpLeg")]


def rotate(pb, axis, deg):
    bpy.context.view_layer.update()
    head = (rig.matrix_world @ pb.head)
    R = Matrix.Rotation(math.radians(deg), 4, axis)
    w = rig.matrix_world @ pb.matrix
    w = Matrix.Translation(head) @ R @ Matrix.Translation(-head) @ w
    pb.matrix = rig.matrix_world.inverted() @ w


def drive_helpers():
    """Helper bones turn half their joint (src/zombie/lowbody/helpers.ts): with the joint rotation J taken in the
    parent-carried rest frame (child = P * J * rest), the helper gets P * slerp(I, J, 0.5) * rest."""
    from mathutils import Quaternion
    bpy.context.view_layer.update()
    for side in ("Left", "Right"):
        for h, c in HALF:
            hb, cb = rig.pose.bones.get(side + h), rig.pose.bones.get(side + c)
            if not hb or not cb:
                continue
            par = cb.parent
            P = (par.matrix @ par.bone.matrix_local.inverted()).to_quaternion() if par else Quaternion()
            C = (cb.matrix @ cb.bone.matrix_local.inverted()).to_quaternion()
            J = P.inverted() @ C
            Hq = P @ Quaternion().slerp(J, 0.5)
            m = Hq.to_matrix().to_4x4() @ hb.bone.matrix_local
            hp = (par.matrix @ par.bone.matrix_local.inverted()) @ hb.bone.head_local if par else hb.bone.head_local
            m.translation = hp
            hb.matrix = m
            bpy.context.view_layer.update()


tz = float(os.environ.get("POSE_TGT_Z", "-0.45"))
views = {"front": ((0, -2.4, tz), (0, 0, tz)), "34": ((1.5, -1.9, tz + 0.1), (0, 0, tz + 0.03)),
         "face": ((0.35, -0.75, 0.0), (0, 0, -0.05))}
out = []
for pose, rot in POSES.items():
    for pb in rig.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    order = [b.name for b in rig.data.bones]  # parents come before children
    for name in order:
        if name in rot:
            rotate(rig.pose.bones[name], *rot[name])
    drive_helpers()
    sc.render.resolution_x, sc.render.resolution_y = 700, 820
    for v, (pos, t) in views.items():
        cam.location = Vector(pos)
        cam.rotation_euler = (Vector(t) - Vector(pos)).to_track_quat("-Z", "Y").to_euler()
        sc.render.filepath = os.path.join(ROOT, "renders", f"game_{TAG}_pose_{pose}_{v}.png")
        bpy.ops.render.render(write_still=True)
        out.append(sc.render.filepath)
print("POSE_DONE", len(out))
