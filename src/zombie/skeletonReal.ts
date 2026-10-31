// Skeleton for the semi-realistic zombie: adult male, 1.82 m, broad shoulders, five fingers.
// Same naming and conventions as skeleton.ts (T-pose bind, identity bind rotations).
import { Vector3 } from 'three';
import type { BoneDef } from './skeleton';

const v = (x: number, y: number, z: number) => new Vector3(x, y, z);

function armDefs(s: 1 | -1): BoneDef[] {
  const P = s > 0 ? 'Left' : 'Right';
  const x = (n: number) => n * s;
  const y = 1.44;
  const d: BoneDef[] = [
    { name: `${P}Shoulder`, parent: 'Spine2', p: v(x(0.035), 1.452, -0.025), tail: `${P}Arm` },
    { name: `${P}Arm`, parent: `${P}Shoulder`, p: v(x(0.205), y + 0.005, -0.03), tail: `${P}ForeArm` },
    { name: `${P}ForeArm`, parent: `${P}Arm`, p: v(x(0.5), y, -0.04), tail: `${P}Hand` },
    { name: `${P}Hand`, parent: `${P}ForeArm`, p: v(x(0.76), y - 0.002, -0.03), tail: `${P}HandMiddle1` },
  ];
  // [name, z offset, base x, phalanx lengths]
  const fingers: Array<[string, number, number, number[]]> = [
    ['Index', 0.031, 0.862, [0.048, 0.03, 0.025]],
    ['Middle', 0.009, 0.866, [0.052, 0.034, 0.026]],
    ['Ring', -0.013, 0.862, [0.049, 0.032, 0.025]],
    ['Pinky', -0.033, 0.852, [0.038, 0.025, 0.022]],
  ];
  for (const [f, z, x0, lens] of fingers) {
    const segs = ['1', '2', '3', '_End'];
    let px = x0;
    let prev = `${P}Hand`;
    for (let i = 0; i < 4; i++) {
      const name = `${P}Hand${f}${segs[i]}`;
      d.push({ name, parent: prev, p: v(x(px), y - 0.006, -0.03 + z), tail: i < 3 ? `${P}Hand${f}${segs[i + 1]}` : undefined });
      prev = name;
      if (i < 3) px += lens[i];
    }
  }
  const thumb = [v(0.782, y - 0.012, 0.0), v(0.812, y - 0.02, 0.03), v(0.838, y - 0.026, 0.05), v(0.862, y - 0.03, 0.064)];
  const tn = ['Thumb1', 'Thumb2', 'Thumb3', 'Thumb_End'];
  let prev = `${P}Hand`;
  thumb.forEach((p, i) => {
    const name = `${P}Hand${tn[i]}`;
    d.push({ name, parent: prev, p: v(x(p.x), p.y, p.z), tail: i < 3 ? `${P}Hand${tn[i + 1]}` : undefined });
    prev = name;
  });
  return d;
}

function legDefs(s: 1 | -1): BoneDef[] {
  const P = s > 0 ? 'Left' : 'Right';
  const x = (n: number) => n * s;
  return [
    { name: `${P}UpLeg`, parent: 'Hips', p: v(x(0.1), 0.95, 0), tail: `${P}Leg` },
    { name: `${P}Leg`, parent: `${P}UpLeg`, p: v(x(0.106), 0.52, 0.015), tail: `${P}Foot` },
    { name: `${P}Foot`, parent: `${P}Leg`, p: v(x(0.112), 0.09, -0.015), tail: `${P}ToeBase` },
    { name: `${P}ToeBase`, parent: `${P}Foot`, p: v(x(0.116), 0.025, 0.12), tail: `${P}Toe_End` },
    { name: `${P}Toe_End`, parent: `${P}ToeBase`, p: v(x(0.118), 0.025, 0.205) },
  ];
}

export const REAL_HEAD_Y = 1.585;

export const REAL_BONE_DEFS: BoneDef[] = [
  { name: 'Hips', parent: null, p: v(0, 0.98, 0), tail: 'Spine' },
  { name: 'Spine', parent: 'Hips', p: v(0, 1.08, -0.01), tail: 'Spine1' },
  { name: 'Spine1', parent: 'Spine', p: v(0, 1.2, -0.015), tail: 'Spine2' },
  { name: 'Spine2', parent: 'Spine1', p: v(0, 1.33, -0.02), tail: 'Neck' },
  { name: 'Neck', parent: 'Spine2', p: v(0, 1.5, -0.02), tail: 'Head' },
  { name: 'Head', parent: 'Neck', p: v(0, REAL_HEAD_Y, 0), tail: 'HeadTop_End' },
  { name: 'HeadTop_End', parent: 'Head', p: v(0, 1.825, 0.0) },
  { name: 'Jaw', parent: 'Head', p: v(0, 1.69, -0.035), tail: v(0, 1.605, 0.085) },
  ...armDefs(1),
  ...armDefs(-1),
  ...legDefs(1),
  ...legDefs(-1),
];
