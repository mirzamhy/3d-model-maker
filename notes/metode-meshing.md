---
tags: [konsep, meshing, sdf, retopologi]
dibuat: 2026-11-02
---
# Metode meshing (dari bentuk ke mesh low-poly)

Alur di proyek ini: **SDF → mesh padat → mesh low-poly**. Hasil uji ada di [Eksperimen topologi kepala](eksperimen-topologi-kepala.md), sumbernya di [Sumber belajar](sumber-belajar.md).

## 1. Bentuk: SDF
SDF (signed distance function) adalah fungsi yang memberi jarak titik ke permukaan: negatif di dalam, positif di luar. Bentuk dirakit dari primitif seperti ellipsoid, capsule, dan hull, lalu digabung dengan `smin` (gabungan halus) atau `smax` (potongan halus). Rumus dari Inigo Quilez. Hull bersudut (`JAW`, `NOSE`, `CHEEK`) dipakai untuk bidang tegas.

## 2. SDF ke mesh padat
- **Ray shell + voxel remesh** (yang dipakai): sinar ditembakkan dari tengah, titik permukaan dicari dengan bisection, lalu voxel remesh Blender (1.1 mm) menyatukan semua bagian jadi satu mesh tertutup.
- **Marching cubes / surface nets**: cara klasik grid ke mesh.
- **Dual contouring**: grid plus normal, jadi tepi tajam tetap tajam. Di Blender versinya adalah Remesh "Sharp" (octree). Di kepala ini hasilnya bolong dan tidak lebih baik.

## 3. Mesh padat ke low-poly
| Metode | Cara kerja | Kuat | Lemah |
|---|---|---|---|
| **Edge collapse (QEM)** | buang edge yang paling sedikit mengubah bentuk (Garland & Heckbert) | kepadatan otomatis ikut detail | segitiga acak, ada sliver |
| **QuadriFlow / Instant Meshes** | medan arah dan posisi, quad seragam searah lekuk | quad rapi, loop mengalir | kepadatan seragam, detail kecil hilang |
| **Planar dissolve** | gabung muka yang hampir sejajar | bidang besar | tidak berguna kalau permukaan melengkung di mana-mana |
| **Template topologi** | grid tetap yang dirancang tangan, vertex ditempel ke SDF | loop mata dan mulut terkontrol, siap animasi | perlu dirancang per jenis kepala |

## 4. Trik yang kita buat
- **Half + mirror**: simpan setengah (x ≥ 0), olah, lalu cerminkan dan weld di garis tengah. Hasilnya simetri sempurna.
- **Newton snap ke SDF**: `p ← p − d·∇d/|∇d|²`, diulang beberapa kali, sehingga vertex jatuh tepat di permukaan.
- **Density warp untuk QuadriFlow**: ruang di sekitar wajah dan telinga digelembungkan dengan fungsi radial monoton `f(r) = r(1 + a·e^{−(r/R)²})` (aman selama a < 2.2), QuadriFlow dijalankan, lalu warp dibalik (bisection). Area yang digelembungkan kebagian quad lebih banyak.
- **Relaksasi tangensial dengan kunci tepi**: vertex digeser ke rata-rata tetangga hanya sepanjang bidang singgung. Vertex di tepi lipat > 30° tidak digeser.
- **Beautify fill**: flip edge hanya di antara muka yang hampir sejajar (< 12–18°), supaya garis hidung dan bibir aman.

## 5. Jebakan Blender (background mode)
- `quadriflow_remesh` menolak mesh langsung dari voxel remesh ("needs to be manifold") walau mesh itu manifold. Solusinya decimate dulu ke ±30k muka.
- Warp yang terlalu kuat (a ≥ 2.1) membuat QuadriFlow gagal tanpa pesan jelas. Mesh tetap padat.
- Remesh Sharp bisa menghasilkan mesh terbuka. Cek dengan `closed()`.
