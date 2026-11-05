# E2: does the model match the reference sheet? Silhouette IoU front + side, per body band, and landmark heights.
#   blender -b <file.blend> --factory-startup -P tools/qa/silhouette_iou.py -- --measure output/ref/survivor
# --measure: folder written by tools/blender/ref_measure.py (mask_front.npy, mask_right.npy, measure.json).
# The model is rendered as a flat white mask with an orthographic camera at the reference's own pixel scale
# (feet on the bottom row of the reference, front: body centre on the reference centre column, side: bounding
# boxes centred, flipped to face the same way). IoU = shared pixels / pixels in either.
# Output: output/qa/<tag>_iou.json and <tag>_iou.png (green = both, red = reference only, blue = model only).
import json
import os
import sys
import tempfile

import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "blender"))
import qa_common as Q  # noqa: E402


def opts(p):
    p.add_argument("--measure", default="output/ref/survivor")
    p.add_argument("--min", type=float, default=0.90)
    p.add_argument("--landmark-tol", type=float, default=0.02, help="share of the stature")
    p.add_argument("--tag", default="")


def mask_scene():
    sc = bpy.context.scene
    Q.set_engine(sc)
    sh = sc.display.shading
    sh.light = "FLAT"
    sh.color_type = "SINGLE"
    sh.single_color = (1, 1, 1)
    sh.show_cavity = False
    sh.show_shadows = False
    sh.show_object_outline = False
    if sc.world is None:
        sc.world = bpy.data.worlds.new("_qa_world")
    sc.world.color = (0, 0, 0)
    sc.render.film_transparent = False
    try:
        sc.display.render_aa = "OFF"
    except TypeError:
        pass
    try:
        sc.view_settings.view_transform = "Standard"
    except TypeError:
        pass
    for o in bpy.data.objects:
        if o.type == "MESH" and o not in Q.meshes():
            o.hide_render = True
    return sc


def render_mask(view, w, h, mpp, centre, tmp):
    """Orthographic mask, 1 px = mpp metres, image centre at world point `centre`."""
    cam = Q.ortho_camera()
    cam.data.clip_end = 100
    cam.data.ortho_scale = max(w, h) * mpp
    d = np.array(Q.VIEWS[view])
    Q.aim(cam, centre + d * 10, centre)
    p = Q.render_to(os.path.join(tmp, f"mask_{view}.png"), w, h)
    return Q.load_png(p)[..., 0] > 0.5


def bbox_cols(m):
    cols = np.nonzero(m.any(0))[0]
    return (cols[0] + cols[-1]) / 2.0 if len(cols) else m.shape[1] / 2.0


def shift_cols(m, dx):
    out = np.zeros_like(m)
    dx = int(round(dx))
    if dx >= 0:
        out[:, dx:] = m[:, :m.shape[1] - dx]
    else:
        out[:, :dx] = m[:, -dx:]
    return out


def iou(a, b):
    u = (a | b).sum()
    return float((a & b).sum() / u) if u else 0.0


def overlay(ref, mod):
    img = np.zeros(ref.shape + (3,), np.float32)
    img[ref & mod] = (0.25, 0.75, 0.35)
    img[ref & ~mod] = (0.9, 0.2, 0.2)
    img[~ref & mod] = (0.25, 0.45, 1.0)
    return img


def main():
    a = Q.args("E2 silhouette IoU", opts)
    tag = Q.tag_of(a)
    mdir = a.measure if os.path.isabs(a.measure) else os.path.join(Q.ROOT, a.measure)
    lm = json.load(open(os.path.join(mdir, "measure.json")))
    mpp = lm["scale_m_per_px"]
    ref_f = np.load(os.path.join(mdir, "mask_front.npy"))
    ref_s = np.load(os.path.join(mdir, "mask_right.npy"))
    F, S = lm["front"], lm["right"]
    objs = Q.meshes()
    mask_scene()
    lo, hi = Q.world_bounds(objs)
    tmp = tempfile.mkdtemp(prefix="qa_iou_")

    # front: reference column x0 = body centre (x = 0), bottom row = ground
    h, w = ref_f.shape
    cx = (w / 2 - (F["x0"] + 0.5)) * mpp
    cz = (F["bot"] + 1 - h / 2) * mpp
    mod_f = render_mask("front", w, h, mpp, np.array([cx, 0.0, cz]), tmp)
    # side: same scale, bounding boxes centred, facing matched
    h2, w2 = ref_s.shape
    cy = float((lo[1] + hi[1]) / 2)
    cz2 = (S["bot"] + 1 - h2 / 2) * mpp
    mod_s = render_mask("right", w2, h2, mpp, np.array([0.0, cy, cz2]), tmp)
    if S["facing"] < 0:  # model toes point to larger columns from this camera; reference toes point left
        mod_s = mod_s[:, ::-1]
    # bounding boxes first, then the best shift within +-25 px: the reference's hair and toes move its bounding box
    base = bbox_cols(ref_s) - bbox_cols(mod_s)
    best = max(range(-25, 26), key=lambda k: iou(ref_s, shift_cols(mod_s, base + k)))
    mod_s = shift_cols(mod_s, base + best)

    # bands from the reference front landmarks (rows -> metres -> rows of each view)
    zf = lambda r: (F["bot"] + 1 - r) * mpp
    bands_m = {"head+neck": (zf(F["neck"]), 9.0), "torso+arms": (zf(F["crotch"]), zf(F["neck"])),
               "legs": (-1.0, zf(F["crotch"]))}

    def band_iou(ref, mod, bot):
        out = {}
        rows = (bot + 1 - np.arange(ref.shape[0])) * mpp  # height of each row
        for k, (z0, z1) in bands_m.items():
            sel = (rows > z0) & (rows <= z1)
            out[k] = round(iou(ref[sel], mod[sel]), 3)
        return out

    res = {
        "iou_front": round(iou(ref_f, mod_f), 4), "iou_side": round(iou(ref_s, mod_s), 4),
        "bands_front": band_iou(ref_f, mod_f, F["bot"]), "bands_side": band_iou(ref_s, mod_s, S["bot"]),
        "ref_only_px_front": int((ref_f & ~mod_f).sum()), "model_only_px_front": int((~ref_f & mod_f).sum()),
        "model_height_m": round(float(hi[2] - lo[2]), 4), "ref_height_m": round((F["bot"] - F["top"]) * mpp, 4),
    }
    # landmarks: the reference measuring code run on the model's own front mask
    try:
        import ref_measure as RM
        mf = RM.front_landmarks(mod_f)
        H = res["ref_height_m"]
        lmk = {}
        for k in ("neck", "sh_top", "crotch", "ankle", "top"):
            lmk[k] = {"ref_m": round(zf(F[k]), 3), "model_m": round(zf(mf[k]), 3)}
        lmk["armpit"] = {"ref_m": round(zf(F["armpit"][0]), 3), "model_m": round(zf(mf["armpit"][0]), 3)}
        lmk["arm_tip_x"] = {"ref_m": round((F["tip"] - F["x0"]) * mpp, 3), "model_m": round((mf["tip"] - mf["x0"]) * mpp, 3)}
        for v in lmk.values():
            v["diff_share"] = round(abs(v["model_m"] - v["ref_m"]) / H, 4)
        res["landmarks"] = lmk
    except Exception as e:  # odd silhouettes (A-pose, props) have no armpit/crotch to find
        res["landmarks_error"] = repr(e)

    gates = [("front IoU", res["iou_front"] >= a.min, res["iou_front"], f">= {a.min}"),
             ("side IoU", res["iou_side"] >= a.min, res["iou_side"], f">= {a.min}")]
    for k, v in res.get("landmarks", {}).items():
        gates.append((f"landmark {k}", v["diff_share"] <= a.landmark_tol,
                      f"{v['model_m']} vs ref {v['ref_m']}", f"diff <= {a.landmark_tol:.0%} of stature"))
    res["gates"] = [{"gate": g, "result": "PASS" if ok else "FAIL", "value": val, "need": need} for g, ok, val, need in gates]
    res["passed"] = all(ok for _, ok, _, _ in gates)

    # picture: front | side, same height
    hh = max(h, h2)
    pad = lambda img: np.concatenate([img, np.zeros((hh - img.shape[0],) + img.shape[1:], np.float32)], 0)
    pic = np.concatenate([pad(overlay(ref_f, mod_f)), np.ones((hh, 4, 3), np.float32), pad(overlay(ref_s, mod_s))], 1)
    pic = np.repeat(np.repeat(pic, 2, 0), 2, 1)  # 2x for reading
    png = os.path.join(Q.QA_OUT, f"{tag}_iou.png")
    os.makedirs(Q.QA_OUT, exist_ok=True)
    Q.save_png(pic, png)
    np.save(os.path.join(Q.QA_OUT, f"{tag}_mask_front.npy"), mod_f)  # for later row-by-row comparisons
    np.save(os.path.join(Q.QA_OUT, f"{tag}_mask_side.npy"), mod_s)
    path = Q.save_json(res, f"{tag}_iou.json")
    for g in res["gates"]:
        print(f"QA {g['result']:4}  {g['gate']}: {g['value']}  (need {g['need']})")
    print("QA_BANDS front", res["bands_front"], "side", res["bands_side"])
    print("QA_DONE", path, png)


if __name__ == "__main__":
    main()
