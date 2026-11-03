# Close renders of the ear only, straight at the ear plane and from the back/top, for comparing with references.
#   EAR_SRC=output/head-game/template/head_tpl_v11_color.blend EAR_TAG=v11 blender -b -P tools/blender/ear_view.py
import bpy, os, math
from mathutils import Vector
ROOT = r"C:\Mirza Personal\model 3d maker"
SRC = os.path.join(ROOT, os.environ.get("EAR_SRC", r"output\head-game\template\head_tpl_v11_color.blend"))
TAG = os.environ.get("EAR_TAG", "v11")
bpy.ops.wm.open_mainfile(filepath=SRC)
sc = bpy.context.scene
cam = sc.camera
a = math.radians(float(os.environ.get("EAR_ANGLE", "15")))
n = Vector((math.cos(a), -math.sin(a), 0.0))  # ear normal in Blender axes
c = Vector((0.074, 0.016, -0.002))
views = {"ear_flat": (c + n * 0.22, c), "ear_34": (c + (n + Vector((0, -0.7, 0.25))).normalized() * 0.22, c),
         "ear_top": (c + (n + Vector((0, 0.3, 0.9))).normalized() * 0.22, c),
         "ear_front": (c + (n + Vector((0, -1.3, 0.1))).normalized() * 0.22, c)}
sc.render.resolution_x = sc.render.resolution_y = 700
paths = []
for name, (pos, t) in views.items():
    cam.location = pos
    cam.rotation_euler = (t - pos).to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = os.path.join(ROOT, "renders", f"game_tpl_{TAG}_{name}.png")
    bpy.ops.render.render(write_still=True)
    paths.append(sc.render.filepath)
# wire overlay version via Freestyle
sc.render.use_freestyle = True
sc.view_layers[0].freestyle_settings.linesets[0].select_by_visibility = True if sc.view_layers[0].freestyle_settings.linesets else None
pos, t = views["ear_flat"]
cam.location = pos
cam.rotation_euler = (t - pos).to_track_quat("-Z", "Y").to_euler()
for ls in sc.view_layers[0].freestyle_settings.linesets:
    ls.select_by_edge_types = True
    for k in ("select_silhouette", "select_border", "select_crease"):
        setattr(ls, k, True)
    ls.select_edge_mark = False
sc.render.line_thickness = 1.0
sc.view_layers[0].freestyle_settings.crease_angle = math.radians(179)
sc.render.filepath = os.path.join(ROOT, "renders", f"game_tpl_{TAG}_ear_wire.png")
bpy.ops.render.render(write_still=True)
print("EAR_VIEW_DONE")

# wire overlay: project the ear edges into the 3/4 render and draw them (Freestyle is unreliable headless)
from bpy_extras.object_utils import world_to_camera_view
import json
sc.render.use_freestyle = False
for name in ("ear_34", "ear_flat", "ear_front"):
    pos, t = views[name]
    cam.location = pos
    cam.rotation_euler = (t - pos).to_track_quat("-Z", "Y").to_euler()
    bpy.context.view_layer.update()
    ear = bpy.data.objects["Ears"]
    mw = ear.matrix_world
    pts = [world_to_camera_view(sc, cam, mw @ v.co) for v in ear.data.vertices]
    ez = ear.data.attributes["ear_zone"].data
    edges = sorted({tuple(sorted(ek)) for f in ear.data.polygons if ez[f.index].value > 0
                    and (mw @ f.center).x > 0 for ek in f.edge_keys})
    json.dump({"pts": [(p.x, 1 - p.y, p.z) for p in pts], "edges": edges},
              open(os.path.join(ROOT, "renders", f"game_tpl_{TAG}_{name}_wire.json"), "w"))
print("EAR_WIRE_DONE")
