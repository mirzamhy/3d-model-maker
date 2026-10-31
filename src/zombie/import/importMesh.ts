// Bridge for meshes made elsewhere (AI image-to-3D such as Modly / Hunyuan3D / Tripo / Meshy).
// A static T-pose GLB is loaded, merged, fitted to the skeleton's size and bound to the
// 66-bone Mixamo skeleton with automatic skin weights, so it can use every pose of this project.
import { BufferAttribute, BufferGeometry, Float32BufferAttribute, Material, Mesh, Matrix4, Uint16BufferAttribute, Uint32BufferAttribute, Vector3 } from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { MeshoptDecoder } from 'three/examples/jsm/libs/meshopt_decoder.module.js';
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js';
import { buildSkeleton, type Skel } from '../skeleton';
import { REAL_BONE_DEFS } from '../skeletonReal';

export interface ImportOpts {
  /** Target height in metres (feet to top of head). The skeleton is 1.82 m. */
  height: number;
  /** Extra offsets in metres after fitting. */
  dx: number;
  dy: number;
  dz: number;
  /** Rotation about Y in degrees, to make the model face +Z. */
  rotY: number;
  /** Rotation about X in degrees (use -90 for Z-up exports). */
  rotX: number;
}

export const DEFAULT_OPTS: ImportOpts = { height: 1.82, dx: 0, dy: 0, dz: 0, rotY: 0, rotX: 0 };

interface Source {
  name: string;
  geometry: BufferGeometry;
  materials: Material[];
}

export interface ImportReport {
  name: string;
  triangles: number;
  uniqueVertices: number;
  materials: number;
  smoothed: boolean;
  ms: number;
}

let source: Source | null = null;
let opts: ImportOpts = { ...DEFAULT_OPTS };
let cache: { key: string; geometry: BufferGeometry; report: ImportReport } | null = null;

export const hasImport = () => source !== null;
export const getImportOpts = () => ({ ...opts });
export const getImportName = () => source?.name ?? '';
export function setImportOpts(p: Partial<ImportOpts>) {
  opts = { ...opts, ...p };
  cache = null;
}
export const lastReport = () => cache?.report ?? null;

// ---------- loading ----------

/** Give every geometry the same attribute set (position, normal, uv, colour rgb) and an index. */
function normalise(g: BufferGeometry): BufferGeometry {
  const n = g.getAttribute('position').count;
  if (!g.getAttribute('normal')) g.computeVertexNormals();
  const out = new BufferGeometry();
  out.setAttribute('position', g.getAttribute('position').clone());
  out.setAttribute('normal', g.getAttribute('normal').clone());
  const uv = g.getAttribute('uv');
  out.setAttribute('uv', uv ? uv.clone() : new Float32BufferAttribute(new Float32Array(n * 2), 2));
  const col = g.getAttribute('color');
  const rgb = new Float32Array(n * 3).fill(1);
  if (col) for (let i = 0; i < n; i++) for (let k = 0; k < 3; k++) rgb[i * 3 + k] = col.getComponent(i, k);
  out.setAttribute('color', new Float32BufferAttribute(rgb, 3));
  if (g.index) out.setIndex(g.index.clone());
  else {
    const idx = new Uint32Array(n);
    for (let i = 0; i < n; i++) idx[i] = i;
    out.setIndex(new BufferAttribute(idx, 1));
  }
  return out;
}

/** Split a mesh that uses several materials (geometry groups) into one geometry per material. */
function splitGroups(g: BufferGeometry, mats: Material[]): Array<{ g: BufferGeometry; m: Material }> {
  const idx = g.index!;
  if (!g.groups.length) return [{ g, m: mats[0] }];
  return g.groups.map((grp) => {
    const sub = g.clone();
    const a = new Uint32Array(grp.count);
    for (let i = 0; i < grp.count; i++) a[i] = idx.getX(grp.start + i);
    sub.setIndex(new BufferAttribute(a, 1));
    sub.clearGroups();
    return { g: sub, m: mats[grp.materialIndex ?? 0] ?? mats[0] };
  });
}

export async function loadGlb(data: ArrayBuffer | string, name: string): Promise<void> {
  const loader = new GLTFLoader();
  loader.setMeshoptDecoder(MeshoptDecoder);
  const gltf = typeof data === 'string' ? await loader.loadAsync(data) : await loader.parseAsync(data, '');
  gltf.scene.updateMatrixWorld(true);
  const geos: BufferGeometry[] = [];
  const materials: Material[] = [];
  gltf.scene.traverse((o) => {
    const m = o as Mesh;
    if (!m.isMesh) return;
    const raw = m.geometry.clone();
    raw.applyMatrix4(new Matrix4().copy(m.matrixWorld));
    const base = normalise(raw);
    const mats = Array.isArray(m.material) ? m.material : [m.material];
    for (const part of splitGroups(base, mats)) {
      geos.push(part.g);
      materials.push(part.m);
    }
  });
  if (!geos.length) throw new Error('GLB has no meshes');
  const merged = mergeGeometries(geos, true);
  if (!merged) throw new Error('could not merge meshes');
  source?.geometry.dispose();
  source = { name, geometry: merged, materials };
  opts = { ...DEFAULT_OPTS };
  cache = null;
}

// ---------- fitting ----------

function fit(src: BufferGeometry, o: ImportOpts): BufferGeometry {
  const g = src.clone();
  const m = new Matrix4()
    .makeRotationY((o.rotY * Math.PI) / 180)
    .multiply(new Matrix4().makeRotationX((o.rotX * Math.PI) / 180));
  g.applyMatrix4(m);
  g.computeBoundingBox();
  const b = g.boundingBox!;
  const s = o.height / Math.max(1e-6, b.max.y - b.min.y);
  const cx = (b.min.x + b.max.x) / 2;
  const cz = (b.min.z + b.max.z) / 2;
  const fitM = new Matrix4()
    .makeTranslation(o.dx, o.dy, o.dz + 0.02)
    .multiply(new Matrix4().makeScale(s, s, s))
    .multiply(new Matrix4().makeTranslation(-cx, -b.min.y, -cz));
  g.applyMatrix4(fitM);
  g.computeBoundingBox();
  g.computeBoundingSphere();
  return g;
}

// ---------- automatic skin weights ----------

/** Rough thickness (m) of each bone. Distances are measured relative to it so thin bones (fingers) win near themselves. */
function boneRadius(name: string) {
  if (/Hand(Index|Middle|Ring|Pinky)/.test(name)) return 0.009;
  if (/Thumb/.test(name)) return 0.011;
  if (/Hand$/.test(name)) return 0.04;
  if (/ForeArm/.test(name)) return 0.04;
  if (/Arm$/.test(name)) return 0.05;
  if (/Shoulder/.test(name)) return 0.05;
  if (/Neck/.test(name)) return 0.05;
  if (/Head/.test(name)) return 0.09;
  if (/UpLeg/.test(name)) return 0.09;
  if (/Leg$/.test(name)) return 0.06;
  if (/Foot/.test(name)) return 0.05;
  if (/Toe/.test(name)) return 0.03;
  return 0.12; // hips, spine
}

const DENSE_LIMIT = 45_000_000; // floats (~180 MB) before smoothing is skipped

function bindWeights(g: BufferGeometry, skel: Skel, smooth: number) {
  const pos = g.getAttribute('position');
  const idx = g.index!;
  const N = pos.count;

  // weld coincident vertices (UV seams) so they always share weights
  const keyToUnique = new Map<string, number>();
  const uniqueOf = new Uint32Array(N);
  const upos: number[] = [];
  for (let i = 0; i < N; i++) {
    const x = pos.getX(i);
    const y = pos.getY(i);
    const z = pos.getZ(i);
    const k = `${Math.round(x * 2e4)},${Math.round(y * 2e4)},${Math.round(z * 2e4)}`;
    let u = keyToUnique.get(k);
    if (u === undefined) {
      u = keyToUnique.size;
      keyToUnique.set(k, u);
      upos.push(x, y, z);
    }
    uniqueOf[i] = u;
  }
  const U = keyToUnique.size;

  // candidate bones: skip the jaw (no mouth split on foreign meshes) and zero-length leaf bones
  const cand: number[] = [];
  skel.defs.forEach((d, i) => {
    const [a, b] = skel.seg[i];
    if (d.name === 'Jaw' || a.distanceTo(b) < 0.004) return;
    cand.push(i);
  });
  const B = cand.length;
  const ax = new Float32Array(B), ay = new Float32Array(B), az = new Float32Array(B);
  const dx = new Float32Array(B), dy = new Float32Array(B), dz = new Float32Array(B);
  const l2 = new Float32Array(B), r2 = new Float32Array(B);
  cand.forEach((bi, j) => {
    const [a, b] = skel.seg[bi];
    ax[j] = a.x; ay[j] = a.y; az[j] = a.z;
    dx[j] = b.x - a.x; dy[j] = b.y - a.y; dz[j] = b.z - a.z;
    l2[j] = dx[j] * dx[j] + dy[j] * dy[j] + dz[j] * dz[j];
    const r = boneRadius(skel.defs[bi].name);
    r2[j] = r * r;
  });

  const canSmooth = smooth > 0 && U * B <= DENSE_LIMIT;
  let W = new Float32Array(canSmooth ? U * B : B);
  const top = new Uint16Array(U * 4);
  const topW = new Float32Array(U * 4);

  const pickTop = (row: Float32Array, off: number, u: number) => {
    let i0 = -1, i1 = -1, i2 = -1, i3 = -1;
    let w0 = 0, w1 = 0, w2 = 0, w3 = 0;
    for (let j = 0; j < B; j++) {
      const w = row[off + j];
      if (w > w3) {
        if (w > w0) { i3 = i2; w3 = w2; i2 = i1; w2 = w1; i1 = i0; w1 = w0; i0 = j; w0 = w; }
        else if (w > w1) { i3 = i2; w3 = w2; i2 = i1; w2 = w1; i1 = j; w1 = w; }
        else if (w > w2) { i3 = i2; w3 = w2; i2 = j; w2 = w; }
        else { i3 = j; w3 = w; }
      }
    }
    const ids = [i0, i1, i2, i3];
    const ws = [w0, w1, w2, w3].map((w) => (w > 0.02 ? w : 0));
    const sum = ws[0] + ws[1] + ws[2] + ws[3] || 1;
    for (let k = 0; k < 4; k++) {
      top[u * 4 + k] = ids[k] >= 0 && ws[k] > 0 ? cand[ids[k]] : 0;
      topW[u * 4 + k] = ids[k] >= 0 ? ws[k] / sum : 0;
    }
  };

  // 1. inverse (normalised) distance to every candidate bone segment
  const row = new Float32Array(B);
  for (let u = 0; u < U; u++) {
    const px = upos[u * 3], py = upos[u * 3 + 1], pz = upos[u * 3 + 2];
    let sum = 0;
    for (let j = 0; j < B; j++) {
      let t = l2[j] > 0 ? ((px - ax[j]) * dx[j] + (py - ay[j]) * dy[j] + (pz - az[j]) * dz[j]) / l2[j] : 0;
      t = t < 0 ? 0 : t > 1 ? 1 : t;
      const ex = px - ax[j] - t * dx[j], ey = py - ay[j] - t * dy[j], ez = pz - az[j] - t * dz[j];
      const q = (ex * ex + ey * ey + ez * ez) / r2[j]; // (dist/radius)^2
      const w = 1 / (q * q + 1e-6); // power 4
      row[j] = w;
      sum += w;
    }
    if (canSmooth) {
      const o = u * B;
      for (let j = 0; j < B; j++) W[o + j] = row[j] / sum;
    } else {
      for (let j = 0; j < B; j++) row[j] /= sum;
      pickTop(row, 0, u);
    }
  }

  // 2. smooth the weights over the mesh graph so noisy envelopes do not leave spikes
  if (canSmooth) {
    const deg = new Uint32Array(U + 1);
    const pairs: number[] = [];
    for (let f = 0; f < idx.count; f += 3) {
      const a = uniqueOf[idx.getX(f)], b = uniqueOf[idx.getX(f + 1)], c = uniqueOf[idx.getX(f + 2)];
      if (a === b || b === c || a === c) continue;
      pairs.push(a, b, b, c, c, a);
    }
    for (let i = 0; i < pairs.length; i++) deg[pairs[i] + 1]++;
    for (let i = 0; i < U; i++) deg[i + 1] += deg[i];
    const fill = deg.slice(0, U);
    const nb = new Uint32Array(pairs.length);
    for (let i = 0; i < pairs.length; i += 2) {
      nb[fill[pairs[i]]++] = pairs[i + 1];
      nb[fill[pairs[i + 1]]++] = pairs[i];
    }
    let next = new Float32Array(U * B);
    for (let it = 0; it < smooth; it++) {
      for (let u = 0; u < U; u++) {
        const s = deg[u], e = deg[u + 1];
        const o = u * B;
        if (e === s) { for (let j = 0; j < B; j++) next[o + j] = W[o + j]; continue; }
        const inv = 0.5 / (e - s);
        for (let j = 0; j < B; j++) next[o + j] = 0.5 * W[o + j];
        for (let k = s; k < e; k++) {
          const q = nb[k] * B;
          for (let j = 0; j < B; j++) next[o + j] += inv * W[q + j];
        }
      }
      [W, next] = [next, W];
    }
    for (let u = 0; u < U; u++) pickTop(W, u * B, u);
  }

  // 3. write per-vertex attributes (coincident vertices share the welded result)
  const si = new Uint16Array(N * 4);
  const sw = new Float32Array(N * 4);
  for (let i = 0; i < N; i++) {
    const u = uniqueOf[i];
    for (let k = 0; k < 4; k++) {
      si[i * 4 + k] = top[u * 4 + k];
      sw[i * 4 + k] = topW[u * 4 + k];
    }
  }
  g.setAttribute('skinIndex', new Uint16BufferAttribute(si, 4));
  g.setAttribute('skinWeight', new Float32BufferAttribute(sw, 4));
  return { uniqueVertices: U, smoothed: canSmooth };
}

// ---------- public build ----------

export function buildImported() {
  if (!source) throw new Error('no imported mesh');
  const skel = buildSkeleton(REAL_BONE_DEFS);
  const key = JSON.stringify(opts);
  if (!cache || cache.key !== key) {
    const t0 = performance.now();
    const g = fit(source.geometry, opts);
    const r = bindWeights(g, skel, 2);
    const report: ImportReport = {
      name: source.name,
      triangles: g.index!.count / 3,
      uniqueVertices: r.uniqueVertices,
      materials: source.materials.length,
      smoothed: r.smoothed,
      ms: Math.round(performance.now() - t0),
    };
    cache?.geometry.dispose();
    cache = { key, geometry: g, report };
  }
  const geometry = cache.geometry.clone();
  geometry.computeBoundingSphere();
  return { skel, mb: { triangles: cache.report.triangles }, geometry, material: source.materials };
}

/** Bounding box of the fitted mesh, handy to check alignment against the skeleton. */
export function fittedBounds() {
  if (!cache) return null;
  const b = cache.geometry.boundingBox!;
  return { min: b.min.clone(), max: b.max.clone(), size: b.getSize(new Vector3()) };
}
