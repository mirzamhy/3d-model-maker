TASK: improve ONLY the function buildHair(ctx: RCtx) (current version below). I rendered it. Here is what it looks like, in words.

=== WHAT THE RENDER LOOKS LIKE NOW ===
Side view of the head: a BALD, smooth, pale-white scalp with about 170 separate dark-brown "beans" (thin ellipsoids) stuck on it like seeds or bristles. Between the beans you see bare white skin everywhere, so it reads as a bald head with spikes, not hair. The fringe beans over the forehead stick out forward like a row of pencils. The back of the head is mostly bare. Nothing covers the top of the ears.

=== TARGET ===
Dense, shaggy, dark-brown hair that fully covers the top, back and sides of the skull, with a ragged uneven edge and a few loose clumps hanging lower. From a distance it must read as one hair mass; only the lower edge and a few tips are separate clumps.

=== HOW TO FIX ===
1. SCALP CAP (new, this is the main fix): a hair-coloured shell that covers the skull so no skin shows through.
   mb.use('hair'); build it with loft(mb, stations, { sides: 32, front: v(0,0,1), weigh: wHead, capEnd: 'flat', paint: { base: new Color(C.hair) }, open: (phi, ring, c) => ... }).
   Stations (Station = { c: v(0, HY + h, z), rs, rf }) from this table, each rs and rf made 0.007 m larger than the skull (so the cap sits just outside the skin). Skull rows [h, rs, rf, z] (already x1.07):
     [0.060, 0.0749, 0.0910, 0.025]
     [0.090, 0.0803, 0.1017, 0.015]
     [0.110, 0.0835, 0.1049, 0.010]
     [0.150, 0.0920, 0.1124, 0.000]
     [0.170, 0.0942, 0.1156, -0.005]
     [0.190, 0.0899, 0.1113, -0.010]
     [0.210, 0.0803, 0.1017, -0.015]
     [0.225, 0.0642, 0.0856, -0.017]
     [0.235, 0.0428, 0.0535, -0.017]
     [0.243, 0.0021, 0.0021, -0.017]
   Use smoothStations(stations, 3). Add a small per-vertex outward bump with shape: (i, phi, c) => 0.004 * (fbm(ctx.seed + 3, c.x * 40 + phi * 5, c.y * 40, c.z * 40, 1) - 0.5) so the cap surface is lumpy, not smooth. (fbm(seed, x, y, z, freq, octaves=4) returns 0..1 and is imported from '../noise'.)
   Hairline = which faces to LEAVE OUT with open(phi, ring, c): let h = c.y - HY and a = Math.abs(fromFrontSigned(phi)) (0 = front, PI = back). Return true (open) when
     a < 1.2 and h < 0.205 - 0.035 * a   (forehead hairline, higher at the centre, lower at the temples)
     or 1.2 <= a < 1.9 and h < 0.115       (leave the ear area and cheek free below this)
     or a >= 1.9 and h < 0.075             (back of the head reaches down to the nape)
   fromFrontSigned is imported from '../mesh'; add it to the import list if needed.
   The cap itself is brown (#5E5144 scaled by 0.7) so even with gaps between clumps it never shows skin.
2. CLUMPS on top of the cap: increase to about 300 clumps and make each clump THICKER and shorter so they overlap: radii (0.008 to 0.013, half-length 0.02 to 0.04, 0.006 to 0.009). Use ellipsoid detail 0 for ordinary clumps (cheap, 20 faces; the shading is smooth so it still looks round) and detail 1 only for the 14 fringe clumps.
   Orient strands to LIE ALONG the head surface (direction = tangent of the scalp pointing away from the crown, blended 35% with straight down), not sticking out radially. Root them INSIDE the cap (sunk 0.006 m) so only the outer part shows.
   Distribution: top (h 0.19-0.243): 60 clumps; upper sides and temples: 80; back: 90 (down to h = 0.07); fringe: 14 hanging over the forehead down to h about 0.17 to 0.185 (left side shorter than right); plus 20 loose clumps on the lower back and sides that hang 1 to 2 cm below the cap edge.
   Brightness per clump 0.7 + 0.6 * hash(...); tips slightly lighter.
3. Keep everything deterministic with hash(ctx.seed, i). Triangle budget for the whole function: under 9000 triangles.

=== API available in the file already ===
const v = (x,y,z) => new Vector3(x,y,z);  const HY = REAL_HEAD_Y;  const C = { hair: '#5e5144', ... };
import { Color, Quaternion, Vector3 } from 'three';  import { hash } from '../hash';  import { fbm, gauss } from '../noise';
import { MeshBuilder, loft, smoothStations, rigid, ellipsoid, fromFrontSigned, type Station } from '../mesh';
ellipsoid(mb, centre, radii: Vector3, weigh, paint: {base: Color}, detail = 1, q?: Quaternion)   // q = new Quaternion().setFromUnitVectors(v(0,1,0), dir) makes the long local Y axis point along dir
loft options used here: sides, front, weigh, paint: { base: Color, rule?: (p) => Color }, capEnd: 'flat', open(phi, ring, c), shape(i, phi, c)
rigid(skel, 'Head') returns the weigher. ctx = { mb, skel, seed, V }.

KEEP IT COMPACT: under 130 lines, small helper functions, one-line comments.
