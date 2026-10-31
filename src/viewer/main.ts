import {
  ACESFilmicToneMapping,
  AmbientLight,
  Color,
  DirectionalLight,
  FogExp2,
  HemisphereLight,
  Mesh,
  MeshStandardMaterial,
  OrthographicCamera,
  PCFSoftShadowMap,
  PerspectiveCamera,
  PlaneGeometry,
  Scene,
  ShadowMaterial,
  SpotLight,
  SRGBColorSpace,
  Vector3,
  WebGLRenderer,
} from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { GLTFExporter } from 'three/examples/jsm/exporters/GLTFExporter.js';
import { buildZombie, setXray, type Rig, type Style } from '../zombie/build';
import { applyPose, POSES, type PoseName } from '../zombie/pose';
import { fittedBounds, getImportName, getImportOpts, hasImport, lastReport, loadGlb, setImportOpts } from '../zombie/import/importMesh';
import { RigOverlay } from './overlay';

type View = 'depan' | 'kiri' | 'belakang' | 'kanan' | 'bebas' | 'wajah' | '4 view' | 'gerombolan';
type SceneMode = 'horor' | 'studio';
const VIEWS: View[] = ['depan', 'kiri', 'belakang', 'kanan', 'bebas', 'wajah', '4 view', 'gerombolan'];
const POSE_LABEL: Record<PoseName, string> = {
  tpose: 'T-pose',
  idle: 'Idle bungkuk',
  walk: 'Jalan',
  reach: 'Meraih',
  attack: 'Menyerang',
  lunge: 'Menerkam',
  roar: 'Meraung',
  crawl: 'Merayap',
  sit: 'Duduk',
};
const STYLE_LABEL: Record<Style, string> = { real: 'Semi-realistis', lowpoly: 'Low-poly', argon: 'Argon (Gemini)', import: 'Impor GLB' };
const SCENE_LABEL: Record<SceneMode, string> = { horor: 'Horor', studio: 'Studio' };

const state = {
  seed: 7,
  style: 'real' as Style,
  scene: 'horor' as SceneMode,
  pose: 'lunge' as PoseName,
  view: 'bebas' as View,
  rig: false,
  labels: true,
  xray: false,
  spin: false,
};

const stage = document.getElementById('stage')!;
const labelHost = document.getElementById('labels')!;
const renderer = new WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(Math.min(2, window.devicePixelRatio));
renderer.outputColorSpace = SRGBColorSpace;
renderer.toneMapping = ACESFilmicToneMapping;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = PCFSoftShadowMap;
stage.prepend(renderer.domElement);

// ---------- scene + two lighting setups ----------
const scene = new Scene();
const studio = {
  hemi: new HemisphereLight('#dfe6ee', '#4a4d52', 1.1),
  amb: new AmbientLight('#ffffff', 0.25),
  key: new DirectionalLight('#ffffff', 2.2),
  rim: new DirectionalLight('#cfd8ff', 0.6),
  floor: new Mesh(new PlaneGeometry(30, 30), new ShadowMaterial({ opacity: 0.28 })),
};
studio.key.position.set(2.2, 4, 3.2);
studio.rim.position.set(-3, 2.5, -2.5);

const horror = {
  hemi: new HemisphereLight('#5b7566', '#050605', 0.55),
  key: new SpotLight('#f2e4cc', 42, 14, 0.55, 0.65, 1.6),
  rim: new DirectionalLight('#7ee0bd', 1.6),
  back: new DirectionalLight('#9fb4ff', 0.35),
  floor: new Mesh(new PlaneGeometry(30, 30), new MeshStandardMaterial({ color: '#151a17', roughness: 0.92 })),
};
horror.key.position.set(1.6, 4.2, 3.6);
horror.key.target.position.set(0, 0.8, 0);
horror.rim.position.set(-2.5, 2.8, -3);
horror.back.position.set(2.5, 1.5, -3);

for (const l of [studio.key, horror.key]) {
  l.castShadow = true;
  l.shadow.mapSize.set(2048, 2048);
  l.shadow.bias = -0.0004;
}
studio.key.shadow.camera.left = -3;
studio.key.shadow.camera.right = 3;
studio.key.shadow.camera.top = 3;
studio.key.shadow.camera.bottom = -1;
for (const f of [studio.floor, horror.floor]) {
  f.rotation.x = -Math.PI / 2;
  f.receiveShadow = true;
}
scene.add(...Object.values(studio), ...Object.values(horror), horror.key.target);

function applyScene() {
  const h = state.scene === 'horor';
  Object.values(studio).forEach((o) => (o.visible = !h));
  Object.values(horror).forEach((o) => (o.visible = h));
  scene.background = new Color(h ? '#0c110f' : '#5b6067');
  scene.fog = h ? new FogExp2('#0c110f', 0.075) : null;
  renderer.toneMappingExposure = h ? 1.15 : 1.05;
  document.body.dataset.scene = state.scene;
}

const persp = new PerspectiveCamera(30, 1, 0.05, 60);
const ortho = new OrthographicCamera(-1, 1, 1, -1, 0.05, 60);
const controls = new OrbitControls(persp, renderer.domElement);
controls.target.set(0, 0.92, 0);
controls.enableDamping = true;

interface Actor {
  rig: Rig;
  pose?: PoseName;
  t0: number;
}
let actors: Actor[] = [];
let overlay: RigOverlay | null = null;

const HORDE: Array<{ x: number; z: number; ry: number; pose: PoseName; seed: number }> = [
  { x: -1.25, z: -0.9, ry: 0.35, pose: 'walk', seed: 3 },
  { x: -0.45, z: 0.15, ry: 0.15, pose: 'lunge', seed: 0 },
  { x: 0.55, z: -0.6, ry: -0.2, pose: 'reach', seed: 11 },
  { x: 1.35, z: 0.25, ry: -0.35, pose: 'roar', seed: 5 },
  { x: 0.25, z: 1.05, ry: -0.6, pose: 'crawl', seed: 21 },
];

function rebuild() {
  for (const a of actors) {
    scene.remove(a.rig.root);
    a.rig.mesh.geometry.dispose();
  }
  overlay?.dispose();
  if (overlay) scene.remove(overlay.group);
  overlay = null;
  const build = (seed: number) => buildZombie(seed, state.style);
  if (state.view === '4 view') {
    actors = [0, 1, 2, 3].map((i) => {
      const rig = build(state.seed);
      rig.root.position.x = (i - 1.5) * 0.95;
      rig.root.rotation.y = [0, Math.PI / 2, Math.PI, -Math.PI / 2][i];
      return { rig, t0: 0 };
    });
  } else if (state.view === 'gerombolan') {
    actors = HORDE.map((h, i) => {
      const rig = build(state.seed + h.seed);
      rig.root.position.set(h.x, 0, h.z);
      rig.root.rotation.y = h.ry;
      return { rig, pose: h.pose, t0: i * 0.7 };
    });
  } else {
    actors = [{ rig: build(state.seed), t0: 0 }];
    overlay = new RigOverlay(actors[0].rig, labelHost);
    scene.add(overlay.group);
  }
  for (const a of actors) scene.add(a.rig.root);
  setView(state.view);
  updateStats();
}

function setView(v: View) {
  const target = new Vector3(0, 0.92, 0);
  const at = (dir: Vector3, d: number) => {
    controls.target.copy(target);
    persp.position.copy(dir.normalize()).multiplyScalar(d).add(target);
    controls.update();
  };
  if (v === '4 view') return;
  if (v === 'gerombolan') return at(new Vector3(0.05, 0.12, 1), 6.4);
  if (v === 'wajah') {
    // follow the head wherever the pose put it
    const head = actors[0]?.rig.bones.Head;
    if (head) {
      actors[0].rig.root.updateMatrixWorld(true);
      head.getWorldPosition(target);
      target.y += 0.1;
    }
    return at(new Vector3(0.45, 0.05, 1), 0.85);
  }
  const dirs: Record<string, Vector3> = {
    depan: new Vector3(0.16, 0.1, 1),
    kiri: new Vector3(1, 0.06, 0),
    belakang: new Vector3(0, 0.06, -1),
    kanan: new Vector3(-1, 0.06, 0),
    bebas: new Vector3(0.55, 0.12, 1),
  };
  at(dirs[v], 4.4);
}

function resize() {
  const w = stage.clientWidth;
  const h = stage.clientHeight;
  renderer.setSize(w, h, false);
  persp.aspect = w / h;
  persp.updateProjectionMatrix();
  // frustum is relative to the camera (centred on y = 0.92); fit 4 figures in width or 2.2 m in height
  const aspect = w / h;
  const halfW = Math.max(1.1 * aspect, 2.15);
  const halfH = halfW / aspect;
  ortho.top = halfH;
  ortho.bottom = -halfH;
  ortho.left = -halfW;
  ortho.right = halfW;
  ortho.position.set(0, 0.92, 10);
  ortho.lookAt(0, 0.92, 0);
  ortho.updateProjectionMatrix();
}

let t = 0;
function frame(dt: number) {
  t += dt;
  for (const a of actors) {
    applyPose(a.rig, a.pose ?? state.pose, t + a.t0);
    setXray(a.rig, state.xray);
  }
  if (state.spin && state.view !== '4 view') {
    const off = persp.position.clone().sub(controls.target);
    off.applyAxisAngle(new Vector3(0, 1, 0), dt * 0.5);
    persp.position.copy(controls.target).add(off);
  }
  controls.update();
  const cam = state.view === '4 view' ? ortho : persp;
  for (const a of actors) a.rig.root.updateMatrixWorld(true);
  if (overlay) {
    overlay.group.visible = state.rig;
    overlay.update(cam, stage.clientWidth, stage.clientHeight, state.rig && state.labels);
  }
  const title = document.getElementById('title')!;
  title.style.display = state.rig ? '' : 'none';
  renderer.render(scene, cam);
}

let last = performance.now();
function loop(now: number) {
  frame(Math.min(0.05, (now - last) / 1000));
  last = now;
  requestAnimationFrame(loop);
}

// ---------- UI ----------
function buttons(hostId: string, items: string[], label: (s: string) => string, get: () => string, set: (s: string) => void) {
  const host = document.getElementById(hostId)!;
  const render = () => host.querySelectorAll('button').forEach((b) => b.classList.toggle('on', b.dataset.k === get()));
  for (const k of items) {
    const b = document.createElement('button');
    b.textContent = label(k);
    b.dataset.k = k;
    b.onclick = () => {
      set(k);
      render();
    };
    host.appendChild(b);
  }
  render();
  return render;
}
const needsRebuild = (a: View, b: View) => (a === '4 view' || a === 'gerombolan' || b === '4 view' || b === 'gerombolan') && a !== b;
const syncStyle = buttons('styles', ['real', 'lowpoly', 'argon', 'import'], (k) => STYLE_LABEL[k as Style], () => state.style, (k) => {
  if (k === 'import' && !hasImport()) {
    glbFile.click();
    return;
  }
  state.style = k as Style;
  rebuild();
});
const syncScene = buttons('scenes', ['horor', 'studio'], (k) => SCENE_LABEL[k as SceneMode], () => state.scene, (k) => {
  state.scene = k as SceneMode;
  applyScene();
});
const syncPose = buttons('poses', POSES, (k) => POSE_LABEL[k as PoseName], () => state.pose, (k) => (state.pose = k as PoseName));
const syncView = buttons('views', VIEWS, (k) => k, () => state.view, (k) => {
  const prev = state.view;
  state.view = k as View;
  if (needsRebuild(prev, state.view)) rebuild();
  else setView(state.view);
});
const bind = (id: string, key: 'rig' | 'labels' | 'xray' | 'spin') => {
  const el = document.getElementById(id) as HTMLInputElement;
  el.checked = state[key];
  el.onchange = () => (state[key] = el.checked);
  return () => (el.checked = state[key]);
};
const syncChecks = [bind('rig', 'rig'), bind('labelsOn', 'labels'), bind('xray', 'xray'), bind('spin', 'spin')];
const seedEl = document.getElementById('seed') as HTMLInputElement;
seedEl.value = String(state.seed);
seedEl.onchange = () => {
  state.seed = Math.max(1, Number(seedEl.value) || 1);
  rebuild();
};
document.getElementById('rand')!.onclick = () => {
  state.seed = 1 + Math.floor(Math.random() * 9999);
  seedEl.value = String(state.seed);
  rebuild();
};
// ---------- import GLB ----------
const importInfo = document.getElementById('importInfo')!;
const num = (id: string) => document.getElementById(id) as HTMLInputElement;
function syncImportUi() {
  const o = getImportOpts();
  num('fitH').value = String(o.height);
  num('fitDy').value = String(o.dy);
  num('fitDz').value = String(o.dz);
  num('fitRy').value = String(o.rotY);
  num('fitRx').value = String(o.rotX);
  const r = lastReport();
  if (r) importInfo.innerHTML = `<b>${r.name}</b>: ${r.triangles.toLocaleString('id-ID')} segitiga, ${r.materials} material, bobot dihitung ${r.ms} ms${r.smoothed ? '' : ' (tanpa smoothing)'}`;
}
async function importGlb(data: ArrayBuffer | string, name: string) {
  importInfo.textContent = 'Memuat ' + name + '…';
  try {
    await loadGlb(data, name);
    state.style = 'import';
    rebuild();
    syncStyle();
    syncImportUi();
  } catch (e) {
    importInfo.textContent = 'Gagal: ' + (e as Error).message;
  }
}
const glbFile = document.getElementById('glbFile') as HTMLInputElement;
document.getElementById('glbLoad')!.onclick = () => glbFile.click();
glbFile.onchange = async () => {
  const f = glbFile.files?.[0];
  if (f) await importGlb(await f.arrayBuffer(), f.name);
  glbFile.value = '';
};
stage.addEventListener('dragover', (e) => e.preventDefault());
stage.addEventListener('drop', async (e) => {
  e.preventDefault();
  const f = e.dataTransfer?.files?.[0];
  if (f && /\.(glb|gltf)$/i.test(f.name)) await importGlb(await f.arrayBuffer(), f.name);
});
document.getElementById('fitApply')!.onclick = () => {
  setImportOpts({ height: Number(num('fitH').value) || 1.82, dy: Number(num('fitDy').value) || 0, dz: Number(num('fitDz').value) || 0, rotY: Number(num('fitRy').value) || 0, rotX: Number(num('fitRx').value) || 0 });
  if (state.style === 'import') rebuild();
  syncImportUi();
};

document.getElementById('png')!.onclick = () => capture(`zombie_${state.style}_${state.pose}_${state.view.replace(' ', '')}_s${state.seed}`);
document.getElementById('glb')!.onclick = () => exportGlb(`zombie_${state.style}_s${state.seed}`);

function updateStats() {
  const s = actors[0].rig.stats;
  document.getElementById('stats')!.innerHTML = `Segitiga: <b>${s.triangles.toLocaleString('id-ID')}</b><br>Tulang: <b>${s.bones}</b><br>Tinggi: <b>${s.height.toFixed(3)} m</b>`;
}

// ---------- save ----------
async function post(name: string, ext: 'png' | 'glb', data: string) {
  const res = await fetch('/__save', { method: 'POST', body: JSON.stringify({ name, ext, data }) });
  return res.ok;
}

/** Composite WebGL canvas + HTML labels + title into one PNG. */
async function capture(name: string) {
  frame(0);
  const src = renderer.domElement;
  const c = document.createElement('canvas');
  c.width = src.width;
  c.height = src.height;
  const g = c.getContext('2d')!;
  g.drawImage(src, 0, 0);
  if (state.rig) {
    const k = src.width / stage.clientWidth;
    const sr = stage.getBoundingClientRect();
    g.scale(k, k);
    for (const el of Array.from(labelHost.querySelectorAll<HTMLElement>('.rig-label'))) {
      if (el.style.display === 'none') continue;
      const r = el.getBoundingClientRect();
      const x = r.left - sr.left;
      const y = r.top - sr.top + r.height / 2;
      g.font = '600 11px Segoe UI, sans-serif';
      g.fillStyle = '#eef0f2';
      g.textBaseline = 'middle';
      g.fillText(el.textContent ?? '', x, y);
      g.strokeStyle = el.style.getPropertyValue('--c');
      g.lineWidth = 1.5;
      g.beginPath();
      if (el.dataset.side === 'u') {
        g.moveTo(x + r.width / 2, y + r.height / 2 + 4);
        g.lineTo(x + r.width / 2, y + r.height / 2 + 26);
      } else if (el.dataset.side === 'r') {
        g.moveTo(x - 6, y);
        g.lineTo(x - 28, y);
      } else {
        g.moveTo(x + r.width + 6, y);
        g.lineTo(x + r.width + 28, y);
      }
      g.stroke();
    }
    g.fillStyle = '#e4e6ea';
    g.font = '800 34px Segoe UI, sans-serif';
    g.textBaseline = 'top';
    g.fillText('ZOMBIE', 34, 16);
    g.font = '400 22px Segoe UI, sans-serif';
    g.fillText('RIG STRUCTURE', 34, 54);
  }
  return post(name, 'png', c.toDataURL('image/png'));
}

async function exportGlb(name: string) {
  const r = buildZombie(state.seed, state.style); // fresh copy in bind pose
  r.root.updateMatrixWorld(true);
  const buf = await new GLTFExporter().parseAsync(r.root, { binary: true });
  const bytes = new Uint8Array(buf as ArrayBuffer);
  let bin = '';
  for (let i = 0; i < bytes.length; i += 0x8000) bin += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
  r.mesh.geometry.dispose();
  return post(name, 'glb', btoa(bin));
}

// Debug/automation hook (the browser pane throttles rAF, so tools drive frames manually).
(window as unknown as { __zm: unknown }).__zm = {
  state,
  set(p: Partial<typeof state>) {
    const prevView = state.view;
    const rebuildNeeded = (p.seed !== undefined && p.seed !== state.seed) || (p.style !== undefined && p.style !== state.style) || (p.view !== undefined && needsRebuild(prevView, p.view));
    Object.assign(state, p);
    seedEl.value = String(state.seed);
    if (p.scene) applyScene();
    if (rebuildNeeded) rebuild();
    else if (p.view) setView(state.view);
    [syncStyle, syncScene, syncPose, syncView, ...syncChecks].forEach((f) => f());
    frame(0);
  },
  frame: (dt = 1 / 60) => frame(dt),
  setTime: (v: number) => {
    t = v;
    frame(0);
  },
  capture,
  exportGlb,
  loadGlb: async (url: string, opts?: Parameters<typeof setImportOpts>[0]) => {
    await importGlb(url, url.split('/').pop() ?? 'model.glb');
    if (opts) {
      setImportOpts(opts);
      rebuild();
      syncImportUi();
    }
    return { name: getImportName(), report: lastReport(), bounds: fittedBounds() };
  },
  stats: () => actors[0].rig.stats,
  actors: () => actors,
};

window.addEventListener('resize', resize);
resize();
applyScene();
rebuild();
requestAnimationFrame(loop);
