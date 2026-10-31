// Triangle builder with per-face (flat) or per-vertex (smooth) colour, skin weights and
// per-material buckets, plus the loft (ring sweep) primitive (docs/02-struktur-mesh.md).
import { BufferGeometry, Color, Float32BufferAttribute, IcosahedronGeometry, Quaternion, Uint16BufferAttribute, Vector3 } from 'three';
import { mergeGeometries, mergeVertices } from 'three/examples/jsm/utils/BufferGeometryUtils.js';
import { hashPos, smoothstep } from './hash';
import { FACE_JITTER, PALETTE, VERTEX_JITTER } from './spec';
import type { Skel } from './skeleton';

export type Weights = Array<[number, number]>; // [boneIndex, weight]
export type Weigher = (p: Vector3) => Weights;

export interface Wound {
  c: Vector3;
  r: number;
}

export interface Paint {
  base: Color;
  /** Optional colour override by position (face centroid in flat mode, vertex in smooth mode). */
  rule?: (p: Vector3) => Color | null;
  wounds?: Wound[];
  woundColor?: Color;
  woundDark?: Color;
  jitter?: number;
}

interface Bucket {
  pos: number[];
  col: number[];
  si: number[];
  sw: number[];
}

export class MeshBuilder {
  private buckets = new Map<string, Bucket>();
  private cur!: Bucket;

  constructor(
    readonly seed: number,
    /** smooth = per-vertex colour, shared normals (realistic); flat = faceted low-poly. */
    readonly smooth = false,
  ) {
    this.use('default');
  }

  /** Switch the material bucket the next triangles go into. */
  use(name: string) {
    let b = this.buckets.get(name);
    if (!b) {
      b = { pos: [], col: [], si: [], sw: [] };
      this.buckets.set(name, b);
    }
    this.cur = b;
    return this;
  }

  get triangles() {
    let n = 0;
    for (const b of this.buckets.values()) n += b.pos.length / 9;
    return n;
  }

  tri(a: Vector3, b: Vector3, c: Vector3, wa: Weights, wb: Weights, wc: Weights, paint: Paint) {
    const cb = this.cur;
    const flatCol = this.smooth ? null : this.shade(new Vector3().add(a).add(b).add(c).multiplyScalar(1 / 3), paint);
    for (const [p, w] of [
      [a, wa],
      [b, wb],
      [c, wc],
    ] as Array<[Vector3, Weights]>) {
      const color = flatCol ?? this.shade(p, paint);
      cb.pos.push(p.x, p.y, p.z);
      cb.col.push(color.r, color.g, color.b);
      for (let i = 0; i < 4; i++) {
        cb.si.push(w[i] ? w[i][0] : 0);
        cb.sw.push(w[i] ? w[i][1] : 0);
      }
    }
  }

  shade(cen: Vector3, paint: Paint): Color {
    const col = (paint.rule?.(cen) ?? paint.base).clone();
    if (paint.wounds) {
      const wc = paint.woundColor ?? PALETTE.wound;
      const wd = paint.woundDark ?? PALETTE.woundDark;
      for (const w of paint.wounds) {
        const n = hashPos(this.seed + 31, cen.x, cen.y, cen.z) - 0.5;
        const d = cen.distanceTo(w.c) + w.r * 0.45 * n;
        const t = 1 - smoothstep(w.r * 0.4, w.r, d);
        if (t > 0) col.lerp(t > 0.8 ? wd : wc, Math.min(1, t * 1.25));
      }
    }
    const j = paint.jitter ?? (this.smooth ? 0 : FACE_JITTER);
    if (j) col.multiplyScalar(1 + (hashPos(this.seed + 7, cen.x, cen.y, cen.z) - 0.5) * 2 * j);
    return col;
  }

  /** One geometry; with several buckets it gets one group per bucket, in `materials` order. */
  geometry(): { geometry: BufferGeometry; materials: string[] } {
    const names = [...this.buckets.keys()].filter((n) => this.buckets.get(n)!.pos.length > 0);
    const geos = names.map((n) => {
      const b = this.buckets.get(n)!;
      let g = new BufferGeometry();
      g.setAttribute('position', new Float32BufferAttribute(b.pos, 3));
      g.setAttribute('color', new Float32BufferAttribute(b.col, 3));
      g.setAttribute('skinIndex', new Uint16BufferAttribute(b.si, 4));
      g.setAttribute('skinWeight', new Float32BufferAttribute(b.sw, 4));
      if (this.smooth) g = mergeVertices(g, 1e-5);
      g.computeVertexNormals();
      return g;
    });
    const geometry = geos.length === 1 ? geos[0] : mergeGeometries(geos, true)!;
    geometry.computeBoundingBox();
    geometry.computeBoundingSphere();
    return { geometry, materials: names };
  }
}

// ---------- skin weights ----------

function distToSegment(p: Vector3, a: Vector3, b: Vector3) {
  const ab = new Vector3().subVectors(b, a);
  const t = Math.min(1, Math.max(0, new Vector3().subVectors(p, a).dot(ab) / Math.max(1e-9, ab.lengthSq())));
  return p.distanceTo(a.clone().addScaledVector(ab, t));
}

/** Inverse-distance weights to the segments of the allowed bones; top 4, normalised. */
export function weigher(skel: Skel, names: string[], power = 4): Weigher {
  const ids = names
    .map((n) => skel.index.get(n))
    .filter((i): i is number => i !== undefined);
  if (!ids.length) throw new Error(`no known bones in ${names.join(',')}`);
  return (p) => {
    const raw = ids.map((i): [number, number] => [i, 1 / (Math.pow(distToSegment(p, skel.seg[i][0], skel.seg[i][1]), power) + 1e-12)]);
    raw.sort((x, y) => y[1] - x[1]);
    let top = raw.slice(0, 4);
    let sum = top.reduce((s, w) => s + w[1], 0);
    top = top.map(([i, w]) => [i, w / sum] as [number, number]).filter(([, w]) => w > 0.02);
    sum = top.reduce((s, w) => s + w[1], 0);
    return top.map(([i, w]) => [i, w / sum] as [number, number]);
  };
}

export const rigid = (skel: Skel, name: string): Weigher => {
  const i = skel.index.get(name)!;
  return () => [[i, 1]];
};

// ---------- loft ----------

export interface Station {
  c: Vector3;
  /** Radius along the side axis. */
  rs: number;
  /** Radius along the front axis. */
  rf: number;
}

export interface LoftOpts {
  sides: number;
  /** Reference "front" direction; must not be parallel to the tube. */
  front: Vector3;
  phase?: number;
  weigh: Weigher;
  paint: Paint;
  capStart?: 'flat' | 'point' | 'none';
  capEnd?: 'flat' | 'point' | 'none';
  tipLen?: number;
  /** Return true to leave the face out (e.g. open shirt front). phi: angle, 0 = side, PI/2 = front. */
  open?: (phi: number, ring: number, c: Vector3) => boolean;
  /** Ragged hem on the last ring: extension amplitude in metres. */
  hem?: number;
  jitter?: number;
  /** Extra radial offset in metres for ring i at angle phi (+ = outwards). */
  shape?: (i: number, phi: number, c: Vector3) => number;
}

export interface LoftResult {
  rings: Vector3[][];
  frames: Array<{ T: Vector3; F: Vector3; S: Vector3 }>;
}

export function loft(mb: MeshBuilder, st: Station[], o: LoftOpts): LoftResult {
  const N = o.sides;
  const phase = o.phase ?? Math.PI / 2;
  const jitter = o.jitter ?? (mb.smooth ? 0 : VERTEX_JITTER);
  const frames = st.map((s, i) => {
    const a = st[Math.max(0, i - 1)].c;
    const b = st[Math.min(st.length - 1, i + 1)].c;
    const T = new Vector3().subVectors(b, a).normalize();
    const F = o.front.clone().addScaledVector(T, -o.front.dot(T)).normalize();
    const S = new Vector3().crossVectors(T, F).normalize();
    return { T, F, S };
  });
  const rings = st.map((s, i) => {
    const { T, F, S } = frames[i];
    const ring: Vector3[] = [];
    for (let k = 0; k < N; k++) {
      const phi = phase + (2 * Math.PI * k) / N;
      const cs = Math.cos(phi);
      const sn = Math.sin(phi);
      const nrm = new Vector3().addScaledVector(S, cs / s.rs).addScaledVector(F, sn / s.rf).normalize();
      const p = s.c.clone().addScaledVector(S, s.rs * cs).addScaledVector(F, s.rf * sn);
      const extra = o.shape?.(i, normAngle(phi), s.c) ?? 0;
      p.addScaledVector(nrm, extra);
      if (jitter) {
        const h = hashPos(mb.seed, p.x, p.y, p.z) - 0.5;
        p.addScaledVector(nrm, h * 2 * jitter * (s.rs + s.rf) * 0.5);
      }
      if (o.hem && i === st.length - 1) {
        const hk = hashPos(mb.seed + 3, p.x, p.y, p.z);
        const drop = k % 2 === 0 ? o.hem * (0.45 + 0.55 * hk) : o.hem * (0.05 + 0.2 * hk);
        p.addScaledVector(T, drop);
      }
      ring.push(p);
    }
    return ring;
  });
  const w = rings.map((r) => r.map((p) => o.weigh(p)));
  for (let i = 0; i < rings.length - 1; i++) {
    const cMid = st[i].c.clone().lerp(st[i + 1].c, 0.5);
    for (let k = 0; k < N; k++) {
      const k2 = (k + 1) % N;
      const phiMid = phase + (2 * Math.PI * (k + 0.5)) / N;
      if (o.open?.(normAngle(phiMid), i, cMid)) continue;
      const a = rings[i][k];
      const b = rings[i][k2];
      const c = rings[i + 1][k2];
      const d = rings[i + 1][k];
      mb.tri(a, b, c, w[i][k], w[i][k2], w[i + 1][k2], o.paint);
      mb.tri(a, c, d, w[i][k], w[i + 1][k2], w[i + 1][k], o.paint);
    }
  }
  const cap = (i: number, kind: 'flat' | 'point' | 'none' | undefined, dir: number) => {
    if (!kind || kind === 'none') return;
    const tip = st[i].c.clone();
    if (kind === 'point') tip.addScaledVector(frames[i].T, dir * (o.tipLen ?? 0.02));
    const wt = o.weigh(tip);
    for (let k = 0; k < N; k++) {
      const k2 = (k + 1) % N;
      if (dir > 0) mb.tri(rings[i][k], tip, rings[i][k2], w[i][k], wt, w[i][k2], o.paint);
      else mb.tri(rings[i][k2], tip, rings[i][k], w[i][k2], wt, w[i][k], o.paint);
    }
  };
  cap(0, o.capStart, -1);
  cap(rings.length - 1, o.capEnd, 1);
  return { rings, frames };
}

export const normAngle = (a: number) => {
  const t = a % (2 * Math.PI);
  return t < 0 ? t + 2 * Math.PI : t;
};

/** Signed angle away from straight ahead (phi = PI/2), in (-PI, PI]. */
export const fromFrontSigned = (phi: number) => {
  const a = normAngle(phi - Math.PI / 2);
  return a > Math.PI ? a - 2 * Math.PI : a;
};

const catmull = (p0: number, p1: number, p2: number, p3: number, t: number) =>
  0.5 * (2 * p1 + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t * t * t);

/** Catmull-Rom resample of key stations: `sub` rings per key segment. */
export function smoothStations(st: Station[], sub: number): Station[] {
  if (sub <= 1 || st.length < 2) return st;
  const out: Station[] = [];
  const n = st.length;
  for (let i = 0; i < n - 1; i++) {
    const s0 = st[Math.max(0, i - 1)];
    const s1 = st[i];
    const s2 = st[i + 1];
    const s3 = st[Math.min(n - 1, i + 2)];
    for (let k = 0; k < sub; k++) {
      const t = k / sub;
      out.push({
        c: new Vector3(catmull(s0.c.x, s1.c.x, s2.c.x, s3.c.x, t), catmull(s0.c.y, s1.c.y, s2.c.y, s3.c.y, t), catmull(s0.c.z, s1.c.z, s2.c.z, s3.c.z, t)),
        rs: Math.max(0.002, catmull(s0.rs, s1.rs, s2.rs, s3.rs, t)),
        rf: Math.max(0.002, catmull(s0.rf, s1.rf, s2.rf, s3.rf, t)),
      });
    }
  }
  out.push({ ...st[n - 1], c: st[n - 1].c.clone() });
  return out;
}

// ---------- small solids ----------

/** Oriented box: centre, half sizes along (ax, ay, az). */
export function box(mb: MeshBuilder, c: Vector3, half: Vector3, weigh: Weigher, paint: Paint, ax = new Vector3(1, 0, 0), ay = new Vector3(0, 1, 0), az = new Vector3(0, 0, 1)) {
  const corner = (sx: number, sy: number, sz: number) =>
    c.clone().addScaledVector(ax, sx * half.x).addScaledVector(ay, sy * half.y).addScaledVector(az, sz * half.z);
  const p = [corner(-1, -1, -1), corner(1, -1, -1), corner(1, 1, -1), corner(-1, 1, -1), corner(-1, -1, 1), corner(1, -1, 1), corner(1, 1, 1), corner(-1, 1, 1)];
  const w = p.map(weigh);
  const faces = [
    [4, 5, 6, 7],
    [1, 0, 3, 2],
    [5, 1, 2, 6],
    [0, 4, 7, 3],
    [7, 6, 2, 3],
    [0, 1, 5, 4],
  ];
  for (const [a, b, cc, d] of faces) {
    mb.tri(p[a], p[b], p[cc], w[a], w[b], w[cc], paint);
    mb.tri(p[a], p[cc], p[d], w[a], w[cc], w[d], paint);
  }
}

/** Four-sided pyramid from base centre along dir. */
export function spike(mb: MeshBuilder, base: Vector3, dir: Vector3, len: number, width: number, depth: number, weigh: Weigher, paint: Paint, up = new Vector3(0, 1, 0)) {
  const d = dir.clone().normalize();
  let u = up.clone().addScaledVector(d, -up.dot(d));
  if (u.lengthSq() < 1e-6) u = new Vector3(1, 0, 0);
  u.normalize();
  const s = new Vector3().crossVectors(d, u).normalize();
  const tip = base.clone().addScaledVector(d, len);
  const q = [
    base.clone().addScaledVector(s, width),
    base.clone().addScaledVector(u, depth),
    base.clone().addScaledVector(s, -width),
    base.clone().addScaledVector(u, -depth),
  ];
  const wt = weigh(tip);
  const wq = q.map(weigh);
  for (let i = 0; i < 4; i++) {
    const j = (i + 1) % 4;
    mb.tri(q[i], q[j], tip, wq[i], wq[j], wt, paint);
  }
  mb.tri(q[0], q[2], q[1], wq[0], wq[2], wq[1], paint);
  mb.tri(q[0], q[3], q[2], wq[0], wq[3], wq[2], paint);
}

export function gem(mb: MeshBuilder, c: Vector3, r: number, weigh: Weigher, paint: Paint, detail = 0) {
  ellipsoid(mb, c, new Vector3(r, r, r), weigh, paint, detail);
}

/** Icosphere scaled to radii r, rotated by q, at c. */
export function ellipsoid(mb: MeshBuilder, c: Vector3, r: Vector3, weigh: Weigher, paint: Paint, detail = 1, q = new Quaternion()) {
  const g = new IcosahedronGeometry(1, detail).toNonIndexed();
  const a = g.getAttribute('position');
  for (let i = 0; i < a.count; i += 3) {
    const v = [0, 1, 2].map((k) => new Vector3(a.getX(i + k) * r.x, a.getY(i + k) * r.y, a.getZ(i + k) * r.z).applyQuaternion(q).add(c));
    mb.tri(v[0], v[1], v[2], weigh(v[0]), weigh(v[1]), weigh(v[2]), paint);
  }
  g.dispose();
}
