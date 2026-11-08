---
tags: [moc]
dibuat: 2026-11-02
---
# Peta belajar 3D (MOC)

Pintu masuk semua catatan belajar. Kembali ke [Home](../Home.md).

## Konsep
- [Pipeline karakter dan evaluasi](pipeline-karakter-dan-evaluasi.md): 9 tahap brief sampai ekspor, gerbang E1–E5, jalur alat, rencana latihan (**rencana utama**)
- [Alat QA](alat-qa.md): `tools/qa/` eval E1, IoU siluet E2, sheet E3, ekspor glb, deformasi E4; survivor v5base sampai v12 (punggung/dada atas)
- [Metode meshing](metode-meshing.md): SDF, collapse, QuadriFlow, dual contouring, template, snap, warp
- [Ukuran kualitas mesh](ukuran-kualitas-mesh.md): dev, aspect, sliver, planes, dihedral
- [Konsep part modular](konsep-part-modular.md): karakter = rakitan part (landmark, bentuk, topologi, konektor, cek); usulan, menunggu konfirmasi
- [Gaya segitiga besar](gaya-segitiga-besar.md): decimate simetris dari baseline, fitur wajah dilindungi; **500 dan 350 disetujui**
- [Triangulasi quad ke segitiga](triangulasi-quad-ke-tri.md): versi segitiga untuk game, diagonal dipilih dari SDF
- [Pipeline AI image-to-3D](pipeline-ai-image-to-3d.md): cara kerja Tripo, Meshy, Hunyuan3D (multi-view, SDF, marching cubes, retopo, UV, bake, rig) dan bandingannya dengan cara kita
- [Topologi wajah low-poly](topologi-wajah-lowpoly.md): kolom dan baris fitur, loop mata, loop mulut, nasolabial, pole

## Eksperimen
- [Eksperimen topologi kepala](eksperimen-topologi-kepala.md): 8 metode, budget 900 tris (2 Nov 2026)
- [Template topologi kepala](template-topologi-kepala.md): v1–v7, loop dirancang + proyeksi ke SDF (3 Nov 2026)

## Kartu part
- [Model dari gambar referensi](model-dari-gambar-referensi.md): lembar 4 view → siluet → cincin quad (visual hull + prior); badan v1 survivor
- [MPFB2 sebagai cetakan badan](mpfb-cetakan-badan.md): MakeHuman di Blender untuk anatomi, topologi cincin quad tetap kita
- [Blender MCP](blender-mcp.md): Claude menyetir Blender live (viewport, screenshot, impor aset, AI generate)
- [Tutorial Rozi 3D: karakter low-poly](tutorial-rozi3d-lowpoly-karakter.md): box modeling dari kubus, jari dari extrude, rambut dari curve, baju dari duplikat face + Solidify
- [Badan quad](parts/badan-quad.md): topologi quad dirancang (10 kolom, lubang lengan 8, mitten, selangkangan quad), bentuk + bobot dari F2; v1 menunggu penilaian
- [Badan F2 + kepala baru](parts/badan-f2.md): badan lengkap F2 (rig 73 tulang) dijahit ke kepala template; pilihan user
- [Hidung (nose)](parts/hidung.md): bidang datar Asaro (depan, samping, bawah); v2 tidak mancung, menunggu penilaian
- [Uji gerak di browser](uji-gerak-viewer.md): lama vs baru berdampingan, jalan/jongkok/lompat/zombie; rumus rotasi sumbu dunia
- [Torso](parts/torso.md): torso Blender v2 (cadangan, diganti badan F2)
- [Tangan (jari)](parts/tangan.md): telapak 10 titik, 4 jari 3 ruas + jempol dari face buku jari (cara Rozi); v11 survivor **disetujui**
- [Baju modular](parts/baju.md): kaos, cargo, bot dari face badan + Solidify, bobot badan, kulit tertutup dibuang; E4 cek tembus; survivor v13
- [Kaos loft](parts/baju-loft.md): baju dengan bentuk sendiri (jatuh lurus dari dada, kelonggaran, rib kerah, kelim, manset, lengan tumpang); survivor v17a
- [Part DEADZONE](parts/game-deadzone.md): karakter untuk game zombie user (tiktok/): part kaku per tulang + instancing, kepala v16f dan badan bidang besar diekspor ke JSON game; viewer.html; lp1
- [Studi referensi survivor jaket](ref-survivor-jaket.md): 5 video wireframe user (kepala, torso, lengan, kaki): segitiga rapat hanya di bentuk, lapisan bertepi tebal, detail menonjol (kantong, tali, sol), rambut shard
- [Kepala v17 trace](parts/kepala-trace-v17.md): titik dibaca dari frame depan (x,y) + samping (z), segitiga manual sepanjang garis anatomi, rambut = massa tebal + duri tarik titik per zona (jambul, ubun, samping, tengkuk); 216 + 200 tris
- [Kepala campuran seed](parts/kepala-mix-seed.md): 3 style wajah (offset landmark v17) + 12 style rambut (parameter HP: zona cukur, mohawk, panjang, keriting) dicampur per seed, cek muka terbalik; prototipe `head_mix.py`
- [Kepala bidang besar](parts/kepala-bidang.md): kepala baru dari loft 10 kolom (rahang baji, hidung baji, rambut helm), gaya GIF referensi; v16b kepala bola + leher tusuk (base disetujui); v16c mulut, batang hidung, dagu lebar, rongga mata dalam; v16d rambut cambang + belakang; v16e telinga v13 dipasang; v16f detail (kelopak, lubang hidung, rona, helai)
- [Rig game](parts/rig.md): 52 tulang deform dari posisi sendi ref_body, bobot cincin (bukan bone heat), uji E4 8 pose; batas siku 110°, lutut 130° (bobot engsel)
- [Telinga (ear)](parts/ear.md): gaya setengah hati dari referensi user; v13 **disetujui** (trace titik per titik dari gambar user, n-gon utuh)

## Referensi
- [Thread BlenderArtists topologi low-poly](blenderartists-topologi-lowpoly.md)
- [Sumber belajar](sumber-belajar.md)
- [Cara belajar topologi](cara-belajar-topologi.md): prinsip, kursus, rencana latihan 7 hari

## Workflow
- [Workflow Claude + Blender + Obsidian](claude-blender-workflow.md)
- [Skill lowpoly-karakter](../skills/lowpoly-karakter/SKILL.md): ringkasan semua pelajaran (alur trace, gaya bidang besar, resep rambut, jebakan Blender, pipeline DEADZONE). Terpasang di `~/.claude/skills/lowpoly-karakter/`; kalau skill diubah, salin ulang ke sana.

## Status sekarang (7 Nov 2026)
- **Kepala v17r** (`head_lp_v17.blend`): trace dua pandangan, rambut massa + duri satu aliran, celah telinga ditutup. Belum dipasang di game (`game_parts.py` masih pakai v16f).
- Semua pelajaran dirangkum jadi skill `lowpoly-karakter` (`skills/`).

## Status lama (3 Nov 2026)
- Eyeless mid yang disetujui: pipeline collapse. Kandidat pengganti: **collapse_soft**.
- **BASELINE kepala = template v7 (3 Nov)**: `output/head-game/template/head_baseline*.glb`. Riwayat: v6 disetujui untuk mulut; bibir, celah, sudut mulut, dan ujung hidung sudah terbaca; 918 tris, 26 sliver. **v7**: garis rahang, leher ramping, tengkuk mulus. Sisa: tepi gelap di samping hidung. **Update 3 Nov**: hidung bidang datar v2 (`TPL_NOSE=planes`, tidak mancung), badan quad v1 (`body_quad.py`) menggantikan badan F2 sebagai kandidat, viewer gerak `viewer/gerak.html` (menunggu penilaian). **Telinga v13 disetujui** (trace dari gambar user); baseline = kepala v7 + telinga v13 dibangun di atas baseline, menunggu penilaian.

## Aturan catatan
- Satu konsep satu note. Tautkan ke note lain dan ke `docs/`.
- Gambar disimpan di `notes/attachments/` (`lab/` untuk render eksperimen, `topology-refs/` untuk referensi).
- Tiap eksperimen baru: tambah baris di note eksperimen beserta penilaian user.
