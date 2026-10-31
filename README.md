# Model 3D Maker — Zombie Prosedural

Zombie yang dibangun prosedural dengan TypeScript + Three.js, dalam dua gaya:

- **Semi-realistis** (default): ±17k segitiga, 66 tulang (5 jari), wajah tengkorak dengan rahang berengsel dan gigi terbuka, jaket terbuka dengan kerah, kaus V-neck, celana panjang dengan saku, sepatu. Detail pori kulit, lipatan kulit jaket, dan serat kain dibuat oleh shader noise (tanpa tekstur). Warna kulit, jaket, kaus, celana berubah per seed.
- **Low-poly**: ±2k segitiga, 58 tulang, faceted.

Pose: T-pose, idle bungkuk, jalan, meraih, menyerang, menerkam, meraung, merayap, duduk. Scene: horor (gelap, kabut, lampu sorot) atau studio. Tampilan: depan/kiri/belakang/kanan/bebas, close-up wajah, 4 view, gerombolan (5 zombie).

## Jalankan

```bash
npm install
npm run dev
```

Buka http://localhost:5195. Panel kanan berisi pose, sudut kamera (depan/kiri/belakang/kanan/bebas/4 view), layer rig, X-ray, seed variasi, dan tombol simpan PNG/GLB ke `renders/`.

## Struktur

```
docs/                    brief/PRD + referensi gambar (baca docs/README.md)
docs/07-proses-pembuatan.md  catatan proses nyata: langkah, angka, masalah + perbaikan
renders/                 hasil render PNG + zombie_s7.glb
src/zombie/
  spec.ts                semua angka: tinggi, palet, jumlah sisi
  hash.ts                noise deterministik per seed
  skeleton.ts            58 tulang, nama Mixamo, bind pose T-pose
  mesh.ts                MeshBuilder, loft (sapuan cincin), bobot skin, box/spike/gem
  parts/body.ts          torso, leher, lengan, tangan + jari, kaki
  parts/head.ts          kepala, rongga mata, rahang (tulang Jaw), gigi, telinga, rambut
  parts/clothes.ts       kemeja terbuka, lengan sobek, celana, ikat pinggang, bot
  skeletonReal.ts        66 tulang untuk gaya semi-realistis
  noise.ts               value noise + fbm (warna per vertex)
  real/head.ts           tengkorak: fitur wajah dari fungsi gaussian, rahang, gigi, mata, telinga
  real/body.ts           leher, dada, pergelangan, tangan 5 jari dengan kuku
  real/clothes.ts        kaus V-neck, jaket + kerah + lapel, celana + saku, ikat pinggang, sepatu
  real/materials.ts      material + shader detail (bump noise di posisi bind-pose)
  real/variant.ts        variasi warna per seed, warna kulit busuk, darah
  build.ts               buildZombie(seed, style) -> SkinnedMesh + Skeleton
  pose.ts                9 pose, kontak lantai per pose
src/viewer/
  main.ts                scene, kamera, UI, ekspor
  overlay.ts             tampilan rig: tulang, ring kontrol, label
```

## Catatan teknis

- Bobot skin dihitung dengan inverse-distance ke segmen tulang yang diizinkan per bagian (pangkat 4, maksimal 4 tulang, dinormalisasi).
- Bind pose memakai T-pose (mengikuti gambar rig), bukan A-pose seperti saran di docs/03.
- Bagian tubuh saling tumpang tindih di sambungan (lengan masuk ke torso, dll.) supaya tidak ada celah; sambungan diikat oleh bobot campuran.
- Ekspor GLB berisi 1 mesh, 1 skin, atribut `POSITION, COLOR_0, JOINTS_0, WEIGHTS_0, NORMAL`. Bisa dibuka di Blender. Detail shader (pori/lipatan) tidak ikut terekspor; warna per vertex ikut.
- Gaya semi-realistis memakai mesh halus (vertex digabung, normal halus) dan beberapa material per bagian (kulit, mata, gigi, kaus, jaket, celana, kulit sepatu, logam).
