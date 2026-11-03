---
tags: [moc]
dibuat: 2026-11-02
---
# Peta belajar 3D (MOC)

Pintu masuk semua catatan belajar. Kembali ke [Home](../Home.md).

## Konsep
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
- [Badan F2 + kepala baru](parts/badan-f2.md): badan lengkap F2 (rig 73 tulang) dijahit ke kepala template; pilihan user
- [Hidung (nose)](parts/hidung.md): bidang datar Asaro (depan, samping, bawah); v2 tidak mancung, menunggu penilaian
- [Uji gerak di browser](uji-gerak-viewer.md): lama vs baru berdampingan, jalan/jongkok/lompat/zombie; rumus rotasi sumbu dunia
- [Torso](parts/torso.md): torso Blender v2 (cadangan, diganti badan F2)
- [Telinga (ear)](parts/ear.md): gaya setengah hati dari referensi user; v13 **disetujui** (trace titik per titik dari gambar user, n-gon utuh)

## Referensi
- [Thread BlenderArtists topologi low-poly](blenderartists-topologi-lowpoly.md)
- [Sumber belajar](sumber-belajar.md)
- [Cara belajar topologi](cara-belajar-topologi.md): prinsip, kursus, rencana latihan 7 hari

## Workflow
- [Workflow Claude + Blender + Obsidian](claude-blender-workflow.md)

## Status sekarang (3 Nov 2026)
- Eyeless mid yang disetujui: pipeline collapse. Kandidat pengganti: **collapse_soft**.
- **BASELINE kepala = template v7 (3 Nov)**: `output/head-game/template/head_baseline*.glb`. Riwayat: v6 disetujui untuk mulut; bibir, celah, sudut mulut, dan ujung hidung sudah terbaca; 918 tris, 26 sliver. **v7**: garis rahang, leher ramping, tengkuk mulus. Sisa: tepi gelap di samping hidung, bahu belum ada. **Telinga v13 disetujui** (trace dari gambar user); baseline = kepala v7 + telinga v13 dibangun di atas baseline, menunggu penilaian.

## Aturan catatan
- Satu konsep satu note. Tautkan ke note lain dan ke `docs/`.
- Gambar disimpan di `notes/attachments/` (`lab/` untuk render eksperimen, `topology-refs/` untuk referensi).
- Tiap eksperimen baru: tambah baris di note eksperimen beserta penilaian user.
