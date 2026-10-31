TASK: write ONLY the function buildHair(ctx: RCtx). It currently is an empty stub (void ctx;), so the zombie's head is a bald, smooth, pale egg. Add the hair.

=== TARGET (what the reference picture looks like, in words) ===
An adult man in his 30s, shaggy brown hair, 5 to 9 cm long, messy and uneven like he has not combed it for months:
- Thick on top and at the back, strands falling forward over the forehead in an uneven fringe that reaches down to about the eyebrows on one side and stays higher on the other.
- Covers the top half of both ears and the temples; at the back it reaches down to the nape (about 4 cm above the shoulder line); sides are shorter than the top.
- Looks like a MASS of many separate strands and clumps with gaps between them, not a smooth cap or helmet.
- Dark brown, hex #5E5144, with lighter dry tips and darker roots (vary each clump by about +-25% brightness).

=== GEOMETRY OF THE SCALP (copy this table into your function, heights in metres above the Head bone at y = HY = 1.585) ===
Each row: [h, rs (side radius), rf (front-back radius), z (centre in z)], ALREADY multiplied by the 1.07 head scale:
  [0.110, 0.0835, 0.1049, 0.010]
  [0.150, 0.0920, 0.1124, 0.000]
  [0.170, 0.0942, 0.1156, -0.005]
  [0.190, 0.0899, 0.1113, -0.010]
  [0.210, 0.0803, 0.1017, -0.015]
  [0.225, 0.0642, 0.0856, -0.017]
  [0.235, 0.0428, 0.0535, -0.017]
  [0.243, 0.0021, 0.0021, -0.017]
Interpolate linearly between rows. A point on the scalp at height h and angle a (a = 0 straight ahead (+Z), a = +-PI/2 at the sides, a = PI at the back) is:
  x = -rs * sin(a);  y = HY + h;  z = zc + rf * cos(a)
Outward normal on the horizontal plane is (-sin(a)/rs, 0, cos(a)/rf) normalised (mix in +Y near the top).

=== WHAT TO BUILD ===
1. Use mb.use('hair') then build everything with ellipsoid(): each strand clump is a long thin ellipsoid:
   radii (0.005 to 0.008, length/2 = 0.018 to 0.045, 0.005 to 0.008) with the long axis along local +Y.
   Orient it with q = new Quaternion().setFromUnitVectors(v(0,1,0), dir) where dir is the strand direction (unit vector).
   Centre = rootPoint + dir * (length/2) - a little inside (root sunk 0.004 m into the scalp).
2. Root points: about 170 clumps, at random (hash) positions on the scalp:
   - top (h from 0.19 to 0.24, all angles): dir = outward normal blended 50% with the "down and slightly forward" direction, so hair lies over the skull.
   - fringe: 14 clumps at the front hairline (a from -0.9 to +0.9, h around 0.20 to 0.215): dir points forward (+z) and down (-y), length 0.06 to 0.09 so tips reach h about 0.165 to 0.18 (over the forehead). Make the left and right side different lengths.
   - sides: 40 clumps (|a| from 1.1 to 2.0, h from 0.12 to 0.20): dir = down and slightly outward, length 0.045 to 0.065; the ones just above the ears must cover the top of the ears (ears are at |a| about PI/2, h about 0.135).
   - back: 50 clumps (|a| from 2.2 to PI, h from 0.07 to 0.2): dir = down, length 0.05 to 0.08; the lowest ones end near h = 0.06 (nape).
   - add random jitter of +-20 degrees to every direction.
3. Weight: const wHead = rigid(skel, 'Head'); use it for everything. Paint: { base: new Color(C.hair) } with brightness scaled per clump by 0.75 + 0.5 * hash(ctx.seed, 700 + i) (clone the colour; lighten the tip a bit by using a slightly lighter second small ellipsoid at the end of long clumps if you have room).
4. Deterministic: use hash(ctx.seed, index) only (no Math.random). hash returns a number in [0, 1).

=== API available in the file already ===
const v = (x,y,z) => new Vector3(x,y,z);  const HY = REAL_HEAD_Y;  const C = { hair: '#5e5144', ... };
import { Color, Quaternion, Vector3 } from 'three';  import { hash } from '../hash';  import { rigid, ellipsoid } from '../mesh';
ellipsoid(mb, centre: Vector3, radii: Vector3, weigh, paint: {base: Color}, detail = 1, q?: Quaternion)   // detail 0 or 1 only, keep it small
rigid(skel, 'Head') returns the weigher. ctx = { mb, skel, seed, V }.

KEEP IT COMPACT: under 120 lines, small helper functions and loops, comments one line each.
