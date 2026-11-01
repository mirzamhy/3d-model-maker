import { Bone, DoubleSide, Group, type Material, MeshStandardMaterial, Skeleton, SkinnedMesh, Vector3 } from 'three';
import { hash } from './hash';
import { MeshBuilder, type Wound } from './mesh';
import { arm, leg, torso } from './parts/body';
import { boots, pants, shirt } from './parts/clothes';
import type { Ctx } from './parts/ctx';
import { head } from './parts/head';
import { realHand, realNeckChest } from './real/body';
import { realJacket, realPants, realShirt, realShoes } from './real/clothes';
import { realHead } from './real/head';
import { buildArgon } from './argon/zombie';
import { buildZombie2 } from './argon/zombie2';
import { buildImported, hasImport } from './import/importMesh';
import { buildLowRig } from './lowbody/mannequin';
import { buildLowBody } from './lowbody/body';
import type { Shape } from './lowbody/bodySpec';
import { realMaterial } from './real/materials';
import { makeVariant, type RCtx } from './real/variant';
import { BONE_DEFS, buildSkeleton } from './skeleton';
import { REAL_BONE_DEFS } from './skeletonReal';

export type Style = 'real' | 'lowpoly' | 'argon' | 'zombie2' | 'lowrig' | 'lowbody' | 'import';

export interface Rig {
  root: Group;
  mesh: SkinnedMesh;
  skeleton: Skeleton;
  bones: Record<string, Bone>;
  /** Bind-pose local position per bone. */
  bindLocal: Record<string, Vector3>;
  /** Bind-pose world (model) position per bone. */
  bindWorld: Record<string, Vector3>;
  seed: number;
  style: Style;
  stats: { triangles: number; bones: number; height: number };
  /** 0 = male, 1 = female (low-poly base bodies). */
  femininity?: number;
}

const v = (x: number, y: number, z: number) => new Vector3(x, y, z);

function wounds(seed: number, list: Array<[number, number, number, number]>): Wound[] {
  return list.map(([x, y, z, r], i) => ({
    c: v(x + (hash(seed, 300 + i) - 0.5) * 0.03, y + (hash(seed, 320 + i) - 0.5) * 0.03, z),
    r: r * (0.8 + 0.4 * hash(seed, 340 + i)),
  }));
}

function buildLowpoly(seed: number) {
  const skel = buildSkeleton(BONE_DEFS);
  const mb = new MeshBuilder(seed, false);
  const ctx: Ctx = {
    mb,
    skel,
    seed,
    skinWounds: wounds(seed, [
      [-0.035, 1.7, 0.085, 0.035],
      [-0.06, 1.61, 0.075, 0.018],
      [0.05, 1.08, 0.085, 0.03],
      [0.4, 1.395, 0.02, 0.035],
      [-0.64, 1.375, 0.01, 0.045],
      [0.56, 1.37, -0.02, 0.03],
      [0.11, 0.35, 0.045, 0.04],
      [-0.11, 0.58, 0.05, 0.035],
      [-0.11, 0.43, -0.04, 0.03],
    ]),
    shirtStains: wounds(seed + 1, [
      [0.12, 1.3, 0.1, 0.05],
      [-0.15, 1.2, 0.08, 0.045],
      [0.06, 1.24, -0.12, 0.055],
      [-0.1, 1.06, -0.11, 0.05],
      [0.17, 1.02, 0.03, 0.04],
      [-0.27, 1.38, 0.05, 0.03],
    ]),
    pantsStains: wounds(seed + 2, [
      [-0.12, 0.8, 0.09, 0.05],
      [0.1, 0.72, 0.08, 0.035],
      [0.05, 0.95, -0.11, 0.04],
    ]),
  };
  torso(ctx);
  head(ctx);
  arm(ctx, 1);
  arm(ctx, -1);
  leg(ctx, 1);
  leg(ctx, -1);
  shirt(ctx);
  pants(ctx);
  boots(ctx);
  const { geometry } = mb.geometry();
  const material: Material = new MeshStandardMaterial({ vertexColors: true, flatShading: true, roughness: 0.92, metalness: 0, side: DoubleSide });
  return { skel, mb, geometry, material };
}

function buildReal(seed: number) {
  const skel = buildSkeleton(REAL_BONE_DEFS);
  const mb = new MeshBuilder(seed, true);
  const ctx: RCtx = { mb, skel, seed, V: makeVariant(seed) };
  realNeckChest(ctx);
  realHead(ctx);
  realHand(ctx, 1);
  realHand(ctx, -1);
  realShirt(ctx);
  realJacket(ctx);
  realPants(ctx);
  realShoes(ctx);
  const { geometry, materials } = mb.geometry();
  const material = materials.map((n) => realMaterial(n));
  return { skel, mb, geometry, material };
}

export function buildZombie(seed = 1, style: Style = 'real', opts: { femininity?: number; shape?: Shape } = {}): Rig {
  const built: { skel: ReturnType<typeof buildSkeleton>; mb: { triangles: number }; geometry: import('three').BufferGeometry; material: Material | Material[]; extras?: import('three').Object3D[] } =
    style === 'lowrig' ? buildLowRig(seed, opts.femininity ?? 0, opts.shape) : style === 'lowbody' ? buildLowBody(seed, opts.femininity ?? 0, undefined, opts.shape) : style === 'import' && hasImport() ? buildImported() : style === 'argon' ? buildArgon(seed) : style === 'zombie2' ? buildZombie2(seed) : style === 'lowpoly' ? buildLowpoly(seed) : buildReal(seed);
  const { skel, mb, geometry, material } = built;
  const mesh = new SkinnedMesh(geometry, material);
  mesh.castShadow = true;
  mesh.receiveShadow = style !== 'lowpoly' && style !== 'lowrig' && style !== 'lowbody';
  mesh.frustumCulled = false;
  mesh.name = `zombie_${style}_${seed}`;
  mesh.add(skel.bones[0]);
  mesh.bind(new Skeleton(skel.bones));

  const root = new Group();
  root.add(mesh);
  for (const e of built.extras ?? []) root.add(e);
  const scale = style === 'lowrig' || style === 'lowbody' ? 1 : 1 + (hash(seed, 1) - 0.5) * 0.08;
  root.scale.setScalar(scale);

  const bones: Record<string, Bone> = {};
  const bindLocal: Record<string, Vector3> = {};
  const bindWorld: Record<string, Vector3> = {};
  skel.defs.forEach((d, i) => {
    bones[d.name] = skel.bones[i];
    bindLocal[d.name] = skel.bones[i].position.clone();
    bindWorld[d.name] = d.p.clone();
  });

  return {
    root,
    mesh,
    skeleton: mesh.skeleton,
    bones,
    bindLocal,
    bindWorld,
    seed,
    style,
    femininity: opts.femininity,
    stats: { triangles: mb.triangles, bones: skel.bones.length, height: (geometry.boundingBox!.max.y - geometry.boundingBox!.min.y) * scale },
  };
}

/** Set opacity / depth-write on every material of a rig (X-ray toggle). */
export function setXray(r: Rig, on: boolean) {
  const mats = Array.isArray(r.mesh.material) ? r.mesh.material : [r.mesh.material];
  for (const m of mats) {
    if (m.transparent !== on) {
      m.transparent = on;
      m.needsUpdate = true;
    }
    m.opacity = on ? 0.5 : 1;
    m.depthWrite = !on;
  }
}
