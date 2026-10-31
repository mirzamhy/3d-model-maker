// Short, single-turn request: rewrite one function. Usage: node ask-part.mjs <code.ts> <feedback.md> <out.ts> "function buildX" "function buildNext"
import { readFileSync, writeFileSync } from 'node:fs';

const [, , codeFile, fbFile, out] = process.argv;
const code = readFileSync(codeFile, 'utf8');
const [, , , , , START, END] = process.argv; const head = code.slice(code.indexOf(START), code.indexOf(END));
const fb = readFileSync(fbFile, 'utf8');

const api = `// API available (already imported in the file):
// const v = (x,y,z) => new Vector3(x,y,z); const HY = REAL_HEAD_Y; // 1.585, Head bone height
// interface Station { c: Vector3; rs: number /*side radius*/; rf: number /*front radius*/ }
// smoothStations(st: Station[], sub: number): Station[]            // Catmull-Rom resample
// loft(mb, st: Station[], { sides, front: Vector3, weigh, paint: {base: Color, rule?: (p)=>Color},
//        capStart?: 'flat'|'point'|'none', capEnd?: ..., shape?: (i, phi, c) => radialOffsetMetres })
//   ring point: p = c + rs*cos(phi)*S + rf*sin(phi)*F, phi = PI/2 is the front (+Z); S = +X side
// fromFrontSigned(phi): signed angle from the front in (-PI, PI]
// ellipsoid(mb, centre: Vector3, radii: Vector3, weigh, paint, detail = 1, q?: Quaternion)
// box(mb, centre, half: Vector3, weigh, paint, ax: Vector3, ay: Vector3, az: Vector3)   // oriented box
// rigid(skel, 'Head' | 'Jaw'): Weigher ; gauss(x, mu, sigma) ; hash(seed, i) in [0,1)
// skinAt(ctx, p, dark0to1, red0to1): Color ; mb.use('skin'|'eye'|'teeth')
// weigher(skel, ['LeftForeArm','LeftHand'], power = 4): Weigher   // inverse-distance to bone segments, top 4
// bloodRun(ctx, p, x0, width, yTop, yBottom): number 0..1 ; ctx.V.bloodDark, ctx.V.blood, ctx.V.bulk ; fbm(seed, x, y, z, freq, octaves=4) 0..1`;

const prompt = `${fb}

=== CURRENT ${START} (rewrite this) ===
\`\`\`ts
${head}
\`\`\`

${api}

Return ONLY the new \`${START}(ctx: RCtx) { ... }\` (plus any small helper functions it needs, defined above it) in one \`\`\`ts block. TypeScript strict.`;

const t0 = Date.now();
const res = await fetch('http://127.0.0.1:8081/v1/chat/completions', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json', Authorization: 'Bearer sk-local' },
  body: JSON.stringify({ model: 'gemini-4-argon', messages: [{ role: 'user', content: prompt }], stream: false }),
});
const j = await res.json();
const content = j.choices?.[0]?.message?.content ?? '';
const m = content.match(/```(?:ts|typescript)?\n([\s\S]*?)```/);
const newHead = m ? m[1] : '';
console.log('status', res.status, 'secs', ((Date.now() - t0) / 1000).toFixed(0), 'prompt chars', prompt.length, 'reply chars', content.length);
if (!newHead.includes(START)) { console.log(content.slice(0, 1500)); process.exit(1); }
writeFileSync(out, code.replace(head, newHead.trimEnd() + '\n\n'));
console.log('spliced ok');
