# Measure a turnaround reference sheet: silhouette masks per view + body landmarks, in metres.
#   blender -b --factory-startup -P tools/blender/ref_measure.py        (REF_IMG, REF_TAG override)
# The sheet (notes/attachments/ref/survivor_sheet.webp) has 4 views in a row: front, right, back, left (T-pose).
# Masks: |luminance - background| > threshold. Scale: stature REF_HEIGHT m = mask height of the front view.
# Coordinates out: x = character's left (m), y up from the ground (m), z forward (m); front view x0 = body centre.
# Output: output/ref/<tag>/measure.json (+ masks as .npy) and renders/ref_<tag>_overlay.png (masks + landmarks).
import bpy
import json
import os
import numpy as np

ROOT = r"C:\Mirza Personal\model 3d maker"
IMG = os.path.join(ROOT, os.environ.get("REF_IMG", "notes/attachments/ref/survivor_sheet.webp"))
TAG = os.environ.get("REF_TAG", "survivor")
HEIGHT = float(os.environ.get("REF_HEIGHT", "1.78"))
OUT = os.path.join(ROOT, "output", "ref", TAG)
# view boxes (x0, x1, y0, y1) in image pixels, y from the top
VIEWS = {"front": (10, 330, 95, 430), "right": (345, 445, 95, 430), "back": (440, 745, 95, 430),
         "left": (740, 830, 95, 430)}  # bottom stops above the view labels
THRESH = 0.07


def load():
    img = bpy.data.images.load(IMG)
    w, h = img.size
    return np.array(img.pixels[:], np.float32).reshape(h, w, 4)[::-1, :, :3]  # row 0 = top


def mask_of(a, box):
    x0, x1, y0, y1 = box
    c = a[y0:y1, x0:x1].mean(2)
    bg = np.median(np.concatenate([c[:, :3].ravel(), c[:, -3:].ravel()]))
    m = np.abs(c - bg) > THRESH
    # drop specks: keep pixels with >= 2 masked neighbours
    n = sum(np.roll(np.roll(m, dy, 0), dx, 1) for dy in (-1, 0, 1) for dx in (-1, 0, 1))
    m = m & (n >= 3)
    # fill holes (dark hair, eyes are close to the background): background = what the border can reach
    bg_ = np.zeros_like(m)
    bg_[0, :] = bg_[-1, :] = bg_[:, 0] = bg_[:, -1] = True
    bg_ &= ~m
    while True:
        g = bg_.copy()
        g[1:] |= bg_[:-1]
        g[:-1] |= bg_[1:]
        g[:, 1:] |= bg_[:, :-1]
        g[:, :-1] |= bg_[:, 1:]
        g &= ~m
        if (g == bg_).all():
            break
        bg_ = g
    return ~bg_


def intervals(row):
    """[start, end) runs of True."""
    r = np.concatenate([[False], row, [False]]).astype(int)
    d = np.diff(r)
    return list(zip(np.nonzero(d == 1)[0], np.nonzero(d == -1)[0]))


def containing(row, x):
    for a, b in intervals(row):
        if a <= x < b:
            return a, b
    return None


def front_landmarks(m):
    H, W = m.shape
    ys = np.nonzero(m.any(1))[0]
    top, bot = ys[0], ys[-1]
    # centre: middle of the widest run at waist height
    yw = int(top + 0.42 * (bot - top))  # waist (the legs split above 55 %)
    cand = max(intervals(m[yw]), key=lambda t: t[1] - t[0])
    x0 = (cand[0] + cand[1] - 1) / 2.0
    xi = int(round(x0))
    # crotch: first body pixel going up from the bottom on the centre column
    col = m[:, xi]
    y = bot
    while y > top and not col[y]:
        y -= 1
    crotch = y
    # armpit: going up from the crotch, the run containing the centre jumps outward when it joins the arm
    widths = []
    for y in range(crotch, top, -1):
        a, b = containing(m[y], xi) or (xi, xi + 1)
        widths.append((y, a, b))
    armpit = None
    for (y, a, b), (y2, a2, b2) in zip(widths, widths[1:]):
        if y > crotch - 0.15 * (bot - top):
            continue  # the pelvis widening above the crotch is not the armpit
        if (b2 - xi) > 1.6 * (b - xi) + 4:
            armpit = (y2, b - 1)  # row where the arm joins, torso edge x just below
            break
    # arm band: columns right of the armpit, take the run nearest the arm line
    arm = []
    ay = armpit[0]
    for x in range(armpit[1] + 2, W):
        runs = intervals(m[:, x])
        if not runs:
            break
        a, b = min(runs, key=lambda t: abs((t[0] + t[1]) / 2 - ay))
        if abs((a + b) / 2 - ay) > 40:
            break
        arm.append((x, a, b))
        ay = (a + b) / 2
    tip = arm[-1][0]
    # shoulder top: highest body pixel above the armpit column
    sh_top = np.nonzero(m[:, armpit[1]])[0][0]
    # neck: narrowest run containing the centre between the shoulder top and the crown
    neck = min(((b - a, y) for y, a, b in widths if top + 0.06 * (bot - top) < y < sh_top), default=(0, sh_top))[1]
    # legs: run right of the centre below the crotch
    leg = []
    for y in range(crotch + 1, bot + 1):
        runs = [(a, b) for a, b in intervals(m[y]) if (a + b) / 2 > x0]
        if runs:
            a, b = min(runs, key=lambda t: t[0])
            leg.append((y, a, b))
    lw = np.array([b - a for _, a, b in leg])
    ly = np.array([y for y, _, _ in leg])
    low = (ly > crotch + 0.75 * (bot - crotch)) & (ly < bot - 0.03 * (bot - top))
    ankle = int(ly[low][np.argmin(lw[low])])
    return dict(top=int(top), bot=int(bot), x0=float(x0), crotch=int(crotch), armpit=[int(armpit[0]), int(armpit[1])],
                sh_top=int(sh_top), neck=int(neck), tip=int(tip), ankle=ankle,
                arm=[[int(x), int(a), int(b)] for x, a, b in arm], leg=[[int(y), int(a), int(b)] for y, a, b in leg],
                trunk=[[int(y), int(a), int(b)] for y, a, b in widths])


def side_profile(m):
    """Per row: runs (z extents in pixels). Facing: toes point forward."""
    ys = np.nonzero(m.any(1))[0]
    top, bot = ys[0], ys[-1]
    rows = {int(y): [[int(a), int(b)] for a, b in intervals(m[y])] for y in range(top, bot + 1)}
    # facing: on the sole rows the foot reaches further on the toe side than the ankle column
    sole = m[bot - 3:bot + 1].any(0)
    ank = m[int(bot - 0.08 * (bot - top))]
    s = np.nonzero(sole)[0]
    a = np.nonzero(ank)[0]
    c_ank = (a[0] + a[-1]) / 2
    facing = 1 if (s[-1] - c_ank) > (c_ank - s[0]) else -1  # +1: toes toward larger column index
    return dict(top=int(top), bot=int(bot), facing=facing, rows=rows)


def overlay(a, masks, lm):
    out = a.copy()
    for name, (x0, x1, y0, y1) in VIEWS.items():
        m = masks[name]
        out[y0:y1, x0:x1][m] = out[y0:y1, x0:x1][m] * 0.5 + np.array([0.9, 0.5, 0.1]) * 0.5
    fx0, _, fy0, _ = VIEWS["front"]

    def dot(y, x, col, r=2):
        out[fy0 + y - r:fy0 + y + r + 1, fx0 + x - r:fx0 + x + r + 1] = col
    f = lm["front"]
    for key, col in (("crotch", (0, 1, 0)), ("ankle", (0, 1, 1)), ("neck", (1, 0, 1)), ("sh_top", (1, 1, 0))):
        x = int(f["x0"]) if key in ("crotch", "neck") else f["armpit"][1]
        if key == "ankle":
            x = int(np.mean([(r[1] + r[2]) / 2 for r in f["leg"] if r[0] == f["ankle"]]))
        dot(f[key], x, col)
    dot(f["armpit"][0], f["armpit"][1], (1, 0, 0))
    for x, a_, b_ in f["arm"][::6]:
        dot(int((a_ + b_) / 2), x, (0.2, 0.6, 1), 1)
    for y, a_, b_ in f["leg"][::6]:
        dot(y, int((a_ + b_) / 2), (0.2, 0.6, 1), 1)
    dot(f["top"], int(f["x0"]), (1, 1, 1))
    h, w = out.shape[:2]
    img = bpy.data.images.new("ov", w, h)
    img.pixels = np.concatenate([out[::-1], np.ones((h, w, 1), np.float32)], 2).ravel()
    img.filepath_raw = os.path.join(ROOT, "renders", f"ref_{TAG}_overlay.png")
    img.file_format = "PNG"
    img.save()


def main():
    a = load()
    masks = {k: mask_of(a, b) for k, b in VIEWS.items()}
    lm = {"front": front_landmarks(masks["front"])}
    for k in ("right", "left"):
        lm[k] = side_profile(masks[k])
    f = lm["front"]
    px = HEIGHT / (f["bot"] - f["top"])
    lm["scale_m_per_px"] = px
    lm["height_px"] = {k: int(np.ptp(np.nonzero(masks[k].any(1))[0])) for k in masks}
    os.makedirs(OUT, exist_ok=True)
    for k, m in masks.items():
        np.save(os.path.join(OUT, f"mask_{k}.npy"), m)
    json.dump(lm, open(os.path.join(OUT, "measure.json"), "w"))
    overlay(a, masks, lm)
    yy = lambda y: round((f["bot"] - y) * px, 3)
    print("REF", json.dumps({"m_per_px": round(px, 4), "heights_px": lm["height_px"], "crown": yy(f["top"]),
                             "neck": yy(f["neck"]), "shoulder_top": yy(f["sh_top"]), "armpit_y": yy(f["armpit"][0]),
                             "armpit_x": round((f["armpit"][1] - f["x0"]) * px, 3),
                             "arm_tip_x": round((f["tip"] - f["x0"]) * px, 3), "crotch": yy(f["crotch"]),
                             "ankle": yy(f["ankle"]), "side_facing": [lm["right"]["facing"], lm["left"]["facing"]]}))


if __name__ == "__main__":
    main()
