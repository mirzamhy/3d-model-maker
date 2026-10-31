// Skin layer: torso, neck, arms, hands, legs.
import { Vector3 } from 'three';
import { loft, spike, weigher, type Station } from '../mesh';
import { PALETTE, SIDES } from '../spec';
import type { Ctx } from './ctx';

const v = (x: number, y: number, z: number) => new Vector3(x, y, z);

export function torso(ctx: Ctx) {
  const { mb, skel } = ctx;
  const st: Station[] = [
    { c: v(0, 0.86, 0), rs: 0.128, rf: 0.088 },
    { c: v(0, 0.95, 0), rs: 0.138, rf: 0.094 },
    { c: v(0, 1.05, 0), rs: 0.118, rf: 0.084 },
    { c: v(0, 1.15, -0.005), rs: 0.122, rf: 0.084 },
    { c: v(0, 1.25, -0.012), rs: 0.142, rf: 0.088 },
    { c: v(0, 1.33, -0.015), rs: 0.158, rf: 0.086 },
    { c: v(0, 1.4, -0.015), rs: 0.135, rf: 0.068 },
    { c: v(0, 1.445, -0.01), rs: 0.06, rf: 0.05 },
  ];
  loft(mb, st, {
    sides: SIDES.torso,
    front: v(0, 0, 1),
    weigh: weigher(skel, ['Hips', 'Spine', 'Spine1', 'Spine2', 'Neck', 'LeftShoulder', 'RightShoulder']),
    capStart: 'flat',
    paint: {
      base: PALETTE.skin,
      wounds: ctx.skinWounds,
      // dark V-neck singlet over the chest, green belly below it
      rule: (c) => (c.y < 0.97 ? PALETTE.pantsDark : c.y > 1.14 && c.y < 1.27 + 1.4 * Math.abs(c.x) ? PALETTE.undershirt : null),
    },
    // slightly sunken chest and ribs between the shirt flaps
    shape: (i, phi) => (i === 4 && Math.abs(Math.sin(phi) - 1) < 0.05 ? -0.01 : 0),
  });

  loft(
    mb,
    [
      { c: v(0, 1.36, -0.012), rs: 0.046, rf: 0.046 },
      { c: v(0, 1.44, -0.004), rs: 0.04, rf: 0.042 },
      { c: v(0, 1.535, 0.005), rs: 0.039, rf: 0.041 },
    ],
    {
      sides: SIDES.neck,
      front: v(0, 0, 1),
      weigh: weigher(skel, ['Spine2', 'Neck', 'Head']),
      paint: { base: PALETTE.skin, rule: (c) => (c.z > 0.02 && c.y > 1.47 ? PALETTE.skinShadow : null) },
    },
  );
}

/** Point on the bind-pose line between two bones. */
function along(ctx: Ctx, a: string, b: string, t: number) {
  const pa = ctx.skel.defs[ctx.skel.index.get(a)!].p;
  const pb = ctx.skel.defs[ctx.skel.index.get(b)!].p;
  return pa.clone().lerp(pb, t);
}

export function arm(ctx: Ctx, s: 1 | -1) {
  const { mb, skel } = ctx;
  const P = s > 0 ? 'Left' : 'Right';
  const A = `${P}Arm`;
  const F = `${P}ForeArm`;
  const H = `${P}Hand`;
  const st: Station[] = [
    { c: v(0.13 * s, 1.384, -0.014), rs: 0.046, rf: 0.046 },
    { c: along(ctx, A, F, 0), rs: 0.044, rf: 0.044 },
    { c: along(ctx, A, F, 0.45), rs: 0.037, rf: 0.038 },
    { c: along(ctx, A, F, 0.9), rs: 0.031, rf: 0.032 },
    { c: along(ctx, F, H, 0), rs: 0.032, rf: 0.031 },
    { c: along(ctx, F, H, 0.2), rs: 0.033, rf: 0.031 },
    { c: along(ctx, F, H, 0.6), rs: 0.028, rf: 0.026 },
    { c: along(ctx, F, H, 1), rs: 0.02, rf: 0.024 },
    { c: along(ctx, F, H, 1).add(v(0.02 * s, 0, 0)), rs: 0.018, rf: 0.03 },
  ];
  loft(mb, st, {
    sides: SIDES.arm,
    front: v(0, 0, 1),
    weigh: weigher(skel, ['Spine2', `${P}Shoulder`, A, F, H]),
    // bony elbow knob at the back
    shape: (i, phi) => (i === 4 && Math.sin(phi) < -0.8 ? 0.012 : 0),
    paint: { base: PALETTE.skin, wounds: ctx.skinWounds, rule: (c) => (Math.abs(c.x) > 0.48 && Math.abs(c.x) < 0.53 ? PALETTE.skinLight : null) },
  });

  // palm
  const hp = skel.defs[skel.index.get(H)!].p;
  loft(
    mb,
    [
      { c: v(hp.x + 0.005 * s, hp.y - 0.002, hp.z), rs: 0.018, rf: 0.034 },
      { c: v(hp.x + 0.045 * s, hp.y - 0.003, hp.z - 0.002), rs: 0.021, rf: 0.05 },
      { c: v(hp.x + 0.088 * s, hp.y - 0.004, hp.z - 0.004), rs: 0.016, rf: 0.048 },
    ],
    {
      sides: 6,
      phase: 0,
      front: v(0, 0, 1),
      weigh: weigher(skel, [F, H, `${P}HandIndex1`, `${P}HandMiddle1`, `${P}HandPinky1`]),
      capStart: 'flat',
      capEnd: 'flat',
      jitter: 0.02,
      paint: { base: PALETTE.skin },
    },
  );

  // fingers + thumb, with a dark claw nail on each tip
  for (const f of ['Index', 'Middle', 'Pinky', 'Thumb']) {
    const names = f === 'Thumb' ? ['Thumb1', 'Thumb2', 'Thumb3', 'Thumb_End'] : ['1', '2', '3', '_End'].map((n) => f + n);
    const pts = names.map((n) => skel.defs[skel.index.get(`${P}Hand${n}`)!].p);
    const radii = f === 'Thumb' ? [0.013, 0.011, 0.009, 0.0072] : [0.0105, 0.0094, 0.0082, 0.0066];
    loft(
      mb,
      pts.map((c, i) => ({ c, rs: radii[i], rf: radii[i] })),
      {
        sides: SIDES.finger,
        phase: Math.PI / 4,
        front: v(0, 1, 0),
        weigh: weigher(skel, [H, ...names.slice(0, 3).map((n) => `${P}Hand${n}`)]),
        capStart: 'flat',
        capEnd: 'flat',
        jitter: 0.02,
        paint: { base: PALETTE.skin, rule: (c) => (Math.abs(c.x) > 0.9 ? PALETTE.skinLight : null) },
      },
    );
    const dir = pts[3].clone().sub(pts[2]).normalize();
    const tipW = weigher(skel, [`${P}Hand${names[2]}`]);
    spike(mb, pts[3], dir.clone().add(v(0, -0.6, 0)), 0.02, 0.006, 0.005, tipW, { base: PALETTE.nail, jitter: 0.02 });
  }
}

export function leg(ctx: Ctx, s: 1 | -1) {
  const { mb, skel } = ctx;
  const P = s > 0 ? 'Left' : 'Right';
  const U = `${P}UpLeg`;
  const L = `${P}Leg`;
  const Ft = `${P}Foot`;
  const st: Station[] = [
    { c: along(ctx, U, L, -0.1), rs: 0.072, rf: 0.074 },
    { c: along(ctx, U, L, 0.28), rs: 0.066, rf: 0.068 },
    { c: along(ctx, U, L, 0.65), rs: 0.056, rf: 0.058 },
    { c: along(ctx, L, Ft, 0), rs: 0.046, rf: 0.05 },
    { c: along(ctx, L, Ft, 0.2), rs: 0.046, rf: 0.05 },
    { c: along(ctx, L, Ft, 0.48), rs: 0.04, rf: 0.042 },
    { c: along(ctx, L, Ft, 0.72), rs: 0.034, rf: 0.036 },
    { c: along(ctx, L, Ft, 0.95), rs: 0.03, rf: 0.032 },
  ];
  loft(mb, st, {
    sides: SIDES.leg,
    front: v(0, 0, 1),
    weigh: weigher(skel, ['Hips', U, L, Ft]),
    capEnd: 'flat',
    // knee cap in front, calf muscle at the back
    shape: (i, phi) => (i === 3 && Math.sin(phi) > 0.8 ? 0.01 : i === 4 && Math.sin(phi) < -0.8 ? 0.012 : 0),
    paint: { base: PALETTE.skin, wounds: ctx.skinWounds, rule: (c) => (c.y > 0.47 && c.y < 0.53 && c.z > 0.03 ? PALETTE.skinLight : null) },
  });
}
