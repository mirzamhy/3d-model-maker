// Per-seed look for the semi-realistic zombie: skin tone, clothes colours, bulk.
import { Color, Vector3 } from 'three';
import { hash, smoothstep } from '../hash';
import type { MeshBuilder } from '../mesh';
import { fbm } from '../noise';
import type { Skel } from '../skeleton';

export interface Variant {
  skin: Color;
  bruise: Color;
  raw: Color;
  blood: Color;
  bloodDark: Color;
  jacket: Color;
  shirt: Color;
  pants: Color;
  shoe: Color;
  belt: Color;
  /** Body bulk multiplier for torso / clothes radii. */
  bulk: number;
}

const pick = <T>(seed: number, i: number, list: T[]) => list[Math.floor(hash(seed, i) * list.length) % list.length];

export function makeVariant(seed: number): Variant {
  return {
    skin: new Color(pick(seed, 1, ['#a89ca2', '#ad978b', '#9c9f95', '#a398aa'])),
    bruise: new Color(pick(seed, 2, ['#6e5468', '#5f5a73', '#6b5a52'])),
    raw: new Color('#8f3a32'),
    blood: new Color('#6a1512'),
    bloodDark: new Color('#300808'),
    jacket: new Color(pick(seed, 3, ['#4a4532', '#3b2d26', '#2a2827', '#8b8682', '#4b3a2c'])),
    shirt: new Color(pick(seed, 4, ['#a8996f', '#2b2927', '#5d544a', '#8f8878'])),
    pants: new Color(pick(seed, 5, ['#2f2724', '#3a3330', '#6b5a43', '#2a2a2c'])),
    shoe: new Color(pick(seed, 6, ['#231b17', '#1c1a19', '#2e2119'])),
    belt: new Color('#221a15'),
    bulk: 0.96 + 0.1 * hash(seed, 7),
  };
}

export interface RCtx {
  mb: MeshBuilder;
  skel: Skel;
  seed: number;
  V: Variant;
}

/** Mottled undead skin: base tone with bruise and raw patches; extra darkening / redness on top. */
export function skinAt(ctx: RCtx, p: Vector3, dark = 0, red = 0) {
  const { V, seed } = ctx;
  const c = V.skin.clone();
  const m = fbm(seed, p.x, p.y, p.z, 9);
  const b = fbm(seed + 5, p.x, p.y, p.z, 24);
  c.lerp(V.bruise, smoothstep(0.48, 0.72, m) * 0.6);
  c.lerp(V.raw, Math.min(1, smoothstep(0.6, 0.8, b) * 0.45 + red));
  // fine dark veins
  const vn = fbm(seed + 21, p.x, p.y, p.z, 26, 3);
  c.lerp(V.bruise.clone().multiplyScalar(0.7), smoothstep(0.9, 0.98, 1 - Math.abs(2 * vn - 1)) * 0.55);
  c.multiplyScalar(1 - Math.min(0.85, dark));
  return c;
}

/** Cloth tone with low-frequency wear and grime. */
export function clothAt(ctx: RCtx, base: Color, p: Vector3, grime = 0.25) {
  const c = base.clone();
  const n = fbm(ctx.seed + 9, p.x, p.y, p.z, 6);
  c.multiplyScalar(0.82 + 0.36 * n);
  const g = fbm(ctx.seed + 13, p.x, p.y, p.z, 14);
  c.lerp(new Color('#1f1a16'), smoothstep(0.55, 0.8, g) * grime);
  return c;
}

/** Blood amount 0..1 at p, from streaks that run down from (x0, yTop). */
export function bloodRun(ctx: RCtx, p: Vector3, x0: number, width: number, yTop: number, yBottom: number) {
  const streak = fbm(ctx.seed + 17, p.x * 3, p.y * 0.4, p.z, 18);
  const across = Math.exp(-(((p.x - x0) / width) ** 2));
  const along = smoothstep(yBottom, yTop, p.y);
  return Math.min(1, across * along * (0.55 + 0.9 * streak));
}
