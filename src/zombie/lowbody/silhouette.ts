// F5: silhouette score of the generated body against the measured references (refSil.json).
// The trunk is compared with the trunk-bone cross-sections (arms excluded, like the reference measuring
// does) and the legs with the whole-body slices below the arm height. Score = intersection / union of the
// row extents, in front view (half widths) and side view (front and back depth), per reference.
import { Vector3 } from 'three';
import sil from './refSil.json';
import type { LowTopo } from './body';

interface RefSil { name: string; group: 'male' | 'female'; stature: number; headwear: number; rows: number[][]; torso: number[][] }
export const REF_SIL = sil as unknown as RefSil[];

interface Row { y: number; xMin: number; xMax: number; zMin: number; zMax: number }

/** Extents of the cut of the given triangles with the plane y = c (x and z range of the cut segments). */
function cut(pos: Vector3[], tris: number[][], c: number): Row | null {
  let xMin = Infinity, xMax = -Infinity, zMin = Infinity, zMax = -Infinity;
  const add = (p: Vector3) => { xMin = Math.min(xMin, p.x); xMax = Math.max(xMax, p.x); zMin = Math.min(zMin, p.z); zMax = Math.max(zMax, p.z); };
  for (const t of tris) {
    const a = pos[t[0]], b = pos[t[1]], d = pos[t[2]];
    const lo = Math.min(a.y, b.y, d.y), hi = Math.max(a.y, b.y, d.y);
    if (c < lo || c > hi || lo === hi) continue;
    for (const [p, q] of [[a, b], [b, d], [d, a]]) {
      if ((p.y - c) * (q.y - c) <= 0 && p.y !== q.y) add(p.clone().lerp(q, (c - p.y) / (q.y - p.y)));
    }
  }
  return xMin === Infinity ? null : { y: c, xMin, xMax, zMin, zMax };
}

export interface SilScore { front: number; side: number; total: number; legs: [number, number]; trunk: [number, number] }

/** Score one body (rest pose, left of centre arms in T-pose) against one reference silhouette. */
export function scoreAgainst(topo: LowTopo, trunkTris: number[][], legTris: number[][], H: number, ref: RefSil): SilScore {
  const acc = { fi: 0, fu: 0, si: 0, su: 0, lfi: 0, lfu: 0, lsi: 0, lsu: 0, tfi: 0, tfu: 0, tsi: 0, tsu: 0 };
  // legs and feet: whole-body slices below the arm height
  for (const r of ref.rows) {
    if (r[0] > 0.5) continue;
    const m = cut(topo.pos, legTris, r[0] * H);
    if (!m) continue;
    const fw = (a0: number, a1: number, b0: number, b1: number) => [Math.max(0, Math.min(a1, b1) - Math.max(a0, b0)), Math.max(a1, b1) - Math.min(a0, b0)];
    const [fi, fu] = fw(m.xMin / H, m.xMax / H, r[1], r[2]);
    const [si, su] = fw(m.zMin / H, m.zMax / H, r[3], r[4]);
    acc.lfi += fi; acc.lfu += fu; acc.lsi += si; acc.lsu += su;
  }
  // trunk and head: trunk-bone cross-sections, front/back from z = 0 and half width from x = 0
  for (const r of ref.torso) {
    if (r[0] < 0.5) continue; // below this the legs take over
    const m = cut(topo.pos, trunkTris, r[0] * H);
    if (!m) continue;
    const half = Math.max(Math.abs(m.xMin), Math.abs(m.xMax)) / H;
    acc.tfi += Math.min(half, r[3]); acc.tfu += Math.max(half, r[3]);
    const f = m.zMax / H, b = -m.zMin / H;
    acc.tsi += Math.max(0, Math.min(f, r[1]) + Math.min(b, r[2]));
    acc.tsu += Math.max(f, r[1]) + Math.max(b, r[2]);
  }
  const front = (acc.lfi + acc.tfi) / (acc.lfu + acc.tfu);
  const side = (acc.lsi + acc.tsi) / (acc.lsu + acc.tsu);
  return { front, side, total: (front + side) / 2, legs: [acc.lfi / acc.lfu, acc.lsi / acc.lsu], trunk: [acc.tfi / acc.tfu, acc.tsi / acc.tsu] };
}

/** Split the body triangles into trunk (spine chain, neck, head and helper bones that sit on them) and legs. */
export function splitTris(topo: LowTopo, boneNames: string[]) {
  // the references' trunk bone also carries the shoulder caps, so the shoulder bone and the shoulder helper count as trunk
  const trunkRe = /^(Hips|Spine|Spine1|Spine2|Neck|Head|(Left|Right)(Shoulder|ArmHelper))$/, legRe = /(UpLeg|Leg|Foot|ToeBase|HipHelper|KneeHelper)$/;
  const dom = (t: number[]) => {
    const acc = new Map<string, number>();
    for (const v of t) for (const [b, w] of topo.weights[v]) acc.set(boneNames[b], (acc.get(boneNames[b]) ?? 0) + w);
    return [...acc].sort((a, b) => b[1] - a[1])[0][0];
  };
  const trunk: number[][] = [], legs: number[][] = [];
  for (const t of topo.tris) {
    const d = dom(t);
    if (trunkRe.test(d)) trunk.push(t);
    if (legRe.test(d)) legs.push(t);
  }
  return { trunk, legs };
}

/** Mean scores of a body over the references of its group. */
export function scoreBody(topo: LowTopo, boneNames: string[], H: number, group: 'male' | 'female', only?: string) {
  const { trunk, legs } = splitTris(topo, boneNames);
  const refs = REF_SIL.filter((r) => r.group === group && (!only || r.name === only));
  const per = refs.map((r) => ({ name: r.name, ...scoreAgainst(topo, trunk, legs, H, r) }));
  const mean = (k: 'front' | 'side' | 'total') => per.reduce((s, x) => s + x[k], 0) / per.length;
  return { group, front: mean('front'), side: mean('side'), total: mean('total'), per };
}

/** Debug: our trunk extents next to a reference's at each of its torso rows: [y/H, ours half, ref half, ours front, ref front, ours back, ref back]. */
export function trunkCurves(topo: LowTopo, boneNames: string[], H: number, name: string) {
  const ref = REF_SIL.find((r) => r.name === name)!;
  const { trunk } = splitTris(topo, boneNames);
  return ref.torso.map((r) => {
    const m = cut(topo.pos, trunk, r[0] * H);
    if (!m) return [r[0], null];
    return [r[0], Math.max(Math.abs(m.xMin), Math.abs(m.xMax)) / H, r[3], m.zMax / H, r[1], -m.zMin / H, r[2]].map((v) => (v === null ? v : Math.round((v as number) * 1000) / 1000));
  });
}
