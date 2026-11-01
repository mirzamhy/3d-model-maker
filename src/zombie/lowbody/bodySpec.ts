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

/**
 * Body sliders (F4). All are multipliers around the reference average (1 = unchanged) except height (metres).
 *  - shoulder: shoulder width (arms move out, chest and shoulder rows widen);
 *  - hip: pelvis width (legs move out, hip rows widen);
 *  - girth: overall thickness of trunk and limbs (weight);
 *  - muscle: arms, legs and chest fill out (more than girth), waist stays.
 */
export interface Shape { height?: number; shoulder?: number; hip?: number; girth?: number; muscle?: number }
export const SHAPE_RANGE = { height: [1.5, 2.0], shoulder: [0.85, 1.25], hip: [0.85, 1.25], girth: [0.8, 1.3], muscle: [0.8, 1.5] } as const;

/** Outward shift of the arm and leg lines per unit of girth and muscle (shares of stature). */
export const ARM_PUSH = { girth: 0.1, muscle: 0.05 };
export const LEG_PUSH = 0.03;
const bell = (f: number, c: number, w: number) => Math.max(0, 1 - Math.abs(f - c) / w);

export const REF_STATURE = { male: R.male.stature, female: R.female.stature };

const lerp = (a: number, b: number, t: number) => a + (b - a) * t;

/**
 * Proportions for a body. femininity 0 = the male average, 1 = the female average.
 * height defaults to the matching reference stature (1.73 m male, 1.67 m female).
 */
export function bodySpec(femininity = 0, height?: number, shape: Shape = {}): BodySpec {
  const t = Math.min(1, Math.max(0, femininity));
  const H = (shape.height && shape.height > 0 ? shape.height : undefined) ?? height ?? lerp(R.male.stature, R.female.stature, t);
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
  const kS = shape.shoulder ?? 1, kH = shape.hip ?? 1, kG = shape.girth ?? 1, kM = shape.muscle ?? 1;
  // trunk rows: shoulder and hip width around their heights, girth below the neck, muscle on the chest
  for (const r of trunk) {
    const f = r.y / H;
    const fade = f < 0.86 ? 1 : Math.max(0, 1 - (f - 0.86) / 0.04); // neck and head keep their size
    r.half *= (1 + (kS - 1) * bell(f, 0.78, 0.1)) * (1 + (kH - 1) * bell(f, 0.5, 0.09)) * (1 + (kG - 1) * fade) * (1 + (kM - 1) * 0.5 * bell(f, 0.74, 0.14));
    r.front *= (1 + (kG - 1) * fade) * (1 + (kM - 1) * 0.6 * bell(f, 0.74, 0.14));
    r.back *= (1 + (kG - 1) * fade) * (1 + (kM - 1) * 0.3 * bell(f, 0.74, 0.14));
  }
  // crotch: lowest row where the trunk is already 60 % as wide as at the hip joint
  const hipHalf = trunkAt(trunk, raw.Hips.y).half;
  const crotchY = (trunk.find((r) => r.half >= 0.6 * hipHalf) ?? trunk[0]).y;

  const silhouette = M.silhouette.map((s, i) => {
    const f = F.silhouette[i] ?? s;
    return [s[0] * H, lerp(s[1], f[1], t) * H, lerp(s[2], f[2], t) * H, lerp(s[3], f[3], t) * H];
  });

  // joints: arms slide out with the shoulders, legs with the hips
  // a thicker trunk and thicker arms push the arm line outwards, or the hanging arm sinks into the body
  const dxArm = (kS - 1) * raw.LeftArm.x + (kG - 1) * ARM_PUSH.girth * H + (kM - 1) * ARM_PUSH.muscle * H;
  const dxLeg = (kH - 1) * raw.LeftUpLeg.x + (kG - 1) * LEG_PUSH * H;
  for (const k of Object.keys(raw)) {
    if (/^Left(Arm|ForeArm|Hand|Thumb\d|Mitten\d)$/.test(k)) raw[k].x += dxArm;
    if (/^Left(UpLeg|Leg|Foot|ToeBase)$/.test(k)) raw[k].x += dxLeg;
  }
  // limb sections: girth everywhere but hands, feet and the head; muscle fills arms and legs further
  for (const k of Object.keys(sections)) {
    if (/Hand|Foot|Toe|Head|Neck|Thumb|Mitten/.test(k)) continue;
    const m = /^Left(Arm|ForeArm|UpLeg|Leg)$/.test(k) ? 1 + (kM - 1) * 0.8 : 1;
    const g = kG * m;
    sections[k] = sections[k].map((s) => ({ ...s, front: s.front * g, back: s.back * g, out: s.out * g, in: s.in * g }));
  }

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
