# "Big triangle" low-poly style: fewer, larger flat triangles made from the approved baseline head.
#   BIG_TRIS=300 BIG_TAG=big300 blender -b --factory-startup -P tools/blender/head_bigtri.py
# Symmetric edge-collapse (QEM) on the head with the lips, mouth slot, eye rings and nose tip protected by a
# vertex group (inverted: protected vertices never collapse), so the face keeps its mouth and eye shape while cheeks/skull become big facets.
# Ears are reduced by BIG_EAR ratio, brows are kept.
import bpy
import json
import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import head_template as T  # noqa: E402
import head_topo_lab as L  # noqa: E402

ROOT = r"C:\Mirza Personal\model 3d maker"
SRC = os.path.join(ROOT, os.environ.get("BIG_SRC", r"output\head-game\template\head_baseline.blend"))
TARGET = int(os.environ.get("BIG_TRIS", "300"))
EAR_RATIO = float(os.environ.get("BIG_EAR", "0.6"))
PROTECT = float(os.environ.get("BIG_PROTECT", "8"))  # vertex group factor: how strongly protected verts resist
TAG = os.environ.get("BIG_TAG", f"big{TARGET}")
OUT = os.path.join(ROOT, r"output\head-game\template")


def tri_count(ob):
    return sum(len(p.vertices) - 2 for p in ob.data.polygons)


def protect_group(ob):
    """Vertices of the lips/mouth faces and the eye-socket area get weight 1."""
    me = ob.data
    keep = set()
    lips = me.attributes.get("lips")
    if lips:
        for p in me.polygons:
            if lips.data[p.index].value >= 1:
                keep.update(p.vertices)
    co = L.mesh_arrays(ob)
    h = L.to_head(co)
    x, y, z = np.abs(h[:, 0]), h[:, 1], h[:, 2]
    eye = (x > 0.012) & (x < 0.05) & (y > -0.016) & (y < 0.022) & (z > 0.04)  # eye ring and socket
    nose = (x < 0.012) & (y < -0.02) & (y > -0.05) & (z > 0.07)  # nose tip and wings
    keep.update(np.nonzero(eye | nose)[0].tolist())
    g = ob.vertex_groups.new(name="keep")
    g.add(sorted(keep), 1.0, "REPLACE")
    return g


def decimate(ob, ratio, group=None):
    m = ob.modifiers.new("dec", "DECIMATE")
    m.decimate_type = "COLLAPSE"
    m.ratio = ratio
    m.use_symmetry = True
    m.symmetry_axis = "X"
    m.use_collapse_triangulate = True
    if group:
        # in Blender's collapse the group marks what MAY collapse (weight 0 = never), so invert it
        m.vertex_group = group.name
        m.invert_vertex_group = True
        m.vertex_group_factor = PROTECT
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.modifier_apply(modifier=m.name)


def main():
    bpy.ops.wm.open_mainfile(filepath=SRC)
    head = bpy.data.objects["Head_Main"]
    base = tri_count(head)
    g = protect_group(head)
    # the modifier ratio counts faces of the input; search the ratio that lands on the triangle target
    lo, hi = 0.02, 1.0
    keep_me = head.data.copy()
    for _ in range(14):
        mid = (lo + hi) / 2
        head.data = keep_me.copy()
        decimate(head, mid, g)
        if tri_count(head) > TARGET:
            hi = mid
        else:
            lo = mid
    head.data = keep_me.copy()
    decimate(head, lo, g)
    ear = bpy.data.objects.get("Ears")
    if ear:
        bpy.ops.object.select_all(action="DESELECT")
        bm_ratio = EAR_RATIO
        decimate(ear, bm_ratio)
    for ob in [o for o in bpy.data.objects if o.type == "MESH"]:
        for p in ob.data.polygons:
            p.use_smooth = False
    c = np.array([tuple(p.center) for p in head.data.polygons])
    d = np.abs(T.SDF(L.to_head(c))) * 1000
    st = {"head_tris_before": base, "head_tris": tri_count(head), "ratio": round(lo, 4),
          "ears_tris": tri_count(ear) if ear else 0, "fit_mm_mean_p95": [round(float(d.mean()), 3),
                                                                        round(float(np.percentile(d, 95)), 3)],
          "has_lips_attr": "lips" in head.data.attributes}
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, f"head_{TAG}.blend"))
    json.dump(st, open(os.path.join(OUT, f"stats_{TAG}.json"), "w"), indent=1)
    print("BIG_STATS", json.dumps(st))


if __name__ == "__main__":
    main()
