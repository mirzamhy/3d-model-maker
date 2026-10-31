# 04 — Matematika

Notasi: huruf tebal kecil = vektor (**p**), huruf besar = matriks (M), q = quaternion. Semua sudut radian di kode.

## 1. Transformasi hierarkis (forward kinematics)

Setiap tulang j punya matriks lokal L_j = T(**t**) · R(q) · S(**s**). Matriks world:

```
W_root = L_root
W_j    = W_parent(j) · L_j
```

Posisi world tulang = kolom translasi W_j. Three.js menghitung ini di `updateMatrixWorld()`. Urutan perkalian penting: induk di kiri.

## 2. Quaternion

Rotasi sudut θ di sumbu satuan **u**:

```
q = (cos θ/2,  u · sin θ/2)
```

- Gabung rotasi: q = q₂ ⊗ q₁ (q₁ dulu).
- Interpolasi pose: **slerp** (Shoemake, 1985):
  ```
  slerp(q₀, q₁, t) = q₀ (q₀⁻¹ q₁)^t
  ```
  Jika dot(q₀,q₁) < 0, balik tanda q₁ supaya lewat jalur terpendek.
- Kenapa bukan Euler: Euler kena gimbal lock dan interpolasinya tidak lurus.

## 3. Swing–twist decomposition

Untuk membatasi/membagi puntiran (twist) di sekitar sumbu tulang **a**:

```
r = (q.x, q.y, q.z)
p = (r · a) a                     proyeksi bagian vektor ke sumbu
twist = normalize(q.w, p)
swing = q ⊗ twist⁻¹
```

Dipakai untuk: memindahkan 50% twist pergelangan ke lengan bawah (cegah candy-wrapper), dan batas sendi (lutut hanya boleh tekuk di satu sumbu).

## 4. Linear Blend Skinning (LBS)

Rumus dasar skinning (Magnenat-Thalmann dkk., 1988; dirumuskan ulang Lewis dkk., 2000):

```
v' = Σ_i  w_i · W_i · B_i⁻¹ · v          dengan Σ w_i = 1, w_i ≥ 0
```

- v = posisi vertex di bind pose (homogen, w=1)
- W_i = matriks world tulang i sekarang
- B_i⁻¹ = inverse bind matrix tulang i
- Normal: pakai bagian 3×3 yang sama (cukup untuk rotasi tanpa skala non-uniform).

Inilah yang dijalankan shader `SkinnedMesh` Three.js dan dijelaskan di spesifikasi glTF 2.0 (bagian *Skins*).

Kelemahan: mencampur matriks secara linear → saat dua tulang berbeda puntiran 180°, campurannya mendekati matriks singular → volume kempes ("candy-wrapper").

## 5. Dual Quaternion Skinning (DQS)

Kavan dkk. (2007, 2008): ubah tiap transform rigid jadi dual quaternion q̂ = q_r + ε q_d, dengan q_d = ½ **t** q_r. Campur:

```
b̂ = Σ w_i q̂_i   (balik tanda q̂_i jika dot(q_r,i , q_r,0) < 0)
ĉ = b̂ / ‖b_r‖
```

Lalu terapkan ĉ ke vertex. Hasil: tidak kempes di puntiran. Three.js tidak punya DQS bawaan; kalau dibutuhkan, ganti chunk shader `skinning_vertex`. Untuk zombie low-poly kurus, **LBS + cincin ekstra di sendi + pembagian twist** biasanya cukup. DQS opsional.

## 6. Inverse kinematics 2 tulang (analitik)

Rantai akar → tengah (panjang a) → ujung (panjang b), target jarak d dari akar:

```
d  = clamp(|target − akar|, |a − b| + ε, a + b − ε)
cos α = (a² + d² − b²) / (2 a d)            sudut di akar (hukum kosinus)
cos β = (a² + b² − d²) / (2 a b)            sudut di sendi tengah
```

Arah tekuk ditentukan pole vector **p**: proyeksikan (p − akar) ke bidang tegak lurus arah akar→target, normalisasi → **n**. Posisi sendi tengah:

```
mid = akar + â · a·cos α + n · a·sin α          â = arah akar→target
```

Sudah diimplementasi di `game/src/render/rig.ts → solveTwoBone`.

## 7. IK rantai panjang (FABRIK)

Untuk tulang belakang + leher menunduk ke korban (Aristidou & Lasenby, 2011). Per iterasi:

```
maju:   p_n = target;  untuk i = n−1..0:  p_i = p_{i+1} + L_i · normalize(p_i − p_{i+1})
mundur: p_0 = akar;    untuk i = 1..n:    p_i = p_{i−1} + L_{i−1} · normalize(p_i − p_{i−1})
ulang sampai |p_n − target| < toleransi (biasanya 3–10 iterasi)
```

Setelah posisi didapat, rotasi tiap tulang = rotasi terpendek dari arah lama ke arah baru (`Quaternion.setFromUnitVectors`). Three.js juga punya `CCDIKSolver` (alternatif).

## 8. Noise deterministik

Semua variasi dari satu seed. Hash integer sederhana (cepat, cukup untuk jitter):

```ts
function hash(seed: number, i: number): number {      // hasil 0..1
  let h = (seed ^ Math.imul(i, 0x9e3779b1)) >>> 0;
  h = Math.imul(h ^ (h >>> 16), 0x85ebca6b);
  h = Math.imul(h ^ (h >>> 13), 0xc2b2ae35);
  return ((h ^ (h >>> 16)) >>> 0) / 4294967296;
}
```

Untuk variasi halus (misal noda yang menyebar) pakai value/gradient noise (Perlin, 2002) dengan input posisi vertex.

## 9. Normal per face (flat shading)

```
n = normalize((b − a) × (c − a))
```

Urutan vertex segitiga **berlawanan jarum jam** dilihat dari luar (konvensi Three.js/glTF), kalau tidak face akan terbalik dan hilang karena backface culling.

## 10. Jalan menyeret (zombie shuffle)

Fase φ = 2π · f · t, f ≈ 0.8 Hz (lambat). Kaki kiri φ, kanan φ + π.

```
langkah maju kaki:    z_foot = S/2 · sin φ                         S = panjang langkah 0.35 m
angkat kaki:          y_foot = h · max(0, sin φ)^1.5               h = 0.04 m (rendah = menyeret)
pincang:              kaki kanan h × 0.4 dan durasi menapak +20%
naik-turun panggul:   y_hips = y0 − 0.02 · |cos φ|
goyang samping:       x_hips = 0.03 · sin φ ;  roll badan = 4° · sin φ
lengan (pendulum):    θ_arm = 10° · sin(φ + π) − lag, tangan ikut 0.3 s terlambat via approach()
```

Kaki di-IK ke posisi foot di atas supaya tidak ngesot (no foot-skate). Kecepatan maju badan = S · f · 2 supaya telapak yang menapak diam relatif ke lantai.

Smoothing frame-rate independent (sudah di `rig.ts`):

```
x ← target + (x − target) · e^(−rate · dt)
```

## 11. Cek otomatis (dipakai di tes)

- Tinggi: `Box3.setFromObject(mesh).max.y − min.y`.
- Celah sambungan: untuk tiap pasangan cincin bersama, `max |ringA_k − ringB_k| < 0.01`.
- Bobot: `|Σw − 1| < 1e-4`, semua w ≥ 0.
- Sudut bungkuk: `atan2(head.z − hips.z, head.y − hips.y)` dalam derajat ∈ [12, 20].
