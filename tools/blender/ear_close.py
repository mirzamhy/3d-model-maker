import sys, os, math, bpy
from mathutils import Vector
a = sys.argv[sys.argv.index("--") + 1:]; out = a[0]; angs = [float(x) for x in a[1:]]
os.makedirs(out, exist_ok=True)
sc = bpy.context.scene
cols = {"Hair": (0.20, 0.13, 0.08, 1), "Ears": (0.95, 0.6, 0.45, 1), "Eyes": (0.05, 0.03, 0.02, 1)}
blk = bpy.data.materials.new("k"); blk.diffuse_color = (0, 0, 0, 1)
for o in list(bpy.data.objects):
    if o.type != "MESH":
        bpy.data.objects.remove(o); continue
    m = bpy.data.materials.new(o.name); m.diffuse_color = cols.get(o.name, (0.80, 0.55, 0.38, 1))
    o.data.materials.clear(); o.data.materials.append(m)
    w = o.copy(); w.data = o.data.copy(); sc.collection.objects.link(w); w.data.materials.clear(); w.data.materials.append(blk)
    md = w.modifiers.new("w", "WIREFRAME"); md.thickness = 0.00025; md.use_relative_offset = False; md.offset = 1
sc.render.engine = "BLENDER_WORKBENCH"
sh = sc.display.shading; sh.light = "STUDIO"; sh.color_type = "MATERIAL"
sc.world = sc.world or bpy.data.worlds.new("w"); sc.world.color = (0.93, 0.93, 0.93)
sc.view_settings.view_transform = "Standard"
sc.render.resolution_x, sc.render.resolution_y = 700, 700
cam = bpy.data.objects.new("c", bpy.data.cameras.new("c")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = "ORTHO"; cam.data.ortho_scale = 0.12
c = Vector((0.07, 0.031, -0.025))  # left ear (head x +, z -0.031 -> blender y +0.031)
for ang in angs:
    t = math.radians(ang)
    cam.location = c + Vector((math.sin(t), -math.cos(t), 0.1)).normalized() * 3
    cam.rotation_euler = (c - cam.location).to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = os.path.join(out, "z%+04d.png" % int(ang))
    bpy.ops.render.render(write_still=True)
