---
tags: [referensi, forum, topologi, lowpoly]
dibuat: 2026-11-02
sumber: https://blenderartists.org/t/help-with-topology-and-low-poly-models/1619342
---
# Thread BlenderArtists: "Help with Topology and low poly models"

Diringkas oleh agent Haiku (2 Nov 2026) dari 21 post. Teks di bawah parafrase, bukan kutipan. Terkait: [Topologi wajah low-poly](topologi-wajah-lowpoly.md).

## Pertanyaan
Penanya ingin membuat karakter game low-poly di antara gaya Synty dan realistis. Topologi wajahnya selalu kebanyakan detail, dan ia bingung menyambung wajah ke belakang kepala.

## Saran dari para penjawab
- **goorman**: Decimate bisa menurunkan polycount, hasilnya bervariasi. Low-poly gampang tanpa sadar berubah jadi high-poly. Latihan dan tutorial lebih penting dari aturan.
- **MartinZ**: Tentukan dulu arti "tampilan low-poly" yang dicari. Meniru susunan vertex dari referensi mengajarkan struktur, tapi kalau referensinya gambar AI, hasilnya jelek karena vertex tidak mengikuti bentuk. Mulai dari model realistis, lalu uji geometri low-poly mana yang menonjolkan fitur yang diinginkan. Sumber: [Blender demo files](https://www.blender.org/download/demo-files/).
- **oo_1942**: Wajah harus menjaga fitur kunci dan proporsi manusia di polycount berapa pun. Referensi: [Low poly head (Sketchfab)](https://sketchfab.com/3d-models/low-poly-head-6b6a762bd8b34b6d9d46d44129b55037). Membuat wajah dari grid lebih sulit daripada dari blok. Jangan percaya gambar referensi buatan AI.
- **Okidoki**: Metode "cube to anything", dengan tutorial [1](https://www.youtube.com/watch?v=pa0ZlrJPK8I), [2](https://www.youtube.com/watch?v=8KTEckFQY3c), [3](https://www.youtube.com/watch?v=YCX54Nffuys). Blockout bentuk dari referensi. Subdivide menambah kerumitan, jadi topologi ditentukan sendiri. Referensi ortografis paling mudah diselaraskan.
- **thoslos**: Pisahkan model low-poly "final" (dirender apa adanya) dari model "basis" untuk subdivision. Quad penting untuk subdivision. Segitiga tidak masalah untuk model final karena renderer toh men-triangulasi. Arahkan edge mengikuti kontur bentuk. Uji deformasi lebih awal (rig, weight, shape key). Buang edge yang tidak menyumbang bentuk.

## Urutan kerja
1. Tentukan gaya target.
2. Siapkan referensi asli, sebaiknya ortografis.
3. Blockout dengan kubus atau blok.
4. Tentukan topologi sendiri dan sederhanakan fitur.
5. Uji deformasi sebelum mesh dikunci.

Penanya sendiri akhirnya memutuskan menggambar referensi, mempelajari bidang kepala, membuat mulut sederhana dulu, dan memakai segitiga di tempat yang perlu.

## Yang tidak dijawab thread ini
Susunan loop mulut, sudut bibir, hidung, jumlah loop mata, dan budget poligon tidak dibahas. Dua post menanyakan loop mata, hidung, dan mulut tapi tidak dijawab. Untuk itu pakai analisis gambar di [Topologi wajah low-poly](topologi-wajah-lowpoly.md).

## Arti untuk proyek kita
- **Kepala game kita adalah model "final"**, jadi segitiga boleh. Yang penting edge mengikuti kontur bentuk. Ini mendukung arah collapse_soft dan template.
- **"Cube to anything" = template topologi.** Blok yang dirancang lalu dibentuk sama dengan grid tetap yang di-snap ke SDF.
- **Uji deformasi lebih awal**: begitu template kepala jadi, coba buka mulut lewat shape key sebelum detail dikunci.
- **Referensi asli, bukan AI**: SDF kita berasal dari angka anatomi (docs/01), sudah sesuai.
