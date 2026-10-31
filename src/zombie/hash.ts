/** Deterministic integer hash -> [0, 1). Same seed + index = same value. */
export function hash(seed: number, i: number): number {
  let h = (seed ^ Math.imul(i, 0x9e3779b1)) >>> 0;
  h = Math.imul(h ^ (h >>> 16), 0x85ebca6b);
  h = Math.imul(h ^ (h >>> 13), 0xc2b2ae35);
  return ((h ^ (h >>> 16)) >>> 0) / 4294967296;
}

/** Hash of a position (quantised to 0.1 mm) so duplicated vertices get the same value. */
export function hashPos(seed: number, x: number, y: number, z: number): number {
  const qx = Math.round(x * 10000);
  const qy = Math.round(y * 10000);
  const qz = Math.round(z * 10000);
  return hash(seed, Math.imul(qx, 73856093) ^ Math.imul(qy, 19349663) ^ Math.imul(qz, 83492791));
}

export const smoothstep = (a: number, b: number, x: number) => {
  const t = Math.min(1, Math.max(0, (x - a) / (b - a)));
  return t * t * (3 - 2 * t);
};
