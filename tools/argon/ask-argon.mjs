// Full request: docs + engine API -> whole zombie.ts. Usage: node ask-argon.mjs <projectRoot> <out.ts> [model] [prevCode feedback.md images...]; NOIMG=1 sends feedback as text only.
import { readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

const root = process.argv[2];
const out = process.argv[3];
const model = process.argv[4] ?? 'gemini-4-argon';
const prev = process.argv[5]; // previous code file
const fb = process.argv[6]; // feedback file
const imgs = process.argv.slice(7); // png paths
const rd = (p) => readFileSync(join(root, p), 'utf8');

const system = `You are an expert procedural 3D modeller writing TypeScript for three.js 0.169.
You write ONE complete, compilable TypeScript module and nothing else. No explanations outside the code block.`;

const user = `Task: write the file \`src/zombie/argon/zombie.ts\` that procedurally builds a SEMI-REALISTIC HORROR ZOMBIE
(pale rotting skin, skull-like face with deep eye sockets, hollow cheeks, lipless mouth with exposed yellow teeth,
hinged jaw, milky eyes; open leather jacket with collar, V-neck t-shirt with blood, long trousers with belt, leather shoes,
five-finger hands with nails). Adult male, 1.82 m, T-pose bind.

It must export exactly:
\`\`\`ts
export function buildArgon(seed: number): { skel: Skel; mb: MeshBuilder; geometry: BufferGeometry; material: Material[] }
\`\`\`
Implementation contract:
- const skel = buildSkeleton(REAL_BONE_DEFS); const mb = new MeshBuilder(seed, true);
- Build every body part with the helpers below (loft, smoothStations, weigher, rigid, ellipsoid, box), switching material bucket with mb.use(name).
  Allowed bucket names: 'skin','eye','teeth','shirt','jacket','pants','leather','metal'.
- Finish with: const { geometry, materials } = mb.geometry(); const material = materials.map((n) => realMaterial(n)); return { skel, mb, geometry, material };
- The mesh is skinned to the skeleton; poses rotate bones named in REAL_BONE_DEFS, so weights must use those bones (Jaw for the lower jaw, finger bones for fingers, etc).
- Use makeVariant(seed) / skinAt / clothAt / bloodRun from variant.ts for colours.
- Aim for 12k-20k triangles. Parts may overlap at joints (no gaps).
- Imports (paths relative to src/zombie/argon/zombie.ts):
  import { BufferGeometry, Color, Material, Quaternion, Vector3 } from 'three';
  import { hash } from '../hash'; import { fbm, gauss } from '../noise';
  import { MeshBuilder, loft, smoothStations, weigher, rigid, ellipsoid, box, fromFrontSigned, type Station, type Weigher } from '../mesh';
  import { buildSkeleton, type Skel } from '../skeleton'; import { REAL_BONE_DEFS, REAL_HEAD_Y } from '../skeletonReal';
  import { makeVariant, skinAt, clothAt, bloodRun, type RCtx } from '../real/variant'; import { realMaterial } from '../real/materials';
- TypeScript strict mode. Only use the APIs shown below.

=== BUILD PROCESS (follow this method, it describes how the reference model was made) ===
${rd('docs/07-proses-pembuatan.md')}

=== ENGINE API: src/zombie/mesh.ts ===
\`\`\`ts
${rd('src/zombie/mesh.ts')}
\`\`\`

=== src/zombie/skeletonReal.ts ===
\`\`\`ts
${rd('src/zombie/skeletonReal.ts')}
\`\`\`

=== src/zombie/skeleton.ts (types + buildSkeleton) ===
\`\`\`ts
${rd('src/zombie/skeleton.ts').split('export const BONE_DEFS')[0]}
${'export interface Skel' + rd('src/zombie/skeleton.ts').split('export interface Skel')[1]}
\`\`\`

=== src/zombie/real/variant.ts ===
\`\`\`ts
${rd('src/zombie/real/variant.ts')}
\`\`\`

=== src/zombie/noise.ts and hash.ts ===
\`\`\`ts
${rd('src/zombie/noise.ts')}
${rd('src/zombie/hash.ts')}
\`\`\`

Return the full file in a single \`\`\`ts code block.`;

const messages = [{ role: 'system', content: system }, { role: 'user', content: user }];
if (prev) {
  messages.push({ role: 'assistant', content: '```ts\n' + readFileSync(prev, 'utf8') + '\n```' });
  const parts = [{ type: 'text', text: readFileSync(fb, 'utf8') }];
  for (const p of imgs) parts.push({ type: 'image_url', image_url: { url: 'data:image/png;base64,' + readFileSync(p).toString('base64') } });
  messages.push({ role: 'user', content: process.env.NOIMG ? parts[0].text : parts });
}
const t0 = Date.now();
const res = await fetch('http://127.0.0.1:8081/v1/chat/completions', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json', Authorization: 'Bearer sk-local' },
  body: JSON.stringify({ model, messages, stream: false }),
});
const txt = await res.text();
writeFileSync(out + '.raw.json', txt);
console.log('status', res.status, 'secs', ((Date.now() - t0) / 1000).toFixed(0), 'prompt chars', user.length);
let content = '';
try { content = JSON.parse(txt).choices[0].message.content; } catch { console.log(txt.slice(0, 800)); process.exit(1); }
const m = content.match(/```(?:ts|typescript)?\n([\s\S]*?)```/);
writeFileSync(out, m ? m[1] : content);
console.log('chars', content.length, 'codeblock', !!m);
