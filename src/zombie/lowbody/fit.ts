// F5: silhouette fit. Coordinate descent on the trunk width/depth multipliers (six heights) and the leg
// scales, maximising the mean IoU against the references of one group (silhouette.ts). Run from the page:
//   __zm.fitGroup('male')  ->  { start, end, front, side, t }   (paste t into FIT_MALE in body.ts)
// Pass `only` (a reference name) to fit a single reference instead: shows what the generator can reproduce.
import { buildLowBody, type FitTune } from './body';
import { bodySpec } from './bodySpec';
import { scoreBody } from './silhouette';

const ones = () => [1, 1, 1, 1, 1, 1];

function evaluate(group: 'male' | 'female', t: FitTune, only?: string) {
  const f = group === 'female' ? 1 : 0;
  const b = buildLowBody(1, f, t);
  const r = scoreBody(b.geometry.userData.lowTopo, b.skel.defs.map((d) => d.name), bodySpec(f).height, group, only);
  b.geometry.dispose();
  return { total: r.total, front: r.front, side: r.side, closed: b.check.closed };
}

export function fitGroup(group: 'male' | 'female', only?: string, passes = 5) {
  const t = { halfMul: ones(), frontMul: ones(), backMul: ones(), legW: 1, legD: 1 };
  let best = evaluate(group, t, only);
  const start = best.total;
  const keys = ['halfMul', 'frontMul', 'backMul'] as const;
  const params: Array<[string, number?]> = [...keys.flatMap((k) => [0, 1, 2, 3, 4, 5].map((i) => [k, i] as [string, number])), ['legW'], ['legD']];
  let step = 0.06;
  for (let pass = 0; pass < passes; pass++) {
    for (const [k, i] of params) {
      for (const d of [step, -step]) {
        const c = JSON.parse(JSON.stringify(t));
        if (i === undefined) c[k] += d; else c[k][i] += d;
        const v = i === undefined ? c[k] : c[k][i];
        if (!(v > 0.7 && v < 1.4)) continue;
        const r = evaluate(group, c, only);
        if (r.closed && r.total > best.total + 1e-5) {
          best = r;
          if (i === undefined) (t as Record<string, unknown>)[k] = c[k]; else (t as unknown as Record<string, number[]>)[k][i] = c[k][i];
        }
      }
    }
    step *= 0.65;
  }
  const round = (o: unknown): unknown => JSON.parse(JSON.stringify(o, (_, v) => (typeof v === 'number' ? Math.round(v * 1000) / 1000 : v)));
  return { start, end: best.total, front: best.front, side: best.side, t: round(t) };
}
