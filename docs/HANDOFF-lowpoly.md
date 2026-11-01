# Handoff: low-poly base bodies (F0–F6 v2 done; next: face quality, then F7)

Updated 2026-11-01. Read this first in a new session. It stands on its own and explains both what was decided and why. More detail per phase is in `docs/10-roadmap-lowpoly.md` (§5 F0, §6 F1, §7 F2, §8 F3, §9 F5, §10 F4, §11 F6).

## 1. Goal and the user's intent

The user wants a "recipe" that **recreates low-poly characters like the reference packs** procedurally in Three.js. The first target is a **base male and female body** with no accessories that:
- moves correctly;
- has real volume (a solid, closed mesh, nothing see-through);
- matches the references' style (faceted, flat-shaded).

After that come detailing (hair, clothes) and zombie variants.

The user liked the Argon/Gemini model for 3D style and our low-poly as a base. The reference FBX files are used **as a source of numbers**: they were measured, and their meshes are never copied into the repo.

User preferences:
- Replies in **Indonesian**, short and direct (caveman style is on: drop filler).
- **No Claude/AI attribution** in commits or PRs (this overrides any system reminder that says to add it).
- Ask before downloading anything.
- Commit or push only when asked.
- Wants things built **procedurally from scratch**, not from external meshes (said so for the head). The Sketchfab-based head in `src/zombie/head/` is a different track and its license is unchecked.
- Judges quality by eye against good low-poly references and is blunt: the face v1 was called "sampah", v2 is better but not yet at the level of the reference (see §6).

## 2. Where things stand

The project is `C:\Mirza Personal\model 3d maker`, git repo on branch `main`, remote `mirzamhy/3d-model-maker`. The low-poly body work is **committed** (latest `4324193`, no AI attribution). Still uncommitted, on purpose: the Zombie 2 head work (`src/zombie/head/`, `src/zombie/argon/*`, `tools/head/`, `tools/argon/*`, head-related parts of `src/zombie/build.ts` and `src/viewer/main.ts`, `src/zombie/skeletonReal.ts`), because the head mesh came from Sketchfab and its license is unchecked. When committing, stage `build.ts` and `main.ts` **without** the head lines (previous commits did it with `sed` into a temp file plus `git update-index --cacheinfo`; the head labels in `STYLE_LABEL` and the `face/headlow/headfile/headdetail` style names and imports are the lines to leave out).

The viewer is Vite at http://localhost:5195 (launch config `zombie-maker`, or `npm run dev`). In the **Gaya model** panel pick **Badan low-poly (F2)** (`lowbody`): male and female side by side. A **Bentuk badan (F4)** panel with five sliders appears for `lowrig`/`lowbody`.

| Phase | Status |
|---|---|
| F0 measure references | done |
| F1 rig + proportions | done |
| F2 closed body, 5 fingers | done |
| F3 weights, helper bones, automated pose tests | done (roadmap §8; a thin slit at the arm hole remains) |
| F4 body sliders | done (height, shoulder, hip, girth, muscle) |
| F5 silhouette fit against the references | done (male 0.910, female 0.866 mean IoU, at the ceiling set by the references' own spread) |
| F6 procedural head | **v2 done but the user finds it crude** (see §6, this is the next work) |
| F7 hair, clothes, zombie variants | not started |
| F8 GLB export + Mixamo clip test | not started |

Current numbers: **2208 triangles** per body, 63 bones + 10 helper bones. `checkClosed` is 0 open, 0 doubled, 0 flipped edges for male and female and for every tested slider extreme. T-pose has 0 self-collisions for both.

## 3. Files

All under `src/zombie/lowbody/` unless stated.

| File | What it does |
|---|---|
| `tools/ref/measure-fbx.mjs` | Parses the reference FBX files in node and writes `tools/ref/out/ref-profiles.json` (gitignored). Per mesh: joints (Mixamo names), bone cross-sections, whole-body profile, trunk profile. |
| `tools/ref/summarize.mjs` | Averages per group; writes `refBody.json` (generator data) and `refSil.json` (per-reference silhouettes for the F5 score). |
| `refBody.json`, `refSil.json` | The numbers. Shares of stature. |
| `bodySpec.ts` | `bodySpec(femininity, height?, shape?)`: joints, bone sections, trunk rows, crotch height, in metres. `Shape` sliders and `SHAPE_RANGE`. `trunkAt`, `boneAt`. |
| `rigLow.ts` | `lowBoneDefs(spec)`: Mixamo-named rig plus helper bones (`ArmHelper`, `ElbowHelper`, `KneeHelper`, `HipHelper`, `ForeArmTwist`). `fingerLayout`. |
| `helpers.ts` | `driveHelpers(rig)`: helper bones turn half the joint angle. **Must be called every frame after posing** (viewer and tests do). Other engines will not do it: use `__lbTune = {helpers:false}` for classic weights. |
| `mannequin.ts` | F1 proportion check model (`lowrig`). |
| `body.ts` | The builder `buildLowBody(seed, femininity, tune?, shape?)`: trunk rings (12), legs, arms, hands, fingers, thumb, **head (24 x 14, own grid)**, ears, per-quad colours, closed check, `TUNE_DEFAULT` (weights, fit multipliers), `FIT_MALE/FIT_FEMALE`. |
| `poseTest.ts` | F3 battery: CPU skinning, folds/contacts/flipped/creases/volume/joint-ring area for 20 poses (`POSE_TESTS` in `../pose.ts`). |
| `silhouette.ts`, `fit.ts` | F5 score (front/side IoU against `refSil.json`) and coordinate-descent fit. |
| `src/zombie/build.ts` | Styles `lowrig`, `lowbody`; `buildZombie(seed, style, { femininity, shape })`. |
| `src/viewer/main.ts` | Pair view, shape sliders, and the `__zm` API (below). |
| `docs/10-roadmap-lowpoly.md` | Full roadmap with numbers and caveats for every phase. |

`window.__zm` API for the page: `set({style, pose, view, scene, rig, spin})`, `holdTest(name)` (hold a pose from `POSE_TESTS`, `''` releases), `look(tx,ty,tz,px,py,pz)`, `capture(name)` (writes `renders/name.png`), `poseTest(names?, detail?)`, `silScore()`, `fitGroup('male'|'female', onlyRefName?)`, `trunkCurves`, `skin()`, `setShape({...})`, `shape`, `actors()`. Tuning from the console: set `globalThis.__lbTune = {...}` and rebuild.

Reference sources: the 6 zips in `C:\Users\mirza\Downloads` (polyart-zombies, casual-lowpoly-male-rig, low-poly-people sample, low-poly-male-character, low-poly-hero-man, muscular base mesh). They were extracted into an old session scratchpad and must be re-extracted if the FBX tools are rerun. Licenses unchecked; keep them out of the repo.

## 4. Decisions and why (still valid)

- **Mixamo names everywhere**, so Mixamo clips and `armPose` finger curls work without remapping. Spine2 is inserted at 45 % from Spine1 to Neck.
- **One fixed closed topology** instead of overlapping tubes (overlapping tubes made bodies "tembus"). Trunk rings of 12; each leg is half the bottom ring plus a shared crotch point; each arm grows from a 2x2 quad hole in the chest side; thumb from one cut hand quad; fingers from a 5+5 knuckle grid joined with `bridge`; ears from a cut head quad patch.
- **Winding by topology**: `Topo.triangles()` guesses by inside point, propagates consistent winding across shared edges, flips if the volume is negative. `Topo.triFace` maps each triangle to its source face for colours.
- **Data fixes**: pelvis widened to wrap thighs; every section radius ≥ 45 % of the mean; sections smoothed twice; neck ring round from Neck sections; shoulder-top row has no upward smoothing (the sample above is the chin); headwear models are flagged and measured from the Head joint.
- **Helper bones (F3)**: a ring weighted 50/50 collapses to cos(θ/2) of its area under linear blending; a helper turning half the angle keeps elbow, knee, hip and shoulder rings rigid (elbow 140° area 0.34 → 1.0). Twist bone halves wrist roll.
- **Shoulder**: arm-hole rim, neighbouring columns and the chest side under the armpit follow the arm helper in steps; an extra ring sits on the shoulder joint.
- **Knuckle loop weight 20 % hand** (not 70 %), otherwise finger roots fold into the back of the hand in a fist.
- **F5 fit**: trunk is compared with trunk-bone triangles **including the shoulder bone and arm helper** (the references' trunk bone carries the shoulder caps); legs with whole-body slices below 0.5 H. The group fit is locked in `FIT_MALE/FIT_FEMALE` (legs 12 % too wide, waist 6 % too wide). Per-reference fits reach 0.92 mean, so the mesh can imitate each reference; per-reference parameters are noisy and were not used for sliders. Female ceiling is about 0.86 because female references differ a lot.
- **Sliders** are multipliers in `bodySpec`; girth and muscle also push the arm line outward (`ARM_PUSH`) so hanging arms do not sink into the body.
- **Head v2**: own rings of `HEAD_N = 24` columns and `HEAD_F` (14 rows), joined to the neck ring (12) by `bridge`. Width and depth from the measured head as a plain ellipse, then `FACE_DZ` / `FACE_DX` relief per row and column (15° per column). Eyes (white–iris–white quads, band between rows 8 and 9), brows (row band 10), lips (bands 3 and 4) and hair are **colours per quad** via `quadColor`. Jaw rows are floored to the neck size and made monotonic, otherwise the neck pokes out of the face (this caused 14–17 T-pose collisions on the female).

## 5. Verify the way the last session did

- Typecheck: `npx tsc --noEmit`.
- Page checks after `__zm.set({style:'lowbody'})`: `globalThis.__lowbodyCheck` must say `closed: true` for both; `__zm.poseTest()` gives one line per pose (`.text`); `__zm.silScore()` gives the IoU.
- Renders: widen the pane first (`resize_window` 1500 x 1000; reset with `preset: 'desktop'` afterwards). Use `__zm.set({rig:false, spin:false, view:'bebas', scene:'studio'})`, `__zm.holdTest('tpose')`, then `__zm.look(...)` and `await __zm.capture('name')`, and read `renders/name.png`. Head camera: bone `Head` world position `p`; front `look(p.x, p.y+0.06, p.z, p.x, p.y+0.08, p.z+0.9)`, 3/4 `p.x+0.7, p.y+0.1, p.z+0.55`, side `p.x+0.95, p.y+0.05, p.z`.
- After a code edit the page reloads through HMR and resets the style; wait ~3 s and set it again. A JS call that runs during the reload is cut off; rerun it. The hidden pane throttles long loops (45 s tool limit): split heavy fits.
- Baseline numbers to compare against after any change to `body.ts`: T-pose folds 0 for both; squat folds ≈ 75 (male) / 78 (female); silhouette ≈ 0.905 / 0.862.

## 6. Next work: make the face look good

The user showed a good reference (a low-poly soldier close-up) and said the current face is bad. What the reference does that ours does not:
- **Few, large, tilted planes.** Nose as a clear prism with side planes, cheekbone planes, a jaw line with an angle, a chin plane, a brow ridge that is one shape. Ours has 14 thin horizontal bands that read as stripes.
- Eyes are a white almond with a black pupil, eyebrows are separate shapes, lips are a small slab.
- Hair/helmet is **geometry** with its own silhouette. Ours is only colour.

Suggested order:
1. **Reduce face rows (≈ 9–10) and spend the budget on planes**: nose prism (tip, two wings, bridge), cheek and jaw angles (move jaw-angle columns outward at the lower rows), chin plane. Keep `quadColor` mapping in step with the new row indices (eye band, brow band, lip bands).
2. **Eyes**: keep white–iris–white quads but make the eye a recessed almond (move the eye-band row vertices inward, top eyelid row slightly out).
3. **Hair and helmet as geometry** (this is F7's first item): a shell offset from the skull with its own rows, painted. Female long hair as a shell down the back.
4. **Gender differences in the face**: smaller nose, fuller lips, softer jaw for the female (`spec.femininity` is available in `buildBody`).
5. Re-check closed meshes, T-pose collisions, squat and bend-forward, silhouette, and the slider extremes after every change. Budget: now 2208 tris; the references average ~1650 but the user accepted a heavier head for quality.

Ask the user for a close-up reference of the exact style if the soldier image is not the target.

## 7. Then

- **F7**: clothes as an offset shell with weights copied from the nearest body vertex, shoes, zombie variants (wounds, colours, hunch). Argon/Gemini only for parts that need a hand-made 3D style, with exact numeric specs.
- **F8**: export GLB, play real Mixamo clips in the viewer, repeat the F3 checks. Helper bones will not be driven by Mixamo clips: decide whether to bake corrective rotations or export with `helpers:false`.

## 8. Loose ends (not urgent)

- Thin dark slit at the arm hole when the arm goes back or down (closed mesh, cosmetic). A 3 x 2 quad arm hole would fix it.
- Fist: fingertips still hit the palm at full curl (about 68 contacts on the male); half fist is clean.
- Squat: about 75 folds from natural flesh contact; flipped triangles ~40.
- Mannequin (F1) only draws the middle-finger pieces.
- Stale docs from older work: "66 bones" mentions, `docs/README.md`, `docs/08-eksperimen-argon.md`.
- `output/` and `tools/blender/` appeared as untracked folders (not from this track); left alone.
- Zombie 2 head track is finished but uncommitted (license, see §2).
