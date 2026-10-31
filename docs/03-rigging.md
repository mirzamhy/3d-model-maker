# 03 — Rigging

## 1. Konsep singkat

- **Skeleton**: pohon tulang (bone). Tiap tulang punya transform lokal (posisi, rotasi, skala) relatif ke induknya.
- **Bind pose (rest pose)**: pose saat mesh "diikat" ke tulang. Mesh dibuat di pose ini.
- **Inverse bind matrix** `B⁻¹`: matriks yang membawa vertex dari ruang model ke ruang lokal tulang saat bind pose. glTF menyimpannya di `skin.inverseBindMatrices`; Three.js di `skeleton.boneInverses`.
- **Skinning**: tiap vertex dipengaruhi ≤ 4 tulang dengan bobot `w`. Posisi akhir = campuran transform tulang-tulang itu (rumus di 04 §4).
- **Rigid binding** (cara DEADZONE lama: part ditempel ke 1 tulang) cepat tapi sendi patah. Untuk v2 pakai **skinning 2 tulang di zona sendi**.

## 2. Hierarki tulang

Nama mengikuti konvensi Mixamo supaya animasi/retarget dari tool lain cocok.

```
Hips                         (root; di 0.92 m, antara dua sendi panggul)
├─ Spine
│  └─ Spine1
│     └─ Spine2
│        ├─ Neck
│        │  └─ Head
│        │     ├─ Jaw
│        │     └─ HeadTop_End          (ujung, tanpa bobot)
│        ├─ LeftShoulder               (klavikula)
│        │  └─ LeftArm                 (bahu)
│        │     └─ LeftForeArm          (siku)
│        │        └─ LeftHand          (pergelangan)
│        │           ├─ LeftHandThumb1 → 2 → 3
│        │           ├─ LeftHandIndex1 → 2 → 3
│        │           ├─ LeftHandMiddle1 → 2 → 3 → LeftHandMiddle_End
│        │           └─ LeftHandPinky1 → 2 → 3     (jari manis digabung dgn kelingking)
│        └─ RightShoulder … (cermin)
├─ LeftUpLeg                   (panggul)
│  └─ LeftLeg                  (lutut)
│     └─ LeftFoot              (pergelangan kaki)
│        └─ LeftToeBase → LeftToe_End
└─ RightUpLeg … (cermin)
```

Total ±48 tulang (jari 3 ruas × 4 × 2 = 24). Kalau terlalu berat, jari jadi 2 ruas.

## 3. Bind pose

- Pakai **A-pose**: lengan turun ±45° dari horizontal, telapak menghadap ke bawah-dalam. A-pose memberi deformasi bahu lebih baik daripada T-pose untuk karakter yang kebanyakan lengannya turun.
- Badan tegak lurus (tanpa bungkuk). Bungkuk adalah **pose animasi** (01 §4), bukan bentuk mesh.
- Sumbu lokal tiap tulang: **+Y menunjuk ke anak** (sepanjang tulang), +Z ke depan, +X = Y × Z. Konsisten di kiri dan kanan supaya rotasi bisa dicerminkan dengan membalik tanda.
- Simpan bind pose sebagai data (`skeleton.ts`), bangun posisi world dengan forward kinematics, lalu panggil `skeleton.calculateInverses()` setelah semua tulang diposisikan.

## 4. Bobot (skin weights)

Langkah:

1. **Pemilik cincin.** Saat loft, tiap cincin dicatat `(tulangA, t)` dengan t = posisi sepanjang tulang 0..1.
2. **Zona sendi.** Di dekat sendi (t < 0.25 atau t > 0.75), campur dengan tulang tetangga:
   ```
   di ujung bawah tulang (t > 0.75): w_anak = smoothstep(0.75, 1.0, t) · 0.5
   di ujung atas tulang  (t < 0.25): w_induk = (1 − smoothstep(0.0, 0.25, t)) · 0.5
   w_sendiri = 1 − sisa
   ```
   Di tepat sendi (t=1 tulang A = t=0 tulang B) bobot 50/50.
3. **Bagian rigid** (gigi, mata, gesper, rambut): bobot 1 ke satu tulang (`Head`, `Jaw`, `Hips`).
4. **Pakaian** menyalin bobot dari vertex kulit terdekat (nearest-vertex transfer). Cara ini standar di Blender (*Data Transfer*) dan menjaga baju ikut kulit.
5. **Normalisasi**: ambil 4 bobot terbesar, bagi dengan jumlahnya (A3).
6. Tulis ke atribut `skinIndex` (Uint16×4) dan `skinWeight` (Float32×4).

Area sulit:

| Area | Masalah | Solusi |
|---|---|---|
| Bahu | Kempes saat lengan naik | Bobot 3 tulang: Spine2 0.2 / Shoulder 0.3 / Arm 0.5 di cincin pertama lengan |
| Siku / lutut | Candy-wrapper & kempes | Tambah 1 cincin ekstra tepat di sendi; atau pakai DQS (04 §5) |
| Pergelangan (twist) | Lengan bawah terpelintir seperti permen | Bagi twist: 50% rotasi twist Hand dipindah ke ForeArm (swing-twist, 04 §3) |
| Panggul / bokong | Robek saat kaki diangkat | Cincin atas paha: Hips 0.4 / UpLeg 0.6 |

Alternatif otomatis (untuk riset, tidak wajib): Bounded Biharmonic Weights (Jacobson dkk., 2011), Pinocchio (Baran & Popović, 2007), RigNet (Xu dkk., 2020). Lihat 06.

## 5. Kontrol (rig di atas skeleton)

| Kontrol | Fungsi | Metode |
|---|---|---|
| Kaki IK | Telapak tetap di lantai saat jalan | 2-bone IK analitik (04 §6) dengan pole = depan lutut |
| Tangan IK | Menerkam target (korban) | 2-bone IK, pole = belakang-bawah siku |
| Spine/Neck look-at | Kepala menoleh ke target | Bagi rotasi: Spine1 15%, Spine2 20%, Neck 30%, Head 35% |
| Jari curl | Satu nilai 0..1 → semua ruas | curl × [25°, 35°, 40°] per ruas |
| Jaw | Buka mulut 0..1 | Rotasi X 0..25° |

`rig.ts` di DEADZONE sudah punya `solveTwoBone` (law of cosines) dan `approach`. Pakai ulang.

## 6. Implementasi Three.js

```ts
const bones: Bone[] = defs.map(d => { const b = new Bone(); b.name = d.name; return b; });
defs.forEach((d, i) => d.parent >= 0 && bones[d.parent].add(bones[i]));
bones.forEach((b, i) => { b.position.copy(defs[i].localPos); b.quaternion.copy(defs[i].localRot); });

const mesh = new SkinnedMesh(geometry, material);
const skeleton = new Skeleton(bones);
mesh.add(bones[0]);
mesh.bind(skeleton);              // menghitung boneInverses dari pose saat ini
```

- `geometry` wajib punya atribut `skinIndex` & `skinWeight`.
- Debug: `new SkeletonHelper(mesh)`.
- Banyak zombie: satu geometry dibagi, skeleton per zombie (`SkeletonUtils.clone`). Jangan bangun ulang geometry per instance.
- Ekspor: `GLTFExporter` → `.glb`, cek di Blender (bobot terlihat di Weight Paint).
