// Semi-realistic head: skull-like face carved with gaussian features on a lofted base,
// exposed teeth (no lips), hinged jaw, milky eyes, ears.
import { Color, Quaternion, Vector3 } from 'three';
import { hash } from '../hash';
import { box, ellipsoid, fromFrontSigned, loft, rigid, smoothStations, type Station, type Weigher } from '../mesh';
import { gauss } from '../noise';
import { REAL_HEAD_Y as HY } from '../skeletonReal';
import { skinAt, type RCtx } from './variant';

const v = (x: number, y: number, z: number) => new Vector3(x, y, z);

// [height above head bone, rs, rf, centre z]
const KEYS: Array<[number, number, number, number]> = [
  [-0.006, 0.036, 0.034, 0.008],
  [0.006, 0.046, 0.042, 0.032],
  [0.022, 0.054, 0.054, 0.034],
  [0.045, 0.064, 0.071, 0.022],
  [0.075, 0.07, 0.083, 0.012],
  [0.1, 0.074, 0.089, 0.008],
  [0.125, 0.079, 0.094, 0.004],
  [0.15, 0.082, 0.098, 0],
  [0.17, 0.084, 0.101, -0.004],
  [0.19, 0.083, 0.1, -0.008],
  [0.205, 0.079, 0.097, -0.011],
  [0.218, 0.072, 0.09, -0.014],
  [0.228, 0.062, 0.079, -0.016],
  [0.235, 0.049, 0.064, -0.017],
  [0.24, 0.031, 0.041, -0.017],
  [0.243, 0.002, 0.002, -0.017],
];

/** Head is drawn a little larger than the 7.5-head body for a heavier, menacing read. */
const HR = 1.07;

const MOUTH_SPLIT = 0.084;
const EYE_H = 0.148;
const EYE_A = 0.47;

/** Radial offset (m) of the face surface at height h above the head bone, signed angle a from the front. */
export function faceFeature(h: number, a: number) {
  const aa = Math.abs(a);
  let d = 0;
  d += -0.03 * gauss(h, EYE_H, 0.02) * gauss(aa, EYE_A, 0.2); // deep eye sockets
  d += 0.009 * gauss(h, 0.172, 0.009) * gauss(aa, 0.42, 0.32); // brow ridge
  d += 0.01 * gauss(h, 0.145, 0.014) * gauss(a, 0, 0.09); // nose bridge (bone only)
  d += -0.02 * gauss(h, 0.118, 0.012) * gauss(a, 0, 0.14); // rotted nasal cavity
  d += 0.012 * gauss(h, 0.128, 0.013) * gauss(aa, 0.82, 0.18); // cheekbones
  d += -0.02 * gauss(h, 0.092, 0.022) * gauss(aa, 0.74, 0.22); // hollow cheeks
  d += -0.01 * gauss(h, 0.175, 0.022) * gauss(aa, 1.28, 0.2); // temples
  d += -0.01 * gauss(h, 0.085, 0.016) * gauss(aa, 0, 0.45); // lipless mouth recess
  d += 0.009 * gauss(h, 0.028, 0.015) * gauss(a, 0, 0.25); // chin
  d += 0.007 * gauss(h, 0.05, 0.016) * gauss(aa, 1.15, 0.25); // jaw angle
  d += 0.004 * gauss(h, 0.205, 0.03) * gauss(aa, Math.PI, 0.6); // occipital bulge
  return d;
}

/** Interpolated key radius at height h (linear; good enough for placing details). */
function keyAt(h: number) {
  for (let i = 0; i < KEYS.length - 1; i++) {
    const [h0, rs0, rf0, z0] = KEYS[i];
    const [h1, rs1, rf1, z1] = KEYS[i + 1];
    if (h <= h1) {
      const t = (h - h0) / (h1 - h0);
      return { rs: (rs0 + (rs1 - rs0) * t) * HR, rf: (rf0 + (rf1 - rf0) * t) * HR, z: z0 + (z1 - z0) * t };
    }
  }
  const k = KEYS[KEYS.length - 1];
  return { rs: k[1] * HR, rf: k[2] * HR, z: k[3] };
}

/** Point on the base ellipse (before features) at height h, angle a, pushed inwards by `inset`. */
function surface(h: number, a: number, inset = 0) {
  const k = keyAt(h);
  const x = -(k.rs - inset) * Math.sin(a);
  const z = k.z + (k.rf - inset) * Math.cos(a);
  return v(x, HY + h, z);
}

export function realHead(ctx: RCtx) {
  const { mb, skel, seed } = ctx;
  const jawW = rigid(skel, 'Jaw');
  const headW = rigid(skel, 'Head');
  const weigh: Weigher = (p) => (p.y < HY + MOUTH_SPLIT && p.z > 0.012 ? jawW(p) : headW(p));
  const wound = { h: 0.2 + 0.02 * hash(seed, 60), a: -0.3 + 0.6 * hash(seed, 61) };

  mb.use('skin');
  const st: Station[] = smoothStations(
    KEYS.map(([h, rs, rf, z]) => ({ c: v(0, HY + h, z), rs: rs * HR, rf: rf * HR })),
    3,
  );
  loft(mb, st, {
    sides: 32,
    front: v(0, 0, 1),
    weigh,
    capStart: 'flat',
    capEnd: 'flat',
    shape: (_i, phi, c) => faceFeature(c.y - HY, fromFrontSigned(phi)),
    paint: {
      base: ctx.V.skin,
      rule: (p) => {
        const h = p.y - HY;
        const a = -Math.atan2(p.x, p.z - keyAt(h).z);
        const aa = Math.abs(a);
        const depth = Math.max(0, -faceFeature(h, a));
        let dark = Math.min(1, depth / 0.022) * 0.72;
        let red = 0;
        // raw flesh around the lipless mouth and the nasal hole
        red += 0.75 * gauss(h, 0.085, 0.026) * gauss(aa, 0, 0.55);
        red += 0.5 * gauss(h, 0.117, 0.015) * gauss(a, 0, 0.16);
        // bruised, sunken eyes
        red += 0.35 * gauss(h, EYE_H, 0.03) * gauss(aa, EYE_A, 0.3);
        dark += 0.25 * gauss(h, EYE_H - 0.018, 0.012) * gauss(aa, EYE_A, 0.25);
        // forehead gash
        const g = gauss(h, wound.h, 0.018) * gauss(a, wound.a, 0.18);
        red += 0.7 * g;
        dark += 0.35 * g;
        // gum line, and the mouth cavity band that stretches open with the jaw
        if (h > 0.068 && h < 0.104 && aa < 0.62) dark += 0.35;
        if (h > 0.079 && h < 0.095 && aa < 0.62) return new Color('#1c0605');
        return skinAt(ctx, p, dark, red);
      },
    },
  });

  // ears
  for (const s of [1, -1]) {
    const q = new Quaternion().setFromAxisAngle(v(0, 1, 0), -0.25 * s);
    ellipsoid(mb, v(0.087 * s, HY + 0.135, -0.018), v(0.007, 0.027, 0.015), headW, { base: ctx.V.skin, rule: (p) => skinAt(ctx, p, 0.1, 0.12) }, 1, q);
  }

  // milky, slightly glowing eyes sunk in the sockets
  mb.use('eye');
  for (const s of [1, -1]) {
    const a = EYE_A * s;
    const outer = surface(EYE_H, a);
    const n = outer.clone().sub(v(0, outer.y, keyAt(EYE_H).z)).normalize();
    const c = outer.clone().addScaledVector(n, -0.031);
    ellipsoid(mb, c, v(0.0135, 0.0125, 0.0135), headW, { base: new Color('#b9c3c6') }, 2);
    ellipsoid(mb, c.clone().addScaledVector(n, 0.0122), v(0.0042, 0.0042, 0.002), headW, { base: new Color('#8e9a9c') }, 1);
  }

  // dark mouth cavity behind the teeth
  mb.use('skin');
  ellipsoid(mb, v(0, HY + 0.084, 0.05), v(0.05, 0.022, 0.035), headW, { base: new Color('#160404') }, 1);

  // teeth: exposed, long, yellowed, a few missing
  mb.use('teeth');
  const tooth = (h: number, a: number, len: number, wdt: number, down: boolean, w: Weigher, i: number) => {
    const c = surface(h, a, 0.011);
    const out = c.clone().sub(v(0, c.y, keyAt(h).z)).setY(0).normalize();
    const tan = v(out.z, 0, -out.x);
    const yel = new Color('#c4b27c').lerp(new Color('#6e5a32'), hash(seed, 400 + i) * 0.7);
    c.y += down ? -len / 2 : len / 2;
    const tilt = (hash(seed, 450 + i) - 0.5) * 0.35;
    const up = v(0, Math.cos(tilt), 0).addScaledVector(tan, Math.sin(tilt));
    box(mb, c, v(wdt, len / 2, 0.003), w, { base: yel }, tan, up, out);
  };
  for (let i = 0; i < 12; i++) {
    if (hash(seed, 500 + i) < 0.1) continue;
    const a = -0.68 + (1.36 * i) / 11;
    tooth(0.098, a, 0.012 + 0.004 * hash(seed, 510 + i), 0.0036, true, headW, i);
  }
  for (let i = 0; i < 11; i++) {
    if (hash(seed, 530 + i) < 0.12) continue;
    const a = -0.6 + (1.2 * i) / 10;
    tooth(0.071, a, 0.011 + 0.003 * hash(seed, 540 + i), 0.0034, false, jawW, 20 + i);
  }
}
