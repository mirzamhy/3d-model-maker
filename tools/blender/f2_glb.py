# Rigged, coloured GLBs of the old and new F2 character for the web motion viewer (viewer/gerak.html).
#   blender -b --factory-startup -P tools/blender/f2_glb.py
# old = the F2 body as Three.js builds it (its own low-poly head), straight from the exported JSON.
# new = F2 body + template head (output of f2_assemble.py, coloured by head_paint.py).
# Both use the same 73-bone rig and head coordinates (eye level y = 0), so the viewer animates them identically.
# Colours go out as COLOR_0 (face colours, so the low-poly facets stay flat).
import bpy
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(__file__))
import f2_assemble as F  # noqa: E402
import head_paint as P  # noqa: E402

ROOT = F.ROOT
OUT = os.path.join(ROOT, r"output\head-game\f2")
NEW_SRC = os.path.join(ROOT, os.environ.get("F2_GLB_NEW", "output/head-game/f2/head_f2_male_v2_color.blend"))  # v2 = planar nose


def corner_colours():
    """The exporter only takes point/corner colours: copy each face colour to its corners."""
    for ob in [o for o in bpy.data.objects if o.type == "MESH"]:
        me = ob.data
        src = me.attributes.get("Col")
        if src is None or src.domain != "FACE":
            continue
        dst = me.color_attributes.new("Color", "BYTE_COLOR", "CORNER")
        for poly in me.polygons:
            c = src.data[poly.index].color
            for li in poly.loop_indices:
                    dst.data[li].color = c
        me.color_attributes.active_color = dst


def export(path):
    corner_colours()
    kw = dict(filepath=path, export_format="GLB", export_skins=True, export_animations=False)
    for opt in ({"export_vertex_color": "NAME", "export_vertex_color_name": "Color", "export_all_vertex_colors": False}, {"export_colors": True}, {}):
        try:
            bpy.ops.export_scene.gltf(**kw, **opt)
            return
        except TypeError:
            continue


def old_glb():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    d = json.load(open(F.JSON))
    verts = [F.to_bl(F.body_to_head(p)) for p in d["pos"]]
    me = bpy.data.meshes.new("F2_Old")
    me.from_pydata(verts, [], d["tris"])
    ob = bpy.data.objects.new("F2_Old", me)
    bpy.context.collection.objects.link(ob)
    names = [b["name"] for b in d["bones"]]
    for nm in names:
        ob.vertex_groups.new(name=nm)
    for i, w in enumerate(d["weights"]):
        for bi, val in w:
            ob.vertex_groups[names[bi]].add([i], val, "REPLACE")
    for p in me.polygons:
        p.use_smooth = False
    P.face_colours(ob, random.Random(7))
    me.materials.append(P.colour_material())
    rig = F.build_armature(d)
    ob.parent = rig
    ob.modifiers.new("Rig", "ARMATURE").object = rig
    export(os.path.join(OUT, "f2_old.glb"))


def new_glb():
    bpy.ops.wm.open_mainfile(filepath=NEW_SRC)
    for ob in [o for o in bpy.data.objects if o.type in ("CAMERA", "LIGHT")]:
        bpy.data.objects.remove(ob)
    export(os.path.join(OUT, "f2_new.glb"))


if __name__ == "__main__":
    old_glb()
    new_glb()
    print("GLB_DONE")
