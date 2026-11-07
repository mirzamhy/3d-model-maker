---
tags: [game, deadzone, part, low-poly]
dibuat: 2026-11-07
versi: lp1
---
# Part low-poly untuk game DEADZONE (lp1)

Tujuan awal belajar: karakter untuk game zombie online user, **DEADZONE** (`C:\Mirza Personal\tiktok`, Three.js, TikTok LIVE portrait, sampai 360 aktor).

## Cara game menggambar karakter
- Tanpa skinned mesh. Tiap aktor = **potongan kaku per tulang** (badan, panggul, leher, kepala, lengan atas/bawah, tangan, paha, betis, bot) yang dipose tiap frame dengan IK (`game/src/render/actors.ts`).
- **Satu `InstancedMesh` per part**, dipakai semua aktor: 12 aktor = 39 draw call.
- Warna = vertex color × warna instance. Part yang diwarnai (baju, kulit) harus **putih**, detail lebih gelap (rasio).
- Variasi dari seed: rambut, topi, rompi, tas, syal, masker, warna.
- Part lama: primitif halus (lathe, bola, torus), rata-rata ~3500 tris per aktor; siku/lutut bola, baju cuma warna di tabung.

## Konvensi frame part (lokal tulang)
- Anggota (upperArm 0.29, forearm 0.27, thigh 0.42, shin 0.41, neck): +y dari sendi sepanjang tulang. Mesh simetris di x (kiri-kanan pakai mesh sama). Untuk kaki menggantung, lokal −z = depan lutut.
- torso: pinggang y 0 → pangkal leher y 0.5, +z depan, diskala `bodyW`/`bodyD`. Bahu di (±0.19, 0.42).
- pelvis: pinggang y 0 → selangkangan −0.13, pinggul (±0.095, −0.05).
- hand: pergelangan y 0, jari +y. boot: pergelangan kaki di origin, +z ke ujung, sol y −0.08.
- head/face/hair: frame kepala, origin di atas leher.

## Pipeline
`tools/blender/game_parts.py` (Blender headless):
- Badan: loft berbidang besar (6 sisi lengan, 8 sisi kaki, 10 sisi badan dengan bidang depan/belakang datar), ujung kubah runcing supaya sendi yang berputar tidak berlubang.
- Kaos: kelim bawah dan rib kerah (tangga + warna band 0.86). Lengan atas = lengan baju dengan manset di atas siku. Celana kargo lurus. Bot: batang + kaki loft sepanjang z + sol gelap.
- **Kepala = kepala bidang v16f** (`head_lp_v6.blend`), skala 1.35 ke frame kepala (kepala besar terbaca di HP, topi lama masih pas). Kulit dibagi warna kulit → putih, zona gelap tetap rasio. Mata dan alis = `faceLP` (tanpa tint), rambut = `hairLP` (tint warna rambut).
- Keluaran: `tiktok/game/src/render/lowpoly/survivor_parts.json` (segitiga datar, normal per poligon, warna) + `output/game/parts_v1.blend`.

Di game (`parts.ts`): `LOWPOLY` (matikan dengan `?lp=0`) mengganti 9 part badan (dipakai survivor dan zombie). Survivor memakai `headLP` / `faceLP` / `hairLP`. Kepala zombie tetap lama.

Viewer: `http://127.0.0.1:5190/viewer.html` (`game/viewer.html`): 12 aktor dengan rig asli, diam / jalan / serang / mati, wireframe, galeri part. Bandingkan dengan `?lp=0`.

## Hasil lp1
- Part survivor: badan 196, panggul 96, leher 44, lengan atas 104, lengan bawah 68, tangan 68, paha 92, betis 92, bot 144, kepala 484, wajah 48, rambut 244.
- Rata-rata line-up (survivor + zombie): 3538 → 3083 tris per aktor. Survivor sendiri sekitar 1900 + perlengkapan.
- Jalan / diam: sendi tertutup, tidak ada celah. Tes game 76/76 lolos.

## Pelajaran
- Game dengan ratusan aktor: **part kaku + instancing** lebih murah daripada skinned mesh. Model dibuat per tulang, bukan satu badan.
- Quad yang sedikit bengkok dipecah jadi 2 segitiga dengan normal berbeda menghasilkan **garis-garis** di wajah. Normal per poligon (Newell), seperti flat shading di Blender, membuat tiap bidang satu warna.
- Warna yang diwarnai per karakter: simpan rasio terhadap warna dasar (kulit / rambut), bukan warna asli.

## Berikutnya
- Penilaian user. Kepala zombie (skull/zface) versi bidang besar. Rambut lain (keriting, kuncir, cepol) dan topi versi low-poly. Celana: saku samping dari `pocketThigh` versi bidang.
