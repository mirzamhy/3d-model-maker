---
name: lowpoly-karakter
description: Use when membuat atau memperbaiki karakter low-poly (kepala, wajah, rambut, telinga, badan, tangan, baju, rig) di Blender lewat Python, terutama untuk game DEADZONE (tiktok/, Three.js) atau gaya bidang besar flat-shaded; juga saat user bilang bentuk "jelek", "aneh", "beda dari contoh", "kotak-kotak", "berantakan", "menggantung", atau "ada celah".
---

# Karakter low-poly (gaya bidang besar)

Ringkasan semua pelajaran dari proyek `C:\Mirza Personal\model 3d maker` (vault Obsidian, catatan di `notes/`).
Inti: **trace referensi, bangun dari sedikit bidang yang disengaja, bandingkan dengan render yang diselaraskan.**
Jangan menebak bentuk, jangan pahat + decimate.

Detail teknis dan jebakan Blender: [referensi-teknis.md](referensi-teknis.md).

## Alur kerja wajib

1. **Cek yang sudah ada dulu.** Baca `notes/00-MOC-belajar-3d.md` dan kartu part terkait (`notes/parts/*.md`).
   Part yang sudah disetujui (telinga v13, tangan v11, kepala v17) dipakai ulang lewat **data** (titik + muka),
   bukan ditulis ulang. Cek nama skrip baru tidak menimpa modul lama.
2. **Referensi dulu, angka dulu.** Ambil frame depan dan samping (video turntable: ekstrak frame).
   Ukur di crop bergrid (50 px), zoom 2x per area. Frame miring: ukur kedua sisi, rata-ratakan.
3. **Trace dua pandangan.** Depan = x, y. Samping = z. Petakan tinggi samping ke tinggi depan dengan dua patokan
   (alis, dagu). Overlay titik trace di atas gambar asli sebelum bangun 3D.
4. **Bangun bidang besar.** Tulis titik setengah sisi + muka manual sepanjang garis anatomi, cerminkan.
   N-gon/quad untuk kerja, segitiga hanya saat ekspor.
5. **Cek otomatis tiap build:** manifold (tiap edge tepat 2 muka), jumlah tris, simetri, titik tertanam di kulit.
6. **Bandingkan dengan render yang diselaraskan** (kamera ortho, skala px→m dan pusat sama dengan frame referensi),
   berdampingan dan ditumpuk. Volume dan warna dinilai dari **render berwarna dengan framing sama** dengan
   crop video berwarna, bukan wireframe abu. Turntable (12° per frame) lebih jelas daripada 3 sudut.
7. **Close-up di area yang dikeluhkan**, dengan wireframe, dari arah yang dihadapi part itu. Cek **kedua sisi**.
8. **Catat** di kartu part: versi, keluhan user (kutip), penyebab, perbaikan, gambar QA di `notes/attachments/qa/`,
   tautkan dari MOC. Bagian "Pelajaran" diisi aturan yang bisa dipakai ulang.

## Gaya

- **Bidang besar = bentuk anatomi besar.** Tiap bidang satu warna (flat shading, normal per poligon).
- "Kotak-kotak" / "berisik" = **terlalu banyak face kecil**, bukan masalah warna. Bangun dari sedikit bidang.
- **Jangan sculpt/subdivide + decimate**: hasilnya sup segitiga acak. Detail lewat loop/potongan yang ditempatkan sengaja.
- Detail tanpa ubah struktur: zona warna di face yang ada + objek kecil menempel (kelopak, helai, celah mata).
- Bagian yang terlihat di siluet hanya boleh dapat alur (−); tonjolan (+) hanya di tempat yang tidak terlihat siluet.
- Tonjolan butuh lembah di sebelahnya, kalau tidak hanya jadi lereng.

## Kepala dan wajah

- Trace titik landmark + segitiga manual (v17): benar dalam satu kali coba. Loft cincin/template butuh puluhan versi.
- Rak alis menghadap ke bawah, jadi alur mata = bayangan. Pipi = kipas dari titik tulang pipi. Bibir atas M, bawah tebal.
- Kepala dan leher = dua bagian (bola + tusuk) untuk gaya ini. Rahang tidak menyatu dengan leher, aman saat menoleh.
- Ukuran kepala tetap (dagu ke ubun 0.22 m) supaya topi dan frame game tetap pas.

## Telinga dan part tumpuk

- User beri gambar wire: **trace, jangan menebak anatomi** (v8–v12 menebak, semua meleset).
- Part tumpuk dilem ke **kulit** (ukur pangkal dari permukaan kepala), bukan ke bidang datar. Kalau tidak: celah, menggantung.
- Cek tertanam dulu sebelum menilai bentuk. Render tegak lurus bidang part.
- **Ubah ukuran satu part = ukur ulang semua titik yang bergantung padanya** (tepi rambut di sekitar telinga).

## Rambut (paling sering salah)

Resep yang disetujui (v17r, `tools/blender/head_trace.py: build_hair`):
1. Cangkang = muka kepala di zona rambut, subdivide sekali.
2. **Volume = tebal massa dasar**, bukan duri. Tebal naik ke atas/belakang/samping (~1–3 cm), tepi dahi 5 mm,
   **menipis ke tepi samping/belakang** dan **hampir nol dekat telinga**.
3. Rok dari tepi rambut turun ke kulit, supaya tepi punya ketebalan.
4. Duri = titik permukaan ditarik keluar, hanya di zona: jambul (tengah depan saja, |x| kecil), ubun, jentikan pelipis,
   gigi tepi. Titik terpilih memblokir tetangganya.
5. **Satu medan aliran** (zona dicampur smoothstep): atas ke depan-atas-satu sisi, samping naik, belakang turun.
   Duri bertetangga hampir sejajar, **hanya beda panjang** (0.7–1.35x). Tanpa belokan acak.
6. Ujung duri atas diangkat ke arah **atas**, bukan sepanjang normal (normal di sisi kepala = tanduk).
7. Panjang duri berkurang ke tepi kepala. Duri dipilih simetris atau dicek kedua sisi (hash tetap = duri yang sama tiap versi).
8. Garis rambut **melingkari telinga**: cambang di depan, di atas telinga, turun di belakang; tepi tepat di tepi telinga,
   menyelip di bawah pangkal belakang telinga. Tidak ada pita kulit.

Gejala dan sebab:
- Bulu babi / piramid di mana-mana: poke semua muka. Pakai zona.
- "Kurang volume": massa dasar tipis, lebar datang dari ujung duri.
- "Berantakan, bertabrakan": arah per zona + acak. Pakai satu medan aliran.
- Tanduk sendirian di sudut atas: zona jambul tanpa batas samping, ekor panjang terlalu lebar.
- "Menggantung / ada celah" di telinga: massa tebal berhenti mendadak, sisi bawahnya gelap seperti atap. Tipiskan ke tepi.
- Duri mendatar di balik telinga: zona jentikan tanpa batas belakang. Cari titik rambut terjauh dari kepala.
- Helai sekunder (clump) dicoba: mahal (566 tris) dan user lebih suka massa + duri.

## Badan, baju, rig

- Badan dari siluet: ukur per tinggi, jangan pakai proporsi rata-rata (kaki bergaya besar).
- Baju dari salinan kulit = kulit dicat. Baju perlu bentuk sendiri: jatuh dari titik terlebar, kelonggaran, rib, kelim, manset.
  Longgar boleh di paha/betis, pas di lutut/siku. Buang kulit di bawah baju.
- Sambungan: jumlah titik konektor sama, kolom part bawah memuat kolom part atas.
- Rig: bobot hitung sendiri + cermin (bone heat tidak simetris). Lipatan sendi diperbaiki di bobot (engsel), bukan tambah cincin.
  Uji dengan sapuan sudut. Pose uji harus masuk akal.

## Game DEADZONE

- Karakter = **part kaku per tulang + InstancedMesh**, bukan skinned mesh. Frame part lokal tulang: lihat `notes/parts/game-deadzone.md`.
- Ekspor `tools/blender/game_parts.py` ke `tiktok/game/src/render/lowpoly/survivor_parts.json`. Segitiga datar, normal per poligon (Newell).
- Part yang diwarnai per karakter: simpan **rasio** ke warna dasar (kulit/rambut putih), bukan warna asli.
- Verifikasi di `http://127.0.0.1:5190/viewer.html` (bandingkan `?lp=0`). Jangan `flatShading` Three.js untuk quad.
- Budget kasar survivor ~1900 tris + perlengkapan; kepala ~230, rambut ~250, telinga ~90.

## Kerja dengan user

- Balas bahasa Indonesia, singkat. Keluhan user = data: kutip di catatan, cari penyebab dengan angka/close-up, baru ubah.
- Satu keluhan bisa punya beberapa penyebab; perbaikan sering memunculkan efek samping. Render ulang semua sudut setelah fix.
- Commit hanya kalau diminta, tanpa atribusi Claude. Jangan commit file sesi lain (`src/`, `renders/`, zombie businessman,
  simple character, `tools/blender-mcp`, `tools/head`, `tools/argon`).
- Simpan .blend sebelum `execute_blender_code` lewat MCP.
