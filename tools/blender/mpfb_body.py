# MakeHuman body from MPFB2 (Blender extension "mpfb", GPL) as a SHAPE MOULD: anatomy (chest, shoulders, calves,
# neck) comes from MakeHuman's targets, our own clean quad rings get projected onto it later (like body_quad.py did
# with the F2 body). Run WITHOUT --factory-startup (the extension lives in the user preferences):
#   blender -b -P tools/blender/mpfb_body.py          (MB_MUSCLE, MB_WEIGHT, MB_TAG override)
import bpy
import json
import math
import os
from mathutils import Vector

from bl_ext.blender_org.mpfb.services.humanservice import HumanService
from bl_ext.blender_org.mpfb.services.targetservice import TargetService
from bl_ext.blender_org.mpfb.services.rigservice import RigService

ROOT = r"C:\Mirza Personal\model 3d maker"
OUT = os.path.join(ROOT, "output", "mpfb")
TAG = os.environ.get("MB_TAG", "mpfb_male_v1")
HEIGHT = float(os.environ.get("MB_HEIGHT", "1.78"))


def main():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob)
    macro = TargetService.get_default_macro_info_dict()
    macro.update(gender=1.0, age=0.5, muscle=float(os.environ.get("MB_MUSCLE", "0.8")),
                 weight=float(os.environ.get("MB_WEIGHT", "0.5")), proportions=1.0, height=0.6)
    body = HumanService.create_human(macro_detail_dict=macro)
    # bake: shape keys -> mesh, helper geometry (masked) removed
    TargetService.bake_targets(body)
    # T-pose like the reference sheet: MPFB's "default" rig + its bundled t-pose, baked into the mesh
    rig = None
    if os.environ.get("MB_TPOSE", "1") == "1":
        rig = HumanService.add_builtin_rig(body, "default")
        import bl_ext.blender_org.mpfb as mpfb_pkg
        pose = json.load(open(os.path.join(os.path.dirname(mpfb_pkg.__file__), "data", "poses", "default_fk",
                                           "t-pose.json")))
        bpy.ops.object.select_all(action="DESELECT")
        bpy.context.view_layer.objects.active = rig
        rig.select_set(True)
        bpy.ops.object.mode_set(mode="POSE")
        RigService.set_pose_from_dict(rig, pose)
        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.context.view_layer.update()
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = body
    body.select_set(True)
    for m in list(body.modifiers):
        bpy.ops.object.modifier_apply(modifier=m.name)
    if rig is not None:
        bpy.data.objects.remove(rig)
    # scale to the reference stature, feet on the ground
    zs = [v.co.z for v in body.data.vertices]
    s = HEIGHT / (max(zs) - min(zs))
    for v in body.data.vertices:
        v.co = Vector((v.co.x * s, v.co.y * s, (v.co.z - min(zs)) * s))
    body.name = "MPFB_Body"
    me = body.data
    tris = sum(len(p.vertices) - 2 for p in me.polygons)
    # arm angle: shoulder to wrist direction in the front plane (T-pose = 0, A-pose ~ 45)
    xs = sorted(me.vertices, key=lambda v: v.co.x)
    tip = xs[-1].co
    st = {"verts": len(me.vertices), "tris": tris, "scale": round(s, 4), "macro": {k: v for k, v in macro.items() if k != "race"},
          "hand_tip": [round(c, 3) for c in tip]}
    os.makedirs(OUT, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, f"{TAG}.blend"))
    json.dump(st, open(os.path.join(OUT, f"stats_{TAG}.json"), "w"), indent=1)
    print("MB_STATS", json.dumps(st))
    # quick look: 4 orthographic views with sun light
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE"
    sc.render.resolution_x, sc.render.resolution_y = 500, 700
    mat = bpy.data.materials.new("skin")
    mat.diffuse_color = (0.8, 0.55, 0.42, 1)
    me.materials.clear()
    me.materials.append(mat)
    for p in me.polygons:
        p.use_smooth = False
    ld = bpy.data.lights.new("sun", "SUN")
    ld.energy = 3.5
    lo = bpy.data.objects.new("sun", ld)
    sc.collection.objects.link(lo)
    lo.rotation_euler = (0.9, 0.0, 0.5)
    if sc.world is None:
        sc.world = bpy.data.worlds.new("w")
    sc.world.color = (0.25, 0.26, 0.28)
    cd = bpy.data.cameras.new("cam")
    cd.type = "ORTHO"
    cd.ortho_scale = 2.0
    cam = bpy.data.objects.new("cam", cd)
    sc.collection.objects.link(cam)
    sc.camera = cam
    for name, d in (("front", (0, -1, 0)), ("side", (1, 0, 0)), ("back", (0, 1, 0)), ("34", (0.7, -0.7, 0))):
        d = Vector(d).normalized()
        cam.location = Vector((0, 0, 0.92)) + d * 6
        cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
        sc.render.filepath = os.path.join(ROOT, "renders", f"{TAG}_{name}.png")
        bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
