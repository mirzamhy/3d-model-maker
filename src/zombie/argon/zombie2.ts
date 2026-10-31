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

/** Palette from spec/zombie2.spec.json, darkened about 12% because the studio and horror lights over-expose pale colours. */
const C = {
  skin: '#a9a799',
  jacket: '#818181',
  vest: '#5c5c5c',
  shirt: '#d6d0c4',
  tie: '#4b3b2d',
  pants: '#3e3e3e',
  shoe: '#33261f',
  belt: '#2a211b',
  hair: '#5e5144',
};

function buildHair(ctx: RCtx) {
    ctx.mb.use('hair');
    const wHead = rigid(ctx.skel, 'Head');
    const s0 = ctx.seed;

    // Skull profile: [h, side radius, front radius, z center]
    const T = [
        [0.060, 0.0749, 0.0910, 0.025],
        [0.090, 0.0803, 0.1017, 0.015],
        [0.115, 0.0846, 0.1058, 0.009], // Clamped bottom for the cap
        [0.150, 0.0920, 0.1124, 0.000],
        [0.170, 0.0942, 0.1156, -0.005],
        [0.190, 0.0899, 0.1113, -0.010],
        [0.210, 0.0803, 0.1017, -0.015],
        [0.225, 0.0642, 0.0856, -0.017],
        [0.235, 0.0428, 0.0535, -0.017],
        [0.243, 0.0021, 0.0021, -0.017]
    ];

    // 1. SCALP CAP: built only from stations with h >= 0.115
    const rawStations: Station[] = T.filter(t => t[0] >= 0.114).map(([h, rs, rf, z]) => ({
        c: v(0, HY + h, z), rs: rs + 0.007, rf: rf + 0.007
    }));
    
    loft(ctx.mb, smoothStations(rawStations, 3), {
        sides: 64,
        front: v(0, 0, 1),
        weigh: wHead,
        capEnd: 'flat',
        paint: { base: new Color(C.hair).multiplyScalar(0.7) },
        shape: (i, phi, c) => 0.004 * (fbm(s0 + 3, c.x * 40 + phi * 5, c.y * 40, c.z * 40, 1) - 0.5),
        open: (phi, ring, c) => {
            const h = c.y - HY;
            const a = Math.abs(fromFrontSigned(phi));
            return (a < 1.2 && h < 0.215 - 0.03 * a * a) || // smooth curved hairline
                   (a >= 1.2 && a < 1.9 && h < 0.115) ||    // ears and cheeks
                   (a >= 1.9 && h < 0.075);                 // nape
        }
    });

    // 2. CLUMPS: dense overlapping strands covering the cap
    const crown = v(0, HY + 0.243, -0.017);
    for (let i = 0; i < 300; i++) {
        const hsh = (j: number) => hash(s0, i * 15 + j);
        let a = 0, h = 0, isLoose = false;
        
        let rx = 0.005 + 0.004 * hsh(12);
        if (hsh(13) > 0.85) rx = 0.011; // mostly thinner, a few fat ones
        let ry = 0.02 + 0.02 * hsh(9);
        let rz = 0.006 + 0.003 * hsh(10);
        let dirOverride: Vector3 | null = null;

        if (i < 22) { // Fringe over forehead
            a = -0.95 + 1.9 * hsh(1);
            h = 0.215 - 0.03 * a * a + (hsh(2) - 0.5) * 0.015; // roots on hairline curve
            rx = 0.004 + 0.003 * hsh(3);
            ry = 0.012 + 0.018 * hsh(4);
            ry = Math.min(ry, (h - 0.19) * 1.6 + 0.01); // clip length to stay above eyes
            const sweep = -0.9 + 1.8 * hsh(5);
            dirOverride = v(Math.sin(sweep), -0.5, 0.8).normalize();
        } else if (i < 92) { // Top
            a = -Math.PI + 2 * Math.PI * hsh(1);
            h = 0.19 + 0.053 * hsh(2);
        } else if (i < 172) { // Upper sides & temples
            a = 1.2 + 0.8 * hsh(1);
            if (hsh(2) < 0.5) a = -a;
            h = 0.13 + 0.07 * hsh(3);
            ry = 0.015 + 0.01 * hsh(4); // length 0.03 to 0.05
        } else if (i < 272) { // Back
            a = 1.9 + (Math.PI - 1.9) * hsh(1);
            if (hsh(2) < 0.5) a = -a;
            h = 0.07 + 0.12 * hsh(3);
            ry = 0.02 + 0.0175 * hsh(4); // length 0.04 to 0.075
            if (hsh(5) < 0.4) rx = 0.005 + 0.003 * hsh(6);
        } else { // Loose clumps on lower edge
            a = 1.2 + (Math.PI - 1.2) * hsh(1);
            if (hsh(2) < 0.5) a = -a;
            h = (Math.abs(a) >= 1.9) ? 0.075 : 0.115;
            isLoose = true;
        }

        // Interpolate cap surface point
        let row = 0;
        while (row < T.length - 2 && h > T[row + 1][0]) row++;
        const t = Math.max(0, Math.min(1, (h - T[row][0]) / (T[row + 1][0] - T[row][0])));
        const r = (j: number) => T[row][j] + t * (T[row + 1][j] - T[row][j]);
        const rs = r(1) + 0.007, rf = r(2) + 0.007, zc = r(3);

        const root = v(-rs * Math.sin(a), HY + h, zc + rf * Math.cos(a));
        if (isLoose) root.y -= 0.01 + 0.015 * hsh(7);

        let dir: Vector3;
        if (dirOverride) {
            dir = dirOverride;
        } else {
            const norm = v(-Math.sin(a) / rs, Math.max(0, h - 0.2) * 20, Math.cos(a) / rf).normalize();
            dir = root.clone().sub(crown).normalize();
            dir.sub(norm.clone().multiplyScalar(dir.dot(norm))).normalize(); 
            dir.lerp(v(0, -1, 0), i >= 92 && i < 172 ? 0.6 : 0.35); // pull down, mostly down for sides
            dir.x += (hsh(8) - 0.5) * 0.4;
            dir.y += (hsh(9) - 0.5) * 0.4;
            dir.z += (hsh(10) - 0.5) * 0.4;
            dir.normalize();
        }

        const radii = v(rx, ry, rz);
        const c = root.clone().addScaledVector(dir, radii.y - 0.006); // sink 6mm into cap
        const q = new Quaternion().setFromUnitVectors(v(0, 1, 0), dir);
        
        const color = new Color(C.hair).multiplyScalar(0.7 + 0.6 * hsh(11));
        const detail = (i < 22) ? 1 : 0;
        ellipsoid(ctx.mb, c, radii, wHead, { base: color }, detail, q);

        if (isLoose || i < 22) {
            const tipC = root.clone().addScaledVector(dir, radii.y * 2 - 0.006);
            const tipR = v(radii.x * 0.6, 0.01, radii.z * 0.6);
            ellipsoid(ctx.mb, tipC, tipR, wHead, { base: color.clone().multiplyScalar(1.2) }, 0, q);
        }
    }
}

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

function buildInner(ctx: RCtx) {
  const { mb, skel, seed, V } = ctx;
  const B = V.bulk;
  const wT = weigher(skel, ['Hips', 'Spine', 'Spine1', 'Spine2', 'Neck']);
  const wCol = weigher(skel, ['Spine2', 'Neck']);

  // 1. Shirt body
  mb.use('shirt');
  const colShirt = V.shirt || new Color('#e6e2dc');
  const paintShirt = {
    base: colShirt,
    rule: (p: Vector3) => {
      let c = clothAt(ctx, colShirt, p, 0.45);
      if (bloodRun(ctx, p, 0.03, 0.06, 1.35, 1.0) > 0.2) c = c.clone().lerp(new Color('#6a4a3a'), 0.25);
      return c;
    }
  };

  const shirtData = [
    { y: 0.88, rs: 0.150, rf: 0.108, zc: 0.000 },
    { y: 1.05, rs: 0.158, rf: 0.112, zc: -0.008 },
    { y: 1.25, rs: 0.170, rf: 0.118, zc: -0.013 },
    { y: 1.40, rs: 0.182, rf: 0.112, zc: -0.018 },
    { y: 1.47, rs: 0.140, rf: 0.095, zc: -0.020 },
    { y: 1.51, rs: 0.075, rf: 0.068, zc: -0.020 }
  ];
  const stS = shirtData.map(s => ({ c: v(0, s.y, s.zc), rs: s.rs * B, rf: s.rf * B }));
  loft(mb, smoothStations(stS, 5), {
    sides: 48, front: v(0, 0, 1), weigh: wT, capStart: 'flat', paint: paintShirt,
    shape: (i, phi, c) => {
      const f = fromFrontSigned(phi);
      const belly = Math.max(0, 1.4 - c.y) * 2;
      return 0.003 * gauss(f, 0, 0.05) + 0.005 * (1 + belly) * (fbm(seed + 21, c.x * 20 + phi * 4, c.y * 8, c.z * 20, 1) - 0.5);
    }
  });

  // 2. Shirt collar
  const stC = [
    { c: v(0, 1.49, -0.018), rs: 0.068 * B, rf: 0.064 * B },
    { c: v(0, 1.58, -0.018), rs: 0.062 * B, rf: 0.058 * B }
  ];
  loft(mb, stC, {
    sides: 24, front: v(0, 0, 1), weigh: wCol, paint: paintShirt,
    open: (phi) => Math.abs(fromFrontSigned(phi)) < 0.28
  });
  
  const qFlapL = new Quaternion().setFromAxisAngle(v(0, 1, 0), -0.35);
  const qFlapR = new Quaternion().setFromAxisAngle(v(0, 1, 0), 0.35);
  ellipsoid(mb, v(0.04, 1.55, 0.06), v(0.02, 0.012, 0.006), wCol, paintShirt, 1, qFlapL);
  ellipsoid(mb, v(-0.04, 1.55, 0.06), v(0.02, 0.012, 0.006), wCol, paintShirt, 1, qFlapR);

  // 3. Shirt cuffs
  [-1, 1].forEach(s => {
    const wArm = weigher(skel, [s > 0 ? 'LeftForeArm' : 'RightForeArm', s > 0 ? 'LeftHand' : 'RightHand']);
    loft(mb, [
      { c: v(s * 0.725, 1.44, -0.03), rs: 0.042 * B, rf: 0.044 * B },
      { c: v(s * 0.775, 1.44, -0.03), rs: 0.042 * B, rf: 0.044 * B }
    ], { sides: 20, front: v(0, 1, 0), weigh: wArm, capStart: 'flat', capEnd: 'flat', paint: paintShirt });
  });

  // 4. Vest
  const colVest = new Color('#6b6b6b');
  const vestData = [
    { y: 0.98, rs: 0.163, rf: 0.116, zc: -0.006 },
    { y: 1.10, rs: 0.168, rf: 0.119, zc: -0.010 },
    { y: 1.25, rs: 0.178, rf: 0.124, zc: -0.014 },
    { y: 1.38, rs: 0.186, rf: 0.118, zc: -0.018 },
    { y: 1.44, rs: 0.165, rf: 0.105, zc: -0.020 }
  ];
  const stV = vestData.map(s => ({ c: v(0, s.y, s.zc), rs: s.rs * B, rf: s.rf * B }));
  loft(mb, smoothStations(stV, 4), {
    sides: 56, front: v(0, 0, 1), weigh: wT,
    paint: { base: colVest, rule: p => clothAt(ctx, colVest, p, 0.5) },
    open: (phi, r, c) => {
      const f = Math.abs(fromFrontSigned(phi));
      if (c.y > 1.20 && f < ((c.y - 1.20) / 0.20) * 0.62) return true;
      if (c.y > 1.43 && f < 1.9) return true;
      return false;
    }
  });

  // Buttons
  mb.use('metal');
  const paintBtn = { base: new Color('#1d1d1d') };
  [1.17, 1.12, 1.07, 1.02, 0.99].forEach(y => {
    let s0 = vestData[0], s1 = vestData[1];
    for (let i = 0; i < vestData.length - 1; i++) {
      if (vestData[i].y <= y && vestData[i + 1].y >= y) { s0 = vestData[i]; s1 = vestData[i + 1]; }
    }
    const t = (y - s0.y) / (s1.y - s0.y + 1e-5);
    const bz = s0.zc + (s1.zc - s0.zc) * t + (s0.rf + (s1.rf - s0.rf) * t) * B + 0.003;
    ellipsoid(mb, v(0, y, bz), v(0.0065, 0.0065, 0.0065), wT, paintBtn);
  });

  // 5. Tie
  mb.use('shirt');
  const colTie = new Color('#4b3b2d');
  const paintTie = {
    base: colTie,
    rule: (p: Vector3) => {
      let c = colTie.clone();
      if (Math.floor((p.x + p.y) / 0.018) % 2 === 0) c.lerp(new Color(0, 0, 0), 0.12);
      return c;
    }
  };
  
  const qKnot = new Quaternion().setFromAxisAngle(v(0, 0, 1), 0.1);
  ellipsoid(mb, v(0.006, 1.495, 0.078), v(0.017, 0.016, 0.014), wCol, paintTie, 1, qKnot);

  const stTie = Array.from({ length: 8 }, (_, i) => {
    const t = i / 7;
    let hw = 0.014 + (0.030 - 0.014) * t;
    if (t > 0.8) hw *= (1 - (t - 0.8) * 3);
    return {
      c: v(0.012 * Math.sin(t * 2.2), 1.48 - 0.46 * t, 0.125 - 0.012 * t + 0.006),
      rs: hw, rf: 0.004
    };
  });
  
  loft(mb, stTie, {
    sides: 8, front: v(0, 0, 1), weigh: wT, capEnd: 'point', paint: paintTie
  });
}

function buildSuit(ctx: RCtx) {
  const { mb, skel, V, seed } = ctx;
  const wBody = weigher(skel, ['Hips', 'Spine', 'Spine1', 'Spine2', 'Neck', 'LeftShoulder', 'RightShoulder']);
  const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
  const clamp = (v: number, min: number, max: number) => Math.max(min, Math.min(max, v));

  mb.use('shirt'); // Use shirt bucket for the fabric bump shader

  // 1. Jacket body
  loft(mb, smoothStations([
    { c: v(0, 0.82, 0.00), rs: 0.200 * V.bulk, rf: 0.140 * V.bulk },
    { c: v(0, 0.95, -0.005), rs: 0.190 * V.bulk, rf: 0.133 * V.bulk },
    { c: v(0, 1.10, -0.010), rs: 0.185 * V.bulk, rf: 0.130 * V.bulk },
    { c: v(0, 1.30, -0.015), rs: 0.205 * V.bulk, rf: 0.138 * V.bulk },
    { c: v(0, 1.40, -0.020), rs: 0.225 * V.bulk, rf: 0.130 * V.bulk },
    { c: v(0, 1.47, -0.022), rs: 0.170 * V.bulk, rf: 0.105 * V.bulk },
    { c: v(0, 1.52, -0.022), rs: 0.095 * V.bulk, rf: 0.085 * V.bulk },
  ], 6), {
    sides: 56, front: v(0, 0, 1), weigh: wBody,
    open: (phi, ring, c) => {
      const a = fromFrontSigned(phi);
      if (c.y > 1.51 && Math.abs(a) < 1.3) return true; // Open neck
      const t = clamp((c.y - 0.82) / 0.58, 0, 1);
      const half = 0.25 + 0.4 * Math.sin(Math.min(1, t * 1.15) * Math.PI * 0.5);
      return Math.abs(a) < half; // Open front
    },
    shape: (i, phi, c) => {
      const n = fbm(seed + 11, c.x * 14 + phi * 3, c.y * 6, c.z * 14, 1) - 0.5;
      return 0.007 * n * (c.y < 1.3 ? 1 : 0.3) + 0.004 * Math.sin(phi * 3); // Dust & sag
    },
    paint: {
      base: new Color(), rule: (p) => {
        const c = clothAt(ctx, V.jacket, p, 0.5);
        const stain = bloodRun(ctx, p, 0, 0.4, 1.5, 0.8);
        return stain > 0 ? c.lerp(new Color('#5a3a30'), stain * 0.25) : c;
      }
    }
  });

  // 2. Collar
  const wCollar = weigher(skel, ['Spine2', 'Neck']);
  loft(mb, [
    { c: v(0, 1.47, -0.02), rs: 0.070 * V.bulk, rf: 0.065 * V.bulk },
    { c: v(0, 1.56, -0.02), rs: 0.085 * V.bulk, rf: 0.075 * V.bulk },
  ], {
    sides: 24, front: v(0, 0, 1), weigh: wCollar,
    open: (phi) => Math.abs(fromFrontSigned(phi)) < 0.75,
    paint: { base: new Color(), rule: (p) => clothAt(ctx, V.jacket, p, 0.5).multiplyScalar(0.85) }
  });

  // 3. Lapels & 5. Sleeves
  const darkMetal = new Color('#2a2a2a');
  for (const s of [1, -1]) {
    const P = s > 0 ? 'Left' : 'Right';
    
    // Lapels
    const lapelSt = [];
    for (let i = 0; i < 8; i++) {
      const t = i / 7;
      lapelSt.push({
        c: v(lerp(s * 0.05, s * 0.115, t) + s * 0.01, lerp(1.50, 1.12, t), lerp(0.09, 0.128, t) + 0.01),
        rs: lerp(0.026, 0.010, t) * V.bulk, rf: 0.006 * V.bulk
      });
    }
    loft(mb, lapelSt, {
      sides: 8, front: v(0, 0, 1), weigh: wBody,
      paint: { base: new Color(), rule: (p) => clothAt(ctx, V.jacket, p, 0.5).multiplyScalar(0.95) }
    });

    // Sleeves
    const wArm = weigher(skel, [`${P}Shoulder`, `${P}Arm`, `${P}ForeArm`]);
    const px = (x: number) => x * s;
    loft(mb, smoothStations([
      { c: v(px(0.19), 1.44, -0.030), rs: 0.075 * V.bulk, rf: 0.075 * V.bulk },
      { c: v(px(0.30), 1.44, -0.032), rs: 0.062 * V.bulk, rf: 0.064 * V.bulk },
      { c: v(px(0.50), 1.44, -0.035), rs: 0.054 * V.bulk, rf: 0.058 * V.bulk },
      { c: v(px(0.66), 1.44, -0.038), rs: 0.048 * V.bulk, rf: 0.050 * V.bulk },
      { c: v(px(0.73), 1.44, -0.040), rs: 0.044 * V.bulk, rf: 0.046 * V.bulk },
    ], 6), {
      sides: 24, front: v(0, 1, 0), weigh: wArm,
      open: (phi, ring, c) => {
        const h = (hash(seed, ring * 10 + Math.floor(phi * 10)) - 0.5) * 0.15;
        return Math.abs(c.x * s - 0.5) < 0.03 && Math.abs(fromFrontSigned(phi) - (s > 0 ? 1.6 : -1.6)) < 0.55 + h;
      },
      shape: (i, phi, c) => {
        const n = fbm(seed + i, c.x * 10, c.y * 10, c.z * 10, 1) - 0.3;
        return 0.006 * gauss(c.x * s, 0.5, 0.07) * n + hash(seed, i) * 0.002; // elbow wrinkles
      },
      paint: { base: new Color(), rule: (p) => clothAt(ctx, V.jacket, p, 0.55) }
    });

    // Cuff
    loft(mb, [
      { c: v(px(0.70), 1.44, -0.04), rs: 0.048 * V.bulk, rf: 0.050 * V.bulk },
      { c: v(px(0.735), 1.44, -0.04), rs: 0.048 * V.bulk, rf: 0.050 * V.bulk },
    ], {
      sides: 24, front: v(0, 1, 0), weigh: wArm,
      paint: { base: new Color(), rule: (p) => clothAt(ctx, V.jacket, p, 0.6).multiplyScalar(0.85) } // darker
    });
    
    // Cuff buttons
    mb.use('metal');
    ellipsoid(mb, v(px(0.71), 1.40, -0.04), v(0.004, 0.004, 0.004), wArm, { base: darkMetal });
    ellipsoid(mb, v(px(0.725), 1.40, -0.04), v(0.004, 0.004, 0.004), wArm, { base: darkMetal });
    mb.use('shirt'); // restore bucket for the next iteration
  }

  // 4. Buttons (Body)
  mb.use('metal');
  ellipsoid(mb, v(0, 1.05, 0.13 * V.bulk), v(0.009, 0.009, 0.009), wBody, { base: darkMetal });
  ellipsoid(mb, v(0, 0.96, 0.135 * V.bulk), v(0.009, 0.009, 0.009), wBody, { base: darkMetal });
}

function pelvis(ctx: RCtx) {
  const { mb, skel, V } = ctx;
  mb.use('pants');
  const weigh = weigher(skel, ['Hips', 'Spine', 'LeftUpLeg', 'RightUpLeg']);
  loft(mb, [
    { c: v(0, 0.80, 0.000), rs: 0.170 * V.bulk, rf: 0.125 * V.bulk },
    { c: v(0, 0.92, 0.000), rs: 0.172 * V.bulk, rf: 0.126 * V.bulk },
    { c: v(0, 1.04, -0.004), rs: 0.166 * V.bulk, rf: 0.122 * V.bulk },
    { c: v(0, 1.07, -0.006), rs: 0.164 * V.bulk, rf: 0.120 * V.bulk }
  ], {
    sides: 48, front: v(0, 0, 1), weigh, capEnd: 'flat',
    paint: { base: V.pants, rule: (p) => clothAt(ctx, V.pants, p, 0.5) }
  });
}

function belt(ctx: RCtx) {
  const { mb, skel, V } = ctx;
  const weigh = weigher(skel, ['Hips', 'Spine', 'LeftUpLeg', 'RightUpLeg']);
  mb.use('leather');
  loft(mb, [
    { c: v(0, 1.025, -0.004), rs: 0.170 * V.bulk, rf: 0.126 * V.bulk }, // +0.004
    { c: v(0, 1.062, -0.005), rs: 0.168 * V.bulk, rf: 0.124 * V.bulk }
  ], { sides: 48, front: v(0, 0, 1), weigh, capStart: 'none', capEnd: 'none', paint: { base: V.belt } });

  mb.use('metal');
  const bC = v(0, 1.043, 0.125 * V.bulk + 0.004); // zFront + 0.004
  box(mb, bC, v(0.022, 0.016, 0.003), weigh, { base: new Color('#8c7a52') });
  box(mb, bC, v(0.015, 0.010, 0.0035), weigh, { base: new Color('#1a1410') });
}

function legs(ctx: RCtx) {
  const { mb, skel, V, seed } = ctx;
  for (const s of [1, -1]) {
    const P = s > 0 ? 'Left' : 'Right';
    const weigh = weigher(skel, [`${P}UpLeg`, `${P}Leg`, `${P}Foot`]);
    const px = (x: number) => x * s;

    mb.use('skin');
    loft(mb, [
      { c: v(px(0.103), 0.60, 0.009), rs: 0.065 * V.bulk, rf: 0.073 * V.bulk },
      { c: v(px(0.106), 0.52, 0.015), rs: 0.062 * V.bulk, rf: 0.070 * V.bulk }, // -0.008
      { c: v(px(0.108), 0.44, 0.009), rs: 0.059 * V.bulk, rf: 0.063 * V.bulk }
    ], { sides: 20, front: v(0, 0, 1), weigh, paint: { base: new Color(), rule: p => skinAt(ctx, p, 0.15, 0.1) } });

    mb.use('pants');
    const st = smoothStations([
      { c: v(px(0.100), 0.98, 0.000), rs: 0.098 * V.bulk, rf: 0.108 * V.bulk },
      { c: v(px(0.101), 0.80, 0.004), rs: 0.093 * V.bulk, rf: 0.104 * V.bulk },
      { c: v(px(0.106), 0.52, 0.015), rs: 0.070 * V.bulk, rf: 0.078 * V.bulk },
      { c: v(px(0.109), 0.30, 0.003), rs: 0.064 * V.bulk, rf: 0.068 * V.bulk },
      { c: v(px(0.111), 0.12, -0.012), rs: 0.062 * V.bulk, rf: 0.066 * V.bulk },
      { c: v(px(0.112), 0.06, -0.012), rs: 0.066 * V.bulk, rf: 0.070 * V.bulk }
    ], 5);

    loft(mb, st, {
      sides: 28, front: v(0, 0, 1), weigh, hem: s > 0 ? 0.05 : 0.03,
      shape: (i, phi, c) => {
        const crease = 0.004 * gauss(fromFrontSigned(phi), 0, 0.07);
        const wr = 0.006 * (fbm(seed + 31 + (s > 0 ? 0 : 7), c.x * 25 + phi * 4, c.y * 10, c.z * 25, 1) - 0.5) * (1 + 1.2 * gauss(c.y, 0.52, 0.08));
        return crease + wr;
      },
      open: (phi, ring, c) => {
        const hole = Math.abs(c.y - 0.52) < 0.045 + 0.012 * (hash(seed, 800 + Math.floor(phi * 20)) - 0.5) &&
                     Math.abs(fromFrontSigned(phi)) < 0.5 + 0.12 * (hash(seed, 830 + Math.floor((c.y - 0.4) * 80)) - 0.5);
        const fray = c.y < 0.09 && hash(seed, 860 + Math.floor(phi * 14) + (s > 0 ? 0 : 20)) < 0.22;
        return hole || fray;
      },
      paint: { base: V.pants, rule: (p) => clothAt(ctx, V.pants, p, 0.6) }
    });
  }
}

function shoes(ctx: RCtx) {
  const { mb, skel, V, seed } = ctx;
  mb.use('leather');
  const scuffedColor = V.shoe.clone().lerp(new Color('#ffffff'), 0.25);
  
  for (const s of [1, -1]) {
    const P = s > 0 ? 'Left' : 'Right';
    const weigh = weigher(skel, [`${P}Foot`, `${P}ToeBase`, `${P}Toe_End`]);
    const px = (x: number) => x * s;
    const lerpX = (t: number) => px(0.110 + (0.118 - 0.110) * t);

    loft(mb, [
      { c: v(lerpX(0), 0.055, -0.075), rs: 0.040 * V.bulk, rf: 0.050 * V.bulk },
      { c: v(lerpX(0.26), 0.062, 0.010), rs: 0.050 * V.bulk, rf: 0.062 * V.bulk },
      { c: v(lerpX(0.54), 0.048, 0.100), rs: 0.050 * V.bulk, rf: 0.042 * V.bulk },
      { c: v(lerpX(0.79), 0.038, 0.180), rs: 0.049 * V.bulk, rf: 0.032 * V.bulk },
      { c: v(lerpX(1.0), 0.030, 0.245), rs: 0.038 * V.bulk, rf: 0.026 * V.bulk }
    ], {
      sides: 20, front: v(0, 1, 0), weigh, capStart: 'flat', capEnd: 'point', tipLen: 0.01,
      paint: { base: V.shoe, rule: p => (fbm(seed, p.x * 40, p.y * 40, p.z * 40, 2) > 0.62 && p.z > 0.18) ? scuffedColor : V.shoe }
    });

    const soleC = new Color('#17120f');
    loft(mb, [
      { c: v(lerpX(0.02), 0.01, -0.070), rs: 0.040 * V.bulk, rf: 0.01 },
      { c: v(lerpX(0.79), 0.01, 0.180), rs: 0.050 * V.bulk, rf: 0.01 },
      { c: v(lerpX(1.0), 0.01, 0.245), rs: 0.038 * V.bulk, rf: 0.01 }
    ], { sides: 20, front: v(0, 1, 0), weigh, capStart: 'flat', capEnd: 'flat', paint: { base: soleC } });

    box(mb, v(lerpX(0), -0.015, -0.035), v(0.035 * V.bulk, 0.015, 0.04), weigh, { base: soleC });

    for (const lz of [0.02, 0.045, 0.07, 0.095, 0.12]) {
      const t = (lz - 0.010) / 0.090;
      const ly = 0.062 - t * (0.062 - 0.048);
      const lcx = px(0.111 + t * 0.003);
      box(mb, v(lcx, ly + 0.002, lz), v(0.02, 0.0015, 0.003), weigh, { base: new Color('#1a1410') });
    }
  }
}

function buildLower(ctx: RCtx) {
  pelvis(ctx);
  belt(ctx);
  legs(ctx);
  shoes(ctx);
}

export function buildZombie2(seed: number): { skel: Skel; mb: MeshBuilder; geometry: BufferGeometry; material: Material[] } {
  const skel = buildSkeleton(REAL_BONE_DEFS);
  const mb = new MeshBuilder(seed, true);
  const V = makeVariant(seed);
  // fixed palette from spec/zombie2.spec.json
  V.skin = new Color(C.skin);
  V.jacket = new Color(C.jacket);
  V.shirt = new Color(C.shirt);
  V.pants = new Color(C.pants);
  V.shoe = new Color(C.shoe);
  V.belt = new Color(C.belt);
  const ctx: RCtx = { mb, skel, seed, V };

  buildHead(ctx);
  buildHair(ctx);
  buildBody(ctx);
  buildInner(ctx);
  buildSuit(ctx);
  buildLower(ctx);

  const { geometry, materials } = mb.geometry();
  const material = materials.map((n) => realMaterial(n));
  
  return { skel, mb, geometry, material };
}
