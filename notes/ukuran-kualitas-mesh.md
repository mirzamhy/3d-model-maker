---
tags: [konsep, ukuran, qa]
dibuat: 2026-11-02
---
# Ukuran kualitas mesh

Angka yang dipakai untuk menilai mesh low-poly tanpa hanya mengandalkan mata. Semuanya dihitung di `tools/blender/head_topo_lab.py`. Dipakai di [Eksperimen topologi kepala](eksperimen-topologi-kepala.md).

| Ukuran | Arti | Bagus kalau |
|---|---|---|
| **tris** | jumlah segitiga | sesuai budget (eyeless mid ±900) |
| **closed** | tiap edge dipakai tepat 2 muka | `true` |
| **symmetry** | vertex kiri punya pasangan cermin | 0 unmatched |
| **dev mean / p95 (mm)** | jarak permukaan ke SDF asli, di vertex dan titik tengah muka | kecil: bentuk setia |
| **aspect p90** | sisi terpanjang / tinggi terpendek segitiga (1.15 = sama sisi) | mendekati 2 |
| **slivers** | jumlah segitiga sangat gepeng (sisi² / 2·luas > 8) | sedikit |
| **planes** | jumlah area datar (tetangga beda normal < 3°) | sedikit = bidang besar |
| **dihedral p95** | sudut lipat antar-muka yang besar | kecil = permukaan tenang |
| **quad share** | porsi quad | tinggi kalau mau diedit atau dianimasi |

Catatan: angka saja tidak cukup. QuadriFlow punya aspect bagus tapi wajahnya hilang. Selalu cek render 4 view dan close-up.
