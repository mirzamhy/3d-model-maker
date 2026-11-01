// F3 helper bones for the low-poly body. Linear blend skinning shrinks a bent joint: the ring weighted
// 50/50 between two bones collapses to cos(angle / 2) of its area (0.34 at a 140 degree elbow). A helper
// bone sitting on the joint and turning HALF the joint angle carries that ring rigidly, so the bend is
// spread over two half-angle steps instead of one. Twist bones do the same for wrist roll.
// Helpers are not Mixamo bones; they must be driven after every pose (driveHelpers). A clip that knows
// nothing about them still plays, the joints just fall back to the plain weights' look.
import { Quaternion } from 'three';
import type { Rig } from '../build';

const ID = new Quaternion();
const q = new Quaternion();

/** Joint helpers: helper bone, the child bone whose local rotation it halves. */
const HALF: Array<[string, string]> = [
  ['ArmHelper', 'Arm'],
  ['ElbowHelper', 'ForeArm'],
  ['KneeHelper', 'Leg'],
  ['HipHelper', 'UpLeg'],
];

export function driveHelpers(r: Rig) {
  for (const P of ['Left', 'Right']) {
    for (const [h, child] of HALF) {
      const hb = r.bones[`${P}${h}`], cb = r.bones[`${P}${child}`];
      if (hb && cb) hb.quaternion.slerpQuaternions(ID, cb.quaternion, 0.5);
    }
    // forearm twist: half of the hand's roll around the forearm axis (local x, bind rotations are identity)
    const tw = r.bones[`${P}ForeArmTwist`], hand = r.bones[`${P}Hand`];
    if (tw && hand) {
      const h = hand.quaternion;
      q.set(h.x, 0, 0, h.w);
      if (q.lengthSq() < 1e-12) q.identity();
      else q.normalize();
      tw.quaternion.slerpQuaternions(ID, q, 0.5);
    }
  }
}
