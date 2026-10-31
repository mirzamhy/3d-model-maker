# PRD — Model Zombie Low-Poly "Walker" (v2)

## 1. Latar

Game DEADZONE (Three.js, TikTok LIVE, layar portrait 1080×1920) butuh zombie yang terbaca jelas dari jauh, ringan untuk dirender dalam jumlah banyak, dan bisa dianimasikan (jalan menyeret, menyerang, mati).

Generasi v1 (Gemini) gagal. Referensi target: [ref/referensi-4-view.webp](ref/referensi-4-view.webp).

## 2. Diagnosis hasil v1 ([ref/hasil-gemini-v1.png](ref/hasil-gemini-v1.png))

| # | Masalah di v1 | Seharusnya (referensi) |
|---|---|---|
| 1 | Kepala melayang di atas badan, tanpa leher | Leher tipis menyambung kepala ke dada, kepala condong ke depan |
| 2 | Lengan tidak ada; hanya 2 bola (dodecahedron) di bahu | Lengan panjang kurus: lengan atas, lengan bawah, tangan dengan jari bengkok, ujung jari sampai pertengahan paha |
| 3 | Mata berupa bola besar menonjol keluar kepala | Mata cekung dalam rongga, kecil, putih pucat |
| 4 | Badan berbentuk tong lebar; organ (iga, usus) ditempel di permukaan seperti stiker | Torso kurus, dada sedikit cekung, kemeja terbuka memperlihatkan perut hijau; luka berupa bercak warna di face, bukan objek tempelan |
| 5 | Ada celah antara badan dan celana; paku/duri acak di pinggang | Ikat pinggang menutup sambungan; celana pendek sobek bergerigi |
| 6 | Kaki pendek, kaki ujung berupa balok dengan jari kuning | Tungkai panjang, lutut sedikit tekuk, sepatu bot cokelat sobek, jari kaki keluar dari ujung bot |
| 7 | Proporsi kepala ≈ 1/4 tinggi badan | Tinggi ≈ 7 kepala (lihat 01) |
| 8 | Postur tegak lurus | Bungkuk: punggung atas melengkung, kepala maju, bahu turun |
| 9 | Warna jenuh (hijau neon, merah mengkilap), garis wireframe terlihat | Palet kusam: hijau zaitun, krem kotor, cokelat; flat shading tanpa garis tepi |
| 10 | Tidak ada tanda rig/skinning | Satu `SkinnedMesh` dengan skeleton standar |

Akar masalah: v1 membangun model dari primitif lepas (sphere, cylinder, box) yang diposisikan dengan tebakan, tanpa skeleton sebagai acuan. Solusi v2: **skeleton → profil penampang → loft mesh → skin**.

## 3. Tujuan

- G1. Siluet 4 view (depan, kiri, belakang, kanan) mirip referensi saat ditumpuk (overlay) — penilaian visual + cek bounding box.
- G2. Satu mesh tertutup per lapisan (kulit, baju, celana, bot), di-skin ke satu skeleton.
- G3. Animasi idle (goyang), walk (menyeret), attack (dua tangan menerkam), death (jatuh) tanpa sobek/robek mesh di sendi.
- G4. Ringan: ≤ 3.000 segitiga per zombie, 1 draw call per material (target 1–2 material total).
- G5. Deterministik: seed yang sama = zombie yang sama. Variasi (tinggi, sobekan, posisi luka, warna) dari seed.

## 4. Bukan tujuan

- Tekstur gambar (UV painting). Warna cukup per-face / vertex color.
- Rig wajah lengkap. Cukup tulang rahang (jaw) untuk buka-tutup mulut.
- Simulasi kain fisik.

## 5. Syarat lulus (acceptance criteria)

| ID | Syarat | Cara cek |
|---|---|---|
| A1 | Tinggi total 1,75 m ± 5% (sebelum skala per-seed) | `Box3.setFromObject` di bind pose |
| A2 | Tidak ada celah: setiap vertex sambungan berjarak < 1 cm ke tetangga part | Tes otomatis jarak antar cincin sambungan |
| A3 | Semua vertex punya bobot, jumlah bobot = 1 ± 1e-4, maks 4 tulang | Unit test di `skinWeight` |
| A4 | Jumlah segitiga ≤ 3.000 | `geometry.index.count/3` atau `position.count/3` |
| A5 | Ujung jari tangan (pose bungkuk istirahat) berada di ketinggian 0,36–0,42 × tinggi badan (≈ pertengahan paha) | Posisi world tulang `*HandMiddle_End` |
| A6 | Sudut bungkuk: garis panggul→kepala condong 12°–20° ke depan dari vertikal | Hitung dari posisi world `Hips` dan `Head` |
| A7 | Saat siku ditekuk 120° dan lutut 90°, volume tidak kempes lebih dari 30% di sendi | Visual + bandingkan jarak vertex luar sendi |
| A8 | Render 4 view tanpa garis wireframe, flat shading | Screenshot |
| A9 | Seed sama → hash posisi vertex sama | Unit test |

## 6. Gaya visual

- Low-poly faceted, flat shading (`flatShading: true` atau geometry non-indexed + normal per face).
- Penampang tubuh 5–8 sisi. Kepala ≈ 120–200 segitiga.
- Warna per face dengan jitter kecerahan ±4% supaya facet terlihat seperti referensi.
- Lihat palet di [01-anatomi-proporsi.md](01-anatomi-proporsi.md#palet).

## 7. Keluaran

- Kode di `game/src/render/zombie/` (struktur di [05](05-struktur-file-dan-alur.md)).
- Fungsi `buildZombie(seed: number): { mesh: SkinnedMesh; skeleton: Skeleton; bones: Record<BoneName, Bone> }`.
- Script ekspor `scripts/export-zombie-glb.ts` ⇒ `zombie.glb` (glTF 2.0) agar bisa dicek di Blender / gltf-viewer.
- Tes di `tests/zombie.test.ts` untuk A1–A6, A9.
