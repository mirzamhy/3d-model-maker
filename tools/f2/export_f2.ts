// Dump the F2 low-poly body (src/zombie/lowbody/body.ts) to JSON for Blender: shared vertices, triangles,
// skin weights (bone index, weight) and the bone list (name, parent, head and tail in bind pose).
//   node_modules/.bin/esbuild tools/f2/export_f2.ts --bundle --platform=node --format=esm --outfile=tools/f2/out/export_f2.mjs
//   node tools/f2/out/export_f2.mjs 0 output/head-game/f2/f2_male.json      (femininity 0 = male, 1 = female)
import { writeFileSync, mkdirSync } from 'node:fs';
import { dirname } from 'node:path';
import { buildLowBody, type LowTopo } from '../../src/zombie/lowbody/body';

const fem = Number(process.argv[2] ?? 0);
const out = process.argv[3] ?? 'output/head-game/f2/f2_male.json';
const r = buildLowBody(1, fem);
const topo = r.geometry.userData.lowTopo as LowTopo;
const bones = r.skel.defs.map((d, i) => ({
  name: d.name,
  parent: d.parent ?? null,
  head: r.skel.seg[i][0].toArray(),
  tail: r.skel.seg[i][1].toArray(),
}));
mkdirSync(dirname(out), { recursive: true });
writeFileSync(out, JSON.stringify({
  femininity: fem,
  check: r.check,
  pos: topo.pos.map((p) => p.toArray().map((v) => Math.round(v * 1e6) / 1e6)),
  tris: topo.tris,
  weights: topo.weights,
  rings: topo.rings,
  bones,
}));
console.log('F2_EXPORT', out, 'verts', topo.pos.length, 'tris', topo.tris.length, 'bones', bones.length, JSON.stringify(r.check));
