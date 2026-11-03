# Colour pass for a finished game head: per-face colours by face region + a lit Eevee render.
#   "/c/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup -P tools/blender/head_paint.py
#   PAINT_SRC=output/head-game/template/head_tpl_v6.blend PAINT_TAG=tpl_v6_color ...
# Colours live in a face colour attribute "Col" (one colour per face, low-poly palette look), read by one material.
# Regions are decided in head coordinates (x left, y up, z forward, y = 0 at eye level).
import bpy
import bmesh
import math
import os
import random
import numpy as np
from mathutils import Vector

ROOT = r"C:\Mirza Personal\model 3d maker"
SRC = os.path.join(ROOT, os.environ.get("PAINT_SRC", r"output\head-game\template\head_tpl_v6.blend"))
TAG = os.environ.get("PAINT_TAG", "tpl_v6_color")
REN = os.path.join(ROOT, "renders")

SKIN = (0.80, 0.58, 0.45)
SOCKET = (0.62, 0.43, 0.36)  # eye hollow, a little darker and cooler
WARM = (0.84, 0.54, 0.43)  # cheeks, nose tip, ears
LIP = (0.66, 0.36, 0.33)
MOUTH = (0.22, 0.10, 0.09)  # inside the mouth line
NECK = (0.74, 0.53, 0.41)
BROW = (0.16, 0.10, 0.06)
# ear zones (attribute ear_zone): 0 back, 1 helix rim, 2 antihelix, 3 concha bowl, 4 ear canal
EAR_ZONE = {0: (0.80, 0.55, 0.43), 1: (0.86, 0.57, 0.45), 2: (0.82, 0.56, 0.44), 3: (0.70, 0.44, 0.36),
            4: (0.36, 0.20, 0.17)}


def hc(v):
    return np.array([v[0], v[2], -v[1]])


# soft colour spots: (colour, centre (|x|, y), radius (x, y), strength), only on the front (z > 0.03)
SPOTS = [
    (SOCKET, (0.031, 0.003), (0.017, 0.011), 0.9),  # eye hollow
    (WARM, (0.047, -0.026), (0.014, 0.013), 0.75),  # cheek
    (WARM, (0.0, -0.037), (0.009, 0.008), 0.6),  # nose tip
]


def region_colour(c, lip_tag):
    x, y, z = abs(c[0]), c[1], c[2]
    if lip_tag == 1:
        return MOUTH
    if lip_tag == 2:
        return LIP
    col = np.array(NECK if y < -0.125 else SKIN)
    if z > 0.03:
        for spot, (cx, cy), (rx, ry), k in SPOTS:
            w = k * math.exp(-((x - cx) / rx) ** 2 - ((y - cy) / ry) ** 2)
            col = col * (1 - w) + np.array(spot) * w
    return tuple(col)


def to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def jitter(col, rnd, amt=0.035):
    """Palette colours are sRGB; the colour attribute is linear."""
    k = 1 + rnd.uniform(-amt, amt)
    return tuple(to_linear(min(1.0, ch * k)) for ch in col) + (1.0,)


def face_colours(ob, rnd, fixed=None):
    me = ob.data
    attr = me.color_attributes.get("Col") or me.color_attributes.new("Col", "FLOAT_COLOR", "FACE")
    lips = me.attributes.get("lips")
    ez = me.attributes.get("ear_zone")
    for p in me.polygons:
        if ez:
            base = EAR_ZONE[ez.data[p.index].value]
        elif fixed:
            base = fixed
        else:
            lt = lips.data[p.index].value if lips else 0
            base = region_colour(hc(p.center), lt)
        attr.data[p.index].color = jitter(base, rnd)
    me.color_attributes.active_color = attr


def colour_material():
    m = bpy.data.materials.new("FaceColour")
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    a = nt.nodes.new("ShaderNodeAttribute")
    a.attribute_name = "Col"
    nt.links.new(a.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.7
    if "Subsurface Weight" in bsdf.inputs:
        bsdf.inputs["Subsurface Weight"].default_value = 0.05
    return m


def light(name, kind, loc, target, energy, size=0.3, color=(1, 1, 1)):
    ld = bpy.data.lights.new(name, kind)
    ld.energy = energy
    ld.color = color
    if kind == "AREA":
        ld.size = size
    ob = bpy.data.objects.new(name, ld)
    bpy.context.collection.objects.link(ob)
    ob.location = loc
    ob.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return ob


def setup_scene():
    sc = bpy.context.scene
    for eng in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try:
            sc.render.engine = eng
            break
        except TypeError:
            continue
    w = bpy.data.worlds.new("w")
    w.use_nodes = True
    bg = w.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = (0.045, 0.047, 0.052, 1)
    bg.inputs["Strength"].default_value = 1.0
    sc.world = w
    sc.view_settings.view_transform = "AgX" if "AgX" in [i.identifier for i in
                                                          sc.view_settings.bl_rna.properties["view_transform"].enum_items] else "Filmic"
    t = (0, 0, -0.04)
    light("Key", "AREA", (0.55, -0.75, 0.35), t, 22, 0.6, (1.0, 0.95, 0.88))
    light("Fill", "AREA", (-0.7, -0.5, 0.0), t, 6, 0.8, (0.85, 0.9, 1.0))
    light("Rim", "AREA", (-0.2, 0.8, 0.45), t, 18, 0.5)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    cam.data.lens = 85
    bpy.context.collection.objects.link(cam)
    sc.camera = cam
    return sc, cam


def shoot(sc, cam, path, pos, target, res):
    sc.render.resolution_x, sc.render.resolution_y = res
    cam.location = Vector(pos)
    cam.rotation_euler = (Vector(target) - Vector(pos)).to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    return path


def sheet(paths, out):
    imgs = [bpy.data.images.load(p) for p in paths]
    w, h = imgs[0].size
    arr = np.zeros((h, w * len(imgs), 4), dtype=np.float32)
    for i, im in enumerate(imgs):
        arr[:, i * w:(i + 1) * w] = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)
    img = bpy.data.images.new(os.path.basename(out), w * len(imgs), h, alpha=True)
    img.pixels = arr.ravel()
    img.filepath_raw = out
    img.file_format = "PNG"
    img.save()


def main():
    bpy.ops.wm.open_mainfile(filepath=SRC)
    for ob in [o for o in bpy.data.objects if o.type in ("CAMERA", "LIGHT")]:
        bpy.data.objects.remove(ob)
    rnd = random.Random(7)
    mat = colour_material()
    for ob in [o for o in bpy.data.objects if o.type == "MESH"]:
        fixed = BROW if ob.name.startswith("Eyebrow") else WARM if ob.name.startswith("Ear") else None
        face_colours(ob, rnd, fixed)
        ob.data.materials.clear()
        ob.data.materials.append(mat)
        for p in ob.data.polygons:
            p.use_smooth = False
            p.material_index = 0
    sc, cam = setup_scene()
    # PAINT_TGT_Z / PAINT_DIST frame a bigger part (bust: -0.35 / 2.0); defaults frame the head
    tgt = (0, 0, float(os.environ.get("PAINT_TGT_Z", "-0.05")))
    d = float(os.environ.get("PAINT_DIST", "0.95"))
    h = tgt[2]
    views = {"front": (0, -d, h + 0.02), "34": (d * 0.62, -d * 0.78, h + 0.03), "side": (d, 0, h + 0.02),
             "back": (-d * 0.35, d * 0.94, h + 0.04)}
    p = lambda n: os.path.join(REN, f"game_{TAG}_{n}.png")
    sheet([shoot(sc, cam, p(n), v, tgt, (700, 820)) for n, v in views.items()], p("sheet"))
    close = {"mouth": ((0.0, -0.32, -0.065), (0, 0, -0.07)), "face34": ((0.2, -0.36, 0.0), (0, 0, -0.03)),
             "ear": ((0.30, -0.10, 0.02), (0.072, 0.02, -0.005)), "ear_back": ((0.22, 0.22, 0.02), (0.072, 0.02, -0.005))}
    sheet([shoot(sc, cam, p(n), pos, t, (800, 800)) for n, (pos, t) in close.items()], p("close_sheet"))
    out = os.path.join(ROOT, os.environ.get("PAINT_OUT", r"output\head-game\template"))
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out, f"head_{TAG}.blend"))
    bpy.ops.export_scene.gltf(filepath=os.path.join(out, f"head_{TAG}.glb"),
                              export_format="GLB")
    print("PAINT_DONE", TAG)


if __name__ == "__main__":
    main()
