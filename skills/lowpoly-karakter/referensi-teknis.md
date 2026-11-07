# Referensi teknis: lowpoly-karakter

## Blender headless

```bash
"/c/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b file.blend --factory-startup -P script.py -- args
```

- Pakai path absolut di argumen skrip. Path Windows di heredoc/sed: `\f` jadi form feed. Pakai `/`.
- Hapus file lewat variabel shell: `rm -- "${O:?}"`.

## Koordinat dan skala trace (kepala v17)

- Koordinat kepala (x, y atas, z depan) ke Blender: (x, −z, y).
- Depan f01: S = 0.0003 m/px. Samping f06: SD = 0.000325 m/px.
- `to_m(xpx, ypx, dpx) = (xpx*S, (915-ypx)*S - 0.122, (444-dpx)*SD)`.
- Tinggi samping ke depan: `yf = 470 + (ys - 490) * 1.085` (patokan alis + dagu).
- Referensi: `notes/attachments/ref/survivor_ref/full2/f01.jpg`, `f06.jpg`.

## Alat QA

- `tools/blender/align_side.py`: render samping ortho dengan skala/pusat sama dengan f06 (1920x1080).
- `tools/blender/col_turn.py`: render berwarna kulit/rambut di sudut tertentu, framing sama dengan crop video.
- `tools/blender/ear_close.py`: close-up telinga ortho 12 cm + wireframe.
- `tools/qa/`: eval E1, IoU siluet E2, sheet E3, ekspor glb, deformasi E4 (lihat `notes/alat-qa.md`).
- IoU bisa turun karena detail yang benar (celah jari). Nilai dengan mata di close-up juga.

## Jebakan bmesh / Blender

- Cek manifold: `[e for e in bm.edges if len(e.link_faces) != 2]` harus kosong.
- `bm.verts[i]` basi setelah vertex baru ditambah; simpan list dulu, panggil `ensure_lookup_table()`.
- BMVert di `set` Python bisa salah diam-diam setelah op bmesh; pakai index yang di-refresh.
- Jangan merge vertex di sudut mulut (non-manifold); rapatkan saja.
- `image.pixels` mulai dari baris **bawah**. Ukur titik, jangan tebak dari gambar.
- Warna domain FACE tidak ikut glTF (exporter hanya POINT/CORNER). Salin ke CORNER, `export_vertex_color="NAME"`.
  Cari atribut lewat `me.attributes.get("Col")`; `color_attributes.new` bisa bikin `Col.001` yang tidak dibaca material.
- Mirror weld membelah tutup leher; hapus muka yang semua titiknya di cincin (mode `FACES`).
- Importer glTF menambah icosphere 80 face sebagai bentuk tulang: jangan dihitung.
- Proyeksi snap ke permukaan terdekat berbahaya di cekungan; proyeksikan sepanjang sinar pembuatnya.

## Pipeline game

```bash
blender -b --factory-startup -P tools/blender/game_parts.py -- \
  --head output/head-game/template/head_lp_v17.blend \
  --json "C:/Mirza Personal/tiktok/game/src/render/lowpoly/survivor_parts.json" \
  --blend output/game/parts_v1.blend
```

- Head/Ears ke `headLP`, Hair ke `hairLP`, lainnya ke `faceLP`.
- Transform kepala: `HEAD_S = 1.35`, `HEAD_OFF = (0, 0.06, 0.01)`.
- Warna linear: kulit (0.612, 0.302, 0.173); rambut (0.27, 0.18, 0.11)^2.2.

## Browser pane

- Pane tersembunyi: requestAnimationFrame berhenti, canvas WebGL kosong. Cek data lewat JavaScript atau render di Blender.

## Catatan sumber

- Kepala v17 + rambut: `notes/parts/kepala-trace-v17.md`
- Telinga: `notes/parts/ear.md`; kepala bidang: `notes/parts/kepala-bidang.md`
- Game: `notes/parts/game-deadzone.md`; rig: `notes/parts/rig.md`; baju: `notes/parts/baju.md`, `baju-loft.md`
- Jebakan umum: `notes/claude-blender-workflow.md`
