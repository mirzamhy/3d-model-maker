// Motion viewer: two characters side by side (?pair=f2 | survivor), same procedural moves.
// Survivor: tools/blender/rig_game.py bones, renamed to the Mixamo names below (ALIAS).
// GLBs come from tools/blender/f2_glb.py (same 73-bone rig, head coordinates: x = character's left, y up, z forward).
//
// Poses are written as world-axis rotations D per bone, relative to the T-pose rest:
//   bone.quaternion = restLocal * (restWorld^-1 * D * restWorld)
// so D turns the bone around its own pivot in the rest-pose world frame, carried along by the parent's motion.
// Blender bone rolls never leak into the poses. Helper bones (ArmHelper, ElbowHelper, KneeHelper, HipHelper) turn
// half their joint, like src/zombie/lowbody/helpers.ts. The hips are moved so the lowest foot point stays on the ground.
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';

// Character pairs, picked with ?pair=<name> (default: survivor). Left character first.
type Char = { file: string; label: string; sub: string };
const PAIRS: Record<string, [Char, Char]> = {
  f2: [{ file: '/output/head-game/f2/f2_old.glb', label: 'Lama', sub: 'F2 asli, kepala F2' },
    { file: '/output/head-game/f2/f2_new.glb', label: 'Baru', sub: 'badan quad + kepala template' }],
  survivor: [{ file: '/output/head-game/f2/f2_new.glb', label: 'F2 + kepala', sub: 'rig F2 73 tulang + helper' },
    { file: '/output/qa/survivor_v13_dressed.glb', label: 'Survivor v13', sub: 'baju: kaos, cargo, bot' }],
};
const PAIR = PAIRS[new URLSearchParams(location.search).get('pair') ?? 'survivor'] ?? PAIRS.survivor;
// rig_game.py bone names (glTF loader drops the '.': upper_arm.L -> upper_armL) -> the Mixamo names used here
const ALIAS: Record<string, string> = { hips: 'Hips', spine: 'Spine', chest: 'Spine1', upper_chest: 'Spine2', neck: 'Neck', head: 'Head' };
for (const [s, S] of [['L', 'Left'], ['R', 'Right']]) {
  Object.assign(ALIAS, {
    [`shoulder${s}`]: `${S}Shoulder`, [`upper_arm${s}`]: `${S}Arm`, [`forearm${s}`]: `${S}ForeArm`, [`hand${s}`]: `${S}Hand`,
    [`thigh${s}`]: `${S}UpLeg`, [`shin${s}`]: `${S}Leg`, [`foot${s}`]: `${S}Foot`, [`toe${s}`]: `${S}ToeBase`,
  });
  for (const [f, F] of [['thumb', 'Thumb'], ['index', 'Index'], ['middle', 'Middle'], ['ring', 'Ring'], ['pinky', 'Pinky']])
    for (const k of [1, 2, 3]) ALIAS[`${f}0${k}${s}`] = `${S}Hand${F}${k}`;
}
const GAP = 0.55; // half distance between the two characters (m)
const RAD = Math.PI / 180;
const X = new THREE.Vector3(1, 0, 0), Y = new THREE.Vector3(0, 1, 0), Z = new THREE.Vector3(0, 0, 1);

// ---------- scene ----------
const app = document.getElementById('app')!;
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.setSize(innerWidth, innerHeight);
renderer.shadowMap.enabled = true;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
app.appendChild(renderer.domElement);

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x0d0e10);
scene.fog = new THREE.Fog(0x0d0e10, 6, 14);
const camera = new THREE.PerspectiveCamera(32, innerWidth / innerHeight, 0.05, 50);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;

scene.add(new THREE.HemisphereLight(0xdfe6f0, 0x3a2e26, 0.9));
const key = new THREE.DirectionalLight(0xfff1e0, 2.4);
key.position.set(2.2, 4, 3);
key.castShadow = true;
key.shadow.mapSize.set(2048, 2048);
Object.assign(key.shadow.camera, { left: -2, right: 2, top: 2.5, bottom: -0.5, near: 0.5, far: 12 });
scene.add(key);
const rim = new THREE.DirectionalLight(0xc8d8ff, 1.2);
rim.position.set(-2.5, 3, -3);
scene.add(rim);

const floor = new THREE.Mesh(new THREE.CircleGeometry(4, 64), new THREE.MeshStandardMaterial({ color: 0x1b1d21, roughness: 1 }));
floor.rotation.x = -Math.PI / 2;
floor.receiveShadow = true;
scene.add(floor);
const grid = new THREE.GridHelper(8, 32, 0x30333a, 0x24262b);
(grid.material as THREE.Material).transparent = true;
(grid.material as THREE.Material).opacity = 0.6;
scene.add(grid);

// ---------- rig wrapper ----------
type Pose = { d: Record<string, THREE.Quaternion>; hips?: THREE.Vector3; plantZ?: boolean; air?: number };

class Rig {
  root = new THREE.Group();
  bones: Record<string, THREE.Bone> = {};
  restLocal = new Map<THREE.Bone, THREE.Quaternion>();
  restWorld = new Map<THREE.Bone, THREE.Quaternion>();
  restPos = new Map<THREE.Bone, THREE.Vector3>();
  restFoot: Record<string, THREE.Vector3> = {};
  hipsParentInv = new THREE.Quaternion();
  hipsParentScale = 1;
  wire: THREE.SkinnedMesh[] = [];
  skel!: THREE.SkeletonHelper;
  tris = 0;

  constructor(gltf: { scene: THREE.Group }, x: number) {
    const model = gltf.scene;
    // no flatShading: the GLB already carries one normal per Blender face, so a non-planar quad reads as one
    // facet (as in the Blender renders) instead of splitting into two differently lit triangles
    const mat = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.75, metalness: 0 });
    const wireMat = new THREE.MeshBasicMaterial({ color: 0x111111, wireframe: true, transparent: true, opacity: 0.55 });
    const meshes: THREE.SkinnedMesh[] = [];
    model.traverse((o) => {
      if ((o as THREE.Bone).isBone) {
        if (ALIAS[o.name]) o.name = ALIAS[o.name];
        this.bones[o.name] = o as THREE.Bone;
      }
      if ((o as THREE.SkinnedMesh).isSkinnedMesh) meshes.push(o as THREE.SkinnedMesh);
    });
    for (const m of meshes) {
      m.material = mat;
      m.castShadow = true;
      m.frustumCulled = false;
      const g = m.geometry;
      this.tris += (g.index ? g.index.count : g.attributes.position.count) / 3;
      const w = new THREE.SkinnedMesh(g, wireMat);
      w.bind(m.skeleton, m.bindMatrix);
      w.frustumCulled = false;
      w.visible = false;
      m.parent!.add(w);
      w.position.copy(m.position);
      w.quaternion.copy(m.quaternion);
      w.scale.copy(m.scale);
      this.wire.push(w);
    }
    this.root.add(model);
    this.root.position.x = x;
    scene.add(this.root);
    this.root.updateMatrixWorld(true);
    // feet on the floor: lowest skinned vertex at rest (bind pose = rest)
    const box = new THREE.Box3();
    const v = new THREE.Vector3();
    for (const m of meshes) {
      const p = m.geometry.attributes.position;
      for (let i = 0; i < p.count; i++) box.expandByPoint(v.fromBufferAttribute(p, i).applyMatrix4(m.matrixWorld));
    }
    model.position.y -= box.min.y;
    this.root.updateMatrixWorld(true);
    for (const b of Object.values(this.bones)) {
      this.restLocal.set(b, b.quaternion.clone());
      this.restWorld.set(b, b.getWorldQuaternion(new THREE.Quaternion()));
      this.restPos.set(b, b.position.clone());
    }
    const hp = this.bones.Hips.parent!;
    this.hipsParentInv = hp.getWorldQuaternion(new THREE.Quaternion()).invert();
    this.hipsParentScale = hp.getWorldScale(new THREE.Vector3()).x;
    for (const n of FOOT_PTS) this.restFoot[n] = this.bones[n].getWorldPosition(new THREE.Vector3());
    this.skel = new THREE.SkeletonHelper(model);
    this.skel.visible = false;
    scene.add(this.skel);
  }

  private setD(b: THREE.Bone, d: THREE.Quaternion) {
    const w = this.restWorld.get(b)!;
    const q = w.clone().invert().multiply(d).multiply(w);
    b.quaternion.copy(this.restLocal.get(b)!).multiply(q);
  }

  private moveHips(world: THREE.Vector3) {
    const h = this.bones.Hips;
    const local = world.clone().applyQuaternion(this.hipsParentInv).divideScalar(this.hipsParentScale);
    h.position.copy(this.restPos.get(h)!).add(local);
  }

  apply(p: Pose) {
    for (const [b, q] of this.restLocal) b.quaternion.copy(q);
    for (const [n, d] of Object.entries(p.d)) if (this.bones[n]) this.setD(this.bones[n], d);
    for (const s of ['Left', 'Right']) {
      for (const [h, c] of HALF) {
        const d = p.d[s + c];
        if (d && this.bones[s + h]) this.setD(this.bones[s + h], new THREE.Quaternion().slerp(d, 0.5));
      }
    }
    // ground: shift the hips so the lowest foot point is back at its rest height
    this.moveHips(new THREE.Vector3());
    this.root.updateMatrixWorld(true);
    let dy = Infinity, dz = 0;
    for (const n of FOOT_PTS) {
      const c = this.bones[n].getWorldPosition(new THREE.Vector3());
      dy = Math.min(dy, c.y - this.restFoot[n].y);
      if (n.endsWith('Foot')) dz += (c.z - this.restFoot[n].z) / 2;
    }
    const off = new THREE.Vector3(0, -dy + (p.air ?? 0), p.plantZ ? -dz : 0);
    if (p.hips) off.add(p.hips);
    this.moveHips(off);
  }

  show(wire: boolean, bones: boolean) {
    for (const w of this.wire) w.visible = wire;
    this.skel.visible = bones;
  }
}

const FOOT_PTS = ['LeftFoot', 'LeftToeBase', 'RightFoot', 'RightToeBase'];
const HALF: Array<[string, string]> = [['ArmHelper', 'Arm'], ['ElbowHelper', 'ForeArm'], ['KneeHelper', 'Leg'], ['HipHelper', 'UpLeg']];

// ---------- pose building ----------
/** World-axis rotation from steps applied in order: rot([X, 10], [Z, -70]) = first X then Z. */
function rot(...steps: Array<[THREE.Vector3, number]>) {
  const q = new THREE.Quaternion();
  for (const [ax, deg] of steps) q.premultiply(new THREE.Quaternion().setFromAxisAngle(ax, deg * RAD));
  return q;
}

class PoseBuilder {
  d: Record<string, THREE.Quaternion> = {};
  set(n: string, q: THREE.Quaternion) {
    this.d[n] = q;
    return this;
  }
  /** s = +1 left, -1 right. down: arm lowered from T-pose; fwd: raised forward; swing: + backward; elbow: forearm bend. */
  arm(s: 1 | -1, down: number, fwd = 0, swing = 0, elbow = 0, spread = 0) {
    const P = s > 0 ? 'Left' : 'Right';
    this.d[P + 'Arm'] = rot([Z, -down * s], [Y, -fwd * s], [X, swing], [Z, spread * s]);
    if (elbow) this.d[P + 'ForeArm'] = rot([Y, -elbow * s]);
    return this;
  }
  /** thigh: + forward; knee: + bend; foot: extra toe-up (-) / toe-down (+) on top of staying level; spread: knees out. */
  leg(s: 1 | -1, thigh: number, knee: number, foot = 0, spread = 0) {
    const P = s > 0 ? 'Left' : 'Right';
    this.d[P + 'UpLeg'] = rot([X, -thigh], [Z, spread * s], [Y, spread * 0.5 * s]);
    if (knee) this.d[P + 'Leg'] = rot([X, knee]);
    this.d[P + 'Foot'] = rot([X, thigh - knee + foot]);
    return this;
  }
  spine(lean: number, twist = 0, side = 0) {
    const q = rot([X, lean / 3], [Y, twist / 3], [Z, side / 3]);
    for (const n of ['Spine', 'Spine1', 'Spine2']) this.d[n] = q.clone();
    return this;
  }
  /** Curl the four fingers (deg per joint, toward the palm: the T-pose palm faces down) and the thumb. */
  fingers(s: 1 | -1, curl: number, thumb = curl * 0.5) {
    const P = s > 0 ? 'Left' : 'Right';
    for (const f of ['Index', 'Middle', 'Ring', 'Pinky'])
      for (const [k, share] of [[1, 0.8], [2, 1.1], [3, 0.7]] as const) this.d[`${P}Hand${f}${k}`] = rot([Z, -curl * share * s]);
    for (const k of [1, 2, 3]) this.d[`${P}HandThumb${k}`] = rot([X, thumb * (k === 1 ? 0.5 : 0.8)]);
    return this;
  }
  head(nod: number, turn = 0, tilt = 0) {
    this.d.Neck = rot([X, nod * 0.4], [Y, turn * 0.4], [Z, tilt * 0.4]);
    this.d.Head = rot([X, nod * 0.6], [Y, turn * 0.6], [Z, tilt * 0.6]);
    return this;
  }
}

const smooth = (t: number) => t * t * (3 - 2 * t);
const clamp01 = (t: number) => Math.min(1, Math.max(0, t));
/** 0 -> 1 -> 0 over a loop with holds: up over [a, b], hold, down over [c, d]. */
function ramp(p: number, a: number, b: number, c: number, d: number) {
  if (p < a || p > d) return 0;
  if (p < b) return smooth((p - a) / (b - a));
  if (p < c) return 1;
  return 1 - smooth((p - c) / (d - c));
}

type Move = { label: string; period: number; note: string; pose: (p: number, t: number) => Pose };

const MOVES: Record<string, Move> = {
  tpose: { label: 'T-pose', period: 1, note: 'Pose diam bawaan rig.', pose: () => ({ d: {} }) },
  idle: {
    label: 'Diam', period: 4, note: 'Napas, lengan turun 72°.',
    pose: (p) => {
      const b = Math.sin(p * 2 * Math.PI);
      const pb = new PoseBuilder().arm(1, 72, 4, 0, 8 + b * 2).arm(-1, 72, 4, 0, 8 + b * 2)
        .spine(1.5 * b).head(-1.5 * b, 4 * Math.sin(p * Math.PI * 2 * 0.5));
      pb.leg(1, 0, 2).leg(-1, 0, 2);
      return { d: pb.d };
    },
  },
  walk: {
    label: 'Jalan', period: 1.1, note: 'Paha ±24°, lutut tekuk saat ayun, lengan ayun berlawanan.',
    pose: (p) => {
      const f = p * 2 * Math.PI;
      const pb = new PoseBuilder();
      for (const s of [1, -1] as const) {
        const ph = s > 0 ? f : f + Math.PI;
        const thigh = 24 * Math.sin(ph);
        const swing = Math.max(0, Math.cos(ph));
        const knee = 6 + 52 * swing * swing + 10 * Math.max(0, -Math.sin(ph)) ** 2;
        pb.leg(s, thigh, knee, -8 * swing);
        pb.arm(s, 74, 2, 18 * Math.sin(ph), 14 + 12 * Math.max(0, -Math.sin(ph)));
      }
      pb.spine(4, 6 * Math.sin(f), 0).head(-3, -4 * Math.sin(f));
      pb.set('Hips', rot([Y, -6 * Math.sin(f)], [Z, 2.5 * Math.cos(2 * f)]));
      return { d: pb.d };
    },
  },
  run: {
    label: 'Lari', period: 0.68, note: 'Paha ±42°, lutut 100°, siku 85°, badan condong 10°.',
    pose: (p) => {
      const f = p * 2 * Math.PI;
      const pb = new PoseBuilder();
      for (const s of [1, -1] as const) {
        const ph = s > 0 ? f : f + Math.PI;
        const swing = Math.max(0, Math.cos(ph));
        pb.leg(s, 12 + 38 * Math.sin(ph), 16 + 95 * swing * swing + 20 * Math.max(0, -Math.sin(ph)), -10 * swing);
        pb.arm(s, 68, 6, 36 * Math.sin(ph), 85);
        pb.fingers(s, 70);
      }
      pb.spine(10, 9 * Math.sin(f)).head(-8, -6 * Math.sin(f));
      pb.set('Hips', rot([X, 6], [Y, -9 * Math.sin(f)]));
      return { d: pb.d, air: 0.05 * Math.abs(Math.sin(2 * f)) };
    },
  },
  squat: {
    label: 'Jongkok', period: 3.2, note: 'Paha 92°, lutut 125°, telapak tetap rata di lantai.',
    pose: (p) => {
      const u = ramp(p, 0.05, 0.4, 0.6, 0.95);
      const pb = new PoseBuilder();
      for (const s of [1, -1] as const) {
        pb.leg(s, 92 * u, 125 * u, 0, 12 * u);
        pb.arm(s, 72 * (1 - u) + 8 * u, 82 * u, 0, 10 + 20 * u);
      }
      pb.spine(28 * u).head(-22 * u);
      return { d: pb.d, plantZ: true };
    },
  },
  jump: {
    label: 'Lompat', period: 2.2, note: 'Ancang-ancang jongkok, tolak, melayang, mendarat.',
    pose: (p) => {
      const crouch = ramp(p, 0.0, 0.22, 0.24, 0.34) * 0.75 + ramp(p, 0.62, 0.7, 0.72, 0.92) * 0.6;
      const flight = clamp01((p - 0.32) / 0.32);
      const air = p > 0.32 && p < 0.64 ? 0.38 * Math.sin(flight * Math.PI) : 0;
      const tuck = air > 0 ? Math.sin(flight * Math.PI) : 0;
      const armsUp = ramp(p, 0.24, 0.34, 0.5, 0.66);
      const pb = new PoseBuilder();
      for (const s of [1, -1] as const) {
        pb.leg(s, 80 * crouch + 30 * tuck, 110 * crouch + 50 * tuck, 25 * tuck);
        pb.arm(s, 72 * (1 - armsUp) - 60 * armsUp, 20 * armsUp, 40 * crouch * (1 - armsUp), 15);
      }
      pb.spine(22 * crouch + 4 * tuck).head(-14 * crouch);
      return { d: pb.d, air, plantZ: air === 0 };
    },
  },
  wave: {
    label: 'Lambai', period: 1.2, note: 'Lengan kanan naik, lengan bawah melambai.',
    pose: (p) => {
      const w = Math.sin(p * 2 * Math.PI);
      const pb = new PoseBuilder().arm(1, 72, 4, 0, 10);
      // shoulder rolls 90 deg first (palm turns from down to forward), so the elbow bends on its own hinge (Y)
      // and the forearm goes up; bending around Z instead twists the elbow and leaves the palm facing sideways
      pb.set('RightArm', rot([X, -90], [Z, -8], [Y, 14]));
      pb.set('RightForeArm', rot([Y, 100 + 18 * w]));
      pb.set('RightHand', rot([Y, 12 * w]));
      pb.spine(-2, -6, 3).head(2, -14, 6);
      pb.leg(1, 0, 2).leg(-1, 0, 2);
      return { d: pb.d };
    },
  },
  zombie: {
    label: 'Zombie', period: 1.9, note: 'Lengan ke depan, langkah seret pincang, kepala miring.',
    pose: (p) => {
      const f = p * 2 * Math.PI;
      const pb = new PoseBuilder();
      for (const s of [1, -1] as const) {
        const ph = s > 0 ? f : f + Math.PI;
        const swing = Math.max(0, Math.cos(ph));
        const limp = s > 0 ? 1 : 0.55; // the right leg drags
        pb.leg(s, 16 * limp * Math.sin(ph), 10 + 30 * limp * swing * swing, -4 * swing);
        pb.arm(s, -14 + 5 * Math.sin(ph * 2), 80 + 4 * Math.sin(ph), 0, 18 + 6 * Math.sin(ph)); // raised a bit: the spine lean tips them down
      }
      pb.spine(14, 5 * Math.sin(f), 6 * Math.sin(f)).head(16, 8, 22 + 4 * Math.sin(f));
      pb.set('Hips', rot([Y, -5 * Math.sin(f)], [Z, 5 * Math.sin(f)]));
      return { d: pb.d };
    },
  },
  fist: {
    label: 'Kepal', period: 2.4, note: 'Tangan ke depan, jari mengepal lalu terbuka (jari 3 ruas + jempol).',
    pose: (p) => {
      const u = ramp(p, 0.08, 0.38, 0.62, 0.92);
      const pb = new PoseBuilder();
      for (const s of [1, -1] as const) pb.arm(s, 10, 70, 0, 20).fingers(s, 95 * u, 70 * u);
      pb.leg(1, 0, 2).leg(-1, 0, 2);
      return { d: pb.d };
    },
  },
  look: {
    label: 'Tengok', period: 4, note: 'Kepala menoleh kiri-kanan 60°, mendongak dan menunduk.',
    pose: (p) => {
      const f = p * 2 * Math.PI;
      const pb = new PoseBuilder().arm(1, 72, 4, 0, 8).arm(-1, 72, 4, 0, 8).head(18 * Math.sin(2 * f), 60 * Math.sin(f));
      pb.spine(0, 12 * Math.sin(f));
      pb.leg(1, 0, 2).leg(-1, 0, 2);
      return { d: pb.d };
    },
  },
};

// ---------- UI ----------
// bone: aim at that bone of the right-hand character, camera at bone + pos (follows the current pose)
const VIEWS: Record<string, { pos: [number, number, number]; target: [number, number, number]; bone?: string }> = {
  Depan: { pos: [0, 1.15, 5.2], target: [0, 0.9, 0] },
  '3/4': { pos: [3.4, 1.5, 3.9], target: [0, 0.85, 0] },
  Samping: { pos: [5.2, 1.1, 0], target: [0, 0.85, 0] },
  'Kepala kiri': { pos: [-GAP + 0.22, 1.7, 0.62], target: [-GAP, 1.64, 0] },
  'Kepala kanan': { pos: [GAP + 0.22, 1.7, 0.62], target: [GAP, 1.64, 0] },
  'Lutut kanan': { pos: [-0.5, 0.05, 0.3], target: [0, 0, 0], bone: 'RightLeg' },
  'Siku kanan': { pos: [-0.35, 0.2, 0.55], target: [0, 0, 0], bone: 'RightForeArm' },
  'Tangan kanan': { pos: [-0.25, 0.15, 0.4], target: [0, 0, 0], bone: 'RightHandMiddle1' },
};
let move = 'walk', paused = false, speed = 1, wire = false, bonesOn = false, clock = 0;

function button(parent: HTMLElement, label: string, onClick: () => void) {
  const b = document.createElement('button');
  b.textContent = label;
  b.onclick = onClick;
  parent.appendChild(b);
  return b;
}
const moveBtns: Record<string, HTMLButtonElement> = {};
const moves = document.getElementById('moves')!;
for (const [k, m] of Object.entries(MOVES)) moveBtns[k] = button(moves, m.label, () => selectMove(k));
function selectMove(k: string) {
  move = k;
  clock = 0;
  for (const [n, b] of Object.entries(moveBtns)) b.classList.toggle('on', n === k);
  document.getElementById('note')!.textContent = MOVES[k].note;
}
const views = document.getElementById('views')!;
for (const [k, v] of Object.entries(VIEWS)) button(views, k, () => setView(v));
function setView(v: (typeof VIEWS)[string]) {
  const b = v.bone ? rigs[1]?.bones[v.bone] : undefined;
  const t = b ? b.getWorldPosition(new THREE.Vector3()) : new THREE.Vector3(...v.target);
  controls.target.copy(t);
  camera.position.set(...v.pos);
  if (b) camera.position.add(t);
}
const bWire = document.getElementById('bWire')!, bBones = document.getElementById('bBones')!, bPause = document.getElementById('bPause')!;
bWire.onclick = () => { wire = !wire; bWire.classList.toggle('on', wire); rigs.forEach((r) => r.show(wire, bonesOn)); };
bBones.onclick = () => { bonesOn = !bonesOn; bBones.classList.toggle('on', bonesOn); rigs.forEach((r) => r.show(wire, bonesOn)); };
bPause.onclick = () => { paused = !paused; bPause.classList.toggle('on', paused); };
(document.getElementById('speed') as HTMLInputElement).oninput = (e) => { speed = +(e.target as HTMLInputElement).value; };

// ---------- load + loop ----------
const rigs: Rig[] = [];
const loader = new GLTFLoader();
const [gOld, gNew] = await Promise.all(PAIR.map((c) => loader.loadAsync(c.file)));
for (const [i, c] of PAIR.entries()) {
  const tag = document.getElementById(i ? 'tagNew' : 'tagOld')!;
  tag.querySelector('b')!.textContent = c.label;
  tag.querySelector('span')!.textContent = c.sub;
}
rigs.push(new Rig(gOld, -GAP), new Rig(gNew, GAP));
document.getElementById('statOld')!.textContent = `${rigs[0].tris} segitiga`;
document.getElementById('statNew')!.textContent = `${rigs[1].tris} segitiga`;
selectMove(move);
setView(VIEWS['3/4']);
// debug: gerak.freeze('squat', 0.5) shows one phase of a move, paused
const freeze = (k: string, phase: number) => { selectMove(k); clock = phase * MOVES[k].period; paused = true; bPause.classList.add('on'); };
(window as unknown as { gerak: unknown }).gerak = { rigs, MOVES, selectMove, freeze };

const timer = new THREE.Clock();
renderer.setAnimationLoop(() => {
  const dt = timer.getDelta();
  if (!paused) clock += dt * speed;
  const m = MOVES[move];
  const p = (clock / m.period) % 1;
  for (const r of rigs) r.apply(m.pose(p, clock));
  controls.update();
  renderer.render(scene, camera);
});
addEventListener('resize', () => {
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
});
