"""Body under the clothes, from a body carved out of a CLOTHED silhouette (female sheet: baggy cargo trousers, boots).

ref_body.py carves the skin from the sheet silhouette. On a clothed sheet that silhouette is the cloth, so the legs
come out as thick as the trousers. Here the legs shrink toward their bone axis (hip -> knee -> ankle) and the hips /
waist toward the body axis, by factors that undo the cloth ease; the clothes (clothes.py loft) put the volume back.
Arms (bare under a short sleeve), chest (fitted tee), head untouched.
  blender -b <ref_body.blend> --factory-startup -P tools/blender/body_inset.py -- --joints <joints.json> --out <out.blend>
"""
import sys, json, argparse
import bpy
import numpy as np

TRUNK, LEG, CROTCH = 1, 7, 8
# leg: factor along the leg, t = 0 hip .. 1 ankle (reference cargo ~0.20 m wide at the thigh, 0.17 at the knee,
# bunching above a wide rubber boot)
LEG_T = [0.0, 0.3, 0.5, 0.8, 1.0, 1.25]
LEG_K = [0.86, 0.78, 0.68, 0.70, 0.80, 0.85]
# trunk: factor by height (m above ground): hips (trouser seat) .. waist .. chest (fitted tee: 1)
TRUNK_Y = [0.70, 0.86, 0.98, 1.08, 1.16]
TRUNK_K = [0.86, 0.88, 0.93, 0.97, 1.0]
TRUNK_KZ = TRUNK_K   # depth factor (same as width unless a profile says otherwise)
# f3 (measured on the f2 render vs the sheet, waist 0.27 m wide where the sheet's tee is 0.22): narrower waist and a
# thinner belly so the body suits the small head; chest from 1.25 up untouched
PROFILES = {"f3": dict(y=[0.70, 0.86, 1.00, 1.05, 1.10, 1.15, 1.20, 1.25],
                       k=[0.86, 0.88, 0.83, 0.75, 0.80, 0.86, 0.94, 1.0],
                       kz=[0.86, 0.88, 0.80, 0.70, 0.75, 0.80, 0.95, 1.0])}
SLEEVE_END = 0.10  # m along the arm from its root: end of the short sleeve on the reference
SHOULDER_X = 0.12  # m: shoulder rows outside this are capped around the arm axis


def seg_point(p, a, b):
    ab = b - a
    t = np.clip(np.dot(p - a, ab) / np.dot(ab, ab), 0, 1)
    return a + ab * t, t


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--joints", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--body", default="Character")
    ap.add_argument("--profile", default="")
    a = ap.parse_args(argv)
    global TRUNK_Y, TRUNK_K, TRUNK_KZ
    if a.profile:
        P = PROFILES[a.profile]
        TRUNK_Y, TRUNK_K, TRUNK_KZ = P["y"], P["k"], P["kz"]
    J = json.load(open(a.joints))
    ob = bpy.data.objects[a.body]
    me = ob.data
    part = me.attributes["part"]
    vpart = {}
    for p in me.polygons:
        for vi in p.vertices:
            vpart.setdefault(vi, set()).add(part.data[p.index].value)
    co = np.array([v.co[:] for v in me.vertices])
    hip, knee, ank = (np.array(J[k]) for k in ("hip", "knee", "ankle"))
    leg_len = np.linalg.norm(knee - hip) + np.linalg.norm(ank - knee)
    new = co.copy()
    moved = 0
    for i, p in enumerate(co):
        parts = vpart.get(i, set())
        if parts & {LEG, CROTCH} and p[2] < J["crotch_y"] + 0.02:
            s = 1.0 if p[0] >= 0 else -1.0
            h, k_, an = (q * np.array([s, 1, 1]) for q in (hip, knee, ank))
            q1, t1 = seg_point(p, h, k_)
            q2, t2 = seg_point(p, k_, an)
            d1, d2 = np.linalg.norm(p - q1), np.linalg.norm(p - q2)
            if d1 <= d2:
                q, t = q1, t1 * np.linalg.norm(k_ - h) / leg_len
            else:
                q, t = q2, (np.linalg.norm(k_ - h) + t2 * np.linalg.norm(an - k_)) / leg_len
            if p[2] < an[2]:          # foot below the ankle: shrink toward the foot centre line at that height
                q = np.array([an[0], p[1] * 0.0 + an[1], p[2]])
                t = 1.25
            f = float(np.interp(t, LEG_T, LEG_K))
            # crotch row blends into the trunk factor so the seam stays closed
            w = np.clip((J["crotch_y"] + 0.02 - p[2]) / 0.06, 0, 1)
            f = f * w + float(np.interp(p[2], TRUNK_Y, TRUNK_K)) * (1 - w)
            if p[2] < an[2]:
                d = p - q
                d[2] = 0          # keep the sole on the ground
                new[i] = q + d * f
            else:
                new[i] = q + (p - q) * f
            moved += 1
        elif TRUNK in parts and p[2] < TRUNK_Y[-1]:
            f = float(np.interp(p[2], TRUNK_Y, TRUNK_K))
            fz = float(np.interp(p[2], TRUNK_Y, TRUNK_KZ))
            band = co[np.abs(co[:, 2] - p[2]) < 0.012]
            band = band[np.abs(band[:, 0]) < 0.25]
            cy = (band[:, 1].min() + band[:, 1].max()) / 2 if len(band) else 0.0
            new[i] = np.array([p[0] * f, cy + (p[1] - cy) * fz, p[2]])
            moved += 1
    # arms: the T-shirt sleeve was carved in as arm thickness, so the upper arm was thick and the arm dropped to the
    # bare forearm at the sleeve end (user: "tangannya ga nyatu, beda ukurannya"). Inside the sleeve the radius is
    # pulled to the bare arm just past the sleeve end, growing a little toward the shoulder (deltoid).
    root, elb, wri = (np.array(J[k]) for k in ("arm_root", "elbow", "wrist"))
    ARM = 3
    arm_idx = [i for i in range(len(co)) if ARM in vpart.get(i, set()) and abs(co[i][0]) > root[0] - 0.01]
    if arm_idx:
        def axis(p):
            s = 1.0 if p[0] >= 0 else -1.0
            r, e, w = (q * np.array([s, 1, 1]) for q in (root, elb, wri))
            q1, t1 = seg_point(p, r, e)
            q2, t2 = seg_point(p, e, w)
            if np.linalg.norm(p - q1) <= np.linalg.norm(p - q2):
                return q1, t1 * np.linalg.norm(e - r)
            return q2, np.linalg.norm(e - r) + t2 * np.linalg.norm(w - e)
        info = [(i, *axis(new[i])) for i in arm_idx]
        rad = lambda i, q: np.linalg.norm(new[i] - q)
        dist = np.array([d for _, _, d in info])
        r_all = np.array([rad(i, q) for i, q, _ in info])
        # bare-arm radius just past the sleeve end
        cut = SLEEVE_END
        near = (dist > cut) & (dist < cut + 0.06)
        r_bare = float(np.median(r_all[near])) if near.any() else float(np.median(r_all))
        # v2: the step is in the TRUNK too: the armpit was found at the sleeve edge (x 0.23-0.25), so the shoulder rows
        # reach out as a sleeve-thick block. Every vertex (trunk or arm) outside SHOULDER_X and above the armpit gets a
        # radius cap around the arm axis line that shrinks from the shoulder to the bare arm: one taper, no step.
        # v3: the shoulder top row stayed flat out to x 0.23 (sleeve top) and dropped 3.6 cm onto the arm: the cap
        # now slopes the shoulder from 0.12 to the arm root (deltoid +20 %)
        if root[0] > 0.21:   # arm root at the sleeve edge (measured armpit)
            lim_x = [SHOULDER_X, 0.20, root[0], root[0] + cut]
            lim_r = [0.10, 0.058, r_bare * 1.2, r_bare]
        else:                # real armpit (ref_body RB_ARMPIT_X): shoulder slope -> deltoid -> bare arm
            lim_x = [SHOULDER_X, root[0], root[0] + cut]
            lim_r = [0.085, r_bare * 1.3, r_bare]
        n_cap = 0
        for i in range(len(new)):
            p = new[i]
            ax = abs(p[0])
            if ax <= SHOULDER_X or ax > root[0] + cut or p[2] < root[2] - 0.08:
                continue
            q = np.array([p[0], root[1], root[2] + (wri[2] - root[2]) * max(0.0, ax - root[0]) / (wri[0] - root[0])])
            d = p - q
            d[0] = 0.0
            r = np.linalg.norm(d)
            want = float(np.interp(ax, lim_x, lim_r))
            if r > want:
                new[i] = q + d * (want / r) + np.array([p[0] - q[0], 0, 0])
                n_cap += 1
        print("ARM bare radius", round(r_bare, 4), "sleeve end", cut, "capped", n_cap)
    for v, p in zip(me.vertices, new):
        v.co = p
    me.update()
    bpy.ops.wm.save_as_mainfile(filepath=a.out)
    print("INSET moved", moved, "of", len(co))


main()
