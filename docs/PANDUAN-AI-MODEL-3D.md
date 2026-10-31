# Panduan AI: Membuat Model 3D dari Gambar Referensi

File ini ditujukan untuk **AI** (Claude, Gemini, GPT, dll.). Manusia memberi: (1) satu atau beberapa gambar referensi, (2) satu kalimat permintaan, (3) file ini. AI membaca file ini, **memilih modul jenis yang sesuai** (bagian 7), lalu bekerja sesuai **MODE** di bawah.

---

## MODE KELUARAN (baca dulu, ini menentukan apa yang boleh kamu hasilkan)

Ada dua mode. **Bila manusia tidak menulis mode, pakai MODE ANALISIS.**

### MODE ANALISIS (bawaan): kamu adalah analis referensi, bukan pembuat model

Tugasmu mengubah gambar mentah menjadi **bahan kerja** untuk AI lain yang akan membangun modelnya.

**DILARANG di mode ini:** membuat file GLB, FBX, OBJ, STL; menulis kode three.js, Blender Python, atau kode model apa pun; membuat model 3D dalam bentuk apa pun. Walaupun kamu mampu, itu bukan tugasmu di sini.

**Yang harus kamu hasilkan (berurutan, satu per satu):**
1. **Catatan analisis** (Fase A, bagian 3): subjek, modul terpilih (bagian 2) dan alasannya, jangkar skala, garis pemandu, daftar bagian, apa yang simetris.
2. **Gambar referensi baru yang bersih** (bila kamu bisa membuat gambar): dari foto input, buat lembar ortografis (depan, samping, belakang, atas sesuai modul) dengan skala dan garis pemandu yang sama, latar polos abu-abu terang, cahaya merata, pose konstruksi modul (karakter: T-pose). Desain harus **identik** di semua tampak dan identik dengan foto input.
3. **Gambar lembar detail** (bila bisa): panel close-up bagian penting (tangan, kepala dengan profil samping, sepatu, kerah, tekstur material, sampel warna dengan kode hex), diberi label dan ukuran perkiraan.
4. **Lembar spesifikasi teks** (Fase B, Lampiran A): JSON atau tabel berisi angka dalam meter untuk tiap bagian, kedalaman fitur dalam cm, material dan hex, pola dan keausan, aksesori. Bagian yang tidak terlihat ditulis `ASUMSI`.
5. **Ringkasan untuk pembangun** (maks. 15 baris): urutan bagian yang paling penting, hal yang paling mudah salah, dan apa yang tidak boleh diubah.

Berhenti setelah butir 5. Katakan "Analisis selesai, siap diserahkan ke AI pembangun." dan tanyakan hanya bila ada hal yang benar-benar tidak bisa kamu simpulkan.

### MODE BUILD: kamu adalah pembangun model

Dipakai hanya bila manusia menulis **"MODE BUILD"** atau menyerahkan lembar spesifikasi dan memintamu membangun. Ikuti seluruh pipeline bagian 3 (Fase C sampai H). Bila lembar spesifikasi sudah ada, **pakai angkanya** dan jangan menganalisis ulang dari nol; hanya perbaiki bila bertentangan dengan gambar.

> Ringkas: **ANALISIS = gambar bersih + angka. BUILD = model.** Satu AI, satu peran.

---

## 0. Untuk manusia: cara memakai

Alurnya dua tahap, dengan dua AI (atau dua sesi) yang berbeda:

**Tahap 1: AI analis** (mis. ChatGPT yang bisa membuat gambar). Lampirkan foto + file ini, lalu tulis:

```
Baca PANDUAN-AI-MODEL-3D.md. MODE: ANALISIS. Jangan membuat GLB atau kode.
Dari foto ini, buat lembar referensi ortografis yang bersih, lembar detail, dan lembar spesifikasi angka.
Detail: semi-realistis.
```

Hasilnya (gambar referensi baru + spesifikasi teks) **kamu bawa ke tahap 2**.

**Tahap 2: AI pembangun** (mis. Claude Code atau Argon). Lampirkan hasil tahap 1 + file ini, lalu tulis:

```
Baca PANDUAN-AI-MODEL-3D.md. MODE: BUILD. Pakai lembar spesifikasi dan gambar referensi terlampir. Keluaran: three.js + GLB.
```

Yang boleh ditambahkan (opsional): tingkat detail (T1/T2/T3), mesin keluaran (three.js, Blender Python), apakah perlu rig dan animasi, dan jumlah segitiga maksimum. Kalau tidak ditulis, AI memakai nilai bawaan di bagian 2.

Referensi yang paling membantu: tampak ortografis (depan, samping, belakang), latar polos, cahaya merata, plus lembar detail dan lembar warna/material. Prompt untuk membuat referensi seperti itu ada di `docs/` (prompt A/B/C).

---

## 1. Perintah wajib untuk AI

0. **Patuhi MODE di bagian atas.** Di MODE ANALISIS dilarang membuat GLB atau kode model. Bila ragu mode mana yang berlaku, pakai MODE ANALISIS.
1. **Jangan menulis kode model sebelum lembar spesifikasi (bagian 3, Fase B) selesai.** Model dibuat dari angka, bukan dari kesan.
2. **Pilih modul jenis dulu** (bagian 2). Jangan memakai satu cara untuk semua jenis.
3. **Bekerja dalam fase kecil.** Satu fase satu keluaran yang bisa diperiksa. Jangan menulis seluruh model dalam satu jawaban.
4. **Tulis angka, bukan kata sifat.** "Lengan atas 0,30 m, lebar 0,09 m di pangkal dan 0,07 m di siku", bukan "lengan kekar".
5. **Katakan yang tidak terlihat.** Bagian yang tidak tampak di gambar ditandai `ASUMSI` beserta alasannya. Jangan mengarang lalu menyebutnya fakta.
6. **Bagian harus tersambung.** Tidak ada celah di sendi, tidak ada bagian melayang, tidak ada tumpukan bola.
7. **Verifikasi tiap fase** dengan render atau pemeriksaan angka (bagian 10). Bila ada alat render, pakai. Bila tidak ada, tulis perhitungan dan batas toleransinya.
8. **Ikuti struktur file bagian 11** dan jangan memakai angka ajaib di file bagian tubuh. Semua angka berasal dari file spesifikasi.
9. **Laporkan jujur**: apa yang sudah sesuai referensi, apa yang belum, dan asumsi yang dibuat.

---

## 2. Langkah 0: intake dan memilih modul

### 2.1 Baca permintaan dan gambar
Catat: subjek, jumlah gambar dan tampaknya (depan/samping/belakang/atas/3-4), apakah ada lembar detail, gaya (realistis, kartun, low-poly), dan kata kunci tambahan (rig, animasi, tekstur, ukuran).

### 2.2 Pilih modul
Cocokkan subjek dengan tabel. Kalau subjek gabungan (mis. orang di atas motor), bangun **tiap bagian dengan modulnya sendiri**, lalu gabungkan di akhir.

| Ciri subjek | Modul |
|---|---|
| Manusia, zombi, robot humanoid, monster berkaki dua dengan dua lengan | **M1 Karakter humanoid** |
| Hewan, makhluk berkaki empat atau lebih, burung, ikan, naga | **M2 Makhluk non-humanoid** |
| Benda mati: perabot, alat, senjata, wadah, mesin kecil, properti | **M3 Objek keras (hard-surface)** |
| Mobil, truk, motor, sepeda, kereta, tank | **M4 Kendaraan darat** |
| Pesawat, helikopter, drone, kapal, roket, pesawat luar angkasa | **M5 Pesawat dan kapal** |
| Rumah, gedung, jembatan, menara, interior, kota | **M6 Bangunan dan lingkungan** |
| Pohon, tanaman, batu, medan, awan, air | **M7 Organik dan alam** |
| Baju, topi, tas, perhiasan yang dipakai di tubuh | Lapisan **pakaian** di M1 atau M2 |

### 2.3 Nilai bawaan jika tidak disebutkan
- Tingkat detail **T2** (menengah). Pilihan: **T1** blok/low-poly (≤ 3k segitiga, shading datar), **T2** menengah (3k–12k, shading halus), **T3** semi-realistis (12k–25k, banyak material, detail permukaan).
- Satuan meter. Sumbu: **+Y atas, +Z depan, +X kiri objek**. Origin di tengah dasar objek (kaki, roda, fondasi).
- Keluaran three.js (TypeScript) dan ekspor GLB. Alternatif: skrip Blender Python.
- Rig hanya jika subjek bergerak oleh sendi (M1, M2, bagian bergerak di M4/M5). Kalau tidak diminta, M3, M6, M7 tidak di-rig.
- Tanya manusia **hanya jika** ambigu dan jawabannya mengubah hasil besar. Selain itu, pilih bawaan dan tulis asumsinya.

---

## 3. Pipeline universal

Setiap fase punya **keluaran** dan **syarat lulus**. Jangan lanjut sebelum lulus.

**Pembagian mode:** Fase **A dan B** (plus gambar referensi baru) adalah pekerjaan MODE ANALISIS. Fase **C sampai H** adalah pekerjaan MODE BUILD.

### Fase A: analisis gambar
- Tentukan **jangkar skala**: satu ukuran yang diketahui (tinggi orang ±1,75 m, tinggi pintu 2,0 m, diameter roda, panjang bodi). Semua ukuran lain diturunkan dari sini.
- Tarik **garis pemandu horizontal** yang sama di semua tampak (puncak, bahu atau atap, pinggang, lutut atau as roda, tanah). Pastikan tampak sejajar. Bila tidak, catat selisihnya.
- Daftar **bagian utama** dan **bagian sekunder** (tidak boleh melewatkan bagian yang menyentuh siluet).
- Tandai apa yang **simetris** dan apa yang tidak.
- Keluaran: catatan analisis singkat. Syarat lulus: semua tampak sudah dipetakan ke satu sistem koordinat.

### Fase B: lembar spesifikasi
Isi template Lampiran A. Untuk tiap bagian utama: panjang, lebar dan kedalaman di tiga titik (awal, tengah, ujung), posisi pusat, kelengkungan, tumpang tindih dengan bagian lain. Untuk permukaan: warna (kode hex), kekasaran, lokasi keausan, pola, dan decal.
- Syarat lulus: tidak ada sel kosong tanpa `ASUMSI`, dan tinggi total sama dengan jangkar skala.

### Fase C: baseline struktur
Bentuk dasar tiap bagian dari spesifikasi, **tanpa detail**: balok, silinder, loft sederhana. Tampilkan dalam satu warna.
- Syarat lulus: siluet depan, samping, dan atas cocok dengan referensi dalam toleransi 5% pada tiap garis pemandu.

### Fase D: struktur gerak (hanya bila perlu)
Rangka tulang atau hierarki pivot (bagian 7). Pasang bobot kulit atau induk-anak.
- Syarat lulus: gerakkan tiap sendi 45° dan 90°, tidak ada bentuk robek atau tembus.

### Fase E: detail bentuk
Tambah **per lapis**, satu lapis per ronde, urutan dari besar ke kecil:
1. fitur besar (kepala, kap mesin, atap)
2. fitur sedang (lipatan, panel, jendela, lengkung)
3. fitur kecil (kancing, baut, kuku, gagang)
- Syarat lulus per lapis: render dibandingkan dengan lembar detail referensi, dan selisihnya ditulis.

### Fase F: material, warna, pola
Strategi (bagian 8): warna per vertex, shader prosedural, tekstur, decal. Warna ikut kode hex dari lembar spesifikasi.

### Fase G: verifikasi
Render dari semua tampak referensi dengan kamera yang sama. Bandingkan, perbaiki bagian yang paling jauh dari referensi dulu. Ulangi sampai kriteria modul terpenuhi.

### Fase H: pengiriman
Ekspor, laporan, daftar asumsi, dan cara menjalankan (bagian 11).

---

## 4. Mengukur dari gambar

1. **Skala**: `meter_per_piksel = ukuran_jangkar_meter / ukuran_jangkar_piksel` pada tampak yang sama. Hitung terpisah untuk tiap tampak, karena tampak tidak selalu berukuran sama.
2. **Lebar pada ketinggian tertentu**: baca lebar siluet depan pada tiap garis pemandu. Untuk bentuk lingkaran atau elips, lebar depan memberi jari-jari sisi (`rs`), lebar samping memberi jari-jari depan (`rf`).
3. **Kedalaman fitur** (rongga mata, kaca depan, lekuk): dari **profil samping**, ukur selisih terhadap garis rata-rata siluet. Dari satu gambar saja, nilai ini hanya perkiraan, jadi tandai `ASUMSI` dan beri rentang (mis. −2 sampai −3 cm).
4. **Rasio lebih tepercaya daripada nilai mutlak.** Catat rasio ke tinggi total dulu, lalu kalikan jangkar.
5. **Tampak 3/4 atau perspektif**: jangan dipakai untuk mengukur. Pakai hanya untuk bentuk dan detail.
6. Bila skrip tersedia: ambil siluet (ambang warna latar), pindai baris demi baris, dan simpan lebar tiap ketinggian sebagai tabel. Ini lebih akurat daripada menebak dengan mata.

---

## 5. Aturan modeling universal

- **Satu badan, bukan tumpukan primitif.** Bagian saling tumpang tindih di sambungan (lengan masuk badan, kaki masuk pinggul, roda masuk fender) supaya tidak ada celah saat bergerak.
- **Lapisan luar sedikit lebih besar** dari lapisan dalam (baju di atas kulit, cat di atas besi), selisih 1 sampai 5 mm sesuai skala, supaya permukaan tidak saling tembus.
- **Simetri**: bangun satu sisi, cerminkan dengan `s = ±1`. Tandai bagian yang sengaja tidak simetris.
- **Kerapatan segitiga mengikuti kelengkungan.** Bidang datar sedikit cincin, sendi dan lengkung banyak cincin.
- **Tidak ada angka ajaib** di kode bagian. Angka ada di spesifikasi, kode hanya membaca.
- **Deterministik**: semua variasi acak memakai `hash(seed, indeks)`, jadi hasil bisa diulang.
- **Penamaan**: tulang dan pivot memakai nama yang jelas dan konsisten (humanoid: nama Mixamo).
- **Jangan menutup masalah dengan tekstur.** Bentuk dulu, lalu warna, lalu detail permukaan.

---

## 6. Matematika singkat

| Kebutuhan | Rumus |
|---|---|
| **Loft** (sapuan cincin sepanjang jalur) | tiap stasiun punya pusat `c`, jari-jari `rs` (samping) dan `rf` (depan). Tangen `T` = arah stasiun berikutnya dikurangi sebelumnya. Depan `F = normalize(front − (front·T)T)`, samping `S = T × F`. Titik cincin: `p = c + rs·cos φ·S + rf·sin φ·F`. |
| **Resampling halus** | Catmull-Rom: `0.5·(2p1 + (−p0+p2)t + (2p0−5p1+4p2−p3)t² + (−p0+3p1−3p2+p3)t³)` pada `c`, `rs`, `rf`. |
| **Fitur wajah / lekuk lokal** | jumlah gaussian: `d(h, a) = Σ A·gauss(h, μh, σh)·gauss(a, μa, σa)`, `gauss(x, μ, σ) = exp(−((x−μ)/σ)²/2)`. Negatif = cekung, positif = menonjol. Dipakai juga untuk lekuk bodi mobil, lipatan baju, cekungan batu. |
| **Bobot kulit otomatis** | `w_i = 1 / ((jarak(p, segmen_i) / radius_i)⁴ + ε)`, ambil 4 terbesar, normalisasi. Vertex yang berimpit digabung, lalu bobot di-smoothing dengan tetangga. |
| **Skinning** | linear blend skinning: `v' = Σ w_i · M_i · B_i⁻¹ · v` (spesifikasi glTF 2.0). Dual quaternion skinning bila sendi memutir (Kavan dkk. 2007). |
| **Hierarki gerak** | `M_dunia = M_induk · M_lokal`, putaran Euler urutan XYZ berarti **Z diterapkan pertama** di three.js. |
| **Noise permukaan** | value noise 3D dan fbm: `Σ a^k · noise(2^k · p)`. Mode *ridged*: `1 − |2n − 1|` untuk garis lipatan tajam. |
| **Bump tanpa UV** | tinggi `h(p)` pada posisi bind-pose, normal diganggu dengan turunan layar `dFdx/dFdy`. Tidak butuh tekstur atau UV. |
| **IK (jika perlu)** | FABRIK: iterasi maju-mundur sepanjang rantai tulang (Aristidou & Lasenby 2011). |

---

## 7. Modul jenis

Format tiap modul: **ciri**, **tampak dan pose referensi**, **baseline**, **kolom spesifikasi wajib**, **rig**, **detail**, **kegagalan umum**, **kriteria lulus**.

### M1. Karakter humanoid (manusia, zombi, robot, monster berkaki dua)

- **Tampak ideal**: depan, samping, belakang. **Pose konstruksi: T-pose**, lengan lurus ke samping, telapak ke bawah, jari sedikit terpisah, kaki selebar bahu, wajah ke depan. Bila referensi bukan T-pose, bangun di T-pose dan hitung pose referensi sebagai rotasi tulang.
- **Proporsi bawaan** (dewasa, ±7,5 tinggi kepala): tinggi 1,75 sampai 1,85 m, bahu ±2 lebar kepala, siku di garis pinggang, ujung jari tengah di pertengahan paha, lutut di ¼ tinggi dari tanah. Panjang telapak tangan ≈ tinggi wajah, panjang jari tengah ≈ ¾ panjang telapak.
- **Baseline**: leher, dada, perut, pinggul, tiap segmen lengan, tangan (telapak + 5 jari), tiap segmen kaki, kaki. Dibuat dengan **loft** sepanjang tulang. Kepala: profil 15 sampai 17 cincin (dagu ke ubun-ubun) dengan fitur gaussian.
- **Kolom spesifikasi**: tinggi total, lebar bahu dan pinggul, kedalaman dada, tiap segmen (panjang, lebar pangkal/tengah/ujung, kedalaman), jari (panjang tiap ruas, tebal), kepala (lebar, tinggi, kedalaman, **tabel fitur**: mata, alis, hidung, pipi, mulut, dagu, rahang dengan kedalaman cm), posisi telinga.
- **Rig**: nama Mixamo, rotasi bind = identitas di T-pose. Tulang minimum: `Hips, Spine, Spine1, Spine2, Neck, Head, Jaw` + `Left/Right Shoulder, Arm, ForeArm, Hand` + 3 ruas × 5 jari + `UpLeg, Leg, Foot, ToeBase`. Rahang terpisah bila mulut harus bisa terbuka (bobot rahang pada vertex di bawah garis mulut dan di depan telinga).
- **Pakaian**: lapisan loft terpisah, lebih besar 1 sampai 5 mm dari kulit. Bukaan (jaket, V-neck) dengan fungsi `open(phi, cincin)`. Lipatan dengan offset radial dari fbm, kuat di bawah dada, hampir nol di bahu. Kerah dan lapel dibuat loft terpisah.
- **Detail berurutan**: wajah dan gigi, tangan dan kuku, pakaian, lipatan, luka, noda, aksesori (ikat pinggang, sepatu, jam, tas).
- **Kegagalan umum**: kepala seperti telur atau kaleng (profil terlalu sedikit cincin), mata dan gigi terkubur (koordinat tetap, bukan titik di permukaan), engsel rahang terlalu rendah (harus di dekat telinga), sepatu seperti tunggul, tangan terlepas dari lengan (celah di pergelangan), pose duduk melayang (rotasi pinggul ikut memutar kaki).
- **Kriteria lulus**: siluet tiga tampak dalam 5%, 9 pose uji (T-pose, berdiri, jalan, meraih, menerkam, duduk, merayap, rahang terbuka, tangan mengepal) tidak robek, jari bergerak sendiri.

### M2. Makhluk non-humanoid (hewan, burung, ikan, naga)

- **Tampak ideal**: samping (terpenting), depan, belakang, atas. Pose netral: berdiri, kepala lurus, ekor lurus, sayap atau sirip terbuka datar.
- **Baseline**: badan sebagai loft sepanjang tulang punggung (kepala ke ujung ekor), tiap kaki sebagai rantai loft (paha, betis, metatarsus, kaki), kepala sebagai loft dengan moncong. Burung: badan oval, sayap pipih (loft lebar-tipis) per ruas.
- **Kolom spesifikasi**: panjang badan, tinggi pundak, panjang leher, lebar dada dan pinggul, panjang tiap ruas kaki (hewan berjalan di jari, bukan telapak, sehingga ruas "terbalik" dari manusia), panjang ekor, bentuk kepala (moncong, rahang, mata di samping atau depan).
- **Rig**: tulang punggung 5 sampai 9 ruas, leher 2 sampai 4, ekor 3 sampai 8, empat rantai kaki. Nama bebas tapi konsisten (`Spine1..N`, `Neck1..N`, `Tail1..N`, `FrontLeftUpper/Lower/Foot`). Sayap atau sirip: rantai tulang tambahan.
- **Detail**: bulu atau sisik sebagai warna per vertex dan bump prosedural (bukan geometri per bulu), tanduk atau taring, mata, kuku.
- **Kegagalan umum**: sendi kaki terbalik (lutut vs tumit), badan seperti tabung tanpa tulang rusuk dan pinggul, leher kaku, kaki tidak menyentuh tanah.
- **Kriteria lulus**: siluet samping dalam 5%, berjalan atau mengepak sayap tanpa robek, kaki menyentuh tanah di pose diam.

### M3. Objek keras (perabot, alat, senjata, wadah, properti)

- **Tampak ideal**: depan, samping, atas (plus 3/4). Pose: dalam kondisi tertutup, di atas permukaan datar.
- **Baseline**: komposisi bentuk dasar (balok, silinder, loft profil, revolusi). Bentuk **revolusi** (botol, vas, roda) lebih baik dibuat dari profil 2D yang diputar.
- **Kolom spesifikasi**: dimensi luar (P × L × T), tebal dinding atau panel, radius sudut (chamfer atau fillet, dalam mm), posisi dan ukuran tiap lubang, kancing, engsel, gagang.
- **Rig**: biasanya tidak ada. Bagian bergerak (pintu, laci, tutup) memakai **pivot**: objek anak dengan titik putar di sumbu engsel dan sudut batas.
- **Detail berurutan**: sudut membulat, alur panel, baut dan kancing, tekstur material (kayu: serat memakai noise teregang; logam: goresan kecil; plastik: tekstur halus), logo dan decal, keausan di sudut dan tepi (tempat tangan menyentuh).
- **Kegagalan umum**: sudut tajam sempurna (tidak menangkap cahaya), ketebalan nol pada panel, bagian melayang karena tidak ada tumpang tindih, skala komponen kecil tidak konsisten.
- **Kriteria lulus**: dimensi dalam 3%, semua bagian bergerak berputar di sumbu yang benar tanpa menembus.

### M4. Kendaraan darat (mobil, truk, motor, sepeda, kereta, tank)

- **Tampak ideal**: depan, belakang, kiri, kanan, atas. Pose: di tanah datar, roda lurus, pintu dan kap tertutup.
- **Ukuran bawaan** (periksa dengan referensi): mobil panjang 4,0 sampai 4,8 m, lebar 1,7 sampai 1,95 m, tinggi 1,4 sampai 1,6 m, jarak sumbu roda 2,5 sampai 2,9 m, diameter roda 0,60 sampai 0,75 m. Motor: roda 0,60 sampai 0,70 m, jarak sumbu 1,3 sampai 1,5 m.
- **Baseline**: bodi sebagai **loft panjang** dari bumper depan ke belakang dengan penampang berubah (kap, kabin, bagasi), bukan satu balok. Atau tiga loft: kap, kabin, bagasi. Roda sebagai silinder (ban) + silinder lebih kecil (pelek). Kaca sebagai panel melengkung.
- **Kolom spesifikasi**: panjang, lebar, tinggi, tinggi bodi di as roda, tinggi kolong, jarak sumbu, jejak roda, diameter dan lebar ban, profil samping bodi (tabel tinggi tiap 10% panjang), kemiringan kaca depan dan belakang, posisi lampu, grill, cermin, gagang pintu.
- **Rig (hierarki pivot)**: `Body` sebagai akar. Anak: 4 roda (sumbu putar di as, roda depan juga memutar di sumbu vertikal untuk kemudi), 4 pintu (sumbu engsel vertikal di tepi depan pintu), kap dan bagasi (engsel horizontal). Suspensi bisa ditambah sebagai gerak vertikal roda.
- **Detail berurutan**: garis panel dan celah antar pintu, lampu, grill, kaca, pelek dan jari-jari, plat nomor, cat (warna dengan kilap tinggi, `roughness` 0,2 sampai 0,35), karet pada ban (kasar, hitam), chrome (`metalness` tinggi), goresan atau karat bila sesuai referensi.
- **Kegagalan umum**: bodi kotak (tanpa profil samping yang melengkung), roda terlalu kecil atau melayang, kolong terlalu tinggi, kaca sama datar dengan bodi, bayangan ban tidak menyentuh tanah.
- **Kriteria lulus**: siluet samping dan atas dalam 3%, roda menyentuh tanah dan berputar di sumbu yang benar, pintu terbuka 70° tanpa menembus bodi.

### M5. Pesawat dan kapal (pesawat, helikopter, drone, kapal, roket)

- **Tampak ideal**: atas (plan), samping, depan, belakang. Pesawat: pose di tanah dengan roda keluar atau terbang dengan roda masuk, sesuai referensi.
- **Baseline**: **badan pesawat** (fuselage) sebagai loft panjang dengan penampang melingkar atau elips yang berubah (hidung runcing, tengah silinder, ekor menyempit). **Sayap** sebagai loft pipih dengan airfoil (profil sayap) yang makin kecil ke ujung, sudut sapu dan dihedral dari tampak atas dan depan. Kapal: lambung loft dari tampak atas (garis air) dan depan (penampang), dek di atasnya, bangunan atas dari balok dan loft.
- **Kolom spesifikasi**: panjang, bentang sayap, tinggi total, tabel penampang badan tiap 10% panjang, akord sayap di pangkal dan ujung, sudut sapu, dihedral, tebal sayap relatif, ukuran dan posisi mesin, kemudi, flap, jendela. Kapal: panjang, lebar, sarat air, tinggi lambung.
- **Rig (hierarki pivot)**: `Body` akar. Anak: aileron, elevator, rudder (engsel di tepi depan permukaan kontrol), roda pendarat (lipat), baling-baling atau rotor (sumbu putar), pintu. Kapal: kemudi, baling-baling, derek.
- **Detail berurutan**: garis panel, rivet, jendela, lampu navigasi, mesin dan turbin (kipas dengan bilah berulang), livery (pola cat), tulisan dan lambang, keausan, jelaga di knalpot.
- **Kegagalan umum**: sayap tanpa airfoil (papan datar), badan pesawat silinder lurus, mesin menempel bukan menggantung dari pilon, skala bilah rotor salah, penampang tidak mulus.
- **Kriteria lulus**: tampak atas dan samping dalam 3%, permukaan kontrol berputar di engsel yang benar, penampang mulus tanpa patahan.

### M6. Bangunan dan lingkungan (rumah, gedung, jembatan, interior, kota)

- **Tampak ideal**: tampak depan, belakang, kiri, kanan (elevasi), plus denah atap atau denah lantai. Pose: di tanah datar.
- **Ukuran bawaan**: tinggi lantai 2,7 sampai 3,5 m, pintu 2,0 sampai 2,1 m × 0,9 m, ambang jendela ±0,9 m dari lantai, tinggi jendela 1,2 sampai 1,5 m, tebal dinding 0,15 sampai 0,3 m, kemiringan atap 20° sampai 45°.
- **Baseline**: **massa bangunan** dulu (balok per lantai, lalu atap), baru lubang pintu dan jendela. Dinding dibuat dengan **ketebalan** (bukan bidang), lubang dipotong dengan membangun dinding dari segmen di sekeliling lubang.
- **Kolom spesifikasi**: denah (P × L), jumlah lantai dan tinggi tiap lantai, tabel pintu dan jendela (lebar, tinggi, ambang, posisi pada tiap elevasi), bentuk atap (pelana, perisai, datar), overhang atap, balkon, tangga, kolom, pola fasad (ritme jendela).
- **Rig**: tidak ada. Bagian bergerak: pintu dan jendela sebagai pivot di engsel. Pengulangan (jendela, balkon, tiang) dibuat dengan **instancing**, bukan salinan manual.
- **Detail berurutan**: bingkai pintu dan jendela, ambang, kusen, genteng atau bata (pola warna dan bump, bukan geometri per bata untuk bangunan besar), talang, cerobong, pagar, tanaman, noda cuaca (lebih gelap di bawah jendela dan di pojok), graffiti atau papan nama.
- **Kegagalan umum**: dinding setebal nol, jendela hanya gambar di bidang, ritme jendela tidak konsisten antar lantai, atap tanpa overhang, skala pintu tidak manusiawi.
- **Kriteria lulus**: elevasi dalam 2% pada garis lantai dan atap, ritme lubang sama dengan referensi, tinggi pintu terhadap lantai masuk akal.

### M7. Organik dan alam (pohon, tanaman, batu, medan, air)

- **Tampak ideal**: samping, atas, dan 3/4 (bentuk alami tidak menuntut ortografis ketat).
- **Baseline**: pohon: batang dan cabang sebagai **loft percabangan rekursif** (jari-jari mengecil, sudut dengan aturan sederhana), tajuk sebagai klaster elipsoid atau bidang daun. Batu: bola atau ikosahedron yang dideformasi dengan noise berlapis. Medan: grid tinggi dengan fbm. Air: bidang dengan normal bergelombang (shader).
- **Kolom spesifikasi**: tinggi, lebar tajuk atau diameter batu, tinggi batang sampai cabang pertama, aturan percabangan (jumlah, sudut, rasio panjang), kerapatan daun, rentang warna (hex), skala noise dan amplitudo.
- **Rig**: biasanya tidak ada. Bila diminta bergoyang tertiup angin: rantai tulang pendek di tiap cabang atau gerak di shader vertex.
- **Detail berurutan**: kulit kayu (bump ridged), akar, lumut (warna berdasarkan arah normal ke atas), daun (instancing bidang daun), bunga atau buah, retakan batu.
- **Kegagalan umum**: pohon simetris sempurna, percabangan di satu bidang, daun sebagai bola hijau, batu seperti bola, medan berulang jelas.
- **Kriteria lulus**: siluet dalam 8% (toleransi lebih longgar untuk bentuk alami), tidak ada pola ulang yang mencolok, variasi seed menghasilkan bentuk berbeda.

---

## 8. Detail bertahap: aksesori, tekstur, pola

Urutan penerapan: **geometri → warna → permukaan → penanda**.

| Lapis | Cara | Catatan |
|---|---|---|
| Aksesori (sabuk, gesper, kacamata, antena, kunci) | objek terpisah dengan bobot atau pivot ke bagian induk, ukuran dari spesifikasi | tumpang tindih sedikit dengan induk |
| Warna dasar | warna per vertex dari fungsi posisi (`rule(p)`): warna dasar + variasi fbm | pakai kode hex dari spesifikasi |
| Pola (garis, kotak, kamuflase, livery) | fungsi atas koordinat objek (mis. `floor(x/0.1)%2`), mask, atau warna per vertex berpola | kerapatan segitiga harus lebih halus dari pola, kalau tidak, pola tampak berblok kotak-kotak |
| Keausan, kotoran, karat, darah | fbm sebagai topeng, dibatasi area (gaussian atau gradien ketinggian), makin tebal di sudut, cekung, dan bawah | hindari bentuk bulat sempurna |
| Detail permukaan (pori, serat, goresan, kerutan) | bump prosedural dari noise 3D di posisi bind-pose (tanpa UV) | hanya terlihat di viewer; ekspor GLB tidak membawa shader |
| Tekstur gambar | bila ada UV dan file tekstur, pakai peta warna, normal, dan kekasaran | lebih baik untuk detail halus dan logo |
| Decal (logo, tulisan, plat nomor) | bidang kecil sedikit menonjol di permukaan, atau tekstur | tulisan selalu sebagai decal, bukan geometri |

**Batas jujur**: model prosedural tidak mencapai detail hasil sculpting dan tekstur foto. Untuk tahap itu, ekspor GLB lalu lanjutkan di Blender (sculpt, bake normal map, tekstur cat). Rig dan nama tulang tetap bisa dipakai.

---

## 9. Bila mendelegasikan ke AI lain

Pengalaman nyata dengan model Gemini yang diberi dokumen proses:
- **Kirim pesan pendek** (±10 ribu karakter). Pada prompt yang sangat panjang, instruksi di bagian akhir sering diabaikan.
- **Instruksi di depan**, lalu kode saat ini, lalu API yang dibutuhkan.
- **Satu bagian per ronde** (kepala saja, lalu tangan, lalu pakaian). Sambungkan hasilnya dengan skrip, jangan minta seluruh file ditulis ulang. Minta fungsi bernama dan jaga fungsi lain agar tidak berubah.
- **Batasi panjang jawaban** (mis. "maksimal 150 baris"). Jawaban yang terlalu panjang terpotong di tengah kode.
- **Deskripsikan apa yang terlihat dalam teks** bila gambar tidak bisa dikirim: "kepala seperti telur manekin, tidak ada mata, dua noda samar di tempat mata", lalu **bentuk targetnya** dengan angka. Ini jauh lebih efektif daripada daftar bug.
- Jelaskan **penyebab** bila diketahui (koordinat mata tetap, 2 cm di dalam kepala), supaya perbaikannya struktural, bukan kosmetik.
- Selalu cek typecheck dan render setelah tiap ronde, lalu simpan versi tiap ronde.

---

## 10. Verifikasi dan masalah umum

### 10.1 Cara memeriksa
1. **Siluet**: render dari kamera ortografis di tiap tampak referensi, ukur lebar tiap garis pemandu, bandingkan dengan tabel spesifikasi.
2. **Tabel selisih**: kolom bagian, nilai referensi, nilai model, selisih %, status.
3. **Uji gerak**: tiap sendi 45° dan 90°, lihat retak dan tembus.
4. **Uji kontak**: bagian yang menyentuh tanah benar-benar menyentuh (kaki, roda, fondasi), dan tidak tenggelam.
5. **Uji variasi**: seed berbeda tidak merusak bentuk.

### 10.2 Masalah umum dan perbaikan

| Gejala | Penyebab biasa | Perbaikan |
|---|---|---|
| Bentuk seperti telur atau kaleng | terlalu sedikit cincin pada profil | 15 sampai 17 cincin kunci + Catmull-Rom |
| Fitur terlalu halus | amplitudo gaussian terlalu kecil | naikkan ke 1 sampai 3 cm, perkecil σ |
| Bagian terkubur di dalam bodi | koordinat tetap, bukan dihitung dari permukaan | fungsi `surface(h, a, inset)` yang mengembalikan titik di permukaan |
| Celah di sendi | bagian tidak saling tumpang tindih | perpanjang bagian ke dalam induk |
| Mesh robek saat bergerak | bobot kulit kasar atau satu sisi | perbaiki jangkauan tulang yang diizinkan, tambah smoothing |
| Pola berblok kotak-kotak | warna per vertex dengan cincin sedikit | naikkan jumlah cincin dan sisi (sub 6, ≥ 40 sisi) |
| Tepi bukaan bergerigi | cincin terlalu sedikit di area bukaan | resampling lebih rapat dekat bukaan |
| Bagian pecah di seam | vertex di jahitan UV berbobot beda | gabungkan vertex berimpit sebelum bobot |
| Objek melayang atau tenggelam | titik kontak tidak dihitung | fungsi grounding dari daftar kontak dan clearance |
| Pose berputar ke arah salah | urutan Euler | di three.js XYZ, Z diterapkan pertama; tes satu sumbu per kali |
| Jawaban AI terpotong | output terlalu panjang | minta ≤ 150 baris, satu fungsi per ronde |

---

## 11. Keluaran dan struktur file

```
proyek/
  spec/<nama>.spec.json      lembar spesifikasi (Lampiran A), satu-satunya sumber angka
  src/<nama>/
    skeleton.ts              tulang atau pivot (jika ada rig)
    parts/<bagian>.ts        satu file per bagian utama
    materials.ts             material dan shader
    build.ts                 menyatukan semua bagian, mengembalikan objek siap render
    pose.ts                  pose uji (jika ada rig)
  viewer/                    viewer, kamera, ekspor
  renders/                   render tiap fase dan tiap tampak
  docs/laporan.md            laporan akhir
```

**Laporan akhir** (`docs/laporan.md`) memuat: modul yang dipilih dan alasannya, jangkar skala, tabel selisih (bagian 10.1), daftar asumsi, hal yang belum sesuai referensi, cara menjalankan dan mengekspor.

---

## Lampiran A: template lembar spesifikasi

```json
{
  "subjek": "string",
  "modul": "M1|M2|M3|M4|M5|M6|M7",
  "tingkat_detail": "T1|T2|T3",
  "jangkar_skala": { "deskripsi": "tinggi orang", "meter": 1.8 },
  "satuan": "meter",
  "sumbu": "+Y atas, +Z depan, +X kiri objek",
  "tampak_referensi": ["depan", "samping", "belakang"],
  "dimensi_total": { "tinggi": 0, "lebar": 0, "kedalaman": 0 },
  "garis_pemandu": { "puncak": 0, "bahu_atau_atap": 0, "pinggang": 0, "lutut_atau_as": 0, "tanah": 0 },
  "bagian": [
    {
      "nama": "lengan_atas",
      "induk": "bahu",
      "simetris": true,
      "panjang": 0,
      "lebar": { "awal": 0, "tengah": 0, "ujung": 0 },
      "kedalaman": { "awal": 0, "tengah": 0, "ujung": 0 },
      "pusat": [0, 0, 0],
      "tumpang_tindih_dengan": ["dada"],
      "fitur": [{ "nama": "otot", "kedalaman_cm": 0.5, "posisi": "tengah", "asumsi": true }]
    }
  ],
  "material": [
    { "nama": "kulit", "hex": "#a89ca2", "kekasaran": 0.58, "logam": 0, "keausan": "memar di pipi dan siku" }
  ],
  "pola_dan_decal": [{ "nama": "garis", "bagian": "jaket", "deskripsi": "lipatan vertikal di bawah dada" }],
  "aksesori": [{ "nama": "ikat_pinggang", "ukuran": [0, 0, 0], "posisi": [0, 0, 0], "induk": "pinggul" }],
  "tidak_simetris": [],
  "asumsi": ["tampak belakang tidak ada, bagian belakang jaket diasumsikan polos"]
}
```

---

## Lampiran B: sumber

Daftar lengkap dan tautan: `docs/06-sumber.md`. Yang dipakai di panduan ini:
- **glTF 2.0** spesifikasi skin (Khronos): format bobot dan tulang.
- **Kavan dkk.**, *Skinning with Dual Quaternions*, I3D 2007, dan *Geometric Skinning with Approximate Dual Quaternion Blending*, ACM TOG 27(4), 2008.
- **Jacobson dkk.**, *Bounded Biharmonic Weights*, ACM TOG 30(4), 2011.
- **Baran & Popović**, *Automatic Rigging and Animation of 3D Characters* (Pinocchio), ACM TOG 26(3), 2007: gagasan bobot dari jarak.
- **Aristidou & Lasenby**, *FABRIK*, Graphical Models 73(5), 2011.
- **Xu dkk.**, *RigNet*, arXiv 2005.00559, 2020.
- **Mikkelsen**, *Bump Mapping Unparametrized Surfaces on the GPU*, 2010: dasar bump dari turunan layar.
- Dokumen proyek ini: `docs/07-proses-pembuatan.md` (angka nyata, masalah dan perbaikan), `docs/08-eksperimen-argon.md` (cara mendelegasikan), `docs/09-impor-mesh-ai.md` (impor GLB ke rig).
