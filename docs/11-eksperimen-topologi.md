# 11 — Eksperimen topologi kepala game (2026-11-02)

Pertanyaan: apakah teknik dari literatur (QuadriFlow, dual contouring, planar dissolve) bisa menggantikan pipeline sekarang (voxel remesh → edge-collapse decimate → mirror) untuk kepala game tanpa mata (eyeless mid, budget ±900 tris)?

Script: `tools/blender/head_topo_lab.py`. Semua metode mulai dari dense mesh yang sama (`head_game.dense_body`), lalu diukur dengan cara yang sama. Hasil: `output/head-game/lab/` (`.blend`, `.glb`, `lab_stats.json`) dan `renders/game_lab_<metode>_*.png`.

```bash
LAB_METHODS=collapse,quadriflow "/c/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup -P tools/blender/head_topo_lab.py
```

## Ukuran

- **dev mean / p95**: jarak permukaan low-poly ke SDF asli dalam mm, diukur di vertex dan titik tengah muka. Makin kecil, makin setia ke bentuk.
- **aspect p90**: rasio sisi terpanjang ke tinggi terpendek segitiga (persentil 90). Nilai 1.15 berarti segitiga sama sisi; makin besar, makin gepeng.
- **planes**: jumlah area datar (tetangga yang normalnya beda < 3°). Makin sedikit, makin "bidang besar".

## Hasil

| Metode | Tris | Quad | Tertutup | dev mean | dev p95 | aspect p90 | planes |
|---|---|---|---|---|---|---|---|
| collapse (sekarang) | 898 | 0 % | ya | 0.60 | 1.31 | 4.88 | 782 |
| QuadriFlow 450 quad | 914 | 86 % | ya | 0.99 | **4.10** | **2.41** | **414** |
| planar dissolve | 1048 | 0 % | ya | 0.58 | 1.51 | 5.19 | 895 |
| Remesh Sharp (dual contouring) | 900 | 0 % | **tidak** | 0.61 | 1.33 | 5.15 | 769 |
| QuadriFlow 5× lalu collapse | 422 | 0 % | ya | 1.20 | 3.85 | 15.86 | 323 |

## Kesimpulan

1. **Collapse tetap yang terbaik untuk kepala ini.** Kepadatan segitiga mengikuti lekuk: rapat di hidung, mulut, dan telinga, longgar di tengkorak. Pada budget 900, hanya metode ini yang menjaga wajah.
2. **QuadriFlow** menghasilkan topologi paling bersih (quad 86 %, segitiga dua kali lebih rata, bidang setengahnya). Tapi kepadatannya seragam, jadi hidung, mulut, rongga mata, dan telinga hilang (p95 4.1 mm). Cocok untuk bagian tanpa detail kecil (tengkorak, leher, bahu, badan) atau untuk budget jauh lebih tinggi. QuadriFlow menolak mesh langsung dari voxel remesh ("needs to be manifold") walau mesh itu manifold. Solusinya decimate dulu ke ±30k muka.
3. **Planar dissolve tidak mengurangi apa-apa**, karena hasil collapse sudah melengkung di mana-mana: tidak ada tetangga yang hampir sejajar. Sampai sudut 12° jumlah tris masih 1048. Tampilan "bidang besar miring" seperti di pack referensi (roadmap §11, HANDOFF-lowpoly §6) harus dirancang di bentuk SDF-nya (hull bersudut seperti `JAW`, `NOSE`, `CHEEK`), bukan dari dissolve setelah meshing.
4. **Remesh Sharp (octree dual contouring) di Blender** tidak membawa keuntungan dan menghasilkan mesh terbuka. Tepi tajam pada SDF ini sudah tertangkap oleh voxel remesh yang halus (1.1 mm).
5. **Hybrid** (QuadriFlow padat lalu collapse) paling buruk: segitiga gepeng dan bentuk hilang.

## Ronde 2: gabungan struktur QuadriFlow + detail collapse

Masukan user: QuadriFlow strukturnya oke tapi detail hilang; collapse detailnya bagus tapi ada segitiga yang tidak proporsional, cekungan, dan patahan yang tidak mulus. Ukuran tambahan: **slivers** (segitiga dengan rasio sisi² / 2·luas > 8) dan **dihedral p95** (sudut lipat antar-muka, persentil 95).

| Metode | Tris | Quad | dev mean | dev p95 | aspect p90 | slivers | dihedral p95 |
|---|---|---|---|---|---|---|---|
| collapse | 898 | 0 % | 0.60 | 1.31 | 4.88 | 26 | 68.5° |
| collapse_clean | 898 | 0 % | 0.90 | 2.65 | 2.42 | 2 | 62.5° |
| **collapse_soft** | 898 | 0 % | 0.69 | 1.71 | 3.76 | 16 | 68.4° |
| qf_warp (a 1.3) | 926 | 91 % | 0.91 | 3.67 | 2.45 | 18 | 50.7° |
| qf_warp A (a 1.8, telinga 1.7) | ±960 | – | 1.01 | 3.93 | 3.57 | 24 | 59.6° |
| qf_warp B (a 2.1) | gagal | | | | | | |

- **collapse_clean**: snap ke SDF + flip edge datar + relaksasi tangensial, 3 putaran. Segitiga paling rata, tapi relaksasi ikut melunakkan batang hidung dan menggembungkan bibir.
- **collapse_soft** (kompromi terbaik): vertex di tepi lipat > 30° dikunci (hidung, bibir, rongga mata tetap seperti hasil collapse), hanya area datar yang di-flip dan direlaksasi lalu di-snap ke SDF. Detail wajah tetap, tengkorak/leher/bahu lebih rata, sliver 26 → 16.
- **qf_warp**: ruang di sekitar wajah dan telinga digelembungkan dengan warp radial monoton (skala lokal 1 + a) sebelum QuadriFlow, jadi area itu kebagian quad lebih banyak. Setelah itu warp dibalik dan vertex di-snap ke SDF. Hidung dan rongga mata muncul kembali, tapi telinga (bentuk tipis) pecah jadi lembaran dan mulut masih kasar. a ≥ 2.1 membuat QuadriFlow menolak mesh.

## Arah ke depan

- Pertahankan collapse untuk kepala dan wajah.
- Kalau nanti kepala perlu animasi wajah (mulut membuka, kedip), edge loop di sekitar mata dan mulut lebih penting daripada keseragaman. Jalur yang realistis adalah **template topologi tetap** seperti badan F2 (roadmap §3), dengan posisi vertex diproyeksikan ke SDF, bukan remesh otomatis.
- QuadriFlow layak dicoba untuk badan atau leher-bahu versi Blender kalau butuh quad.
