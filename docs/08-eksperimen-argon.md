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
