# All-triangle version of the baseline head (game engines want triangles).
#   blender -b --factory-startup -P tools/blender/head_tri.py
#   TRI_SRC=output/head-game/template/head_baseline.blend TRI_METHOD=sdf|beauty|fixed TRI_TAG=tri ...
# A quad can be split along either diagonal. On a flat-shaded low-poly head the choice decides where the fold
# shows. Method "sdf": take the diagonal whose midpoint lies closer to the head SDF, so the fold follows the
# real surface (cheek bulges out, eye socket folds in). The SDF is symmetric, so both halves pick the mirrored
# diagonal. N-gons (ear) and quads off the SDF (ear, brows) use Blender's "beauty" split.
import bpy
import bmesh
import json
import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import head_template as T  # noqa: E402
import head_topo_lab as L  # noqa: E402

ROOT = r"C:\Mirza Personal\model 3d maker"
SRC = os.path.join(ROOT, os.environ.get("TRI_SRC", r"output\head-game\template\head_baseline.blend"))
METHOD = os.environ.get("TRI_METHOD", "sdf")
TAG = os.environ.get("TRI_TAG", f"tri_{METHOD}")
OUT = os.path.join(ROOT, r"output\head-game\template")


def sdf_at(pts_bl):
    return np.abs(T.SDF(L.to_head(np.array(pts_bl))))


def split_quads_sdf(bm):
    quads = [f for f in bm.faces if len(f.verts) == 4]
    pairs = []
    for f in quads:
        v = f.verts
        m0 = (v[0].co + v[2].co) / 2
        m1 = (v[1].co + v[3].co) / 2
        pairs.append((f, v, m0, m1))
    d = sdf_at([tuple(p[2]) for p in pairs] + [tuple(p[3]) for p in pairs])
    n = len(pairs)
    for i, (f, v, _, _) in enumerate(pairs):
        a, b = (v[0], v[2]) if d[i] <= d[n + i] else (v[1], v[3])
        bmesh.utils.face_split(f, a, b)


def triangulate(ob, use_sdf):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    if use_sdf:
        split_quads_sdf(bm)
    method = "FIXED" if METHOD == "fixed" else "BEAUTY"
    rest = [f for f in bm.faces if len(f.verts) > 3]
    bmesh.ops.triangulate(bm, faces=rest, quad_method=method, ngon_method="BEAUTY")
    bm.to_mesh(ob.data)
    bm.free()


def fit(ob):
    """Mean / p95 distance (mm) from triangle centroids to the SDF: how well the folds follow the surface."""
    c = np.array([tuple(p.center) for p in ob.data.polygons])
    d = sdf_at(c) * 1000
    return round(float(d.mean()), 3), round(float(np.percentile(d, 95)), 3)


def main():
    bpy.ops.wm.open_mainfile(filepath=SRC)
    st = {}
    for ob in [o for o in bpy.data.objects if o.type == "MESH"]:
        is_head = not (ob.name.startswith("Ear") or ob.name.startswith("Eyebrow"))
        triangulate(ob, use_sdf=is_head and METHOD == "sdf")
        for p in ob.data.polygons:
            p.use_smooth = False
        tris = len(ob.data.polygons)
        st[ob.name] = {"tris": tris, "all_tris": all(len(p.vertices) == 3 for p in ob.data.polygons)}
        if is_head:
            st[ob.name]["fit_mm_mean_p95"] = fit(ob)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, f"head_{TAG}.blend"))
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, f"head_{TAG}.glb"), export_format="GLB")
    json.dump(st, open(os.path.join(OUT, f"stats_{TAG}.json"), "w"), indent=1)
    print("TRI_STATS", json.dumps(st))


if __name__ == "__main__":
    main()
