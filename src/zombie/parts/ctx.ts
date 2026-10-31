import type { MeshBuilder, Wound } from '../mesh';
import type { Skel } from '../skeleton';

export interface Ctx {
  mb: MeshBuilder;
  skel: Skel;
  seed: number;
  skinWounds: Wound[];
  shirtStains: Wound[];
  pantsStains: Wound[];
}
