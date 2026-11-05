---
tags: [alat, blender, mcp]
---
# Blender MCP (Claude menyetir Blender live)

Repo: ahujasid/blender-mcp (add-on "MCP for Blender" v1.8 + server `uvx blender-mcp`).
Dipasang 3 Nov 2026:
- Add-on: `tools/blender-mcp/addon.py` (diunduh dari raw GitHub, dibaca dulu: socket `localhost:9876`,
  telemetri opt-in default **mati**), dipasang + diaktifkan di preferensi Blender 5.2.
- Server: `claude mcp add blender -s user -e DISABLE_TELEMETRY=true -- uvx blender-mcp` (user scope).
- Tool: info scene, jalankan Python di Blender (`execute_blender_code`: simpan file dulu!), screenshot viewport,
  impor Poly Haven / Sketchfab / Poly Pizza, generate AI (Hyper3D Rodin, Hunyuan3D, Meshy, Tripo: butuh key).

Cara pakai: buka Blender (GUI) -> N (sidebar) -> tab "MCP for Blender" -> **Connect to Claude** /
Start server. Lalu sesi Claude baru (tool MCP dimuat saat sesi mulai).

Bedanya dengan skrip headless kita: user dan Claude melihat viewport yang sama, revisi tanpa render bolak-balik.
Bukan generator model otomatis: bentuk tetap dibangun (lihat [[mpfb-cetakan-badan]], [[model-dari-gambar-referensi]]).
