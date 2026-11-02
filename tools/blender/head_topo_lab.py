# Topology lab for the eyeless game head: same shape, same triangle budget, different meshing methods.
#   blender -b --factory-startup -P tools/blender/head_topo_lab.py
#   LAB_METHODS=quadriflow,planar LAB_TRIS=900 blender -b ...
#
# Methods (all start from the same dense voxel mesh built by head_game.dense_body):
#   collapse   : current pipeline. Keep x >= 0, edge-collapse decimate, mirror. Triangles follow curvature.
#   quadriflow : QuadriFlow quad remesh (Huang et al. 2018, built into Blender). Quads in loops along the form.
#   planar     : collapse to a higher budget, then planar dissolve (merge near-coplanar faces into big planes),
#                then triangulate. Aims at the "few large tilted planes" look of the reference low-poly packs.
#   sharp      : Blender Remesh "Sharp" (octree dual contouring) before collapse. Keeps creases crisp.
# Every result is mirror-symmetric, closed-checked and scored against the SDF:
#   dev_mm_mean / dev_mm_p95 : |SDF| at face centres and vertices, in mm (how far the low mesh is from the true shape)
#   aspect_p90               : 90th percentile triangle aspect ratio (longest edge / shortest altitude, 1.15 = equilateral)
#   planes                   : number of face groups whose normals differ by < 3 deg from a neighbour (fewer = bigger planes)
# Output: output/head-game/lab/<method>.{blend,glb}, lab_stats.json, renders/lab_<method>_{sheet,wire_sheet}.png
import bpy
import bmesh
import json
import math
import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("HEAD_EYELESS", "1")
import head_lowpoly as H  # noqa: E402
import head_game as G  # noqa: E402

LAB = os.path.join(G.OUT, "lab")
os.makedirs(LAB, exist_ok=True)
TRIS = int(os.environ.get("LAB_TRIS", "900"))
METHODS = os.environ.get("LAB_METHODS", "collapse,quadriflow,planar,sharp").split(",")


def full_sdf(p):
    """Whole Head_Main shape in head coordinates: head + neck, both ears, shoulder base."""
    d = G.head_only_sdf(p)
    q = p.copy()
    q[:, 0] = np.abs(q[:, 0])  # ears are mirrored
    d = np.minimum(d, H.ear_sdf(q))
    return np.minimum(d, G.shoulders_sdf(p))


def mesh_arrays(ob):
    me = ob.data
    co = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    return co


def to_head(co):
    return np.stack([co[:, 0], co[:, 2], -co[:, 1]], axis=1)


def deviation(ob):
    co = mesh_arrays(ob)
    cen = np.array([p.center for p in ob.data.polygons])
    pts = to_head(np.vstack([co, cen]))
    d = np.abs(full_sdf(pts)) * 1000
    return float(d.mean()), float(np.percentile(d, 95))


def aspect_p90(ob):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    r = []
    for f in bm.faces:
        a, b, c = (v.co for v in f.verts)
        e = [(b - a).length, (c - b).length, (a - c).length]
        area = f.calc_area()
        if area < 1e-12:
            r.append(99.0)
            continue
        r.append(max(e) / (2 * area / max(e)))
    bm.free()
    return float(np.percentile(r, 90))


def planes(ob, deg=3.0):
    """Flood-fill faces whose normal is within `deg` of a neighbour: count of flat regions."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.faces.ensure_lookup_table()
    cos = math.cos(math.radians(deg))
    seen = set()
    groups = 0
    for f in bm.faces:
        if f.index in seen:
            continue
        groups += 1
        stack = [f]
        seen.add(f.index)
        while stack:
            g = stack.pop()
            for e in g.edges:
                for h in e.link_faces:
                    if h.index not in seen and g.normal.dot(h.normal) > cos:
                        seen.add(h.index)
                        stack.append(h)
    bm.free()
    return groups


def keep_half(ob):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(0, 0, 0), plane_no=(1, 0, 0), clear_inner=True)
    bm.to_mesh(ob.data)
    bm.free()


def mirror_weld(ob, triangulate=True):
    """Half mesh (x >= 0, open on x = 0) -> mirrored, welded, closed. Same as head_game but quads optional."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    seam = {v for e in bm.edges if e.is_boundary for v in e.verts}
    for v in bm.verts:
        if v in seam or v.co.x < 0:
            v.co.x = 0.0
    m = bmesh.ops.duplicate(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:])
    for g in m["geom"]:
        if isinstance(g, bmesh.types.BMVert):
            g.co.x = -g.co.x
    bmesh.ops.reverse_faces(bm, faces=[g for g in m["geom"] if isinstance(g, bmesh.types.BMFace)])
    bmesh.ops.remove_doubles(bm, verts=[v for v in bm.verts if abs(v.co.x) < 1e-7], dist=1e-6)
    if triangulate:
        bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(ob.data)
    bm.free()


def tri_count(ob):
    return sum(len(p.vertices) - 2 for p in ob.data.polygons)


def collapse(ob, tris_half):
    dec = ob.modifiers.new("decimate", "DECIMATE")
    dec.decimate_type = "COLLAPSE"
    dec.ratio = min(1.0, tris_half / tri_count(ob))
    dec.use_collapse_triangulate = True
    G.apply_modifier(ob, dec)


def m_collapse(ob):
    keep_half(ob)
    collapse(ob, TRIS / 2)
    mirror_weld(ob)


def m_sharp(ob):
    rm = ob.modifiers.new("remesh", "REMESH")
    rm.mode = "SHARP"  # octree dual contouring
    rm.octree_depth = 8
    rm.scale = 0.99
    rm.sharpness = 1.0
    rm.use_remove_disconnected = True
    G.apply_modifier(ob, rm)
    keep_half(ob)
    collapse(ob, TRIS / 2)
    mirror_weld(ob)


def m_planar(ob):
    """Collapse to a richer mesh, dissolve near-flat regions into planes, retriangulate; tune angle to hit budget."""
    keep_half(ob)
    collapse(ob, TRIS * 1.4 / 2)
    base = ob.data.copy()
    best = None
    for ang in (2, 3, 4, 5, 6, 7, 8, 10, 12):
        ob.data = base.copy()
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        boundary = [e for e in bm.edges if e.is_boundary]
        inner = [e for e in bm.edges if not e.is_boundary]
        bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(ang), use_dissolve_boundaries=False,
                                 verts=[v for v in bm.verts if not any(e.is_boundary for e in v.link_edges)],
                                 edges=inner, delimit=set())
        # beauty triangulation keeps the big n-gons as fans of fairly even triangles
        bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method="BEAUTY", ngon_method="BEAUTY")
        bm.to_mesh(ob.data)
        bm.free()
        t = tri_count(ob) * 2
        best = (ang, t)
        if t <= TRIS:
            break
    print(f"LAB planar angle {best[0]} deg -> {best[1]} tris")
    mirror_weld(ob)


def m_quadriflow(ob):
    """QuadriFlow on the whole closed mesh (it needs a closed manifold), then make exact symmetry by mirroring."""
    # straight from the voxel remesh QuadriFlow refuses ("needs to be manifold"); a collapse pass first fixes it
    dec = ob.modifiers.new("pre", "DECIMATE")
    dec.ratio = 30000 / len(ob.data.polygons)
    G.apply_modifier(ob, dec)
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    target = TRIS // 2  # quads; each becomes 2 triangles
    res = bpy.ops.object.quadriflow_remesh(use_mesh_symmetry=True, use_preserve_sharp=True,
                                           use_preserve_boundary=False, smooth_normals=False,
                                           mode="FACES", target_faces=target, seed=0)
    print("LAB quadriflow", res, len(ob.data.polygons), "faces")
    # quadriflow symmetry is approximate: keep x >= 0 and mirror, keeping quads where possible
    keep_half(ob)
    mirror_weld(ob, triangulate=False)


def m_qf_collapse(ob):
    """Hybrid: dense QuadriFlow (even, loop-aligned triangles) then curvature-driven collapse to the budget."""
    global TRIS
    budget = TRIS
    TRIS = budget * 5  # QuadriFlow pass at 5x the final budget
    m_quadriflow(ob)
    TRIS = budget
    keep_half(ob)
    collapse(ob, TRIS / 2)
    mirror_weld(ob)


# ---------- surface snapping, density warp, cleanup ----------
def sdf_grad(p, h=1e-4):
    g = np.zeros_like(p)
    for i in range(3):
        e = np.zeros(3)
        e[i] = h
        g[:, i] = (full_sdf(p + e) - full_sdf(p - e)) / (2 * h)
    return g


def snap_points(p, iters=5):
    """Newton steps along the SDF gradient: every point lands on the true surface."""
    for _ in range(iters):
        d = full_sdf(p)
        g = sdf_grad(p)
        p = p - (d / np.maximum((g * g).sum(1), 1e-9))[:, None] * g
    return p


def set_co(ob, co):
    ob.data.vertices.foreach_set("co", co.ravel())
    ob.data.update()


def snap(ob, keep_seam=True):
    co = mesh_arrays(ob)
    p = snap_points(to_head(co))
    new = np.stack([p[:, 0], -p[:, 2], p[:, 1]], axis=1)
    if keep_seam:
        new[np.abs(co[:, 0]) < 1e-7, 0] = 0.0
    set_co(ob, new)


# radial density warps (head coords): (centre, radius, strength). Local scale near the centre is 1 + a, so
# QuadriFlow, which spreads quads evenly by area, puts ~(1 + a)^2 times more quads there. a < 2.2 keeps it one-to-one.
_e = lambda k, d: float(os.environ.get(k, d))
FACE_W = (H.V(0, _e("LAB_FACE_Y", "-0.03"), 0.07), _e("LAB_FACE_R", "0.055"), _e("LAB_FACE_A", "1.3"))
EAR_W = (H.EAR_C, _e("LAB_EAR_R", "0.028"), _e("LAB_EAR_A", "0.9"))


def _radial(p, c, R, a, inverse=False):
    v = p - c
    r = np.linalg.norm(v, axis=1)
    if not inverse:
        s = 1 + a * np.exp(-(r / R) ** 2)
        return c + v * s[:, None]
    lo, hi = np.zeros_like(r), r.copy()  # solve f(t) = r, f(t) = t (1 + a e^{-(t/R)^2}) is monotone
    for _ in range(50):
        mid = (lo + hi) / 2
        f = mid * (1 + a * np.exp(-(mid / R) ** 2))
        lo, hi = np.where(f < r, mid, lo), np.where(f < r, hi, mid)
    t = (lo + hi) / 2
    return c + v * (t / np.maximum(r, 1e-12))[:, None]


def warp_chain():
    c, R, a = FACE_W
    ec, eR, ea = EAR_W
    ecw = _radial(ec[None], c, R, a)[0]  # ear centres as they sit after the face warp
    ecw2 = ecw * np.array([-1, 1, 1])
    return [(c, R, a), (ecw, eR, ea), (ecw2, eR, ea)]


def warp(ob, inverse=False):
    co = mesh_arrays(ob)
    p = to_head(co)
    chain = warp_chain()
    for c, R, a in (reversed(chain) if inverse else chain):
        p = _radial(p, c, R, a, inverse)
    set_co(ob, np.stack([p[:, 0], -p[:, 2], p[:, 1]], axis=1))


def m_qf_warp(ob):
    """QuadriFlow on a density-warped copy: more quads on face and ears, even quads elsewhere."""
    dec = ob.modifiers.new("pre", "DECIMATE")
    dec.ratio = 30000 / len(ob.data.polygons)
    G.apply_modifier(ob, dec)
    warp(ob)
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    res = bpy.ops.object.quadriflow_remesh(use_mesh_symmetry=True, use_preserve_sharp=False,
                                           use_preserve_boundary=False, smooth_normals=False,
                                           mode="FACES", target_faces=TRIS // 2, seed=0)
    print("LAB qf_warp", res, len(ob.data.polygons), "faces")
    warp(ob, inverse=True)
    snap(ob, keep_seam=False)
    keep_half(ob)
    mirror_weld(ob, triangulate=False)
    snap(ob)


def relax_tangent(bm, lam=0.5):
    """Move each vertex toward its neighbours' average, only along its tangent plane (keeps the shape)."""
    new = {}
    for v in bm.verts:
        if not v.link_edges:
            continue
        avg = sum((e.other_vert(v).co for e in v.link_edges), v.co * 0) / len(v.link_edges)
        d = avg - v.co
        n = v.normal
        d = d - n * d.dot(n)
        new[v] = v.co + d * lam
    for v, c in new.items():
        if abs(v.co.x) < 1e-7:
            c.x = 0.0
        v.co = c


def m_collapse_clean(ob):
    """Collapse, then fix slivers and dents: snap to surface, flip bad edges, relax along the surface, snap."""
    keep_half(ob)
    collapse(ob, TRIS / 2)
    snap(ob)
    for _ in range(3):
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        bm.normal_update()
        # flip only edges between nearly coplanar faces, so creases (nose ridge, lip line) are not touched
        flat_edges = [e for e in bm.edges if len(e.link_faces) == 2
                      and e.link_faces[0].normal.angle(e.link_faces[1].normal, 0) < math.radians(18)]
        bmesh.ops.beautify_fill(bm, faces=bm.faces[:], edges=flat_edges)
        relax_tangent(bm, 0.45)
        bm.to_mesh(ob.data)
        bm.free()
        snap(ob)
    mirror_weld(ob)
    snap(ob)


def m_collapse_soft(ob):
    """Like collapse_clean, but feature vertices (any edge folding > 30 deg) stay where the collapse put them,
    and nothing is snapped: the collapse already places vertices well. Only flat areas are evened out."""
    keep_half(ob)
    collapse(ob, TRIS / 2)
    for _ in range(2):
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        bm.normal_update()
        fold = lambda e: (e.link_faces[0].normal.angle(e.link_faces[1].normal, 0)
                          if len(e.link_faces) == 2 else math.pi)
        flat_edges = [e for e in bm.edges if fold(e) < math.radians(12)]
        bmesh.ops.beautify_fill(bm, faces=bm.faces[:], edges=flat_edges)
        bm.normal_update()
        locked = {v for v in bm.verts if any(fold(e) > math.radians(30) for e in v.link_edges)}
        before = {v: v.co.copy() for v in locked}
        relax_tangent(bm, 0.35)
        for v, c in before.items():
            v.co = c
        bm.to_mesh(ob.data)
        bm.free()
    # pull relaxed (unlocked) vertices back onto the surface; locked ones are untouched
    co = mesh_arrays(ob)
    snapped = np.stack([(p := snap_points(to_head(co)))[:, 0], -p[:, 2], p[:, 1]], axis=1)
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.normal_update()
    bm.verts.ensure_lookup_table()
    feat = np.array([any(len(e.link_faces) == 2 and e.link_faces[0].normal.angle(e.link_faces[1].normal, 0)
                         > math.radians(30) for e in v.link_edges) for v in bm.verts])
    bm.free()
    new = np.where(feat[:, None], co, snapped)
    new[np.abs(co[:, 0]) < 1e-7, 0] = 0.0
    set_co(ob, new)
    mirror_weld(ob)


def dihedral_p95(ob):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bm.normal_update()
    a = [math.degrees(e.link_faces[0].normal.angle(e.link_faces[1].normal, 0)) for e in bm.edges if len(e.link_faces) == 2]
    bm.free()
    return float(np.percentile(a, 95))


def slivers(ob, limit=8.0):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    n = 0
    for f in bm.faces:
        a, b, c = (v.co for v in f.verts)
        e = max((b - a).length, (c - b).length, (a - c).length)
        area = f.calc_area()
        if area < 1e-12 or e * e / (2 * area) > limit:
            n += 1
    bm.free()
    return n


def quad_share(ob):
    q = sum(1 for p in ob.data.polygons if len(p.vertices) == 4)
    return round(q / max(1, len(ob.data.polygons)), 3)


def run(method):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    ob = G.dense_body()
    ob.name = ob.data.name = "Head_Main"
    globals()["m_" + method](ob)
    quads = quad_share(ob)
    G.paint_lips(ob)
    brows = [G.eyebrow("Eyebrow_L", 1, ob), G.eyebrow("Eyebrow_R", -1, ob)]
    for o in (ob, *brows):
        G.flat(o)
    mean, p95 = deviation(ob)
    st = {"method": method, "head": G.stats(ob), "quad_share": quads, "closed": G.closed(ob),
          "symmetry": G.symmetry(ob), "dev_mm_mean": round(mean, 3), "dev_mm_p95": round(p95, 3),
          "aspect_p90": round(aspect_p90(ob), 2), "planes": planes(ob), "slivers": slivers(ob),
          "dihedral_p95": round(dihedral_p95(ob), 1)}
    print("LAB_STATS " + json.dumps(st))
    G.render_all("lab_" + method, [ob, *brows])
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(LAB, f"{method}.blend"))
    bpy.ops.export_scene.gltf(filepath=os.path.join(LAB, f"{method}.glb"), export_format="GLB")
    return st


if __name__ == "__main__":
    path = os.path.join(LAB, "lab_stats.json")
    allst = json.load(open(path)) if os.path.exists(path) else {}
    for m in METHODS:
        m = m.strip()
        allst[m] = run(m)
        with open(path, "w") as f:
            json.dump(allst, f, indent=2)
