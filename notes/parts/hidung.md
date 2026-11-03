# Hidung (nose) — bidang datar ala Asaro

Status: v2 "planes" + tidak mancung (3 Nov 2026), menunggu penilaian user. v1 ditolak: "jangan mancung gini". Baseline v7 tetap bisa dibuat ulang (`TPL_NOSE=sdf`, default).

Keluhan user: hidung terlalu lancip, harusnya ada bidang datar kontur hidung (referensi: kepala low-poly
dengan strip depan hidung dua kolom, bidang samping lebar, bidang bawah segitiga).

## Kenapa lancip
Hidung cuma hasil proyeksi grid ke SDF. Kolom tengah (x = 0) jadi punggung hidung, kolom berikutnya (x ≈ 10 mm)
jatuh 8–10 mm ke belakang → penampang segitiga tajam (baji). Di baris mata bahkan tidak ada kolom 6°, jadi batang
hidung cuma satu garis.

## Planes of the head (John Asaro)
Kepala disederhanakan jadi bidang-bidang. Hidung = baji/keystone:
- **bidang depan** (bridge → ridge → tip): sempit di pangkal, melebar di ujung;
- **bidang samping**: bidang terbesar hidung (pemula sering bikin terlalu sempit);
- **bidang bawah**: segitiga menghadap bawah, dari ujung ke pangkal lubang hidung.

## Cara buat (`tools/blender/head_template.py`, `TPL_NOSE=planes`)
1. Kolom 6° ikut lewat baris mata (`EYE_COLS + [6]`), jadi batang hidung punya dua tepi. +8 vertex.
2. `shape_nose` setelah snap: tepi (kolom 6) dipindah sejajar punggung hidung (`zr(y) − 1 mm`) dengan setengah
   lebar `NOSE_W`: 4.5 mm di pangkal → 8 mm di ujung. Punggung + 2 tepi = satu strip datar.
3. (v2) Punggung hidung ditarik ke belakang `NOSE_BACK`: 0 mm di pangkal, 2.5 / 4.5 mm di tengah, 6 mm di ujung
   (env `TPL_NOSE_BACK`). Ujung hidung z 107 → 101 mm; menonjol 13 mm dari dahi (dulu 19). Bidang bawah ikut mundur 60%.
4. Titik pangkal lubang hidung (dulu 20 mm masuk) maju ke 3 mm di belakang titik bawah tengah → bidang bawah datar.

Hasil: kepala 934 segitiga (baseline 914), tertutup, simetris. Badan F2 v2 = `output/head-game/f2/f2_male_v2.blend`.

```
TPL_NOSE=planes TPL_TAG=nose_v2 blender -b --factory-startup -P tools/blender/head_template.py
F2_HEAD=output/head-game/template/head_nose_v2.blend F2_TAG=f2_male_v2 blender ... -P tools/blender/f2_assemble.py
```

Banding v1: atas = planes v1, bawah = baseline (punggung tajam).
(Catatan: urutan baris di lembar banding ini sempat salah dibilang terbalik ke user; piksel Blender mulai dari bawah.)
![[hidung_planes_cmp.png]]
Banding v2: atas = v2 (tidak mancung), bawah = v1 (mancung):
![[hidung_planes_cmp_v2.png]]
Di viewer gerak:
![[hidung_planes_viewer.jpg]]

Sumber: Proko / Marco Bucci (nose planes, side plane terbesar), arXiv 1502.01954 (Asaro planes),
blenderartists (hidung low-poly cuma bagian grid kotak → kurang bentuk).
Terkait: [[topologi-wajah-lowpoly]], [[template-topologi-kepala]], [[uji-gerak-viewer]].
