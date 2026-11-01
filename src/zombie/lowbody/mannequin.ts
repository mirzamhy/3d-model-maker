// F1 check model: a wooden-doll mannequin on the low-poly rig. One faceted ellipsoid per bone, sized from
// the measured cross-sections, rigidly bound to that bone. It shows proportions and joint placement and lets
// the rig be posed before the real one-piece body (F2) exists. Also draws the reference silhouette outline.
import { BufferGeometry, Color, Float32BufferAttribute, LineBasicMaterial, LineLoop, Matrix4, MeshStandardMaterial, Quaternion, Vector3, type Object3D } from 'three';
import { MeshBuilder, ellipsoid, rigid } from '../mesh';
import { buildSkeleton, type Skel } from '../skeleton';
import { bodySpec, type BodySpec, type Section, type Shape } from './bodySpec';
import { isEndBone, lowBoneDefs } from './rigLow';

/** Which measured reference bone (and which of its six stations) shapes each rig bone. */
function refFor(name: string): [string, number, number] | null {
  const n = name.replace(/^Right/, 'Left');
  const map: Record<string, [string, number, number]> = {
    Hips: ['Hips', 1, 5], Spine: ['Spine', 0, 5], Spine1: ['Spine1', 0, 2], Spine2: ['Spine1', 2, 4], Neck: ['Neck', 1, 5], Head: ['Head', 0, 5],
    LeftShoulder: ['LeftShoulder', 1, 4], LeftArm: ['LeftArm', 0, 5], LeftForeArm: ['LeftForeArm', 0, 5], LeftHand: ['LeftHand', 0, 5],
    LeftHandThumb1: ['LeftThumb1', 0, 5], LeftHandThumb2: ['LeftThumb2', 0, 5], LeftHandMiddle1: ['LeftMitten1', 0, 5], LeftHandMiddle2: ['LeftMitten2', 0, 5],
    LeftUpLeg: ['LeftUpLeg', 1, 5], LeftLeg: ['LeftLeg', 0, 5], LeftFoot: ['LeftFoot', 0, 5], LeftToeBase: ['LeftToeBase', 0, 4],
  };
  return map[n] ?? null;
}

function avgSection(list: Section[], a: number, b: number): Section {
  const part = list.slice(a, b + 1);
  const m = (k: keyof Section) => part.reduce((t, s) => t + s[k], 0) / part.length;
  return { front: m('front'), back: m('back'), out: m('out'), in: m('in') };
}

const SKIN = new Color('#c99a7c');

function addPieces(mb: MeshBuilder, skel: Skel, spec: BodySpec) {
  skel.defs.forEach((d, i) => {
    if (isEndBone(d.name)) return;
    const r = refFor(d.name);
    if (!r || !spec.sections[r[0]]) return;
    const sec = avgSection(spec.sections[r[0]], r[1], r[2]);
    const [head, tail] = skel.seg[i];
    const axis = tail.clone().sub(head);
    const len = Math.max(axis.length(), 0.02);
    axis.normalize();
    const front = Math.abs(axis.z) > 0.8 ? new Vector3(0, 1, 0) : new Vector3(0, 0, 1);
    const u = front.clone().addScaledVector(axis, -front.dot(axis)).normalize();
    const w = new Vector3().crossVectors(axis, u).normalize();
    const halfW = Math.max((sec.out + sec.in) / 2, 0.012);
    const halfD = Math.max((sec.front + sec.back) / 2, 0.012);
    // wide, short bones (pelvis, clavicle) still get a body as long as they are thick
    const halfL = Math.max(len / 2 * 1.1, Math.min(halfW, halfD) * 0.9);
    const c = head.clone().add(tail).multiplyScalar(0.5).addScaledVector(u, (sec.front - sec.back) / 2).addScaledVector(w, (sec.out - sec.in) / 2);
    const q = new Quaternion().setFromRotationMatrix(new Matrix4().makeBasis(w, axis, u));
    const shade = SKIN.clone().multiplyScalar(i % 2 ? 1 : 0.9);
    ellipsoid(mb, c, new Vector3(halfW, halfL, halfD), rigid(skel, d.name), { base: shade }, 1, q);
  });
}

/** Front outline of the reference average, drawn just behind the body. */
function silhouetteLine(spec: BodySpec, color: string): Object3D {
  const s = spec.silhouette;
  const back = Math.min(...s.map((r) => r[3])) * -1 - 0.02;
  const pts: number[] = [];
  for (const r of s) pts.push(r[1], r[0], back);
  for (const r of [...s].reverse()) pts.push(-r[1], r[0], back);
  const g = new BufferGeometry();
  g.setAttribute('position', new Float32BufferAttribute(pts, 3));
  const line = new LineLoop(g, new LineBasicMaterial({ color, transparent: true, opacity: 0.8 }));
  line.name = 'refSilhouette';
  return line;
}

export function buildLowRig(seed: number, femininity: number, shape?: Shape) {
  const spec = bodySpec(femininity, undefined, shape);
  const skel = buildSkeleton(lowBoneDefs(spec));
  const mb = new MeshBuilder(seed, false);
  addPieces(mb, skel, spec);
  const { geometry } = mb.geometry();
  const material = new MeshStandardMaterial({ vertexColors: true, flatShading: true, roughness: 0.8, metalness: 0 });
  const extras = [silhouetteLine(spec, femininity > 0.5 ? '#ff7ab8' : '#6fa8ff')];
  return { skel, mb, geometry, material, extras };
}
