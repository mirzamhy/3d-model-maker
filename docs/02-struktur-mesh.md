# 02 — Struktur Mesh Low-Poly

## 1. Prinsip

Model dibangun dari **loft**: deretan cincin penampang (cross-section) di sepanjang tulang, lalu cincin yang berurutan disambung dengan quad (2 segitiga). Ini cara yang sama dengan box-modeling/edge-loop di Blender, hanya ditulis dalam kode.

Kenapa loft, bukan primitif:

- Cincin sambungan antar segmen bisa **dibagi bersama** (shared ring) → tidak ada celah (A2).
- Jumlah sisi per cincin terkendali → poly budget pasti.
- Setiap cincin tahu tulang mana pemiliknya → bobot skin mudah dihitung.

## 2. Lapisan (layers)

| Lapisan | Geometri | Catatan |
|---|---|---|
| Body | loft kulit: torso, leher, kepala, lengan, tangan, paha, betis | satu mesh tertutup |
| Shirt | loft offset +6–10 mm dari kulit torso & lengan atas, terbuka di depan | tepi bawah bergerigi |
| Undershirt | tidak perlu mesh terpisah: warnai face kulit dada dengan warna singlet | hemat poligon |
| Pants | loft offset +8 mm dari panggul & paha | ujung bergerigi |
| Belt | 1 cincin tebal (prisma 8 sisi) + box gesper | |
| Boots | loft sendiri, lebih lebar dari betis | |
| Head extras | gigi (prisma kecil), mata (icosahedron detail 0, r=0.012) masuk ke rongga, rambut (piramida pipih) | |

Semua lapisan digabung ke **satu BufferGeometry** (group per material jika perlu) dan memakai skeleton yang sama.

## 3. Penampang (cross-section)

Cincin elips dengan N sisi:

```
untuk k = 0..N-1:
  φ = 2π·k/N + offsetSudut
  p = center + rx·cos φ · X̂ + rz·sin φ · Ẑ        (X̂, Ẑ = sumbu lokal tulang yang tegak lurus arah tulang)
```

| Segmen | N sisi | Cincin |
|---|---|---|
| Torso (panggul→leher) | 8 | 6 |
| Leher | 6 | 2 |
| Kepala | 8 | 6–7 (profil di §4) |
| Lengan atas / bawah | 6 | 3 + 3 |
| Tangan + jari | 4–5 | telapak 2, jari 3 ruas × 4 jari + jempol |
| Paha / betis | 6 | 3 + 3 |
| Bot | 7 | 4 + ujung |

Radius sepanjang segmen pakai profil `r(t)`, t ∈ [0,1], interpolasi smoothstep antar nilai di tabel 01 §3. Contoh lengan bawah: lebar dekat siku, mengecil di pergelangan.

## 4. Kepala

Bangun sebagai loft vertikal dengan profil:

| Cincin | Tinggi relatif | rx | rz | Pusat z |
|---|---|---|---|---|
| 0 (bawah dagu) | 0.00 | 0.045 | 0.040 | +0.030 |
| 1 (rahang) | 0.18 | 0.060 | 0.070 | +0.015 |
| 2 (mulut) | 0.33 | 0.068 | 0.085 | +0.010 |
| 3 (tulang pipi) | 0.50 | 0.075 | 0.095 | 0 |
| 4 (mata/alis) | 0.62 | 0.078 | 0.098 | 0 |
| 5 (dahi) | 0.80 | 0.070 | 0.090 | −0.005 |
| 6 (ubun) | 0.95 | 0.040 | 0.055 | −0.010 |
| tutup | 1.00 | titik | | |

Detail wajah via **perpindahan vertex**, bukan objek tempel:

- Rongga mata: vertex cincin 4 di sudut φ ≈ ±35° dari depan didorong masuk 12 mm.
- Pipi cekung: cincin 2–3 di samping (φ ≈ ±70°) masuk 6 mm.
- Hidung: 1 vertex depan cincin 3 keluar 10 mm (bentuk segitiga).
- Mulut: face depan cincin 1–2 dipisah → rahang (cincin 0–1) di-skin ke tulang `Jaw`, sisanya ke `Head`.

## 5. Tepi sobek (hem bergerigi)

Ujung kemeja, lengan kemeja, celana pendek, atas bot. Ambil cincin paling bawah, lalu geser tiap vertex ke bawah:

```
dy_k = −A · (0.35 + 0.65 · hash(seed, k))       A = 0.03..0.06 m
```

Lalu sisipkan vertex tengah di antara k dan k+1 yang **naik** (dy = −0.2A) → pola gigi gergaji. Hasilnya segitiga panjang yang terlihat seperti kain robek di referensi.

## 6. Faceting dan noise

1. Bangun geometry **indexed** dulu (buat skin & tes jarak).
2. Tambahkan jitter posisi deterministik ke tiap vertex (kecuali vertex sambungan antar part):
   `p += n̂ · r · 0.05 · (hash(seed, i) − 0.5)` (5% radius lokal, sepanjang normal).
3. Di akhir, `geometry.toNonIndexed()` lalu `computeVertexNormals()` → setiap segitiga punya normal sendiri = look faceted. Atau cukup `flatShading: true` di material.

## 7. Luka dan bercak

Pewarnaan per face berdasarkan jarak centroid face ke titik luka:

```
untuk tiap luka W (pusat c, radius R, seed):
  d = |centroid − c|
  t = 1 − smoothstep(R·0.4, R, d + R·0.3·(hash(face)−0.5))
  warna = lerp(warna, wound, t);   jika t > 0.8 → woundDark
```

Tepi luka jadi tidak rata karena noise per face. Posisi luka referensi: dahi kanan, dada kiri, lengan bawah kanan, paha kanan, betis kiri.

## 8. Anggaran poligon

| Bagian | Segitiga |
|---|---|
| Kepala + rahang + gigi + mata + rambut | 450 |
| Torso + leher | 260 |
| Lengan ×2 | 200 |
| Tangan ×2 (jari sederhana) | 400 |
| Kaki ×2 | 200 |
| Bot ×2 | 220 |
| Kemeja | 380 |
| Celana + ikat pinggang | 300 |
| **Total** | **≈ 2.400** (batas 3.000) |

Untuk zombie jauh (LOD1): tangan jadi "sarung" tanpa jari, N sisi turun 2 → ±1.200 segitiga. Opsional: simplifikasi otomatis via meshoptimizer (Garland & Heckbert QEM).

## 9. Yang dilarang

- `SphereGeometry`, `DodecahedronGeometry`, `CylinderGeometry` sebagai bagian tubuh utama.
- Objek organ/iga/usus yang ditempel di luar badan.
- Garis wireframe / `EdgesGeometry` di render final.
- Angka posisi yang tidak berasal dari tulang atau `spec.ts`.
