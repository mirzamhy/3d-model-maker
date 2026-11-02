# Handoff — low-poly game head (eyeless)

## Status
- Mid LOD approved by user.
- Eyeless mid done (no eyes, only socket hollow + cheek hollow, deepened per feedback).
- Waiting user feedback on hollow depth. Eyeless low/high not built yet.
- Nothing committed (folder not a git repo; user commits only on request, no AI attribution).

## Files
- `tools/blender/head_lowpoly.py` — `head_sdf(p, eyeball=True, neck_cut=-0.19, eyeless=False)`; eyeless branch carves eye socket (~9 mm below brow) + cheek hollow (~8 mm). Cheek hollow only in eyeless, so with-eyes mid unchanged.
- `tools/blender/head_game.py` — main build. Objects: `Head_Main`, `Eyebrow_L`, `Eyebrow_R`.
- Outputs `output/head-game/`: `head_{low,mid,high}.{blend,glb}`, `head_mid_eyeless.{blend,glb}`, `stats_*.json`, `renders/game_mid_eyeless_{sheet,wire_sheet,close_sheet}.png`.

## Run
```bash
HEAD_EYELESS=1 HEAD_LODS=mid "/c/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup -P tools/blender/head_game.py
```
Other LODs: `HEAD_LODS=low` / `high` (with `HEAD_EYELESS=1` for eyeless).

## Eyeless mid stats
Head_Main 447 v / 898 tri; brows 36 tri each; total 487 v / 1455 e / 970 tri. Symmetric 449/449, closed.

## Method notes
- Shape = numpy SDF (smin/smax, ellipsoid, capsule, hull) -> ray-shell sampling -> voxel remesh -> decimate half + mirror (exact symmetry). Workbench renders for previews.
- Axes: x left, y up, z forward, y=0 eye level.
- Depth probe: march z 0.13 -> -0.02 at (x, y) until SDF < 0.
- Procedural only, never copy reference meshes. Ask before downloads.

## Next options
- Tune hollow depth if user asks.
- Build eyeless low/high.
