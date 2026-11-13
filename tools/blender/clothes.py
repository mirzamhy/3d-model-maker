# Modular clothes for a rigged ref_body character (rig_game.py done): each garment is a copy of the body faces it
# covers (picked by the "part" / "ring" face labels ref_body.py writes), pushed out along the body normals, given a
# thin wall (Solidify, closed), coloured per face, and skinned with the body's own weights (copied vertex by vertex,
# so it bends exactly like the skin under it). Box modeling as in the Rozi 3D tutorial (duplicate faces + Solidify).
#   blender -b <rigged.blend> --factory-startup -P tools/blender/clothes.py -- --out <dressed.blend> [--set basic]
# Garment vertices keep "src" (body vertex index): tools/qa/deform_test.py checks the body never pokes through.
import argparse
import json
import os
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Vector

TRUNK, NECK, ARM, HAND, FINGER, THUMB, LEG, CROTCH = 1, 2, 3, 4, 5, 6, 7, 8
WALL = 0.004  # garment wall thickness (m), inward from the outer surface

# garment: faces as {part: (first ring, last ring)}, offset (m) per (part, ring) -> function, colour (sRGB)
# trunk bands 0-9 (neck base -> crotch), arm bands 0-7 (root -> wrist), leg bands 0-13 (crotch -> toe, 10-13 = foot)
SETS = {
    "basic": [
        {"name": "Shirt", "faces": {TRUNK: (0, 8), ARM: (0, 1)}, "colour": (0.36, 0.38, 0.26),
         "offset": lambda part, ring: 0.012 if part == TRUNK else 0.010},
        {"name": "Pants", "faces": {TRUNK: (7, 9), CROTCH: (0, 0), LEG: (0, 8)}, "colour": (0.50, 0.45, 0.33),
         # cargo: loose on the thigh and shin, snug at the waist (under the shirt) and tucked at the boot top
         # (knee bands 3-5 snug: a loose wall flipped at the outer knee in the squat)
         "offset": lambda part, ring: 0.007 if part != LEG else (0.006 if ring >= 7 else 0.009 if 3 <= ring <= 5 else 0.013),
         # cargo pockets: the outer side faces of the mid thigh stand out
         "bump": lambda part, ring, p: 0.012 if part == LEG and ring in (1, 2) and p.normal.x * p.center.x > 0
         and abs(p.normal.x) > 0.6 else 0.0},
        {"name": "Boots", "faces": {LEG: (7, 13)}, "colour": (0.25, 0.17, 0.11), "sole": (0.12, 0.10, 0.09),
         "offset": lambda part, ring: 0.012},
    ],
}
# loft: the shirt has its own shape (garment_loft.py: drape, ease, collar rib, hem band, cuffs); pants / boots as basic
SETS["loft"] = [{"name": "Shirt", "builder": "shirt_loft"}] + SETS["basic"][1:]
# female survivor f2 (notes/parts/survivor-cewek.md): fitted olive tee with a short sleeve, brown cargo, grey rubber
# boots. Shirt heights from the female sheet (armpit 1.254, bust 1.19, hem 0.93), arm root x 0.246.
SETS["loft_f"] = [{"name": "Shirt", "builder": "shirt_loft", "shirt": dict(
    hem_z=0.94, chest_z=1.20, armpit_z=1.254, waist_z=1.12, belly_z=1.02, fit=0.75,
    shoulder_ease=0.006, chest_ease=0.010, belly_ease=0.018, hem_ease=0.026,
    sleeve_x=(0.14, 0.25, 0.29, 0.315, 0.335), sleeve_ease=(0.0, 0.016, 0.014, 0.014),
    colour=(0.40, 0.45, 0.28), band=(0.34, 0.38, 0.24))}] +     [dict(SETS["basic"][1], colour=(0.36, 0.26, 0.17),
          # baggy cargo: body_inset.py took 2.5-3.5 cm off the carved legs, the trousers put the volume back
          # v1 0.027 on the thigh read as riding breeches: thigh 0.014, knee 0.016, bunch above the boot 0.022
          offset=lambda part, ring: 0.007 if part != LEG else (0.008 if ring >= 7 else 0.022 if ring == 6
                                                              else 0.016 if 3 <= ring <= 5 else 0.014),
          bump=lambda part, ring, p: 0.022 if part == LEG and ring in (1, 2) and p.normal.x * p.center.x > 0
          and abs(p.normal.x) > 0.6 else 0.0),
     dict(SETS["basic"][2], colour=(0.33, 0.33, 0.32), sole=(0.16, 0.16, 0.15), offset=lambda part, ring: 0.016)]

# female v2: brick red tee, dark blue jeans (slimmer than the cargo, no pockets), black boots
SETS["loft_f_v2"] = [{"name": "Shirt", "builder": "shirt_loft", "shirt": dict(
    SETS["loft_f"][0]["shirt"], colour=(0.58, 0.24, 0.18), band=(0.46, 0.18, 0.14))},
    dict(SETS["loft_f"][1], colour=(0.20, 0.25, 0.36),
         offset=lambda part, ring: 0.007 if part != LEG else (0.008 if ring >= 7 else 0.012 if ring == 6 else 0.010),
         bump=lambda part, ring, p: 0.0),
    dict(SETS["loft_f"][2], colour=(0.12, 0.11, 0.11), sole=(0.06, 0.06, 0.06))]

# female v3: charcoal tee with a short cap sleeve, khaki shorts to mid thigh (bare knee and shin), tall brown
# combat boots up the shin
SETS["loft_f_v3"] = [{"name": "Shirt", "builder": "shirt_loft", "shirt": dict(
    SETS["loft_f"][0]["shirt"], sleeve_x=(0.14, 0.25, 0.27, 0.285, 0.30),
    colour=(0.22, 0.23, 0.24), band=(0.15, 0.16, 0.17))},
    dict(SETS["loft_f"][1], name="Pants", faces={TRUNK: (7, 9), CROTCH: (0, 0), LEG: (0, 2)}, colour=(0.55, 0.48, 0.34),
         offset=lambda part, ring: 0.007 if part != LEG else 0.014, bump=lambda part, ring, p: 0.0),
    dict(SETS["loft_f"][2], faces={LEG: (6, 13)}, colour=(0.30, 0.20, 0.12), sole=(0.10, 0.08, 0.07),
         offset=lambda part, ring: 0.012 if ring <= 9 else 0.016)]

# female v4 (scavenger, gear.py adds pack / bandana / belt / pads): dark olive tee, grey cargo, brown boots
SETS["loft_f_v4"] = [{"name": "Shirt", "builder": "shirt_loft", "shirt": dict(
    SETS["loft_f"][0]["shirt"], colour=(0.30, 0.33, 0.22), band=(0.24, 0.27, 0.18))},
    dict(SETS["loft_f"][1], colour=(0.30, 0.30, 0.29)),
    dict(SETS["loft_f"][2], colour=(0.30, 0.20, 0.12), sole=(0.10, 0.08, 0.07))]

# f3: real armpit x 0.16 (ref_body RB_ARMPIT_X): the sleeve starts at the shoulder and ends where the sheet's sleeve
# ends (x ~0.24), not 9 cm further out
SETS["loft_f3"] = [{"name": "Shirt", "builder": "shirt_loft", "shirt": dict(
    SETS["loft_f"][0]["shirt"], sleeve_x=(0.10, 0.17, 0.20, 0.225, 0.242), fit=0.92)}] + SETS["loft_f"][1:]


def opts():
    p = argparse.ArgumentParser()
    p.add_argument("--out", required=True)
    p.add_argument("--set", default="basic")
    p.add_argument("--body", default="Character")
    p.add_argument("--keep-skin", action="store_true", help="keep the body faces under the clothes")
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    return p.parse_args(argv)


def lin(c):
    return tuple(ch ** 2.2 for ch in c) + (1.0,)


def garment(body, rig, spec, mat):
    me = body.data
    part = me.attributes["part"].data
    ring = me.attributes["ring"].data
    sel = []
    for p in me.polygons:
        pr = spec["faces"].get(part[p.index].value)
        if pr and pr[0] <= ring[p.index].value <= pr[1]:
            sel.append(p)
    # per body vertex: largest offset of the selected faces using it, normal from the selected faces only
    # (at the garment edge the normal must not lean toward the uncovered skin)
    off, nrm = {}, {}
    for p in sel:
        o = spec["offset"](part[p.index].value, ring[p.index].value)
        o += spec.get("bump", lambda pa_, ri_, p_: 0.0)(part[p.index].value, ring[p.index].value, p)
        for vi in p.vertices:
            off[vi] = max(off.get(vi, 0.0), o)
            nrm[vi] = nrm.get(vi, Vector()) + p.normal * p.area
    mw = body.matrix_world
    bm = bmesh.new()
    src = bm.verts.layers.int.new("src")
    vmap = {}
    for vi in off:
        n = nrm[vi].normalized()
        v = bm.verts.new(me.vertices[vi].co + n * off[vi])
        v[src] = vi
        vmap[vi] = v
    for p in sel:
        bm.faces.new([vmap[vi] for vi in p.vertices])
    edge_verts = {v[src] for e in bm.edges if e.is_boundary for v in e.verts}  # garment openings, body indices
    if spec.get("sole"):  # boot sole: not below the ground
        for v in bm.verts:
            if (mw @ v.co).z < 0.0:
                v.co = mw.inverted() @ Vector(((mw @ v.co).x, (mw @ v.co).y, 0.0))
    gm = bpy.data.meshes.new(spec["name"])
    bm.to_mesh(gm)
    bm.free()
    ob = bpy.data.objects.new(spec["name"], gm)
    bpy.context.scene.collection.objects.link(ob)
    ob.matrix_world = mw.copy()
    # weights: the body's, vertex by vertex
    names = {g.index: g.name for g in body.vertex_groups}
    groups = {}
    sa = gm.attributes["src"].data
    for v in gm.vertices:
        for g in me.vertices[sa[v.index].value].groups:
            n = names[g.group]
            if n not in groups:
                groups[n] = ob.vertex_groups.new(name=n)
            groups[n].add([v.index], g.weight, "REPLACE")
    # wall (closed shell); vertex groups and "src" are carried to the inner verts
    m = ob.modifiers.new("wall", "SOLIDIFY")
    m.thickness = WALL
    m.offset = -1.0
    m.use_rim = True
    m.use_even_offset = False  # even offset thickens sharp folds (crotch, heel): the inner wall went 12 mm into the skin
    m.thickness_clamp = 0.5  # and no wall thicker than half the shortest edge
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.modifier_apply(modifier="wall")
    # colour per face (FACE "Col", same material as the body), darker sole, slight jitter
    rnd = np.random.default_rng(len(spec["name"]))
    col = gm.color_attributes.new("Col", "FLOAT_COLOR", "FACE")
    for p in gm.polygons:
        base = spec["sole"] if spec.get("sole") and p.normal.z < -0.6 else spec["colour"]
        k = 1 + rnd.uniform(-0.04, 0.04)
        col.data[p.index].color = lin(tuple(min(1.0, c * k) for c in base))
    gm.color_attributes.active_color = col
    for p in gm.polygons:
        p.use_smooth = False
    gm.materials.append(mat)
    ob["qa_wall"] = WALL  # eval_model: the rim quads are this thin by design
    ob.parent = rig
    ob.matrix_world = mw.copy()
    am = ob.modifiers.new("Armature", "ARMATURE")
    am.object = rig
    tris = sum(len(p.vertices) - 2 for p in gm.polygons)
    return ob, {"faces_copied": len(sel), "triangles": tris}, ({p.index for p in sel}, edge_verts)


def hide_covered_skin(body, covers):
    """Delete body faces under clothes. covers: [(set of body face indices, set of garment boundary body verts)].
    A face goes when some garment covers it and none of its corners is on that garment's opening (the band just
    under a collar / sleeve / hem stays, so no hole shows from outside). Garment "src" indices are remapped
    (-1 = skin removed there). Returns faces removed."""
    me = body.data
    gone = set()
    for faces, edge_verts in covers:
        for fi in faces:
            if not any(v in edge_verts for v in me.polygons[fi].vertices):
                gone.add(fi)
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[bm.faces[i] for i in gone], context="FACES_ONLY")
    old = bm.verts.layers.int.new("_old")  # before taking vertex references: a new layer invalidates them
    for v in bm.verts:
        v[old] = v.index
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context="VERTS")
    bm.verts.index_update()
    remap = {v[old]: v.index for v in bm.verts}
    bm.verts.layers.int.remove(old)
    bm.to_mesh(me)
    bm.free()
    for ob in bpy.data.objects:
        a = ob.data.attributes.get("src") if ob.type == "MESH" and ob is not body else None
        if a is not None:
            for d in a.data:
                d.value = remap.get(d.value, -1)
    body["qa_open_ok"] = True
    return len(gone)


def main():
    a = opts()
    body = bpy.data.objects[a.body]
    rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    mat = body.data.materials[0] if body.data.materials else None
    st, covers = {}, []
    for spec in SETS[a.set]:
        if spec.get("builder") == "shirt_loft":
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            import garment_loft
            _, s, cov = garment_loft.shirt(body, rig, mat, spec.get("shirt"))
        else:
            _, s, cov = garment(body, rig, spec, mat)
        st[spec["name"]] = s
        covers.append(cov)
    if not a.keep_skin:
        st["skin_faces_removed"] = hide_covered_skin(body, covers)
        st["body_triangles"] = sum(len(p.vertices) - 2 for p in body.data.polygons)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(a.out))
    print("CLOTHES_STATS", json.dumps(st))


if __name__ == "__main__":
    main()
