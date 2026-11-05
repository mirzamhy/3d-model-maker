---
tags: [pipeline, evaluasi, rencana, karakter]
dibuat: 2026-11-04
status: rencana, belum dijalankan
---
# Pipeline karakter 3D dan evaluasinya

Tujuan: satu cara kerja yang bisa diulang untuk banyak proyek (karakter game, animasi, prop), dengan output
Blender (`.blend`) dan three.js (`.glb`). Rencana ini dirangkum dari semua eksperimen di vault:
[MOC](00-MOC-belajar-3d.md), terutama [telinga](parts/ear.md), [model dari referensi](model-dari-gambar-referensi.md),
[tutorial Rozi 3D](tutorial-rozi3d-lowpoly-karakter.md), dan [ukuran kualitas mesh](ukuran-kualitas-mesh.md).

## Apa yang sudah terbukti (dasar rencana)
| Berhasil | Gagal |
|---|---|
| Trace titik per titik dari gambar wire (telinga v13, sekali coba) | Menebak anatomi dari deskripsi (telinga v8–v12) |
| Cincin quad dari siluet 4 view (badan v5base, 1938 tris, bersih) | Sculpt + decimate: segitiga acak, user tidak suka |
| Sambungan dengan jumlah titik loop sama (leher v5) | Menjahit ke loop yang ada titik sisipan: lubang |
| Bidang besar + flat shading + n-gon utuh | Detail kecil di geometri (alis mesh, otot halus) |
| Part tumpuk dilem ke kulit (SDF) | Part diukur dari bidangnya sendiri: menggantung |
| Ukur angka + render tiap ronde + penilaian user | Menilai dari satu render 3/4 saja |

Kesimpulan: **bentuk dirancang (bukan dihasilkan), dicek dengan angka dan gambar, disetujui user per part.**

## Pipeline 9 tahap

### 0. Brief (sebelum menyentuh Blender)
Isi [template brief](#template-brief) di bawah. Tanpa brief, ronde revisi membengkak (kasus leher: 6 ronde).
Yang wajib jelas: gaya, budget tris, target (game engine / three.js / render), perlu rig atau tidak, gerakan apa.

### 1. Referensi
- Minimal: **lembar depan + samping** dengan proporsi sama (ideal 4 view + T-pose/A-pose).
- Per part sulit (telinga, tangan, wajah): **gambar wire gaya low-poly** yang user pilih. Ini yang di-trace.
- Kalau user hanya punya gambar biasa: buat lembar referensi dulu (AI image atau sketsa), minta user setuju.
- Simpan di `references/<proyek>/` dan tempel di note proyek.

### 2. Blockout (bentuk kasar, 300–800 tris)
- Cara: **cincin quad dari siluet** (`ref_body.py`) atau box modeling (extrude + loop cut, cara Rozi).
- Mirror selalu aktif: kerja setengah.
- Kepala, badan, tangan, kaki sebagai satu mesh atau part terpisah sesuai brief.
- **Gerbang:** siluet depan dan samping cocok dengan referensi (lihat evaluasi E2). User lihat sheet 4 view.

### 3. Part detail (satu kartu part per bagian)
Urutan biasa: kepala, tangan + jari, kaki/sepatu, telinga, rambut, baju, aksesori.
- Tiap part punya **kartu** di `notes/parts/` (landmark, topologi, konektor, riwayat versi, penilaian).
- Part sulit: **trace dari gambar wire** dengan grid piksel, overlay trace dulu sebelum 3D.
- Jari: extrude per face dari buku jari (Rozi), 3 ruas, jempol dari samping telapak.
- Rambut: curve + bevel + taper, lalu konversi ke mesh dan dikurangi.
- Baju: duplikat face badan + Solidify; atau shell terpisah dengan loop yang mengikuti badan.

### 4. Rakit + konektor
- **Jahit** (satu mesh): loop dua sisi harus sama jumlah titiknya dan bersih.
- **Tumpuk** (part terpisah): titik pangkal ditanam 1 mm di bawah kulit, diukur dari permukaan badan.
- **Gerbang:** mesh tertutup, simetris, tidak ada part tembus atau menggantung di 4 view + close-up.

### 5. Bersih-bersih
Normal ke luar, merge titik dobel, hapus face dalam, skala 1 unit = 1 m, kaki di y = 0, origin di antara kaki,
nama objek dan material rapi.

### 6. UV + warna
- Gaya flat: **warna per face / palet tekstur kecil** (satu gambar 256 px berisi kotak warna). Murah dan rapi di game.
- Wajah (mata, alis, mulut) **dilukis di tekstur**, bukan mesh.
- Warna per-face harus disalin ke domain CORNER sebelum ekspor glTF (jebakan lama).

### 7. Rig + bobot
- Default: **Rigify metarig** (standar, bisa ke Unity/Godot/three.js lewat ekspor deform bones).
- Alternatif sederhana untuk three.js: rig tulang manual (seperti rig F2 73 tulang).
- Automatic weights, lalu perbaiki di bahu, siku, pinggul, selangkangan, leher.
- Topologi yang dibutuhkan rig: **minimal 3 loop di tiap sendi** (siku, lutut, bahu, pinggul, jari).

### 8. Uji gerak
- Pose uji standar: T-pose, A-pose, jongkok, angkat tangan, tinju, lari (frame terjauh), putar kepala.
- three.js: `viewer/gerak.html` (jalan, jongkok, lompat), dicek dengan data, bukan screenshot saja.

### 9. Ekspor + LOD
- `.glb` untuk three.js / game, `.blend` sebagai sumber.
- Triangulasi hanya saat ekspor (diagonal dipilih, lihat [triangulasi](triangulasi-quad-ke-tri.md)).
- LOD: LOD0 penuh, LOD1 ±50 %, LOD2 ±25 % (decimate dengan fitur wajah dilindungi).

## Evaluasi

### E1. Gerbang otomatis (script, tiap ronde)
Rencana: satu script `tools/blender/eval_model.py <file.blend>` yang menulis JSON + render sheet.

| Cek | Lulus kalau |
|---|---|
| tris per LOD | ≤ budget brief |
| closed (manifold) | true, per part |
| symmetry | 0 vertex tanpa pasangan (kecuali aset asimetris yang disengaja) |
| quad share | ≥ 85 % sebelum ekspor |
| slivers | ≤ 2 % muka |
| normal terbalik | 0 |
| titik dobel / face dalam | 0 |
| skala | tinggi = brief ± 1 %, kaki di y = 0 |
| loop di sendi | ≥ 3 di siku, lutut, bahu, pinggul |
| UV | tidak tumpang tindih (kecuali mirror), tidak ada face tanpa UV |
| bobot | tiap vertex total 1, ≤ 4 tulang per vertex (batas game) |
| ekspor glb | terbuka lagi tanpa error, warna ikut |

### E2. Kecocokan dengan referensi (angka)
- **Siluet IoU** depan dan samping: render mask hitam-putih model vs mask referensi. Target ≥ 0.90 badan, ≥ 0.85 part.
- **Overlay**: model setengah transparan di atas referensi, garis merah = beda > 1 cm.
- **Landmark**: tinggi dagu, bahu, pinggang, selangkangan, lutut; beda ≤ 2 % tinggi badan.

### E3. Sheet visual (untuk mata user)
Satu gambar standar per ronde: 4 view flat shaded + wire, close-up kepala 3/4, tangan, kaki, dan pose uji.
Selalu disandingkan dengan versi sebelumnya dan referensi. Tidak menilai dari satu render saja.

### E4. Uji deformasi
Di pose uji: tidak ada face terlipat, volume sendi tidak kolaps (siku/lutut ≥ 70 % tebal asli), baju tidak tembus.

### E5. Penilaian user (gerbang akhir tiap tahap)
- User nilai dengan skala sederhana per part: **ok / hampir / ulang**, plus sketsa coretan kalau perlu.
- Feedback dicatat di kartu part (tabel riwayat) dengan gambar.
- **Batas ronde**: kalau satu part sudah 3 ronde tanpa kemajuan, berhenti menebak dan minta gambar wire untuk di-trace.

### Skor per versi (tulis di kartu part)
`v13 | tris 88 | closed ✓ | sym 0 | IoU 0.91 | user: ok`

## Jalur alat (kapan pakai apa)
| Situasi | Pakai |
|---|---|
| Ada lembar 4 view | cincin quad dari siluet (script) |
| Part sulit + ada gambar wire | trace titik per titik |
| Butuh anatomi realistis | MPFB2 sebagai cetakan, topologi tetap kita |
| Edit cepat, lihat langsung | Blender MCP (live) |
| Prop / aset latar | `search_assets` (Poly Haven, Poly Pizza) atau `generate_3d`, lalu retopo |
| Karakter langsung di browser | three.js prosedural (gaya lama `src/zombie`), ukur sama dengan E1–E4 |

## Rencana latihan (urut, makin sulit)
1. **Survivor sampai jadi**: jari, sepatu, baju modular, rambut, rig Rigify, uji gerak, glb. Ini proyek uji pipeline penuh.
2. **Karakter chibi** (kepala besar, ±1500 tris): uji pipeline dengan proporsi lain.
3. **Prop set** (senjata, tas, peti): latihan bidang besar dan UV palet.
4. **Hewan / makhluk berkaki 4**: siluet tanpa template manusia.
5. **Karakter ke three.js**: animasi Mixamo / buatan sendiri, cek di viewer.

Tiap latihan menghasilkan: note proyek, kartu part, skor E1–E5, dan daftar pelajaran baru.

## Alat (sudah dibuat 4 Nov 2026)
`tools/qa/`: `eval_model.py` (E1), `silhouette_iou.py` (E2), `sheet.py` (E3), `export_glb.py`, dan `qa.ps1` untuk
menjalankan semuanya. Cara pakai dan hasil uji pertama: [Alat QA](alat-qa.md). E4 menunggu rig.

## Template brief
```
Proyek:
Gaya: (low-poly bidang besar / chibi / semi-realistis)
Target: (three.js / Unity / Godot / render)
Budget tris: LOD0 ___  LOD1 ___
Tinggi: ___ m   Pose dasar: T / A
Rig: (ya/tidak, Rigify/manual)   Gerakan: ___
Part: kepala, tangan (jari? ___), kaki, rambut, baju (modular?), aksesori
Warna: (per face / tekstur / palet)
Referensi: (file 4 view, gambar wire part)
Selesai kalau: ___
```
