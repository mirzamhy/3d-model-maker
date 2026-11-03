---
tags: [konsep, pipeline, ai-3d, riset]
dibuat: 2026-11-03
---
# Pipeline AI image-to-3D (cara kerja platform seperti Tripo, Meshy, Hunyuan3D)

User menempelkan penjelasan dari satu platform AI 3D (3 Nov 2026). Note ini menjelaskan tiap tahapnya, model nyata yang dipakai di tiap tahap, bagian yang hanya bahasa pemasaran, dan bandingannya dengan cara kita ([Template topologi kepala](template-topologi-kepala.md), [Metode meshing](metode-meshing.md)).

## Gambaran besar
```
foto  -> bersihkan latar -> bayangkan sisi lain (multi-view diffusion)
      -> tebak bentuk 3D sebagai FIELD (SDF / voxel / Gaussian)
      -> ubah field jadi mesh padat (marching cubes / FlexiCubes)
      -> sederhanakan / retopo (target jumlah face)
      -> UV unwrap (xatlas) -> proyeksi warna + bake tekstur
      -> rig (opsional) -> ekspor GLB/FBX/OBJ -> buka di Blender, save .blend
```
Intinya: **AI menebak volume dulu, mesh rapi belakangan.** Topologi adalah langkah terakhir dan paling lemah.

## Tahap demi tahap
| # | Tahap | Apa yang terjadi | Contoh model / alat nyata |
|---|---|---|---|
| 1 | Persiapan gambar | latar dibuang (segmentasi), objek dipusatkan dan diskalakan, kadang diberi caption otomatis | rembg / SAM, captioner |
| 2 | Multi-view | satu foto hanya memperlihatkan satu sisi, jadi model difusi **membayangkan** sisi depan, samping, dan belakang yang konsisten | Zero123++ (6 view dibuat sekaligus dalam satu gambar 3×2), SV3D (video orbit), MVDream, Hunyuan3D-Paint |
| 3 | Tebakan bentuk 3D | jaringan memprediksi **field kontinu**, bukan mesh langsung | LRM / InstantMesh (rekonstruksi dari beberapa view), Hunyuan3D 2 (flow transformer menjadi SDF), TRELLIS (latent voxel jarang 64³) |
| 4 | Ekstraksi mesh | field diubah jadi mesh segitiga padat, ratusan ribu tris, tanpa topologi rapi | Marching Cubes, Dual Contouring, FlexiCubes (NVIDIA) |
| 5 | Retopo / decimate | mesh padat disederhanakan sesuai **target face count** | decimate QEM, QuadriFlow, Instant Meshes; versi AI: MeshAnything (transformer yang "menggambar" mesh seperti artis), Tripo Smart Mesh, Meshy Smart Topology |
| 6 | UV unwrap | permukaan dibuka jadi peta 2D supaya tekstur bisa ditempel | xatlas (dipakai Hunyuan3D 2.1), UVAtlas |
| 7 | Tekstur dan bake | warna dari foto dan view hasil tebakan diproyeksikan ke mesh, lalu di-bake ke tekstur | Hunyuan3D-Paint: lighting dibuang dulu, multi-view, lalu bake |
| 8 | Detail (normal map) | detail dari mesh padat (rongga mata, tulang pipi) disimpan sebagai **normal map** untuk mesh low-poly | bake high→low di Blender (Cycles, Selected to Active), Marmoset, Substance |
| 9 | Rig (opsional) | kerangka dan bobot skinning ditebak AI | UniRig (SIGGRAPH 2025, VAST/Tripo): transformer menebak kerangka, model kedua menebak bobot |
| 10 | Ekspor | GLB/FBX/OBJ. ".blend" hanya hasil import lalu save, tidak ada matematika tambahan | Blender File > Import |

## Penjelasan istilah
- **SDF (signed distance field)**: fungsi yang memberi jarak ke permukaan, negatif di dalam. Sama dengan `head_sdf` kita. Bedanya, mereka **menebak** SDF dengan jaringan saraf, sedangkan kita **menulisnya** dengan rumus.
- **Marching Cubes**: grid kubus kecil; di setiap kubus yang dilewati permukaan dibuat beberapa segitiga. Hasilnya padat dan rata, tanpa loop wajah. Ini sama dengan voxel mesh di [eksperimen topologi kepala](eksperimen-topologi-kepala.md).
- **FlexiCubes**: versi marching yang titiknya bisa digeser saat training, jadi lebih rapat ke bentuk dan lebih bersih.
- **Multi-view diffusion**: Stable Diffusion yang dilatih pada render objek 3D dari banyak sudut. Zero123 lama membuat tiap view sendiri-sendiri sehingga tidak konsisten. Zero123++ membuat 6 view dalam satu gambar sehingga saling cocok.
- **Target face count**: Meshy Smart Topology 100–15 000 face (default 4 000); Tripo 500–20 000 tris atau 500–10 000 quad. Penjelasan yang ditempel user juga menyebut "sekitar 4 000 face".
- **Normal map**: menyimpan arah permukaan, bukan kedalaman. Detail terlihat saat kena cahaya, tetapi **siluet tidak berubah**. Jadi bentuk besar tetap harus ada di mesh low-poly.
- **UV**: koordinat 2D tiap titik mesh untuk membaca tekstur. Kita sekarang tidak memakai UV, karena warna per muka disimpan di atribut `Col` ([template §warna](template-topologi-kepala.md)).

## Mana yang fakta, mana yang bahasa pemasaran
- Penjelasan pertama (9 tahap) sesuai dengan paper (Hunyuan3D 2, InstantMesh, TRELLIS).
- Penjelasan kedua (10 tahap) lebih banyak narasi. Contoh:
  - **"Depth estimation"** dari satu gambar terlalu disederhanakan. Sistem modern tidak cukup memakai peta kedalaman karena sisi belakang tidak kelihatan. Yang dipakai adalah multi-view diffusion atau latent 3D yang langsung menebak volume.
  - **"Edge loop ditempatkan dengan sengaja di wajah dan sendi"** adalah klaim. Retopo otomatis memang menaruh lebih banyak face di area melengkung, tetapi loop mata, mulut, dan nasolabial yang dirancang seperti di template kita jarang ada. Reviewer pihak ketiga menyebut smart low poly "tumpul" di tangan dan wajah.
  - "Your model is currently moving through this pipeline" adalah teks status, bukan penjelasan teknis.

## Bandingan dengan cara kita
| | Platform AI | Kita (template + part) |
|---|---|---|
| Bentuk | ditebak dari foto (data latih besar) | ditulis tangan: SDF + landmark + trace gambar |
| Sisi tak terlihat | dibayangkan multi-view diffusion | dirancang (kartu part) |
| Topologi | hasil terakhir, otomatis, loop tidak dijamin | **dirancang duluan**: loop mata, mulut, rahang, telinga |
| Detail | normal map dari mesh padat | geometri + warna per muka |
| Kecepatan | menit, satu tombol | butuh iterasi dengan user |
| Kontrol, konsisten antar karakter | rendah (tiap generate beda topologi) | tinggi: satu topologi, banyak parameter ([konsep part modular](konsep-part-modular.md)) |

Kesimpulan:
- Pipeline AI kuat di **tahap 1–4**: bentuk kasar dari foto, termasuk sisi yang tidak terlihat.
- Kita kuat di **tahap 5**: topologi yang bisa di-rig dan konsisten.
- Gabungan yang masuk akal: hasil AI (atau foto) dipakai sebagai **referensi bentuk dan landmark**, lalu template kita di-snap ke bentuk itu. Cara snap/proyeksi ini sudah kita pakai ke SDF. Lisensi model sumber harus dicek dulu, misalnya Hunyuan3D berlisensi non-komersial.

## Yang bisa kita ambil
1. **Normal map bake** (tahap 8): mesh template low-poly + SDF detail tinggi → bake detail rongga mata dan pipi tanpa menambah poly.
2. **xatlas UV** (tahap 6) kalau nanti butuh tekstur gambar, bukan warna per muka.
3. **Multi-view sebagai referensi**: gambar depan dan samping yang konsisten membantu trace kartu part, seperti trace telinga v13.
4. **Rig otomatis** (UniRig) untuk uji deformasi. Hasilnya akan lebih baik di template kita karena loop sudah rapi.

## Sumber
- [Zero123++](https://ar5iv.labs.arxiv.org/html/2310.15110) · [SV3D](https://ar5iv.labs.arxiv.org/html/2403.12008) · [One-2-3-45++](https://arxiv.org/pdf/2311.07885)
- [TRELLIS](https://microsoft.github.io/TRELLIS/) · [TRELLIS.2](https://huggingface.co/microsoft/TRELLIS.2-4B/blob/main/README.md) · [Hunyuan3D 2.0 paper](https://arxiv.org/pdf/2501.12202) · [Hunyuan3D 2.1 xatlas helper](https://huggingface.co/spaces/tencent/Hunyuan3D-2.1/raw/main/hy3dpaint/utils/uvwrap_utils.py)
- [InstantMesh](https://arxiv.org/pdf/2404.07191) · [FlexiCubes](https://research.nvidia.com/labs/sil/geometry-processing/main.html)
- [MeshAnything](https://arxiv.org/abs/2406.10163)
- [Tripo retopology docs](https://developers.tripo3d.com/en/docs/mesh-decimate.md) · [Meshy remesh docs](https://docs.meshy.ai/en/webapp/guides/3d-model/remesh) · [Tripo vs Meshy (blog vendor)](https://www.tripo3d.ai/blog/tripo-smart-mesh-p1-vs-meshy-t2)
- [UniRig](https://arxiv.org/abs/2504.12451)
- [Marmoset baking tips](https://docs.marmoset.co/docs/tips-tricks/) · [Normal map workflow glossary](https://3d.irpr.agency/glossary/normal-mapping-workflow/)
- [UniTEX (kritik UV)](https://arxiv.org/pdf/2505.23253) · [Survey produksi aset 3D 2026](https://arxiv.org/pdf/2604.23629)
