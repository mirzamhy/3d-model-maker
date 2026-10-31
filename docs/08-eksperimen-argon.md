# 08 — Eksperimen: Model Dibuat oleh Gemini Argon

Tujuan: menguji apakah AI lain (Gemini `gemini-4-argon`, lewat proxy lokal `gemini-web2api` di `http://127.0.0.1:8081/v1`) bisa membuat zombie dengan mengikuti [07-proses-pembuatan.md](07-proses-pembuatan.md) dan API mesh di repo ini.

Hasilnya dipasang sebagai gaya ketiga **"Argon (Gemini)"** di viewer, sehingga memakai rig, pose, dan lampu yang sama dengan versi asli.

## File

| File | Isi |
|---|---|
| `src/zombie/argon/zombie.ts` | versi aktif (ronde 3) |
| `src/zombie/argon/zombie.r1.ts.txt` … `r3.ts.txt` | salinan tiap ronde |
| `tools/argon/ask-argon.mjs` | kirim dokumen + API lengkap, minta seluruh file (ronde 1 dan 2) |
| `tools/argon/ask-part.mjs` | kirim pesan pendek, minta satu fungsi saja, lalu sambungkan otomatis ke file (ronde 3) |
| `tools/argon/feedback-*.md` | kritik yang dikirim tiap ronde |
| `renders/argon*_*.png` | render tiap ronde |

## Jalannya eksperimen

| Ronde | Cara | Hasil |
|---|---|---|
| 1 | Prompt ±48 ribu karakter: dokumen 07 + mesh.ts + skeleton + variant. Minta 1 file utuh. | Lolos typecheck tanpa perbaikan, rig dan 9 pose jalan, 8.900 segitiga. Wajah seperti telur kosong karena mata dan gigi ditaruh di koordinat tetap yang terkubur di dalam kepala. Ada celah di pergelangan. |
| 2 | Kode ronde 1 + 10 poin kritik kode + 3 gambar render. | Dengan gambar, proxy mengembalikan jawaban kosong (unggah gambar tidak didukung). Versi teks saja hasilnya lebih jelek: kepala disalin persis, telapak tangan hilang, 6.300 segitiga. |
| 3a | Deskripsi **visual** dalam teks + "ubah kepala saja", tetap dengan prompt panjang. | Kepala tetap tidak diubah, yang diubah malah bagian lain. |
| 3a' | Pesan **pendek** (±10 ribu karakter): instruksi di depan, hanya fungsi `buildHead` + ringkasan API. | Berhasil. Gigi terlihat, rahang menganga, rongga mata dan hidung gelap. |
| 3b | Cara yang sama untuk `buildBody` (leher, dada, tangan). | Percobaan pertama terpotong (batas output ±10 ribu karakter). Setelah diminta "maksimal 150 baris", berhasil: tangan tersambung ke pergelangan, jari beruas. Total 13.500 segitiga. |

## Pelajaran

1. **Deskripsikan apa yang terlihat**, bukan hanya bug di kode. Contoh: "kepala seperti telur manekin, tidak ada mata", lalu jelaskan bentuk targetnya.
2. **Pesan pendek dan instruksi di depan.** Pada prompt yang sangat panjang, Argon cenderung mengabaikan instruksi di bagian akhir.
3. **Satu bagian per ronde.** Minta satu fungsi saja, lalu sambungkan dengan skrip. Jangan minta seluruh file ditulis ulang.
4. **Batasi panjang jawaban.** Output lebih dari ±10 ribu karakter akan terpotong.
5. **Gambar tidak bisa dikirim** lewat proxy ini, jadi semua umpan balik visual harus ditulis dalam teks.

## Sisa kekurangan (ronde 3)

- Bola mata terlalu kecil dan tenggelam.
- Jaket kaku seperti kotak, dengan kerah bersilang.
- Darah di kaus masih berbentuk kotak-kotak.
- Lengan masih tabung polos tanpa lipatan.

---

## Zombie 2: dibangun Argon dari lembar referensi ChatGPT

Alur dua tahap dari [PANDUAN-AI-MODEL-3D.md](PANDUAN-AI-MODEL-3D.md): ChatGPT (MODE ANALISIS) membuat lembar referensi dari foto ([referensi-zombie-jas-chatgpt.webp](ref/referensi-zombie-jas-chatgpt.webp)), lalu Argon membangun modelnya (MODE BUILD).

| Langkah | Isi |
|---|---|
| Spesifikasi | [spec/zombie2.spec.json](../spec/zombie2.spec.json): angka dari lembar, palet hex, deskripsi bagian, daftar asumsi. Argon tidak bisa melihat gambar, jadi spesifikasi ini yang dikirim sebagai teks. |
| Basis | `src/zombie/argon/zombie2.ts`, dimulai dari hasil Argon ronde 3 (kepala dan badan), dipecah menjadi fungsi `buildHead`, `buildHair`, `buildBody`, `buildInner`, `buildSuit`, `buildLower`. |
| Ronde per bagian | `tools/argon/zombie2/z2-*.md` berisi pesan yang dikirim: rambut (3 ronde), jas dan lengan, rompi + kemeja + dasi, celana + ikat pinggang + sepatu. Tiap pesan memuat deskripsi visual keadaan sekarang, target, angka, dan daftar API. |
| Perbaikan sendiri | Warna diturunkan sekitar 12% (cahaya membuat warna pucat berlebih terang), lebar lapel dikurangi. |

Hasil: 34.900 segitiga, 66 tulang, rig dan semua pose jalan, tombol **Zombie 2 (Argon)** di viewer. Render: `renders/z2_*.png`.

**Yang berhasil:** jas dengan bahu, kerah, lapel, manset, dan robekan siku; rompi, kemeja, dasi; celana dengan lipatan dan lutut bolong; sepatu Oxford bertali; rambut menutup kepala. Tampilan gerombolan terbaca sebagai zombie berjas.

**Yang masih kurang dibanding lembar referensi:**
- Wajah: kulit terlalu putih dan rata, rahang bawah tampak seperti janggut putih, poni terlihat seperti kacang panjang. Belum ada kesan wajah manusia yang tirus.
- Rambut berupa gumpalan elips, bukan helai.
- Lapel masih agak lebar, lubang lutut tampak seperti tambalan karena kulit di bawahnya hampir sewarna.
- Garis rambut di dahi masih bergerigi.
- Detail kecil di lembar (retak kulit, jahitan, noda halus) belum ada.

**Pelajaran tambahan:**
- Pesan paling efektif memuat: keadaan sekarang dalam kata-kata ("jas seperti kotak abu-abu tanpa kerah"), target, tabel stasiun berangka, dan batas baris (≤ 150).
- Kamera "wajah" memakai posisi kepala dari pose sebelumnya. Saat mengambil render, panggil `__zm.set(...)` dua kali bila pose dan tampilan berubah bersamaan.
- Server proxy Argon bisa mati sendiri. Jalankan lagi dengan `gemini-web2api.exe --port 8081 --cookie-file cookie.txt`.
