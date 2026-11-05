# Shared helpers for the QA tools (eval_model, sheet, silhouette_iou, export_glb).
# Every tool runs inside Blender on the file that is open:
#   blender -b <file.blend> --factory-startup -P tools/qa/<tool>.py -- [options]
# Blender axes: x = character's left, -y = forward (character faces -y), z up, feet on z = 0.
import argparse
import json
import os
import sys

import bpy
import numpy as np
from mathutils import Vector

ROOT = r"C:\Mirza Personal\model 3d maker"
QA_OUT = os.path.join(ROOT, "output", "qa")


def args(description, add):
    """Parse the options after '--' on the Blender command line."""
    p = argparse.ArgumentParser(description=description)
    add(p)
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    return p.parse_args(argv)


def tag_of(a=None):
    """Output name: --tag, else the .blend file name."""
    if a is not None and getattr(a, "tag", None):
        return a.tag
    return os.path.splitext(os.path.basename(bpy.data.filepath))[0] or "untitled"


def meshes(skip_hidden=True):
    """Mesh objects that end up in the model (no cameras, lights, wire helpers)."""
    out = []
    for o in bpy.data.objects:
        if o.type != "MESH":
            continue
        if skip_hidden and (o.hide_render or o.name.startswith("_qa")):
            continue
        out.append(o)
    return out


def evaluated_mesh(ob):
    """Mesh with modifiers applied (mirror, solidify, armature in rest), in world space. Caller frees it."""
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev, depsgraph=dg)
    me.transform(ob.matrix_world)
    return me


def world_bounds(objs):
    lo = np.full(3, np.inf)
    hi = np.full(3, -np.inf)
    for o in objs:
        for c in o.bound_box:
            p = np.array(o.matrix_world @ Vector(c))
            lo = np.minimum(lo, p)
            hi = np.maximum(hi, p)
    return lo, hi


def save_json(data, name):
    os.makedirs(QA_OUT, exist_ok=True)
    path = os.path.join(QA_OUT, name)
    with open(path, "w") as f:
        json.dump(data, f, indent=1)
    return path


def save_png(arr, path):
    """arr: (h, w, 3|4) float 0..1, row 0 = TOP of the picture."""
    h, w = arr.shape[:2]
    if arr.shape[2] == 3:
        arr = np.concatenate([arr, np.ones((h, w, 1), np.float32)], 2)
    img = bpy.data.images.new(os.path.basename(path), w, h, alpha=True)
    img.pixels = np.ascontiguousarray(arr[::-1], dtype=np.float32).ravel()  # Blender rows start at the bottom
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)


def load_png(path):
    """(h, w, 4) float, row 0 = TOP."""
    img = bpy.data.images.load(path)
    w, h = img.size
    a = np.array(img.pixels[:], np.float32).reshape(h, w, 4)[::-1]
    bpy.data.images.remove(img)
    return a


def set_engine(scene, name="BLENDER_WORKBENCH"):
    try:
        scene.render.engine = name
    except TypeError:
        pass


def ortho_camera(name="_qa_cam"):
    cam = bpy.data.objects.get(name)
    if cam is None:
        cam = bpy.data.objects.new(name, bpy.data.cameras.new(name))
        bpy.context.scene.collection.objects.link(cam)
    cam.data.type = "ORTHO"
    bpy.context.scene.camera = cam
    return cam


def aim(cam, pos, target, up=(0, 0, 1)):
    pos, target = Vector(pos), Vector(target)
    cam.location = pos
    cam.rotation_euler = (target - pos).to_track_quat("-Z", "Y").to_euler()


def render_to(path, w, h):
    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y = w, h
    sc.render.resolution_percentage = 100
    sc.render.filepath = path
    sc.render.image_settings.file_format = "PNG"
    bpy.ops.render.render(write_still=True)
    return path


# view name -> direction FROM the model TO the camera (Blender axes)
VIEWS = {
    "front": (0, -1, 0),
    "right": (-1, 0, 0),   # character's right side (x = left, so right = -x)
    "back": (0, 1, 0),
    "left": (1, 0, 0),
    "34": (-0.7071, -0.7071, 0),
}
