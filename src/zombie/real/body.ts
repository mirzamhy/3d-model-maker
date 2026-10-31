// Semi-realistic exposed skin: neck, upper chest (seen through the V-neck), wrists, hands.
import { Vector3 } from 'three';
import { box, ellipsoid, fromFrontSigned, loft, smoothStations, weigher, type Station } from '../mesh';
import { gauss } from '../noise';
import { bloodRun, skinAt, type RCtx } from './variant';

const v = (x: number, y: number, z: number) => new Vector3(x, y, z);
const TORSO = ['Hips', 'Spine', 'Spine1', 'Spine2', 'Neck', 'LeftShoulder', 'RightShoulder'];

export function realNeckChest(ctx: RCtx) {
  const { mb, skel, V } = ctx;
  mb.use('skin');
  const b = V.bulk;
  loft(
    mb,
    smoothStations(
      [
        { c: v(0, 1.12, -0.02), rs: 0.165 * b, rf: 0.112 * b },
        { c: v(0, 1.3, -0.025), rs: 0.18 * b, rf: 0.118 * b },
        { c: v(0, 1.42, -0.03), rs: 0.15 * b, rf: 0.095 * b },
        { c: v(0, 1.49, -0.025), rs: 0.08, rf: 0.07 },
      ],
      3,
    ),
    {
      sides: 24,
      front: v(0, 0, 1),
      weigh: weigher(skel, TORSO),
      capStart: 'flat',
      paint: { base: V.skin, rule: (p) => skinAt(ctx, p, 0.15, bloodRun(ctx, p, 0.01, 0.07, 1.5, 1.2) * 0.5).lerp(V.bloodDark, bloodRun(ctx, p, 0.01, 0.06, 1.48, 1.22) * 0.6) },
    },
  );

  // neck with tendons and Adam's apple; blood runs from the mouth down the throat
  loft(
    mb,
    smoothStations(
      [
        { c: v(0, 1.4, -0.028), rs: 0.075, rf: 0.07 },
        { c: v(0, 1.48, -0.022), rs: 0.062, rf: 0.058 },
        { c: v(0, 1.55, -0.01), rs: 0.06, rf: 0.058 },
        { c: v(0, 1.61, -0.004), rs: 0.054, rf: 0.054 },
      ],
      3,
    ),
    {
      sides: 24,
      front: v(0, 0, 1),
      weigh: weigher(skel, ['Spine2', 'Neck', 'Head']),
      shape: (_i, phi, c) => {
        const a = fromFrontSigned(phi);
        return 0.005 * gauss(Math.abs(a), 0.55, 0.14) * gauss(c.y, 1.52, 0.06) + 0.006 * gauss(a, 0, 0.16) * gauss(c.y, 1.535, 0.02);
      },
      paint: {
        base: V.skin,
        rule: (p) => skinAt(ctx, p, 0.08, 0.1).lerp(V.bloodDark, bloodRun(ctx, p, 0.005, 0.05, 1.63, 1.42) * 0.75),
      },
    },
  );
}

export function realHand(ctx: RCtx, s: 1 | -1) {
  const { mb, skel, V } = ctx;
  const P = s > 0 ? 'Left' : 'Right';
  const H = `${P}Hand`;
  const hp = skel.defs[skel.index.get(H)!].p;
  const handPaint = {
    base: V.skin,
    rule: (p: Vector3) => {
      const c = skinAt(ctx, p, 0.05, 0.15);
      const tip = Math.min(1, Math.max(0, (Math.abs(p.x) - 0.82) / 0.08));
      return c.lerp(V.blood, Math.min(0.9, tip * 0.5 + bloodRun(ctx, p, p.x, 1, 2, 0) * 0.35));
    },
  };
  mb.use('skin');

  // wrist (disappears into the sleeve cuff)
  loft(
    mb,
    [
      { c: v(0.69 * s, hp.y + 0.001, hp.z - 0.005), rs: 0.032, rf: 0.036 },
      { c: v(0.765 * s, hp.y, hp.z), rs: 0.026, rf: 0.033 },
    ],
    { sides: 16, front: v(0, 0, 1), weigh: weigher(skel, [`${P}ForeArm`, H]), paint: handPaint },
  );

  // palm
  const palm: Station[] = [
    { c: v(0.758 * s, hp.y - 0.002, hp.z), rs: 0.023, rf: 0.032 },
    { c: v(0.79 * s, hp.y - 0.004, hp.z - 0.001), rs: 0.022, rf: 0.04 },
    { c: v(0.83 * s, hp.y - 0.005, hp.z - 0.002), rs: 0.019, rf: 0.047 },
    { c: v(0.866 * s, hp.y - 0.006, hp.z - 0.003), rs: 0.014, rf: 0.046 },
  ];
  loft(mb, smoothStations(palm, 2), {
    sides: 16,
    front: v(0, 0, 1),
    capStart: 'flat',
    capEnd: 'flat',
    weigh: weigher(skel, [`${P}ForeArm`, H, `${P}HandIndex1`, `${P}HandMiddle1`, `${P}HandRing1`, `${P}HandPinky1`, `${P}HandThumb1`]),
    paint: handPaint,
  });
  // thumb mound
  ellipsoid(mb, v(0.79 * s, hp.y - 0.012, hp.z + 0.022), v(0.028, 0.013, 0.016), weigher(skel, [H, `${P}HandThumb1`]), handPaint, 1);

  for (const f of ['Index', 'Middle', 'Ring', 'Pinky', 'Thumb']) {
    const names = f === 'Thumb' ? ['Thumb1', 'Thumb2', 'Thumb3', 'Thumb_End'] : ['1', '2', '3', '_End'].map((n) => f + n);
    const pts = names.map((n) => skel.defs[skel.index.get(`${P}Hand${n}`)!].p);
    const k = f === 'Thumb' ? 1.18 : f === 'Pinky' ? 0.86 : 1;
    // knuckle (joint) rings slightly fatter than mid-phalanx rings
    const keys: Station[] = [];
    for (let j = 0; j < 3; j++) {
      const rj = (0.0098 - j * 0.0007) * k;
      keys.push({ c: pts[j].clone(), rs: rj, rf: rj * 0.92 });
      keys.push({ c: pts[j].clone().lerp(pts[j + 1], 0.5), rs: rj * 0.86, rf: rj * 0.8 });
    }
    keys.push({ c: pts[3].clone(), rs: 0.0074 * k, rf: 0.0066 * k });
    loft(mb, smoothStations(keys, 2), {
      sides: 10,
      front: v(0, 1, 0),
      capStart: 'flat',
      capEnd: 'point',
      tipLen: 0.007,
      weigh: weigher(skel, [H, ...names.slice(0, 3).map((n) => `${P}Hand${n}`)]),
      paint: handPaint,
    });
    // nail on the back of the last phalanx
    const dir = pts[3].clone().sub(pts[2]).normalize();
    const up = v(0, 1, 0).addScaledVector(dir, -dir.y).normalize();
    const side = new Vector3().crossVectors(dir, up);
    const nc = pts[2].clone().lerp(pts[3], 0.72).addScaledVector(up, 0.0064 * k);
    box(mb, nc, v(0.0075 * k, 0.0012, 0.0058 * k), weigher(skel, [`${P}Hand${names[2]}`]), { base: V.skin.clone().lerp(V.bloodDark, 0.45) }, dir, up, side);
  }
}
