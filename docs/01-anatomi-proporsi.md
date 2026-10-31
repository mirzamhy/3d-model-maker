# 01 — Anatomi, Proporsi, Postur, Palet

Semua angka di sini masuk ke `spec.ts`. Satuan meter. Sumbu: **+Y atas, +Z depan (arah wajah), +X kiri karakter**. Origin di lantai, di tengah antara kedua kaki.

## 1. Unit kepala

Proporsi figur manusia biasa dihitung dalam "tinggi kepala" (H). Manusia dewasa realistis ≈ 7,5–8 H (Loomis, 1943). Referensi zombie ini sedikit bergaya: kepala agak besar, badan kurus → **7 H**.

```
TINGGI = 1.75
H = TINGGI / 7 = 0.25
```

## 2. Tinggi landmark (bind pose tegak, sebelum bungkuk)

Nilai = kelipatan H dari lantai. Postur bungkuk diterapkan **setelah** bind pose (lihat §4), supaya skinning dihitung pada pose netral.

| Landmark | Tinggi (H) | Meter | Catatan |
|---|---|---|---|
| Puncak kepala | 7.0 | 1.750 | |
| Mata | 6.5 | 1.625 | rongga cekung |
| Dagu | 6.0 | 1.500 | rahang terbuka sedikit |
| Pangkal leher / bahu | 5.6 | 1.400 | bahu turun (droop) |
| Puting / dada | 5.0 | 1.250 | |
| Pusar / pinggang | 4.2 | 1.050 | ikat pinggang di sini |
| Selangkangan (crotch) | 3.5 | 0.875 | sendi panggul ±0.04 di atasnya |
| Ujung celana pendek | 2.7 | 0.675 | tepi bergerigi |
| Lutut | 2.0 | 0.500 | |
| Atas bot | 1.0 | 0.250 | |
| Pergelangan kaki | 0.35 | 0.088 | |
| Lantai | 0 | 0 | |

## 3. Lebar dan panjang (tegak, dilihat dari depan)

| Ukuran | Nilai (H) | Meter |
|---|---|---|
| Lebar bahu (sendi ke sendi) | 1.45 | 0.36 |
| Lebar pinggul (sendi ke sendi) | 0.80 | 0.20 |
| Lebar kepala | 0.62 | 0.155 |
| Dalam kepala (depan-belakang) | 0.78 | 0.195 |
| Lengan atas (bahu→siku) | 1.30 | 0.325 |
| Lengan bawah (siku→pergelangan) | 1.15 | 0.29 |
| Tangan (pergelangan→ujung jari tengah) | 0.80 | 0.20 |
| Paha (sendi panggul→lutut) | 1.65 | 0.415 |
| Betis (lutut→pergelangan kaki) | 1.65 | 0.41 |
| Panjang telapak / bot | 1.10 | 0.275 |

Lengan zombie sengaja **±8% lebih panjang** dari manusia normal → ujung jari jatuh di pertengahan paha (lihat A5 di PRD).

Ketebalan (radius penampang, rx = kiri-kanan, rz = depan-belakang):

| Segmen | rx | rz |
|---|---|---|
| Leher | 0.040 | 0.042 |
| Dada atas | 0.150 | 0.095 |
| Pinggang | 0.120 | 0.085 |
| Panggul | 0.140 | 0.095 |
| Lengan atas | 0.035 | 0.035 |
| Siku | 0.030 | 0.030 |
| Lengan bawah | 0.032 | 0.028 |
| Paha | 0.060 | 0.062 |
| Lutut | 0.045 | 0.048 |
| Betis | 0.042 | 0.046 |

Badannya **kurus**: lengan dan betis jauh lebih tipis dari manusia sehat. Ini kunci siluet.

## 4. Postur (diterapkan sebagai pose, bukan bentuk mesh)

Dari view samping referensi:

| Sendi | Rotasi (derajat) | Sumbu |
|---|---|---|
| Hips | +4 maju | X |
| Spine | +6 | X |
| Spine1 | +8 | X |
| Spine2 (dada atas) | +10 | X |
| Neck | +12 | X |
| Head | −18 (wajah naik lagi, melihat ke depan) | X |
| Shoulder (klavikula) | turun 8, maju 6 | Z, Y |
| Arm (bahu) | turun 70 dari T-pose → ≈ A-pose 20° dari badan | Z |
| ForeArm | tekuk 15 | X lokal |
| Hand | tekuk 10, jari melengkung 25–40 per ruas | |
| UpLeg | maju 8 | X |
| Leg (lutut) | tekuk 14 | X |
| Foot | kompensasi supaya telapak rata di lantai | X |

Total condong panggul→kepala ≈ 15° (cek A6).

Asimetri kecil membuat lebih "hidup": bahu kiri 2° lebih turun, kepala miring 4°.

## 5. Bagian-bagian (dari referensi)

**Kepala**: botak dengan beberapa helai rambut gelap runcing di atas-belakang (4–7 "spike" pipih). Tengkorak sedikit lonjong. Pipi cekung. Telinga kecil menempel. Rongga mata dalam, mata putih pucat bulat kecil. Rahang terbuka, gigi kuning tidak rata (6–8 gigi atas, 5–7 bawah). Luka merah di dahi kanan.

**Torso**: kemeja krem pendek lengan, terbuka di depan (dua sisi depan tergantung), tepi bawah dan lengan sobek bergerigi, bercak cokelat-merah. Di dalam: kaus/singlet abu-abu tua berleher V, perut hijau terlihat. Ikat pinggang cokelat tua dengan gesper kotak abu.

**Lengan**: kulit hijau, kurus, siku menonjol, luka merah di lengan bawah. Tangan besar relatif terhadap lengan, jari panjang bengkok seperti cakar.

**Celana**: pendek selutut cokelat, sobek bergerigi di ujung, robekan di paha kanan memperlihatkan luka.

**Kaki**: betis hijau dengan luka; bot cokelat besar (lebih lebar dari betis), bagian atas bot terlipat kain sobek, ujung kiri sobek dan jari kaki keluar.

**Belakang**: kemeja utuh dengan bercak gelap; rambut hanya di bagian atas-belakang.

## Palet

Warna referensi (diambil kira-kira dari gambar; boleh disetel ±5%):

| Nama | Hex | Pakai di |
|---|---|---|
| skin | `#9DA66B` | kulit dasar |
| skinShadow | `#6F7A4A` | rongga mata, sela jari, bawah dagu |
| skinLight | `#B8BE86` | dahi, tulang pipi, buku jari |
| wound | `#7A2E22` | luka |
| woundDark | `#4A1A14` | pusat luka |
| shirt | `#C9B492` | kemeja |
| shirtDirt | `#8E6F4E` | bercak di kemeja |
| undershirt | `#4B4A48` | singlet |
| pants | `#6B5640` | celana |
| belt | `#4A3526` | ikat pinggang |
| buckle | `#7C7C7A` | gesper |
| boot | `#5E4430` | bot |
| hair | `#2B2A2A` | rambut |
| eye | `#E4E0C8` | bola mata |
| teeth | `#D8CBA0` | gigi |

Aturan warna: setiap face = warna dasar × (1 + jitter), jitter ∈ [−0.04, +0.04] dari hash seed+indexFace. Jangan pakai warna jenuh atau emissive. Material `MeshStandardMaterial({ vertexColors: true, flatShading: true, roughness: 0.9, metalness: 0 })`.
