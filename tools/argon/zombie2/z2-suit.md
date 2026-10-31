TASK: rewrite ONLY buildSuit(ctx: RCtx): it must now build ONLY the suit JACKET (body, collar, lapels, sleeves with cuffs, tears). The old code in the function also builds a shirt: REMOVE the shirt (another function, buildInner, will build the shirt, vest and tie).

=== WHAT THE RENDER LOOKS LIKE NOW ===
Front view, T-pose: the "jacket" is a plain light-grey rectangular box from the shoulders to the thigh, with a wide straight opening down the front. No collar, no lapels, no buttons, no shoulder shape. The sleeves are smooth identical tubes with no elbow bend, no cuffs and no wrinkles. The bottom edge is a row of rectangular tabs (it looks like a cardboard fringe). The cloth is a flat colour with no wear.

=== TARGET (the reference picture, in words) ===
A worn grey wool two-button business suit jacket, #9A9A9A, dull, dusty and wrinkled, hanging open on a thin undead man:
- Notch lapels: from the collar base at the neck, two flat folded-back strips run down the front edges to about the waist (y = 1.12), each about 6 cm wide at the chest and narrowing, folded outwards (they stand 1 to 1.5 cm proud of the jacket). A collar band (3 to 4 cm tall) runs round the back of the neck and flares open at the front, joining the lapels.
- The front is open: the opening is narrow at the hem (half-angle about 0.25 rad), widest at the chest (about 0.6 rad), so the vest and shirt are visible between the lapels.
- Shoulders: padded, slightly squared, the shoulder seam about 0.23 m from the centre line. The jacket hangs straight from the chest and ends at y = 0.82 (just below the belt, over the buttocks).
- Sleeves: long, end at the wrist at x = 0.73 with a cuff ring (a slightly wider band 3 cm long, darker, with 2 small buttons). Each sleeve is a bit baggy, with bunched wrinkles around the elbow (x about 0.5) and long diagonal creases near the armpit.
- Wear: fabric is dusty (use clothAt with grime 0.5), darker around the armpits, lower hem and cuffs. Small reddish-brown stains (not blood pools) on the chest and shoulders (use bloodRun lightly, colour #5a3a30 at most 25% strength). Elbows are worn through: on each sleeve cut a ragged hole about 5 cm wide at the elbow (use the loft open() callback) so the skin/shirt shows; frayed edge lighter grey.

=== HOW TO BUILD (dimensions in metres, +Y up, +Z front, +X = zombie's left) ===
Use mb.use('shirt') for the jacket cloth (it has a fabric bump shader); mb.use('metal') only for buttons.

1. Jacket body: loft with smoothStations(stations, 6), sides 56, front v(0,0,1), weigh = weigher(skel, ['Hips','Spine','Spine1','Spine2','Neck','LeftShoulder','RightShoulder']). Stations { c: v(0, y, zc), rs, rf } (rs = half width, rf = half depth):
     y 0.82: rs 0.200, rf 0.140, zc 0.00
     y 0.95: rs 0.190, rf 0.133, zc -0.005
     y 1.10: rs 0.185, rf 0.130, zc -0.010
     y 1.30: rs 0.205, rf 0.138, zc -0.015
     y 1.40: rs 0.225, rf 0.130, zc -0.020
     y 1.47: rs 0.170, rf 0.105, zc -0.022
     y 1.52: rs 0.095, rf 0.085, zc -0.022
   Multiply rs and rf by V.bulk. Front opening: open(phi, ring, c) returns true when |fromFrontSigned(phi)| < half, where t = (c.y - 0.82) / 0.58 clamped 0..1 and half = 0.25 + 0.4 * Math.sin(Math.min(1, t * 1.15) * Math.PI * 0.5) (about 0.25 at the hem, about 0.65 near the chest); also open everything above y = 1.51 in the front half (|a| < 1.3) so the neck is free.
   Wrinkles: shape(i, phi, c) = 0.007 * (fbm(ctx.seed + 11, c.x * 14 + phi * 3, c.y * 6, c.z * 14, 1) - 0.5) * (c.y < 1.3 ? 1 : 0.3) + a gentle sag 0.004 * Math.sin(phi * 3) (so it is not a perfect ellipse). Paint rule: (p) => clothAt(ctx, V.jacket, p, 0.5), then lerp 20% towards #5a3a30 by bloodRun for small stains.
2. Collar: loft ring flaring around the neck: stations y 1.47 to 1.56 (rs 0.07 to 0.085, rf 0.065 to 0.075, zc -0.02), sides 24, open front (|a| < 0.75), weigher(skel, ['Spine2','Neck']), colour clothAt darker (x0.85).
3. Lapels: for each side s (+1 left, -1 right): a long thin loft along the front opening edge from (s*0.05, 1.50, 0.09) to (s*0.115, 1.12, 0.128), 8 stations, each station rs = lerp(0.032, 0.012, t) (half width across the strip), rf = 0.006 (thickness), sides 8, front = v(0, 0, 1). Push the lapel 0.01 outward. Same weigher as the body, cloth colour x1.05 lighter at the edge.
4. Buttons: two small dark metal ellipsoids (radius 0.009) on the body edge at y 1.05 and y 0.96 (centre line, z = rf), bucket 'metal', paint #2a2a2a.
5. Sleeves, each side s: weigh = weigher(skel, [`${P}Shoulder`, `${P}Arm`, `${P}ForeArm`]) with P = s>0 ? 'Left' : 'Right'. Loft along x (front = v(0, 1, 0)): stations (cx, y 1.44, z) with half sizes rs (vertical) and rf:
     x 0.19: rs 0.075, rf 0.075 (shoulder cap, blends into the body)
     x 0.30: rs 0.062, rf 0.064
     x 0.50: rs 0.054, rf 0.058 (elbow)
     x 0.66: rs 0.048, rf 0.050
     x 0.73: rs 0.044, rf 0.046 (cuff end)
   All x multiplied by s. z of the centre is -0.03 to -0.04. Wrinkles by gaussian near the elbow: shape = 0.006 * gauss(c.x * s, 0.5, 0.07) * (fbm(...) - 0.3) + small noise. Elbow hole via open(): open when Math.abs(c.x * s - 0.5) < 0.03 && Math.abs(fromFrontSigned(phi) - (s > 0 ? 1.6 : -1.6)) < 0.55 (ragged edge: add hash noise on the threshold). Cuff: a second short loft x 0.70 to 0.735, radii +0.004, darker colour, with 2 tiny button ellipsoids.
   Sleeve colour: clothAt(ctx, V.jacket, p, 0.55).

=== API available in the file already ===
imports: Color, Quaternion, Vector3 from 'three'; hash from '../hash'; fbm, gauss from '../noise';
 MeshBuilder, loft, smoothStations, weigher, rigid, ellipsoid, box, fromFrontSigned, type Station, type Weigher from '../mesh';
 makeVariant, skinAt, clothAt, bloodRun, type RCtx from '../real/variant'.
const v = (x,y,z) => new Vector3(x,y,z);  const C = { jacket:'#9a9a9a', vest:'#6b6b6b', shirt:'#e6e2dc', tie:'#4b3b2d', ... };
clothAt(ctx, baseColor: Color, p: Vector3, grime = 0.25): Color      // cloth tone with wear and grime
bloodRun(ctx, p, x0, width, yTop, yBottom): number 0..1 (streaks)    // use only for small stains here
weigher(skel, ['Spine','Spine1',...]): Weigher ; ellipsoid(mb, centre, radii: Vector3, weigh, paint:{base: Color}, detail = 1, q?)
loft(mb, stations: Station[], { sides, front, weigh, paint: { base: Color, rule?: (p) => Color }, capStart?, capEnd?, open?(phi, ring, c), shape?(i, phi, c), hem?, jitter? })
ctx = { mb, skel, seed, V } with V.bulk, V.jacket (Color).

KEEP IT COMPACT: under 140 lines; use small helper functions (e.g. a local function sleeve(s)) and loops; one-line comments.
