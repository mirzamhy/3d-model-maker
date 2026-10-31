# 05 — Struktur File dan Alur Kerja

## 1. Struktur kode

```
tiktok/
├─ docs/zombie-model/              ← brief ini
│  ├─ README.md
│  ├─ PRD.md
│  ├─ 01-anatomi-proporsi.md
│  ├─ 02-struktur-mesh.md
│  ├─ 03-rigging.md
│  ├─ 04-matematika.md
│  ├─ 05-struktur-file-dan-alur.md
│  ├─ 06-sumber.md
│  └─ ref/
│     ├─ referensi-4-view.webp
│     ├─ hasil-gemini-v1.png
│     └─ v2/                       ← screenshot hasil tiap fase (front/left/back/right.png)
│
├─ game/src/render/
│  ├─ rig.ts                       ← SUDAH ADA: math murni (IK 2 tulang, approach, angleDelta)
│  └─ zombie/
│     ├─ spec.ts                   ← SEMUA angka: proporsi, radius, palet, budget. Data saja.
│     ├─ skeleton.ts               ← daftar tulang (nama, induk, posisi bind), buildSkeleton()
│     ├─ math/
│     │  ├─ hash.ts                ← hash(seed,i), rng per seed
│     │  ├─ quat.ts                ← swing-twist, slerp helper
│     │  └─ fabrik.ts              ← FABRIK untuk spine/neck
│     ├─ mesh/
│     │  ├─ loft.ts                ← ring(), loft(cincin[]) → posisi + index + pemilik cincin
│     │  ├─ hem.ts                 ← tepi sobek bergerigi
│     │  ├─ facet.ts               ← jitter, toNonIndexed, warna per face, luka
│     │  └─ merge.ts               ← gabung layer jadi satu BufferGeometry
│     ├─ parts/
│     │  ├─ head.ts                ← kepala, rahang, gigi, mata, rambut
│     │  ├─ torso.ts               ← torso + leher
│     │  ├─ arms.ts                ← lengan + tangan + jari
│     │  ├─ legs.ts                ← paha + betis
│     │  └─ clothes.ts             ← kemeja, celana, ikat pinggang, bot
│     ├─ skin.ts                   ← hitung skinIndex/skinWeight, transfer ke baju, normalisasi
│     ├─ build.ts                  ← buildZombie(seed) → { mesh, skeleton, bones }
│     ├─ pose.ts                   ← applyHunch(), idle(), walk(), attack(), death()
│     └─ index.ts                  ← export publik
│
├─ scripts/
│  ├─ export-zombie-glb.ts         ← tulis zombie.glb untuk dicek di Blender
│  └─ zombie-turntable.ts          ← (opsional) render 4 view ke docs/zombie-model/ref/v2/
│
└─ tests/
   └─ zombie.test.ts               ← A1–A6, A9 dari PRD
```

Aturan:

- `spec.ts`, `skeleton.ts`, `math/*`, `mesh/loft.ts`, `skin.ts` **tanpa import Three.js** jika bisa (array angka saja) → bisa dites di Node seperti `rig.ts`.
- Three.js hanya di `build.ts`, `pose.ts`, `facet.ts` (BufferGeometry).
- Satu file maksimal ±300 baris. Lebih dari itu, pecah.

## 2. Alur kerja per fase

Setiap fase: kerjakan → tes → screenshot 4 view → bandingkan dengan referensi → baru lanjut.

| Fase | Kerjakan | Selesai jika |
|---|---|---|
| F0 | Baca semua doc. Tulis `spec.ts` dari tabel 01. | Angka lengkap, tidak ada TODO |
| F1 | `skeleton.ts` + render `SkeletonHelper` saja (tanpa mesh) | Tinggi tulang cocok tabel 01 §2; screenshot depan/samping |
| F2 | `loft.ts` + kulit tubuh (torso, leher, lengan, kaki) tanpa kepala detail | Satu mesh tertutup, tidak ada celah (A2), siluet depan cocok |
| F3 | Kepala: profil, rongga mata, pipi, rahang, gigi, mata, rambut | Wajah terbaca dari jarak game (zoom kamera game normal) |
| F4 | Tangan + jari | Jari bengkok seperti cakar, ujung jari di pertengahan paha (A5) |
| F5 | `skin.ts`: bobot + `SkinnedMesh` | A3 lulus; tekuk siku 120° & lutut 90° tanpa robek (A7) |
| F6 | Pakaian: kemeja terbuka, celana, ikat pinggang, bot; tepi sobek | Siluet 4 view cocok referensi |
| F7 | Facet: jitter, warna per face, luka, flat shading | Mirip gaya referensi; A8 |
| F8 | `pose.ts`: bungkuk, idle, walk, attack, death | A6; kaki tidak ngesot saat jalan |
| F9 | Variasi seed (tinggi ±6%, luka, sobekan, rambut), LOD1, ekspor glb | A4, A9; 20 zombie di layar tetap 60 fps |
| F10 | Ganti zombie lama di `actors.ts` dengan `buildZombie` | Game jalan normal, tes lama tetap lulus |

## 3. Cara membandingkan dengan referensi

1. Kamera ortografik, tinggi frustum 2.0 m, target (0, 0.9, 0).
2. Posisi kamera: depan (0, 0.9, 5), kiri (5, 0.9, 0), belakang (0, 0.9, −5), kanan (−5, 0.9, 0).
3. Latar abu `#6E6E6E`, satu directional light dari kiri-atas-depan + ambient 0.4 (mirip studio referensi).
4. Simpan ke `ref/v2/{front,left,back,right}.png`, susun berdampingan dengan referensi.
5. Periksa: tinggi kepala, lebar bahu, panjang lengan, tinggi celana, ukuran bot, condong badan.

Di DEADZONE, mode inspeksi sudah ada: `?camera=close&debug=1`, akses lewat `window.__dz`. Pane browser memperlambat rAF, jadi render manual via `__dz.scene.render()`.

## 4. Prompt pembuka untuk AI

> Kamu akan membangun model zombie low-poly prosedural di `game/src/render/zombie/`. Baca dulu semua file di `docs/zombie-model/` sesuai urutan README, dan lihat dua gambar di `docs/zombie-model/ref/`. Gambar `hasil-gemini-v1.png` adalah contoh gagal; jangan ulangi kesalahan di PRD §2. Kerjakan per fase (05 §2), satu fase per giliran. Di akhir tiap fase: jalankan tes, ambil screenshot 4 view, bandingkan dengan referensi, laporkan selisih yang terlihat, lalu tunggu persetujuan sebelum fase berikutnya. Semua angka harus dari `spec.ts`.
