// Rig-structure overlay in the style of docs/ref/referensi-rig.webp:
// bone sticks, joint balls, control rings (yellow centre, red left, blue right), foot boxes, labels.
import {
  BufferGeometry,
  Camera,
  Color,
  CylinderGeometry,
  Group,
  Line,
  LineBasicMaterial,
  LineLoop,
  Mesh,
  MeshBasicMaterial,
  Quaternion,
  RingGeometry,
  SphereGeometry,
  TorusGeometry,
  Vector3,
} from 'three';
import type { Rig } from '../zombie/build';

const YELLOW = new Color('#f2d23c');
const RED = new Color('#ff4a3d');
const BLUE = new Color('#3d8bff');
const BONE = new Color('#e8e8e8');

interface Ctrl {
  bone: string;
  tail: string;
  r: number;
  color: Color;
  label?: string;
  side?: 1 | -1 | 0;
  /** Put the label above the joint instead of beside it. */
  above?: boolean;
}

const CTRLS: Ctrl[] = [
  { bone: 'Hips', tail: 'Spine', r: 0.2, color: YELLOW, label: 'PELVIS / HIP', side: 0 },
  { bone: 'Spine', tail: 'Spine1', r: 0.15, color: YELLOW },
  { bone: 'Spine1', tail: 'Spine2', r: 0.15, color: YELLOW, label: 'SPINE', side: 0 },
  { bone: 'Spine2', tail: 'Neck', r: 0.16, color: YELLOW },
  { bone: 'Neck', tail: 'Head', r: 0.075, color: YELLOW, label: 'HEAD / NECK', side: 0 },
];
for (const s of [1, -1] as const) {
  const P = s > 0 ? 'Left' : 'Right';
  const c = s > 0 ? RED : BLUE;
  const t = s > 0 ? '(L)' : '(R)';
  CTRLS.push(
    { bone: `${P}Arm`, tail: `${P}ForeArm`, r: 0.065, color: c, label: `SHOULDER ${t}`, side: s, above: true },
    { bone: `${P}ForeArm`, tail: `${P}Hand`, r: 0.05, color: c, label: `ELBOW ${t}`, side: s, above: true },
    { bone: `${P}Hand`, tail: `${P}HandMiddle1`, r: 0.045, color: c, label: `WRIST ${t}`, side: s, above: true },
    { bone: `${P}Leg`, tail: `${P}Foot`, r: 0.07, color: c, label: `KNEE ${t}`, side: s },
    { bone: `${P}Foot`, tail: `${P}ToeBase`, r: 0.065, color: c, label: `ANKLE ${t}`, side: s },
    { bone: `${P}UpLeg`, tail: `${P}Leg`, r: 0.085, color: c, side: s },
  );
}

const overlayMat = (c: Color, opacity = 1) => new MeshBasicMaterial({ color: c, depthTest: false, depthWrite: false, transparent: true, opacity });

export class RigOverlay {
  readonly group = new Group();
  private sticks: Array<{ a: string; b: string; m: Mesh }> = [];
  private balls: Array<{ b: string; m: Mesh }> = [];
  private rings: Array<{ c: Ctrl; m: Mesh }> = [];
  private feet: Array<{ toe: string; foot: string; m: LineLoop; color: Color }> = [];
  private ground: Mesh;
  private labels: Array<{ el: HTMLDivElement; c: Ctrl }> = [];

  constructor(private rig: Rig, private labelHost: HTMLElement) {
    this.group.renderOrder = 10;
    const stickGeo = new CylinderGeometry(1, 1, 1, 6);
    const ballGeo = new SphereGeometry(1, 10, 8);
    const skipStick = /HeadTop_End|Jaw|Toe_End/;
    for (const b of Object.values(rig.bones)) {
      if (!b.parent || !(b.parent as { isBone?: boolean }).isBone) continue;
      if (skipStick.test(b.name)) continue;
      const finger = /Hand(Index|Middle|Pinky|Thumb)/.test(b.name);
      const m = new Mesh(stickGeo, overlayMat(BONE, 0.9));
      m.userData.r = finger ? 0.0025 : 0.007;
      m.renderOrder = 11;
      this.group.add(m);
      this.sticks.push({ a: b.parent.name, b: b.name, m });
      const ball = new Mesh(ballGeo, overlayMat(BONE));
      ball.scale.setScalar(finger ? 0.004 : 0.016);
      ball.renderOrder = 12;
      this.group.add(ball);
      this.balls.push({ b: b.name, m: ball });
    }
    for (const c of CTRLS) {
      const m = new Mesh(new TorusGeometry(c.r, 0.0045, 6, 40), overlayMat(c.color, 0.95));
      m.renderOrder = 13;
      this.group.add(m);
      this.rings.push({ c, m });
      if (c.label) {
        const el = document.createElement('div');
        el.className = 'rig-label';
        el.textContent = c.label;
        el.style.setProperty('--c', `#${c.color.getHexString()}`);
        labelHost.appendChild(el);
        this.labels.push({ el, c });
      }
    }
    for (const s of [1, -1] as const) {
      const P = s > 0 ? 'Left' : 'Right';
      const color = s > 0 ? RED : BLUE;
      const g = new BufferGeometry().setFromPoints([new Vector3(-0.05, 0, -0.09), new Vector3(0.05, 0, -0.09), new Vector3(0.05, 0, 0.13), new Vector3(-0.05, 0, 0.13)]);
      const m = new LineLoop(g, new LineBasicMaterial({ color, depthTest: false, transparent: true }));
      m.renderOrder = 13;
      this.group.add(m);
      this.feet.push({ toe: `${P}ToeBase`, foot: `${P}Foot`, m, color });
      const lab = document.createElement('div');
      lab.className = 'rig-label';
      lab.textContent = `FOOT ${s > 0 ? '(L)' : '(R)'}`;
      lab.style.setProperty('--c', `#${color.getHexString()}`);
      labelHost.appendChild(lab);
      this.labels.push({ el: lab, c: { bone: `${P}ToeBase`, tail: `${P}Toe_End`, r: 0, color, side: s } });
    }
    this.ground = new Mesh(new RingGeometry(0.62, 0.628, 64), new MeshBasicMaterial({ color: YELLOW, transparent: true, opacity: 0.8, depthWrite: false }));
    this.ground.rotation.x = -Math.PI / 2;
    this.ground.scale.set(1, 0.62, 1);
    this.ground.position.y = 0.002;
    this.group.add(this.ground);
    void Line;
  }

  private wp(name: string, out = new Vector3()) {
    return this.rig.bones[name].getWorldPosition(out);
  }

  update(camera: Camera, w: number, h: number, showLabels: boolean) {
    const a = new Vector3();
    const b = new Vector3();
    const up = new Vector3(0, 1, 0);
    const zAxis = new Vector3(0, 0, 1);
    for (const s of this.sticks) {
      this.wp(s.a, a);
      this.wp(s.b, b);
      const len = a.distanceTo(b);
      s.m.position.copy(a).add(b).multiplyScalar(0.5);
      s.m.quaternion.setFromUnitVectors(up, b.clone().sub(a).normalize());
      s.m.scale.set(s.m.userData.r, len, s.m.userData.r);
    }
    for (const bl of this.balls) this.wp(bl.b, bl.m.position);
    const q = new Quaternion();
    for (const r of this.rings) {
      this.wp(r.c.bone, a);
      this.wp(r.c.tail, b);
      r.m.position.copy(a);
      q.setFromUnitVectors(zAxis, b.sub(a).normalize());
      r.m.quaternion.copy(q);
    }
    for (const f of this.feet) {
      this.wp(f.foot, a);
      this.wp(f.toe, b);
      f.m.position.set(a.x, 0.004, a.z);
      f.m.rotation.y = Math.atan2(b.x - a.x, b.z - a.z);
    }
    const hips = this.wp('Hips', a);
    this.ground.position.x = hips.x;
    this.ground.position.z = hips.z;

    for (const l of this.labels) {
      l.el.style.display = showLabels ? '' : 'none';
      if (!showLabels) continue;
      this.wp(l.c.bone, a);
      const p = a.clone().project(camera);
      const x = (p.x * 0.5 + 0.5) * w;
      const y = (-p.y * 0.5 + 0.5) * h;
      // labels sit on the screen side the joint is on
      if (l.c.above) {
        l.el.style.transform = `translate(${x}px, ${y - 30}px) translate(-50%, -100%)`;
        l.el.dataset.side = 'u';
        continue;
      }
      const screenSide = l.c.side === 0 ? 1 : Math.sign(p.x - this.wp('Hips', b).project(camera).x) || 1;
      l.el.style.transform = `translate(${x + (screenSide > 0 ? 34 : -34)}px, ${y}px) translate(${screenSide > 0 ? '0' : '-100%'}, -50%)`;
      l.el.dataset.side = screenSide > 0 ? 'r' : 'l';
    }
  }

  dispose() {
    for (const l of this.labels) l.el.remove();
  }
}
