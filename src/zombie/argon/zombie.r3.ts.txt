import { BufferGeometry, Color, Material, Quaternion, Vector3 } from 'three';
import { hash } from '../hash';
import { fbm, gauss } from '../noise';
import { MeshBuilder, loft, smoothStations, weigher, rigid, ellipsoid, box, fromFrontSigned, type Station, type Weigher } from '../mesh';
import { buildSkeleton, type Skel } from '../skeleton';
import { REAL_BONE_DEFS, REAL_HEAD_Y } from '../skeletonReal';
import { makeVariant, skinAt, clothAt, bloodRun, type RCtx } from '../real/variant';
import { realMaterial } from '../real/materials';

const v = (x: number, y: number, z: number) => new Vector3(x, y, z);
const HY = REAL_HEAD_Y;

function buildHead(ctx: RCtx) {
  const { mb, skel } = ctx;
  mb.use('skin');
  const HR = 1.07;
  
  const rawKeys = [
    { h: -0.006, rs: 0.045, rf: 0.050, z: 0.015 },
    { h: 0.010,  rs: 0.055, rf: 0.060, z: 0.025 },
    { h: 0.020,  rs: 0.060, rf: 0.065, z: 0.030 }, // jaw moves forward
    { h: 0.040,  rs: 0.065, rf: 0.075, z: 0.030 },
    { h: 0.060,  rs: 0.070, rf: 0.085, z: 0.025 },
    { h: 0.075,  rs: 0.073, rf: 0.090, z: 0.020 },
    { h: 0.090,  rs: 0.075, rf: 0.095, z: 0.015 },
    { h: 0.110,  rs: 0.078, rf: 0.098, z: 0.010 },
    { h: 0.130,  rs: 0.082, rf: 0.102, z: 0.005 },
    { h: 0.150,  rs: 0.086, rf: 0.105, z: 0.000 },
    { h: 0.170,  rs: 0.088, rf: 0.108, z: -0.005 }, // widest
    { h: 0.190,  rs: 0.084, rf: 0.104, z: -0.010 },
    { h: 0.210,  rs: 0.075, rf: 0.095, z: -0.015 },
    { h: 0.225,  rs: 0.060, rf: 0.080, z: -0.017 },
    { h: 0.235,  rs: 0.040, rf: 0.050, z: -0.017 },
    { h: 0.243,  rs: 0.002, rf: 0.002, z: -0.017 }  // near-point top
  ];

  const keyAt = (h: number) => {
    if (h <= rawKeys[0].h) return rawKeys[0];
    const last = rawKeys[rawKeys.length - 1];
    if (h >= last.h) return last;
    for (let i = 0; i < rawKeys.length - 1; i++) {
      if (h >= rawKeys[i].h && h <= rawKeys[i+1].h) {
        const t = (h - rawKeys[i].h) / (rawKeys[i+1].h - rawKeys[i].h);
        return {
          rs: rawKeys[i].rs + t * (rawKeys[i+1].rs - rawKeys[i].rs),
          rf: rawKeys[i].rf + t * (rawKeys[i+1].rf - rawKeys[i].rf),
          z: rawKeys[i].z + t * (rawKeys[i+1].z - rawKeys[i].z)
        };
      }
    }
    return rawKeys[0];
  };

  const surface = (h: number, a: number, inset: number = 0) => {
    const k = keyAt(h);
    return v(
      -(k.rs * HR - inset) * Math.sin(a),
      HY + h,
      k.z + (k.rf * HR - inset) * Math.cos(a)
    );
  };

  const keys: Station[] = rawKeys.map(k => ({
    c: v(0, HY + k.h, k.z),
    rs: k.rs * HR,
    rf: k.rf * HR
  }));
  const st = smoothStations(keys, 3);
  
  const faceFeature = (h: number, a: number) => {
    let out = 0;
    out += -0.030 * gauss(h, 0.148, 0.020) * gauss(Math.abs(a), 0.47, 0.20); // eyes
    out += +0.009 * gauss(h, 0.172, 0.009) * gauss(Math.abs(a), 0.42, 0.32); // brow
    out += +0.010 * gauss(h, 0.145, 0.014) * gauss(Math.abs(a), 0, 0.09);    // nose bridge
    out += -0.020 * gauss(h, 0.118, 0.012) * gauss(Math.abs(a), 0, 0.14);    // nostril
    out += +0.012 * gauss(h, 0.128, 0.013) * gauss(Math.abs(a), 0.82, 0.18); // cheekbone
    out += -0.020 * gauss(h, 0.092, 0.022) * gauss(Math.abs(a), 0.74, 0.22); // hollow cheek
    out += -0.010 * gauss(h, 0.175, 0.022) * gauss(Math.abs(a), 1.28, 0.20); // temple
    out += -0.010 * gauss(h, 0.085, 0.016) * gauss(Math.abs(a), 0, 0.45);    // mouth
    out += +0.009 * gauss(h, 0.028, 0.015) * gauss(Math.abs(a), 0, 0.25);    // chin
    out += +0.007 * gauss(h, 0.050, 0.016) * gauss(Math.abs(a), 1.15, 0.25); // jaw corner
    out += +0.004 * gauss(h, 0.205, 0.030) * gauss(Math.abs(a), Math.PI, 0.60); // back head
    return out;
  };

  const wHead = rigid(skel, 'Head');
  const wJaw = rigid(skel, 'Jaw');
  const weigh = (p: Vector3) => (p.y < HY + 0.084 && p.z > 0.012 ? wJaw(p) : wHead(p));

  loft(mb, st, {
    sides: 36,
    front: v(0, 0, 1),
    weigh,
    capStart: 'flat',
    capEnd: 'flat',
    shape: (i, phi, c) => faceFeature(c.y - HY, fromFrontSigned(phi)),
    paint: {
      base: new Color(),
      rule: (p) => {
        const h = p.y - HY;
        const a = -Math.atan2(p.x, p.z - keyAt(h).z);
        const depth = faceFeature(h, a);
        const dark = Math.min(1, Math.max(0, -depth) / 0.022) * 0.72;
        
        if (h > 0.079 && h < 0.095 && Math.abs(a) < 0.62) return new Color('#1c0605'); // mouth band
        
        let red = 0;
        red += gauss(h, 0.085, 0.026) * gauss(Math.abs(a), 0, 0.55); // around mouth
        red += gauss(h, 0.118, 0.020) * gauss(Math.abs(a), 0, 0.15); // nasal hole
        red += gauss(h, 0.148, 0.025) * gauss(Math.abs(a), 0.47, 0.20); // bruise around eyes
        
        return skinAt(ctx, p, dark, red);
      }
    }
  });

  // Eyes
  mb.use('eye');
  for (const s of [1, -1]) {
    const outer = surface(0.148, s * 0.47);
    const n = outer.clone().sub(v(0, outer.y, keyAt(0.148).z)).normalize();
    const centre = outer.clone().sub(n.clone().multiplyScalar(0.031));
    
    ellipsoid(mb, centre, v(0.0135, 0.0125, 0.0135), wHead, { base: new Color('#c4d8dc') }, 2);
    
    const pupilPos = centre.clone().add(n.clone().multiplyScalar(0.0122));
    ellipsoid(mb, pupilPos, v(0.003, 0.003, 0.001), wHead, { base: new Color('#333') });
  }

  // Mouth cavity
  mb.use('skin');
  ellipsoid(mb, v(0, HY + 0.084, keyAt(0.084).z + 0.04), v(0.05, 0.022, 0.035), wHead, { base: new Color('#160404') }, 2);

  // Teeth
  mb.use('teeth');
  for (let top = 0; top <= 1; top++) {
    const h = top ? 0.098 : 0.071;
    const n = top ? 12 : 11;
    const w = top ? wHead : wJaw;
    const range = top ? 0.68 : 0.60;
    const upDir = top ? v(0, -1, 0) : v(0, 1, 0); // up vs down
    
    for (let i = 0; i < n; i++) {
      if (hash(ctx.seed, 100 + top * 20 + i) < 0.1) continue; // ~10% missing
      const t = n > 1 ? i / (n - 1) : 0;
      const a = -range + t * (2 * range);
      
      const c = surface(h, a, 0.011);
      const k = keyAt(h);
      
      const outDir = v(c.x, 0, c.z - k.z).normalize();
      const tan = v(outDir.z, 0, -outDir.x);
      
      const len = 0.011 + 0.005 * hash(ctx.seed, 150 + top * 30 + i);
      const col = new Color('#c4b27c').lerp(new Color('#6e5a32'), hash(ctx.seed, 200 + i));
      
      const tilt = (hash(ctx.seed, 300 + i) - 0.5) * 0.3;
      const realUp = upDir.clone().applyAxisAngle(outDir, tilt).normalize();
      
      box(mb, c, v(0.0036, len / 2, 0.003), w, { base: col }, tan, realUp, outDir);
    }
  }

  // Ears
  mb.use('skin');
  for (const s of [1, -1]) {
    const q = new Quaternion().setFromAxisAngle(v(0, 1, 0), -s * 0.25);
    ellipsoid(mb, v(s * 0.087, HY + 0.135, -0.018), v(0.007, 0.027, 0.015), wHead, { base: skinAt(ctx, v(s * 0.087, HY + 0.135, -0.018)) }, 1, q);
  }
}

function buildBody(ctx: RCtx) {
  const { mb, skel, V } = ctx;
  mb.use('skin');
  
  // Neck - Thicker, starting from inside chest, with Adam's apple and tendons
  const wNeck = weigher(skel, ['Spine2', 'Neck', 'Head']);
  loft(mb, smoothStations([
    { c: v(0, 1.36, -0.02), rs: 0.055 * V.bulk, rf: 0.05 * V.bulk },
    { c: v(0, HY + 0.03, -0.01), rs: 0.055 * V.bulk, rf: 0.05 * V.bulk }
  ], 4), {
    sides: 24, front: v(0, 0, 1), weigh: wNeck,
    shape: (i, phi) => {
      const a = Math.abs(fromFrontSigned(phi));
      return (a < 0.2 ? 0.005 : 0) + (Math.abs(a - 1.2) < 0.2 ? 0.004 : 0);
    },
    paint: { base: new Color(), rule: (p) => skinAt(ctx, p) }
  });

  // Chest - High vertex count and subdivisions for smooth soft blood streaks
  const wSpine = weigher(skel, ['Hips', 'Spine', 'Spine1', 'Spine2']);
  loft(mb, smoothStations([
    { c: v(0, 1.1, -0.01), rs: 0.14 * V.bulk, rf: 0.1 * V.bulk },
    { c: v(0, 1.35, -0.01), rs: 0.16 * V.bulk, rf: 0.12 * V.bulk },
    { c: v(0, 1.45, -0.02), rs: 0.15 * V.bulk, rf: 0.1 * V.bulk },
  ], 6), {
    sides: 40, front: v(0, 0, 1), weigh: wSpine,
    paint: { base: new Color(), rule: (p) => {
      const c = skinAt(ctx, p);
      const run = bloodRun(ctx, p, 0, 0.08, 1.45, 1.1);
      if (run > 0) c.lerp(V.bloodDark, run);
      return c;
    }}
  });

  // Hands and Wrists
  for (const s of [1, -1]) {
    const P = s > 0 ? 'Left' : 'Right';
    const wx = (bones: string[]) => weigher(skel, bones.map(b => P + b));
    
    // Forearm / Wrist skin bridging the gap
    loft(mb, smoothStations([
      { c: v(s * 0.62, 1.44, -0.04), rs: 0.035, rf: 0.035 },
      { c: v(s * 0.80, 1.438, -0.03), rs: 0.03, rf: 0.02 }
    ], 3), {
      sides: 16, front: v(0, 1, 0), weigh: wx(['ForeArm', 'Hand']),
      paint: { base: new Color(), rule: (p) => skinAt(ctx, p) }
    });

    // Broad, flat palm with knuckle bumps on the back
    const wPalm = wx(['Hand', 'HandIndex1', 'HandMiddle1', 'HandRing1', 'HandPinky1', 'HandThumb1']);
    loft(mb, smoothStations([
      { c: v(s * 0.76, 1.438, -0.03), rs: 0.04, rf: 0.015 },
      { c: v(s * 0.81, 1.438, -0.03), rs: 0.0425, rf: 0.013 },
      { c: v(s * 0.86, 1.434, -0.03), rs: 0.042, rf: 0.01 }
    ], 3), {
      sides: 24, front: v(0, 1, 0), weigh: wPalm,
      shape: (i, phi) => (Math.abs(fromFrontSigned(phi)) < 0.4 && i > 3) ? 0.003 : 0,
      paint: { base: new Color(), rule: (p) => skinAt(ctx, p) }
    });

    // Thumb mound
    ellipsoid(mb, v(s * 0.79, 1.43, -0.01), v(0.025, 0.015, 0.02), wPalm, { base: new Color(), rule: (p) => skinAt(ctx, p) });

    // Thumb (angled forward, thicker)
    const tSt = [v(s*0.782, 1.428, 0.0), v(s*0.812, 1.42, 0.03), v(s*0.838, 1.414, 0.05), v(s*0.862, 1.41, 0.064)]
      .map((c, i) => ({ c, rs: 0.012 - i*0.001, rf: 0.012 - i*0.001 }));
    const wThumb = wx(['Hand', 'HandThumb1', 'HandThumb2', 'HandThumb3', 'HandThumb_End']);
    
    loft(mb, smoothStations(tSt, 3), {
      sides: 12, front: v(0, 1, 0), weigh: wThumb, capEnd: 'point',
      shape: (i) => (i % 3 === 0 && i > 0 && i < 9) ? 0.002 : 0, // Knuckle bulges
      paint: { base: new Color(), rule: (p) => skinAt(ctx, p, 0, p.x*s > 0.84 ? 0.5 : 0) }
    });
    box(mb, tSt[3].c.clone().add(v(s*0.005, tSt[3].rf, 0)), v(0.007, 0.001, 0.007), wThumb, { base: new Color('#887c71') });

    // Fingers
    const fingers = [
      ['Index', 0.862, 0.001, [0.048, 0.03, 0.025]],
      ['Middle', 0.866, -0.021, [0.052, 0.034, 0.026]],
      ['Ring', 0.862, -0.043, [0.049, 0.032, 0.025]],
      ['Pinky', 0.852, -0.063, [0.038, 0.025, 0.022]]
    ] as const;

    for (const [f, x0, z0, lens] of fingers) {
      const st: Station[] = [];
      let px = x0;
      for (let i = 0; i <= 3; i++) {
        const r = 0.0095 - i * 0.0008; // Thicker base tapering to 0.007 tip
        st.push({ c: v(s * px, 1.434, z0), rs: r, rf: r });
        if (i < 3) px += lens[i];
      }
      
      const wf = wx([`Hand${f}1`, `Hand${f}2`, `Hand${f}3`, `Hand${f}_End`]);
      loft(mb, smoothStations(st, 3), {
        sides: 12, front: v(0, 1, 0), weigh: wf, capEnd: 'point',
        shape: (i) => (i % 3 === 0 && i > 0 && i < 9) ? 0.0015 : 0, // Joint bulges
        paint: { base: new Color(), rule: (p) => skinAt(ctx, p, 0, p.x*s > px - 0.02 ? 0.7 : 0) }
      });
      // Flat nail on top of the last segment
      box(mb, st[3].c.clone().add(v(0, st[3].rf - 0.001, 0)), v(0.008, 0.001, 0.005), wf, { base: new Color('#887c71') });
    }
  }
}

function buildClothes(ctx: RCtx) {
  const { mb, skel, V } = ctx;
  const wSpine = weigher(skel, ['Hips', 'Spine', 'Spine1', 'Spine2', 'LeftShoulder', 'RightShoulder']);

  // Shirt
  mb.use('shirt');
  loft(mb, smoothStations([
    { c: v(0, 0.96, 0), rs: 0.155 * V.bulk, rf: 0.115 * V.bulk },
    { c: v(0, 1.2, -0.01), rs: 0.17 * V.bulk, rf: 0.125 * V.bulk },
    { c: v(0, 1.45, -0.02), rs: 0.175 * V.bulk, rf: 0.12 * V.bulk },
    { c: v(0, 1.48, -0.02), rs: 0.08 * V.bulk, rf: 0.08 * V.bulk },
  ], 6), {
    sides: 48, front: v(0, 0, 1), weigh: wSpine, hem: 0.02,
    open: (phi, ring, c) => {
      const a = fromFrontSigned(phi);
      return c.y > 1.35 && Math.abs(a) < ((c.y - 1.35) / 0.15) * 0.5; // V-neck
    },
    paint: { base: new Color(), rule: (p) => {
      const c = clothAt(ctx, V.shirt, p, 0.4);
      const run = bloodRun(ctx, p, 0, 0.1, 1.45, 1.0);
      if (run > 0) c.lerp(V.blood, run);
      return c;
    }}
  });

  // Jacket
  mb.use('jacket');
  loft(mb, smoothStations([
    { c: v(0, 0.85, 0), rs: 0.175 * V.bulk, rf: 0.13 * V.bulk },
    { c: v(0, 1.1, -0.01), rs: 0.185 * V.bulk, rf: 0.135 * V.bulk },
    { c: v(0, 1.45, -0.02), rs: 0.19 * V.bulk, rf: 0.13 * V.bulk },
    { c: v(0, 1.5, -0.025), rs: 0.1 * V.bulk, rf: 0.09 * V.bulk },
    { c: v(0, 1.53, -0.025), rs: 0.09 * V.bulk, rf: 0.08 * V.bulk },
  ], 3), {
    sides: 40, front: v(0, 0, 1), weigh: wSpine, hem: 0.01,
    open: (phi, ring, c) => {
      const a = fromFrontSigned(phi);
      if (c.y > 1.51 && Math.abs(a) < 1.0) return true; // Front neck opening
      return Math.abs(a) < 0.2 + 0.32 * (ring / 12); // Jacket front opening
    },
    shape: (i, phi) => {
      const a = fromFrontSigned(phi);
      return 0.005 * Math.sin(a * 15); // Vertical folds
    },
    paint: { base: new Color(), rule: (p) => clothAt(ctx, V.jacket, p, 0.6) }
  });
  
  // Jacket sleeves
  for (const s of [1, -1]) {
    const P = s > 0 ? 'Left' : 'Right';
    const wArm = weigher(skel, [`${P}Shoulder`, `${P}Arm`, `${P}ForeArm`]);
    const px = (x: number) => x * s;
    loft(mb, smoothStations([
      { c: v(px(0.18), 1.44, -0.03), rs: 0.06 * V.bulk, rf: 0.065 * V.bulk },
      { c: v(px(0.50), 1.44, -0.04), rs: 0.05 * V.bulk, rf: 0.055 * V.bulk },
      { c: v(px(0.72), 1.44, -0.03), rs: 0.04 * V.bulk, rf: 0.045 * V.bulk },
    ], 3), {
      sides: 20, front: v(0, 1, 0), weigh: wArm,
      shape: (i, phi, c) => {
        const dist = Math.abs(c.x * s - 0.50);
        return dist < 0.1 ? 0.004 * Math.sin(phi * 8) : 0; // elbow wrinkles
      },
      paint: { base: new Color(), rule: (p) => clothAt(ctx, V.jacket, p, 0.6) }
    });
  }

  // Pants (Hips)
  mb.use('pants');
  const wPantsHip = weigher(skel, ['Hips', 'Spine']);
  loft(mb, smoothStations([
    { c: v(0, 0.88, 0), rs: 0.16 * V.bulk, rf: 0.12 * V.bulk },
    { c: v(0, 0.98, 0), rs: 0.17 * V.bulk, rf: 0.13 * V.bulk },
    { c: v(0, 1.05, 0), rs: 0.165 * V.bulk, rf: 0.125 * V.bulk },
  ], 2), {
    sides: 32, front: v(0, 0, 1), weigh: wPantsHip,
    paint: { base: new Color(), rule: (p) => clothAt(ctx, V.pants, p, 0.5) }
  });

  // Pants (Legs)
  for (const s of [1, -1]) {
    const P = s > 0 ? 'Left' : 'Right';
    const wLeg = weigher(skel, [`${P}UpLeg`, `${P}Leg`, `${P}Foot`]);
    const px = (x: number) => x * s;
    loft(mb, smoothStations([
      { c: v(px(0.1), 0.92, 0), rs: 0.075 * V.bulk, rf: 0.09 * V.bulk },
      { c: v(px(0.106), 0.52, 0.015), rs: 0.06 * V.bulk, rf: 0.07 * V.bulk },
      { c: v(px(0.11), 0.15, 0), rs: 0.05 * V.bulk, rf: 0.06 * V.bulk },
    ], 3), {
      sides: 24, front: v(0, 0, 1), weigh: wLeg, hem: 0.01,
      shape: (i, phi, c) => {
        const dist = Math.abs(c.y - 0.52);
        return dist < 0.15 ? 0.005 * Math.sin(phi * 6) : 0; // knee folds
      },
      paint: { base: new Color(), rule: (p) => clothAt(ctx, V.pants, p, 0.5) }
    });
  }

  // Belt
  mb.use('leather');
  loft(mb, [
    { c: v(0, 1.02, 0), rs: 0.168 * V.bulk, rf: 0.128 * V.bulk },
    { c: v(0, 1.05, 0), rs: 0.168 * V.bulk, rf: 0.128 * V.bulk }
  ], {
    sides: 40, front: v(0, 0, 1), weigh: wPantsHip,
    paint: { base: V.belt }
  });
  
  // Belt Buckle
  mb.use('metal');
  box(mb, v(0, 1.035, 0.13 * V.bulk), v(0.02, 0.015, 0.002), wPantsHip, { base: new Color('#8c7a52') });

  // Leather Shoes
  mb.use('leather');
  for (const s of [1, -1]) {
    const P = s > 0 ? 'Left' : 'Right';
    const wShoe = weigher(skel, [`${P}Foot`, `${P}ToeBase`, `${P}Toe_End`]);
    const px = (x: number) => x * s;
    loft(mb, smoothStations([
      { c: v(px(0.115), 0.15, -0.01), rs: 0.045 * V.bulk, rf: 0.055 * V.bulk },
      { c: v(px(0.115), 0.08, -0.015), rs: 0.045 * V.bulk, rf: 0.065 * V.bulk },
      { c: v(px(0.118), 0.025, 0.12), rs: 0.045 * V.bulk, rf: 0.055 * V.bulk },
      { c: v(px(0.12), 0.025, 0.20), rs: 0.045 * V.bulk, rf: 0.03 * V.bulk },
    ], 3), {
      sides: 20, front: v(0, 1, 0), weigh: wShoe, capEnd: 'flat', capStart: 'none',
      paint: { base: V.shoe }
    });
  }
}

export function buildArgon(seed: number): { skel: Skel; mb: MeshBuilder; geometry: BufferGeometry; material: Material[] } {
  const skel = buildSkeleton(REAL_BONE_DEFS);
  const mb = new MeshBuilder(seed, true);
  const V = makeVariant(seed);
  const ctx: RCtx = { mb, skel, seed, V };

  buildHead(ctx);
  buildBody(ctx);
  buildClothes(ctx);

  const { geometry, materials } = mb.geometry();
  const material = materials.map((n) => realMaterial(n));
  
  return { skel, mb, geometry, material };
}
