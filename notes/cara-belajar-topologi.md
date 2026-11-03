---
tags: [belajar, topologi, sumber, rencana]
dibuat: 2026-11-03
---
# Cara belajar topologi (sumber + langkah nyata)

Riset web 3 Nov 2026. Sumber lain ada di [Sumber belajar](sumber-belajar.md) dan [thread BlenderArtists](blenderartists-topologi-lowpoly.md).

## Prinsip yang berulang di banyak sumber
- **Tidak ada satu topologi wajah yang benar.** Di forum Polycount, beberapa artis menegaskan hal ini; tiap layout punya tujuan sendiri ([Polycount: head topology question](https://polycount.com/discussion/212635/head-topology-question)).
- **Loop mata**: mulai dari mata ke luar. Jumlah poligon di atas dan di bawah mata kira-kira sama. Jangan biarkan loop mata menyebar terus tanpa ujung (thread Polycount yang sama).
- **Loop mulut**: satu loop besar dari bawah hidung, mengelilingi sudut mulut dengan jarak lebar, sampai depan dagu. Loop kecil mengelilingi cuping hidung (thread Polycount yang sama).
- **Kulit di sekitar bibir sering bukan loop sungguhan** kalau mulut dipotong dari grid persegi. Ubah jadi loop dengan loop cut, lalu dorong tepi kulit ke luar untuk membentuk sudut mulut ([BlenderArtists: Corners of the mouth](https://blenderartists.org/t/corners-of-the-mouth-updated/368051)).
- **Pole** adalah vertex dengan 3, 5, atau lebih edge. Loop berhenti di pole. Pole 3 dan 5 wajar; 6 ke atas hindari. Taruh pole di area datar yang tidak banyak bergerak ([CG Cookie: The art of good topology](https://cgcookie.com/posts/the-art-of-good-topology-blender), [Blender manual: mesh structure](https://docs.blender.org/manual/pt/2.81/modeling/meshes/structure.html)).
- **Untuk low-poly sangat rendah**, loop tidak terlalu penting karena mata sering hanya tekstur. Loop jadi penting saat wajah dianimasikan (Polycount).
- **Mulai jarang, baru dipadatkan.** Topologi lebih mudah dikendalikan kalau poligonnya sedikit dulu (Polycount).

## Kursus dan bahan latihan (sebagian berbayar)
- [80.lv: retopology workflow untuk kepala siap animasi](https://80.lv/articles/learn-complete-retopology-workflow-for-animation-ready-character-heads): kursus Anna Beganska, dari mid-poly ke low-poly, termasuk alur edge wajah dan bagian dalam mulut.
- [Head Retopology for Games (FlippedNormals)](https://flippednormals.com/product/head-retopology-for-games-low-mid-poly-68536): berbayar, materi yang sama.
- [How to Retopologize a Head Like a Boss (FlippedNormals)](https://flippednormals.com/product/how-to-retopologize-a-head-like-a-boss-64): berbayar.
- [Danny Mac: panduan retopologi bergambar](https://dannymac.gumroad.com/l/TAQM): berbayar, isinya kepala latihan + hasil retopo sebagai pembanding.
- [CG Cookie community: my first retopo](https://cgcookie.com/community/17966-my-first-retopo): saran pemula, kuasai dasar dulu sebelum kepala.
- Tutorial "cube to anything" di [thread BlenderArtists](blenderartists-topologi-lowpoly.md).

## Langkah nyata (rencana latihan)

### Untuk user (manual di Blender)
1. **Hari 1–2, dasar**: baca bagian loop dan pole di Blender manual. Latih Loop Cut (Ctrl+R), Inset (I), Knife (K), dan dissolve edge.
2. **Hari 3–4, kepala kotak**: ikuti satu tutorial "cube to anything". Buat kepala ±200 quad seperti referensi A di [Topologi wajah low-poly](topologi-wajah-lowpoly.md): 3 kolom dahi, hidung 2 kolom, mulut 3 baris.
3. **Hari 5–6, retopo di atas mesh kita**: buka `output/head-game/head_mid_eyeless.glb`. Pakai Snap to Face + modifier Shrinkwrap, lalu gambar ulang topologinya dengan tangan. Mulai dari loop mata, lalu loop mulut, lalu loop masker. Bandingkan dengan `template/head_tpl_v5.glb`.
4. **Hari 7, uji gerak**: buat shape key mulut membuka dan alis naik. Lihat di mana mesh rusak; di situ loop kurang.
5. Tiap latihan: simpan screenshot ke `notes/attachments/latihan/` dan tulis 3 pelajaran di note baru.

### Untuk pipeline kita (Claude + script)
1. Template v6: bibir maju, kolom wajah dikurangi, hidung prisma (lihat [Template topologi kepala](template-topologi-kepala.md)).
2. **Uji deformasi otomatis**: shape key "mulut buka" (vertex celah bawah turun 8 mm, bobot menurun ke dagu) dan ukur sliver dan lipatan. Template harus lebih tahan daripada collapse.
3. **Ukuran "loop"**: hitung apakah ring mulut dan ring mata benar-benar loop tertutup (tiap vertex di ring punya 4 edge). Masukkan ke [Ukuran kualitas mesh](ukuran-kualitas-mesh.md).
4. Kalau user sudah membuat retopo manual (langkah 3 di atas), jadikan itu acuan: posisi kolom dan baris diukur dari mesh user, lalu dikunci di template.
