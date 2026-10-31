# Zombie Low-Poly — Paket Panduan untuk AI

Folder ini adalah brief lengkap untuk AI (Claude, Gemini, dll.) yang akan membuat model zombie low-poly secara prosedural (kode TypeScript + Three.js), lengkap dengan rig dan animasi dasar.

**Baca berurutan. Jangan menulis kode sebelum selesai membaca 00 sampai 04.**

| Urutan | File | Isi |
|---|---|---|
| 0 | [PRD.md](PRD.md) | Tujuan, masalah hasil v1, syarat lulus (acceptance criteria) |
| 1 | [01-anatomi-proporsi.md](01-anatomi-proporsi.md) | Ukuran tubuh, siluet, postur, palet warna dari referensi |
| 2 | [02-struktur-mesh.md](02-struktur-mesh.md) | Cara membangun mesh low-poly: loft, faceting, baju sobek, luka |
| 3 | [03-rigging.md](03-rigging.md) | Hierarki tulang, bind pose, skinning, bobot (weights) |
| 4 | [04-matematika.md](04-matematika.md) | Rumus: transformasi, quaternion, LBS/DQS, IK, noise, gait |
| 5 | [05-struktur-file-dan-alur.md](05-struktur-file-dan-alur.md) | Struktur folder kode + alur kerja per fase + checklist |
| 6 | [06-sumber.md](06-sumber.md) | Daftar jurnal, spesifikasi, dan repo GitHub |
| 7 | [07-proses-pembuatan.md](07-proses-pembuatan.md) | Catatan kerja nyata: urutan langkah, angka wajah, shader, hitungan pose, masalah + perbaikan |

Gambar:

- [ref/referensi-4-view.webp](ref/referensi-4-view.webp) — **target**. Turnaround depan, kiri, belakang, kanan.
- [ref/hasil-gemini-v1.png](ref/hasil-gemini-v1.png) — **hasil gagal** generasi pertama. Dipakai sebagai contoh apa yang tidak boleh terjadi.

## Aturan emas (ringkas)

1. **Satu tubuh, bukan tumpukan bola.** Semua bagian harus tersambung. Tidak ada celah antara kepala-leher-dada-pinggul-kaki.
2. **Tulang dulu, daging belakangan.** Bangun skeleton dengan ukuran dari 01, lalu mesh dibentuk mengikuti tulang.
3. **Angka dari spec, bukan dari tebakan.** Semua ukuran dan warna diambil dari `spec.ts` (lihat 05). Tidak ada angka ajaib di file part.
4. **Low-poly = sedikit sisi + flat shading**, bukan primitif bulat (sphere/dodecahedron) yang ditempel.
5. **Verifikasi visual tiap fase**: render 4 view dengan kamera yang sama seperti referensi lalu bandingkan berdampingan.
