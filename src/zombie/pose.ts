// Poses and procedural animation. Bind rotations are identity, so Euler angles are
// relative to the T-pose. Euler order XYZ applies Z first, then Y, then X (parent axes).
// Signs: arm lowering = -Z on the left, +Z on the right; forward swing = -Y left, +Y right.
import { Vector3 } from 'three';
import type { Rig } from './build';

export type PoseName = 'tpose' | 'idle' | 'walk' | 'reach' | 'attack' | 'lunge' | 'roar' | 'crawl' | 'sit' | 'hwalk' | 'squat' | 'armsup';
export const POSES: PoseName[] = ['tpose', 'idle', 'walk', 'reach', 'attack', 'lunge', 'roar', 'crawl', 'sit', 'hwalk', 'squat', 'armsup'];

const D = Math.PI / 180;

function rot(r: Rig, name: string, x = 0, y = 0, z = 0) {
  const b = r.bones[name];
  if (b) b.rotation.set(x * D, y * D, z * D, 'XYZ');
}

export function resetPose(r: Rig) {
  for (const [n, b] of Object.entries(r.bones)) {
    b.rotation.set(0, 0, 0);
    b.position.copy(r.bindLocal[n]);
  }
}

interface ArmPose {
  shoulder: [number, number]; // droop (down), forward
  arm: [number, number, number]; // swing (x), forward (y), down (z)
  elbow: number;
  wrist: number;
  curl: [number, number, number];
  /** Finger fan (degrees between neighbouring fingers). */
  spread?: number;
}

function armPose(r: Rig, s: 1 | -1, p: ArmPose) {
  const P = s > 0 ? 'Left' : 'Right';
  rot(r, `${P}Shoulder`, 0, -s * p.shoulder[1], -s * p.shoulder[0]);
  rot(r, `${P}Arm`, p.arm[0], -s * p.arm[1], -s * p.arm[2]);
  rot(r, `${P}ForeArm`, 0, -s * p.elbow, 0);
  rot(r, `${P}Hand`, 0, 0, -s * p.wrist);
  const fan: Record<string, number> = { Index: 1, Middle: 0, Ring: -1, Pinky: -2 };
  for (const f of ['Index', 'Middle', 'Ring', 'Pinky']) {
    ['1', '2', '3'].forEach((k, i) => rot(r, `${P}Hand${f}${k}`, 0, i === 0 ? -s * fan[f] * (p.spread ?? 0) : 0, -s * p.curl[i]));
  }
  ['Thumb1', 'Thumb2', 'Thumb3'].forEach((k, i) => rot(r, `${P}Hand${k}`, 0, -s * p.curl[i] * 0.4 - (i === 0 ? s * (p.spread ?? 0) : 0), -s * p.curl[i] * 0.5));
}

function legPose(r: Rig, s: 1 | -1, hip: number, knee: number, foot: number, splay = 0) {
  const P = s > 0 ? 'Left' : 'Right';
  rot(r, `${P}UpLeg`, hip, 0, s * splay);
  rot(r, `${P}Leg`, knee, 0, 0);
  rot(r, `${P}Foot`, foot, 0, -s * splay);
}

function hunch(r: Rig, t: number, extra = 0) {
  rot(r, 'Spine', 7 + 1.2 * Math.sin(t * 1.3) + extra * 0.3, 0, 0);
  rot(r, 'Spine1', 9 + extra * 0.3, 0, 0);
  rot(r, 'Spine2', 12 + extra * 0.4, 0, 1.5);
  rot(r, 'Neck', 14, 0, 0);
  rot(r, 'Head', -27 + 2 * Math.sin(t * 0.9), 4 * Math.sin(t * 0.4), 5 + 3 * Math.sin(t * 0.6));
}

const jaw = (r: Rig, deg: number) => {
  if (r.bones.Jaw) r.bones.Jaw.rotation.x = deg * D;
};

/** Shift the hips so the lowest contact point rests on the floor. Clearance = bone-to-surface distance. */
function groundTo(r: Rig, contacts: Array<[string, number]>) {
  r.root.updateMatrixWorld(true);
  const scale = r.root.scale.y;
  let delta = Infinity;
  const p = new Vector3();
  for (const [n, clear] of contacts) {
    const b = r.bones[n];
    if (!b) continue;
    b.getWorldPosition(p);
    delta = Math.min(delta, (p.y - r.root.position.y) / scale - clear);
  }
  if (Number.isFinite(delta)) r.bones.Hips.position.y -= delta;
}

const feet = (r: Rig): Array<[string, number]> =>
  ['LeftFoot', 'RightFoot', 'LeftToeBase', 'RightToeBase', 'LeftToe_End', 'RightToe_End'].map((n) => [n, r.bindWorld[n].y]);

export function applyPose(r: Rig, pose: PoseName, t: number) {
  resetPose(r);
  if (pose === 'tpose') return;
  let contacts = feet(r);

  const breathe = Math.sin(t * 1.1);
  const idleArm = (s: 1 | -1, ph: number): ArmPose => ({
    shoulder: [8 + (s > 0 ? 2 : 0), 8],
    arm: [-8 + 3 * Math.sin(t * 1.1 + ph), 12, 70],
    elbow: 20 + 3 * breathe,
    wrist: 12,
    curl: [28, 36, 42],
  });

  if (pose === 'idle') {
    hunch(r, t);
    jaw(r, 6 + 5 * Math.max(0, Math.sin(t * 2.1)));
    armPose(r, 1, idleArm(1, 0));
    armPose(r, -1, idleArm(-1, 1.3));
    legPose(r, 1, -6, 14, -8, 3);
    legPose(r, -1, -4, 12, -8, 3);
  }

  if (pose === 'walk') {
    const ph = 2 * Math.PI * 0.8 * t;
    hunch(r, t, 4);
    rot(r, 'Hips', 0, 6 * Math.sin(ph), 4 * Math.sin(ph));
    rot(r, 'Spine', 9, -5 * Math.sin(ph), -2 * Math.sin(ph));
    jaw(r, 10 + 6 * Math.sin(ph * 2));
    const leg = (s: 1 | -1, phase: number, amp: number, kneeAmp: number) => {
      const hip = -6 - 20 * amp * Math.sin(phase);
      const knee = 12 + kneeAmp * Math.max(0, Math.cos(phase));
      legPose(r, s, hip, knee, -(hip + knee) * 0.9, 3);
    };
    leg(1, ph, 1, 30);
    leg(-1, ph + Math.PI, 0.65, 14); // dragged, limping right leg
    const L = idleArm(1, 0);
    L.arm[0] = -8 + 14 * Math.sin(ph);
    const R = idleArm(-1, 0);
    R.arm[0] = -8 - 9 * Math.sin(ph);
    armPose(r, 1, L);
    armPose(r, -1, R);
  }

  if (pose === 'reach') {
    hunch(r, t, -6);
    jaw(r, 14 + 7 * Math.max(0, Math.sin(t * 2.4)));
    const reach = (ph: number): ArmPose => ({
      shoulder: [4, 14],
      arm: [-4 + 4 * Math.sin(t * 1.6 + ph), 80, -16],
      elbow: 10 + 6 * Math.sin(t * 1.6 + ph),
      wrist: 14,
      curl: [20, 28, 34],
    });
    armPose(r, 1, reach(0));
    armPose(r, -1, reach(1.7));
    legPose(r, 1, -10, 16, -6, 3);
    legPose(r, -1, 2, 10, -12, 3);
  }

  if (pose === 'attack') {
    const c = (t % 1.1) / 1.1;
    const swing = c < 0.55 ? Math.sin((c / 0.55) * Math.PI * 0.5) : Math.cos(((c - 0.55) / 0.45) * Math.PI * 0.5);
    hunch(r, t, 8 * swing);
    jaw(r, 8 + 20 * swing);
    const claw = (lag: number): ArmPose => {
      const k = Math.max(0, Math.min(1, swing * 1.2 - lag));
      return { shoulder: [-10 + 14 * k, 16], arm: [0, 72, -55 + 60 * k], elbow: 40 - 30 * k, wrist: 20, curl: [35, 45, 50] };
    };
    armPose(r, 1, claw(0));
    armPose(r, -1, claw(0.15));
    legPose(r, 1, -18, 22, -4, 4);
    legPose(r, -1, 8, 10, -18, 4);
  }

  if (pose === 'lunge') {
    // wide crouch, ready to pounce, clawed hands spread (ref: realistic zombie sheet)
    const sway = Math.sin(t * 1.4);
    rot(r, 'Hips', 0, 6, 0);
    rot(r, 'Spine', 12 + 2 * sway, -4, 0);
    rot(r, 'Spine1', 10, -3, 0);
    rot(r, 'Spine2', 12, -3, 2);
    rot(r, 'Neck', 6, 0, 0);
    rot(r, 'Head', -24 + 3 * sway, 6, 6);
    jaw(r, 20 + 6 * Math.max(0, Math.sin(t * 2.6)));
    armPose(r, 1, { shoulder: [2, 16], arm: [-22 + 4 * sway, 62, 14], elbow: 38, wrist: -14, curl: [14, 24, 24], spread: 9 });
    armPose(r, -1, { shoulder: [6, 12], arm: [4 - 3 * sway, 34, 34], elbow: 34, wrist: -10, curl: [18, 28, 28], spread: 8 });
    legPose(r, 1, -30, 48, -6, 17);
    legPose(r, -1, 6, 32, -26, 14);
  }

  if (pose === 'roar') {
    // arms flung wide, head thrown up, mouth gaping (ref: low-poly horde, centre)
    const pulse = 0.5 + 0.5 * Math.sin(t * 3);
    rot(r, 'Spine', 6, 0, 0);
    rot(r, 'Spine1', -2, 0, 0);
    rot(r, 'Spine2', 2 - 4 * pulse, 0, 0);
    rot(r, 'Neck', -4, 0, 0);
    rot(r, 'Head', -26 - 6 * pulse, 0, 2);
    jaw(r, 18 + 8 * pulse);
    const wide = (s: 1 | -1): ArmPose => ({ shoulder: [-4 - 4 * pulse, 8], arm: [-4 + 2 * s, 34, 34 - 8 * pulse], elbow: 22, wrist: -16, curl: [10, 16, 20], spread: 11 });
    armPose(r, 1, wide(1));
    armPose(r, -1, wide(-1));
    legPose(r, 1, -24, 40, -16, 13);
    legPose(r, -1, -18, 38, -20, 13);
  }

  if (pose === 'crawl') {
    // dragging itself along the floor, one foot raised behind
    const ph = Math.sin(t * 1.6);
    rot(r, 'Hips', 80, 0, 3 * ph);
    rot(r, 'Spine', -4, 0, -3 * ph);
    rot(r, 'Spine1', -6, 0, 0);
    rot(r, 'Spine2', -10, 0, 0);
    rot(r, 'Neck', -30, 0, 0);
    rot(r, 'Head', -38, 6 * ph, 0);
    jaw(r, 16 + 8 * Math.max(0, Math.sin(t * 2.2)));
    armPose(r, 1, { shoulder: [0, 18], arm: [6 * ph, 64, 22], elbow: 40 + 10 * ph, wrist: -24, curl: [14, 20, 20], spread: 8 });
    armPose(r, -1, { shoulder: [0, 18], arm: [-6 * ph, 70, 16], elbow: 34 - 10 * ph, wrist: -24, curl: [14, 20, 20], spread: 8 });
    legPose(r, 1, -46, 92, 30, 8);
    legPose(r, -1, -30, 20, 40, 10);
    contacts = [
      ['LeftHand', 0.025],
      ['RightHand', 0.025],
      ['LeftLeg', 0.065],
      ['RightLeg', 0.065],
      ['RightToe_End', 0.02],
      ['Spine1', 0.13],
    ];
  }

  if (pose === 'sit') {
    // slumped on the floor, one knee up, leaning on a hand behind
    rot(r, 'Hips', -14, 10, 0);
    rot(r, 'Spine', 16, 0, 0);
    rot(r, 'Spine1', 12, 0, 0);
    rot(r, 'Spine2', 10, 0, 3);
    rot(r, 'Neck', 8, 0, 0);
    rot(r, 'Head', -20 + 3 * Math.sin(t), -12, 8);
    jaw(r, 10 + 4 * Math.max(0, Math.sin(t * 1.8)));
    legPose(r, 1, -111, 71, 54, 10);
    legPose(r, -1, -74, 4, -5, 18);
    armPose(r, 1, { shoulder: [10, -8], arm: [22, -4, 84], elbow: 4, wrist: -34, curl: [10, 18, 18], spread: 6 });
    armPose(r, -1, { shoulder: [8, 12], arm: [-14, 36, 48], elbow: 56, wrist: 16, curl: [30, 40, 44] });
    contacts = [
      ['Hips', 0.11],
      ['LeftFoot', 0.08],
      ['RightFoot', 0.08],
      ['LeftToe_End', 0.02],
      ['RightToe_End', 0.02],
      ['LeftHand', 0.025],
    ];
  }

  // ---- human motion tests (upright, no zombie hunch) ----
  if (pose === 'hwalk') {
    const ph = 2 * Math.PI * 0.9 * t;
    rot(r, 'Hips', 0, 5 * Math.sin(ph), 0);
    rot(r, 'Spine', 3, -4 * Math.sin(ph), 0);
    rot(r, 'Spine2', 2, -3 * Math.sin(ph), 0);
    rot(r, 'Head', -4, 4 * Math.sin(ph), 0);
    const leg = (s: 1 | -1, phase: number) => {
      // hip swings forward as phase goes 0 -> pi/2; the knee folds most mid-swing, once the thigh is already forward
      const hip = -24 * Math.sin(phase);
      const knee = 6 + 50 * Math.pow(Math.max(0, Math.cos(phase - 0.5)), 1.5);
      legPose(r, s, hip, knee, -(hip + knee) * 0.55 + 6 * Math.sin(phase));
    };
    leg(1, ph);
    leg(-1, ph + Math.PI);
    const arm = (s: 1 | -1, phase: number): ArmPose => ({ shoulder: [6, 0], arm: [-24 * Math.sin(phase), 6, 76], elbow: 16 + 10 * Math.max(0, Math.sin(phase)), wrist: 4, curl: [20, 26, 30] });
    armPose(r, 1, arm(1, ph + Math.PI));
    armPose(r, -1, arm(-1, ph));
  }

  if (pose === 'squat') {
    // slow full squat and back up: deepest hip and knee bends
    const k = 0.5 - 0.5 * Math.cos(t * 1.4);
    rot(r, 'Spine', 18 * k, 0, 0);
    rot(r, 'Spine1', 8 * k, 0, 0);
    rot(r, 'Head', -16 * k, 0, 0);
    const hip = -110 * k, knee = 125 * k;
    legPose(r, 1, hip, knee, -(hip + knee) - 4 * k, 8 * k);
    legPose(r, -1, hip, knee, -(hip + knee) - 4 * k, 8 * k);
    const reach: ArmPose = { shoulder: [0, 10 * k], arm: [0, 80 * k, 80 - 80 * k], elbow: 6, wrist: 0, curl: [10, 14, 16] };
    armPose(r, 1, reach);
    armPose(r, -1, reach);
  }

  if (pose === 'armsup') {
    // arms swing from the sides to straight overhead, body twists: shoulder and waist extremes
    const k = 0.5 - 0.5 * Math.cos(t * 1.2);
    rot(r, 'Spine', 0, 25 * Math.sin(t * 0.6), 0);
    rot(r, 'Spine2', -6 * k, 15 * Math.sin(t * 0.6), 0);
    const up: ArmPose = { shoulder: [-14 * k, 0], arm: [0, 0, 80 - 158 * k], elbow: 8, wrist: 0, curl: [6, 8, 10] };
    armPose(r, 1, up);
    armPose(r, -1, up);
    legPose(r, 1, 0, 0, 0, 4);
    legPose(r, -1, 0, 0, 0, 4);
  }

  groundTo(r, contacts);
}

// ---- F3 pose battery: held poses at the joint extremes, for the automated deformation tests ----
const still = (r: Rig, arm: ArmPose, legs?: (s: 1 | -1) => void) => {
  armPose(r, 1, arm);
  armPose(r, -1, arm);
  if (legs) { legs(1); legs(-1); }
};
const relaxed: ArmPose = { shoulder: [0, 0], arm: [0, 0, 0], elbow: 0, wrist: 0, curl: [0, 0, 0] };
export const POSE_TESTS: Array<{ name: string; set: (r: Rig) => void }> = [
  { name: 'tpose', set: () => {} },
  { name: 'apose', set: (r) => still(r, { ...relaxed, arm: [0, 0, 45] }) },
  { name: 'armsdown', set: (r) => still(r, { ...relaxed, shoulder: [6, 0], arm: [0, 6, 80] }) },
  { name: 'armsup', set: (r) => still(r, { ...relaxed, shoulder: [-14, 0], arm: [0, 0, -78] }) },
  { name: 'armsfwd', set: (r) => still(r, { ...relaxed, shoulder: [0, 10], arm: [0, 85, 0] }) },
  { name: 'armsback', set: (r) => still(r, { ...relaxed, arm: [0, -40, 70] }) },
  { name: 'elbow140', set: (r) => still(r, { ...relaxed, arm: [0, 20, 60], elbow: 140 }) },
  { name: 'forearmtwist', set: (r) => { still(r, { ...relaxed, arm: [0, 0, 45] }); for (const P of ['Left', 'Right']) r.bones[`${P}ForeArm`]?.rotation.set(Math.PI / 2, 0, 0); } },
  { name: 'wristtwist', set: (r) => { still(r, { ...relaxed, arm: [0, 0, 45] }); for (const P of ['Left', 'Right']) r.bones[`${P}Hand`]?.rotation.set(Math.PI / 2, 0, 0); } },
  { name: 'fist', set: (r) => still(r, { ...relaxed, arm: [0, 0, 45], curl: [85, 95, 70] }) },
  { name: 'knee150', set: (r) => still(r, { ...relaxed, arm: [0, 0, 70] }, (s) => legPose(r, s, -40, 150, 0)) },
  { name: 'squat', set: (r) => { rot(r, 'Spine', 18); rot(r, 'Spine1', 8); still(r, { ...relaxed, shoulder: [0, 10], arm: [0, 80, 0] }, (s) => legPose(r, s, -110, 125, -19, 8)); } },
  { name: 'kick', set: (r) => { still(r, { ...relaxed, arm: [0, 0, 70] }); legPose(r, 1, -90, 0, 0); } },
  { name: 'splits', set: (r) => still(r, { ...relaxed, arm: [0, 0, 45] }, (s) => legPose(r, s, 0, 0, 0, 45)) },
  { name: 'bendfwd', set: (r) => { rot(r, 'Spine', 30); rot(r, 'Spine1', 20); rot(r, 'Spine2', 10); rot(r, 'Neck', 10); rot(r, 'Head', 15); still(r, { ...relaxed, arm: [0, 0, 70] }); } },
  { name: 'twist', set: (r) => { rot(r, 'Spine', 0, 20); rot(r, 'Spine1', 0, 15); rot(r, 'Spine2', 0, 10); rot(r, 'Head', 0, 40); still(r, { ...relaxed, arm: [0, 0, 70] }); } },
  { name: 'walk0', set: (r) => applyPose(r, 'hwalk', 0) },
  { name: 'walk1', set: (r) => applyPose(r, 'hwalk', 0.28) },
  { name: 'walk2', set: (r) => applyPose(r, 'hwalk', 0.56) },
  { name: 'walk3', set: (r) => applyPose(r, 'hwalk', 0.83) },
];
