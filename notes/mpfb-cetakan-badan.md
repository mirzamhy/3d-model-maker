---
tags: [alat, blender, badan]
---
# MPFB2 (MakeHuman untuk Blender) sebagai cetakan bentuk

Kenapa: membentuk anatomi dari siluet + pahat otot terus menghasilkan masalah (leher, sup segitiga).
MakeHuman sudah punya anatomi benar. Pakai sebagai **cetakan bentuk**, topologi tetap cincin quad kita
(gaya bidang besar, lihat [[model-dari-gambar-referensi]]).

- Repo: makehumancommunity/mpfb2 (GPL-3.0), ekstensi Blender "mpfb" 2.0.16. Pasang:
  `blender --online-mode -c extension install -s -e mpfb` (Blender default offline; flag ini cuma untuk perintah itu).
- Data bawaan 83 MB: base mesh, target (otot, proporsi, wajah), rig (standard, rigify), pose.
  **Proxy low-poly tidak ikut** (paket aset sistem terpisah) — tidak perlu, topologi kita sendiri.
- API: `from bl_ext.blender_org.mpfb.services.humanservice import HumanService`;
  `HumanService.create_human(macro_detail_dict=...)` dengan macro gender/age/muscle/weight/proportions/height
  (0..1), lalu `TargetService.bake_targets(body)` + apply modifier mask (buang geometri helper).
  Jalankan Blender **tanpa** `--factory-startup` (ekstensi ada di preferensi user).
- Skrip: `tools/blender/mpfb_body.py` -> `output/mpfb/mpfb_male_v1.blend` (13380 vertex, 26756 tris, pria, otot 0.8,
  diskalakan ke 1.78 m). Pose bawaan **A-pose** (lengan ~45 derajat turun), referensi kita T-pose.

![[attachments/ref/mpfb_male_v1_front.png]]
![[attachments/ref/mpfb_male_v1_34.png]]

Langkah berikut: pasang rig, putar lengan ke T-pose, lalu proyeksikan cincin quad kita ke permukaannya
(raycast BVH seperti `body_quad.py`), dan sesuaikan ke siluet survivor.
