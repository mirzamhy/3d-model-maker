// F3: automated deformation tests for the low-poly base body.
// For every pose in POSE_TESTS the mesh is skinned on the CPU (same maths as the GPU) and checked for:
//  - folds: triangles that cut through triangles of the same or a neighbouring bone (the skin creases into itself);
//  - contacts: triangles that cut through a distant body part (e.g. the arm into the hip; a pose problem, not a skin one);
//  - flipped triangles: the skinned normal points against the rest normal turned by its main bone, or the
//    triangle collapsed to under 15 % of its area;
//  - volume: closed-mesh volume against the rest pose (target 0.97..1.03);
//  - joint rings: cross-section area of the shoulder/elbow/wrist/hip/knee/ankle loops against rest (target >= 0.85).
import { Matrix3, Matrix4, Vector3, type Bone } from 'three';
import type { Rig } from '../build';
import { POSE_TESTS, resetPose } from '../pose';
import type { LowTopo } from './body';
import { driveHelpers } from './helpers';

const EPS = 1e-9;

/** Segment p-q against triangle a-b-c (Moller-Trumbore), strictly inside both. */
function segHitsTri(p: Vector3, q: Vector3, a: Vector3, b: Vector3, c: Vector3) {
  const dx = q.x - p.x, dy = q.y - p.y, dz = q.z - p.z;
  const e1x = b.x - a.x, e1y = b.y - a.y, e1z = b.z - a.z;
  const e2x = c.x - a.x, e2y = c.y - a.y, e2z = c.z - a.z;
  const hx = dy * e2z - dz * e2y, hy = dz * e2x - dx * e2z, hz = dx * e2y - dy * e2x;
  const det = e1x * hx + e1y * hy + e1z * hz;
  if (Math.abs(det) < EPS) return false;
  const inv = 1 / det;
  const sx = p.x - a.x, sy = p.y - a.y, sz = p.z - a.z;
  const u = inv * (sx * hx + sy * hy + sz * hz);
  if (u <= 1e-6 || u >= 1 - 1e-6) return false;
  const qx = sy * e1z - sz * e1y, qy = sz * e1x - sx * e1z, qz = sx * e1y - sy * e1x;
  const v = inv * (dx * qx + dy * qy + dz * qz);
  if (v <= 1e-6 || u + v >= 1 - 1e-6) return false;
  const t = inv * (e2x * qx + e2y * qy + e2z * qz);
  return t > 1e-6 && t < 1 - 1e-6;
}

function trisIntersect(P: Vector3[], A: number[], B: number[]) {
  const [a0, a1, a2] = A.map((i) => P[i]), [b0, b1, b2] = B.map((i) => P[i]);
  return (
    segHitsTri(a0, a1, b0, b1, b2) || segHitsTri(a1, a2, b0, b1, b2) || segHitsTri(a2, a0, b0, b1, b2) ||
    segHitsTri(b0, b1, a0, a1, a2) || segHitsTri(b1, b2, a0, a1, a2) || segHitsTri(b2, b0, a0, a1, a2)
  );
}

const volume = (P: Vector3[], tris: number[][]) => tris.reduce((v, [a, b, c]) => v + P[a].dot(new Vector3().crossVectors(P[b], P[c])), 0) / 6;

/** Area of a (roughly planar) vertex loop: length of its vector area. */
function loopArea(P: Vector3[], ids: number[]) {
  const c = ids.reduce((acc, i) => acc.add(P[i]), new Vector3()).multiplyScalar(1 / ids.length);
  const s = new Vector3();
  for (let k = 0; k < ids.length; k++) {
    const a = P[ids[k]].clone().sub(c), b = P[ids[(k + 1) % ids.length]].clone().sub(c);
    s.add(a.cross(b));
  }
  return s.length() / 2;
}

/** Skinned vertex positions in mesh space for the rig's current pose. */
export function skinPositions(rig: Rig, topo: LowTopo): Vector3[] {
  rig.root.updateMatrixWorld(true);
  const mesh = rig.mesh;
  mesh.skeleton.update();
  const bm = mesh.skeleton.boneMatrices;
  const mats = mesh.skeleton.bones.map((_, i) => new Matrix4().fromArray(bm, i * 16));
  const tmp = new Vector3();
  return topo.pos.map((p, vi) => {
    const sv = p.clone().applyMatrix4(mesh.bindMatrix);
    const out = new Vector3();
    for (const [bi, w] of topo.weights[vi]) out.addScaledVector(tmp.copy(sv).applyMatrix4(mats[bi]), w);
    return out.applyMatrix4(mesh.bindMatrixInverse);
  });
}

export interface PoseResult {
  pose: string;
  folds: number;
  contacts: number;
  flipped: number;
  volume: number;
  rings: Record<string, number>;
  /** worst offenders: "boneA|boneB": count */
  where: Record<string, number>;
  /** sharp new creases: shared edges bent past 100 degrees that were under 50 degrees at rest */
  creases: number;
  creaseWhere: Record<string, number>;
  /** flipped triangles per main bone */
  flipWhere: Record<string, number>;
  /** with detail: the intersecting triangle pairs (rest-pose centroids, bones) */
  pairs?: Array<{ a: number; b: number; ca: number[]; cb: number[]; bones: string }>;
  /** with detail: crease edges (vertex ids, rest positions, bent angle) */
  creaseEdges?: Array<{ v: number[]; p: number[][]; deg: number }>;
}

export function runPoseTests(rig: Rig, only?: string[], detail = false): PoseResult[] {
  const topo = rig.mesh.geometry.userData.lowTopo as LowTopo | undefined;
  if (!topo) throw new Error('not a low-poly body (style lowbody)');
  const bones = rig.mesh.skeleton.bones;
  const nameOf = (i: number) => bones[i].name;
  // bone graph distance, for telling folds (near bones) from contacts (far bones)
  const parent = bones.map((b) => bones.indexOf(b.parent as Bone));
  const chain = (i: number) => { const c: number[] = []; for (let k = i; k >= 0; k = parent[k]) c.push(k); return c; };
  const dist = (a: number, b: number) => {
    const ca = chain(a), cb = chain(b);
    for (let i = 0; i < ca.length; i++) { const j = cb.indexOf(ca[i]); if (j >= 0) return i + j; }
    return 99;
  };
  const dominant = topo.tris.map((t) => {
    const acc = new Map<number, number>();
    for (const v of t) for (const [b, w] of topo.weights[v]) acc.set(b, (acc.get(b) ?? 0) + w);
    return [...acc].sort((x, y) => y[1] - x[1])[0][0];
  });
  const restN = topo.tris.map(([a, b, c]) => new Vector3().subVectors(topo.pos[b], topo.pos[a]).cross(new Vector3().subVectors(topo.pos[c], topo.pos[a])));
  const restVol = volume(topo.pos, topo.tris);
  // shared edges with their two triangles, for the crease test
  const edgeTris = new Map<string, number[]>();
  topo.tris.forEach((t, i) => { for (let k = 0; k < 3; k++) { const a = t[k], b = t[(k + 1) % 3]; const key = a < b ? `${a}_${b}` : `${b}_${a}`; (edgeTris.get(key) ?? edgeTris.set(key, []).get(key)!).push(i); } });
  const edges = [...edgeTris.values()].filter((p) => p.length === 2);
  const angle = (n1: Vector3, n2: Vector3) => Math.acos(Math.max(-1, Math.min(1, n1.dot(n2) / (n1.length() * n2.length() || 1)))) * 180 / Math.PI;
  const restAngle = edges.map(([i, j]) => angle(restN[i], restN[j]));
  const restRing: Record<string, number> = {};
  for (const [k, ids] of Object.entries(topo.rings)) restRing[k] = loopArea(topo.pos, ids);

  const results: PoseResult[] = [];
  for (const pc of POSE_TESTS) {
    if (only && !only.includes(pc.name)) continue;
    resetPose(rig);
    pc.set(rig);
    driveHelpers(rig);
    const P = skinPositions(rig, topo);
    const bm = rig.mesh.skeleton.boneMatrices;
    // flipped / collapsed
    let flipped = 0;
    const flipWhere: Record<string, number> = {};
    const m3 = new Matrix3();
    topo.tris.forEach(([a, b, c], i) => {
      const n = new Vector3().subVectors(P[b], P[a]).cross(new Vector3().subVectors(P[c], P[a]));
      m3.setFromMatrix4(new Matrix4().fromArray(bm, dominant[i] * 16));
      const ref = restN[i].clone().applyMatrix3(m3);
      if (n.dot(ref) < 0 || n.length() < 0.15 * restN[i].length()) {
        flipped++;
        flipWhere[nameOf(dominant[i])] = (flipWhere[nameOf(dominant[i])] ?? 0) + 1;
      }
    });
    // intersections: sweep over x on triangle boxes
    const box = topo.tris.map((t) => {
      const xs = t.map((v) => P[v]);
      return {
        lo: new Vector3(Math.min(xs[0].x, xs[1].x, xs[2].x), Math.min(xs[0].y, xs[1].y, xs[2].y), Math.min(xs[0].z, xs[1].z, xs[2].z)),
        hi: new Vector3(Math.max(xs[0].x, xs[1].x, xs[2].x), Math.max(xs[0].y, xs[1].y, xs[2].y), Math.max(xs[0].z, xs[1].z, xs[2].z)),
      };
    });
    const order = topo.tris.map((_, i) => i).sort((p, q) => box[p].lo.x - box[q].lo.x);
    let folds = 0, contacts = 0;
    const where: Record<string, number> = {};
    const pairs: NonNullable<PoseResult['pairs']> = [];
    const cen = (t: number[]) => t.map((v) => topo.pos[v]).reduce((a, p) => a.add(p), new Vector3()).multiplyScalar(1 / 3).toArray().map((x) => +x.toFixed(3));
    for (let oi = 0; oi < order.length; oi++) {
      const i = order[oi];
      for (let oj = oi + 1; oj < order.length; oj++) {
        const j = order[oj];
        if (box[j].lo.x > box[i].hi.x) break;
        if (box[j].lo.y > box[i].hi.y || box[j].hi.y < box[i].lo.y || box[j].lo.z > box[i].hi.z || box[j].hi.z < box[i].lo.z) continue;
        const A = topo.tris[i], B = topo.tris[j];
        if (A.some((v) => B.includes(v))) continue; // neighbours share an edge or a corner
        if (!trisIntersect(P, A, B)) continue;
        const da = dominant[i], db = dominant[j];
        if (dist(da, db) <= 2) folds++;
        else contacts++;
        const key = [nameOf(da), nameOf(db)].sort().join('|');
        where[key] = (where[key] ?? 0) + 1;
        if (detail && pairs.length < 60) pairs.push({ a: i, b: j, ca: cen(A), cb: cen(B), bones: key });
      }
    }
    const nowN = topo.tris.map(([a, b, c]) => new Vector3().subVectors(P[b], P[a]).cross(new Vector3().subVectors(P[c], P[a])));
    let creases = 0;
    const creaseWhere: Record<string, number> = {};
    const creaseEdges: NonNullable<PoseResult['creaseEdges']> = [];
    edges.forEach(([i, j], e) => {
      const deg = angle(nowN[i], nowN[j]);
      if (restAngle[e] < 50 && deg > 100) {
        creases++;
        const shared = topo.tris[i].filter((v) => topo.tris[j].includes(v));
        if (detail) creaseEdges.push({ v: shared, p: shared.map((v) => topo.pos[v].toArray().map((x) => +x.toFixed(3))), deg: Math.round(deg) });
        const key = [nameOf(dominant[i]), nameOf(dominant[j])].sort().join('|');
        creaseWhere[key] = (creaseWhere[key] ?? 0) + 1;
      }
    });
    const rings: Record<string, number> = {};
    for (const [k, ids] of Object.entries(topo.rings)) rings[k] = +(loopArea(P, ids) / restRing[k]).toFixed(3);
    const top = Object.fromEntries(Object.entries(where).sort((a, b) => b[1] - a[1]).slice(0, 6));
    results.push({ pose: pc.name, folds, contacts, flipped, volume: +(volume(P, topo.tris) / restVol).toFixed(3), rings, where: top, flipWhere, creases, creaseWhere, ...(detail ? { creaseEdges } : {}), ...(detail ? { pairs } : {}) });
  }
  resetPose(rig);
  return results;
}

/** One line per pose, for quick reading. */
export function summarise(results: PoseResult[]) {
  return results.map((r) => {
    const worst = Object.entries(r.rings).sort((a, b) => a[1] - b[1])[0];
    return `${r.pose.padEnd(13)} folds ${String(r.folds).padStart(3)}  contacts ${String(r.contacts).padStart(3)}  flipped ${String(r.flipped).padStart(3)}  creases ${String(r.creases).padStart(3)}  vol ${r.volume.toFixed(3)}  minRing ${worst[0]} ${worst[1]}  ${Object.entries(r.where).slice(0, 3).map(([k, v]) => `${k}:${v}`).join(' ')}`;
  }).join('\n');
}
