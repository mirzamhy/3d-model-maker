// Small 3D value noise + fbm for vertex colouring (CPU side). Deterministic per seed.
import { hash } from './hash';

function lattice(seed: number, x: number, y: number, z: number) {
  return hash(seed, Math.imul(x, 73856093) ^ Math.imul(y, 19349663) ^ Math.imul(z, 83492791));
}

export function vnoise(seed: number, x: number, y: number, z: number) {
  const xi = Math.floor(x);
  const yi = Math.floor(y);
  const zi = Math.floor(z);
  const s = (t: number) => t * t * (3 - 2 * t);
  const fx = s(x - xi);
  const fy = s(y - yi);
  const fz = s(z - zi);
  const l = (a: number, b: number, t: number) => a + (b - a) * t;
  const c = (dx: number, dy: number, dz: number) => lattice(seed, xi + dx, yi + dy, zi + dz);
  return l(
    l(l(c(0, 0, 0), c(1, 0, 0), fx), l(c(0, 1, 0), c(1, 1, 0), fx), fy),
    l(l(c(0, 0, 1), c(1, 0, 1), fx), l(c(0, 1, 1), c(1, 1, 1), fx), fy),
    fz,
  );
}

/** Fractal noise in [0, 1). `f` = base frequency in cycles per metre. */
export function fbm(seed: number, x: number, y: number, z: number, f: number, octaves = 4) {
  let a = 0.5;
  let sum = 0;
  let norm = 0;
  for (let i = 0; i < octaves; i++) {
    sum += a * vnoise(seed + i * 101, x * f, y * f, z * f);
    norm += a;
    f *= 2.03;
    a *= 0.5;
  }
  return sum / norm;
}

export const gauss = (x: number, mu: number, s: number) => {
  const d = (x - mu) / s;
  return Math.exp(-d * d);
};
