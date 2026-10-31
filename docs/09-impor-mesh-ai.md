# 09 — Jembatan Impor Mesh AI (GLB → Rig 66 Tulang)

Mesh dari generator image-to-3D (Modly, Hunyuan3D, Tripo, Meshy, dll.) biasanya **statis**: tidak punya tulang. Jembatan ini memuat GLB seperti itu, menyesuaikan ukurannya, lalu memasangnya ke skeleton 66 tulang proyek ini dengan bobot kulit otomatis. Hasilnya bisa memakai semua pose dan tampilan viewer.

Kode: [src/zombie/import/importMesh.ts](../src/zombie/import/importMesh.ts). Gayanya muncul sebagai tombol **Impor GLB** di panel "Gaya model".

## Cara pakai

1. Buat gambar zombie **T-pose** (lengan lurus ke samping, jari terbuka, menghadap depan).
2. Ubah jadi mesh 3D di layanan favorit (Hunyuan3D di Hugging Face Spaces, Tripo, Meshy, atau Modly kalau GPU kuat), lalu unduh sebagai `.glb`.
3. Buka viewer (`npm run dev`, http://localhost:5195). Seret file `.glb` ke layar, atau klik **Muat GLB…**.
4. Kalau badan tidak pas dengan rig, ubah kolom **Tinggi / Geser / Putar** lalu **Terapkan**.
5. Pilih pose dan tampilan seperti biasa. Ekspor GLB hasilnya sudah ber-rig.

Lewat kode (otomasi): `await __zm.loadGlb('/renders/model.glb', { rotY: 180, height: 1.82 })`.

## Langkah di dalam

```
GLB ──► kumpulkan semua Mesh (matrix dunia diterapkan)
    ──► seragamkan atribut (position, normal, uv, color) + index, pecah per material
    ──► mergeGeometries (grup per material, tekstur asli tetap dipakai)
    ──► fit: putar → skala ke tinggi 1.82 m → kaki di y=0 → pusat x/z
    ──► bobot kulit otomatis → skinIndex/skinWeight → SkinnedMesh pada skeleton
```

### Normalisasi ukuran
Bounding box setelah diputar (`rotX`, `rotY`). Skala seragam `s = tinggi / (maxY − minY)`, lalu `minY → 0`, pusat x dan z ke 0 (z digeser +0.02). Offset `dx, dy, dz` ditambahkan setelahnya.

### Bobot kulit otomatis
Untuk tiap vertex `p` dan tiap tulang `i` dengan segmen `[a, b]` dan radius kasar `r_i`:

```
t = clamp((p − a)·(b − a) / |b − a|², 0, 1)
dist = |p − (a + t(b − a))|
w_i = 1 / ((dist / r_i)⁴ + 1e-6)
```

- Jarak dibagi radius tulang. Tulang tipis (jari, r ≈ 0.009) menang di dekat dirinya sendiri, tulang besar (pinggul, r ≈ 0.12) menang dari jauh.
- Vertex yang posisinya sama (belahan di jahitan UV) **digabung** dulu, jadi tidak pernah retak saat bergerak.
- **Smoothing**: bobot dirata-ratakan dengan tetangga di graf mesh, 2 iterasi (`w' = ½w + ½·rata-rata tetangga`), supaya transisi sendi halus dan tidak ada duri.
- Diambil 4 tulang terbesar, bobot di bawah 0.02 dibuang, lalu dinormalisasi.
- Tulang `Jaw` dan tulang ujung berpanjang nol tidak dipakai. Dasarnya: Baran & Popović 2007 (Pinocchio) untuk gagasan bobot dari jarak, disederhanakan.

## Hasil uji

Diuji dengan dua GLB buatan proyek ini (bukan hasil AI): `zombie_s7.glb` (low-poly, proporsi beda dari skeleton) dan `zombie_real_s7.glb` (semi-realistis, 8 material, 5 jari).

| GLB | Segitiga | Vertex unik | Waktu bobot |
|---|---|---|---|
| zombie_s7 | 2.052 | 1.288 | 68 ms |
| zombie_real_s7 | 19.364 | 10.175 | 140 ms |

Pose menerkam, merayap, duduk, dan meraung: tidak ada mesh robek, jari bergerak sendiri-sendiri, tekstur dan material asli ikut. Render: `renders/import_*.png`.

## Batasan

- **Wajib T-pose**, lengan lurus dan jari terpisah. Lengan yang menempel ke badan atau jari yang menyatu (umum di mesh AI) akan ikut tertarik tulang yang salah.
- **Rahang tidak membuka.** Mesh asing tidak punya pemisah rahang atas dan bawah.
- Proporsi mesh harus mirip manusia dewasa. Bahu atau lengan yang jauh dari tulang akan mendapat bobot yang tidak pas. Gunakan **Tinggi** dan **Geser Y** untuk menyejajarkan.
- Orientasi: mesh harus menghadap +Z dan Y ke atas. Untuk file Z-up isi `Putar X = -90`, untuk yang menghadap ke belakang isi `Putar Y = 180`.
- Smoothing dilewati bila `vertex unik × tulang > 45 juta` (sekitar 700 ribu vertex). Mesh sebesar itu sebaiknya di-decimate dulu.
- GLB terkompresi Draco belum didukung. Meshopt didukung.
- Belum diuji dengan mesh dari generator AI sungguhan, karena GPU di laptop ini tidak cukup untuk menjalankan Modly.

## Menyempurnakan di Blender

Kalau bobot otomatis kurang bagus: impor GLB hasil, buka Weight Paint, dan perbaiki di area bermasalah (ketiak, selangkangan, jari). Nama tulang mengikuti Mixamo, jadi animasi Mixamo bisa langsung dipakai.
