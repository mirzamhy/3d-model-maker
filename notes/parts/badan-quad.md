# Badan quad (body) — topologi dirancang, bentuk dari F2

Status: v1 (3 Nov 2026), menunggu penilaian user. Permintaan: "body nya mesh it make it perfect" → pilihan user:
topologi quad bersih, gaya bidang datar seperti kepala.

Script: `tools/blender/body_quad.py` → `output/head-game/body/body_quad_v1.blend` (+ `head_body_quad_v1_color.*`).
Hasil: badan 100% quad (n-gon/segitiga sisa milik kepala), tertutup, simetris, total 1938 segitiga (F2 + kepala: 2372).
Rig F2 73 tulang, bobot disalin dari F2.

## Kenapa tidak pakai mesh F2 saja
F2 dibangun dari cincin tapi disimpan segitiga. Digabung lagi (`join_triangles`) → 1056 quad, sisa 178 segitiga,
semua di sambungan: kipas bintang leher→bahu, ketiak retak (celah gelap), selangkangan V, jari, jari kaki.
![[badan_f2_sendi_sebelum.png]]

## Rancangan
- **Batang badan 10 kolom** (0, 22, 48, 90, 120, 180° tiap sisi) = cincin leher kepala → jahitan leher semua quad,
  tanpa pita zip. Baris: leher, trapezius, 3 baris bahu, dada, rusuk, pinggang, perut, pinggul, selangkangan.
- **Lubang lengan**: 4 quad sekitar kolom 90 di 3 baris bahu tidak dibuat → lubang 8 titik = cincin pertama lengan
  (atas, atas-depan, depan, bawah-depan, bawah, bawah-belakang, belakang, atas-belakang). Lengan: cincin 8, tiga cincin
  di siku (atas, tepat, bawah — pasangan tulang helper).
- **Tangan mitten**: cincin kotak (superellipse n = 3) pergelangan → telapak → buku jari → tengah jari → ujung;
  ujung 8-gon ditutup 3 quad. Lengkung jari F2 dikurangi setengah. Jempol tumbuh dari face telapak yang paling
  searah jempol, diletakkan sepanjang sisi telapak (2 cincin + tutup).
- **Selangkangan**: baris bawah pecah jadi dua loop kaki 8 titik (tengah depan, 22, 48, 90, 120, tengah belakang,
  dalam-belakang, dalam-depan). Dua quad di bawah selangkangan berbagi edge tengah.
- **Kaki**: tiga cincin di lutut; tabung menekuk ke depan (pergelangan, tumit, tengah telapak, bola kaki, jari),
  ujung ditutup 3 quad. Frame cincin dibawa "parallel transport", jadi kolom tidak terpuntir saat menekuk.
- **Bentuk**: tiap titik = sinar dari sumbu tulang ke permukaan F2 (BVH ray cast, sinar pertama keluar).
  Tangan pakai ukuran parametrik (sela jari F2 bikin sinar meleset).
- **Bobot**: titik terdekat di permukaan F2 → bobot 3 titik segitiga dicampur barycentric, ambil 4 terbesar.

![[badan_quad_v1_sendi.png]]
![[badan_quad_v1_tangan.png]]

## Uji pose (`pose_test.py`, POSE_SET=relaxed,squat; tulang helper digerakkan setengah sudut sendi)
Lengan turun: ketiak bersih, celah lama F2 hilang. Jongkok: lutut dan pinggul terlipat tanpa kempis.
![[badan_quad_v1_pose_relaxed.png]]
![[badan_quad_v1_pose_squat.png]]

## Sisa
- Selangkangan depan agak menggembung (titik tengah depan baris bawah).
- Bahu depan: satu bidang lebar dari dada ke pangkal lengan (10 kolom) — gaya planar, tapi otot dada belum ada.
- Jari tidak bisa ditekuk satu-satu (mitten); bobot jari tetap dari F2.

Terkait: [[badan-f2]], [[hidung]], [[uji-gerak-viewer]], [[konsep-part-modular]].
