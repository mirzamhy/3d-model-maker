// Head: lofted skull with carved eye sockets / cheeks / nose, hinged jaw, teeth, eyes, ears, hair.
import { Vector3 } from 'three';
import { hash } from '../hash';
import { gem, loft, normAngle, rigid, spike, type Station, type Weigher } from '../mesh';
import { PALETTE, SIDES } from '../spec';
import type { Ctx } from './ctx';

const v = (x: number, y: number, z: number) => new Vector3(x, y, z);
const BASE_Y = 1.5;
/** Stylised head: wider (HR) and slightly taller (HS) than the 7-head base. */
const HR = 1.13;
const HS = 1.05;

// [height above head base, rs, rf, centre z]  (docs/02-struktur-mesh.md §4)
const PROFILE: Array<[number, number, number, number]> = [
  [0.0, 0.04, 0.038, 0.032],
  [0.045, 0.057, 0.066, 0.02],
  [0.085, 0.065, 0.08, 0.012],
  [0.122, 0.071, 0.089, 0.004],
  [0.152, 0.076, 0.094, 0],
  [0.178, 0.078, 0.096, -0.004],
  [0.208, 0.072, 0.092, -0.008],
  [0.236, 0.05, 0.064, -0.012],
];

const MOUTH_SPLIT_Y = BASE_Y + 0.066;

/** Angle away from straight ahead, 0..PI. */
const fromFront = (phi: number) => {
  const a = normAngle(phi - Math.PI / 2);
  return a > Math.PI ? 2 * Math.PI - a : a;
};
const near = (a: number, b: number) => Math.abs(a - b) < 0.12;

export function head(ctx: Ctx) {
  const { mb, skel } = ctx;
  const jawW = rigid(skel, 'Jaw');
  const headW = rigid(skel, 'Head');
  const weigh: Weigher = (p) => (p.y < MOUTH_SPLIT_Y && p.z > 0.0 ? jawW(p) : headW(p));

  const eyeY = BASE_Y + PROFILE[4][0] * HS;
  const eyeL = v(0.051, eyeY, 0.064);
  const eyeR = v(-0.051, eyeY, 0.064);

  const st: Station[] = PROFILE.map(([y, rs, rf, z]) => ({ c: v(0, BASE_Y + y * HS, z), rs: rs * HR, rf: rf * HR }));
  loft(mb, st, {
    sides: SIDES.head,
    front: v(0, 0, 1),
    weigh,
    capEnd: 'point',
    tipLen: 0.016,
    capStart: 'flat',
    shape: (i, phi) => {
      const a = fromFront(phi);
      if (i === 4) return near(a, Math.PI / 4) ? -0.017 : near(a, 0) ? -0.003 : 0; // eye sockets
      if (i === 3) return near(a, 0) ? 0.02 : near(a, Math.PI / 4) ? -0.003 : near(a, Math.PI / 2) ? -0.007 : 0; // nose, cheeks
      if (i === 5) return near(a, Math.PI / 4) ? 0.007 : near(a, 0) ? 0.002 : 0; // brow ridge
      if (i === 2) return near(a, 0) ? -0.006 : 0; // mouth
      if (i === 1) return near(a, Math.PI / 2) ? -0.004 : 0;
      return 0;
    },
    paint: {
      base: PALETTE.skin,
      wounds: ctx.skinWounds,
      rule: (c) => {
        if (c.distanceTo(eyeL) < 0.034 || c.distanceTo(eyeR) < 0.034) return PALETTE.skinShadow;
        if (c.y > BASE_Y + 0.047 && c.y < BASE_Y + 0.105 && c.z > 0.05 && Math.abs(c.x) < 0.062) return PALETTE.mouth;
        if (c.y > BASE_Y + 0.18 && c.z > 0.06) return PALETTE.skinLight;
        return null;
      },
    },
  });

  // eyes: pale, small, sunk in the sockets
  for (const e of [eyeL, eyeR]) {
    gem(mb, e, 0.017, headW, { base: PALETTE.eye, jitter: 0.03 });
    gem(mb, e.clone().add(v(0, 0, 0.014)), 0.005, headW, { base: PALETTE.pupil, jitter: 0 });
  }

  // teeth: uneven, some missing
  const seed = ctx.seed;
  for (let i = 0; i < 8; i++) {
    if (hash(seed, 100 + i) < 0.18) continue;
    const a = -0.85 + (1.7 * i) / 7;
    const base = v(Math.sin(a) * 0.063, BASE_Y + 0.099, 0.012 + Math.cos(a) * 0.084);
    const len = 0.014 + 0.01 * hash(seed, 120 + i);
    spike(mb, base, v(0, -1, 0.15), len, 0.0055, 0.004, headW, { base: PALETTE.teeth, jitter: 0.06 }, v(Math.sin(a), 0, Math.cos(a)));
  }
  for (let i = 0; i < 7; i++) {
    if (hash(seed, 140 + i) < 0.2) continue;
    const a = -0.75 + (1.5 * i) / 6;
    const base = v(Math.sin(a) * 0.057, BASE_Y + 0.05, 0.02 + Math.cos(a) * 0.069);
    spike(mb, base, v(0, 1, 0.1), 0.012 + 0.006 * hash(seed, 150 + i), 0.005, 0.0035, jawW, { base: PALETTE.teeth, jitter: 0.06 }, v(Math.sin(a), 0, Math.cos(a)));
  }

  // ears
  for (const s of [1, -1]) {
    spike(mb, v(0.084 * s, BASE_Y + 0.14, -0.012), v(s, 0.35, -0.35), 0.03, 0.012, 0.022, headW, { base: PALETTE.skin }, v(0, 0, 1));
  }

  // sparse spiky hair on the crown and back
  const count = 12 + Math.floor(hash(seed, 200) * 5);
  for (let i = 0; i < count; i++) {
    const ang = Math.PI * (0.75 + 1.5 * hash(seed, 210 + i)); // mostly back half
    const hgt = (0.17 + 0.07 * hash(seed, 230 + i)) * HS;
    const r = (hgt > 0.225 ? 0.05 : hgt > 0.2 ? 0.072 : 0.082) * HR;
    const base = v(Math.cos(ang) * r, BASE_Y + hgt, -0.01 + Math.sin(ang) * r * 1.25);
    const out = v(Math.cos(ang) * 0.8, 0.55, Math.sin(ang) * 0.8 - 0.6);
    spike(mb, base, out, 0.045 + 0.035 * hash(seed, 250 + i), 0.02, 0.005, headW, { base: PALETTE.hair, jitter: 0.08 }, v(Math.cos(ang), 0, Math.sin(ang)));
  }
}
