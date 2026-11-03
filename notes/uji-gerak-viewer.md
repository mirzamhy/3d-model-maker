# Uji gerak di browser (viewer gerak)

Halaman `viewer/gerak.html` (dev server `npm run dev`, buka `http://localhost:5195/viewer/gerak.html`).
Badan lama (F2 asli) dan baru (F2 + kepala template) berdiri berdampingan, gerak sama persis:
T-pose, diam, jalan, lari, jongkok, lompat, lambai, zombie, tengok. Ada wireframe, tulang, kecepatan, kamera.

GLB dibuat `tools/blender/f2_glb.py` → `output/head-game/f2/f2_old.glb`, `f2_new.glb` (rig 73 tulang + warna).

![[gerak_jalan.jpg]]
![[gerak_jongkok.jpg]]

## Pelajaran

1. **Rotasi pose ditulis di sumbu dunia, bukan sumbu tulang.** Tulang dari Blender punya "roll" sendiri,
   jadi sumbu lokalnya acak. Rumus: `q = restLocal * (restWorld⁻¹ * D * restWorld)`.
   D = putaran di sumbu dunia T-pose (X = angguk/ayun depan-belakang, Y = putar, Z = angkat ke samping),
   ikut terbawa gerak induk. Sisi kanan = cermin: tanda Y dan Z dibalik.
2. **Tulang helper F2** (ArmHelper, ElbowHelper, KneeHelper, HipHelper) harus ikut diputar setengah sudut sendinya.
   Kalau tidak, sendi yang ditekuk kempis (lihat `src/zombie/lowbody/helpers.ts`).
3. **Kaki napak lantai otomatis**: setelah pose, ukur titik kaki (Foot, ToeBase) terendah dibanding rest, geser
   Hips sebesar selisihnya. Jongkok juga kunci posisi depan-belakang pergelangan kaki, jadi pinggul mundur sendiri.
4. **Warna per-face tidak ikut ekspor glTF.** Atribut warna di domain FACE tidak ada di `color_attributes`
   (cuma di `attributes`) dan exporter cuma baca POINT/CORNER. Salin ke atribut CORNER dulu, lalu
   `export_vertex_color="NAME"`.

Terkait: [[parts/badan-f2]], [[konsep-part-modular]].

## Pelajaran tambahan (umpan balik user)

5. **Lambai aneh = salah pose, bukan rig.** Lengan bawah ditekuk ke atas di sumbu Z (bukan engsel siku), telapak
   masih menghadap bawah/samping. Benar: putar bahu 90° dulu (`[X, -90]`, telapak jadi menghadap depan), lalu siku
   ditekuk di engselnya sendiri (Y). Siku = engsel satu sumbu; arah tekuk diatur dari putaran bahu.
   ![[gerak_lambai_v2.jpg]]
6. **Jangan `flatShading` di Three.js untuk mesh quad.** glTF memecah quad jadi 2 segitiga; flatShading hitung normal
   per segitiga → quad tidak rata pecah dua warna, wajah berisik. Pakai normal dari Blender (satu per face).
