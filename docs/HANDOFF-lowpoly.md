# Handoff: low-poly base bodies (F0–F3 and F5 done, next F4)

Written 2026-11-01. Read this first in a new session. It stands on its own and explains both what was decided and why. More detail is in `docs/10-roadmap-lowpoly.md`.

## 1. Goal and the user's intent

The user wants a "recipe" that **recreates low-poly characters like the reference packs** procedurally in Three.js. The first target is a **base male and female body** with no accessories that:
- moves correctly;
- has real volume (a solid, closed mesh, nothing see-through);
- matches the references' style (~1.5–2k tris, faceted).

After that come detailing (face, hair, clothes) and zombie variants.

The user liked the Argon/Gemini model for 3D style and our low-poly as a base. The reference FBX files are used **as a source of numbers**: they were measured, and their meshes are never copied into the repo.

User preferences:
- Replies in **Indonesian**, short and direct.
- **No Claude/AI attribution** in commits or PRs.
- Ask before downloading anything.
- Commit or push only when asked.

## 2. Where things stand

The project is `C:\Mirza Personal\model 3d maker`, a git repo on branch `main` with remote `mirzamhy/3d-model-maker`. F0–F2 are committed (0ffbc42..d97614c); F3 may still be uncommitted. The earlier head and Zombie 2 work from previous sessions is uncommitted too.

The viewer is Vite at http://localhost:5195 (launch config `zombie-maker`, or run `npm run dev`). Its **Gaya model** panel has:
- **Rangka low-poly (F1)**: wooden mannequin on the low rig, male and female side by side, with the reference outline.
- **Badan low-poly (F2)**: the one-piece closed body, male and female side by side.

Test poses: `Jalan normal` (hwalk), `Jongkok` (squat), `Angkat tangan` (armsup), plus the old zombie poses.

| Phase | Status |
|---|---|
| F0 measure references | done |
| F1 rig + proportions | done |
| F2 closed body | first version done, with 5 fingers |
| F3 weights + automated motion tests | done (see roadmap §8; a thin slit at the arm hole remains) |
| F5 silhouette "training" | done (roadmap §9; male 0.910, female 0.866 mean IoU, near the ceiling set by the references' own spread) |
| F4 body sliders, F6 head, F7 accessories/zombie, F8 GLB + Mixamo test | not started |

Current numbers: 1556 tris per body, 63 bones + 10 helper bones (driven by `driveHelpers`). F3 added `poseTest.ts`, `helpers.ts` and `__zm.poseTest/holdTest/skin`. `checkClosed` reports 0 open, 0 doubled and 0 flipped edges for both male and female.

## 3. Files

| File | What it does |
|---|---|
| `tools/ref/measure-fbx.mjs` | `node tools/ref/measure-fbx.mjs <out.json> <a.fbx> ...`. Parses FBX with three's FBXLoader in node (DOM shims at the top). Per body mesh it records height, joints (canonical Mixamo names), tris per bone, loops, 6 plane-cut sections per bone (`slices` with `t`), a whole-body profile and a `torso` profile (horizontal cuts of trunk-bone triangles every 1 %). Output: `tools/ref/out/ref-profiles.json`. |
| `tools/ref/summarize.mjs` | Averages the bodies per group into `ref-summary.json` and `ref-silhouettes.svg`. It also writes **`src/zombie/lowbody/refBody.json`**, the data the generator reads. |
| `src/zombie/lowbody/bodySpec.ts` | `bodySpec(femininity 0..1, height?)` turns the data into metres (joints, bone sections with `f`, trunk rows, `crotchY`, silhouette). Also `trunkAt` and `boneAt`. |
| `src/zombie/lowbody/rigLow.ts` | `lowBoneDefs(spec)`: Mixamo-named rig (Hips, Spine, Spine1, Spine2, Neck, Head, Shoulder, Arm, ForeArm, Hand, HandThumb1-2, HandIndex/Middle/Ring/Pinky 1-3, UpLeg, Leg, Foot, ToeBase, plus `_End` markers). `fingerLayout(spec)` spreads the measured mitten over 4 fingers. |
| `src/zombie/lowbody/mannequin.ts` | F1 check model (`buildLowRig`). Only the HandMiddle bones get finger pieces. |
| `src/zombie/lowbody/body.ts` | F2 builder (`buildLowBody`) plus `checkClosed`. Results go to `globalThis.__lowbodyCheck`. |
| `src/zombie/build.ts` | Styles `lowrig` and `lowbody`; `buildZombie(seed, style, { femininity })`. |
| `src/viewer/main.ts` | Pair view for lowrig and lowbody (male x=-0.95, female x=+0.95; overlays for both, labels on the first only). Camera distance 7.2. `__zm.look(tx,ty,tz,px,py,pz)` was added. The reference outline is hidden outside T-pose. |
| `src/zombie/pose.ts` | Poses `hwalk`, `squat` and `armsup` were added. |
| `docs/10-roadmap-lowpoly.md` | Full roadmap, F0 numbers table, F1 and F2 notes. |

Reference sources: the 6 zips in `C:\Users\mirza\Downloads` (polyart-zombies, casual-lowpoly-male-rig, low-poly-people sample, low-poly-male-character, low-poly-hero-man, muscular base mesh). They are extracted to the session scratchpad `...\scratchpad\lp\<zip name>\` and must be re-extracted in a new session. Their licenses have not been checked; keep them out of the repo.

## 4. Decisions and why

**Rig**
- **Mixamo names everywhere**, so Mixamo clips and the existing `armPose` finger curls (Index/Middle/Ring/Pinky 1-3, Thumb1-3) work without remapping.
- **Spine2 is inserted at 45 % from Spine1 to Neck.** The references have only one long chest bone, and Mixamo has three spine bones.

**Reference data**
- **Stature is measured from the Head joint for headwear models.** The police woman (cap + bun) and lpFemale_zombie_E (big hair) had built-in hair or headwear that inflated height and head size. They are auto-flagged when head depth > 26 cm or width > 22 cm. Their stature = Head joint y / (1 − 0.124), and their head and neck sizes are left out of the averages.
- **The male group includes 6 zombies.** In T-pose they are the same shape. Accepted as is.

**Topology** (copies how the references are box-modelled, with no union or boolean)
- **One fixed topology** instead of overlapping tubes, because overlapping tubes were what made bodies "tembus":
  - trunk rings of 12;
  - legs split from the bottom ring as half the ring (7 points) plus 1 shared crotch point, giving an 8-loop per leg;
  - arms grow from a 2×2-quad patch cut from the chest side (8 boundary points);
  - the thumb grows from 1 cut hand quad;
  - fingers grow from a 5+5 knuckle grid joined to the hand ring by `bridge`;
  - fan caps at the crown and the tips.

**Fixes to the raw data**
- **Pelvis rows below the Hips joint are widened to wrap the thighs.** The trunk cut excludes thigh triangles, which made a pinched "diaper" shape. The thigh starts at crotch − 3 % H.
- **Every section radius is at least 45 % of the mean.** The knee cut gave the shin a negative front radius, because kneecap triangles belong to the thigh bone.
- **Sections are smoothed 1-2-1 twice along each limb**, to remove knee and elbow ledges.
- **The neck ring is round, sized from the Neck bone sections.** The trunk cut there mixes chin and collar.
- **Shoulder-top row:**
  - no upward smoothing and never in front of the row below, because the sample above it is already the **chin** (this caused the "two bumps" at the neck base);
  - its middle (throat and nape) leans `0.5·cos²` toward the neck ring and dips 1.2 % H at the front and 0.6 % H at the back.
- **The jaw row (first head row) tilts chin-down, narrows to jaw width, and its back follows the neck.** This removes the "helmet" ledge. Every per-vertex dip is clamped to stay above the row below; without the clamp the female body had 4 flipped edges.
- **Separate fingers instead of the references' mitten**, because the user asked for finger detail and the budget allowed it (references average ~1650 tris).
  - The finger layout comes from the measured mitten: knuckle line, length, hand width and thickness.
  - Length relative to the middle finger: 0.93, 1, 0.94, 0.76.
  - Segment lengths: 46 / 30 / 24 %.
  - The thumb is scaled 0.7–0.75×, because the mitten thumb was too fat.
- **Winding is fixed by topology, not by an inside point.** `Topo.triangles()` first guesses with the inside point, then propagates consistent winding across shared edges, then flips everything if the signed volume is negative. The inside-point guess alone failed on the flat knuckle band.

## 5. Verify the way the last session did

- Typecheck: `npx tsc --noEmit`.
- Closed check: after `__zm.set({style:'lowbody'})`, read `globalThis.__lowbodyCheck`. It must show `closed: true` for both male and female.
- Renders: widen the pane first with `resize_window` (1400–1700 wide). Then `__zm.look(...)` and `await __zm.capture('name')` write `renders/name.png`; read that file. Screenshots of the narrow pane are too small to judge.
- After a code edit the page reloads through HMR and the style resets to default. Wait about 2.5 s, then call `__zm.set({...})` again. A JS call running during the reload gets cut off, so rerun it.
- Get bone positions via `__zm.actors()[0].rig.bones[name].getWorldPosition(new V())`, where `V = bones.Hips.position.constructor`.

## 6. Next: F3 (weights and automated motion tests)

1. **Shoulder.** A dark fold appears at the front of the shoulder when the arm hangs down (visible in `hwalk`). Rework the weights of the arm-patch ring and the Shoulder/Arm blend. Consider an extra ring between the chest patch and Arm f 0.22, or deltoid weights that blend over two rings.
2. **Twist bones** for the forearm and upper arm (candy-wrapper), plus an extra loop if needed.
3. **Automated pose battery** (T, A, squat, arms up, elbow 140°, knee 150°, twist, walk cycle). Measure:
   - triangle self-intersections, via a BVH (three-mesh-bvh would need installing, so ask first) or a simple grid;
   - joint volume ratio, target ≥ 0.85;
   - flipped normals after skinning;
   - 4-view captures.

   Expose the results like `__lowbodyCheck`.
4. Smaller issues: the crotch triangle notch, a small fold behind the knee in squat, the chin overhang (the head gets replaced in F6 anyway).

## 7. Other loose ends (not urgent)

- **Commit the work.** Ask first. Use several focused commits and no AI attribution.
- **Stale docs** from older work: "66 bones" mentions, `docs/README.md`, `docs/08-eksperimen-argon.md`.
- **Mannequin fingers:** the F1 mannequin only draws the HandMiddle finger pieces.
- **Zombie 2 work from earlier sessions** (file-baked head in `src/zombie/head/`, `headFile*.json`, `tools/head/bake-lowpoly.mjs`): finished, but it still needs zombie details. The license of the Sketchfab-sourced head is unchecked.
