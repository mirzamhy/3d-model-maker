// Semi-realistic clothing: V-neck tee, open leather jacket with collar and lapels,
// long trousers with knee folds and cargo pockets, belt, dress shoes.
import { Color, Vector3 } from 'three';
import { box, fromFrontSigned, loft, smoothStations, weigher, type Station } from '../mesh';
import { gauss } from '../noise';
import { bloodRun, clothAt, type RCtx } from './variant';

const v = (x: number, y: number, z: number) => new Vector3(x, y, z);
const TORSO = ['Hips', 'Spine', 'Spine1', 'Spine2', 'Neck', 'LeftShoulder', 'RightShoulder'];

export function realShirt(ctx: RCtx) {
  const { mb, skel, V } = ctx;
  const b = V.bulk;
  mb.use('shirt');
  const keys: Station[] = [
    { c: v(0, 0.95, -0.005), rs: 0.172 * b, rf: 0.122 * b },
    { c: v(0, 1.08, -0.012), rs: 0.17 * b, rf: 0.122 * b },
    { c: v(0, 1.22, -0.02), rs: 0.18 * b, rf: 0.128 * b },
    { c: v(0, 1.34, -0.026), rs: 0.192 * b, rf: 0.126 * b },
    { c: v(0, 1.44, -0.03), rs: 0.17 * b, rf: 0.1 * b },
    { c: v(0, 1.5, -0.025), rs: 0.078, rf: 0.07 },
  ];
  loft(mb, smoothStations(keys, 6), {
    sides: 48,
    front: v(0, 0, 1),
    // V-neck: opening widens towards the collar
    open: (phi, _r, c) => c.y > 1.35 && Math.abs(fromFrontSigned(phi)) < ((c.y - 1.35) / 0.15) * 0.5,
    weigh: weigher(skel, TORSO),
    shape: (_i, phi, c) => 0.0025 * Math.sin(phi * 9 + c.y * 55) * gauss(c.y, 1.05, 0.08),
    paint: {
      base: V.shirt,
      rule: (p) => clothAt(ctx, V.shirt, p, 0.3).lerp(V.bloodDark, bloodRun(ctx, p, 0.02, 0.11, 1.48, 1.05) * 0.7),
    },
  });
}

export function realJacket(ctx: RCtx) {
  const { mb, skel, V } = ctx;
  const b = V.bulk;
  mb.use('jacket');
  const paint = { base: V.jacket, rule: (p: Vector3) => clothAt(ctx, V.jacket, p, 0.35).lerp(V.bloodDark, bloodRun(ctx, p, 0.11, 0.05, 1.3, 1.0) * 0.4) };
  const keys: Station[] = [
    { c: v(0, 1.505, -0.03), rs: 0.088, rf: 0.078 },
    { c: v(0, 1.475, -0.034), rs: 0.2 * b, rf: 0.115 * b },
    { c: v(0, 1.42, -0.032), rs: 0.235 * b, rf: 0.138 * b },
    { c: v(0, 1.32, -0.026), rs: 0.22 * b, rf: 0.148 * b },
    { c: v(0, 1.19, -0.018), rs: 0.205 * b, rf: 0.142 * b },
    { c: v(0, 1.05, -0.01), rs: 0.2 * b, rf: 0.14 * b },
    { c: v(0, 0.95, -0.005), rs: 0.206 * b, rf: 0.145 * b },
    { c: v(0, 0.86, 0), rs: 0.212 * b, rf: 0.15 * b },
  ];
  const st = smoothStations(keys, 3);
  loft(mb, st, {
    sides: 40,
    front: v(0, 0, 1),
    // open front, gap widening towards the hem
    open: (phi, ring) => Math.abs(fromFrontSigned(phi)) < 0.2 + 0.32 * (ring / (st.length - 1)),
    weigh: weigher(skel, [...TORSO, 'LeftArm', 'RightArm', 'LeftUpLeg', 'RightUpLeg']),
    // soft vertical folds below the chest, slight hang at the hem
    shape: (_i, phi, c) => (0.004 * Math.sin(phi * 11 + 1.3) + 0.002 * Math.sin(phi * 23)) * (1 - gauss(c.y, 1.42, 0.12)),
    paint,
  });

  // collar: flares out around the neck, open at the front
  loft(
    mb,
    smoothStations(
      [
        { c: v(0, 1.47, -0.034), rs: 0.1, rf: 0.088 },
        { c: v(0, 1.5, -0.036), rs: 0.098, rf: 0.085 },
        { c: v(0, 1.53, -0.042), rs: 0.112, rf: 0.098 },
      ],
      3,
    ),
    { sides: 32, front: v(0, 0, 1), open: (phi) => Math.abs(fromFrontSigned(phi)) < 0.75, weigh: weigher(skel, ['Spine2', 'Neck']), paint },
  );

  // lapels folded over the chest
  const lapW = weigher(skel, ['Spine1', 'Spine2', 'Neck']);
  for (const s of [1, -1]) {
    const q = [v(0.058 * s, 1.49, 0.07), v(0.135 * s, 1.43, 0.13 * b), v(0.112 * s, 1.27, 0.148 * b), v(0.066 * s, 1.36, 0.132 * b)];
    const lp = { base: V.jacket, rule: (p: Vector3) => clothAt(ctx, V.jacket, p, 0.2).multiplyScalar(0.85) };
    mb.tri(q[0], q[1], q[2], lapW(q[0]), lapW(q[1]), lapW(q[2]), lp);
    mb.tri(q[0], q[2], q[3], lapW(q[0]), lapW(q[2]), lapW(q[3]), lp);
  }

  // sleeves down to the wrist with a cuff and elbow folds
  for (const s of [1, -1]) {
    const P = s > 0 ? 'Left' : 'Right';
    const at = (x: number, rs: number, rf: number): Station => ({ c: v(x * s, 1.445 - (x - 0.2) * 0.012, -0.03 - (x - 0.2) * 0.02), rs: rs * b, rf: rf * b });
    const sk = smoothStations(
      [at(0.12, 0.08, 0.082), at(0.22, 0.074, 0.076), at(0.36, 0.064, 0.067), at(0.5, 0.058, 0.061), at(0.62, 0.054, 0.056), at(0.72, 0.05, 0.052), at(0.745, 0.054, 0.056), at(0.76, 0.052, 0.054)],
      3,
    );
    loft(mb, sk, {
      sides: 24,
      front: v(0, 0, 1),
      weigh: weigher(skel, ['Spine2', `${P}Shoulder`, `${P}Arm`, `${P}ForeArm`, `${P}Hand`]),
      shape: (_i, phi, c) => 0.005 * Math.sin(phi * 5 + Math.abs(c.x) * 120) * gauss(Math.abs(c.x), 0.5, 0.06) + 0.002 * Math.sin(phi * 7 + Math.abs(c.x) * 60),
      paint,
    });
  }
}

export function realPants(ctx: RCtx) {
  const { mb, skel, V } = ctx;
  const b = V.bulk;
  mb.use('pants');
  const paint = { base: V.pants, rule: (p: Vector3) => clothAt(ctx, V.pants, p, 0.35) };
  loft(
    mb,
    smoothStations(
      [
        { c: v(0, 1.07, -0.005), rs: 0.176 * b, rf: 0.126 * b },
        { c: v(0, 0.98, 0), rs: 0.182 * b, rf: 0.13 * b },
        { c: v(0, 0.9, 0), rs: 0.17 * b, rf: 0.12 * b },
        { c: v(0, 0.86, 0), rs: 0.12, rf: 0.08 },
      ],
      3,
    ),
    { sides: 32, front: v(0, 0, 1), capEnd: 'flat', weigh: weigher(skel, ['Hips', 'Spine', 'LeftUpLeg', 'RightUpLeg']), paint },
  );

  for (const s of [1, -1]) {
    const P = s > 0 ? 'Left' : 'Right';
    const U = skel.defs[skel.index.get(`${P}UpLeg`)!].p;
    const K = skel.defs[skel.index.get(`${P}Leg`)!].p;
    const F = skel.defs[skel.index.get(`${P}Foot`)!].p;
    const at = (y: number) => (y > K.y ? U.clone().lerp(K, (U.y - y) / (U.y - K.y)) : K.clone().lerp(F, (K.y - y) / (K.y - F.y)));
    const keys: Station[] = [
      { c: at(1.0).setX(0.085 * s), rs: 0.1 * b, rf: 0.11 * b },
      { c: at(0.86), rs: 0.098 * b, rf: 0.104 * b },
      { c: at(0.72), rs: 0.088 * b, rf: 0.09 * b },
      { c: at(0.6), rs: 0.076, rf: 0.078 },
      { c: at(0.52), rs: 0.072, rf: 0.076 },
      { c: at(0.42), rs: 0.07, rf: 0.074 },
      { c: at(0.26), rs: 0.062, rf: 0.064 },
      { c: at(0.13), rs: 0.06, rf: 0.062 },
      { c: at(0.075), rs: 0.064, rf: 0.068 },
    ];
    loft(mb, smoothStations(keys, 3), {
      sides: 24,
      front: v(0, 0, 1),
      weigh: weigher(skel, ['Hips', `${P}UpLeg`, `${P}Leg`, `${P}Foot`]),
      // bunched folds at the knee and above the shoe
      shape: (_i, phi, c) => 0.005 * Math.sin(phi * 4 + c.y * 140) * gauss(c.y, 0.52, 0.05) + 0.004 * Math.sin(phi * 5 + c.y * 160) * gauss(c.y, 0.15, 0.05),
      paint: { base: V.pants, rule: (p) => (Math.abs(p.y - 0.47) < 0.006 ? clothAt(ctx, V.pants, p).multiplyScalar(0.6) : clothAt(ctx, V.pants, p, 0.35)) },
    });
    // cargo pocket with flap on the outer thigh
    const pw = weigher(skel, [`${P}UpLeg`]);
    const pc = at(0.7);
    const out = v(s, 0, 0.15).normalize();
    const base = pc.clone().addScaledVector(out, 0.092 * b);
    const tan = v(-0.15 * s, 0, 1).normalize();
    box(mb, base, v(0.008, 0.05, 0.045), pw, { base: V.pants, rule: (p) => clothAt(ctx, V.pants, p, 0.2).multiplyScalar(0.92) }, out, v(0, 1, 0), tan);
    box(mb, base.clone().add(v(0, 0.05, 0)).addScaledVector(out, 0.004), v(0.007, 0.012, 0.048), pw, { base: V.pants.clone().multiplyScalar(0.8) }, out, v(0, 1, 0), tan);
  }

  // belt + buckle
  mb.use('leather');
  const bw = weigher(skel, ['Hips', 'Spine']);
  loft(
    mb,
    [
      { c: v(0, 1.07, -0.005), rs: 0.18 * b, rf: 0.13 * b },
      { c: v(0, 1.035, -0.004), rs: 0.181 * b, rf: 0.131 * b },
    ],
    { sides: 40, front: v(0, 0, 1), weigh: bw, paint: { base: V.belt } },
  );
  mb.use('metal');
  box(mb, v(0, 1.052, 0.131 * b + 0.004), v(0.024, 0.017, 0.004), bw, { base: new Color('#9a7a3e') });
}

export function realShoes(ctx: RCtx) {
  const { mb, skel, V } = ctx;
  mb.use('leather');
  for (const s of [1, -1]) {
    const P = s > 0 ? 'Left' : 'Right';
    const x = skel.defs[skel.index.get(`${P}Foot`)!].p.x;
    const keys: Station[] = [
      { c: v(x, 0.05, -0.085), rs: 0.046, rf: 0.042 },
      { c: v(x, 0.055, -0.06), rs: 0.054, rf: 0.054 },
      { c: v(x, 0.055, -0.01), rs: 0.056, rf: 0.056 },
      { c: v(x + 0.003 * s, 0.045, 0.06), rs: 0.058, rf: 0.044 },
      { c: v(x + 0.006 * s, 0.036, 0.13), rs: 0.055, rf: 0.034 },
      { c: v(x + 0.007 * s, 0.03, 0.185), rs: 0.046, rf: 0.027 },
      { c: v(x + 0.007 * s, 0.027, 0.21), rs: 0.028, rf: 0.02 },
    ];
    loft(mb, smoothStations(keys, 3), {
      sides: 20,
      front: v(0, 1, 0),
      capStart: 'flat',
      capEnd: 'flat',
      weigh: weigher(skel, [`${P}Leg`, `${P}Foot`, `${P}ToeBase`]),
      paint: {
        base: V.shoe,
        rule: (p) => (p.y < 0.013 ? new Color('#0f0c0a') : clothAt(ctx, V.shoe, p, 0.15).multiplyScalar(p.y > 0.07 ? 0.85 : 1)),
      },
    });
  }
}
