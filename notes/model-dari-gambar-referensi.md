# Model baru dari lembar referensi (siluet → cincin quad)

Status: badan v1 (3 Nov 2026), menunggu penilaian. Kepala, rambut, otot, dan rig belum.

Permintaan user: bangun **model baru** seperti lembar "Zombie Apocalypse Survivor – Base Model"
(4 view T-pose, part terpisah). Pelajari tiap bagian dari gambar, perkirakan kedalaman, seperti langkah
platform AI image-to-3D ([[pipeline-ai-image-to-3d]]). Model kita sendiri dipakai sebagai bantuan.

![[ref/survivor_sheet.webp]]

## Pipeline kita vs platform AI
| Platform AI | Kita |
|---|---|
| gambar multi-view | sudah ada: depan, kanan, belakang, kiri |
| perkiraan depth (jaringan saraf) | **visual hull**: lebar dari siluet depan, tebal dari siluet samping |
| mesh otomatis | cincin quad yang dirancang (layout [[parts/badan-quad]]) |
| bagian tak terlihat | prior: superellipse untuk sudut, proporsi F2 untuk tebal lengan/tangan |

## Langkah
1. `tools/blender/ref_measure.py`: mask tiap view (selisih terang dari latar), isi lubang (rambut/mata gelap
   = mirip latar: yang tidak tersambung ke tepi = tubuh), landmark: tengah badan, selangkangan, ketiak
   (lebar badan melompat saat bergabung lengan), puncak bahu, dagu (leher tersempit), sumbu lengan dan kaki,
   mata kaki (kaki tersempit di atas telapak). Skala: tinggi 1.78 m = tinggi mask depan.
   Cek: tinggi 4 view 320–324 px (selisih < 1 %) → view konsisten, bisa dipakai.
   ![[ref/survivor_landmarks.png]]
2. `tools/blender/ref_body.py`: per tinggi y, "sinar" lewat mask: run depan → setengah lebar, run samping →
   depan/belakang. 4 titik sumbu dari siluet, titik diagonal dari superellipse (n = 2.6). Lengan: tebal
   vertikal dari view depan, kedalaman = 0.95 × tebal (prior F2). Kaki: run depan per kaki, run samping.
   Telapak: profil tinggi dari siluet samping. Topologi sama dengan badan quad (10 kolom, lubang lengan 8,
   mitten, selangkangan quad).
3. `tools/blender/ref_compare.py`: render ortografik 4 arah, skala dan tanah sama, di bawah crop referensi.

Hasil v1: 2002 segitiga (dengan kepala placeholder), tertutup, simetris.
![[ref/survivor_body_v1_cmp.png]]

## Pelajaran
- **Pita lengan menutupi dada di view samping** (T-pose: lengan terlihat ujung, tangan di depan dada).
  Depan/belakang badan di tinggi itu diinterpolasi dari baris di atas dan bawahnya.
- **Mencari tengah badan di baris 55 % tinggi salah**: di gambar ini kaki sudah terpisah di sana. Pakai 42 %.
- **Lompatan lebar dari selangkangan ke pinggul** mirip ketiak; cari ketiak mulai 15 % tinggi di atas selangkangan.
- **Bintik kecil di bawah ketiak** membelokkan sumbu lengan; pilih run yang tebalnya > 2 cm.
- **Mata kaki bergaya**: kaki besar, bagian tersempit di 0.19 m, bukan 0.075 m proporsi umum. Ukur, jangan pakai rata-rata.
- **Cahaya**: scene kepala (area light dekat kepala) bikin badan bawah gelap bergradasi → render banding pakai
  cahaya matahari rata, kalau tidak bentuk tidak terbaca.

## Belum
Otot dada/perut/punggung (siluet tidak melihatnya; berikutnya: garis bayangan dari view depan jadi loop),
takik gelap depan leher, telapak kaki dari depan masih balok, jari (sekarang mitten), kepala + rambut (part
berikutnya), rig + bobot per cincin.

Terkait: [[pipeline-ai-image-to-3d]], [[parts/badan-quad]], [[konsep-part-modular]].

## v2: otot = pahat rapat, lalu decimate (3 Nov 2026)
Skrip `tools/blender/ref_detail.py` (setelah `ref_body.py`). Siluet tidak bisa melihat otot, jadi otot ditaruh
sebagai peta anatomi di koordinat landmark, lalu dipahat:
1. **Subdivisi badan saja, 2x**, dengan `smooth` (vertex lama tetap di siluet, vertex baru membulatkan cincin 8).
   Edge cincin leher tidak dipecah, jadi kepala tidak tersentuh.
2. **Otot = geser sepanjang normal**: jumlah tonjolan (+) dan alur (-) Gaussian. Badan pakai (|x|, y) + arah
   hadap dari normal (depan/belakang); lengan dan kaki pakai (posisi sepanjang tungkai, sudut di sekelilingnya).
   Dada, garis bawah pec, sternum, 6 kotak perut, linea alba, garis V, punggung (tulang belakang, belikat, lats),
   bokong, deltoid, biseps/triseps, paha depan, tetesan air di atas lutut, tempurung lutut, betis.
3. **Decimate collapse** ke ~5200 tris. Edge yang tersisa mengikuti bentuk otot: ini yang memberi tampilan segitiga
   bersegi seperti referensi. Kepala dan cincin leher dikunci dengan vertex group bobot 0.

Pelajaran:
- Amplitudo anatomi "asli" (5-11 mm) **tidak terbaca** di low poly + cahaya rata. Perlu dilebih-lebihkan ~1.8x
  (`RD_GAIN`). Gaya stylized = otot dibesarkan.
- Opsi simetri di decimate **tidak eksak** (506 vertex tak berpasangan). Solusi: setelah decimate, `bmesh.ops.symmetrize`
  (sisi +x dicerminkan).
- Gelembung lengan bawah datang dari siluet, bukan dari peta otot: cek sumber bentuk dulu sebelum mengubah angka.

![[attachments/ref/survivor_body_v2_cmp.png]]
![[attachments/ref/survivor_body_v2_34.png]]

Sisa: kaki depan masih bola, tangan mitten, kepala dan rambut placeholder, rig belum.

## v3: leher, betis, kaki (feedback user 3 Nov 2026)
Keluhan: sambungan leher-kepala aneh, betis aneh, kaki aneh (minta kaki wedge low-poly sederhana).
Diagnosis dengan angka (`ref_body.Sil` vs mesh per tinggi), bukan tebakan:
- **Leher**: cincin leher template 4.5 cm terlalu depan dan terlalu kurus (setengah lebar 0.045 vs ref 0.058).
  Baris trapezius di bawahnya diambil dari siluet (sudah di belakang), jadi leher menekuk maju.
  Fix `fit_neck()`: geser + lebarkan vertex leher kepala ke siluet referensi di tinggi cincin, memudar ke atas.
  Tinggi pudar tergantung kedalaman: belakang 11 cm (sampai pangkal tengkorak, garis belakang leher lurus),
  tenggorokan 7 cm, dagu 0 (wajah tidak bergeser). Fade terlalu pendek di depan = tangga di tenggorokan.
- **Betis**: tonjolan dobel. Siluet samping sudah memuat betis, bokong, paha; peta otot menambah lagi.
  Aturan: **bagian yang terlihat di siluet hanya boleh dapat alur (-), tonjolan (+) hanya di tempat yang tidak
  terlihat siluet** (dada di balik lengan T-pose, perut, tempurung lutut).
- **Kaki**: wedge kotak (superellipse n=4): telapak rata, atas lurus dari punggung kaki ke ujung, ujung kotak.
  Dikunci di `ref_detail.py` (tidak disubdivisi, tidak di-decimate), kalau tidak smoothing membuatnya bola.

![[attachments/ref/survivor_v3_neck_side.png]]
![[attachments/ref/survivor_v3_calf_side.png]]
![[attachments/ref/survivor_v3_foot_side.png]]

## v4: kepala maskulin (part 1 dari lembar part modular, 3 Nov 2026)
Lembar target part (gambaran saja, angka poly tidak harus sama): ![[attachments/ref/parts_head.png]]
![[attachments/ref/parts_torso.png]] ![[attachments/ref/parts_arms.png]] ![[attachments/ref/parts_legs.png]]

Skrip `tools/blender/ref_head.py`: **satu medan deformasi ruang** `deform(x, y, z)` diterapkan ke semua objek
kepala (kepala, telinga, alis), jadi telinga tetap menempel tanpa dipasang ulang. Cincin leher (y = -0.172)
tidak disentuh, jadi colokan ke badan tetap sama. Isinya:
- rahang melebar ke arah sudut rahang (+16%), dagu lebar (+30%) dan sedikit maju;
- tengkorak dikotakkan: penampang xz didorong ke superellipse n=4 (diagonal x1.19, kekuatan 0.9);
  belakang tengkorak dipendekkan 10%; atas kepala diratakan;
- alis maju 4 mm, tulang pipi keluar 4 mm.
Badan v4 = `RB_HEAD=output/head-game/template/head_masc_v1.blend` di `ref_body.py`.

![[attachments/ref/head_masc_v1_sheet.png]]
![[attachments/ref/survivor_v4_head34.png]]

Sisa kepala: belakang tengkorak masih membulat, rambut belum ada (part terpisah).

## v5: leher baru (topologi, 3 Nov 2026)
User: "leher ga nyambung, bikin leher baru". Dulu badan dijahit ke tabung leher bawaan kepala template (tabung
lurus kurus), lalu tabung itu dipaksa digeser/dilebarkan (`fit_neck`). Sekarang:
1. **Pelajari loop dulu** (jalan dari cincin leher ke atas lewat edge, cetak tiap loop): tabung = 3 cincin bersih
   10 vertex (y -0.172, -0.153, -0.132). Loop di atasnya (bawah dagu ke pangkal tengkorak) punya vertex
   sisipan, jadi **tidak bisa dijahit** dengan 10 titik (hasilnya lubang + edge dipakai 4 face).
2. **Potong** 2 cincin bawah tabung (`cut_neck_tube`, `NECK_CUT_Y = -0.142`), simpan cincin bersih -0.132.
   Cincin itu dilebarkan ke **lebar leher tersempit** referensi (landmark depan), bukan lebar siluet di
   tingginya sendiri (di situ siluet depan = sudut rahang, bikin leher melebar seperti kerah).
   Belakangnya didorong setengah jalan ke garis tengkuk referensi (penuh = tonjolan di bawah tengkorak).
3. **Leher baru dibangun di badan**: cincin atas -> 1 cincin tengah -> cincin pangkal (dari siluet tepat di
   bawah bayangan rahang) = baris 0 badan. Cekungan tenggorokan di kolom 0, punggung otot SCM di kolom 22.
4. Leher **ikut dihaluskan dan di-decimate bersama badan** (`RB_NECK_PIN=0`): kalau dikunci quad sementara badan
   segitiga, sambungan terlihat seperti kerah. Yang dikunci cuma kepala dan kaki.
5. Penanda kunci sekarang atribut vertex `pin` dari `ref_body.py`, bukan tebakan tinggi.

Jebakan: **identitas BMVert tidak stabil** setelah operasi bmesh begitu mesh punya layer int. Set Python berisi
BMVert diam-diam berhenti cocok, kepala ikut disubdivisi + di-decimate. Kenali vertex terkunci lewat
koordinat (mereka tidak pernah bergerak). Juga: buat layer **sebelum** ambil referensi vertex (layer baru
membuat referensi lama basi: `ReferenceError`).
Skala kepala: dulu "dagu" yang terdeteksi ternyata cincin tabung -0.153; setelah tabung dipotong dikunci
konstanta `CHIN_T`.

![[attachments/ref/survivor_v5_neck34.png]]
![[attachments/ref/survivor_v5_neck_side.png]]

## Arah gaya: bidang besar sederhana, BUKAN pahat + decimate (feedback user 3 Nov 2026)
User kasih contoh leher low-poly simpel (prisma 2 segmen, bidang lebar, edge lurus ke bahu): "kok susah sekali".
Pass `ref_detail.py` (subdivisi, pahat otot, decimate) menghasilkan **sup segitiga acak**: tiap segitiga beda
arah, cahaya pecah, sambungan antar bagian kelihatan. Gaya target (lembar part + contoh ini) justru
**quad sedikit dengan edge yang disengaja**: tiap bidang = satu bentuk anatomi besar.
Keputusan: base `ref_body.py` (quad, 1938 tris) adalah jalur utama. Otot ditambah lewat **loop/potongan bidang
yang ditempatkan sengaja** (garis bawah dada, kotak perut) di mesh quad, bukan displacement + decimate.
`ref_detail.py` disimpan sebagai eksperimen.

![[attachments/ref/survivor_v5base_neck34.png]]
