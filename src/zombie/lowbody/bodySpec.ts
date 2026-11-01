// Body proportions for the low-poly base bodies (F1 of docs/10-roadmap-lowpoly.md).
// Every number comes from refBody.json, which tools/ref/summarize.mjs measured from the reference
// low-poly characters: joint positions and bone cross-sections as shares of stature, per gender.
// Units: metres. +Y up, +Z front, +X = character's left. T-pose.
import { Vector3 } from 'three';
import ref from './refBody.json';

export type Gender = 'male' | 'female';

interface RefGroup {
  stature: number;
  torso: number[][];
  joints: Record<string, number[]>;
  bones: Record<string, number[][]>;
  silhouette: number[][];
}
const R = ref as unknown as Record<Gender, RefGroup>;

/** Cross-section at one station along a bone: distances from the bone line, metres. */
export interface Section { front: number; back: number; out: number; in: number }
/** Section with its position along the bone (0 = joint, 1 = child joint; may lie a little outside). */
export interface BoneSection extends Section { f: number }
/** Trunk cross-section at a height: front and back from z = 0, half width from x = 0, metres. */
export interface TrunkSection { y: number; front: number; back: number; half: number }

export interface BodySpec {
  /** 0 = male, 1 = female (in between blends the two). */
  femininity: number;
  height: number;
  /** Joint positions, centre bones and the left side (mirror x for the right). */
  j: Record<string, Vector3>;
  /** Six cross-sections per bone (left side), from the bone head to its tail. */
  sections: Record<string, BoneSection[]>;
  /** Trunk (torso, neck, head) profile every 1 % of the height. */
  trunk: TrunkSection[];
  /** Height where the legs split from the trunk. */
  crotchY: number;
  /** Average front and side outline: [y, half width, front z, back z], metres. */
  silhouette: number[][];
}

export const REF_STATURE = { male: R.male.stature, female: R.female.stature };

const lerp = (a: number, b: number, t: number) => a + (b - a) * t;

/**
 * Proportions for a body. femininity 0 = the male average, 1 = the female average.
 * height defaults to the matching reference stature (1.73 m male, 1.67 m female).
 */
export function bodySpec(femininity = 0, height?: number): BodySpec {
  const t = Math.min(1, Math.max(0, femininity));
  const H = height ?? lerp(R.male.stature, R.female.stature, t);
  const M = R.male, F = R.female;

  const raw: Record<string, Vector3> = {};
  for (const k of Object.keys(M.joints)) {
    const a = M.joints[k], b = F.joints[k] ?? a;
    raw[k] = new Vector3(lerp(a[0], b[0], t), lerp(a[1], b[1], t), lerp(a[2], b[2], t)).multiplyScalar(H);
  }
  // centre bones sit on x = 0
  for (const k of ['Hips', 'Spine', 'Spine1', 'Neck', 'Head', 'Jaw']) if (raw[k]) raw[k].x = 0;

  const sections: Record<string, BoneSection[]> = {};
  for (const k of Object.keys(M.bones)) {
    const a = M.bones[k], b = F.bones[k] ?? a;
    sections[k] = a.map((s, i) => ({
      f: lerp(s[0], b[i][0], t),
      front: lerp(s[1], b[i][1], t) * H,
      back: lerp(s[2], b[i][2], t) * H,
      out: lerp(s[3], b[i][3], t) * H,
      in: lerp(s[4], b[i][4], t) * H,
    }));
  }

  // trunk rows on the shared 1 % grid; both groups are sampled at the same y fractions
  const trunk: TrunkSection[] = [];
  for (const row of M.torso) {
    const f = F.torso.find((r) => Math.abs(r[0] - row[0]) < 1e-6) ?? row;
    trunk.push({ y: row[0] * H, front: lerp(row[1], f[1], t) * H, back: lerp(row[2], f[2], t) * H, half: lerp(row[3], f[3], t) * H });
  }
  for (const row of F.torso) if (!M.torso.some((r) => Math.abs(r[0] - row[0]) < 1e-6) && t > 0.5) trunk.push({ y: row[0] * H, front: row[1] * H, back: row[2] * H, half: row[3] * H });
  trunk.sort((a, b) => a.y - b.y);
  // crotch: lowest row where the trunk is already 60 % as wide as at the hip joint
  const hipHalf = trunkAt(trunk, raw.Hips.y).half;
  const crotchY = (trunk.find((r) => r.half >= 0.6 * hipHalf) ?? trunk[0]).y;

  const silhouette = M.silhouette.map((s, i) => {
    const f = F.silhouette[i] ?? s;
    return [s[0] * H, lerp(s[1], f[1], t) * H, lerp(s[2], f[2], t) * H, lerp(s[3], f[3], t) * H];
  });

  return { femininity: t, height: H, j: raw, sections, silhouette, trunk, crotchY };
}

/** Trunk section at height y (linear between the 1 % rows, clamped at the ends). */
export function trunkAt(trunk: TrunkSection[], y: number): TrunkSection {
  if (y <= trunk[0].y) return { ...trunk[0], y };
  for (let i = 1; i < trunk.length; i++) {
    const a = trunk[i - 1], b = trunk[i];
    if (y <= b.y) {
      const f = (y - a.y) / (b.y - a.y);
      return { y, front: lerp(a.front, b.front, f), back: lerp(a.back, b.back, f), half: lerp(a.half, b.half, f) };
    }
  }
  return { ...trunk[trunk.length - 1], y };
}

/** Bone section at fraction f along the bone (linear between the six measured stations, clamped). */
export function boneAt(list: BoneSection[], f: number): Section {
  if (f <= list[0].f) return list[0];
  for (let i = 1; i < list.length; i++) {
    const a = list[i - 1], b = list[i];
    if (f <= b.f) {
      const k = (f - a.f) / (b.f - a.f);
      return { front: lerp(a.front, b.front, k), back: lerp(a.back, b.back, k), out: lerp(a.out, b.out, k), in: lerp(a.in, b.in, k) };
    }
  }
  return list[list.length - 1];
}
