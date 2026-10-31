// Skeleton in bind pose (T-pose, matching docs/ref/referensi-rig.webp).
// All bind rotations are identity, so every bone's local axes equal world axes in bind pose.
// Names follow the Mixamo convention (docs/03-rigging.md).
import { Bone, Vector3 } from 'three';

export interface BoneDef {
  name: string;
  parent: string | null;
  /** World position in bind pose. */
  p: Vector3;
  /** Segment end used for skin weighting: a bone name or a world point. */
  tail?: string | Vector3;
}

const v = (x: number, y: number, z: number) => new Vector3(x, y, z);

function armDefs(s: 1 | -1): BoneDef[] {
  const P = s > 0 ? 'Left' : 'Right';
  const x = (n: number) => n * s;
  const d: BoneDef[] = [
    { name: `${P}Shoulder`, parent: 'Spine2', p: v(x(0.03), 1.385, -0.012), tail: `${P}Arm` },
    { name: `${P}Arm`, parent: `${P}Shoulder`, p: v(x(0.18), 1.38, -0.015), tail: `${P}ForeArm` },
    { name: `${P}ForeArm`, parent: `${P}Arm`, p: v(x(0.505), 1.378, -0.025), tail: `${P}Hand` },
    { name: `${P}Hand`, parent: `${P}ForeArm`, p: v(x(0.795), 1.376, -0.01), tail: `${P}HandMiddle1` },
  ];
  const fingers: Array<[string, number, number, number[]]> = [
    ['Index', 0.024, 0.885, [0.046, 0.036, 0.03]],
    ['Middle', 0.0, 0.89, [0.052, 0.04, 0.033]],
    ['Pinky', -0.024, 0.878, [0.04, 0.031, 0.026]],
  ];
  for (const [f, z, x0, lens] of fingers) {
    const segs = ['1', '2', '3', '_End'];
    let px = x0;
    let prev = `${P}Hand`;
    for (let i = 0; i < 4; i++) {
      const name = `${P}Hand${f}${segs[i]}`;
      d.push({ name, parent: prev, p: v(x(px), 1.372, -0.01 + z), tail: i < 3 ? `${P}Hand${f}${segs[i + 1]}` : undefined });
      prev = name;
      if (i < 3) px += lens[i];
    }
  }
  const thumb = [v(0.815, 1.368, 0.028), v(0.842, 1.36, 0.052), v(0.866, 1.354, 0.068), v(0.888, 1.35, 0.078)];
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
    { name: `${P}UpLeg`, parent: 'Hips', p: v(x(0.1), 0.915, 0), tail: `${P}Leg` },
    { name: `${P}Leg`, parent: `${P}UpLeg`, p: v(x(0.108), 0.5, 0.012), tail: `${P}Foot` },
    { name: `${P}Foot`, parent: `${P}Leg`, p: v(x(0.115), 0.09, -0.01), tail: `${P}ToeBase` },
    { name: `${P}ToeBase`, parent: `${P}Foot`, p: v(x(0.118), 0.03, 0.13), tail: `${P}Toe_End` },
    { name: `${P}Toe_End`, parent: `${P}ToeBase`, p: v(x(0.12), 0.03, 0.215) },
  ];
}

export const BONE_DEFS: BoneDef[] = [
  { name: 'Hips', parent: null, p: v(0, 0.93, 0), tail: 'Spine' },
  { name: 'Spine', parent: 'Hips', p: v(0, 1.03, -0.005), tail: 'Spine1' },
  { name: 'Spine1', parent: 'Spine', p: v(0, 1.15, -0.01), tail: 'Spine2' },
  { name: 'Spine2', parent: 'Spine1', p: v(0, 1.27, -0.012), tail: 'Neck' },
  { name: 'Neck', parent: 'Spine2', p: v(0, 1.42, -0.008), tail: 'Head' },
  { name: 'Head', parent: 'Neck', p: v(0, 1.5, 0), tail: 'HeadTop_End' },
  { name: 'HeadTop_End', parent: 'Head', p: v(0, 1.75, 0) },
  { name: 'Jaw', parent: 'Head', p: v(0, 1.545, -0.005), tail: v(0, 1.515, 0.085) },
  ...armDefs(1),
  ...armDefs(-1),
  ...legDefs(1),
  ...legDefs(-1),
];

export interface Skel {
  defs: BoneDef[];
  bones: Bone[];
  index: Map<string, number>;
  /** Segment (head, tail) per bone, world space, bind pose. */
  seg: Array<[Vector3, Vector3]>;
}

export function buildSkeleton(defs: BoneDef[] = BONE_DEFS): Skel {
  const index = new Map<string, number>();
  defs.forEach((d, i) => index.set(d.name, i));
  const bones = defs.map((d) => {
    const b = new Bone();
    b.name = d.name;
    return b;
  });
  defs.forEach((d, i) => {
    if (d.parent) {
      const pi = index.get(d.parent)!;
      bones[pi].add(bones[i]);
      bones[i].position.copy(d.p).sub(defs[pi].p);
    } else {
      bones[i].position.copy(d.p);
    }
  });
  const seg = defs.map((d): [Vector3, Vector3] => {
    let tail: Vector3;
    if (d.tail instanceof Vector3) tail = d.tail;
    else if (typeof d.tail === 'string') tail = defs[index.get(d.tail)!].p;
    else tail = d.p.clone().add(new Vector3(0, 0.001, 0));
    return [d.p, tail];
  });
  return { defs, bones, index, seg };
}
