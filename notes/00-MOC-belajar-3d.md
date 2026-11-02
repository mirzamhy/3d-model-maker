---
tags: [moc]
dibuat: 2026-11-02
---
# Peta belajar 3D (MOC)

Pintu masuk semua catatan belajar. Kembali ke [Home](../Home.md).

## Konsep
- [Metode meshing](metode-meshing.md): SDF, collapse, QuadriFlow, dual contouring, template, snap, warp
- [Ukuran kualitas mesh](ukuran-kualitas-mesh.md): dev, aspect, sliver, planes, dihedral
- [Topologi wajah low-poly](topologi-wajah-lowpoly.md): kolom dan baris fitur, loop mata, loop mulut, nasolabial, pole

## Eksperimen
- [Eksperimen topologi kepala](eksperimen-topologi-kepala.md): 8 metode, budget 900 tris (2 Nov 2026)

## Referensi
- [Thread BlenderArtists topologi low-poly](blenderartists-topologi-lowpoly.md)
- [Sumber belajar](sumber-belajar.md)

## Workflow
- [Workflow Claude + Blender + Obsidian](claude-blender-workflow.md)

## Status sekarang (2 Nov 2026)
- Eyeless mid yang disetujui: pipeline collapse. Kandidat pengganti: **collapse_soft**.
- Masalah terbuka: **mulut** kurang struktur di semua versi. Solusi yang dituju: template topologi tetap (cincin mulut, loop nasolabial) lalu snap ke SDF.

## Aturan catatan
- Satu konsep satu note. Tautkan ke note lain dan ke `docs/`.
- Gambar disimpan di `notes/attachments/` (`lab/` untuk render eksperimen, `topology-refs/` untuk referensi).
- Tiap eksperimen baru: tambah baris di note eksperimen beserta penilaian user.
