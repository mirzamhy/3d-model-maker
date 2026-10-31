// Every number the model uses lives here (see docs/01-anatomi-proporsi.md).
// Units: metres. Axes: +Y up, +Z forward (face), +X = character's left.
import { Color } from 'three';

export const HEIGHT = 1.75;
export const HEAD_UNIT = HEIGHT / 7; // 0.25

export const PALETTE = {
  skin: new Color('#9DA66B'),
  skinShadow: new Color('#6F7A4A'),
  skinLight: new Color('#B8BE86'),
  wound: new Color('#7A2E22'),
  woundDark: new Color('#4A1A14'),
  mouth: new Color('#3A1712'),
  shirt: new Color('#C9B492'),
  shirtDirt: new Color('#8E6F4E'),
  undershirt: new Color('#4B4A48'),
  pants: new Color('#6B5640'),
  pantsDark: new Color('#4F3F2F'),
  belt: new Color('#4A3526'),
  buckle: new Color('#8A8A86'),
  boot: new Color('#5E4430'),
  bootSole: new Color('#3B2A1E'),
  hair: new Color('#2B2A2A'),
  eye: new Color('#E4E0C8'),
  pupil: new Color('#2A2620'),
  teeth: new Color('#D8CBA0'),
  nail: new Color('#5A4A36'),
};

export const SIDES = { torso: 8, neck: 6, head: 8, arm: 6, leg: 6, finger: 4, shirt: 14, sleeve: 10, pants: 12, pantLeg: 10, boot: 8 };

/** Brightness jitter per face, ±fraction. */
export const FACE_JITTER = 0.045;
/** Vertex jitter along the ring normal, fraction of local radius. */
export const VERTEX_JITTER = 0.05;
