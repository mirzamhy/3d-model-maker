// Low-poly rig, Mixamo names, built from a BodySpec: spine, neck, head, arms, legs as in the reference
// characters (two spine bones in the references become Spine/Spine1/Spine2 here), plus four separate
// three-segment fingers and a two-segment thumb per hand, so Mixamo clips still map.
// The references model the four fingers as one mitten; the finger layout below spreads that measured
// mitten (knuckle line, length, hand width and thickness) over four fingers.
import { Vector3 } from 'three';
import type { BoneDef } from '../skeleton';
import { boneAt, type BodySpec } from './bodySpec';

export const FINGERS = ['Index', 'Middle', 'Ring', 'Pinky'] as const;

export interface FingerLayout {
  /** Knuckle line centre, hand half width across the knuckles, knuckle thickness (left hand, metres). */
  knuckle: Vector3;
  halfWidth: number;
  thickness: number;
  fingers: Array<{ name: string; joints: Vector3[]; halfW: number; halfT: number }>;
}

/** Left-hand finger layout from the measured mitten. */
export function fingerLayout(spec: BodySpec): FingerLayout {
  const J = spec.j;
  const k = spec.height / 1.73;
  const sec = boneAt(spec.sections.LeftHand, 0.9);
  const K0 = J.LeftMitten1, K1 = J.LeftMitten2;
  const tip = K1.clone().add(K1.clone().sub(K0).multiplyScalar(1.1));
  const len = tip.distanceTo(K0);
  const dir = tip.clone().sub(K0).normalize();
  // hand frame: across the knuckles is z (index at +z, thumb side), thickness is y
  const halfWidth = ((sec.front + sec.back) / 2) * 0.92;
  const thickness = sec.out + sec.in;
  const knuckle = new Vector3(K0.x, K0.y + (sec.in - sec.out) / 2, K0.z + (sec.front - sec.back) / 2);
  const lenK = [0.93, 1, 0.94, 0.76];
  const backX = [0.002, 0, 0.003, 0.008].map((x) => x * k);
  const spread = [0.1, 0.02, -0.06, -0.14]; // fan out, index towards the thumb
  const fingers = FINGERS.map((name, i) => {
    const base = new Vector3(knuckle.x - backX[i], knuckle.y, knuckle.z + halfWidth * (0.75 - 0.5 * i));
    const d = dir.clone().add(new Vector3(0, 0, spread[i])).normalize();
    const L = len * lenK[i];
    const j2 = base.clone().addScaledVector(d, L * 0.46);
    const j3 = j2.clone().addScaledVector(d, L * 0.3);
    const end = j3.clone().addScaledVector(d, L * 0.24);
    return { name, joints: [base, j2, j3, end], halfW: halfWidth * 0.23 * (i === 3 ? 0.88 : 1), halfT: thickness * 0.3 * (i === 3 ? 0.88 : 1) };
  });
  return { knuckle, halfWidth, thickness, fingers };
}

const mirror = (p: Vector3, s: 1 | -1) => new Vector3(p.x * s, p.y, p.z);

export function lowBoneDefs(spec: BodySpec): BoneDef[] {
  const J = spec.j;
  const H = spec.height;
  // the references have one long chest bone; Spine2 splits it so the upper chest can bend on its own
  const spine2 = J.Spine1.clone().lerp(J.Neck, 0.45);
  const crown = new Vector3(0, H, J.Head.z);
  const defs: BoneDef[] = [
    { name: 'Hips', parent: null, p: J.Hips.clone(), tail: 'Spine' },
    { name: 'Spine', parent: 'Hips', p: J.Spine.clone(), tail: 'Spine1' },
    { name: 'Spine1', parent: 'Spine', p: J.Spine1.clone(), tail: 'Spine2' },
    { name: 'Spine2', parent: 'Spine1', p: spine2, tail: 'Neck' },
    { name: 'Neck', parent: 'Spine2', p: J.Neck.clone(), tail: 'Head' },
    { name: 'Head', parent: 'Neck', p: J.Head.clone(), tail: 'HeadTop_End' },
    { name: 'HeadTop_End', parent: 'Head', p: crown },
  ];
  // toe tip: front of the averaged silhouette at floor level
  const toeZ = spec.silhouette[0][2];
  const fingers = fingerLayout(spec);
  for (const s of [1, -1] as const) {
    const P = s > 0 ? 'Left' : 'Right';
    const m = (n: string) => mirror(J[n], s);
    const end = (a: string, b: string, k = 1) => m(b).add(m(b).sub(m(a)).multiplyScalar(k));
    defs.push(
      { name: `${P}Shoulder`, parent: 'Spine2', p: m('LeftShoulder'), tail: `${P}Arm` },
      { name: `${P}Arm`, parent: `${P}Shoulder`, p: m('LeftArm'), tail: `${P}ForeArm` },
      { name: `${P}ForeArm`, parent: `${P}Arm`, p: m('LeftForeArm'), tail: `${P}Hand` },
      { name: `${P}Hand`, parent: `${P}ForeArm`, p: m('LeftHand'), tail: `${P}HandMiddle1` },
      { name: `${P}HandThumb1`, parent: `${P}Hand`, p: m('LeftThumb1'), tail: `${P}HandThumb2` },
      { name: `${P}HandThumb2`, parent: `${P}HandThumb1`, p: m('LeftThumb2'), tail: `${P}HandThumb_End` },
      { name: `${P}HandThumb_End`, parent: `${P}HandThumb2`, p: end('LeftThumb1', 'LeftThumb2', 0.9) },
      { name: `${P}UpLeg`, parent: 'Hips', p: m('LeftUpLeg'), tail: `${P}Leg` },
      { name: `${P}Leg`, parent: `${P}UpLeg`, p: m('LeftLeg'), tail: `${P}Foot` },
      { name: `${P}Foot`, parent: `${P}Leg`, p: m('LeftFoot'), tail: `${P}ToeBase` },
      { name: `${P}ToeBase`, parent: `${P}Foot`, p: m('LeftToeBase'), tail: `${P}Toe_End` },
      { name: `${P}Toe_End`, parent: `${P}ToeBase`, p: new Vector3(m('LeftToeBase').x, m('LeftToeBase').y, toeZ) },
    );
    // four fingers, three segments each, plus an end marker
    for (const f of fingers.fingers) {
      const seg = ['1', '2', '3', '_End'];
      f.joints.forEach((p, i) => {
        const name = `${P}Hand${f.name}${seg[i]}`;
        const parent = i === 0 ? `${P}Hand` : `${P}Hand${f.name}${seg[i - 1]}`;
        defs.push({ name, parent, p: mirror(p, s), tail: i < 3 ? `${P}Hand${f.name}${seg[i + 1]}` : undefined });
      });
    }
  }
  return defs;
}

/** Bones that carry geometry (end markers excluded). */
export const isEndBone = (name: string) => /_End$/.test(name);
