# 07 — Proses Pembuatan (Catatan Kerja Nyata)

File 00–06 berisi **rencana dan teori** yang ditulis sebelum model dibuat. File ini mencatat **apa yang benar-benar dikerjakan**: urutan langkah, angka yang dipakai, masalah yang muncul, dan cara memperbaikinya. Tujuannya supaya orang atau AI lain bisa mengulang, memperbaiki, atau mengembangkan model ini tanpa harus menebak.

Semua angka dalam meter (1 unit = 1 m), sumbu: **+Y atas, +Z depan, +X kiri zombie** (kanan layar saat dilihat dari depan).

---

## 1. Gambaran besar

Model **tidak dibuat di Blender**. Seluruhnya dihasilkan oleh kode TypeScript + Three.js setiap kali halaman dibuka:

```
seed ──► variant (warna, bulk)
        │
skeleton (posisi tulang T-pose) ──► segmen tulang
        │                               │
        ▼                               ▼
bagian tubuh = loft (cincin disapu sepanjang tulang)  ──►  bobot skin (jarak ke segmen)
        │
MeshBuilder (bucket per material) ──► mergeVertices + normal halus ──► 1 geometry, N group
        │
SkinnedMesh + Skeleton ──► pose (rotasi tulang) ──► groundTo (kaki ke lantai)
        │
viewer: lampu, kamera, overlay rig, capture PNG, ekspor GLB
```

Ada dua gaya yang memakai mesin yang sama:

| | Low-poly (versi 1) | Semi-realistis (versi 2, default) |
|---|---|---|
| Tulang | 58 (`skeleton.ts`) | 66, lima jari (`skeletonReal.ts`) |
| Segitiga | ±2.000 | ±16.600 |
| Shading | flat, warna per segitiga | halus, warna per vertex |
| Material | 1 | 8 (kulit, mata, gigi, kaus, jaket, celana, kulit sepatu, logam) |
| Detail permukaan | jitter vertex | shader noise (bump) |

---

## 2. Urutan kerja

Urutan ini yang dipakai, dan urutan ini yang disarankan untuk mengulang:

1. **Setup proyek** — Vite + TypeScript + three 0.169. Port 5195 (`strictPort`). Middleware `/__save` di `vite.config.ts` menerima `{name, ext, data(base64)}` dan menulis ke `renders/`. Ini yang membuat render bisa disimpan otomatis dari browser.
2. **Skeleton** — daftar `BoneDef { name, parent, p (posisi dunia), tail }`. Nama mengikuti Mixamo (`Hips`, `Spine`, `Spine1`, `Spine2`, `Neck`, `Head`, `LeftArm`, `LeftForeArm`, …) supaya kompatibel dengan animasi Mixamo dan Blender.
3. **Primitif mesh** — `MeshBuilder`, `loft`, `weigher`, `ellipsoid`, `box` di `mesh.ts`.
4. **Badan low-poly** (versi 1) — torso, kepala, lengan, kaki, baju sobek, sepatu bot. Diverifikasi dengan render 4 view dibandingkan referensi.
5. **Pose dasar** — tpose, idle, walk, reach, attack + overlay rig (tongkat, bola sendi, cincin kontrol, label).
6. **Ekspor GLB** — `GLTFExporter`, dicek: 1 mesh, 1 skin, atribut `JOINTS_0/WEIGHTS_0`.
7. **Versi semi-realistis** — skeleton baru (66 tulang), mode halus, kepala tengkorak, tangan 5 jari, pakaian berlapis, material + shader detail.
8. **Pose tambahan** — lunge (menerkam), roar (meraung), crawl (merayap), sit (duduk), dengan titik kontak lantai per pose.
9. **Scene horor + tampilan** — lampu sorot, kabut, close-up wajah, gerombolan 5 zombie.
10. **Iterasi visual** — render, lihat, perbaiki angka, ulangi. Bagian 9 berisi daftar masalahnya.

---

## 3. Skeleton (semi-realistis)

File: `src/zombie/skeletonReal.ts`. Pria dewasa 1,82 m, bahu lebar.

| Tulang | Posisi (x, y, z) | Catatan |
|---|---|---|
| Hips | 0, 0.98, 0 | akar |
| Spine / Spine1 / Spine2 | y 1.08 / 1.20 / 1.33 | z sedikit ke belakang (−0.01 … −0.02), mengikuti lengkung punggung |
| Neck | 0, 1.50, −0.02 | |
| Head | 0, 1.585, 0 | `REAL_HEAD_Y`, semua ukuran kepala relatif terhadap ini |
| HeadTop_End | 0, 1.825, 0 | |
| Jaw | 0, 1.69, −0.035 → ujung 0, 1.605, 0.085 | pivot dekat telinga (lihat masalah #6) |
| LeftShoulder → Arm → ForeArm → Hand | x 0.035 → 0.205 → 0.50 → 0.76, y ≈ 1.44 | T-pose, lengan lurus ke samping |
| Jari (Index, Middle, Ring, Pinky) | pangkal x ≈ 0.85–0.87, 3 ruas + `_End` | z offset per jari: +0.031, +0.009, −0.013, −0.033 |
| Thumb | 4 titik miring ke depan-bawah | |
| UpLeg → Leg → Foot → ToeBase → Toe_End | x ≈ 0.10–0.118; y 0.95 → 0.52 → 0.09 → 0.025 | |

**Aturan penting:** semua tulang punya **rotasi bind = identitas**. Artinya di T-pose semua sudut 0, jadi sudut pose bisa ditulis langsung dalam derajat relatif T-pose. `buildSkeleton` mengubah posisi dunia menjadi posisi lokal (`p − p_parent`).

---

## 4. Membangun mesh

### 4.1 MeshBuilder

`MeshBuilder(seed, smooth)` mengumpulkan segitiga ke **bucket per material** (`mb.use('skin')`, `mb.use('jacket')`, …). Setiap vertex membawa posisi, warna, 4 indeks tulang, dan 4 bobot.

Di akhir, `geometry()` melakukan:
1. Satu `BufferGeometry` per bucket.
2. Mode halus: `mergeVertices(g, 1e-5)` (vertex di posisi sama digabung), lalu `computeVertexNormals()` menghasilkan normal halus.
3. `mergeGeometries(geos, true)` menggabungkan semuanya menjadi 1 geometry dengan **group** per bucket. Urutan group = urutan array material.

### 4.2 Loft (sapuan cincin)

Hampir semua bagian (leher, lengan, jari, baju, celana, kepala) dibuat dengan `loft`. Input: daftar **station** `{c (pusat), rs (jari-jari samping), rf (jari-jari depan)}`.

Untuk setiap station:
- **T** (tangen) = arah dari station sebelumnya ke berikutnya.
- **F** (depan) = vektor `front` diproyeksikan tegak lurus T (Gram-Schmidt): `F = normalize(front − (front·T)T)`.
- **S** (samping) = `T × F`.
- Titik cincin ke-k: `p = c + rs·cos φ·S + rf·sin φ·F`, dengan `φ = π/2 + 2πk/N`. Jadi φ = π/2 adalah tepat di depan.
- Normal elips untuk offset: `n = normalize(S·cos φ/rs + F·sin φ/rf)`.
- `shape(i, φ, c)` menambah offset radial di sepanjang n. Ini yang dipakai untuk wajah dan lipatan baju.
- `open(φ, ring, c)` yang mengembalikan `true` membuat segitiga di situ dibuang. Dipakai untuk bukaan jaket dan kerah V.

Cincin bertetangga disambung dengan 2 segitiga per kotak. Ujung bisa ditutup `flat`, `point`, atau dibiarkan `none`.

### 4.3 Resampling halus

Station kunci ditulis sedikit (misalnya 16 untuk kepala), lalu `smoothStations(keys, sub)` menyisipkan `sub` cincin per segmen dengan **Catmull-Rom**:

```
p(t) = 0.5·(2p1 + (−p0+p2)t + (2p0−5p1+4p2−p3)t² + (−p0+3p1−3p2+p3)t³)
```

Diterapkan ke `c.x, c.y, c.z, rs, rf`. Nilai sub yang dipakai: kepala 3, kaus 6 (supaya kerah V tidak bergerigi), jaket/celana/lengan 3.

### 4.4 Bobot skin

`weigher(skel, ['Spine2','Neck'], power=4)`:

```
w_i = 1 / (jarak(p, segmen tulang i)^4 + 1e-12)
ambil 4 terbesar → normalisasi → buang yang < 0.02 → normalisasi lagi
```

- Setiap bagian hanya boleh dipengaruhi tulang yang **diizinkan**. Misalnya jaket bagian dada hanya `Spine1/Spine2/Shoulder`, sehingga tangan tidak ikut menarik dada.
- Pangkat 4 membuat transisi di sendi cukup tajam tapi tetap halus.
- `rigid(skel, 'Head')` memberi bobot 1 ke satu tulang. Dipakai untuk kepala, mata, gigi, dan telinga.
- Bagian tubuh sengaja **tumpang tindih** di sambungan (lengan masuk ke torso), jadi tidak ada celah walau sendi ditekuk.

---

## 5. Kepala tengkorak (bagian tersulit)

File: `src/zombie/real/head.ts`.

### 5.1 Profil dasar

16 cincin kunci `[h, rs, rf, z]`, dengan h = tinggi di atas tulang Head (0 = dagu bawah, 0.243 = ubun-ubun). Semua jari-jari dikali `HR = 1.07` (kepala sedikit lebih besar dari proporsi 7,5 kepala, supaya kesannya lebih berat dan seram).

| h | rs | rf | z | bagian |
|---|---|---|---|---|
| −0.006 | 0.036 | 0.034 | 0.008 | bawah dagu (cincin kecil, bukan piringan datar) |
| 0.022 | 0.054 | 0.054 | 0.034 | dagu |
| 0.075 | 0.070 | 0.083 | 0.012 | mulut |
| 0.150 | 0.082 | 0.098 | 0 | mata |
| 0.170 | 0.084 | 0.101 | −0.004 | dahi (terlebar) |
| 0.228 | 0.062 | 0.079 | −0.016 | atas kepala mulai menutup |
| 0.243 | 0.002 | 0.002 | −0.017 | ubun-ubun (hampir titik, jadi kubah) |

Pusat z bergeser maju di bagian bawah (rahang menonjol) dan mundur di atas (tengkorak belakang).

### 5.2 Fitur wajah = jumlah gaussian

Wajah **tidak dimodel titik per titik**. Setiap fitur adalah gaussian 2D di koordinat (tinggi h, sudut a dari depan):

```
gauss(x, μ, σ) = exp(−((x−μ)/σ)²/2)
offset(h, a) = Σ amplitudo · gauss(h, μh, σh) · gauss(|a|, μa, σa)
```

Offset negatif = cekung, positif = menonjol. Nilai yang dipakai (fungsi `faceFeature`):

| Fitur | Amplitudo (m) | μh | σh | μa (rad) | σa |
|---|---|---|---|---|---|
| Rongga mata | −0.030 | 0.148 | 0.020 | 0.47 | 0.20 |
| Tulang alis | +0.009 | 0.172 | 0.009 | 0.42 | 0.32 |
| Batang hidung (tulang saja) | +0.010 | 0.145 | 0.014 | 0 | 0.09 |
| Lubang hidung busuk | −0.020 | 0.118 | 0.012 | 0 | 0.14 |
| Tulang pipi | +0.012 | 0.128 | 0.013 | 0.82 | 0.18 |
| Pipi cekung | −0.020 | 0.092 | 0.022 | 0.74 | 0.22 |
| Pelipis | −0.010 | 0.175 | 0.022 | 1.28 | 0.20 |
| Ceruk mulut tanpa bibir | −0.010 | 0.085 | 0.016 | 0 | 0.45 |
| Dagu | +0.009 | 0.028 | 0.015 | 0 | 0.25 |
| Sudut rahang | +0.007 | 0.050 | 0.016 | 1.15 | 0.25 |
| Tonjolan belakang kepala | +0.004 | 0.205 | 0.030 | π | 0.60 |

Fungsi ini dipanggil lewat `shape` di loft kepala (32 sisi). Untuk mengubah wajah, cukup ubah tabel ini.

### 5.3 Warna wajah

Warna dihitung per vertex:
- **Makin cekung, makin gelap**: `dark = min(1, kedalaman/0.022) × 0.72`. Rongga mata dan pipi otomatis jadi gelap tanpa perlu dicat.
- Merah daging di sekitar mulut dan lubang hidung, memar di sekitar mata, dan luka di dahi yang posisinya acak per seed.
- Pita mulut (h 0.079–0.095, |a| < 0.62) diberi warna hampir hitam `#1c0605`. Pita ini yang melebar saat rahang terbuka, sehingga terlihat seperti rongga mulut.

### 5.4 Rahang berengsel

- `MOUTH_SPLIT = 0.084`. Vertex dengan `y < HY + 0.084` **dan** `z > 0.012` (bagian depan bawah) diberi bobot penuh ke tulang `Jaw`, sisanya ke `Head`.
- Saat `Jaw.rotation.x` bertambah, rahang bawah berputar di pivot dekat telinga dan mulut terbuka.
- Di belakang gigi ada elipsoid gelap `#160404` (rongga mulut), supaya saat mulut terbuka yang terlihat bukan bagian dalam kepala yang kosong.

### 5.5 Mata, gigi, telinga

- **Mata**: elipsoid r ≈ 0.0135, ditaruh di permukaan dasar lalu didorong masuk 0.031 m ke dalam rongga. Pupil abu kecil di depannya. Material `eye` emissive `#c4d8dc` dengan intensitas 0.28, cukup untuk efek "susu menyala" tanpa terlihat seperti lampu.
- **Gigi**: kotak tipis, 12 di atas (h 0.098, ikut Head) dan 11 di bawah (h 0.071, ikut Jaw). Posisinya di permukaan dikurangi 0.011 m (masuk ke dalam), dimiringkan acak ±10°, warna kuning `#c4b27c` sampai coklat `#6e5a32`, dan sekitar 10% hilang secara acak per seed.
- **Telinga**: elipsoid pipih yang diputar 0.25 rad.

---

## 6. Badan dan pakaian

### 6.1 Leher, dada, tangan (`real/body.ts`)
- Leher dibuat dengan loft, ditambah `shape` untuk tendon dan jakun.
- Kulit dada yang terlihat di kerah V diberi aliran darah gelap (`bloodRun` dengan warna `bloodDark`).
- Tangan terdiri dari pergelangan, telapak, gundukan ibu jari, dan 5 jari. Tiap jari adalah loft sepanjang 3 ruas dengan cincin sedikit membesar di buku jari, kuku berupa kotak pipih di ujung, dan ujung jari berdarah.

### 6.2 Pakaian (`real/clothes.ts`)
Lapisan dari dalam ke luar, masing-masing sedikit lebih besar supaya tidak tembus:

| Bagian | Sisi | Trik |
|---|---|---|
| Kaus V-neck | 48 | `open`: `c.y > 1.35 && |a| < ((c.y−1.35)/0.15)·0.5` membuat V yang melebar ke atas. Resampling sub 6 supaya tepi V halus. |
| Jaket | 40 | `open`: `|a| < 0.2 + 0.32·(ring/jumlah)` membuat bukaan depan yang melebar ke bawah. `shape` menambah lipatan vertikal. Kerah (atas 1.53) dan lapel dibuat terpisah. Lengan punya lipatan siku dan manset. |
| Celana | 32 / 24 | Pinggul plus dua kaki, lipatan di lutut dan ujung, saku samping (kotak), ikat pinggang (loft 40 sisi), gesper kuningan (material `metal`). |
| Sepatu | 20 | Sepatu kulit, sengaja dibuat lebih lebar dari kaki (masalah #12). |

Ukuran badan dan pakaian dikali `V.bulk` (0,96–1,06 per seed).

### 6.3 Variasi per seed (`real/variant.ts`)
`hash(seed, i)` memilih dari daftar:
- kulit: `#a89ca2 #ad978b #9c9f95 #a398aa`
- jaket: 5 warna (zaitun, coklat, hitam, abu, coklat tua)
- kaus: 4 warna, celana: 4 warna, sepatu: 3 warna

Warna kulit akhir (`skinAt`) = warna dasar → dicampur memar (fbm frekuensi 9) → dicampur daging mentah (fbm 24) → urat gelap (*ridged noise*: `1 − |2n − 1|`, diambil puncaknya saja) → digelapkan sesuai `dark`.

---

## 7. Detail permukaan lewat shader

File: `real/materials.ts`. Pori, kerutan, lipatan kulit jaket, dan serat kain **tidak memakai tekstur maupun UV**.

1. Vertex shader menyimpan `vObj = position`, yaitu posisi **bind-pose**. Karena memakai posisi sebelum skinning, pola noise ikut bergerak bersama badan dan tidak "berenang" saat pose berubah.
2. Fragment shader menghitung tinggi `hh = aA·fbm(vObj·fA·sA) + aB·noise(vObj·fB)`. Mode `ridged` memakai `1 − |2·fbm − 1|`, yang menghasilkan garis lipatan tajam (cocok untuk kulit jaket).
3. Normal diganggu dengan rumus *bump mapping* three.js (`perturbNormalArb`): turunan layar `dFdx/dFdy` dari posisi dan dari `hh` menghasilkan normal baru.
4. Warna juga divariasikan sedikit: `diffuse *= 1 + cv·(fbm − 0.5)`.
5. `customProgramCacheKey` wajib diisi supaya material dengan parameter berbeda tidak memakai shader yang sama.

| Material | fA | aA | ridged | fB | aB |
|---|---|---|---|---|---|
| skin | 38 | 0.0011 | – | 420 | 0.00007 |
| shirt | 14 | 0.0016 | – | 650 | 0.00004 |
| jacket | 22 | 0.0016 | ya | 300 | 0.00006 |
| pants | 18 | 0.0016 | ya | 380 | 0.00005 |
| leather | 40 | 0.0005 | ya | 500 | 0.00003 |

**Batasan:** detail ini hanya ada di viewer. GLB berisi bentuk, warna vertex, dan rig, tanpa bump.

---

## 8. Pose

File: `src/zombie/pose.ts`. Setiap frame: `resetPose` → set rotasi tulang → `groundTo`.

### 8.1 Konvensi sudut
- Euler order `'XYZ'` di three.js berarti **Z diterapkan pertama**, lalu Y, lalu X.
- Lengan kiri turun = −Z, lengan kanan turun = +Z. Lengan maju: kiri −Y, kanan +Y. Karena itu `armPose` mengalikan dengan `s` (+1 kiri, −1 kanan), sehingga satu definisi pose berlaku simetris.
- X pada tulang kaki: negatif = paha maju (fleksi pinggul), positif pada `Leg` = lutut menekuk.
- Rahang: `Jaw.rotation.x` dalam derajat. 6–10 untuk diam, 18–26 untuk meraung.

### 8.2 Helper
- `armPose(r, s, {shoulder, arm, elbow, wrist, curl, spread})` mengatur bahu, lengan atas, siku, pergelangan, tekukan 3 ruas jari, dan kipas jari.
- `legPose(r, s, hip, knee, foot, splay)` mengatur kaki.
- `hunch(r, t, extra)` membuat punggung bungkuk dengan kepala mendongak, ciri khas zombie.
- Animasi kecil (napas, goyang) memakai `sin(t·frekuensi)`.

### 8.3 Menempel ke lantai (`groundTo`)
Setiap pose punya daftar titik kontak `[tulang, jarak tulang ke permukaan]`. Setelah rotasi diterapkan:

```
delta = min over contacts (y_dunia_tulang − clearance)
Hips.position.y −= delta
```

Titik kontak terendah jadi tepat menyentuh lantai.

| Pose | Kontak |
|---|---|
| standar | kedua Foot, ToeBase, Toe_End |
| crawl | kedua tangan (0.025), kedua lutut/`Leg` (0.065), `RightToe_End`, `Spine1` (0.13) |
| sit | `Hips` (0.11), kedua kaki (0.08), ujung jari kaki, `LeftHand` (tangan yang menopang) |

### 8.4 Pose duduk (contoh hitungan)
Masalahnya: rotasi `Hips` juga memutar kedua kaki, karena kaki adalah anak Hips. Hips dimiringkan −14° (badan bersandar ke belakang), jadi sudut paha dunia = sudut Hips + sudut UpLeg.
- Kaki kiri ditekuk (lutut naik): UpLeg −111°, Leg +71°, Foot +54°. Paha dunia ≈ −125°, betis kembali ke bawah, telapak rata.
- Kaki kanan lurus ke depan: UpLeg −74°, ditambah Hips −14° ≈ −88°, artinya hampir horizontal di lantai.
- Lengan kiri ke belakang-bawah sebagai penopang: `arm [22, −4, 84]`, siku 4°.

---

## 9. Masalah yang muncul dan perbaikannya

| # | Gejala | Penyebab | Perbaikan |
|---|---|---|---|
| 1 | Tampilan 4 view: figur keluar frame | frustum kamera ortografis ditulis dalam koordinat absolut, padahal relatif ke kamera | pakai ±halfW/±halfH yang muat 4 figur |
| 2 | Screenshot dari browser pane basi/terlambat | pane membatasi `requestAnimationFrame` | render manual lewat `__zm.frame()` lalu `__zm.capture()` ke file PNG, kemudian file dibaca |
| 3 | Low-poly: celah di selangkangan | torso berhenti terlalu tinggi | torso diperpanjang ke bawah, bagian di bawah y 0.97 diwarnai seperti celana |
| 4 | Kepala seperti kaleng, dagu berupa piringan datar | profil hampir silinder dan tutup `flat` di bawah | profil kubah KEYS dengan cincin kecil di bawah dagu dan ujung atas hampir titik |
| 5 | Wajah datar, tidak terbaca sebagai tengkorak | amplitudo gaussian terlalu kecil (±0.005) | dinaikkan ke 0.01–0.03, rongga mata −0.03 |
| 6 | Mulut terbuka seperti kantong di bawah dagu | pivot Jaw terlalu rendah (y 1.632) | pivot dipindah ke (0, 1.69, −0.035), dekat telinga |
| 7 | "Kantong" di bawah dagu | cincin kunci di h −0.03 | cincin itu dihapus |
| 8 | Mulut terbuka berwarna kulit | bagian dalam bibir belum diwarnai | pita mulut dicat `#1c0605` dan ditambah elipsoid rongga mulut |
| 9 | Mata seperti lampu senter | ukuran dan emissive terlalu besar | r 0.0135, emissive 0.28, mata didorong 0.031 m ke dalam rongga |
| 10 | Gigi seperti papan nisan | kotak terlalu besar dan terlalu menonjol | lebar 0.0036, masuk 0.011 m, miring acak, sebagian hilang |
| 11 | Wajah terlalu terang di scene horor | SpotLight 70 dan kulit terlalu pucat | SpotLight 42, palet kulit digelapkan |
| 12 | Sepatu seperti tunggul | loft sepatu terlalu sempit | sepatu diperlebar |
| 13 | Darah di dada terlihat seperti dasi | aliran darah sempit dan terlalu merah | `bloodDark`, lebih lebar dan lembut |
| 14 | Tepi kerah V bergerigi | terlalu sedikit cincin dan sisi | sub 6, 48 sisi, V dimulai lebih tinggi (1.35) |
| 15 | Pose duduk melayang atau tembus lantai | lupa bahwa rotasi Hips ikut memutar kaki | sudut kaki dihitung ulang (bagian 8.4) dan Hips dijadikan titik kontak |
| 16 | Script otomatisasi terputus di tengah | Vite HMR memicu `location.reload` setelah file disimpan | tunggu sebentar setelah edit, lalu jalankan ulang |

---

## 10. Cara memeriksa hasil (otomatis)

Viewer membuka API `window.__zm` (jalankan di console browser atau dari otomasi):

```js
__zm.set({ style: 'real', scene: 'horor', pose: 'roar', view: 'wajah', rig: false, seed: 7 });
__zm.setTime(1.2);          // waktu animasi tetap, supaya hasil bisa diulang
__zm.frame();               // render 1 frame
await __zm.capture('real_wajah_meraung');   // → renders/real_wajah_meraung.png
await __zm.exportGlb('zombie_real_s7');     // → renders/zombie_real_s7.glb
__zm.stats();               // { triangles, bones, height }
```

Checklist setiap perubahan:
1. `npx tsc --noEmit` tidak ada error.
2. Tidak ada error di console.
3. Render view: `4 view` (proporsi), `wajah` (detail kepala), dan pose yang diubah.
4. Bandingkan dengan gambar referensi di `docs/ref/`.
5. Ekspor GLB lalu buka di Blender. Pastikan 66 joint dan mesh ikut bergerak saat tulang diputar.

---

## 11. Cara mengembangkan

**Menambah pose**
1. Tambah nama ke `PoseName` dan `POSES` di `pose.ts`.
2. Tulis blok `if (pose === 'nama') { … }` memakai `hunch/armPose/legPose/jaw/rot`.
3. Kalau tidak berdiri, isi `contacts` dengan tulang yang menyentuh lantai.
4. Tombol di panel muncul otomatis dari `POSES`.

**Mengubah wajah**: ubah tabel di `faceFeature` (bagian 5.2). Amplitudo lebih besar = fitur lebih dalam, σ lebih kecil = fitur lebih tajam.

**Menambah warna**: tambah hex ke daftar di `makeVariant`.

**Menambah pakaian**: buat fungsi di `real/clothes.ts`:
- `mb.use('namaMaterial')`;
- `loft(...)` dengan jari-jari sedikit di luar lapisan di bawahnya;
- `weigher` dengan tulang yang relevan;
- panggil dari `buildReal` di `build.ts`;
- kalau memakai material baru, tambahkan `case` di `realMaterial`.

**Lebih realistis lagi** (di luar jangkauan kode prosedural): ekspor GLB → Blender → sculpt detail (multires) → bake normal map → tekstur cat. Rig dan bobot dari kode ini tetap bisa dipakai.

---

## 12. Ringkasan teknik dan sumbernya

| Teknik | Dipakai untuk | Sumber (lihat 06-sumber.md) |
|---|---|---|
| Linear blend skinning | deformasi mesh oleh tulang | glTF 2.0 skin spec, three.js SkinnedMesh |
| Bobot inverse-distance | bobot otomatis | penyederhanaan dari Baran & Popović 2007 (Pinocchio) |
| Loft dengan frame Gram-Schmidt | semua bagian tubuh | geometri diferensial dasar (sweep surface) |
| Catmull-Rom | resampling cincin halus | Catmull & Rom 1974 |
| Gaussian sum | fitur wajah | fungsi basis radial (RBF) |
| Value noise + fbm, ridged noise | warna kulit, urat, bump | Perlin 1985; Musgrave (ridged multifractal) |
| Bump mapping dari turunan layar | pori dan lipatan | Mikkelsen 2010, "Bump Mapping Unparametrized Surfaces on the GPU" (dasar `perturbNormalArb` three.js) |
| Euler XYZ, hierarki tulang | pose | three.js `Object3D` / `Euler` |
