TASK: rewrite ONLY the function buildBody (neck, chest skin, hands). I rendered your current version; I cannot send images, so here is what it looks like in words.

=== WHAT THE RENDER LOOKS LIKE NOW ===
Hands (lunge pose, arms reaching forward, fingers clawed):
- The hands look like pale WHITE GLOVES floating in the air. Between the end of the jacket sleeve and the hand there is an empty GAP of about 3 cm: you see the background through it, no wrist, no forearm.
- The palm is a short, thin, flat tube, about the width of two fingers; it reads as a cuff or bandage, not a palm. No back-of-hand volume, no knuckles.
- Fingers are thin straight sticks of equal thickness ending in pointed tips; the orange nail boxes float slightly above the finger tips.
- The thumb sticks out sideways like a peg, detached from the palm, the thumb mound ellipsoid floats inside the palm.
- In the crawl pose the fingers pass through the floor and the hand looks like a bunch of twigs.

Neck and chest:
- The neck is a thin pale pipe, too long and too narrow (looks like a mannequin neck), ending abruptly under the jaw.
- On the chest, where the V-neck opens, the blood looks like big square ORANGE-RED TILES / pixel blocks, because the chest skin has very few vertices.

=== WHAT IT SHOULD LOOK LIKE ===
- A gaunt, bony adult male hand, ~19 cm long, connected to a visible bony wrist and forearm skin that continues INSIDE the sleeve (no gap at any pose).
- Palm: broad and flat, ~8.5 cm wide, ~2.5 cm thick, slightly cupped, with a raised thumb mound at the base of the thumb and knuckle bumps on the back.
- Fingers: three segments each, thicker at the base (r ~0.0095) tapering to r ~0.007 at the tip, slight bulges at each knuckle joint, dark yellow-grey nails lying FLAT on the top of the last segment, finger tips stained dark red.
- Thumb: starts from the side of the palm near the wrist, angled forward ~45 degrees, thicker than the fingers.
- Skin colour: same rotting skin (skinAt) with darker veins; knuckles slightly redder.
- Neck: thick (rs ~0.055, rf ~0.05), from inside the chest (y ~1.36) into the head (HY + 0.03), with two tendons running diagonally from behind the ears to the collarbone, and an Adam's apple bump.
- Chest skin: smooth, enough vertices (>= 40 sides, sub 6) so blood (bloodRun with V.bloodDark) runs in soft streaks, no blocks.

=== CONSTRAINTS ===
- Bone positions (world, left side; mirror x for right): Hand at (0.76, 1.438, -0.03); finger bases Index (0.862, 1.434, 0.001), Middle (0.866, 1.434, -0.021), Ring (0.862, 1.434, -0.043), Pinky (0.852, 1.434, -0.063); phalanx lengths Index [0.048,0.03,0.025], Middle [0.052,0.034,0.026], Ring [0.049,0.032,0.025], Pinky [0.038,0.025,0.022]; Thumb joints (0.782,1.428,0.0) (0.812,1.42,0.03) (0.838,1.414,0.05) (0.862,1.41,0.064). ForeArm bone at (0.5, 1.44, -0.04).
- The hand lies horizontally in T-pose: fingers point along +x (left) / -x (right), palm faces DOWN (-y), back of hand faces up (+y). Use front = (0,1,0) for finger and palm lofts so rf is the vertical thickness and rs the width across.
- Forearm/wrist skin loft from x 0.62 to 0.80 weighted to ForeArm + Hand.
- Palm weighted to Hand (+ finger base bones at the knuckle end). Each finger weighted to its own three bones; nails use the same weigher as the last segment.
- Mirror everything with s = +1 (Left) / -1 (Right).

- KEEP THE CODE COMPACT: under 150 lines, no comments longer than one line, use small helper functions and loops. Your previous reply was cut off by the output length limit.
