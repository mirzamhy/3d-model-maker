# Export the open .blend to .glb for three.js / game engines, then reopen the .glb and check it.
#   blender -b <file.blend> --factory-startup -P tools/qa/export_glb.py -- [--out path.glb] [--tag NAME] [--anim]
# Steps: face colours (attribute "Col", FACE domain) are copied to a CORNER colour layer, because the glTF exporter
# only reads point/corner colours. Modifiers are applied in the export, the exporter triangulates.
# The .blend on disk is never saved. Check: same triangle count after reimport, colours present, skin present when
# the source had an armature. Default output: output/qa/<tag>.glb
import json
import os
import struct
import sys

import bpy

sys.path.insert(0, os.path.dirname(__file__))
import qa_common as Q  # noqa: E402


def opts(p):
    p.add_argument("--out", default="")
    p.add_argument("--tag", default="")
    p.add_argument("--anim", action="store_true")


def corner_colours():
    """Copy each FACE colour attribute to a CORNER layer named 'Color' and make it active."""
    n = 0
    for ob in Q.meshes():
        me = ob.data
        src = next((at for at in me.attributes if at.domain == "FACE" and at.data_type in ("FLOAT_COLOR", "BYTE_COLOR")),
                   None)
        if src is None or "Color" in me.color_attributes:
            continue
        dst = me.color_attributes.new("Color", "BYTE_COLOR", "CORNER")
        for poly in me.polygons:
            c = src.data[poly.index].color
            for li in poly.loop_indices:
                dst.data[li].color = c
        me.color_attributes.active_color = dst
        try:
            me.color_attributes.render_color_index = me.color_attributes.find("Color")
        except (AttributeError, TypeError):
            pass
        n += 1
    return n


def expected_triangles():
    total = 0
    for ob in Q.meshes():
        me = Q.evaluated_mesh(ob)
        total += sum(len(p.vertices) - 2 for p in me.polygons)
        bpy.data.meshes.remove(me)
    return total


def export(path, anim=False):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    for ob in Q.meshes():
        ob.select_set(True)
        arm = ob.find_armature()
        if arm:
            arm.select_set(True)
    props = {p.identifier for p in bpy.ops.export_scene.gltf.get_rna_type().properties}
    kw = dict(filepath=path, export_format="GLB", use_selection=True, export_apply=True)
    # "NAME" + "Color": the layer corner_colours() makes ("ACTIVE" silently wrote no COLOR_0 in Blender 5.2)
    want = {"export_skins": True, "export_animations": anim, "export_vertex_color": "NAME",
            "export_vertex_color_name": "Color", "export_all_vertex_colors": False, "export_colors": True,
            "export_yup": True}
    kw.update({k: v for k, v in want.items() if k in props})
    bpy.ops.export_scene.gltf(**kw)


def round_trip(path, anim=False):
    """Export, reopen in an empty scene, compare. Leaves Blender with only the imported glb loaded."""
    has_arm = any(ob.find_armature() for ob in Q.meshes())
    n_col = corner_colours()
    want = expected_triangles()
    export(path, anim)
    size = os.path.getsize(path)
    # colours and skin: read the glTF JSON chunk itself (the importer may drop COLOR_0)
    with open(path, "rb") as f:
        raw = f.read()
    n_json = struct.unpack("<I", raw[12:16])[0]
    gl = json.loads(raw[20:20 + n_json])
    prims = [p for m in gl.get("meshes", []) for p in m["primitives"]]
    colours = bool(prims) and all("COLOR_0" in p["attributes"] for p in prims)
    skinned = bool(gl.get("skins"))
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=path)
    # the importer adds a bone display shape (icosphere, 80 faces) for skinned files: not part of the model
    shapes = {pb.custom_shape for ob in bpy.data.objects if ob.type == "ARMATURE" for pb in ob.pose.bones if pb.custom_shape}
    got = sum(len(ob.data.polygons) for ob in bpy.data.objects if ob.type == "MESH" and ob not in shapes)
    ok = got == want and (colours or n_col == 0) and (skinned or not has_arm)
    return {"ok": ok, "path": path, "bytes": size, "triangles_expected": want, "triangles_glb": got,
            "colour_layers_made": n_col, "colours_in_glb": colours, "armature_expected": has_arm, "skinned_in_glb": skinned,
            "summary": f"{got}/{want} tris, colours {colours}, skin {skinned}, {size // 1024} KB"}


def main():
    a = Q.args("export glb + check", opts)
    tag = Q.tag_of(a)
    path = a.out or os.path.join(Q.QA_OUT, f"{tag}.glb")
    r = round_trip(path, a.anim)
    Q.save_json(r, f"{tag}_export.json")
    print(("QA PASS" if r["ok"] else "QA FAIL") + "  glb round trip: " + r["summary"])
    print("QA_DONE", path)


if __name__ == "__main__":
    main()
