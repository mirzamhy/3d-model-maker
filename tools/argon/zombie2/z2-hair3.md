TASK: fix ONLY buildHair(ctx: RCtx) (current version below). I rendered it from the front/side. Here is what it looks like, in words.

=== WHAT THE RENDER LOOKS LIKE NOW ===
The brown cap now covers the skull, good. Three problems:
1. The FRINGE is a row of about 14 long, fat, evenly spaced beans hanging straight down from the forehead like comb teeth, and they hang down to the MOUTH LEVEL, so they cover both eyes and the nose. Eyes are at h = 0.148 above the head bone; the fringe tips must never go below h = 0.185.
2. The cap's front edge (the hairline) is a visible STAIR-STEP / jagged pixel pattern, because the loft only has 32 sides and the open() test removes whole quads.
3. The side clumps hang down in a regular curtain past the ears to the jaw. They should stop at about h = 0.115 (ear top is at h about 0.15, ear bottom 0.11), and the curtain must not cover the cheek.
4. All clumps look like identical fat beans. Real hair is thinner and varied.

=== TARGET ===
Messy, shaggy, dark-brown hair. The fringe is short and ragged: a few thin clumps over the forehead that end ABOVE the eyebrows (tips between h = 0.19 and h = 0.205), some sweeping sideways. The eyes, nose and mouth are completely visible. The hairline is smooth and slightly irregular. Sides cover the upper ear only. Back reaches the nape.

=== CHANGES TO MAKE ===
a) Cap loft: sides 64 (not 32). Keep the 3x smoothStations. To get a smooth hairline instead of stair-steps, do NOT use open() to cut the front; instead keep the cap as a closed shell and make its front lower edge by clamping the station list: build the cap from only the stations with h >= 0.115, and then OPEN the front sector with open(phi, ring, c) using the same rule as before but ALSO lower the cut so it matches a smooth curve: hairlineH(a) = 0.215 - 0.03 * a^2 (a = |fromFrontSigned(phi)| in radians, 0 front). With 64 sides the steps become half as big; the fringe clumps (below) will hide the rest.
b) Fringe: 22 clumps (not 14), thin (radii 0.004 to 0.007), half-length 0.012 to 0.03, ROOTS on the hairline curve hairlineH(a) for a in [-0.95, 0.95] with random jitter; direction = forward-down mixed with a random sideways sweep (dir = (sin(sweep), -0.5, 0.8) normalised, sweep random in [-0.9, 0.9], different per clump); tip must stay above h = 0.19 (clip the length: len = min(len, (rootH - 0.19) * 1.6 + 0.01)).
c) Sides: clumps rooted at |a| in [1.2, 2.0], h in [0.13, 0.2], dir mostly down, length 0.03 to 0.05, so the lowest tip ends at h >= 0.115.
d) Back: keep, but vary length 0.04 to 0.075 and make 40% of the clumps thinner (radii 0.005 to 0.008).
e) Vary clump radii with hash so they are not identical; most clumps thinner than now (0.005 to 0.009), a few fat ones (0.011).
f) Keep the total under 9000 triangles. Deterministic hash(ctx.seed, i) only.

=== API available in the file already ===
const v = (x,y,z) => new Vector3(x,y,z);  const HY = REAL_HEAD_Y;  const C = { hair: '#5e5144', ... };
imports: Color, Quaternion, Vector3 from 'three'; hash from '../hash'; fbm, gauss from '../noise'; loft, smoothStations, rigid, ellipsoid, fromFrontSigned, type Station from '../mesh'.
ellipsoid(mb, centre, radii: Vector3, weigh, paint: {base: Color}, detail = 1, q?: Quaternion)  // q = new Quaternion().setFromUnitVectors(v(0,1,0), dir)
loft options: sides, front, weigh, paint, capEnd: 'flat', open(phi, ring, c), shape(i, phi, c). rigid(skel, 'Head'). ctx = { mb, skel, seed, V }.
KEEP IT COMPACT: under 130 lines.
