# New body from a turnaround reference sheet (silhouette carving), same quad layout as body_quad.py.
#   blender -b --factory-startup -P tools/blender/ref_measure.py      (masks + landmarks first)
#   blender -b --factory-startup -P tools/blender/ref_body.py         (REF_TAG, RB_TAG override)
# World coordinates (m): ground y = 0, x = character's left, z forward. Blender = (x, -z, y).
#
# How each cross-section is found ("rays" through the silhouettes):
#   - front view: at height y, the run that holds the body centre gives the half width; arm columns give the arm's
#     vertical thickness; leg runs give leg width and centre;
#   - right side view: the run at height y gives front (z+) and back (z-) of the torso or legs; inside the band
#     where the T-pose arm covers the chest, front/back are interpolated from the rows above and below;
#   - the 4 axis points of a ring come straight from the silhouettes, the diagonal ones from a superellipse
#     (n = RB_ROUND) through them: silhouettes cannot see the corners, the superellipse is the prior.
#   - hidden depths (arm front/back, hand width) use proportions from our F2 body (prior), scaled to the stature.
# The template head is a placeholder (scaled to the reference head size); the head and hair are the next part.
import bpy
import bmesh
import json
import math
import os
import sys
import numpy as np
from mathutils import Vector, Matrix

sys.path.insert(0, os.path.dirname(__file__))
import head_game as G  # noqa: E402
import body_quad as Q  # noqa: E402
import f2_assemble as F  # noqa: E402

ROOT = F.ROOT
REF = os.environ.get("REF_TAG", "survivor")
TAG = os.environ.get("RB_TAG", "ref_body_v1")
RDIR = os.path.join(ROOT, "output", "ref", REF)
OUT = os.path.join(ROOT, "output", "ref", REF)
HEAD_SRC = os.path.join(ROOT, os.environ.get("RB_HEAD", "output/head-game/template/head_nose_v2.blend"))
HEIGHT = float(os.environ.get("REF_HEIGHT", "1.78"))
EXP = 2.0 / float(os.environ.get("RB_ROUND", "2.6"))  # superellipse exponent for the diagonals
TRUNK_EXP = 2.0 / float(os.environ.get("RB_TRUNK_ROUND", os.environ.get("RB_ROUND", "2.6")))  # trunk only: 2 = ellipse
S = HEIGHT / 1.729  # stature ratio to F2 (prior sizes)
ARM_DEPTH = 0.95  # arm front/back half depth = this x vertical half thickness (F2 prior)
FOOT_BOX = 0.5  # superellipse exponent for foot sections (n = 4: boxy)
HAIR = 0.035  # hair above the skull at the crown (m), the template head fits under it
COLS = Q.COLS
HAND_ANG = [0, 21, 73, 107, 159, 180, 201, 253, 287, 339]  # palm ring: 8-ring with both side points split;
# angles chosen so the 4 knuckle faces are equally wide after the boxy superellipse (|sin a|^(2/3) = 0.5, 0.97)
PALM_LEN = 0.5  # knuckles at this share of wrist -> middle finger tip
FINGERS = [(0.72, 10.0), (0.9, 3.5), (1.0, -1.5), (0.9, -7.0)]  # little, ring, middle, index: length share, spread deg (+ = toward the little-finger side)
FINGER_SEG = [0.42, 0.33, 0.25]  # segment shares: proximal, middle, distal
FINGER_CURL = [3.0, 9.0, 14.0]  # degrees bent toward the palm at each segment (relaxed hand)
FINGER_SIZE = [(0.66, 0.88), (0.6, 0.8), (0.5, 0.66)]  # ring width/thickness share of the knuckle face
ARM_ANG = Q.ARM_ANG
KNEE_RINGS = [float(d) for d in os.environ.get("RB_KNEE", "0.05,0,-0.05").split(",")]  # ring offsets around the knee (m), must hold 0. 5 rings (+-0.025) flipped sooner in the rig test: keep 3
KNEE_PINCH = float(os.environ.get("RB_KNEE_PINCH", "0"))  # 0..1: how far the knee rings close in at the back. Tested 0.6 / 0.75: worse than 0 (the rig fixes the knee in weights)
ARMPIT_FOLD = float(os.environ.get("RB_ARMPIT_FOLD", "0"))  # 0..1: arm root front pulled to the chest front plane
NECK_ANCHOR = os.environ.get("RB_NECK_ANCHOR", "1") == "1"  # trunk depth across the arm band ends at the neck base (v12)
HEAD_WARP = os.environ.get("RB_HEAD_WARP", "0") == "1"  # head width per height onto the reference (chin..brow)
HEAD_WARP_TOP = 0.04  # template units above eye level (brow)
HEAD_WARP_MAX = 0.15
# trapezoid jaw (template coords, eye level 0): the side of the face runs straight from the cheekbone to the chin
JAW_TAPER = os.environ.get("RB_JAW", "0") == "1"  # for head_masc_v1 only (head_planes has its own jaw)
JAW_TOP = float(os.environ.get("RB_JAW_TOP", "-0.02"))  # taper starts under the cheekbone
JAW_CHIN_Y = -0.115  # chin bottom corners
JAW_CHIN = float(os.environ.get("RB_JAW_CHIN", "0.034"))  # chin half width at JAW_CHIN_Y (cheek ~0.072)
JAW_CORE = 0.02  # |x| under this (mouth, chin centre) is not moved
JAW_LOOP_Y = -0.132  # neck loop: factor back to 1 here
JOINTS = {}  # left-side joint centres for the rig (tools/blender/rig_game.py), Blender coords


class Sil:
    """Silhouette lookups in metres."""

    def __init__(self):
        m = json.load(open(os.path.join(RDIR, "measure.json")))
        self.m = m
        self.F = np.load(os.path.join(RDIR, "mask_front.npy"))
        self.R = np.load(os.path.join(RDIR, "mask_right.npy"))
        f = m["front"]
        self.px = m["scale_m_per_px"]
        self.fb, self.x0 = f["bot"], f["x0"]
        r = m["right"]
        self.rb = r["bot"]
        self.rpx = HEIGHT / (r["bot"] - r["top"])
        self.face = r["facing"]
        # side-view z origin: centre of the torso run at waist height
        yw = int(round(self.rb - 1.05 / self.rpx))
        runs = self.runs(self.R[yw])
        a, b = max(runs, key=lambda t: t[1] - t[0])
        self.zc = (a + b - 1) / 2

    @staticmethod
    def runs(row):
        r = np.concatenate([[False], row, [False]]).astype(int)
        d = np.diff(r)
        return list(zip(np.nonzero(d == 1)[0], np.nonzero(d == -1)[0]))

    def frow(self, y):
        return self.F[int(round(np.clip(self.fb - y / self.px, 0, self.F.shape[0] - 1)))]

    def front_run(self, y, x_hint=0.0):
        """(x_min, x_max) of the run at height y nearest x_hint."""
        runs = self.runs(self.frow(y))
        c = self.x0 + x_hint / self.px
        a, b = min(runs, key=lambda t: 0 if t[0] <= c < t[1] else min(abs(t[0] - c), abs(t[1] - c)))
        return (a - self.x0) * self.px, (b - 1 - self.x0) * self.px

    def side_run(self, y, z_hint=0.0):
        row = self.R[int(round(np.clip(self.rb - y / self.rpx, 0, self.R.shape[0] - 1)))]
        runs = self.runs(row)
        c = self.zc + z_hint * self.face / self.rpx
        a, b = min(runs, key=lambda t: 0 if t[0] <= c < t[1] else min(abs(t[0] - c), abs(t[1] - c)))
        za, zb = (a - self.zc) * self.rpx * self.face, (b - 1 - self.zc) * self.rpx * self.face
        return min(za, zb), max(za, zb)

    def arm_col(self, x, y_hint):
        """Vertical run of the arm at x (m): (y_bottom, y_top)."""
        col = self.F[:, int(round(self.x0 + x / self.px))]
        runs = [t for t in self.runs(col) if (t[1] - t[0]) * self.px > 0.02] or self.runs(col)  # skip specks
        ch = self.fb - y_hint / self.px
        a, b = min(runs, key=lambda t: abs((t[0] + t[1]) / 2 - ch))
        return (self.fb - (b - 1)) * self.px, (self.fb - a) * self.px

    def foot_top(self, z):
        """Height of the side silhouette's lowest run at forward position z (foot profile)."""
        col = self.R[:, int(round(self.zc + z * self.face / self.rpx))]
        runs = self.runs(col)
        if not runs:
            return 0.0
        a, b = max(runs, key=lambda t: t[1])
        return (self.rb - a) * self.rpx


def se(c, s, ex=EXP):
    """Superellipse factors for cos / sin of an angle."""
    return math.copysign(abs(c) ** ex, c), math.copysign(abs(s) ** ex, s)


def landmarks(sil):
    f, px = sil.m["front"], sil.px
    y = lambda row: (sil.fb - row) * px
    L = {"crown": y(f["top"]), "chin": y(f["neck"]), "sh_top": y(f["sh_top"]), "armpit_y": y(f["armpit"][0]),
         "armpit_x": (f["armpit"][1] - sil.x0) * px, "tip": (f["tip"] - sil.x0) * px, "crotch": y(f["crotch"])}
    L["knee"] = 0.285 * HEIGHT
    L["ankle"] = y(f["ankle"])  # narrowest leg row above the foot (this style has big feet, ~0.19 m)
    # arm axis: walk out from the armpit, following the thick run (x, thickness, centre y)
    arm, yh = [], (L["armpit_y"] + L["sh_top"]) / 2
    for x in np.arange(L["armpit_x"] + 0.005, L["tip"] - 0.004, px):
        b_, t_ = sil.arm_col(x, yh)
        arm.append((float(x), t_ - b_, (b_ + t_) / 2))
        yh = (b_ + t_) / 2
    # wrist: thinnest arm column 13-25 cm before the finger tip
    cand = [t for t in arm if L["tip"] - 0.25 * S < t[0] < L["tip"] - 0.13 * S]
    L["wrist"] = min(cand, key=lambda t: t[1])[0]
    L["arm_axis"] = arm
    return L


def build(sil, L, head_ring):
    pos, faces = {}, []
    side = lambda col: "M" if col in (0, 180) else "L"
    tk = lambda r, col: (side(col), "t", r, col)
    # ---- neck (new): head jaw loop (n, 0) -> NECK_RINGS rings -> neck base ring = trunk row 0 ----
    nk = lambda i, col: (side(col), "n", i, col)
    for col, v in head_ring.items():
        pos[nk(0, col)] = v
    # Neck base ring, per column below the jaw loop. TILTED (NECK_TILT): the jaw loop is low under the chin and
    # high at the sides and the nape, so the base follows it: the side of the neck starts high and the plane from
    # there down to the trunk's first row is the trapezius slope (flat base = a shelf when the head is big).
    y_flat = L["chin"] - NECK_BASE_DROP
    jaw_low = min(v[1] for v in head_ring.values())
    y_front = min(y_flat, jaw_low - NECK_GAP)
    if NECK_TILT:
        # sides and back rise to TRAP_GAP under the jaw loop: the slope starts at the head
        base_y = {col: y_front + (jaw_low - TRAP_GAP - y_front) * TRAP_LIFT[col] for col in COLS}
    else:
        base_y = {col: y_front for col in COLS}
    y_neck = y_front  # lowest point (throat): the trunk rows start under it
    na, nb = sil.front_run(y_flat)
    base = {}
    for col in COLS:
        y_c = base_y[col]
        zb, zf = sil.side_run(y_c - 0.006)  # just under the jaw shadow of the side view
        a, b = sil.front_run(y_c - 0.006)
        flare = NECK_FLARE + (TRAP_FLARE - NECK_FLARE) * TRAP_LIFT[col] if NECK_TILT else NECK_FLARE
        half = min((b - a) / 2, flare * (nb - na) / 2)
        t = math.radians(col)
        cf, sf = se(math.cos(t), math.sin(t))
        base[col] = np.array([half * sf, y_c, (zf if cf >= 0 else -zb) * cf])
    NECK_DEBUG.update(jaw_y={c: round(float(head_ring[c][1]), 3) for c in COLS},
                      base_y={c: round(float(v), 3) for c, v in base_y.items()})
    base[0][2] -= SCM_DEPTH  # pit between the two sternocleidomastoids
    rings = [head_ring]
    for k in range(1, (0 if NECK_TILT else NECK_RINGS) + 1):  # tilted: the jaw loop meets the base directly
        u = k / (NECK_RINGS + 1)
        ring = {col: head_ring[col] * (1 - u) + base[col] * u for col in COLS}
        a, b = sil.front_run(L["chin"])  # narrowest neck width all the way: no flare under the jaw
        sx = ((b - a) / 2) / max(abs(v[0]) for v in ring.values())
        for col in COLS:
            ring[col][0] *= sx
        ring[22][2] += SCM_BULGE  # the neck muscle ridge: front plane splits into a V
        ring[0][2] -= SCM_DEPTH
        rings.append(ring)
    for i, ring in enumerate(rings[1:], start=1):
        for col in COLS:
            pos[nk(i, col)] = ring[col]
    for col in COLS:
        pos[tk(0, col)] = base[col]
    nkey = lambda i, col: tk(0, col) if i == len(rings) else nk(i, col)
    for i in range(len(rings)):
        for a_, b_ in zip(COLS, COLS[1:]):
            faces.append([nkey(i, a_), nkey(i, b_), nkey(i + 1, b_), nkey(i + 1, a_)])
    # arm root
    x_root = L["armpit_x"] + 0.015
    axis_y = lambda x: float(np.interp(x, [t[0] for t in L["arm_axis"]], [t[2] for t in L["arm_axis"]]))
    rb, rt = sil.arm_col(x_root, axis_y(x_root))
    # trunk rows
    y_cr = L["crotch"] + 0.018
    below = [L["armpit_y"] - k * (L["armpit_y"] - (L["crotch"] + 0.09)) for k in (0.12, 0.34, 0.55, 0.76, 1.0)]
    rows = [y_neck - 0.45 * (y_neck - rt), rt, (rt + rb) / 2, rb] + below + [y_cr]
    band = (rb - 0.02, rt + 0.02)
    # torso front/back by height, interpolated across the arm band
    ys_ok = [y for y in np.linspace(y_cr, y_neck, 80) if not band[0] <= y <= band[1]]
    zb_ok = [sil.side_run(y)[0] for y in ys_ok]
    zf_ok = [sil.side_run(y)[1] for y in ys_ok]
    if NECK_ANCHOR:
        # the arm band reaches past the neck base, so nothing above it was measured and np.interp held the last
        # value: a vertical back and chest, then a step into the neck (a right angle in the side view). The neck
        # base ring is the top anchor: the upper back and upper chest slope into the neck as in the reference.
        yb_ok, zb_ok = ys_ok + [float(base_y[180])], zb_ok + [float(base[180][2])]
        yf_ok, zf_ok = ys_ok + [float(base_y[0])], zf_ok + [float(base[0][2] + SCM_DEPTH)]
    else:
        yb_ok = yf_ok = ys_ok
    zfb = lambda y: (float(np.interp(y, yb_ok, zb_ok)), float(np.interp(y, yf_ok, zf_ok)))
    trap_half = (lambda r: (r[1] - r[0]) / 2)(sil.front_run(rows[0]))
    for r, y in enumerate(rows, start=1):
        zb, zf = zfb(y)
        if 2 <= r <= 4:
            half = trap_half + (L["armpit_x"] - trap_half) * (r - 1) / 4.0
        else:
            a, b = sil.front_run(y)
            half = (b - a) / 2
        for col in COLS:
            if r in Q.HOLE_ROWS and col in (48, 90, 120):
                continue
            t = math.radians(col)
            cf, sf = se(math.cos(t), math.sin(t), TRUNK_EXP)
            y_c, zb_c, zf_c = y, zb, zf
            if NECK_TILT and r in (1, 2) and col in MID_SPREAD:
                # big head = short neck: throat (y_neck), trapezius row and arm-top row sit within 7 mm, a band of
                # needles down the chest and back. Spread these two rows evenly from the throat to row 3 instead.
                y_even = y_neck - (y_neck - rows[2]) * r / 3.0
                y_c = y + (y_even - y) * MID_SPREAD[col]
                zb_c, zf_c = zfb(y_c)
            pos[tk(r, col)] = np.array([half * sf, y_c, (zf_c if cf >= 0 else -zb_c) * cf])
    # ---- arm rings: vertical thickness from the front view, depth from the prior ----
    z_arm = 0.5 * sum(zfb(L["armpit_y"])) - 0.01
    joint = x_root - 0.025
    xs = [x_root] + [joint + k * (L["wrist"] - joint) for k in (0.2, 0.4, 0.5, 0.55, 0.6, 0.75, 0.9)] + [L["wrist"]]
    pts, tans, dims = [], [], []
    for x in xs:
        b_, t_ = sil.arm_col(x, axis_y(x))
        pts.append(np.array([x, (b_ + t_) / 2, z_arm]))
        dims.append((t_ - b_) / 2)
    for i in range(len(pts)):
        j0, j1 = max(i - 1, 0), min(i + 1, len(pts) - 1)
        tans.append(pts[j1] - pts[j0])
    afr = Q.frames(pts, tans, np.array([0, 1.0, 0]))
    JOINTS.update(arm_root=pts[0], elbow=pts[4])  # elbow: middle of the rings at 0.5 / 0.55 / 0.6
    hole = {0: (2, 90), 1: (2, 48), 2: (3, 48), 3: (4, 48), 4: (4, 90), 5: (4, 120), 6: (3, 120), 7: (2, 120)}
    ak = lambda i, k: tk(*hole[k]) if i == 0 else ("L", "a", i, k)
    for i, (fr, t) in enumerate(zip(afr, dims)):
        c, _, e1, e2 = fr
        for k, a in enumerate(ARM_ANG):
            cu, sw = se(math.cos(math.radians(a)), math.sin(math.radians(a)))
            pos[ak(i, k)] = c + e1 * t * cu + e2 * t * ARM_DEPTH * sw
    # armpit front fold: the front of the arm root (and less of the next ring) moves forward toward the chest front
    # plane, so the chest wraps onto the arm instead of a step from the chest down to the arm root
    for i, w_ in ((0, ARMPIT_FOLD), (1, ARMPIT_FOLD * 0.4)):
        for k, a in enumerate(ARM_ANG):
            f_ = max(0.0, math.sin(math.radians(a)))
            p_ = pos[ak(i, k)]
            target = zfb(p_[1])[1]
            if target > p_[2]:
                p_[2] += w_ * f_ * (target - p_[2])
    # ---- hand: palm (2 rings of 10) -> 4 fingers (3 segments each) + thumb (3 segments). Box modeling as in the
    # Rozi 3D tutorial: the knuckle end is cut into 4 faces, each face is extruded into a finger with a ring at every
    # joint (the rig bends there). Sizes from the F2 prior, the middle finger tip from the silhouette.
    n_arm = len(afr)
    for i in range(n_arm - 1):
        for k in range(8):
            faces.append([ak(i, k), ak(i, (k + 1) % 8), ak(i + 1, (k + 1) % 8), ak(i + 1, k)])
    wrist_c = afr[-1][0]
    tip = np.array([L["tip"] - 0.008, axis_y(L["tip"] - 0.03), z_arm])
    hvec = tip - wrist_c
    hlen = float(np.linalg.norm(hvec))
    hdir = hvec / hlen
    palm = [(0.16, 0.043 * S, 0.017 * S), (PALM_LEN, 0.047 * S, 0.0125 * S)]  # last ring = knuckles
    hp = [wrist_c + hvec * f_ for f_, _, _ in palm]
    hfr = Q.frames(hp, [hvec] * len(hp), afr[-1][2])
    JOINTS.update(wrist=wrist_c, knuckles=hp[1])
    hk = lambda j, k: ("L", "h", j, k)
    for j, (fr, (_, hw, ht)) in enumerate(zip(hfr, palm)):
        c, _, e1, e2 = fr
        for k, a in enumerate(HAND_ANG):
            cu, sw = se(math.cos(math.radians(a)), math.sin(math.radians(a)), 2 / 3.0)
            pos[hk(j, k)] = c + e1 * ht * cu + e2 * hw * sw
    # wrist ring (8) -> palm ring (10): the two side points split in two (one triangle per side)
    W = n_arm - 1
    hv = {0: [0], 1: [1], 2: [2, 3], 3: [4], 4: [5], 5: [6], 6: [7, 8], 7: [9]}
    for k in range(8):
        k2 = (k + 1) % 8
        faces.append([ak(W, k), ak(W, k2), hk(0, hv[k2][0]), hk(0, hv[k][-1])])
        if len(hv[k]) == 2:
            faces.append([ak(W, k), hk(0, hv[k][-1]), hk(0, hv[k][0])])
    thumb_k = 3  # palm face between 102 and 135 deg: front, under (palm down in the T-pose)
    for k in range(10):
        if k != thumb_k:
            faces.append([hk(0, k), hk(0, (k + 1) % 10), hk(1, (k + 1) % 10), hk(1, k)])

    def rot(v, axis, deg):
        axis = Q.unit(axis)
        a = math.radians(deg)
        return v * math.cos(a) + np.cross(axis, v) * math.sin(a) + axis * (axis @ v) * (1 - math.cos(a))

    def tube(base, centre0, path, sizes, frames_, key):
        """Extrude a 4-vertex base face along path points: one ring per point (scaled offsets), cap at the end."""
        e1k, e2k = frames_
        prev = base
        for j, (c, (fw, fh), (e1r, e2r)) in enumerate(zip(path, sizes, key["frames"])):
            ring = []
            for m_, q in enumerate(base):
                off = pos[q] - centre0
                kk = key["name"] + (j, m_)  # flat key starting with "L": mirrored to the right hand
                if "dir" in key:  # radial: corner direction kept, size absolute (m) -> a square tube
                    d_ = key["dir"]
                    pos[kk] = c + Q.unit(off - (off @ d_) * d_) * fw
                else:
                    pos[kk] = c + e2r * (off @ e2k) * fw + e1r * (off @ e1k) * fh
                ring.append(kk)
            for m_ in range(4):
                faces.append([prev[m_], prev[(m_ + 1) % 4], ring[(m_ + 1) % 4], ring[m_]])
            prev = ring
        faces.append(prev[::-1])

    _, _, e1, e2 = hfr[-1]
    top = [hk(1, k) for k in (8, 9, 0, 1, 2)]  # back (little finger) -> front (index), knuckle ring
    bot = [hk(1, k) for k in (7, 6, 5, 4, 3)]
    fl = hlen * (1 - PALM_LEN)  # middle finger length
    for i, (lk, spread) in enumerate(FINGERS):  # little, ring, middle, index
        base = [top[i], top[i + 1], bot[i + 1], bot[i]]
        bc = np.mean([pos[q] for q in base], 0)
        d0 = rot(hdir, e1, spread)
        ln = fl * lk
        pts_, frs = [], []
        p, d, e1r = bc, d0, e1
        for seg, curl in zip(FINGER_SEG, FINGER_CURL):
            ax = np.cross(d, e1r)  # bend toward the palm (down) about the finger's sideways axis
            d, e1r = rot(d, ax, curl), rot(e1r, ax, curl)
            p = p + d * ln * seg
            pts_.append(p)
            frs.append((Q.unit(e1r), Q.unit(np.cross(d, e1r))))
        tube(base, bc, pts_, FINGER_SIZE, (e1, e2), {"name": ("L", "f", i), "frames": frs})
        JOINTS[f"finger{i}"] = [bc] + pts_
    # thumb from the palm face left out above
    base = [hk(0, thumb_k), hk(0, thumb_k + 1), hk(1, thumb_k + 1), hk(1, thumb_k)]
    bc = np.mean([pos[q] for q in base], 0)
    _, _, e1t, e2t = hfr[0]
    tdir = Q.unit(hdir * 0.6 + e2t * 0.6 - e1t * 0.15)  # forward along the palm, a little under it
    t_side = Q.unit(np.cross(tdir, e1t))
    up_t = Q.unit(np.cross(t_side, tdir))
    pts_ = [bc + tdir * 0.055 * S * f_ for f_ in (0.4, 0.75, 1.0)]
    sizes = [(0.013 * S, 0), (0.011 * S, 0), (0.0075 * S, 0)]  # corner radius (m)
    # base offsets are measured in the face's own plane: use the face's two edge directions
    fa = Q.unit(pos[base[1]] - pos[base[0]])
    fb = Q.unit(np.cross(Q.unit(bc - np.mean([pos[hk(0, k)] for k in range(10)], 0)), fa))
    tube(base, bc, pts_, sizes, (fb, fa), {"name": ("L", "t"), "frames": [(up_t, t_side)] * 3, "dir": tdir})
    JOINTS["thumb"] = [bc] + pts_
    # ---- trunk faces ----
    nrows = len(rows) + 1
    for r in range(nrows - 1):
        for a, b in zip(COLS, COLS[1:]):
            if r in (2, 3) and (a, b) in ((48, 90), (90, 120)):
                continue
            faces.append([tk(r, a), tk(r, b), tk(r + 1, b), tk(r + 1, a)])
    # ---- legs ----
    rc = nrows - 1

    def leg_sec(y):
        a, b = sil.front_run(y, 0.12)
        zb, zf = sil.side_run(y)
        return (a + b) / 2, (b - a) / 2, zb, zf

    y_in = L["crotch"] - 0.012
    xc, w, zb, zf = leg_sec(y_in)
    for m_, a in enumerate(Q.CROTCH_IN):
        cf, sf = se(math.cos(math.radians(a)), math.sin(math.radians(a)))
        pos[("L", "ci", 0, m_)] = np.array([xc + w * sf, y_in, (zf if cf >= 0 else -zb) * cf])
    loop = [tk(rc, 0), tk(rc, 22), tk(rc, 48), tk(rc, 90), tk(rc, 120), tk(rc, 180), ("L", "ci", 0, 0), ("L", "ci", 0, 1)]
    faces.append([tk(rc, 0), ("L", "ci", 0, 1), ("L", "ci", 0, 0), tk(rc, 180)])
    c0 = np.array([xc, y_cr, 0.5 * (zb + zf)])
    ang = [math.degrees(math.atan2(pos[q][0] - c0[0], pos[q][2] - c0[2])) for q in loop]
    lk = lambda i, k: loop[k] if i == 0 else ("L", "l", i, k)
    kn, an, cr = L["knee"], L["ankle"], L["crotch"]
    # more rings where the silhouette changes: thigh, 3 around the knee (above, on, below the joint: the rig bends
    # on the middle one), calf bulge, above the ankle, ankle
    leg_y = [cr - 0.08, cr - 0.20] + [kn + d for d in KNEE_RINGS] + [kn - 0.12, kn - 0.22, an + 0.05, an]
    rings = []
    for y in leg_y:
        xc, w, zb, zf = leg_sec(y)
        zm = 0.5 * (zb + zf)
        rings.append([np.array([xc + w * se(math.cos(math.radians(a)), math.sin(math.radians(a)))[1], y,
                                zm + ((zf - zm) if math.cos(math.radians(a)) >= 0 else (zm - zb)) *
                                se(math.cos(math.radians(a)), math.sin(math.radians(a)))[0]]) for a in ang])
    # knee wedge: the rings above and below the knee move toward the knee ring at the back (the crease), so the
    # back faces are short and fold together while the kneecap keeps wide faces (game knee topology)
    k0 = 2 + KNEE_RINGS.index(0.0)
    for i, d in enumerate(KNEE_RINGS):
        if d == 0.0:
            continue
        for k, a in enumerate(ang):
            back = max(0.0, -math.cos(math.radians(a)))
            t = KNEE_PINCH * back
            rings[2 + i][k] = rings[2 + i][k] * (1 - t) + rings[k0][k] * t
    # foot: low-poly wedge like a simple boot (flat sole, straight top from the instep down to a short square toe,
    # boxy sections). It is not subdivided or decimated later (ref_detail pins it), so these rings are final.
    xa, wa, zba, zfa = leg_sec(an + 0.03)
    heel = min(sil.side_run(0.012))
    toe = max(sil.side_run(0.012))
    up, fwd, out = np.array([0, 1.0, 0]), np.array([0, 0, 1.0]), np.array([1.0, 0, 0])
    box = lambda a: se(math.cos(math.radians(a)), math.sin(math.radians(a)), FOOT_BOX)
    e1h = Q.unit(up + 0.9 * fwd)
    ch = np.array([xa + 0.004, 0.05 * S, heel + 0.05 * S])
    rings.append([ch + e1h * 0.055 * S * box(a)[0] + out * wa * 1.05 * box(a)[1] for a in ang])
    a_, b_ = sil.front_run(0.02, 0.12)
    wf, xcf = min((b_ - a_) / 2, 0.05 * S), (a_ + b_) / 2
    z_in = heel + 0.45 * (toe - heel)
    h_in = min(max(sil.foot_top(z_in), 0.06 * S), 0.10 * S)
    h_toe = 0.035 * S
    for frac, wk in ((0.45, 0.95), (0.75, 1.0), (0.97, 0.88)):
        z = heel + frac * (toe - heel)
        h = float(np.interp(z, [z_in, toe], [h_in, h_toe]))  # straight top line
        c = np.array([xa + (xcf - xa) * frac, h / 2, z])
        rings.append([c + up * (h / 2) * box(a)[0] + out * wf * wk * box(a)[1] for a in ang])
    for i, ring in enumerate(rings, start=1):
        for k, p in enumerate(ring):
            pos[lk(i, k)] = p
    rc_ = [np.mean(r, 0) for r in rings]
    JOINTS.update(hip=c0, knee=rc_[leg_y.index(kn)], ankle=rc_[len(leg_y) - 1], heel=rc_[len(leg_y)],
                  ball=rc_[len(leg_y) + 2], toe=rc_[len(leg_y) + 3], crotch_y=L["crotch"], chin_y=L["chin"],
                  crown_y=L["crown"], sh_top_y=L["sh_top"], neck_base_y=y_neck)
    nl = len(rings) + 1
    for i in range(nl - 1):
        for k in range(8):
            faces.append([lk(i, k), lk(i, (k + 1) % 8), lk(i + 1, (k + 1) % 8), lk(i + 1, k)])
    faces += [[lk(nl - 1, k) for k in q] for q in ((0, 1, 2, 3), (4, 5, 6, 7), (0, 3, 4, 7))]
    return pos, faces, rows


def place_head(L):
    """Scale + move the template head (eye level 0, chin ~ -0.12) onto the reference head."""
    # head_planes templates: a closed "Head" + the neck stick "Head_Main" (measure the head, not the stick)
    head = bpy.data.objects.get("Head") or bpy.data.objects["Head_Main"]
    co = np.array([v.co[:] for v in head.data.vertices])
    hd = np.stack([co[:, 0], co[:, 2], -co[:, 1]], 1)
    top_t = hd[:, 1].max()
    skull = L["crown"] - HAIR
    if HEAD_FIT == "chin":
        # the template's REAL chin (lowest point of the front 3 cm, neck tube already cut) onto the reference chin
        front = hd[(hd[:, 2] > hd[:, 2].max() - 0.03) & (hd[:, 1] > NECK_CUT_Y)]
        chin_t = float(front[:, 1].min())
        chin_y = L["chin"] - CHIN_DROP
    else:  # old: a neck tube ring onto the front-view neck landmark (made the head ~20 % too small)
        chin_t, chin_y = CHIN_T, L["chin"]
    s = (skull - chin_y) / (top_t - chin_t)
    y0 = chin_y - chin_t * s
    M = Matrix.Translation((0, -HEAD_DZ, y0)) @ Matrix.Scale(s, 4)
    for ob in [o for o in bpy.data.objects if o.type == "MESH"]:
        ob.data.transform(M)
    return s, y0


def warp_head_width(sil, L, y0, s):
    """Width per height from the chin to the brow onto the reference front silhouette (head + ears + brows together).
    The template's face is a box under the cheeks where the reference narrows to a V: the cheekbones were 1-2 cm
    narrow and the chin wide. Factor per 1 cm row, smoothed, clamped, faded to 1 at both ends."""
    obs = [o for o in bpy.data.objects if o.type == "MESH"]
    co = np.concatenate([np.array([v.co[:] for v in o.data.vertices]) for o in obs])
    z_lo, z_hi = L["chin"] - CHIN_DROP, y0 + HEAD_WARP_TOP * s  # template eye level = 0
    zs = np.arange(z_lo, z_hi + 1e-6, 0.01)
    f = []
    for z in zs:
        sl = co[np.abs(co[:, 2] - z) < 0.005]
        cur = float(np.abs(sl[:, 0]).max()) if len(sl) else 0.0
        a, b = sil.front_run(z)
        f.append(np.clip(((b - a) / 2) / cur, 1 - HEAD_WARP_MAX, 1 + HEAD_WARP_MAX) if cur > 0.02 else 1.0)
    f = np.convolve(np.pad(f, 1, mode="edge"), [0.25, 0.5, 0.25], mode="valid")
    f[0] = f[-1] = 1.0  # fade at both ends
    for o in obs:
        for v in o.data.vertices:
            if z_lo <= v.co.z <= z_hi:
                v.co.x *= float(np.interp(v.co.z, zs, f))
    return {"z": [round(float(z), 3) for z in zs], "factor": [round(float(x), 3) for x in f]}


def jaw_taper():
    """Template jaw is a box (half width 66 mm under the mouth vs 72 mm at the cheekbone). Make the front view a
    trapezoid: per height, the face's outer half width goes onto a straight line from the cheekbone (JAW_TOP) to the
    chin corners (JAW_CHIN). Only the part beyond JAW_CORE is squeezed (mouth and chin centre keep their size);
    never widened. Under the chin the squeeze fades out by the neck loop. Template coords, before place_head."""
    obs = [o for o in bpy.data.objects if o.type == "MESH"]
    head = bpy.data.objects["Head_Main"]
    co = np.array([v.co[:] for v in head.data.vertices])
    width = lambda y: float(np.abs(co[np.abs(co[:, 2] - y) < 0.008][:, 0]).max())
    w_top = width(JAW_TOP)
    ys = np.arange(JAW_LOOP_Y, JAW_TOP + 1e-6, 0.005)
    g = []
    for y in ys:
        if y >= JAW_CHIN_Y:
            t = w_top + (JAW_CHIN - w_top) * (JAW_TOP - y) / (JAW_TOP - JAW_CHIN_Y)
        else:  # under the chin: same squeeze as the chin row, fading to none at the loop
            t = None
        g.append(t)
    gc = []
    for y, t in zip(ys, g):
        cur = width(y)
        if t is None:
            gc.append(None)
        else:
            gc.append(min(1.0, (t - JAW_CORE) / max(cur - JAW_CORE, 1e-4)))
    g_chin = next(v for y, v in zip(ys, gc) if v is not None)
    gf = [v if v is not None else 1 + (g_chin - 1) * (y - JAW_LOOP_Y) / (JAW_CHIN_Y - JAW_LOOP_Y)
          for y, v in zip(ys, gc)]
    gf = np.convolve(np.pad(gf, 1, mode="edge"), [0.25, 0.5, 0.25], mode="valid")
    gf[-1] = 1.0
    gf[0] = 1.0
    for o in obs:
        for v in o.data.vertices:
            if ys[0] <= v.co.z <= ys[-1] and abs(v.co.x) > JAW_CORE:
                k = float(np.interp(v.co.z, ys, gf))
                v.co.x = math.copysign(JAW_CORE + (abs(v.co.x) - JAW_CORE) * k, v.co.x)
    return {"y": [round(float(y), 3) for y in ys], "squeeze": [round(float(x), 3) for x in gf]}


def cut_neck_tube(head):
    """Delete the template's straight neck tube (3 rings of 10 under the jaw) and return the open loop left:
    under the chin at the front, the skull base at the back, 10 vertices on the body's columns.
    Returns {(col, vertex index)} with col on the 0..360 circle (0 = front, 90 = character's left)."""
    bm = bmesh.new()
    bm.from_mesh(head.data)
    tube = [v for v in bm.verts if v.co.z < NECK_CUT_Y]
    keep = {e.other_vert(v) for v in tube for e in v.link_edges} - set(tube)  # the loop above the tube
    bmesh.ops.delete(bm, geom=tube, context="VERTS")
    bm.verts.index_update()
    loop = {v.index for v in keep}
    bm.to_mesh(head.data)
    bm.free()
    me = head.data
    assert len(loop) == 10, len(loop)
    out = set()
    for i in loop:
        p = Q.to_hd(me.vertices[i].co)
        t = math.degrees(math.atan2(p[0], p[2] + 0.01)) % 360
        col = min(COLS + [360 - c for c in COLS[1:-1]], key=lambda c: min(abs(c - t), 360 - abs(c - t)))
        out.add((col, i))
    assert len({c for c, _ in out}) == 10, sorted(out)
    return out


def fit_top_ring(head, sil, ring_idx, y_narrow):
    """The kept template ring is a thin tube section: widen it to the reference neck and move its back half to the
    reference back-of-neck line; the front (under the chin) stays."""
    vs = [head.data.vertices[i].co for i in ring_idx]
    y = float(np.mean([v.z for v in vs]))
    zs = [-v.y for v in vs]
    cm, back = (min(zs) + max(zs)) / 2, min(zs)
    a, b = sil.front_run(y_narrow)  # at the ring's own height the front silhouette is the jaw, not the neck
    sx = ((b - a) / 2) / max(abs(v.x) for v in vs)
    sb = 1 + NECK_BACK_K * ((cm - sil.side_run(y)[0]) / (cm - back) - 1)
    for v in vs:
        v.x *= sx
        z = -v.y
        if z < cm:
            v.y = -(cm + (z - cm) * sb)
    return dict(y=round(y, 3), scale_x=round(sx, 3), scale_back=round(sb, 3))


def fit_neck(head, sil, ring_idx):
    """Move + widen the template's neck onto the reference neck at the ring height, fading out upward.
    The reference neck sits further back and is thicker than the template's: without this the neck leans forward
    off the trapezius. The fade stops just under the chin at the front and at the skull base at the back, so the
    face stays put and the back of the neck runs straight up into the skull (side-view line of the sketch)."""
    co = lambda i: head.data.vertices[i].co
    ring = [co(i) for i in ring_idx]
    y_r = float(np.mean([v.z for v in ring]))
    zs = [-v.y for v in ring]
    mx, cm, md = max(abs(v.x) for v in ring), (min(zs) + max(zs)) / 2, (max(zs) - min(zs)) / 2
    zb, zf = sil.side_run(y_r - 0.006)
    a, b = sil.front_run(y_r - 0.006)
    tx, cr, td = (b - a) / 2, (zb + zf) / 2, (zf - zb) / 2
    sx, sz = tx / mx, td / md
    for v in head.data.vertices:
        y, z = v.co.z, -v.co.y
        zr = z - cm
        y_top = y_r + float(np.interp(zr, [-0.02, 0.05, 0.085], [NECK_FADE_BACK, NECK_FADE_THROAT, 0.0]))
        if y >= y_top:
            continue
        t = max(0.0, min(1.0, (y_top - y) / (y_top - y_r)))
        w = t * t * (3 - 2 * t)
        v.co.x *= 1 + (sx - 1) * w
        z_new = z + w * (cr + zr * sz - z)
        v.co.y = -z_new
    return dict(scale_x=round(sx, 3), scale_z=round(sz, 3), shift_z=round(cr - cm, 3))


NECK_BASE_DROP = 0.017  # neck base ring this far below the front-view neck landmark
NECK_PIN = os.environ.get("RB_NECK_PIN", "0") == "1"  # 0: the neck is smoothed + faceted with the torso (no collar)
NECK_BACK_K = 0.5  # how far the top neck ring goes to the reference back line (1 = all: juts under the skull)
NECK_RINGS = 1  # rings between the jaw loop and the neck base
SCM_DEPTH = 0.004  # throat pit at the front centre (m)
SCM_BULGE = 0.003  # sternocleidomastoid ridge forward (m)
NECK_CUT_Y = -0.142  # template head coords: the lower 2 rings of the straight neck tube go; ring y = -0.132 is the
# last clean 10-ring (the loop above it has in-between vertices, stitching there leaves holes)
CHIN_T = -0.153  # template height matched to the front-view "neck" landmark (head scale of v1-v4, 0.971)
HEAD_FIT = os.environ.get("RB_HEAD_FIT", "chin")  # "chin": real chin -> reference chin (v8); "tube": old CHIN_T
CHIN_DROP = 0.024  # reference chin bottom is this far below the front-view "neck" landmark (sheet face, row 162 vs 157)
NECK_GAP = 0.022  # neck base ring at least this far below the lowest point of the head's jaw loop
NECK_TILT = os.environ.get("RB_NECK_TILT", "1") == "1"  # base ring follows the jaw loop (trapezius slope)
NECK_DEBUG = {}
TRAP_GAP = 0.01  # tilted base: sides this far under the jaw loop
TRAP_LIFT = {0: 0.0, 22: 0.35, 48: 0.85, 90: 1.0, 120: 1.0, 180: 0.7}  # 0 = throat height, 1 = TRAP_GAP under the jaw
MID_SPREAD = {0: 1.0, 22: 0.6, 180: 1.0}  # columns whose rows 1-2 are spread (1 = fully)
TRAP_FLARE = 1.55  # tilted base: half width cap at the sides (x narrowest neck): the slope's upper edge
NECK_FLARE = 1.4  # neck base half width <= this x the narrowest neck (a short neck meets the trapezius slope)
HEAD_DZ = float(os.environ.get("RB_HEAD_DZ", "-0.015"))  # head moved back (reference face sits further back)
NECK_FADE_BACK = 0.11  # fade height above the ring at the back of the neck (skull base)
NECK_FADE_THROAT = 0.07  # ... at the throat (front of the ring); the chin (further forward) is not moved

PART = {"head": 0, "trunk": 1, "neck": 2, "arm": 3, "hand": 4, "finger": 5, "thumb": 6, "leg": 7, "crotch": 8}


def face_label(f):
    """(part code, ring) of a face from its vertex keys (side, kind, index, sub)."""
    kinds = []
    for k in f:
        kind = k[1]
        if kind == "t" and k[0] == "L" and k[3] in (0, 1, 2, 3) and len(k) == 4 and k[3] not in COLS[1:]:
            kind = "thumb"  # thumb keys ("L", "t", segment, corner) share the trunk letter
        kinds.append((kind, k[2]))
    names = {"t": "trunk", "n": "neck", "a": "arm", "h": "hand", "f": "finger", "thumb": "thumb", "l": "leg", "ci": "crotch"}
    order = ["thumb", "f", "h", "a", "l", "ci", "n", "t"]  # most specific kind wins (arm root ring = trunk keys)
    kind = next(o for o in order if any(kd == o for kd, _ in kinds))
    ring = min(i for kd, i in kinds if kd == kind)
    if kind in ("a", "l") and any(kd in ("t", "ci") for kd, _ in kinds):
        ring = 0  # first band: its root ring is made of trunk / crotch keys -> band 0 (band i = ring i -> i + 1)
    return PART[names[kind]], int(ring)


def main():
    sil = Sil()
    L = landmarks(sil)
    bpy.ops.wm.open_mainfile(filepath=HEAD_SRC)
    head = bpy.data.objects["Head_Main"]
    F.remove_neck_cap(head)
    raw = cut_neck_tube(head)  # template coords: the tube goes, the loop under the jaw stays
    if JAW_TAPER:
        NECK_DEBUG["jaw_taper"] = jaw_taper()
    s, y0 = place_head(L)
    if HEAD_WARP:
        NECK_DEBUG["head_warp"] = warp_head_width(sil, L, y0, s)
    neck_fit = fit_top_ring(head, sil, [i for (c, i) in raw], L["chin"])
    vidx = {}
    left = {}
    for (c, i) in raw:
        p = Q.to_hd(head.data.vertices[i].co)
        if c <= 180:
            vidx[("M" if c in (0, 180) else "L", "n", 0, c)] = i
            left[c] = p
        else:
            vidx[("R", "n", 0, 360 - c)] = i
    pos, faces, rows = build(sil, L, left)
    bm = bmesh.new()
    bm.from_mesh(head.data)
    lay = bm.verts.layers.int.new("pin")  # before taking vertex references: a new layer invalidates them
    bm.verts.ensure_lookup_table()
    head_v = list(bm.verts)
    verts = {}

    def vert(key):
        if key in verts:
            return verts[key]
        if key in vidx:
            v = head_v[vidx[key]]
        else:
            p = pos[("L",) + key[1:]].copy() if key[0] == "R" else pos[key].copy()
            if key[0] == "R":
                p[0] = -p[0]
            if key[0] == "M":
                p[0] = 0.0
            v = bm.verts.new(Q.to_bl(p))
        verts[key] = v
        return v

    mirror = lambda k: ("R",) + k[1:] if k[0] == "L" else k
    # face labels for later parts (clothes): "part" (PART codes) and "ring" (trunk row, arm / leg ring index;
    # the smallest of the face's corners). Template head faces keep 0.
    l_part = bm.faces.layers.int.new("part")
    l_ring = bm.faces.layers.int.new("ring")
    for f in faces:
        part, ring = face_label(f)
        for ff in [bm.faces.new([vert(k) for k in f])] + (
                [bm.faces.new([vert(mirror(k)) for k in f][::-1])] if any(k[0] == "L" for k in f) else []):
            ff[l_part] = part
            ff[l_ring] = ring
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    # "pin": kept as built by ref_detail (no subdivision, no muscles, no decimation): head, neck, foot
    for v in head_v:
        v[lay] = 1
    for k, v in verts.items():
        if (NECK_PIN and (k[1] == "n" or (k[1] == "t" and k[2] == 0))) or v.co.z < L["ankle"] + 1e-3:
            v[lay] = 1
    bm.to_mesh(head.data)
    bm.free()
    head.name = "Character"
    G.flat(head)
    sizes = {}
    for p in head.data.polygons:
        sizes[len(p.vertices)] = sizes.get(len(p.vertices), 0) + 1
    st = {"character": G.stats(head), "faces_by_sides": sizes, "closed": G.closed(head), "symmetry": G.symmetry(head),
          "head_scale": round(s, 3), "neck_fit": neck_fit, "neck": NECK_DEBUG, "landmarks_m": {k: round(v, 3) for k, v in L.items() if k != "arm_axis"},
          "trunk_rows_y": [round(y, 3) for y in rows]}
    os.makedirs(OUT, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, f"{TAG}.blend"))
    json.dump(st, open(os.path.join(OUT, f"stats_{TAG}.json"), "w"), indent=1)
    bl = lambda v: [round(float(c), 5) for c in Q.to_bl(v)] if hasattr(v, "__len__") else round(float(v), 5)
    jt = {k: ([bl(p) for p in v] if isinstance(v, list) else bl(v)) for k, v in JOINTS.items()}
    json.dump(jt, open(os.path.join(OUT, f"joints_{TAG}.json"), "w"), indent=1)
    print("RB_STATS", json.dumps(st))


if __name__ == "__main__":
    main()
