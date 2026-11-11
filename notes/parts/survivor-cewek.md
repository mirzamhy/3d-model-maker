---
tags: [cewek, kepala, rambut, badan, game, deadzone]
dibuat: 2026-11-10
versi: f2 dipilih user (jalur ref_body + baju loft); f3 = badan ramping sesuai angka, cadangan; f1 = loft tabung game_parts
---
# Survivor cewek (f1)

Permintaan user: "aku mau bikin versi cewek gunakan refrensi ini namun jangan terlalu jauh style dengan model sebelumnya".
Referensi: `notes/attachments/ref/survivor_f/` (turn sheet, depan bertekstur, wire kepala, depan T-pose):
kaos hijau zaitun pas badan lengan pendek, celana kargo coklat dengan saku paha, bot karet abu tinggi, rambut cepol + dua helai depan.

## Prinsip
- **Gaya tetap = survivor cowok**: bidang besar, bibir, celah mata, telinga v13 sama. Yang beda hanya titik dan penampang.
- **Rangka game sama** (panjang tulang dipakai bersama): cewek = penampang part lebih ramping, bukan rig baru.

## Kepala (`tools/blender/head_female.py`)
- Kepala v17 + offset landmark `FEMALE` (px trace): rahang ramping, dagu kecil runcing, hidung lebih kecil dan kurang menonjol,
  rak alis lebih lembut, mulut lebih kecil, leher tipis.
- Rambut: generator v17r dengan `HP_F` (sisir ke belakang, massa tipis rata, tanpa duri), + **cepol** icosphere 1x subdiv
  (80 tris, jitter kecil) di atas-belakang, + **dua helai depan** (prisma meruncing dari pelipis ke tinggi rahang, di depan telinga).
- v1: telinga hilang (salinan `EarsBase` ikut `hide_render`), cepol terlalu kecil/rendah. v2: cepol pusat (0, 0.118, -0.062), r 0.056.
- Keluaran: `output/head-game/template/head_f1.blend` (objek Head, Hair, Eyes, Ears seperti v17, bisa dibaca `game_parts.head_parts`).
- ![[female_head_v2.png]]

## Badan (`game_parts.parts_body_f`)
- Kaos pas: pinggang 0.106 (cowok 0.140), dada depan maju (rzf 0.134 di y 0.245), bahu sempit, kerah rib.
- Celana: pinggul lebar (0.158), paha ramping, saku kargo kotak di sisi luar paha, ujung celana menggembung lalu masuk bot.
- Bot karet tinggi: batang sampai mata kaki + 0.21, kaki lebih kecil. Lengan, tangan, leher lebih ramping.
- **Saku hanya sisi luar (+x)**: paha kiri butuh mesh dicerminkan (scale x −1). Mesh simetris memberi saku di sisi dalam juga (jelek).
  Di game ini berarti part paha kiri terpisah atau instance dengan skala negatif (belum dibuat).
- Preview T-pose `tools/blender/body_preview.py` (cowok kiri, cewek kanan; depan, samping, 3/4, belakang).
  v1 framing terpotong, saku melayang; v2 bentuk masih seperti tabung; v3 pinggang/pinggul + bot tinggi:
  ![[female_body_v3.png]]

## v4–v6: proporsi dari referensi (2026-11-10)
User: "polish lagi kepalanya sedikit terlalu besar coba perhatikan refrensinya kemudian badan model model ini kok jadi aneh".
- Ukur `front.webp` di grid 50 px (tinggi ubun–sol 1265 px = 1.87 m, 0.00148 m/px). Penyebab "aneh" = **proporsi rangka game**,
  bukan hanya bentuk part:

| | referensi | rangka game (v3) |
|---|---|---|
| pinggul | 0.98 m | 0.92 |
| lutut | 0.56 m | 0.50 (betis pendek) |
| bahu | 1.47 m | 1.39 (badan + leher panjang) |
| lengan bahu–pergelangan | ~0.40–0.50 | 0.56 |
| kepala / tinggi | 15 % | 16 % (terasa besar karena bahu rendah) |

- `game_parts.PROP0` = rangka game sekarang, `PROP_REF` = upperArm 0.26, forearm 0.23, thigh 0.44, shin 0.47, torso 0.48,
  shoulderY 0.405. `rescale()` meregang part sepanjang tulang. Kepala cewek `HEAD_S` 1.2 (cowok 1.3), dulu 1.35.
- Badan cewek v4–v6: celana kargo longgar (paha r 0.104, lutut 0.086, menggembung di atas bot), pinggul 0.172, kelim kaos melebar,
  **lengan telanjang kurus (warna kulit) + part `sleeve` terpisah** di tulang lengan atas (lengan kaos pendek, mulai 5 cm di dalam bahu;
  v4 mulai di sendi dan terbaca manset lepas), bahu kaos diteruskan sampai sendi lengan, pinggang celana tidak menembus kaos.
- Cek dengan **render yang diselaraskan**: `body_preview.py --match` merender cewek dengan skala/pusat sama dengan `front.webp`,
  lalu ditempel referensi | model | overlay 50 %: ![[female_match_v6.png]]
- Lembar cowok + cewek proporsi baru: ![[female_body_v6.png]]
- **Masuk game = ubah `BONES` di `tiktok/game/src/render/parts.ts`** (berlaku untuk semua aktor, termasuk zombie) atau rangka per karakter.
  Belum dilakukan. Part baru cewek: `sleeve`, paha kiri cermin.

## f2: jalur yang sama dengan survivor cowok (2026-11-10)
User: "bukankah kita sudah buat beberapa model yang kaya gini?" → bangun ulang di jalur utama:

```bash
# 1. siluet + landmark dari lembar cewek (bayangan lantai: ambang 0.18, sol dipotong, celah kaki tidak diisi)
REF_IMG=notes/attachments/ref/survivor_f/turn_sheet.webp REF_TAG=survivor_f REF_HEIGHT=1.75 REF_THRESH=0.18 REF_MAX_HOLE=600 REF_ARMPIT_STEP=3 REF_VIEWS='{"front":[40,455,8,436],"right":[462,642,8,436],"back":[642,1045,8,436],"left":[1050,1225,8,436]}'   blender -b --factory-startup -P tools/blender/ref_measure.py
# 2. kepala cewek + tusuk leher Head_Main dari head_lp_v6 (paint_keep: warna sendiri)
blender -b --factory-startup -P tools/blender/head_combine.py -- head_f1.blend head_lp_v6.blend head_f1n.blend
# 3. badan dari siluet (RB_HAIR 0.115 = rambut + cepol di atas tengkorak, kalau tidak kepala x1.46)
REF_TAG=survivor_f RB_TAG=ref_body_f2base RB_HEAD=output/head-game/template/head_f1n.blend REF_HEIGHT=1.75 RB_HAIR=0.115   blender -b --factory-startup -P tools/blender/ref_body.py
# 4. badan di bawah baju (siluet = kain)
blender -b ref_body_f2base.blend -P tools/blender/body_inset.py -- --joints joints_ref_body_f2base.json --out ref_body_f2inset.blend
# 5. cat, rig, baju
PAINT_SRC=.../ref_body_f2inset.blend PAINT_TAG=ref_body_f2inset_color PAINT_OUT=output/ref/survivor_f blender -b -P head_paint.py
blender -b head_ref_body_f2inset_color.blend -P rig_game.py -- --joints ... --out survivor_f2_rig.blend
blender -b survivor_f2_rig.blend -P clothes.py -- --out survivor_f2_dressed.blend --set loft_f
# 6. banding (env REF_* sama dengan langkah 1)
CMP_SRC=output/ref/survivor_f/survivor_f2_dressed.blend CMP_TAG=survivor_f2 blender -b -P ref_compare.py
```

- Alat diubah (bawaan tetap sama untuk cowok): `ref_measure` (REF_VIEWS, REF_THRESH, REF_MAX_HOLE, REF_ARMPIT_STEP,
  lewati bayangan kontak di antara sol), `ref_body` (RB_HAIR), `ref_compare` (REF_IMG), `garment_loft` (`fit`, `waist_z`),
  `clothes` (set `loft_f`: kaos pas lengan pendek zaitun, kargo coklat, bot karet abu).
- **Badan dari siluet berpakaian**: kaki keluar setebal celana kargo. `body_inset.py` mengecilkan kaki ke sumbu tulang
  (0.68–0.86) dan pinggul/pinggang (0.86–0.97); celana mengembalikan volume.
- **Bahu = lengan kaos**: ketiak terdeteksi di tepi lengan kaos (x 0.23), baris atas bahu datar sampai x 0.23 lalu turun
  3.6 cm ke lengan. User: "kok tanganya gini bro ga nyatu beda ukurannya". Perbaikan: radius di sekitar sumbu lengan dibatasi,
  menyempit dari bahu (x 0.12) ke lengan telanjang (+20 % deltoid): ![[female_f2_shoulder.png]] (atas sebelum, bawah sesudah).
- Kaos loft cowok jatuh lurus dari dada (kotak). `fit` 0.75 + cincin pinggang 1.12: kaos ikut pinggang.
  Celana 0.027 di paha terbaca celana berkuda → 0.014 / lutut 0.016 / gumpalan atas bot 0.022.
- Hasil: ![[survivor_f2_cmp.png]] badan 656 + kaos 912 + celana 756 + bot 440 + kepala.
- Kurang: saku kargo tidak terlihat (bump 2 pita paha), pinggul celana masih lebar, cepol lebih kecil dari referensi,
  garis tipis tembus di punggung bawah. Belum diuji pose (E4) dan belum dipotong per tulang untuk game.

## f3: badan disesuaikan ke kepala (2026-11-10)
User: "coba recreate ulang badanya sesuaikan sama ukuran kepala". Ukur lebar siluet per tinggi (render banding vs mask referensi):
- **Bahu 0.49 m**: ketiak terbaca di ujung lengan kaos (x 0.231), lengan dibangun mulai dari situ. Kepala (lebar 0.15)
  terlihat kecil di atas bahu selebar itu. Fix `ref_body` env `RB_ARMPIT_X=0.16` (ketiak asli); di dalam lengan kaos
  tebal lengan = tebal tepat di luar ketiak lama (`sleeve_x`), lalu `body_inset` memangkas ke lengan telanjang
  (batas radius 0.085 di x 0.12 -> deltoid 1.3x -> lengan).
- **Pinggang 0.27 m vs 0.22 di referensi**, samping 0.22 vs 0.17: `body_inset --profile f3` (lebar 0.75-0.86, tebal 0.70-0.80
  di 1.00-1.15 m), kaos `fit` 0.92, set `loft_f3` (lengan kaos x 0.10-0.242, berhenti di ujung lengan kaos referensi).
- Hasil: lebar badan depan/samping 1.0-1.25 m dalam 1 cm dari referensi. ![[survivor_f3_cmp.png]]
- Sisa: kepala tetap lebih sempit dari referensi (0.15 vs 0.26 m dengan rambut): rambut referensi mengembang di samping
  dan cepolnya besar, kepala kita rambutnya menempel tengkorak.
- User menilai gambar banding **f2** (bahu lebar, lengan kaos panjang): "bagus ini sih" (2026-11-10). f2 dan f3 sama-sama disimpan. **User memilih f2 sebagai dasar** (bahu lebar dan lengan kaos panjang lebih disukai daripada f3 yang sesuai angka referensi).
- Perintah: sama dengan f2, plus `RB_ARMPIT_X=0.16`, `body_inset.py -- --profile f3`, `clothes.py --set loft_f3`.

## f2 dipotong per tulang (2026-11-10)
Sketsa user (struktur part): kepala (C/1), leher (D/2), badan (3), lengan atas (4, 5), lengan bawah (6, 7), tangan (8, 9),
panggul (10), paha (11, 12), betis (13, 14), kaki (15, 16). Leher = tiang terpisah, lereng bahu ikut badan, lengan dipotong tegak
di ujung bahu. Badan satu part (garis tengah sketsa = garis bentuk, bukan potongan; rangka game torso satu tulang).
User: "ya coba lakukan dan perhatikan detail kepala dan lehernya".

`tools/blender/cut_parts.py` (dressed .blend -> `survivor_f2_parts.blend`, 16 objek, 3896 tris), cek `tools/blender/parts_pose.py`:
- Face -> part dari bobot tulang terbesar (jari -> tangan, toe -> kaki, shoulder/spine/chest -> badan). Tiap part di-parent ke tulangnya
  (kaku, tanpa skin). Potongan terbuka ditutup (`holes_fill` lalu **poke** jadi kipas: tutup panjang tak datar yang dipecah sudut ke
  sudut terlipat keluar garisnya).
- **Kepala**: Head + Hair + Eyes + Ears. Tabung leher tipis bawaan template kepala (sisi di bawah rahang + tutup bawah z 1.376)
  dibuang, kepala berhenti di rahang. **Leher** = tiang leher badan (kode part 0 + 2) yang masuk ke dalam tengkorak; cincin bawah
  turun 3 cm ke dalam badan. Menoleh 35° dan menunduk 25°: tanpa celah. ![[survivor_f2_neck.png]]
- **Lengan kaos** = pulau mesh sendiri -> lengan atas (bukan bobot: pangkalnya berbobot dada). Pangkal yang terselip di badan
  berayun keluar seperti bantalan bahu saat lengan turun (sendi x 0.246): dipotong di |x| 0.19 (0.215 = jadi gelang lengan).
- Kulit lengan (kode 3) tidak pernah ke badan.
- **Bahu v5** (user: "rapikan bahu dulu"): v4 = lengan kaos dipotong di 0.19, tapi sendi masih di x 0.246 (ujung lengan kaos):
  lengan berayun di titik di luar bahu, sudut bahu kaos menonjol. ![[survivor_f2_parts_v4.png]]
  Fix: sendi `upper_arm` dipindah ke x 0.20 (`CP_SHOULDER_X`) di sumbu lengan; semua titik lengan atas di dalam sendi diproyeksikan ke
  **kubah** di sekitar sendi (jarak tiap titik = jaraknya ke sumbu lengan, dinding kaos tetap tebal), r 0.047; titik badan di luar
  sendi ditarik ke 0.95 r. Kubah yang diputar di pusatnya sendiri tidak berubah bentuk: lengan turun, bahu tetap rapi.
  Lengan kaos tidak dipotong lagi. ![[survivor_f2_parts.png]]
- Pose uji (rotasi sumbu dunia di frame diam tulang): diurai, lengan turun + menoleh, jalan, jongkok. ![[survivor_f2_parts.png]]
- Sisa: pinggul celana terlipat
  saat jalan/jongkok. Belum diekspor ke JSON game (panjang tulang f2 beda dengan `BONES` game).

## f2b: lengan dan bahu dari mask yang benar (2026-11-10)
User: "recreate again lengan dan bahu terlalu kecil cek ulang dan cari refrensi buat membangun".
- Ukur tebal lengan (view depan, per x) model vs mask: sama (0.055-0.067 m). Tapi piksel lembar asli dengan ambang 0.05-0.07:
  **lengan referensi 0.072-0.084 m**. Ambang 0.18 (untuk bayangan lantai) memotong 1-1.5 cm tiap tepi kulit terang di latar putih.
- Fix `ref_measure`: `REF_THRESH_TOP=0.05` hanya di zona lengan (kolom > `REF_ARM_COL` 45 px dari tengah crop, 70 % atas).
  Ambang rendah di seluruh badan membaca bayangan di antara kaki: selangkangan 0.77 -> 0.665 m.
- Bangun ulang dengan perintah f2 (`T=f2b`, `loft_f`): lengan telanjang 0.94-1.00x referensi (dulu 0.76-0.93), r lengan 0.037
  (dulu 0.027), kubah bahu r 0.060 (dulu 0.047). Pergelangan terdeteksi di 0.632 (dulu 0.678).
  ![[survivor_f2b_cmp.png]] ![[survivor_f2b_parts.png]]
- Referensi anatomi (web): lebar bahu perempuan ~2x lebar kepala (sumber berbeda 1.5-2.5); tebal lengan atas tidak ada di panduan
  gambar, jadi diambil dari lembar referensi.

## Belum
- Belum dinilai user. Belum diekspor ke `survivor_parts.json` / game (perlu key part cewek + paha kiri cermin di `actors.ts`).
- Dada hanya terbaca dari samping; tekstur kusam di referensi tidak dipakai (gaya kita warna rata).

## Pelajaran
- **Salah langkah f1**: badan dibangun dari loft tabung `game_parts.parts_body` padahal sudah ada badan yang lebih baik:
  [[badan-quad]] (`body_quad.py`, topologi quad, bentuk + rig dari F2) dan [[baju-loft]] (kaos v17a `garment_loft.py`).
  User: "bukankah kita sudah buat beberapa model yang kaya gini?". Langkah 1 skill (cek yang sudah ada) dilewati.
  Versi cewek berikutnya harus mulai dari badan quad + kaos loft, baru dipotong per tulang untuk game.
- Varian karakter di rig bersama = ubah penampang loft, bukan panjang tulang. Tapi kalau badan terasa "aneh", ukur proporsi tulang dulu:
  bentuk part tidak bisa menutupi kaki pendek / lengan panjang.
- Siluet berpakaian: ketiak = ujung lengan kaos. Cek lebar bahu dengan angka (bahu > 2.5x lebar kepala = salah ukur).
- Banding badan dengan overlay di skala referensi, bukan dengan mata: v3 terlihat "oke" tapi kaki 8 cm kurang.
- Lengan kaos pendek di rig per tulang: lengan = kulit, kaos = part sendiri di tulang yang sama (satu part = satu warna tint).
- Detail asimetris (saku satu sisi) tidak bisa di mesh yang dipakai kiri-kanan; butuh mesh cermin.
- Salinan objek ikut flag `hide_render` dari sumbernya.
- Mask siluet: kulit terang di latar putih butuh ambang rendah. Cek tebal part dengan profil piksel asli, bukan hanya mask.
- Part kaku: pangkal yang terselip di dalam part induk ikut berputar di sendi dan menonjol keluar. Sendi harus di dalam badan, dan pangkal part = kubah di sekitar sendi (bentuk tetap saat berputar).
- Pose uji part kaku: tulis rotasi dalam sumbu dunia lalu ubah ke frame tulang (`M⁻¹ R M`); sumbu lokal tulang tidak bisa ditebak.

## f2c: sendi lengan (2026-11-10)

Keluhan: "masih ga nyambung lengannya kamu sendinya gimana".

Penyebab (diukur):
- Part dibagi menurut bobot rig. Bobot siku sengaja melebar ke lengan bawah (engsel untuk tekukan halus), jadi
  potongan jatuh di x 0.53, padahal tulang siku di x 0.447 (tepat di cincin siku mesh). Lengan bawah berputar di
  titik 8 cm di dalam part lengan atas: saat ditekuk ia bergeser lepas, dan 8 cm kulit lengan bawah tetap lurus
  menempel di lengan atas.
- Ujung siku dan pergelangan ditutup datar: menganga saat ditekuk.

Perbaikan (`cut_parts.py`):
- `chain_part`: face lengan atas / lengan bawah / tangan dibagi menurut posisinya di sumbu lengan, dipotong tepat
  di kepala tulang (siku, pergelangan). Potongan sekarang 0.000 dari titik putar.
- `ball_caps`: kedua ujung tiap sendi (siku, pergelangan, lutut) jadi setengah bola dengan pusat di titik putar:
  pita ke ekuator, satu cincin di 50°, ujung. Bola diputar di pusatnya tetap pas, jadi sendi tertutup di sudut
  berapa pun. 4368 tris (+~500).
- QA: `survivor_f2c_arm.png` (close-up lengan kiri, 4 pose x depan/samping/belakang; `parts_pose --arm`),
  `survivor_f2c_parts.png`.

Pelajaran:
- Part kaku: potong di **titik putar tulang**, bukan di batas bobot. Bobot skinning sengaja kabur di sendi.
- Tutup sendi = setengah bola di titik putar, di kedua part. Tutup datar hanya untuk ujung yang tidak berputar.

## f2c: pinggul (2026-11-10)

Keluhan lama: pinggul celana terlipat saat jalan/jongkok. User: "Ya, pinggul".

Penyebab: bobot rig membawa part paha sampai pinggang (z 0.86; titik putar pinggul z 0.788). Bokong dan sisi
pinggul ikut berputar dengan paha dan terlipat keluar saat jongkok. Pinggul tinggal lempeng 8 cm.

Perbaikan (`cut_parts.py`):
- `leg_part`: potongan miring seperti celana pendek action figure: depan 2 cm di bawah titik putar (`HIP_FRONT`),
  belakang turun 9 cm sampai lipatan bokong (`HIP_BACK`), sisi turun 4 cm (`HIP_SIDE`). Bokong tetap di pinggul.
- Paha atas = setengah bola di titik putar pinggul (`ball_caps`, cari lubang dalam 13 cm), jari-jari dibatasi
  `HIP_R` 0.075 supaya muat di dalam pinggul. Tanpa batas, bola selebar paha atas (12 cm) menonjol di sisi pinggul
  saat berdiri.
- Bawah pinggul satu lubang (dua kaki): tutup datar, bukan bola.
- 4540 tris. QA: `survivor_f2c_hip.png` (`parts_pose --hip`: 4 pose x depan/samping/belakang/3-4 belakang).

Sisa: jongkok 100° tampak kotak di belakang (pinggul seperti celana pendek, bawahnya gelap); ujung bawah kaos
terlihat gelap dari bawah saat badan membungkuk.

Pelajaran:
- Pinggul part kaku: bokong ikut pinggul, potongan miring (rendah di belakang). Bola paha dibatasi lebar soket.

## f2e: bahu kembali miring (2026-11-11)

Keluhan: "lengan dan bahu kok berbeda dari sebelumnya". Bahu f2b/f2c kotak, rata setinggi lengan; lengan kaos
seperti balok terpisah. Sudah begitu di mesh utuh (bukan karena dipotong).

Penyebab: ambang rendah `REF_THRESH_TOP` (dipakai untuk lengan sejak f2b) berlaku mulai 45 px dari tengah, jadi juga
menangkap bayangan tipis latar di atas bahu. Celah leher-lengan terbaca penuh, pangkal lengan (`arm_col` di x_root)
terukur setinggi bahu, baris trunk atas ikut naik: bahu rata.

Perbaikan: `REF_ARM_COL=80` (ambang rendah hanya di luar ujung lengan kaos, lengan telanjang). Ukur ulang, bangun
f2e (`SET=loft_f INSET="" T=f2e`). Bahu = f2, lengan telanjang r 0.0354 (f2 0.027, f2b 0.037), kubah bahu r 0.047.
QA: `survivor_f2_f2b_f2e_shoulder.png`, `survivor_f2e_cmp.png`, `survivor_f2e_parts.png`.

Pelajaran: ambang mask yang dilonggarkan untuk satu bagian harus dibatasi ke kolom bagian itu saja; cek baris
tetangga (bahu) ikut berubah atau tidak.

Catatan user soal sambungan: render referensi dan `survivor_f2_cmp` = satu mesh skinned, jadi menyatu. Part kaku
per tulang (format game sekarang) selalu punya sambungan; paha-bokong paling kelihatan karena pinggul berputar besar.

## f2e: pinggul-paha ikut sketsa user (2026-11-11)

Keluhan: "pembuatan pahamu patah coba buat ulang ... yang awal itu konsepku jadi sesuaikan kembali".

Penyebab: potongan f2c kebalikan dari sketsa. Pinggul menggantung seperti rok sampai lipatan bokong, paha masuk dengan
bola kecil (r 0.075): saat jalan/jongkok rok diam, paha keluar dari bawahnya = terlihat patah.

Sketsa (QA `images/24.jpg`): pinggul (10) = pita pinggang sempit, V ke selangkangan; paha (11/12) mulai tepat di bawahnya
dan membawa sisi pinggul + bokong.

Perbaikan (`cut_parts.py`):
- `leg_part`: garis celana dalam, z selangkangan `HIP_CROTCH` 0.77 di tengah naik ke `HIP_SIDE_Z` 0.80 di |x| 0.15.
  (0.835 terlalu tinggi: celana hanya punya cincin z 0.862 dan 0.788, sisi pinggang masuk paha, celah putih di samping.)
- `dome_axis`: titik paha di atas titik putar (sepanjang sumbu paha) ke kubah di sekitar titik putar, seperti bahu.
- Bola pinggul dihapus. 4344 tris. QA: `survivor_f2e_hip.png`, `survivor_f2e_parts.png`.

Sisa: jongkok 100° tetap kotak di belakang (batas part kaku).

## f2g: pemotong baru `cut_rigid.py` (2026-11-11)

Keluhan: "coba carikan refrensi rig tubuh deh aku bingung dan potonganmu juga aneh".

Referensi:
- Karakter bersegmen PS1/N64: tiap bagian satu objek, satu tulang, tanpa weight paint; sambungan disembunyikan
  dengan geometri tumpuk ([itch devlog](https://flynn-delta.itch.io/kit207-portfolio/devlog/565388/self-study-2-animation),
  [Polycount](https://polycount.com/discussion/comment/2758265)). Ujung part mengecil dan tumpuk sedikit di sendi
  ([OverScore](https://overscore.media/posts/low-poly-character-rigging-with-blender-and-mixamo)).
- Roblox R15 (15 part kaku): tiap anggota badan tertutup sendiri (tutup bulat/datar), part boleh tumpuk
  ([docs](https://create.roblox.com/docs/avatar/character-bodies.md)).
- Action figure: pinggul = sendi bola; untuk berlutut perlu bola, bukan potongan lurus
  ([Yakface](https://yakfaceforums.com/main/2019/01/06/hyper-articulated-hips/)).

Tiga aturan: (1) bola di bahu dan pinggul (ujung anak setengah bola di titik putar, masuk ke induk); (2) engsel di
siku, pergelangan, lutut, pergelangan kaki (kedua ujung setengah bola, tumpuk); (3) potong dengan bidang lurus lewat
titik putar.

Penyebab "aneh": `cut_parts.py` memilih part per face. Mesh baju kasar (celana hanya cincin z 0.862 dan 0.788 di
pinggul) jadi garis potong mengikuti tepi face, zig-zag, bukan garis di titik putar.

`cut_rigid.py`: `bisect_plane` lewat tiap titik putar (hanya face di zona sendi itu), part dari posisi geometris
(bahu/siku/pergelangan sepanjang sumbu lengan, V celana dalam z 0.77 + 0.2|x|, lutut dan pergelangan kaki sepanjang
sumbu tulang kering), kaos = badan, celana = pinggul (ujung kaos menutup pinggang). Satu bola per sendi dari lapisan
terluar (`ball_caps(..., taken)`: bot, celana, kaos, kulit; baju punya dua lapis). Bola pergelangan kaki maks 5 cm
(titik putar 9 cm di atas sol). Kepala/leher tetap dari `cut_parts`. 5552 tris.
QA: `survivor_f2g_parts.png`, `survivor_f2g_hip.png`, `survivor_f2g_arm.png`.

Sisa: ujung bola lutut runcing saat jongkok 120°; lubang kecil kulit di sisi ujung kaos saat membungkuk.

## f2h: lutut bulat (2026-11-11)

Keluhan: lutut runcing saat jongkok (user: "lanjut rapikan lutut").

Penyebab: bola sendi = satu cincin di 50° lalu kerucut ke satu titik ujung. Lingkar celana di lutut tidak bulat
(pusatnya bukan di titik putar), jadi kerucutnya jadi duri saat lutut ditekuk 120°.

Perbaikan (`cut_parts.ball_caps`, dipakai `cut_rigid`): cincin di `BALL_RINGS` (35°, 70°), jari-jari tiap cincin
makin ke kutub makin mendekati rata-rata (bulat), kutub ditutup n-gon datar, tanpa titik ujung. Uji satu cincin 45°:
5512 tris tapi lutut jongkok kotak; dua cincin dipakai, 5984 tris. `parts_pose --knee`: close-up lutut kiri.
QA: `survivor_f2h_knee.png`, `survivor_f2h_parts.png`.

Sisa: saat jalan (lutut 50°) bagian bawah paha sedikit menonjol seperti bibir di depan lutut.
