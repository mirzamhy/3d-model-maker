---
tags: [tutorial, blender, karakter, box-modeling]
sumber: YouTube "Lowpoly Game Ready Character Modeling Blender 3D" Part 1-6, Rozi 3D (tanpa narasi, dipelajari dari frame tiap 30 detik)
---
# Tutorial Rozi 3D: karakter low-poly game-ready (box modeling)

Video: Part 1 KfGkywrBnWY, Part 2 P-qHTOZpHMs, Part 3 J6GE11GHN_Q, Part 4 QVcd40TvdU0, Part 5 PXW06H9v02w,
Part 6 lUG5PLe78sA. Tidak ada suara/subtitle: dibaca dari contact sheet (ffmpeg, 1 frame / 30 detik, 3x3).

## Part 1 (19 menit): blockout seluruh badan dari kubus
![[attachments/tutorial-rozi/p1_00-04_blockout.jpg]]
1. **Kubus** = badan (diskalakan pipih), **UV sphere low-poly** = kepala (objek terpisah). Kubus dibagi dua,
   modifier **Mirror** (kerja setengah, sisi lain otomatis).
2. Kaki: face bawah kubus di-**extrude** ke bawah, dipotong loop (Ctrl+R) di lutut dan pergelangan, lalu
   titik digeser dari tampak depan dan samping (Numpad 1 / 3) mengikuti siluet.
3. Leher: face atas di-extrude ke atas. Bahu dan lengan: face samping bahu di-extrude keluar, miring ke bawah
   (A-pose, bukan T-pose), loop di siku dan pergelangan.
4. Badan dirapikan: loop ditambah di dada/pinggang, titik digeser supaya bahu miring, dada, punggung.

![[attachments/tutorial-rozi/p1_04-08_badan_kaki.jpg]]
5. Kaki/telapak: ujung kaki di-extrude ke depan (blok), lalu dibentuk.
6. Tangan: telapak = blok dari ujung lengan; buku jari dipotong jadi 4 face, tiap face di-**extrude** jadi jari
   (3 ruas), jempol dari face samping telapak.

![[attachments/tutorial-rozi/p1_09-13_tangan_jari.jpg]]
7. Di akhir: kepala disambung ke leher. Loop bawah kepala dan loop atas leher dibuat **sama jumlah titiknya**,
   lalu disatukan (join + bridge / merge).

## Part 2 (24 menit): kepala dan wajah
![[attachments/tutorial-rozi/p2_00-04_kepala.jpg]]
- Bola low-poly dibentuk jadi kepala (rahang, dagu) dari tampak depan/samping.
- Mata: face dipilih, **inset** jadi lubang mata, didorong ke dalam; bola mata objek terpisah.
- Hidung: face di tengah di-extrude keluar lalu dibentuk. Mulut: loop horisontal + inset untuk bibir.
- Telinga: face samping kepala di-inset dan di-extrude.
![[attachments/tutorial-rozi/p2_09-13_wajah_telinga.jpg]]
- Akhir part 2: topologi wajah dirapikan (loop melingkar di mata dan mulut), badan disambung, shade smooth.

## Part 3 (20 menit): rambut dan baju
![[attachments/tutorial-rozi/p3_00-04_rambut_curve.jpg]]
- Rambut: tiap helai = **curve (bezier)** dengan bevel + taper (ujung lancip), ditata satu-satu di kepala,
  nanti dikonversi ke mesh.
![[attachments/tutorial-rozi/p3_09-13_baju.jpg]]
- Baju: face badan dipilih -> duplikat (Shift+D) -> pisah (P) -> diperbesar sedikit (Alt+S) ->
  modifier **Solidify** (ketebalan kain). Celana sama dari kaki. Sabuk = ring silinder, simpul = blok kecil.
- Sepatu dari bentuk telapak kaki.

## Part 4 (16 menit): warna, UV, tekstur wajah
![[attachments/tutorial-rozi/p4_09-13_tekstur_wajah.jpg]]
- Material polos per bagian (kulit, baju, celana, sepatu, rambut) dulu untuk cek warna.
- Kepala di-UV unwrap, lalu **texture paint**: mata (iris, pupil, kilau), alis, bibir, bayangan hidung
  **dilukis di tekstur**, bukan dibentuk dari geometri. Hemat poly, wajah tetap ekspresif.

## Part 5-6 (16 + 19 menit): rig dan bobot
![[attachments/tutorial-rozi/p5_04-08_rig.jpg]]
- **Rigify metarig** (human) ditambahkan, tulang digeser ke sendi badan (tampak depan + samping), termasuk jari.
- Badan di-parent ke rig dengan **automatic weights**, lalu **weight paint** diperbaiki di bahu, siku,
  pinggul, selangkangan (gradasi warna merah -> biru).
![[attachments/tutorial-rozi/p6_04-08_weight.jpg]]
- Baju dan aksesori ikut di-rig (bobot diperbaiki per bagian), dicek dengan memutar tulang.

## Pelajaran untuk proyek kita
- Ini **box modeling**: semua bentuk dari extrude + loop cut + geser titik, dilihat dari depan/samping.
  Cincin-cincin skrip kita (`ref_body.py`) adalah versi otomatis dari cara ini (extrude = cincin berikutnya).
- **Sambungan kepala-leher**: jumlah titik loop harus sama, lalu disatukan. Sama dengan pelajaran leher v5
  ([[model-dari-gambar-referensi]]).
- **Tangan dan jari**: extrude per face dari buku jari, bukan bentuk mitten. Ini yang belum kita punya.
- **Baju dari duplikat face badan + Solidify**: cara murah untuk part modular (baju terpisah dari badan).
- Mata/alis/bibir **di tekstur**, bukan geometri: hemat poly. Kita sekarang bikin alis sebagai mesh.
- Rig: Rigify metarig + automatic weights + perbaikan weight paint di sendi. Kita punya rig F2 73 tulang
  sendiri; Rigify alternatif standar kalau model diekspor ke game engine.
- Gayanya **smooth shaded** (bukan flat faceted). Gaya bidang besar kita tetap: flat shading + sedikit loop
  ([[lowpoly-style-big-planes]] di memori).
