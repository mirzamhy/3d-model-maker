# Coloured render with the wireframe drawn on top (Wireframe-modifier copies; viewport overlays do not render).
#   WIRE_SRC=output/head-game/template/head_tri_sdf_color.blend WIRE_TAG=tri_sdf blender -b -P tools/blender/wire_render.py
import bpy, os
from mathutils import Vector
ROOT = r"C:\Mirza Personal\model 3d maker"
SRC = os.path.join(ROOT, os.environ["WIRE_SRC"])
TAG = os.environ.get("WIRE_TAG", "wire")
bpy.ops.wm.open_mainfile(filepath=SRC)
sc = bpy.context.scene
cam = sc.camera
dark = bpy.data.materials.new("WireDark")
dark.use_nodes = True
dark.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.02, 0.02, 0.025, 1)
for ob in [o for o in bpy.data.objects if o.type == "MESH"]:
    w = ob.copy()
    w.data = ob.data.copy()
    bpy.context.collection.objects.link(w)
    w.data.materials.clear()
    w.data.materials.append(dark)
    m = w.modifiers.new("wire", "WIREFRAME")
    m.thickness = 0.00045
    m.use_even_offset = False
    m.offset = 1.0
tgt = Vector((0, 0, -0.05))
views = {"front": ((0, -0.62, -0.02), tgt), "34": ((0.42, -0.48, 0.0), tgt), "side": ((0.62, 0, -0.02), tgt),
         "ear": ((0.30, -0.10, 0.02), Vector((0.072, 0.02, -0.005)))}
sc.render.resolution_x, sc.render.resolution_y = 800, 900
paths = []
for name, (pos, t) in views.items():
    cam.location = Vector(pos)
    cam.rotation_euler = (t - Vector(pos)).to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = os.path.join(ROOT, "renders", f"game_{TAG}_wire_{name}.png")
    bpy.ops.render.render(write_still=True)
    paths.append(sc.render.filepath)
print("WIRE_DONE", paths)
