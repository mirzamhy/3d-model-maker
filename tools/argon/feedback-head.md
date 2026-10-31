I rendered your file. I cannot send images, so here is exactly what the renders look like, described in words. Then the task for THIS round.

=== WHAT THE RENDER LOOKS LIKE (your current file) ===

Face close-up (roar pose, head tilted up, jaw should be open, dark green horror lighting):
- The head is a smooth, pale lilac-pink EGG, like a mannequin head or a stocking pulled over a face. It is longer than it is wide, with a slightly pointed chin.
- There are NO visible eyes. Where the eyes should be there are only two faint, shallow, slightly darker smudges, barely deeper than the forehead. No white eyeballs, no pupils, nothing glints.
- There are NO visible teeth and NO open mouth. The lower half of the face is one continuous smooth surface. In the roar pose the jaw bone rotates but nothing visibly opens: no dark gap, no teeth, no mouth cavity.
- The nose is not visible as a hole; there is a faint vertical ridge down the middle of the face.
- The cheeks look slightly saggy, not hollow and skull-like. Cheekbones do not catch light.
- The red tint (meant for the mouth / nasal hole) appears as a pink blush on the cheek and on one side of the forehead instead of around the mouth and nose.
- From the side view the head silhouette is a plain oval, the ears are tiny bumps, and the back of the skull is flat.
- Overall impression: faceless, not scary, nothing reads as a skull.

What it SHOULD look like (target):
- Gaunt skull face. Deep, almost black, round eye sockets about 3 cm across, with a milky pale-grey eyeball sunk at the back of each socket (eyeball visible, slightly glowing).
- Strong brow ridge throwing shadow over the sockets.
- Nose rotted away: a dark, triangular nasal hole in the middle of the face.
- Prominent cheekbones with clearly sunken, shadowed cheeks below them.
- No lips: a horizontal row of long, yellowed, uneven teeth exposed across the front of the mouth, upper row fixed to the skull, lower row on the jaw. When the jaw opens (roar), a dark red-black mouth cavity appears between the rows.
- Raw red flesh around the mouth and nasal hole, purple-dark bruising around the eyes.

=== WHY (from your code) ===
1. Eyes are placed at a hard-coded point (x = ±0.031, z = 0.044). The face surface at eye height is ~0.10 m in front of the head centre, so the eyeballs are buried ~5 cm inside the head. Same for the teeth (radius 0.035-0.045) and the mouth cavity (z = 0.03).
2. Only 7 key rings: the gaussians in faceFeature get flattened between rings and the shape reads as an egg.
3. The paint angle uses fromFrontSigned(Math.atan2(p.x, p.z)), which subtracts PI/2 twice, so face colouring lands on the wrong part of the head.
4. Feature amplitudes are fine; the geometry just does not resolve them.

=== TASK FOR THIS ROUND: ONLY THE HEAD ===
Rewrite ONLY the function buildHead.

Requirements for buildHead:
a) Profile with at least 16 key rings [h, rs, rf, zCentre] from h = -0.006 (small under-chin ring) to h = 0.243 (near-point top), widest at h ~0.17. Wider rf than rs (head deeper than wide). Centre z moves forward at the jaw (+0.03 at h 0.02) and back at the crown (-0.017). Multiply radii by HR = 1.07. smoothStations sub 3, sides 36, capStart 'flat', capEnd 'flat'.
b) Write `keyAt(h)` (linear interpolation of the key table, returns {rs, rf, z}) and `surface(h, a, inset)`:
   x = -(rs - inset) * sin(a);  z = zCentre + (rf - inset) * cos(a);  y = HY + h.
   This matches loft's convention (phi = PI/2 is +Z front, a = fromFrontSigned(phi)).
c) In the paint rule compute a = -Math.atan2(p.x, p.z - keyAt(h).z). Darkness = min(1, max(0, -faceFeature(h, a)) / 0.022) * 0.72 so every cavity is dark. Red: around mouth gauss(h, 0.085, 0.026)*gauss(|a|, 0, 0.55), nasal hole, bruise around eyes. Mouth band h 0.079..0.095, |a| < 0.62 -> colour #1c0605.
d) Eyes: outer = surface(0.148, ±0.47); outward normal n = normalize(outer - (0, outer.y, keyAt(0.148).z)); centre = outer - 0.031 * n; eyeball ellipsoid radii (0.0135, 0.0125, 0.0135) detail 2 in bucket 'eye'; small grey pupil at centre + 0.0122 n.
e) Mouth cavity: dark ellipsoid #160404 centred at (0, HY + 0.084, keyAt(0.084).z + 0.04) radii (0.05, 0.022, 0.035).
f) Teeth (bucket 'teeth'): for each tooth c = surface(h, a, 0.011); out = horizontal outward normal; tan = (out.z, 0, -out.x); box half sizes (0.0036, len/2, 0.003) with axes (tan, up, out), small random tilt about out. Upper 12 teeth at h 0.098 hanging down (Head weight), a from -0.68 to 0.68; lower 11 at h 0.071 pointing up (Jaw weight), a from -0.6 to 0.6; len 0.011-0.016; ~10% missing; colour between #c4b27c and #6e5a32.
g) Jaw weighting: vertices with p.y < HY + 0.084 and p.z > 0.012 -> Jaw, else Head.
h) Ears: flattened ellipsoids at (±0.087, HY + 0.135, -0.018), radii (0.007, 0.027, 0.015), rotated ∓0.25 rad about Y.

