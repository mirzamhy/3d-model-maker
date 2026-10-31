// Cloth layers: open shirt with ragged hem and sleeves, shorts, belt, boots.
import { Color, Vector3 } from 'three';
import { hashPos } from '../hash';
import { box, loft, rigid, weigher, type Station } from '../mesh';
import { PALETTE, SIDES } from '../spec';
import type { Ctx } from './ctx';

const v = (x: number, y: number, z: number) => new Vector3(x, y, z);

/** Coarse blotches: cells of ~6 cm get a darker dirt tint. */
const dirt = (seed: number, base: Color, darker: Color, amount: number) => (c: Vector3) => {
  const h = hashPos(seed, Math.floor(c.x / 0.06) * 0.06, Math.floor(c.y / 0.06) * 0.06, Math.floor(c.z / 0.06) * 0.06);
  return h < amount ? base.clone().lerp(darker, 0.6 + 0.4 * (h / amount)) : null;
};

export function shirt(ctx: Ctx) {
  const { mb, skel, seed } = ctx;
  const st: Station[] = [
    { c: v(0, 1.462, -0.012), rs: 0.072, rf: 0.062 },
    { c: v(0, 1.415, -0.014), rs: 0.16, rf: 0.086 },
    { c: v(0, 1.34, -0.014), rs: 0.184, rf: 0.106 },
    { c: v(0, 1.25, -0.012), rs: 0.17, rf: 0.113 },
    { c: v(0, 1.12, -0.006), rs: 0.157, rf: 0.11 },
    { c: v(0, 0.99, 0), rs: 0.165, rf: 0.117 },
  ];
  loft(mb, st, {
    sides: SIDES.shirt,
    front: v(0, 0, 1),
    phase: Math.PI / 2 + Math.PI / SIDES.shirt,
    hem: 0.07,
    jitter: 0.06,
    open: (phi) => Math.abs(phi - Math.PI / 2) < 0.45,
    weigh: weigher(skel, ['Hips', 'Spine', 'Spine1', 'Spine2', 'Neck', 'LeftShoulder', 'RightShoulder', 'LeftArm', 'RightArm']),
    paint: { base: PALETTE.shirt, rule: dirt(seed + 11, PALETTE.shirt, PALETTE.shirtDirt, 0.22), wounds: ctx.shirtStains },
  });

  for (const s of [1, -1]) {
    const P = s > 0 ? 'Left' : 'Right';
    loft(
      mb,
      [
        { c: v(0.11 * s, 1.385, -0.014), rs: 0.072, rf: 0.07 },
        { c: v(0.2 * s, 1.38, -0.015), rs: 0.067, rf: 0.065 },
        { c: v(0.34 * s, 1.379, -0.018), rs: 0.059, rf: 0.057 },
      ],
      {
        sides: SIDES.sleeve,
        front: v(0, 0, 1),
        hem: 0.045,
        jitter: 0.06,
        weigh: weigher(skel, ['Spine2', `${P}Shoulder`, `${P}Arm`]),
        paint: { base: PALETTE.shirt, rule: dirt(seed + 12, PALETTE.shirt, PALETTE.shirtDirt, 0.25), wounds: ctx.shirtStains },
      },
    );
  }
}

export function pants(ctx: Ctx) {
  const { mb, skel, seed } = ctx;
  const paint = { base: PALETTE.pants, rule: dirt(seed + 21, PALETTE.pants, PALETTE.pantsDark, 0.3), wounds: ctx.pantsStains };
  loft(
    mb,
    [
      { c: v(0, 1.085, 0), rs: 0.152, rf: 0.106 },
      { c: v(0, 0.98, 0), rs: 0.158, rf: 0.11 },
      { c: v(0, 0.9, 0), rs: 0.15, rf: 0.104 },
      { c: v(0, 0.84, 0), rs: 0.1, rf: 0.07 },
    ],
    { sides: SIDES.pants, front: v(0, 0, 1), capEnd: 'flat', weigh: weigher(skel, ['Hips', 'Spine', 'LeftUpLeg', 'RightUpLeg']), paint },
  );
  for (const s of [1, -1]) {
    const P = s > 0 ? 'Left' : 'Right';
    const up = skel.defs[skel.index.get(`${P}UpLeg`)!].p;
    const kn = skel.defs[skel.index.get(`${P}Leg`)!].p;
    const at = (y: number) => up.clone().lerp(kn, (up.y - y) / (up.y - kn.y));
    loft(
      mb,
      [
        { c: at(1.0).setX(0.075 * s), rs: 0.085, rf: 0.095 },
        { c: at(0.9).setX(0.092 * s), rs: 0.09, rf: 0.094 },
        { c: at(0.79), rs: 0.086, rf: 0.088 },
        { c: at(0.69), rs: 0.083, rf: 0.085 },
      ],
      { sides: SIDES.pantLeg, front: v(0, 0, 1), hem: 0.055, jitter: 0.06, weigh: weigher(skel, ['Hips', `${P}UpLeg`, `${P}Leg`]), paint },
    );
  }

  // belt + buckle
  const beltW = weigher(skel, ['Hips', 'Spine']);
  loft(
    mb,
    [
      { c: v(0, 1.078, 0), rs: 0.16, rf: 0.113 },
      { c: v(0, 1.034, 0), rs: 0.161, rf: 0.114 },
    ],
    { sides: 14, front: v(0, 0, 1), jitter: 0.01, weigh: beltW, paint: { base: PALETTE.belt } },
  );
  box(mb, v(0, 1.056, 0.117), v(0.026, 0.021, 0.006), beltW, { base: PALETTE.buckle, jitter: 0.08 });
  box(mb, v(0, 1.056, 0.121), v(0.014, 0.011, 0.004), beltW, { base: PALETTE.belt });
}

export function boots(ctx: Ctx) {
  const { mb, skel } = ctx;
  for (const s of [1, -1]) {
    const P = s > 0 ? 'Left' : 'Right';
    const ft = skel.defs[skel.index.get(`${P}Foot`)!].p;
    const x = ft.x;
    // shaft, ragged rim on top
    loft(
      mb,
      [
        { c: v(x, 0.06, -0.012), rs: 0.058, rf: 0.066 },
        { c: v(x, 0.16, -0.012), rs: 0.054, rf: 0.057 },
        { c: v(x - 0.002 * s, 0.265, -0.01), rs: 0.058, rf: 0.061 },
      ],
      { sides: 9, front: v(0, 0, 1), hem: 0.03, jitter: 0.05, weigh: weigher(skel, [`${P}Leg`, `${P}Foot`]), paint: { base: PALETTE.boot } },
    );
    // foot, swept heel -> toe. Left boot is torn open at the toe.
    const torn = s > 0;
    loft(
      mb,
      [
        { c: v(x, 0.05, -0.075), rs: 0.046, rf: 0.046 },
        { c: v(x, 0.055, -0.04), rs: 0.056, rf: 0.054 },
        { c: v(x + 0.004 * s, 0.05, 0.04), rs: 0.06, rf: 0.05 },
        { c: v(x + 0.006 * s, 0.042, 0.13), rs: 0.058, rf: 0.041 },
        { c: v(x + 0.006 * s, 0.035, 0.195), rs: 0.048, rf: 0.032 },
      ],
      {
        sides: SIDES.boot,
        front: v(0, 1, 0),
        jitter: 0.04,
        capStart: 'flat',
        capEnd: torn ? 'none' : 'flat',
        weigh: weigher(skel, [`${P}Leg`, `${P}Foot`, `${P}ToeBase`]),
        paint: { base: PALETTE.boot, rule: (c) => (c.y < 0.016 ? PALETTE.bootSole : null) },
      },
    );
    if (torn) {
      const toeW = rigid(skel, `${P}ToeBase`);
      for (let i = 0; i < 4; i++) {
        const tx = x + 0.006 + (i - 1.5) * 0.02;
        box(mb, v(tx, 0.022, 0.2), v(0.008, 0.009, 0.014 - i * 0.0015), toeW, { base: PALETTE.skin });
        box(mb, v(tx, 0.027, 0.214 - i * 0.0015), v(0.006, 0.004, 0.003), toeW, { base: PALETTE.nail });
      }
    }
  }
}
