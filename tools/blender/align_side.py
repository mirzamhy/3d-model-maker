"""Render the head from its left side at exactly the scale/placement of reference frame f06 (1920x1080).
side px -> m: 0.000325 ; side crop x (abs-550) 444 -> z 0 ; heights via front px.
blender -b file --factory-startup -P align_side.py -- out.png [wire 0/1]"""
import sys, bpy, math
from mathutils import Vector
a = sys.argv[sys.argv.index("--") + 1:]
out = a[0]; wire = len(a) > 1 and a[1] == "1"
sc = bpy.context.scene
grey = bpy.data.materials.new("g"); grey.diffuse_color = (0.42, 0.42, 0.42, 1)
dark = bpy.data.materials.new("d"); dark.diffuse_color = (0.9, 0.05, 0.05, 1)
for o in list(bpy.data.objects):
    if o.type != "MESH":
        bpy.data.objects.remove(o); continue
    o.data.materials.clear(); o.data.materials.append(grey)
    if wire:
        w = o.copy(); w.data = o.data.copy(); sc.collection.objects.link(w)
        w.data.materials.clear(); w.data.materials.append(dark)
        m = w.modifiers.new("w", "WIREFRAME"); m.thickness = 0.0006; m.use_relative_offset = False; m.offset = 1
sc.render.engine = "BLENDER_WORKBENCH"
sh = sc.display.shading; sh.light = "STUDIO"; sh.color_type = "MATERIAL"
sc.world = sc.world or bpy.data.worlds.new("w"); sc.world.color = (0.95, 0.95, 0.95)
sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
cam = bpy.data.objects.new("c", bpy.data.cameras.new("c")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = "ORTHO"; cam.data.ortho_scale = 1920 * 0.000325
# image centre (960, 540) abs = side crop (410, 540)
zc = (444 - 410) * 0.000325
yf = 470 + (540 - 490) * 1.085
yc = (915 - yf) * 0.0003 - 0.122
c = Vector((0, -zc, yc))
cam.location = c + Vector((5, 0, 0))
cam.rotation_euler = (c - cam.location).to_track_quat("-Z", "Y").to_euler()
sc.render.filepath = out
bpy.ops.render.render(write_still=True)
