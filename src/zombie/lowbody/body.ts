// F2: the low-poly base body as ONE closed mesh (docs/10-roadmap-lowpoly.md).
// Built on a fixed topology, like the reference characters:
//  - trunk: 12-sided rings from the crotch up through chest, neck and head to a crown point;
//  - legs: the bottom trunk ring is split in two 8-vertex loops (left half + right half + one crotch point);
//  - arms: a 3x3 patch is cut out of each side of the chest (8 boundary vertices) and the arm grows from it;
//  - thumbs: one quad is cut out of each hand and a 4-sided thumb grows from it;
//  - feet: the leg tube bends forward into the foot, the sole verts are pulled back into a heel.
// Every ring's shape comes from the measured cross-sections in bodySpec (refBody.json), every vertex gets
// explicit skin weights, and the result is checked for open or doubled edges.
import { Color, MeshStandardMaterial, Vector3 } from 'three';
import { MeshBuilder, type Weights } from '../mesh';
import { buildSkeleton, type Skel } from '../skeleton';
import { boneAt, bodySpec, trunkAt, type BodySpec, type Section } from './bodySpec';
import { fingerLayout, lowBoneDefs } from './rigLow';

type W = Record<string, number>;
interface Vtx { p: Vector3; w: W }
interface Face { v: number[]; inside: Vector3 }

const TRUNK_SIDES = 12;
const LIMB_SIDES = 8;
const SHAPE = 0.85; // < 1 makes rings a little boxy, like the faceted references

const spow = (x: number, e: number) => Math.sign(x) * Math.pow(Math.abs(x), e);

class Topo {
  verts: Vtx[] = [];
  faces: Face[] = [];
  add(p: Vector3, w: W) {
    this.verts.push({ p, w });
    return this.verts.length - 1;
  }
  quad(a: number, b: number, c: number, d: number, inside: Vector3) {
    this.faces.push({ v: [a, b, c, d], inside });
  }
  tri(a: number, b: number, c: number, inside: Vector3) {
    this.faces.push({ v: [a, b, c], inside });
  }
  /** Triangles with outward winding (normal away from the face's inside point). */
  triangles(): number[][] {
    const out: number[][] = [];
    for (const f of this.faces) {
      const tris = f.v.length === 4 ? [[f.v[0], f.v[1], f.v[2]], [f.v[0], f.v[2], f.v[3]]] : [f.v];
      for (const t of tris) {
        const [a, b, c] = t.map((i) => this.verts[i].p);
        const n = new Vector3().subVectors(b, a).cross(new Vector3().subVectors(c, a));
        const cen = a.clone().add(b).add(c).multiplyScalar(1 / 3);
        out.push(n.dot(cen.sub(f.inside)) >= 0 ? t : [t[0], t[2], t[1]]);
      }
    }
    // The inside-point guess can fail on flat bits (knuckle band). Make the winding consistent through the
    // topology: walk across shared edges and flip any neighbour that runs an edge the same way; then make
    // the whole mesh face outwards (positive volume).
    const key = (p: number, q: number) => (p < q ? `${p}_${q}` : `${q}_${p}`);
    const byEdge = new Map<string, number[]>();
    out.forEach((t, i) => { for (let k = 0; k < 3; k++) { const e = key(t[k], t[(k + 1) % 3]); (byEdge.get(e) ?? byEdge.set(e, []).get(e)!).push(i); } });
    const seen = new Uint8Array(out.length);
    const runs = (t: number[], p: number, q: number) => (t[0] === p && t[1] === q) || (t[1] === p && t[2] === q) || (t[2] === p && t[0] === q);
    for (let s0 = 0; s0 < out.length; s0++) {
      if (seen[s0]) continue;
      seen[s0] = 1;
      const stack = [s0];
      while (stack.length) {
        const i = stack.pop()!;
        const t = out[i];
        for (let k = 0; k < 3; k++) {
          const p = t[k], q = t[(k + 1) % 3];
          for (const j of byEdge.get(key(p, q))!) {
            if (j === i || seen[j]) continue;
            if (runs(out[j], p, q)) out[j] = [out[j][0], out[j][2], out[j][1]];
            seen[j] = 1;
            stack.push(j);
          }
        }
      }
    }
    let vol = 0;
    for (const [a, b, c] of out) vol += this.verts[a].p.dot(new Vector3().crossVectors(this.verts[b].p, this.verts[c].p));
    return vol >= 0 ? out : out.map((t) => [t[0], t[2], t[1]]);
  }
}

/** Closed-mesh check: every edge must be used by exactly two triangles, once in each direction. */
export function checkClosed(tris: number[][]) {
  const dir = new Map<string, number>();
  for (const [a, b, c] of tris) for (const [p, q] of [[a, b], [b, c], [c, a]]) dir.set(`${p}_${q}`, (dir.get(`${p}_${q}`) ?? 0) + 1);
  let open = 0, doubled = 0, flipped = 0;
  for (const [k, n] of dir) {
    const [p, q] = k.split('_');
    const back = dir.get(`${q}_${p}`) ?? 0;
    if (n > 1) doubled++;
    if (back === 0) open++;
    else if (n !== back) flipped++;
  }
  return { triangles: tris.length, openEdges: open, doubledEdges: doubled, flippedEdges: flipped, closed: open === 0 && doubled === 0 && flipped === 0 };
}

/** Ring of n points around a bone-like frame. Same frame rule as the measuring tool. */
function frame(axis: Vector3) {
  const front = Math.abs(axis.z) > 0.8 ? new Vector3(0, 1, 0) : new Vector3(0, 0, 1);
  const u = front.clone().addScaledVector(axis, -front.dot(axis)).normalize();
  const w = new Vector3().crossVectors(axis, u).normalize();
  return { u, w };
}

function ringPoints(c: Vector3, axis: Vector3, s: Section, n: number): Vector3[] {
  const { u, w } = frame(axis);
  const pts: Vector3[] = [];
  for (let k = 0; k < n; k++) {
    const a = (k / n) * Math.PI * 2;
    const cu = Math.cos(a), sw = Math.sin(a);
    const ru = cu >= 0 ? s.front : s.back;
    const rw = sw >= 0 ? s.out : s.in;
    pts.push(c.clone().addScaledVector(u, spow(cu, SHAPE) * ru).addScaledVector(w, spow(sw, SHAPE) * rw));
  }
  return pts;
}

/** Re-order `pts` (cyclic shift, maybe reversed) to line up with the previous ring `prev`. */
function align(prev: Vector3[], pts: Vector3[]): Vector3[] {
  let best = pts, bestD = Infinity;
  const n = pts.length;
  for (const rev of [false, true]) {
    const base = rev ? [...pts].reverse() : pts;
    for (let o = 0; o < n; o++) {
      let d = 0;
      for (let k = 0; k < n; k++) d += prev[k].distanceToSquared(base[(k + o) % n]);
      if (d < bestD) { bestD = d; best = base.map((_, k) => base[(k + o) % n]); }
    }
  }
  return best;
}

const centre = (pts: Vector3[]) => pts.reduce((a, p) => a.add(p), new Vector3()).multiplyScalar(1 / pts.length);

interface Station { bone: string; f: number; ref: string; w: W; scale?: number; /** fixed section instead of the measured one */ sec?: Section }

function buildBody(spec: BodySpec, skel: Skel) {
  const T = new Topo();
  const H = spec.height;
  const J = spec.j;
  const jp = (name: string) => skel.defs[skel.index.get(name)!].p;
  const segOf = (name: string) => skel.seg[skel.index.get(name)!];

  // ---------- trunk rows ----------
  const armR = (() => {
    const s = boneAt(spec.sections.LeftArm, 0.25);
    return Math.max((s.out + s.in) / 2, (s.front + s.back) / 2);
  })();
  const armY = J.LeftArm.y, armX = J.LeftArm.x;
  const yA = armY - armR * 1.05, yB = armY + armR * 1.05; // armpit and shoulder-top rows
  const spine2Y = jp('Spine2').y;
  const crotch = spec.crotchY;
  const rowsY: number[] = [crotch, crotch + 0.035 * H, Math.max(J.Hips.y, crotch + 0.06 * H), J.Spine.y, (J.Spine.y + J.Spine1.y) / 2, J.Spine1.y, spine2Y]
    .filter((y) => y < yA - 0.012 * H);
  const iA = rowsY.length;
  rowsY.push(yA, armY, yB);
  const neckY = Math.max(J.Neck.y + 0.015 * H, yB + 0.015 * H);
  rowsY.push(neckY, Math.max(J.Head.y + 0.012 * H, neckY + 0.012 * H));
  for (const k of [0.915, 0.95, 0.98]) rowsY.push(Math.max(k * H, rowsY[rowsY.length - 1] + 0.01 * H));
  rowsY.sort((a, b) => a - b);

  // torso weights: each bone owns the span from its joint to the next, blended over +-3 % of height at joints
  const chain = ['Hips', 'Spine', 'Spine1', 'Spine2', 'Neck', 'Head'];
  const chainY = chain.map((n) => jp(n).y);
  const band = 0.03 * H;
  const trunkW = (y: number): W => {
    let i = chainY.length - 1;
    while (i > 0 && y < chainY[i]) i--;
    const w: W = { [chain[i]]: 1 };
    if (i > 0 && y - chainY[i] < band) { const k = 0.5 * (1 - (y - chainY[i]) / band); w[chain[i - 1]] = k; w[chain[i]] = 1 - k; }
    if (i < chain.length - 1 && chainY[i + 1] - y < band) { const k = 0.5 * (1 - (chainY[i + 1] - y) / band); w[chain[i + 1]] = k; w[chain[i]] = (w[chain[i]] ?? 1) - k; }
    return w;
  };

  const rows: number[][] = [];
  // neck ring: round, sized from the Neck bone's own sections (the trunk cut there mixes chin and collar)
  const neckSecs = spec.sections.Neck;
  const neckR = neckSecs.reduce((t, q) => t + (q.front + q.back + q.out + q.in) / 4, 0) / neckSecs.length;
  const neckRow = rowsY.indexOf(neckY);
  const d = 0.015 * H;
  rowsY.forEach((y, r) => {
    // light smoothing along the height removes steps between the 1 % measurement rows
    const q = [trunkAt(spec.trunk, y - d), trunkAt(spec.trunk, y), trunkAt(spec.trunk, y + d)];
    const s = { front: (q[0].front + 2 * q[1].front + q[2].front) / 4, back: (q[0].back + 2 * q[1].back + q[2].back) / 4, half: (q[0].half + 2 * q[1].half + q[2].half) / 4 };
    // below the hip joint the trunk cut misses the thigh triangles; the pelvis must still wrap both thigh tops
    if (y < J.Hips.y) {
      const th = boneAt(spec.sections.LeftUpLeg, 0.15);
      const legOut = J.LeftUpLeg.x + Math.max(th.out, th.in) * 1.05;
      s.half = Math.max(s.half, legOut);
      s.front = Math.max(s.front, J.LeftUpLeg.z + th.front);
      s.back = Math.max(s.back, -J.LeftUpLeg.z + th.back);
    }
    // shoulder-top row: the cut just above it is already the chin, so no upward smoothing, and it may not
    // stick out in front of the row below
    if (r === iA + 2) {
      const lo = trunkAt(spec.trunk, y - d), mid = trunkAt(spec.trunk, y);
      const below = trunkAt(spec.trunk, rowsY[r - 1]);
      s.front = Math.min((lo.front + mid.front) / 2, below.front);
      s.back = Math.min((lo.back + mid.back) / 2, below.back);
    }
    if (r === neckRow) {
      const zc = J.Neck.z;
      s.front = neckR + zc;
      s.back = neckR - zc;
      s.half = neckR;
    }
    // underside of the head: the jaw, not a flat disc. The back follows the neck into the skull (no ledge),
    // the sides narrow to the jaw, and the row tilts (chin low, nape high).
    const isJaw = r === neckRow + 1;
    if (isJaw) {
      const zc = J.Neck.z;
      s.back = Math.min(s.back, neckR - zc + 0.008 * H);
      s.half = Math.min(s.half * 0.85, neckR + 0.02 * H);
    }
    const isHole = r >= iA && r <= iA + 2;
    const ids: number[] = [];
    for (let i = 0; i < TRUNK_SIDES; i++) {
      const a = (i / TRUNK_SIDES) * Math.PI * 2;
      let x = spow(Math.sin(a), SHAPE) * s.half;
      let z = spow(Math.cos(a), SHAPE) * (Math.cos(a) >= 0 ? s.front : s.back);
      // shoulder-top row: the middle (throat and nape) leans halfway towards the neck ring, so the chest
      // slopes into the neck instead of ending in a flat collar
      const holeCol = (i >= 2 && i <= 4) || (i >= 8 && i <= 10);
      if (r === iA + 2 && !holeCol) {
        const zc = J.Neck.z;
        const zNeck = zc + spow(Math.cos(a), SHAPE) * neckR;
        const k = 0.5 * Math.cos(a) ** 2; // full pull at the throat and nape, fading towards the shoulders
        z = z + (zNeck - z) * k;
        x = x + (spow(Math.sin(a), SHAPE) * neckR - x) * k;
      }
      // the arm patch sits at the shoulder joint: the measured deltoid belongs to the arm, not the chest
      const side = i >= 2 && i <= 4 ? 1 : i >= 8 && i <= 10 ? -1 : 0;
      if (isHole && side) x = side * Math.min(Math.abs(x), armX * (i === 3 || i === 9 ? 1 : 0.85));
      // per-vertex height: shoulder-top row dips to the throat notch in front and a little at the nape;
      // jaw row tilts chin-down
      let vy = y;
      // (never below the row underneath, or the band between them would turn inside out)
      if (r === iA + 2) vy = Math.max(rowsY[r - 1] + 0.006 * H, vy - Math.cos(a) ** 2 * (Math.cos(a) > 0 ? 0.012 : 0.006) * H);
      if (isJaw) vy = Math.max(rowsY[r - 1] + 0.006 * H, vy - Math.cos(a) * 0.014 * H);
      const w = trunkW(vy);
      // shoulder rows follow the clavicle a little, more at the top and outside
      if (r >= iA && Math.abs(Math.sin(a)) > 0.4) {
        const sideName = x > 0 ? 'Left' : 'Right';
        const k = [0.2, 0.35, 0.55][r - iA] ?? 0.45;
        const out = Math.min(1, Math.abs(x) / armX);
        if (r <= iA + 2 || r === iA + 3) w[`${sideName}Shoulder`] = k * out;
        if (isHole && side && i !== 3 && i !== 9 && r === iA + 1) w[`${sideName}Arm`] = 0.15;
      }
      // hips/buttocks rows lean on the thighs at the sides
      if (r <= 1 && Math.abs(Math.sin(a)) > 0.3) w[`${x > 0 ? 'Left' : 'Right'}UpLeg`] = r === 0 ? 0.45 : 0.2;
      ids.push(T.add(new Vector3(x, vy, z), w));
    }
    rows.push(ids);
  });

  // trunk quads, leaving out the two 2x2 arm patches
  const holeQuad = (r: number, i: number) => (r === iA || r === iA + 1) && ((i >= 2 && i < 4) || (i >= 8 && i < 10));
  for (let r = 0; r < rows.length - 1; r++) {
    const inside = new Vector3(0, (rowsY[r] + rowsY[r + 1]) / 2, 0);
    for (let i = 0; i < TRUNK_SIDES; i++) {
      if (holeQuad(r, i)) continue;
      const j = (i + 1) % TRUNK_SIDES;
      T.quad(rows[r][i], rows[r][j], rows[r + 1][j], rows[r + 1][i], inside);
    }
  }
  // crown
  const top = rows[rows.length - 1];
  const crownZ = (T.verts[top[0]].p.z + T.verts[top[6]].p.z) / 2;
  const crown = T.add(new Vector3(0, H, crownZ), { Head: 1 });
  const crownIn = new Vector3(0, rowsY[rowsY.length - 1] - 0.02 * H, crownZ);
  for (let i = 0; i < TRUNK_SIDES; i++) T.tri(top[i], top[(i + 1) % TRUNK_SIDES], crown, crownIn);

  // ---------- limbs ----------
  // Grow a tube from a boundary loop of 8 existing vertices through the stations, then close it at `tip`.
  // tipBone null leaves the last ring open (something else continues from it).
  const limb = (s: 1 | -1, root: number[], stations: Station[], tipBone: string | null, tipW: W, sides: number, skip?: (ring: number, k: number) => boolean) => {
    const P = s > 0 ? 'Left' : 'Right';
    const mir = (p: Vector3) => new Vector3(p.x * s, p.y, p.z);
    // limb bones get the side prefix, centre bones (Hips, Spine...) keep their name
    const side = (n: string) => (/^(Hips|Spine|Spine1|Spine2|Neck|Head)$/.test(n) ? n : `${P}${n}`);
    let prev = root.map((i) => T.verts[i].p);
    let prevIds = root;
    const rings: number[][] = [];
    // sections along the chain, smoothed twice (1-2-1) so neighbouring rings never jump in size
    let secs: Section[] = stations.map((st) => {
      if (st.sec) return st.sec;
      const q = boneAt(spec.sections[`Left${st.ref}`], st.f);
      const k = st.scale ?? 1;
      // a joint cut can assign one side of the limb to the neighbour bone (e.g. the kneecap), leaving a
      // near-zero or negative radius; keep every radius at least 45 % of the mean
      const mean = (q.front + q.back + q.out + q.in) / 4;
      const fl = (x: number) => Math.max(x, 0.45 * mean) * k;
      return { front: fl(q.front), back: fl(q.back), out: fl(q.out), in: fl(q.in) };
    });
    for (let pass = 0; pass < 2; pass++) {
      secs = secs.map((q, i) => {
        if (i === 0 || i === secs.length - 1 || stations[i].sec) return q;
        const a = secs[i - 1], b = secs[i + 1];
        const m = (key: keyof Section) => (a[key] + 2 * q[key] + b[key]) / 4;
        return { front: m('front'), back: m('back'), out: m('out'), in: m('in') };
      });
    }
    for (let r = 0; r < stations.length; r++) {
      const st = stations[r];
      const [a, b] = segOf(`Left${st.bone}`);
      const axis = b.clone().sub(a);
      const c = a.clone().addScaledVector(axis, st.f);
      const scaled = secs[r];
      const pts = align(prev, ringPoints(c, axis.normalize(), scaled, sides).map(mir));
      const w: W = {};
      for (const [n, v] of Object.entries(st.w)) w[side(n)] = v;
      const ids = pts.map((p) => T.add(p, w));
      const inside = centre(prev).add(centre(pts)).multiplyScalar(0.5);
      for (let q = 0; q < sides; q++) {
        if (skip?.(r, q)) continue;
        const q1 = (q + 1) % sides;
        T.quad(prevIds[q], prevIds[q1], ids[q1], ids[q], inside);
      }
      rings.push(ids);
      prev = pts;
      prevIds = ids;
    }
    if (!tipBone) return rings;
    const tipP = mir(jp(`Left${tipBone}`));
    const tw: W = {};
    for (const [n, v] of Object.entries(tipW)) tw[side(n)] = v;
    const tip = T.add(tipP, tw);
    const tipIn = centre(prev);
    for (let q = 0; q < sides; q++) T.tri(prevIds[q], prevIds[(q + 1) % sides], tip, tipIn);
    return rings;
  };

  // Close the gap between two loops with different point counts using triangles (zip along both loops).
  const bridge = (a: number[], b: number[]) => {
    const A = a.map((i) => T.verts[i].p), B = b.map((i) => T.verts[i].p);
    // start b at the point nearest a[0], walking in the direction that follows a
    let st = 0, bd = Infinity;
    B.forEach((p, k) => { const d = p.distanceToSquared(A[0]); if (d < bd) { bd = d; st = k; } });
    const fwd = B[(st + 1) % B.length].distanceToSquared(A[1]) <= B[(st - 1 + B.length) % B.length].distanceToSquared(A[1]);
    const bi = (k: number) => b[(fwd ? st + k : st - k + B.length * 4) % B.length];
    const bp = (k: number) => T.verts[bi(k)].p;
    const inside = centre(A).add(centre(B)).multiplyScalar(0.5);
    let i = 0, j = 0;
    const n = a.length, m = b.length;
    while (i < n || j < m) {
      const ai = a[i % n], ai1 = a[(i + 1) % n];
      if (j >= m || (i < n && T.verts[ai1].p.distanceToSquared(bp(j)) < T.verts[ai].p.distanceToSquared(bp(j + 1)))) {
        T.tri(ai, ai1, bi(j), inside);
        i++;
      } else {
        T.tri(ai, bi(j + 1), bi(j), inside);
        j++;
      }
    }
  };

  const bottom = rows[0];
  // one point under the crotch, shared by both leg loops (the seam between the legs)
  const crotchPt = T.add(new Vector3(0, crotch - 0.025 * H, (T.verts[bottom[0]].p.z + T.verts[bottom[6]].p.z) / 2), { Hips: 1 });
  for (const s of [1, -1] as const) {
    const col = (i: number) => (s > 0 ? i : (TRUNK_SIDES - i) % TRUNK_SIDES);
    // ---- leg: one half of the bottom ring + crotch point ----
    const legRoot = [bottom[col(0)], bottom[col(1)], bottom[col(2)], bottom[col(3)], bottom[col(4)], bottom[col(5)], bottom[col(6)], crotchPt];
    const thighLen = segOf('LeftUpLeg')[0].distanceTo(segOf('LeftUpLeg')[1]);
    const f0 = Math.min(0.3, Math.max(0.08, (J.LeftUpLeg.y - (crotch - 0.03 * H)) / thighLen));
    limb(s, legRoot, [
      { bone: 'UpLeg', f: f0, ref: 'UpLeg', w: { UpLeg: 0.75, Hips: 0.25 }, scale: 1.05 },
      { bone: 'UpLeg', f: 0.5, ref: 'UpLeg', w: { UpLeg: 1 } },
      { bone: 'UpLeg', f: 0.8, ref: 'UpLeg', w: { UpLeg: 1 } },
      { bone: 'UpLeg', f: 0.93, ref: 'UpLeg', w: { UpLeg: 0.8, Leg: 0.2 } },
      { bone: 'Leg', f: 0.0, ref: 'Leg', w: { UpLeg: 0.5, Leg: 0.5 } },
      { bone: 'Leg', f: 0.1, ref: 'Leg', w: { UpLeg: 0.2, Leg: 0.8 } },
      { bone: 'Leg', f: 0.4, ref: 'Leg', w: { Leg: 1 } },
      { bone: 'Leg', f: 0.72, ref: 'Leg', w: { Leg: 1 } },
      { bone: 'Foot', f: 0.12, ref: 'Foot', w: { Leg: 0.25, Foot: 0.75 } },
      { bone: 'Foot', f: 0.5, ref: 'Foot', w: { Foot: 1 } },
      { bone: 'Foot', f: 0.88, ref: 'Foot', w: { Foot: 0.6, ToeBase: 0.4 } },
      { bone: 'ToeBase', f: 0.45, ref: 'ToeBase', w: { ToeBase: 1 } },
    ], 'Toe_End', { ToeBase: 1 }, LIMB_SIDES);
    // ---- arm: the 8 vertices around the cut-out chest patch ----
    const a = rows[iA], m = rows[iA + 1], b = rows[iA + 2];
    const armRoot = [a[col(2)], a[col(3)], a[col(4)], m[col(4)], b[col(4)], b[col(3)], b[col(2)], m[col(2)]];
    const armRings = limb(s, armRoot, [
      { bone: 'Arm', f: 0.22, ref: 'Arm', w: { Arm: 0.75, Shoulder: 0.25 } },
      { bone: 'Arm', f: 0.5, ref: 'Arm', w: { Arm: 1 } },
      { bone: 'Arm', f: 0.8, ref: 'Arm', w: { Arm: 1 } },
      { bone: 'Arm', f: 0.94, ref: 'Arm', w: { Arm: 0.8, ForeArm: 0.2 } },
      { bone: 'ForeArm', f: 0.0, ref: 'ForeArm', w: { Arm: 0.5, ForeArm: 0.5 } },
      { bone: 'ForeArm', f: 0.1, ref: 'ForeArm', w: { Arm: 0.2, ForeArm: 0.8 } },
      { bone: 'ForeArm', f: 0.45, ref: 'ForeArm', w: { ForeArm: 1 } },
      { bone: 'ForeArm', f: 0.85, ref: 'ForeArm', w: { ForeArm: 1 } },
      { bone: 'Hand', f: 0.05, ref: 'Hand', w: { ForeArm: 0.4, Hand: 0.6 } },
      { bone: 'Hand', f: 0.45, ref: 'Hand', w: { Hand: 1 } },
      { bone: 'Hand', f: 0.82, ref: 'Hand', w: { Hand: 1 } },
    ], null, {}, LIMB_SIDES);

    // ---- fingers: the hand ends in a knuckle grid (5 points on the back, 5 on the palm); each of the four
    // quads across it is the root of one 4-sided finger ----
    const P = s > 0 ? 'Left' : 'Right';
    const FL = fingerLayout(spec);
    const mir = (p: Vector3) => new Vector3(p.x * s, p.y, p.z);
    const K = FL.knuckle;
    const ht = FL.thickness * 0.42;
    const top: number[] = [], bot: number[] = [];
    for (let j = 0; j <= 4; j++) {
      const z = K.z + FL.halfWidth * (1 - j / 2);
      const x = K.x - (j === 4 ? 0.006 * H : 0); // the pinky side of the knuckle line sits a little back
      const near = [j - 1, j].filter((f) => f >= 0 && f < 4).map((f) => `${P}Hand${FL.fingers[f].name}1`);
      const w: W = { [`${P}Hand`]: 0.7 };
      for (const n of near) w[n] = 0.3 / near.length;
      top.push(T.add(mir(new Vector3(x, K.y + ht, z)), w));
      bot.push(T.add(mir(new Vector3(x, K.y - ht, z)), { ...w }));
    }
    // band from the last hand ring (8 points) to the knuckle loop (10 points)
    const knuckleLoop = [...top, ...[...bot].reverse()];
    bridge(armRings[armRings.length - 1], knuckleLoop);
    FL.fingers.forEach((f, i) => {
      const root = [top[i], top[i + 1], bot[i + 1], bot[i]];
      const n = (seg: string) => `Hand${f.name}${seg}`;
      const sec = (t: number): Section => ({ front: f.halfW * t, back: f.halfW * t, out: f.halfT * t, in: f.halfT * t });
      limb(s, root, [
        { bone: n('1'), f: 0.35, ref: '', sec: sec(1), w: { [n('1')]: 1 } },
        { bone: n('2'), f: 0.0, ref: '', sec: sec(0.95), w: { [n('1')]: 0.5, [n('2')]: 0.5 } },
        { bone: n('2'), f: 0.5, ref: '', sec: sec(0.9), w: { [n('2')]: 1 } },
        { bone: n('3'), f: 0.0, ref: '', sec: sec(0.85), w: { [n('2')]: 0.5, [n('3')]: 0.5 } },
        { bone: n('3'), f: 0.55, ref: '', sec: sec(0.78), w: { [n('3')]: 1 } },
      ], n('_End'), { [n('3')]: 1 }, 4);
    });

    // ---- thumb: cut the hand quad nearest the thumb joint (between the wrist ring and the mid-hand ring) ----
    const r0 = armRings[8], r1 = armRings[9];
    const thumbJ = jp(`${s > 0 ? 'Left' : 'Right'}HandThumb1`);
    let bestK = 0, bestD = Infinity;
    for (let k = 0; k < LIMB_SIDES; k++) {
      const k1 = (k + 1) % LIMB_SIDES;
      const c = [r0[k], r0[k1], r1[k1], r1[k]].reduce((acc, i) => acc.add(T.verts[i].p), new Vector3()).multiplyScalar(0.25);
      const d = c.distanceTo(thumbJ);
      if (d < bestD) { bestD = d; bestK = k; }
    }
    const k1 = (bestK + 1) % LIMB_SIDES;
    const quadIds = [r0[bestK], r0[k1], r1[k1], r1[bestK]];
    const fi = T.faces.findIndex((f) => f.v.length === 4 && quadIds.every((i) => f.v.includes(i)));
    if (fi >= 0) T.faces.splice(fi, 1);
    limb(s, quadIds, [
      // the reference thumb belongs to a mitten hand; next to separate fingers it is scaled down
      { bone: 'HandThumb1', f: 0.45, ref: 'Thumb1', w: { HandThumb1: 0.7, Hand: 0.3 }, scale: 0.75 },
      { bone: 'HandThumb2', f: 0.15, ref: 'Thumb2', w: { HandThumb1: 0.5, HandThumb2: 0.5 }, scale: 0.75 },
      { bone: 'HandThumb2', f: 0.7, ref: 'Thumb2', w: { HandThumb2: 1 }, scale: 0.7 },
    ], 'HandThumb_End', { HandThumb2: 1 }, 4);
  }
  return T;
}

const SKIN = new Color('#c99a7c');

export function buildLowBody(seed: number, femininity: number) {
  const spec = bodySpec(femininity);
  const skel = buildSkeleton(lowBoneDefs(spec));
  const T = buildBody(spec, skel);
  const tris = T.triangles();
  const check = checkClosed(tris);
  // last checks, readable from the page for automated tests
  const g = globalThis as unknown as { __lowbodyCheck?: Record<string, unknown> };
  g.__lowbodyCheck = { ...(g.__lowbodyCheck ?? {}), [femininity > 0.5 ? 'female' : 'male']: check };
  const mb = new MeshBuilder(seed, false);
  const wts = (w: W): Weights => {
    const list = Object.entries(w).filter(([, v]) => v > 0.001).map(([n, v]) => [skel.index.get(n)!, v] as [number, number]);
    list.sort((a, b) => b[1] - a[1]);
    const top = list.slice(0, 4);
    const sum = top.reduce((t, x) => t + x[1], 0);
    return top.map(([i, v]) => [i, v / sum] as [number, number]);
  };
  const paint = { base: SKIN };
  for (const [a, b, c] of tris) {
    const A = T.verts[a], B = T.verts[b], C = T.verts[c];
    mb.tri(A.p, B.p, C.p, wts(A.w), wts(B.w), wts(C.w), paint);
  }
  const { geometry } = mb.geometry();
  const material = new MeshStandardMaterial({ vertexColors: true, flatShading: true, roughness: 0.82, metalness: 0 });
  return { skel, mb, geometry, material, check };
}
