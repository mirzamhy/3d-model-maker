// F0: measure low-poly reference characters (FBX) and write numbers only, never the mesh.
// For every body mesh it records: height, joint positions (canonical Mixamo names), triangles per bone,
// edge loops and cross-section profile along each bone, and a whole-body height profile (for silhouettes).
// Usage: node tools/ref/measure-fbx.mjs <out.json> <file.fbx> [more.fbx ...]
import fs from 'node:fs';
import path from 'node:path';

// FBXLoader touches a few browser globals while parsing; the mesh data does not need them.
globalThis.self = globalThis;
globalThis.window = globalThis;
globalThis.document = { createElementNS: () => ({ style: {}, addEventListener() {}, getContext: () => null }) };
const THREE = await import('three');
const { FBXLoader } = await import('three/examples/jsm/loaders/FBXLoader.js');
const { Vector3, Matrix4 } = THREE;

const MIN_TRIS = 600; // smaller meshes are accessories (hair, glasses), recorded only by name and size
const SLICES = 6; // cross-sections per bone
const BODY_SLICES = 40; // whole-body height profile

// source bone name -> canonical name. Covers 3ds Max Biped (bip_*) and the Blender rig in the head pack.
function canon(raw) {
  const n = raw.replace(/^mixamorig:?/, '').replace(/\d{3}$/, '');
  const biped = {
    bip_Pelvis: 'Hips', bip_Spine: 'Spine', bip_Spine1: 'Spine1', bip_Neck: 'Neck', bip_Head: 'Head', bip_jaw: 'Jaw',
    Clavicle: 'Shoulder', UpperArm: 'Arm', Forearm: 'ForeArm', Hand: 'Hand',
    Finger0: 'Thumb1', Finger01: 'Thumb2', Finger1: 'Mitten1', Finger11: 'Mitten2',
    Thigh: 'UpLeg', Calf: 'Leg', Foot: 'Foot', Toe0: 'ToeBase',
  };
  if (biped[n]) return biped[n];
  let m = n.match(/^bip_([LR])_(\w+)$/);
  if (m && biped[m[2]]) return (m[1] === 'L' ? 'Left' : 'Right') + biped[m[2]];
  const blender = {
    Pelvis: 'Hips', Spine: 'Spine', Chest: 'Spine1', Neck: 'Neck', Head: 'Head',
    Arm: 'Shoulder', UpArm: 'Arm', LowArm: 'ForeArm', Palm: 'Hand', UpLeg: 'UpLeg', LowLeg: 'Leg', Foot: 'Foot', Toe: 'ToeBase',
  };
  if (blender[n]) return blender[n];
  m = n.match(/^(UpLeg|LowLeg|Foot|Toe|Arm|UpArm|LowArm|Palm)([LR])$/);
  if (m) return (m[2] === 'L' ? 'Left' : 'Right') + blender[m[1]];
  return null; // nubs, IK helpers, finger tips
}

// child joint that ends each bone (for the bone axis); hands, feet tips use the mesh extent instead
const CHILD = {
  Hips: 'Spine', Spine: 'Spine1', Spine1: 'Neck', Neck: 'Head',
  Shoulder: 'Arm', Arm: 'ForeArm', ForeArm: 'Hand', UpLeg: 'Leg', Leg: 'Foot', Foot: 'ToeBase',
};
const childOf = (b) => {
  const side = b.match(/^(Left|Right)/)?.[1] ?? '';
  const c = CHILD[b.slice(side.length)];
  return c ? (['Spine', 'Spine1', 'Neck', 'Head'].includes(c) ? c : side + c) : null;
};

const r3 = (x) => Math.round(x * 1000) / 1000;
const v3 = (v) => [r3(v.x), r3(v.y), r3(v.z)];

function measureMesh(mesh) {
  const g = mesh.geometry;
  const pos = g.attributes.position;
  const idx = g.index ? g.index.array : [...Array(pos.count).keys()];
  const tris = idx.length / 3;
  const P = [];
  for (let i = 0; i < pos.count; i++) P.push(new Vector3().fromBufferAttribute(pos, i).applyMatrix4(mesh.bindMatrix ?? mesh.matrixWorld));

  // joints in the same bind space: inverse of each bone inverse matrix
  const joints = {};
  const boneCanon = [];
  let nameOf = () => null;
  if (mesh.isSkinnedMesh) {
    // name pass, then fingers by hierarchy: duplicated characters get renamed fingers (Finger012...),
    // so under each hand the first chain (Max numbering) is the thumb, the second the mitten
    const names = new Map(mesh.skeleton.bones.map((b) => [b, canon(b.name)]));
    for (const b of mesh.skeleton.bones) {
      const pn = b.parent?.isBone ? names.get(b.parent) : null;
      if (pn === 'Spine' && /spine/i.test(b.name)) names.set(b, 'Spine1');
      if (pn && pn.endsWith('Foot') && /toe/i.test(b.name) && !/nub/i.test(b.name)) names.set(b, pn.replace('Foot', 'ToeBase'));
    }
    for (const b of mesh.skeleton.bones) {
      const h = names.get(b);
      if (!h || !h.endsWith('Hand')) continue;
      const side = h.replace('Hand', '');
      const kids = b.children.filter((c) => c.isBone).sort((a, c) => a.name.localeCompare(c.name));
      kids.slice(0, 2).forEach((k, ci) => {
        const base = ci === 0 ? 'Thumb' : 'Mitten';
        names.set(k, side + base + '1');
        const k2 = k.children.find((c) => c.isBone && !/nub/i.test(c.name));
        if (k2) names.set(k2, side + base + '2');
      });
    }
    nameOf = (b) => names.get(b) ?? null;
    mesh.skeleton.bones.forEach((b, i) => {
      const c = names.get(b);
      boneCanon[i] = c;
      if (c) joints[c] = new Vector3().setFromMatrixPosition(new Matrix4().copy(mesh.skeleton.boneInverses[i]).invert());
    });
  }

  // units and frame: scale to metres from the height, feet on y = 0, centred on the hips (or the bbox)
  const box = new THREE.Box3().setFromPoints(P);
  const size = box.getSize(new Vector3());
  const up = size.y >= size.z ? 'y' : 'z';
  if (up === 'z') { // Z-up file: rotate to Y-up
    const rot = new Matrix4().makeRotationX(-Math.PI / 2);
    P.forEach((p) => p.applyMatrix4(rot));
    Object.values(joints).forEach((p) => p.applyMatrix4(rot));
    box.setFromPoints(P); box.getSize(size);
  }
  // centimetres vs metres; odd export scales (e.g. 6.8 "m" tall) are normalised to a 1.75 m person
  let unit = size.y > 20 ? 0.01 : 1;
  const scaled = size.y * unit > 2.5 || size.y * unit < 0.5;
  if (scaled) unit = 1.75 / size.y;
  const origin = joints.Hips ? new Vector3(joints.Hips.x, box.min.y, joints.Hips.z) : new Vector3((box.min.x + box.max.x) / 2, box.min.y, (box.min.z + box.max.z) / 2);
  const norm = (p) => p.sub(origin).multiplyScalar(unit);
  P.forEach(norm);
  Object.values(joints).forEach(norm);

  // facing: toes in front of the ankles means +z; flip to +z if needed. Character left must be +x.
  let facing = '+z';
  const lf = joints.LeftFoot, lt = joints.LeftToeBase;
  if (lf && lt && lt.z < lf.z) {
    facing = '-z';
    const flip = (p) => { p.x = -p.x; p.z = -p.z; };
    P.forEach(flip); Object.values(joints).forEach(flip);
  }
  let leftIsPlusX = joints.LeftArm ? joints.LeftArm.x > 0 : null;

  // dominant bone per vertex
  const dom = new Array(pos.count).fill(null);
  if (mesh.isSkinnedMesh) {
    const si = g.attributes.skinIndex, sw = g.attributes.skinWeight;
    for (let i = 0; i < pos.count; i++) {
      let best = -1, bw = 0;
      for (let k = 0; k < 4; k++) { const w = sw.getComponent(i, k); if (w > bw) { bw = w; best = si.getComponent(i, k); } }
      // weights on nubs / helpers fall back to the nearest named parent
      let b = mesh.skeleton.bones[best];
      while (b && !nameOf(b)) b = b.parent?.isBone ? b.parent : null;
      dom[i] = b ? nameOf(b) : null;
    }
  }

  // unique vertex positions (FBX splits per face corner) for loop counting
  const key = (p) => `${Math.round(p.x * 2000)},${Math.round(p.y * 2000)},${Math.round(p.z * 2000)}`;

  const bones = {};
  const triCount = {};
  const triBone = new Array(tris);
  for (let t = 0; t < tris; t++) {
    const votes = {};
    for (let k = 0; k < 3; k++) { const d = dom[idx[t * 3 + k]] ?? 'none'; votes[d] = (votes[d] ?? 0) + 1; }
    const win = Object.entries(votes).sort((a, b) => b[1] - a[1])[0][0];
    triBone[t] = win;
    triCount[win] = (triCount[win] ?? 0) + 1;
  }

  // plane cut: triangles in `list` against the plane (p - o)·axis = t; extents in the u (front) and w (out)
  // directions, plus the cut length (perimeter). Uses the cut piece nearest to the axis only.
  function section(list, o, axis, u, w, t) {
    const segs = [];
    for (const tr of list) {
      const q = [0, 1, 2].map((k) => P[idx[tr * 3 + k]]);
      const d = q.map((p) => p.clone().sub(o).dot(axis) - t);
      const pts = [];
      for (let k = 0; k < 3; k++) {
        const a = k, b = (k + 1) % 3;
        if ((d[a] < 0) !== (d[b] < 0)) pts.push(q[a].clone().lerp(q[b], d[a] / (d[a] - d[b])));
      }
      if (pts.length === 2) segs.push(pts);
    }
    if (!segs.length) return null;
    let uMin = Infinity, uMax = -Infinity, wMin = Infinity, wMax = -Infinity, perim = 0;
    for (const [a, b] of segs) {
      perim += a.distanceTo(b);
      for (const p of [a, b]) {
        const r = p.clone().sub(o);
        const du = r.dot(u), dw = r.dot(w);
        uMin = Math.min(uMin, du); uMax = Math.max(uMax, du); wMin = Math.min(wMin, dw); wMax = Math.max(wMax, dw);
      }
    }
    return { front: r3(uMax), back: r3(-uMin), out: r3(wMax), in: r3(-wMin), perim: r3(perim), segs: segs.length };
  }

  for (const [name, J] of Object.entries(joints)) {
    const ids = []; const seen = new Set();
    for (let i = 0; i < P.length; i++) if (dom[i] === name) { const k = key(P[i]); if (!seen.has(k)) { seen.add(k); ids.push(i); } }
    if (!ids.length) continue;
    const c = childOf(name);
    let axis, len;
    if (c && joints[c]) { axis = joints[c].clone().sub(J); len = axis.length(); axis.normalize(); }
    else { // end bones: axis to the farthest vertex
      let far = J, fd = 0; for (const i of ids) { const d = P[i].distanceTo(J); if (d > fd) { fd = d; far = P[i]; } }
      axis = far.clone().sub(J); len = axis.length(); axis.normalize();
    }
    // cross-section frame: u = depth (towards the front where possible), w = width
    let front = new Vector3(0, 0, 1);
    if (Math.abs(axis.z) > 0.8) front = new Vector3(0, 1, 0); // feet point forward
    const u = front.clone().sub(axis.clone().multiplyScalar(front.dot(axis))).normalize();
    const w = new Vector3().crossVectors(axis, u).normalize();
    const ts = ids.map((i) => P[i].clone().sub(J).dot(axis));
    const tMin = Math.min(...ts), tMax = Math.max(...ts);
    // cross-sections: cut this bone's triangles with planes across the axis (low-poly vertices sit only on
    // the loops, so sampling vertices leaves gaps; the cut follows the surface between loops)
    const myTris = [];
    for (let t = 0; t < tris; t++) if (triBone[t] === name) myTris.push(t);
    const slices = [];
    for (let s = 0; s < SLICES; s++) {
      const tc = tMin + ((tMax - tMin) * (s + 0.5)) / SLICES;
      const sec = section(myTris, J, axis, u, w, tc);
      if (sec) slices.push({ t: r3(tc), ...sec });
    }
    // edge loops: vertex rings along the axis, merged when closer than 1.2 cm or 4 % of the bone
    const sorted = [...ts].sort((a, b) => a - b);
    const gap = Math.max(0.012, 0.04 * len);
    let loops = 0, last = -Infinity;
    for (const t of sorted) { if (t - last > gap) loops++; last = t; }
    bones[name] = {
      head: v3(J), length: r3(len), axis: v3(axis), verts: ids.length, tris: triCount[name] ?? 0,
      span: [r3(tMin), r3(tMax)], loops, slices,
    };
  }

  // whole-body height profile: half width and depth per horizontal slice
  const H = size.y * unit;
  const body = [];
  const allTris = [...Array(tris).keys()];
  const Y = new Vector3(0, 1, 0), Z = new Vector3(0, 0, 1), X = new Vector3(1, 0, 0);

  // torso + neck + head profile: horizontal cuts through the trunk triangles only (no arm or leg bones),
  // every 1 % of the height from 35 % up to the top. Extents are from the body centre line (x = 0, z = 0).
  const TRUNK = /^(Hips|Spine|Spine1|Neck|Head|Jaw|LeftShoulder|RightShoulder)$/;
  const trunkTris = allTris.filter((t) => TRUNK.test(triBone[t]));
  const torso = [];
  if (trunkTris.length) {
    for (let k = 35; k <= 100; k++) {
      const y = (H * k) / 100;
      const sec = section(trunkTris, new Vector3(), Y, Z, X, y);
      if (sec) torso.push({ y: r3(y), front: sec.front, back: sec.back, out: sec.out, in: sec.in });
    }
  }
  for (let s = 0; s < BODY_SLICES; s++) {
    const y = (H * (s + 0.5)) / BODY_SLICES;
    const sec = section(allTris, new Vector3(), Y, Z, X, y);
    if (sec) body.push({ y: r3(y), xMin: r3(-sec.in), xMax: r3(sec.out), zMin: r3(-sec.back), zMax: r3(sec.front) });
  }

  // T-pose or A-pose: angle of the upper arm below horizontal
  let armAngle = null;
  if (joints.LeftArm && joints.LeftForeArm) {
    const d = joints.LeftForeArm.clone().sub(joints.LeftArm);
    armAngle = r3((Math.atan2(-d.y, Math.abs(d.x)) * 180) / Math.PI);
  }

  return {
    name: mesh.name, skinned: !!mesh.isSkinnedMesh, tris, uniqueVerts: new Set(P.map(key)).size,
    height: r3(H), heightScaled: scaled, width: r3(size.x * unit), depth: r3(size.z * unit), upAxis: up, facing, leftIsPlusX, armAngle,
    maxInfluences: mesh.isSkinnedMesh ? 4 : 0,
    joints: Object.fromEntries(Object.entries(joints).map(([k, p]) => [k, v3(p)])),
    trisPerBone: triCount, bones, body, torso,
  };
}

const [out, ...files] = process.argv.slice(2);
if (!out || !files.length) { console.error('usage: node tools/ref/measure-fbx.mjs <out.json> <file.fbx> ...'); process.exit(1); }
const result = { generated: new Date().toISOString(), note: 'numbers measured from reference FBX files; no mesh data', models: [] };
const warn = console.warn; console.warn = () => {};
for (const f of files) {
  const buf = fs.readFileSync(f);
  const root = new FBXLoader().parse(buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength), '');
  root.updateMatrixWorld(true);
  const accessories = [];
  root.traverse((o) => {
    if (!o.isMesh) return;
    const tris = (o.geometry.index ? o.geometry.index.count : o.geometry.attributes.position.count) / 3;
    if (tris < MIN_TRIS) { accessories.push({ name: o.name, tris, bones: o.isSkinnedMesh ? o.skeleton.bones.length : 0 }); return; }
    const m = measureMesh(o);
    m.file = path.basename(f);
    result.models.push(m);
    console.log(`${m.file} :: ${m.name}  h=${m.height} w=${m.width} d=${m.depth} tris=${m.tris} up=${m.upAxis} face=${m.facing} L+x=${m.leftIsPlusX} arm=${m.armAngle} bones=${Object.keys(m.bones).length}`);
  });
  if (accessories.length) result.models.filter((m) => m.file === path.basename(f)).forEach((m) => (m.accessoriesInFile = accessories));
}
console.warn = warn;
fs.mkdirSync(path.dirname(out), { recursive: true });
fs.writeFileSync(out, JSON.stringify(result, null, 1));
console.log('wrote', out, result.models.length, 'models');
