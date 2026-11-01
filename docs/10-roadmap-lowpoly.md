# 10 — Roadmap: badan low-poly pria dan wanita

Tujuan tahap awal: badan dasar pria dan wanita tanpa aksesori yang tertutup rapat (solid, tidak tembus), bisa digerakkan penuh, dan bentuknya setara dengan contoh low-poly di Downloads. Detail, baju, rambut dan zombie datang sesudahnya.

## 1. Hasil membaca 6 file referensi

Semua file berupa FBX. Isinya diukur dengan FBXLoader di node.

| File | Isi | Tris per badan | Rig |
|---|---|---|---|
| casual-lowpoly-male-rig-t-pose | 1 pria, T-pose | 1552 | 37 node, 29 bone dipakai skin |
| low-poly-people-free-sample-pack | 8 orang (pria, wanita, nenek, anak, polisi, dokter) + rambut, kacamata, stetoskop | 1500–1930 | sama, 29 bone, animasi 6.7 s |
| polyart-zombies-with-animations | 5 zombie pria, 5 zombie wanita + rambut, topi | 1590–1990 | 30 bone (tambah `jaw`), animasi 7.4 s |
| low-poly-male-character | kepala + badan, rig Blender (Rigify-ish, jari lengkap, IK) | 2524 | 62 node |
| low-poly-hero-man | badan statis | 2272 | tidak ada |
| low-poly-muscular-male-base-mesh (Big dude) | badan berotot statis | 866 | tidak ada |

Pola yang sama di hampir semua contoh:

- **Anggaran segitiga**: badan lengkap 1.5k–2k tris, tinggi sekitar 1.82 m. Badan polos bisa serendah ~870 tris.
- **Rig kecil**: rantai Biped 3ds Max dengan ~30 bone: Pelvis, Spine, Spine1, Neck, Head, (Jaw), Clavicle, UpperArm, Forearm, Hand, jempol 2 ruas, empat jari digabung jadi satu "sarung tangan" 2 ruas, Thigh, Calf, Foot, Toe. Maksimal 4 pengaruh bone per vertex.
- **Satu rangka untuk semua**: pria, wanita, nenek, anak dan zombie memakai rangka yang sama, jadi satu animasi jalan di semua karakter.
- **Warna dari palet**: satu PNG kecil berisi kotak-kotak warna. UV tiap muka diarahkan ke satu kotak, jadi warnanya rata per bagian. Di proyek ini setara dengan vertex color per bucket.
- **Aksesori terpisah**: rambut, kacamata dan topi adalah mesh sendiri yang menempel kaku ke 1–2 bone (rambut ke Head). Stetoskop memakai 4 bone.

Model "Low-poly" kita sekarang memakai rangka 73 bone (jari lengkap, bone wajah). Untuk low-poly itu berlebihan. Rangka itu tetap dipakai untuk versi semi-realistis.

## 2. Pencerahan dari GitHub

- **[huxingyi/dust3d](https://github.com/huxingyi/dust3d)** (MIT, 3.6k bintang): modeling low-poly dari node/bola di sepanjang rangka, sudah ada rigging, animasi prosedural dan ekspor GLB/FBX. Idenya paling dekat dengan proyek ini: bentuk diturunkan dari rangka.
- **Makalah B-Mesh (Ji dkk. 2010)**: rangka 1D + bola di tiap simpul jadi base mesh quad dengan alur edge mengikuti tulang. Implementasi: [CorentinDumery/BMesh](https://github.com/CorentinDumery/BMesh) (C++) dan [revfactory/b-mesh](https://github.com/revfactory/b-mesh) (Three.js, MIT): loft 12 sisi untuk tangan dan kaki, SDF + Marching Cubes kecil di percabangan (bahu, panggul), lalu weld vertex dan Taubin smoothing. Cara inilah yang membuat mesh rapat di sambungan.
- **[MakeHuman / MPFB](https://github.com/makehumancommunity/mpfb2)** (GPL/AGPL): satu base mesh androgini yang dimorf jadi pria atau wanita dengan slider. Konsep ini dipakai di sini: **satu topologi, banyak parameter**. Kodenya tidak disalin karena lisensinya.
- **[naver/anny](https://github.com/naver/anny)**: model badan parametrik dari bayi sampai lansia dengan satu topologi. Konsepnya sama.
- **Bone heat (Baran & Popović 2007)**: skin weight otomatis, ada di [libigl bone_heat](https://libigl.github.io/dox/bone__heat_8h.html). Bisa jadi cadangan kalau weight per-ring kurang halus.
- **Linear blend skinning di three.js** menyebabkan efek "candy wrapper" (sambungan mengecil saat diputar). Jalan keluar yang murah adalah bone twist di lengan atas dan lengan bawah, plus loop ekstra di siku dan lutut.

Tidak ada repo di topik `low-poly` yang membuat karakter manusia prosedural siap-rig. Jadi generator tetap dibuat sendiri, dengan ide-ide di atas sebagai dasar.

## 3. Racikan yang dikejar

```
proporsi (tabel per gender) → rangka 30 bone → template topologi tunggal (cage)
   → bentuk dari profil ring per bone → weight per ring → palet warna → GLB
```

Kuncinya adalah **template topologi tunggal**. Badan tidak dirakit dari tabung-tabung yang saling tumpang tindih, karena itu sumber "tembus". Satu jaring tertutup dengan jumlah vertex tetap (~800 quad, ~1.6k tris) dipakai, dan posisi tiap vertex dihitung dari bone + profil ring. Pria dan wanita memakai jaring yang sama dengan parameter berbeda. Karena itu nanti morph, animasi dan aksesori cocok untuk keduanya.

## 4. Langkah berurutan

**F0 — Alat ukur referensi** (`tools/ref/measure-fbx.mjs`)
Membaca FBX dan mencatat tinggi, posisi sendi, profil lebar/tebal tiap ring per bone, jumlah tris per bagian, serta jumlah loop di sendi. Pria diambil dari casual_Male, wanita dari casual_Female, plus Big dude untuk badan berotot. Hasilnya `ref-profiles.json`. Ini dipakai sebagai acuan angka, bukan untuk menyalin mesh.

**F1 — Rangka low-poly 30 bone**
Memakai nama Mixamo (Hips, Spine, Spine1, Spine2, Neck, Head, Shoulder, Arm, ForeArm, Hand, Thumb1-2, "Mitten"1-2, UpLeg, Leg, Foot, ToeBase) supaya animasi Mixamo tetap bisa dipakai. Tabel proporsi pria dan wanita (tinggi, lebar bahu, panggul, panjang tungkai) diambil dari F0.

**F2 — Template badan pria tertutup rapat**
Satu jaring: torso 10–12 sisi, lengan 8, kaki 8, tangan sarung, kaki kotak. Sambungan bahu dan panggul dijahit dengan pola tetap (seperti di referensi), bukan union. Cek otomatis: tiap edge dipakai tepat 2 muka (manifold), tidak ada lubang, normal menghadap keluar, `side: FrontSide` (bukan DoubleSide).

**F3 — Weight dan uji gerak**
Weight per ring dengan 3 loop di siku dan lutut (sebelum, tengah, sesudah), bone twist lengan, dan maksimal 4 pengaruh per vertex. Uji pose otomatis: T, A, jongkok, tangan ke atas, siku 140°, lutut 150°, badan memutar, jalan. Yang diukur:
- jumlah tabrakan segitiga dengan dirinya sendiri (BVH);
- rasio volume sambungan sebelum dan sesudah ditekuk (target ≥ 0.85);
- muka terbalik;
- foto 4 view per pose.

**F4 — Varian wanita dan slider badan**
Topologi sama, parameternya berbeda: bahu, dada, pinggang, panggul, paha. Ditambah slider tinggi, berat dan otot (Big dude sebagai ujung "berotot").

**F5 — Loop "training"**
Siluet depan dan samping model kita dibandingkan dengan referensi (IoU piksel). Parameter digeser sampai skor stabil ≥ 0.9, lalu angka akhirnya dikunci di `bodySpec.ts`. Inilah "racikan" yang bisa dipakai ulang.

**F6 — Kepala**
Kepala low-poly dari file (`headFile`) dipasang ke badan baru, warnanya pakai palet. Leher dijahit ke jaring badan.

**F7 — Aksesori dan pendetailan**
Rambut, baju (shell offset dari badan + weight disalin dari badan terdekat), sepatu, lalu varian zombie (luka, warna, pose bungkuk). Argon dipakai untuk bagian yang butuh gaya 3D, dengan spesifikasi angka yang tepat.

**F8 — Ekspor dan uji animasi**
Ekspor GLB lalu jalankan animasi Mixamo (jalan, lari, idle) di viewer. Pemeriksaan F3 diulang.

## 5. Hasil F0 (selesai)

Alat:
- `node tools/ref/measure-fbx.mjs <out.json> <file.fbx> ...`: mengukur semua mesh badan (≥ 600 tris) di file. Hasilnya `tools/ref/out/ref-profiles.json`, berisi angka saja tanpa mesh. Isinya: tinggi, posisi sendi dalam nama Mixamo, segitiga per bone, jumlah loop, penampang 6 irisan per bone (dipotong lewat permukaan segitiga, bukan dari verteks), dan profil badan 40 irisan.
- `node tools/ref/summarize.mjs`: menghitung rata-rata per kelompok menjadi `ref-summary.json` (rasio terhadap tinggi badan) dan menggambar `ref-silhouettes.svg` (siluet depan dan samping semua badan).

Data: 22 badan, yaitu 9 pria (termasuk 6 zombie), 9 wanita (termasuk 5 zombie), 1 anak, dan 3 dari pack lain. Semua dalam T-pose, menghadap +z, kiri di +x. Nama jari dan tulang pada karakter duplikat (`Finger012`, `Spine003`) dipetakan lewat hierarki.

Rata-rata, dikali tinggi badan:

| Ukuran | Pria | Wanita |
|---|---|---|
| Tinggi rata-rata | 1.73 m | 1.68 m |
| Tinggi pinggul (Hips) | 0.509 | 0.545 |
| Tinggi dada (Spine1) | 0.669 | 0.658 |
| Tinggi leher | 0.842 | 0.837 |
| Tinggi lutut | 0.294 | 0.318 |
| Jarak sendi bahu | 0.204 | 0.205 |
| Jarak sendi panggul | 0.114 | 0.118 |
| Lengan atas / bawah / tangan | 0.146 / 0.143 / 0.067 | 0.137 / 0.135 / 0.058 |
| Paha / betis / kaki | 0.216 / 0.239 / 0.099 | 0.229 / 0.241 / 0.103 |
| Lebar dada maks | 0.190 | 0.173 |
| Lebar panggul maks | 0.188 | 0.193 |
| Lebar pinggang min | 0.181 | 0.159 |
| Lebar lengan atas / bawah | 0.057 / 0.045 | 0.047 / 0.033 |
| Lebar paha / betis | 0.083 / 0.062 | 0.096 / 0.056 |

Pembagian segitiga (rata-rata ~1650 per badan): kepala dan leher ~390, torso ~300–330, lengan ~305, tangan ~190–220, kaki (paha dan betis) ~250–280, telapak ~175. Loop per segmen: lengan atas 5–6, lengan bawah 5, paha 9, betis 6–7.

Yang membedakan wanita dari pria di data ini:
- pinggul lebih tinggi;
- pinggang jauh lebih ramping (0.159 vs 0.181);
- dada lebih sempit tapi panggul sedikit lebih lebar;
- lengan lebih kurus dan pendek;
- paha lebih tebal.

Jarak sendi bahu hampir sama di kedua kelompok.

Catatan:
- Kelompok pria ikut memuat zombie, karena di T-pose bentuknya hampir sama dengan pria biasa.
- Siluet depan di SVG menutup celah antar-kaki karena hanya batas kiri-kanan yang dicatat. F5 akan memakai render siluet sungguhan.

Perbaikan sesudah F0: rambut dan topi yang menyatu dengan mesh badan (misalnya topi dan sanggul polwan, atau rambut mengembang zombie_E) terdeteksi otomatis lewat kedalaman kepala > 26 cm atau lebar > 22 cm. Tinggi badan model seperti itu dihitung dari tulang Head ditambah 12.4 % tinggi badan (jarak rata-rata tulang Head ke ubun-ubun), dan ukuran kepalanya tidak ikut dirata-rata. Hasilnya, tinggi rata-rata wanita menjadi 1.669 m.

## 6. Hasil F1 (selesai)

- `tools/ref/summarize.mjs` sekarang juga menulis `src/zombie/lowbody/refBody.json`. Isinya:
  - posisi tiap sendi sebagai bagian dari tinggi badan, dengan sisi kanan dicerminkan ke kiri;
  - 6 penampang per tulang;
  - siluet rata-rata, per kelompok pria dan wanita.

  Jadi alurnya data → spec, tanpa angka yang diketik tangan.
- `src/zombie/lowbody/bodySpec.ts`: `bodySpec(femininity, height?)` mengubah data itu menjadi meter. `femininity` 0 berarti pria, 1 berarti wanita, dan nilai di antaranya dicampur. Slider untuk F4 sudah tersedia lewat parameter ini.
- `src/zombie/lowbody/rigLow.ts`: 37 bone, yaitu 30 bone yang menggerakkan mesh dan 7 penanda ujung. Namanya mengikuti Mixamo: Hips, Spine, Spine1, Spine2, Neck, Head, Shoulder, Arm, ForeArm, Hand, HandThumb1-2, HandMiddle1-2 (empat jari jadi satu sarung tangan), UpLeg, Leg, Foot, ToeBase. Spine2 disisipkan di 45 % jarak dada ke leher, karena di referensi dada hanya satu tulang panjang.
- `src/zombie/lowbody/mannequin.ts`: manekin kayu untuk mengecek rangka. Tiap tulang diwakili satu ellipsoid seukuran penampang hasil ukur. Garis siluet referensi digambar di belakang figur (biru untuk pria, merah muda untuk wanita) dan hanya tampil di T-pose.
- Viewer:
  - gaya **Rangka low-poly (F1)** menampilkan pria dan wanita berdampingan;
  - pose baru **Jalan normal**, **Jongkok** dan **Angkat tangan**, yaitu pose manusia tanpa bungkuk zombie.

Cek yang sudah dilakukan:
- Di T-pose manekin pas dengan garis siluet.
- Jongkok penuh: pinggul turun ke 0.34 m dan kaki tetap menapak.
- Angkat tangan: tangan naik sampai 1.93 m tanpa menyilang garis tengah.
- Jalan: tumit terangkat maksimal ±17 cm dan kaki tumpu tetap di lantai.

## 7. Hasil F2 (versi pertama)

`src/zombie/lowbody/body.ts` (gaya viewer **Badan low-poly (F2)**) membuat **satu jaring tertutup** dengan topologi tetap. Badannya 1248 segitiga dan memakai rangka 30 bone dari F1.

Susunan topologi:
- **Badan, leher, kepala**: ring 12 sisi dari selangkangan sampai ubun-ubun, ditutup satu titik di puncak.
- **Kaki**: ring paling bawah torso dibelah dua. Tiap kaki memakai setengah ring (7 titik) ditambah satu titik selangkangan bersama, jadi loop 8 titik. Tabung kaki tumbuh dari loop itu, lalu menekuk ke depan jadi telapak.
- **Lengan**: dari tiap sisi dada dipotong petak 2×2 quad, sehingga tersisa lubang dengan 8 titik tepi. Lengan tumbuh dari lubang itu sampai tangan sarung, dan ujungnya ditutup satu titik.
- **Jempol**: satu quad di tangan dipotong, lalu jempol 4 sisi tumbuh dari lubangnya.
- **Weight**: tiap ring punya bobot eksplisit. Tiga loop di siku dan lutut (sebelum, tengah 50/50, sesudah). Torso dibagi antar tulang Hips, Spine, Spine1, Spine2, Neck dan Head dengan campuran ±3 % tinggi badan di tiap sendi. Bahu ikut tulang Shoulder, pinggul samping ikut paha.

Bentuk tiap ring diambil dari data F0 lewat bodySpec. Profil torso adalah irisan horizontal segitiga torso referensi, yang ditambahkan ke `measure-fbx` (`torso`). Untuk tiap tulang dipakai 6 irisan beserta posisinya di sepanjang tulang. Penampang dihaluskan 1-2-1 dua kali di sepanjang tungkai. Tiga koreksi atas data mentah:
- Torso di bawah sendi Hips dilebarkan sampai membungkus paha, karena irisan torso tidak menghitung segitiga paha.
- Tiap jari-jari penampang minimal 45 % dari rata-ratanya, karena tempurung lutut tercatat ke tulang paha sehingga irisan betis di lutut bernilai negatif.
- Leher dibuat bulat dari irisan tulang Neck, karena irisan torso di situ mencampur dagu dan kerah.
- Dada ke leher:
  - Titik tengah depan dan belakang ring atas bahu ditarik setengah jalan ke ring leher dan diturunkan sedikit (cekungan tenggorokan 1.2 % tinggi badan, tengkuk 0.6 %). Dengan begitu dada melandai ke leher dan tidak berakhir sebagai kerah datar.
  - Ring bawah kepala dibuat miring (dagu lebih rendah, tengkuk lebih tinggi) dan dipersempit ke lebar rahang. Bagian belakangnya mengikuti leher, jadi tidak ada lis gelap di bawah kepala.
  - Kedua geseran dibatasi supaya selalu di atas ring di bawahnya. Tanpa batas ini badan wanita sempat punya 4 edge terbalik.

**Jari terpisah** (pengganti sarung tangan referensi):
- **Rangka**: `rigLow.fingerLayout` membagi sarung tangan hasil ukur (garis buku jari, panjang, lebar dan tebal tangan) menjadi empat jari: `HandIndex`, `HandMiddle`, `HandRing`, `HandPinky`, masing-masing ruas 1-3 ditambah penanda ujung.
  - Panjang relatif terhadap jari tengah: 0.93, 1, 0.94, 0.76.
  - Panjang ruas: 46 / 30 / 24 %.
  - Jari sedikit mengembang ke luar, dengan telunjuk ke arah jempol.
  - Total rangka 63 bone.
- **Mesh**: tangan diakhiri grid buku jari, 5 titik di punggung dan 5 di telapak. Grid itu disambung ke ring tangan 8 titik dengan pita segitiga (`bridge`). Tiap quad di grid jadi pangkal satu jari bersisi 4 dengan 5 ring, tiap ruas ada sambungan 50/50.
- **Jempol**: referensi memakai jempol sarung tangan yang terlalu gemuk untuk jari terpisah, jadi dikecilkan ke 0.7–0.75×.
- **Arah normal**: arah segitiga sekarang dirapikan lewat topologi (disebar ke tetangga lewat edge bersama), lalu arah keseluruhan dicek dengan volume bertanda. Penebak titik-dalam saja gagal di pita buku jari yang pipih.
- **Hasil**: 1524 segitiga per badan, tetap tertutup. Pose menyerang menunjukkan jari menekuk per ruas.

Cek otomatis `checkClosed` (hasilnya bisa dibaca di `globalThis.__lowbodyCheck`): pria dan wanita sama-sama 0 edge terbuka, 0 edge dobel, 0 edge terbalik.

Uji pose (render di `renders/f2_*.png`): jongkok, angkat tangan dan jalan. Kulit ikut menekuk sebagai satu jaring tanpa robek.

Sisa pekerjaan untuk F3 dan seterusnya:
- lipatan di atas bahu waktu lengan turun, dan di belakang lutut waktu jongkok;
- belum ada pengukuran tabrakan antarsegitiga dan volume sendi;
- dagu menggantung di atas leher (kepala polos ini akan diganti di F6);
- celah segitiga kecil di selangkangan.

## 8. Hasil F3 (bobot, helper bone, uji gerak otomatis)

**Uji otomatis.** `src/zombie/lowbody/poseTest.ts` dengan 20 pose tahan (`POSE_TESTS` di `pose.ts`): T, A, tangan turun/atas/depan/belakang, siku 140°, twist lengan bawah, twist pergelangan, kepal, lutut 150°, jongkok, tendang, ngangkang, bungkuk, putar badan, 4 fase jalan. Mesh di-skin di CPU (rumus sama dengan GPU), lalu diukur:
- `folds`: segitiga menembus segitiga tulang yang sama atau tetangga (≤ 2 langkah di rangka) = kulit melipat ke dalam;
- `contacts`: menembus bagian tubuh jauh (tangan masuk paha) = masalah pose, bukan kulit;
- `flipped`: normal terbalik terhadap normal rest yang diputar tulang utamanya, atau luas < 15 %;
- `creases`: sudut antar-segitiga melonjak > 100° dari < 50° saat rest;
- `vol`: volume mesh tertutup terhadap rest;
- `rings`: luas penampang ring sendi (bahu, siku, pergelangan, pinggul, lutut, pergelangan kaki) terhadap rest.

Jalankan: `__zm.set({style:'lowbody'}); __zm.poseTest()` (teks per pose di `.text`; `poseTest(['walk1'], true)` memberi daftar pasangan segitiga dan tepi lipatan). `__zm.holdTest('squat')` menahan satu pose di viewer, `__zm.skin()` memberi posisi verteks setelah skinning. Satu putaran penuh ±0.6 s untuk dua badan.

**Perbaikan dari hasil uji:**
- T-pose sudah punya tabrakan di pangkal kelingking dan jempol. Penyebab: ring 4 sisi berbentuk belah ketupat sedang lubang akarnya persegi (tabung terpuntir 45°); ring tangan terakhir sejajar pangkal kelingking; ring pertama jempol terbenam di permukaan tangan. Ring 4 sisi diputar 45°, ring tangan terakhir mundur ke f 0.74, ring pertama jempol didorong keluar dari permukaan, kelingking tidak terlalu melebar. Hasil: T-pose 0 tabrakan pada pria dan wanita.
- **Bahu:** tepi lubang lengan, kolom dada/punggung di sampingnya, dan sisi dada bawah ketiak sekarang ikut lengan bertahap (`TUNE_DEFAULT` di `body.ts`, dicari dengan grid lewat `globalThis.__lbTune`). Tabrakan lengan atas ke badan pada pose lengan turun dari 271 menjadi ±0.
- **Helper bone** (`helpers.ts`, bukan tulang Mixamo): `ArmHelper`, `ElbowHelper`, `KneeHelper`, `HipHelper` berada di sendi dan berputar setengah sudut tulang anaknya; `ForeArmTwist` mengambil setengah putaran tangan. Skinning linear membuat ring 50/50 menyusut ke cos(θ/2); ring yang dibawa helper tetap kaku. Ada satu ring baru di sendi bahu (1556 segitiga, sebelumnya 1524).

| Pose | Sebelum | Sesudah |
|---|---|---|
| siku 140° penampang | 0.34 | 1.00 |
| lutut 150° penampang | 0.26 | 1.00 |
| pinggul jongkok | 0.70 | 1.00 |
| twist pergelangan 90° | 0.54 | 0.86–0.88 |
| tabrakan bahu (11 pose lengan) | 271 | ±1 |
| lipatan tajam bahu | 44 | 7 |

Wajib: panggil `driveHelpers(rig)` setiap frame setelah pose (viewer dan uji sudah melakukannya). Klip Mixamo/GLB di engine lain tidak menggerakkan helper; sendi lalu kembali kaku seperti bobot biasa dan siku/lutut terlihat seperti terlipat setengah. Untuk ekspor ke luar, `__lbTune = {helpers:false}` memberi bobot klasik.

**Sisa:**
- Kantong ketiak/V di depan bahu masih terlihat saat lengan diayun ke belakang. Bobot sudah mentok; perlu topologi lubang lengan yang lebih besar (3×2 quad) atau loop deltoid miring.
- Kontak tangan ke pinggul/paha pada lengan turun dan jalan: proporsi pose, perbaiki di animasi (lengan sedikit abduksi).
- Lipatan dalam pada siku 140°/lutut 150°/jongkok adalah kontak daging yang wajar; segitiga gepeng di lipatan dalam masih 16–40 per pose.
- Kepal: jari menembus telapak (70 tabrakan); perlu kurva tekuk jari yang lebih kecil atau jari yang lebih tipis.

## 9. Catatan

- Lisensi pack referensi belum dicek. Selama masih dipakai sebagai angka acuan (F0), aman. Mesh-nya jangan dimasukkan ke repo.
- Model "Argon (Gemini)" dan "Low-poly" lama tetap ada untuk perbandingan.
