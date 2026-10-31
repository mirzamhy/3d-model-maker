TASK: write ONLY buildInner(ctx: RCtx), currently an empty stub (void ctx;). It builds the clothes UNDER the suit jacket: dirty white dress shirt (with collar and cuffs), grey waistcoat (vest) with buttons, and a brown necktie. (The jacket, hands, trousers are other functions: do not build them.)

=== WHAT THE RENDER LOOKS LIKE NOW ===
Front view: the jacket (light grey, open at the front, lapels, collar) hangs open, and between the lapels you see BARE CHEST SKIN (pinkish with a blood smear) all the way down to the belt. Nothing covers the chest or belly, so it looks like the man wears only a jacket. There is no shirt collar, no tie, no vest. At the belly there is a jagged hole where the shirt used to be, and the belt area shows skin.

=== TARGET (the reference picture, in words) ===
Under the open jacket: a dirty off-white button-up shirt (#E6E2DC, yellowed and creased) with a classic stand-up collar that peeks above the lapels around the neck; over the shirt a grey waistcoat (#6B6B6B), sleeveless, closed with 5 dark buttons, with a deep V at the neck so the shirt and a brown tie (#4B3B2D) show in the V; the tie is long, hangs over the vest, with a slightly loose, crooked knot at the collar and a pointed end resting just above the belt; the shirt is tucked into the trousers. Only small dusty, reddish-brown stains. No blood pools.

=== HOW TO BUILD (metres, +Y up, +Z front, +X = zombie's left) ===
Use mb.use('shirt') for all cloth here (shirt, vest, tie); mb.use('metal') for buttons. Body weights: const wT = weigher(skel, ['Hips','Spine','Spine1','Spine2','Neck']); collar weights: weigher(skel, ['Spine2','Neck']).

1. SHIRT body: loft(mb, smoothStations(stations, 5), { sides: 48, front: v(0,0,1), weigh: wT, capStart: 'flat', ... }). Stations { c: v(0, y, zc), rs, rf } (multiply rs, rf by V.bulk). They must lie INSIDE the jacket (jacket half width at chest is 0.205 to 0.225) and OUTSIDE the skin chest:
     y 0.88: rs 0.150, rf 0.108, zc 0.000
     y 1.05: rs 0.158, rf 0.112, zc -0.008
     y 1.25: rs 0.170, rf 0.118, zc -0.013
     y 1.40: rs 0.182, rf 0.112, zc -0.018
     y 1.47: rs 0.140, rf 0.095, zc -0.020
     y 1.51: rs 0.075, rf 0.068, zc -0.020
   Placket: shape(i, phi, c) adds a small crease line down the centre (+0.003 * gauss(fromFrontSigned(phi), 0, 0.05)) plus soft wrinkles 0.005 * (fbm(ctx.seed + 21, c.x * 20 + phi * 4, c.y * 8, c.z * 20, 1) - 0.5) that are stronger around the belly.
   Paint: (p) => clothAt(ctx, V.shirt, p, 0.45) with small reddish-brown stains: lerp 25% towards #6a4a3a where bloodRun(ctx, p, 0.03, 0.06, 1.35, 1.0) > 0.2.
2. SHIRT collar: stand-up collar loft around the neck: stations from y 1.49 to y 1.58 (rs 0.062 to 0.068, rf 0.058 to 0.064, zc -0.018), sides 24, open front: open(phi) returns true when |fromFrontSigned(phi)| < 0.28 (a narrow gap in front where the tie knot sits). Two small pointed collar flaps: two small boxes or ellipsoids at (±0.04, 1.55, 0.06), radii (0.02, 0.012, 0.006), tilted outward by 20 degrees. Colour as the shirt, slightly lighter.
3. SHIRT cuffs peeking out of the jacket sleeves: for each side s (+1 left, -1 right): a short ring loft along x from s*0.725 to s*0.775 at y 1.44, z -0.03, front v(0,1,0), radii rs 0.042, rf 0.044, sides 20, weigher(skel, [`${P}ForeArm`, `${P}Hand`]) with P = s > 0 ? 'Left' : 'Right'; colour shirt, small grime.
4. VEST (waistcoat): loft sides 56, stations slightly OUTSIDE the shirt (+0.007) and INSIDE the jacket:
     y 0.98: rs 0.163, rf 0.116, zc -0.006
     y 1.10: rs 0.168, rf 0.119, zc -0.010
     y 1.25: rs 0.178, rf 0.124, zc -0.014
     y 1.38: rs 0.186, rf 0.118, zc -0.018
     y 1.44: rs 0.165, rf 0.105, zc -0.020
   Top and neckline: the vest has a deep V: open(phi, ring, c) returns true when c.y > 1.20 && Math.abs(fromFrontSigned(phi)) < ((c.y - 1.20) / 0.20) * 0.62 (V opening at the front, widening towards the top), and also true for c.y > 1.43 && Math.abs(fromFrontSigned(phi)) < 1.9 (open top between the shoulders at the front and sides, to leave the neck/shoulders to the shirt), leaving a back panel (|a| > 1.9). The bottom edge is a straight hem at y = 0.98 with a small point in the centre front (use the hem argument 0.02 only for the centre: or simply leave it straight).
   Paint: clothAt(ctx, V.vest ?? new Color(C.vest), p, 0.5), use new Color(C.vest) (V has no vest field). Darker, dusty.
   Buttons: 5 small dark ellipsoids (radius 0.0065, colour #1d1d1d, bucket 'metal') at the centre line of the vest front, y = 1.17, 1.12, 1.07, 1.02, 0.98 + 0.01; z = vest surface at that y (compute from the station table: z = zc + rf + 0.003, interpolating linearly between the stations).
5. TIE: knot = ellipsoid at (0.006, 1.495, 0.078) radii (0.017, 0.016, 0.014) tilted a little (crooked); blade = a flat loft from the knot down to y 1.02: 8 stations; centre x = 0.012 * sin(t * 2.2) (slight swing), centre y from 1.48 down to 1.02, z = the shirt/vest front surface + 0.006 (it lies on the vest: use z = 0.125 - 0.012 * t + 0.006, roughly the vest surface), half width rs = lerp(0.014, 0.030, smoothstep) then narrowing at the tip to 0.012, half thickness rf = 0.004, sides 8, front = v(0, 0, 1), capEnd: 'point'. Colour C.tie (#4b3b2d) with a subtle diagonal stripe pattern: rule(p) => base darkened 12% where Math.floor((p.x + p.y) / 0.018) % 2 === 0. Add a short second shorter blade behind it (the keeper) only if you have room.

=== API available in the file already ===
const v = (x,y,z) => new Vector3(x,y,z);  const C = { vest:'#6b6b6b', shirt:'#e6e2dc', tie:'#4b3b2d', ... };
imports: Color, Quaternion, Vector3 from 'three'; hash from '../hash'; fbm, gauss from '../noise';
 MeshBuilder, loft, smoothStations, weigher, rigid, ellipsoid, box, fromFrontSigned, type Station, type Weigher from '../mesh';
 skinAt, clothAt, bloodRun, type RCtx from '../real/variant'.
clothAt(ctx, baseColor: Color, p: Vector3, grime = 0.25): Color ; bloodRun(ctx, p, x0, width, yTop, yBottom): number 0..1
ellipsoid(mb, centre, radii: Vector3, weigh, paint: {base: Color}, detail = 1, q?: Quaternion)  // q = new Quaternion().setFromUnitVectors(v(0,1,0), dir) or setFromAxisAngle
loft(mb, stations, { sides, front, weigh, paint: { base: Color, rule?: (p) => Color }, capStart?, capEnd?: 'flat'|'point'|'none', open?(phi, ring, c), shape?(i, phi, c) })
ctx = { mb, skel, seed, V } with V.bulk, V.shirt (Color).

KEEP IT COMPACT: under 140 lines; helper functions allowed above buildInner; one-line comments. A helper like lerpAt(table, y) to interpolate the station table is useful.
