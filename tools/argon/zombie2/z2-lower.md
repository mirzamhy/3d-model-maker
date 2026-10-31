TASK: rewrite ONLY buildLower(ctx: RCtx) (current version below): trousers, belt, buckle, shoes, plus torn knees and frayed hems. Keep the same function name and signature.

=== WHAT THE RENDER LOOKS LIKE NOW ===
Front view: the trousers are two plain, smooth, straight tubes, identical, with no front crease, no wrinkles, a clean round hem and no damage. At the waist the pelvis piece and the belt are separate stair-stepped blocks and there is a small black notch (you see the inside) between the belt and the jacket hem. The shoes are two small dark-brown rounded blobs that look like stumps or loafers: no sole, no toe cap, no laces, shorter than the foot.

=== TARGET (the reference picture, in words) ===
Worn, dusty dark-grey (#3E3E3E) straight-cut suit trousers on a thin man:
- A continuous waistband at y = 1.03 to 1.06 with a dark-brown leather belt (#2A211B, 3.5 cm wide) and a small dull-brass rectangular buckle at the front centre.
- A sharp front crease down each leg, soft horizontal wrinkles at the knee and where the thighs meet the pelvis (sit-folds), and bagginess around the shins.
- BOTH KNEES ARE TORN OPEN: a ragged hole about 9 cm tall and 7 cm wide on the front of each knee, uneven edge with loose threads; the grey, bruised skin of the knee shows through.
- The hems are frayed: they end just above the floor over the shoes, irregular lower edge with a few long torn strips, the left leg torn worse; the trouser bottoms are wider than the ankle (cover the top of the shoe).
- Dirt stains (clothAt grime 0.6), darker at the knees and hems.
- Shoes: brown-black (#33261F) leather lace-up Oxford dress shoes, 0.28 m long, scuffed, with a thin dark sole (2 cm), a low heel (3 cm), a rounded toe cap, and visible laces (5 small lace bars across the instep).

=== HOW TO BUILD (metres, +Y up, +Z front, +X = zombie's left; legs are mirrored with s = +1 left, -1 right) ===
Bone positions for reference: UpLeg (0.10, 0.95, 0.0), Leg/knee (0.106, 0.52, 0.015), Foot/ankle (0.112, 0.09, -0.015), ToeBase (0.116, 0.025, 0.12), Toe_End (0.118, 0.025, 0.205).
Buckets: mb.use('pants') for trousers; mb.use('leather') for belt and shoes; mb.use('metal') for the buckle; mb.use('skin') for the knee skin.

1. PELVIS / WAIST piece: loft sides 48, front v(0,0,1), weigher(skel, ['Hips','Spine','LeftUpLeg','RightUpLeg']): stations (rs, rf multiplied by V.bulk):
     y 0.80: rs 0.170, rf 0.125, zc 0.000
     y 0.92: rs 0.172, rf 0.126, zc 0.000
     y 1.04: rs 0.166, rf 0.122, zc -0.004
     y 1.07: rs 0.164, rf 0.120, zc -0.006 (top edge, capEnd 'flat')
   It must overlap the legs below (legs start at y 0.95) so there is no gap. Paint: clothAt(ctx, V.pants, p, 0.5).
2. BELT: loft sides 48 at y 1.025 to 1.062, rs/rf = pelvis rs/rf at that height + 0.004, colour V.belt, weigher the same as the pelvis, capStart and capEnd 'none'. Buckle: box at (0, 1.043, zFront + 0.004) with half sizes (0.022, 0.016, 0.003), bucket 'metal', colour #8c7a52, plus a smaller dark bar inside it.
3. LEGS (loop s): loft along the leg with smoothStations(stations, 5), sides 28, front v(0,0,1), weigher(skel, [`${P}UpLeg`, `${P}Leg`, `${P}Foot`]) (P = s > 0 ? 'Left' : 'Right'). Stations (cx multiplied by s):
     y 0.98: cx 0.100, z 0.000, rs 0.098, rf 0.108 (inside the pelvis piece)
     y 0.80: cx 0.101, z 0.004, rs 0.093, rf 0.104
     y 0.52: cx 0.106, z 0.015, rs 0.070, rf 0.078 (knee)
     y 0.30: cx 0.109, z 0.003, rs 0.064, rf 0.068
     y 0.12: cx 0.111, z -0.012, rs 0.062, rf 0.066 (wider hem)
     y 0.06: cx 0.112, z -0.012, rs 0.066, rf 0.070 (hem edge, hem option 0.03 for ragged drop; larger drop on the left leg: hem: s > 0 ? 0.05 : 0.03)
   (multiply rs, rf by V.bulk). Front crease: in shape() add +0.004 * gauss(fromFrontSigned(phi), 0, 0.07) for all rings; wrinkles: + 0.006 * (fbm(ctx.seed + 31 + (s > 0 ? 0 : 7), c.x * 25 + phi * 4, c.y * 10, c.z * 25, 1) - 0.5) * (1 + 1.2 * gauss(c.y, 0.52, 0.08)) (stronger at the knee).
   KNEE HOLES: open(phi, ring, c) returns true when |c.y - 0.52| < 0.045 + 0.012 * (hash(ctx.seed, 800 + Math.floor(phi * 20)) - 0.5) && Math.abs(fromFrontSigned(phi)) < 0.5 + 0.12 * (hash(ctx.seed, 830 + Math.floor((c.y - 0.4) * 80)) - 0.5) (ragged edge).
   KNEE SKIN (so the hole is not empty): a short loft in bucket 'skin' under each hole: stations y 0.44 to 0.60 along the same centre line with radii 0.008 smaller than the trouser leg, sides 20, skin colour skinAt(ctx, p, 0.15, 0.1), weigher same as the leg. Place mb.use('skin') before and mb.use('pants') after.
   Frayed hem: also use the loft's hem option and add a few long torn strips: leave out some faces at the bottom edge with open() when c.y < 0.09 && hash(ctx.seed, 860 + Math.floor(phi * 14) + (s > 0 ? 0 : 20)) < 0.22.
4. SHOES (loop s): bucket 'leather', colour V.shoe (#33261F). Build the upper as a loft along the foot from the heel to the toe: front = v(0, 1, 0) (so rf is the vertical thickness), weigher(skel, [`${P}Foot`, `${P}ToeBase`, `${P}Toe_End`]). Stations along z (heel to toe), centre x = s * lerp(0.110, 0.118, t), y centre and half sizes:
     z -0.075: y 0.055, rs 0.040, rf 0.050 (heel, closed with capStart 'flat')
     z 0.010: y 0.062, rs 0.050, rf 0.062 (ankle opening area under the trouser hem)
     z 0.100: y 0.048, rs 0.050, rf 0.042 (instep)
     z 0.180: y 0.038, rs 0.049, rf 0.032 (ball of the foot)
     z 0.245: y 0.030, rs 0.038, rf 0.026 (toe cap, capEnd 'point' with tipLen 0.01)
   Because the loft axis is horizontal use sides 20 and the 'front' vector v(0,1,0). (Stations list order along +z.)
   Sole: a flat thin loft or box under the shoe: from z -0.07 to 0.245, thickness 0.02 (y 0.0 to 0.02), width 0.10 at the ball and 0.08 at the heel, colour #17120f. Heel block: box 0.07 x 0.03 x 0.08 at the heel under the sole.
   Laces: 5 small boxes across the instep at z = 0.02, 0.045, 0.07, 0.095, 0.12 (y about the top of the shoe at that z, half sizes (0.02, 0.0015, 0.003), colour #1a1410, slightly raised).
   Scuffs: paint rule lightens the colour by 25% where fbm(...) > 0.62 near the toe.

=== API available in the file already ===
const v = (x,y,z) => new Vector3(x,y,z);  const C = { pants:'#3e3e3e', shoe:'#33261f', belt:'#2a211b', ... };
imports: Color, Quaternion, Vector3 from 'three'; hash from '../hash'; fbm, gauss from '../noise';
 MeshBuilder, loft, smoothStations, weigher, rigid, ellipsoid, box, fromFrontSigned, type Station, type Weigher from '../mesh';
 skinAt, clothAt, bloodRun, type RCtx from '../real/variant'.
clothAt(ctx, baseColor: Color, p: Vector3, grime = 0.25): Color ; skinAt(ctx, p, dark0to1, red0to1): Color
box(mb, centre, half: Vector3, weigh, paint: {base: Color}, ax?, ay?, az?)  // oriented box
loft(mb, stations, { sides, front, weigh, paint: { base: Color, rule?: (p) => Color }, capStart?, capEnd?: 'flat'|'point'|'none', tipLen?, open?(phi, ring, c), shape?(i, phi, c), hem? })
ctx = { mb, skel, seed, V } with V.bulk, V.pants, V.shoe, V.belt (Colors).

KEEP IT COMPACT: under 150 lines; helper functions allowed above buildLower (for example legs(ctx), shoes(ctx), belt(ctx) that buildLower calls); one-line comments.
