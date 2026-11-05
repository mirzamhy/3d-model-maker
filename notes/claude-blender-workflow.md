---
tags: [workflow, claude, blender, obsidian]
dibuat: 2026-11-02
---
# Workflow Claude + Blender + Obsidian

## Cara kita kerja
1. **Blender headless lewat script Python**: `blender -b --factory-startup -P script.py`. Tidak ada klik manual, jadi tiap hasil bisa diulang persis.
2. **Bentuk dari angka**: SDF di `head_lowpoly.py`, tanpa menyalin mesh orang lain.
3. **Ukur dan render tiap ronde**: stats JSON plus sheet 4 view, wireframe, dan close-up. Lihat [Ukuran kualitas mesh](ukuran-kualitas-mesh.md).
4. **User menilai dengan mata**, Claude mengubah angka dan metode.
5. **Catat di vault ini**: tiap pelajaran jadi satu note yang saling tertaut. Session Claude berikutnya membaca vault dan tidak mulai dari nol.

## Pelajaran dari artikel Berk Erdag (Medium, Jun 2026)
Dia memakai Claude (Sonnet) yang terhubung ke Blender.
- Model manusia diambil dari Mixamo. Animasi jalan buatan Claude gagal, juga setelah dikasih video.
- Motion graphic dengan Geometry Nodes berhasil, termasuk addon panel N buatan Claude.
- Claude lemah di kamera, lighting, dan keputusan kreatif. Ada kesalahan bevel yang dipasang setelah scatter, sehingga scene jadi berat.
- Kesimpulannya: AI bagus untuk tugas berulang dan addon, tapi pengguna harus paham dasar Blender untuk menangkap kesalahan.

Bedanya dengan kita: kita membuat bentuk sendiri secara prosedural, mengukurnya, dan mencatat semuanya. Bukan perintah lewat chat terhadap model jadi.

## Kenapa Obsidian
- Link antar-note (`[teks](file.md)`) dan graph view memperlihatkan hubungan konsep, eksperimen, dan referensi.
- Gambar render dan referensi ditempel langsung di note (`notes/attachments/`).
- Semua file markdown biasa, jadi Claude bisa membaca dan menulisnya tanpa plugin.

## Jebakan teknis yang pernah kena (jangan diulang)
- **Path Windows di heredoc/sed/Python**: `\f` di `head-game\f2` jadi karakter form feed, path rusak diam-diam.
  Pakai garis miring `/` di path, atau Edit tool, bukan sed dengan backslash.
- **Urutan baris piksel Blender** (`image.pixels`) mulai dari **bawah**. Lembar banding yang disusun dari array:
  baris pertama array = baris paling bawah gambar. Sempat salah bilang "atas = baseline" ke user.
  Cek dengan angka (ukur titik), jangan tebak dari gambar.
- **Warna per-face tidak ikut glTF**: atribut warna domain FACE cuma ada di `mesh.attributes`, exporter cuma baca
  POINT/CORNER. Salin ke CORNER dulu (lihat [Uji gerak di browser](uji-gerak-viewer.md)).
- **Browser pane tersembunyi**: requestAnimationFrame berhenti, canvas WebGL kosong di screenshot. Cek data lewat
  JavaScript (`window.gerak`) atau render di Blender.
- **Tulang helper F2 di Blender**: rotasi sendi J diambil di frame rest yang dibawa induk
  (`child = P * J * rest`, jadi `J = P^-1 * C`); helper dapat `P * slerp(I, J, 0.5) * rest`. Rest helper beda arah
  dengan tulang anaknya, jadi jangan setengahkan quaternion lokal mentah-mentah (`pose_test.py: drive_helpers`).
- **Blender bmesh**: `bm.verts[i]` basi setelah vertex baru ditambah; simpan list vertex lama dulu.
- **BMVert di set Python**: setelah op bmesh pada mesh yang punya layer int, `v in set_of_bmverts` bisa salah diam-diam.
  Pakai koordinat atau index yang di-refresh. Buat layer custom sebelum menyimpan referensi vertex.
- **Menjahit ke loop kepala**: cek dulu loop-nya bersih (jumlah vertex = kolom badan, tiap pasangan tetangga
  punya edge langsung). Loop dengan vertex sisipan menghasilkan lubang + edge non-manifold.
