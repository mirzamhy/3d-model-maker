// F0 step 2: average the measured reference bodies per group (male / female) into ratios of body height,
// and draw a front + side silhouette SVG of every measured body for a visual check.
// Usage: node tools/ref/summarize.mjs [tools/ref/out/ref-profiles.json]
import fs from 'node:fs';
import path from 'node:path';

const src = process.argv[2] ?? 'tools/ref/out/ref-profiles.json';
const outDir = path.dirname(src);
const { models } = JSON.parse(fs.readFileSync(src, 'utf8'));

const group = (m) => (/female/i.test(m.name) ? 'female' : /little_boy/i.test(m.name) ? 'child' : m.skinned && /male/i.test(m.name) ? 'male' : 'other');
const r3 = (x) => Math.round(x * 1000) / 1000;
const dist = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]);

// width/depth of a bone's thickest cross-section and of its middle one
const thick = (b) => (b ? b.slices.reduce((m, s) => Math.max(m, s.in + s.out), 0) : null);
const mid = (b, key) => { if (!b) return null; const s = b.slices[Math.floor(b.slices.length / 2)]; return key === 'w' ? s.in + s.out : s.front + s.back; };

// Headwear or hair built into the body mesh (police cap, bun, big hair) inflates the mesh height and the
// head size. Flag it from the head slices, and measure stature from the Head joint instead of the mesh top.
function headInfo(m) {
  const hy = m.joints.Head?.[1];
  if (hy == null) return { flagged: false, crown: m.height };
  const hs = m.body.filter((s) => s.y > hy);
  const depth = Math.max(...hs.map((s) => s.zMax)) - Math.min(...hs.map((s) => s.zMin));
  const width = Math.max(...hs.map((s) => s.xMax - s.xMin));
  return { flagged: depth > 0.26 || width > 0.22, depth, width, hy };
}
const clean = models.filter((m) => m.joints.Head && !headInfo(m).flagged && /male/i.test(m.name));
// crown height above the Head joint as a share of stature, from the clean adult bodies
const crownShare = clean.reduce((a, m) => a + (m.height - m.joints.Head[1]) / m.height, 0) / clean.length;
const stature = (m) => {
  const h = headInfo(m);
  return h.flagged ? h.hy / (1 - crownShare) : m.height;
};

function features(m) {
  const J = m.joints, B = m.bones, H = stature(m);
  const f = {};
  const hi = headInfo(m);
  f.headwear = hi.flagged ? 1 : 0;
  const y = (n) => (J[n] ? J[n][1] / H : null);
  f.hipsY = y('Hips'); f.spineY = y('Spine'); f.chestY = y('Spine1'); f.neckY = y('Neck'); f.headY = y('Head');
  f.kneeY = y('LeftLeg'); f.ankleY = y('LeftFoot');
  f.shoulderW = J.LeftArm && J.RightArm ? dist(J.LeftArm, J.RightArm) / H : null; // shoulder joint spacing
  f.hipW = J.LeftUpLeg && J.RightUpLeg ? dist(J.LeftUpLeg, J.RightUpLeg) / H : null; // hip joint spacing
  for (const [k, n] of [['upperArmL', 'LeftArm'], ['foreArmL', 'LeftForeArm'], ['handL', 'LeftHand'], ['thighL', 'LeftUpLeg'], ['shinL', 'LeftLeg'], ['footL', 'LeftFoot'], ['neckL', 'Neck'], ['headL', 'Head'], ['clavL', 'LeftShoulder']])
    f[k] = B[n] ? B[n].length / H : null;
  // thickness (width x depth at mid bone) as a share of height
  for (const [k, n] of [['upperArm', 'LeftArm'], ['foreArm', 'LeftForeArm'], ['thigh', 'LeftUpLeg'], ['shin', 'LeftLeg'], ['neck', 'Neck'], ['waist', 'Spine'], ['chest', 'Spine1'], ['pelvis', 'Hips']]) {
    f[k + 'W'] = B[n] ? mid(B[n], 'w') / H : null;
    f[k + 'D'] = B[n] ? mid(B[n], 'd') / H : null;
  }
  if (hi.flagged) { f.headL = null; f.neckL = null; f.neckW = null; f.neckD = null; }
  f.headW = hi.flagged || hi.width == null ? null : hi.width / H;
  f.headD = hi.flagged || hi.depth == null ? null : hi.depth / H;
  f.chestMaxW = thick(B.Spine1) / H; f.pelvisMaxW = thick(B.Hips) / H;
  // torso silhouette from the whole-body slices (arms are out in T-pose so the waist band is torso only)
  const band = (lo, hi) => m.body.filter((s) => s.y / H >= lo && s.y / H <= hi);
  const w = (ss) => Math.min(...ss.map((s) => s.xMax - s.xMin)) / H;
  f.waistMinW = w(band(0.56, 0.66));
  f.tris = m.tris; f.height = H;
  // triangle budget per body region
  const tb = m.trisPerBone ?? {};
  const sum = (re) => Object.entries(tb).filter(([k]) => re.test(k)).reduce((a, [, v]) => a + v, 0);
  f.trisHead = hi.flagged ? null : sum(/^(Head|Neck|Jaw)$/); f.trisTorso = sum(/^(Hips|Spine|Spine1)$/);
  f.trisArms = sum(/(Shoulder|Arm|ForeArm)$/); f.trisHands = sum(/(Hand|Thumb|Mitten)/);
  f.trisLegs = sum(/(UpLeg|Leg)$/); f.trisFeet = sum(/(Foot|ToeBase)$/);
  f.loopsUpperArm = B.LeftArm?.loops; f.loopsForeArm = B.LeftForeArm?.loops; f.loopsThigh = B.LeftUpLeg?.loops; f.loopsShin = B.LeftLeg?.loops;
  return f;
}

const groups = {};
for (const m of models) (groups[group(m)] ??= []).push({ name: m.name, f: features(m) });
const summary = {};
for (const [g, list] of Object.entries(groups)) {
  const keys = Object.keys(list[0].f);
  const avg = {}, min = {}, max = {};
  for (const k of keys) {
    const vals = list.map((x) => x.f[k]).filter((v) => typeof v === 'number' && isFinite(v));
    if (!vals.length) continue;
    avg[k] = r3(vals.reduce((a, b) => a + b, 0) / vals.length);
    min[k] = r3(Math.min(...vals)); max[k] = r3(Math.max(...vals));
  }
  summary[g] = { count: list.length, members: list.map((x) => x.name), avg, min, max };
}
fs.writeFileSync(path.join(outDir, 'ref-summary.json'), JSON.stringify(summary, null, 1));

// Data the generator reads (src/zombie/lowbody/refBody.json): per group, every joint as a share of stature
// (left side, right side mirrored in), each bone's cross-sections as shares of stature, and the averaged
// front/side silhouette. Numbers only.
const r4 = (x) => Math.round(x * 10000) / 10000;
const gen = {};
for (const g of ['male', 'female']) {
  const list = models.filter((m) => group(m) === g);
  const joints = {}, bones = {};
  const acc = (obj, key, arr) => { (obj[key] ??= []).push(arr); };
  for (const m of list) {
    const H = stature(m);
    for (const [n, p] of Object.entries(m.joints)) {
      const left = n.replace(/^Right/, 'Left');
      const q = n.startsWith('Right') ? [-p[0], p[1], p[2]] : p;
      acc(joints, left, q.map((x) => x / H));
    }
    const flagged = headInfo(m).flagged;
    for (const [n, b] of Object.entries(m.bones)) {
      if (flagged && /^(Head|Neck)$/.test(n)) continue;
      if (b.slices.length !== 6) continue;
      const left = n.replace(/^Right/, 'Left');
      // [fraction along the bone, front, back, out, in]; extents as shares of stature
      acc(bones, left, b.slices.map((s) => [s.t / b.length, s.front / H, s.back / H, s.out / H, s.in / H]));
    }
  }
  const mean = (arrs) => arrs[0].map((_, i) => (Array.isArray(arrs[0][i]) ? mean(arrs.map((a) => a[i])) : r4(arrs.reduce((t, a) => t + a[i], 0) / arrs.length)));
  // silhouette: 40 bins of y/stature, mean half-extents
  const BINS = 40;
  const sil = [];
  for (let k = 0; k < BINS; k++) {
    const y0 = k / BINS, y1 = (k + 1) / BINS;
    const rows = [];
    for (const m of list) {
      const H = stature(m);
      const hit = m.body.filter((s) => s.y / H >= y0 && s.y / H < y1);
      if (hit.length) rows.push([Math.max(...hit.map((s) => s.xMax)) / H, Math.max(...hit.map((s) => -s.xMin)) / H, Math.max(...hit.map((s) => s.zMax)) / H, Math.max(...hit.map((s) => -s.zMin)) / H]);
    }
    const avg = (f) => r4(rows.reduce((t, r) => t + f(r), 0) / rows.length);
    if (rows.length >= list.length / 2) sil.push([r4((y0 + y1) / 2), avg((r) => (r[0] + r[1]) / 2), avg((r) => r[2]), avg((r) => r[3])]);
  }
  // trunk profile on a fixed grid of y/stature (0.35 ... 1.00), averaged; headwear models skip the head part
  const torso = [];
  for (let k = 35; k <= 100; k++) {
    const yy = k / 100;
    const rows = [];
    for (const m of list) {
      const H = stature(m);
      const hi = headInfo(m);
      if (hi.flagged && yy * H > hi.hy) continue;
      const pts = (m.torso ?? []).map((t) => ({ ...t, y: t.y / H }));
      const j = pts.findIndex((t) => t.y >= yy);
      if (j <= 0) continue;
      const a = pts[j - 1], b = pts[j], f = (yy - a.y) / (b.y - a.y);
      const L = (key) => (a[key] + (b[key] - a[key]) * f) / H;
      rows.push([L('front'), L('back'), (L('out') + L('in')) / 2]);
    }
    if (rows.length >= Math.max(2, list.length / 2)) {
      const av = (i) => r4(rows.reduce((t, r) => t + r[i], 0) / rows.length);
      torso.push([yy, av(0), av(1), av(2)]);
    }
  }
  gen[g] = {
    torso, // [y, front, back, half width]
    count: list.length,
    stature: r3(list.reduce((t, m) => t + stature(m), 0) / list.length),
    joints: Object.fromEntries(Object.entries(joints).map(([k, v]) => [k, mean(v)])),
    bones: Object.fromEntries(Object.entries(bones).map(([k, v]) => [k, mean(v)])),
    silhouette: sil, // [y, halfWidth, front, back]
  };
}
const genOut = path.join('src', 'zombie', 'lowbody', 'refBody.json');
fs.mkdirSync(path.dirname(genOut), { recursive: true });
fs.writeFileSync(genOut, JSON.stringify({ note: 'shares of stature, measured by tools/ref (F0); bone slices are [fraction along bone, front, back, out, in]; torso rows are [y, front, back, half width]', ...gen }));

// silhouettes: front (x,y) and side (z,y) outline from the body slices, plus joints as dots
const S = 160; // px per metre
const cell = 2.1 * S;
const cols = 6;
let svg = '';
models.forEach((m, i) => {
  const ox = (i % cols) * cell * 1.5 + 20, oy = Math.floor(i / cols) * (cell + 40) + 20;
  const Y = (y) => oy + cell - y * S;
  const front = m.body.map((s) => `${ox + cell * 0.5 + s.xMax * S},${Y(s.y)}`).concat(m.body.slice().reverse().map((s) => `${ox + cell * 0.5 + s.xMin * S},${Y(s.y)}`));
  const sx = ox + cell * 1.2;
  const side = m.body.map((s) => `${sx + s.zMax * S},${Y(s.y)}`).concat(m.body.slice().reverse().map((s) => `${sx + s.zMin * S},${Y(s.y)}`));
  const col = { male: '#4a7bd0', female: '#d04a8f', child: '#4ab07a' }[group(m)] ?? '#888';
  svg += `<polygon points="${front.join(' ')}" fill="${col}" fill-opacity="0.35" stroke="${col}"/>`;
  svg += `<polygon points="${side.join(' ')}" fill="${col}" fill-opacity="0.35" stroke="${col}"/>`;
  for (const p of Object.values(m.joints)) svg += `<circle cx="${ox + cell * 0.5 + p[0] * S}" cy="${Y(p[1])}" r="2" fill="#111"/>`;
  svg += `<text x="${ox}" y="${oy + cell + 16}" font-size="12" font-family="sans-serif">${m.name} ${m.height} m ${m.tris} tris</text>`;
});
const W = cols * cell * 1.5 + 40, Hh = Math.ceil(models.length / cols) * (cell + 40) + 40;
fs.writeFileSync(path.join(outDir, 'ref-silhouettes.svg'), `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${Hh}" viewBox="0 0 ${W} ${Hh}"><rect width="100%" height="100%" fill="#fff"/>${svg}</svg>`);

const show = (g, keys) => keys.map((k) => `${k}=${summary[g]?.avg[k]}`).join('  ');
for (const g of ['male', 'female']) {
  console.log(`== ${g} (${summary[g].count})`);
  console.log('flagged headwear:', groups[g].filter((x) => x.f.headwear).map((x) => x.name).join(' ') || '-', ' crownShare', r3(crownShare));
  console.log(show(g, ['headW', 'headD', 'tris', 'hipsY', 'chestY', 'neckY', 'headY', 'kneeY', 'ankleY']));
  console.log(show(g, ['shoulderW', 'hipW', 'upperArmL', 'foreArmL', 'handL', 'thighL', 'shinL', 'footL', 'headL']));
  console.log(show(g, ['chestMaxW', 'pelvisMaxW', 'waistMinW', 'waistW', 'waistD', 'chestD', 'upperArmW', 'foreArmW', 'thighW', 'shinW', 'neckW']));
  console.log(show(g, ['trisHead', 'trisTorso', 'trisArms', 'trisHands', 'trisLegs', 'trisFeet', 'loopsUpperArm', 'loopsForeArm', 'loopsThigh', 'loopsShin']));
}
console.log('wrote', path.join(outDir, 'ref-summary.json'), 'and ref-silhouettes.svg');
