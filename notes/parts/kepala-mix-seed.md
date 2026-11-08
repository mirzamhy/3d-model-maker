---
tags: [kepala, rambut, seed, variasi, low-poly]
dibuat: 2026-11-08
versi: mix-v3 (prototipe, 12 style rambut)
---
# Kepala campuran style per seed (prototipe)

Permintaan user: "bikin konsep kaya yang sebelumnya, beberapa style bisa di mix seed".

## Cara kerja
- Skrip: `tools/blender/head_mix.py` (pakai fungsi `head_trace.py` v17).
- **Style wajah = offset pada landmark v17** (px trace: dx, dy, dd). Titik dan muka sama, jadi style bisa dicampur dengan bobot. Area rambut dan telinga tidak digeser.
  - `ref` (v17 asli), `kotak` (rahang lebar, rak alis maju, hidung lebar, leher tebal), `kurus` (tulang pipi tajam, pipi cekung, dagu panjang sempit, hidung panjang).
  - `FACE_AMP = 1.8`: offset x1 terlalu halus di v1.
- **Style rambut = set parameter `HP`** di `head_trace.py` (default = v17r yang disetujui): arah aliran atas/samping/belakang, tebal massa, lumpy, panjang + angkat duri per zona, panjang gigi tepi, `keep` (bagian duri yang ditarik).
  - `jambul` (v17r), `cepak` (massa tipis, duri pendek), `gondrong` (poni jatuh ke depan, samping dan belakang turun).
- Seed: `rng = default_rng(seed)`; bobot = acak^2.5 dinormalkan (satu style dominan, sisanya mewarnai). Juga sisi belahan, warna kulit (5), warna rambut (5).
- Cek otomatis tiap seed: kepala manifold, **tidak ada muka terbalik** dibanding kepala ref (dot normal < 0.2).

```bash
blender -b --factory-startup -P tools/blender/head_mix.py -- \
  --ears output/head-game/template/head_lp_v6.blend \
  --sheet notes/attachments/qa/mix_sheet_v2.png --seeds 1-16 [--save output/head-mix]
```

## Hasil
- v1: ![[mix_sheet_v1.png]] Warna kulit abu (warna sRGB dipakai langsung sebagai linear), wajah hampir sama.
- v2: ![[mix_sheet_v2.png]] Warna `** 2.2`, offset x1.8. 16/16 seed: 0 muka terbalik, kepala 232 tris, rambut 268 tris.

## v3: 12 style rambut (2026-11-08)
User: "style nya kurang beragam cari refrensi list set rambut".
- Daftar dari referensi barber + pack low-poly (Superhive Le baron: buzz, faux hawk, slicked back, undercut, man bun;
  daftar potongan populer: crop, quiff, side part, fringe, messy, spiky, mullet):
  jambul, cepak, gondrong, buzz, mohawk, slickback, fauxhawk, belahtengah, keriting, panjang, mullet, botak.
- Kontrol baru di `HP` (default = v17r, tidak berubah):
  `mask_w` (mohawk: massa hanya |x| < w), `cut_y`/`cut_k` (undercut/fade: di bawah tinggi y dicukur),
  `drop` (rambut panjang: tepi + rok ditarik turun di samping belakang telinga dan belakang), `curl` (arah duri acak),
  `mid` (belah tengah), `tone` (campur warna kulit: buzz). Bagian dicukur = tanpa duri, warna mendekati kulit
  (`ht.CUT` per titik, rata-rata per muka).
- Seed sekarang pilih **satu style utama + satu sekunder** (≤ 35 %). Saklar zona (`mask_w`, `cut_y`) hanya dari style utama:
  dicampur, mohawk jadi setengah mohawk.
- Warna render lewat atribut: warna FACE bukan color attribute di viewport, disalin ke layer CORNER `ColC`.
- `--styles` = satu tile per style murni (wajah ref): ![[hair_styles_v1.png]]
  Urutan: baris 1 jambul, cepak, gondrong, buzz; baris 2 mohawk, slickback, fauxhawk, belahtengah;
  baris 3 keriting, panjang, mullet, botak.
- Campuran 16 seed: ![[mix_sheet_v3.png]] 0 muka terbalik.
- Lemah: slickback belum kelihatan disisir licin (masih berduri kecil), belahtengah belum terlihat belahannya,
  keriting terbaca jambul berantakan (butuh benjolan bulat rata, bukan duri). Kulit di render atribut sedikit lebih gelap
  dari render material v2.

## Pelajaran
- Topologi tetap = variasi murah: campur posisi titik, bukan bangun ulang.
- Style yang dicampur harus cukup jauh beda; campuran bobot memperkecil perbedaan.
- Warna pilihan mata (sRGB) dikonversi `** 2.2` sebelum dipakai di material/vertex color.

## Lanjut
- Belum dinilai user. Kandidat: perbaiki slickback/belahtengah/keriting, man bun, rambut samping (side part), part tumpuk (topi, masker) dipilih per seed, ekspor seed ke `game_parts.py`.
