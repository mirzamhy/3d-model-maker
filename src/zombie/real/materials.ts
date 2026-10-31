// Materials for the semi-realistic style. Surface detail (pores, wrinkles, leather creases,
// cloth grain) is procedural: a 3D noise height field on the bind-pose position, turned into
// a bump by screen-space derivatives (same maths as three.js bump mapping, no textures/UVs).
import { Color, DoubleSide, MeshStandardMaterial, type Material } from 'three';

const NOISE = /* glsl */ `
varying vec3 vObj;
float zh(vec3 p){ p = fract(p * 0.3183099 + 0.1); p *= 17.0; return fract(p.x * p.y * p.z * (p.x + p.y + p.z)); }
float zn(vec3 x){
  vec3 i = floor(x); vec3 f = fract(x); f = f * f * (3.0 - 2.0 * f);
  return mix(mix(mix(zh(i), zh(i + vec3(1,0,0)), f.x), mix(zh(i + vec3(0,1,0)), zh(i + vec3(1,1,0)), f.x), f.y),
             mix(mix(zh(i + vec3(0,0,1)), zh(i + vec3(1,0,1)), f.x), mix(zh(i + vec3(0,1,1)), zh(i + vec3(1,1,1)), f.x), f.y), f.z);
}
float zfbm(vec3 p){ float a = 0.5, s = 0.0; for (int i = 0; i < 4; i++) { s += a * zn(p); p *= 2.03; a *= 0.5; } return s; }
vec3 zPerturb(vec3 surf_pos, vec3 surf_norm, vec2 dHdxy, float faceDir){
  vec3 vSigmaX = dFdx(surf_pos); vec3 vSigmaY = dFdy(surf_pos); vec3 vN = surf_norm;
  vec3 R1 = cross(vSigmaY, vN); vec3 R2 = cross(vN, vSigmaX);
  float fDet = dot(vSigmaX, R1) * faceDir;
  vec3 vGrad = sign(fDet) * (dHdxy.x * R1 + dHdxy.y * R2);
  return normalize(abs(fDet) * surf_norm - vGrad);
}
`;

interface Detail {
  /** Large-scale height: frequency (cycles/m), anisotropic scale, amplitude (m). */
  fA: number;
  sA: [number, number, number];
  aA: number;
  /** Ridged (creases) instead of soft bumps. */
  ridged?: boolean;
  /** Fine grain: frequency, amplitude (m). */
  fB: number;
  aB: number;
  /** Colour variation amount and frequency. */
  cv: number;
  fC: number;
}

const f = (x: number) => x.toFixed(5);

function withDetail(mat: MeshStandardMaterial, d: Detail) {
  mat.onBeforeCompile = (sh) => {
    sh.vertexShader = sh.vertexShader
      .replace('#include <common>', '#include <common>\nvarying vec3 vObj;')
      .replace('#include <begin_vertex>', '#include <begin_vertex>\nvObj = position;');
    const big = `zfbm(vObj * vec3(${f(d.fA * d.sA[0])}, ${f(d.fA * d.sA[1])}, ${f(d.fA * d.sA[2])}))`;
    const hBig = d.ridged ? `(1.0 - abs(2.0 * ${big} - 1.0))` : big;
    sh.fragmentShader = sh.fragmentShader
      .replace('#include <common>', `#include <common>\n${NOISE}`)
      .replace('#include <color_fragment>', `#include <color_fragment>\n  diffuseColor.rgb *= 1.0 + ${f(d.cv)} * (zfbm(vObj * ${f(d.fC)}) - 0.5);`)
      .replace(
        '#include <normal_fragment_maps>',
        `#include <normal_fragment_maps>
  {
    float hh = ${f(d.aA)} * ${hBig} + ${f(d.aB)} * zn(vObj * ${f(d.fB)});
    normal = zPerturb(-vViewPosition, normal, vec2(dFdx(hh), dFdy(hh)), faceDirection);
  }`,
      );
  };
  mat.customProgramCacheKey = () => JSON.stringify(d);
  return mat;
}

const std = (o: ConstructorParameters<typeof MeshStandardMaterial>[0]) => new MeshStandardMaterial({ vertexColors: true, side: DoubleSide, ...o });

export function realMaterial(name: string): Material {
  switch (name) {
    case 'skin':
      return withDetail(std({ roughness: 0.58, metalness: 0 }), { fA: 38, sA: [1, 1.4, 1], aA: 0.0011, fB: 420, aB: 0.00007, cv: 0.12, fC: 60 });
    case 'eye':
      return std({ roughness: 0.12, emissive: new Color('#c4d8dc'), emissiveIntensity: 0.28 });
    case 'teeth':
      return std({ roughness: 0.35 });
    case 'shirt':
      return withDetail(std({ roughness: 0.95 }), { fA: 14, sA: [1, 0.35, 1], aA: 0.0016, fB: 650, aB: 0.00004, cv: 0.1, fC: 30 });
    case 'jacket':
      return withDetail(std({ roughness: 0.48, metalness: 0.02 }), { fA: 22, sA: [1, 0.55, 1], aA: 0.0016, ridged: true, fB: 300, aB: 0.00006, cv: 0.18, fC: 18 });
    case 'pants':
      return withDetail(std({ roughness: 0.62 }), { fA: 18, sA: [1, 0.4, 1], aA: 0.0016, ridged: true, fB: 380, aB: 0.00005, cv: 0.16, fC: 20 });
    case 'leather':
      return withDetail(std({ roughness: 0.36 }), { fA: 40, sA: [1, 1, 1], aA: 0.0005, ridged: true, fB: 500, aB: 0.00003, cv: 0.1, fC: 30 });
    case 'metal':
      return std({ roughness: 0.32, metalness: 0.85 });
    default:
      return std({ roughness: 0.8 });
  }
}
