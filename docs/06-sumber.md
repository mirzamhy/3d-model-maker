# 06 — Sumber

Tanda: ✔ = metadata dicek ulang lewat web saat dokumen ini ditulis (31 Okt 2026). ○ = referensi klasik yang umum dikutip, belum dicek ulang di sesi ini — cek DOI sebelum dikutip di tulisan formal.

## A. Skinning dan deformasi

1. ○ Magnenat-Thalmann, N., Laperrière, R., & Thalmann, D. (1988). Joint-dependent local deformations for hand animation and object grasping. *Proceedings of Graphics Interface '88*, 26–33. — Asal mula Linear Blend Skinning.
2. ○ Lewis, J. P., Cordner, M., & Fong, N. (2000). Pose space deformation: A unified approach to shape interpolation and skeleton-driven deformation. *Proceedings of SIGGRAPH 2000*, 165–172. — Rumusan LBS dan masalah candy-wrapper.
3. ✔ Kavan, L., Collins, S., Žára, J., & O'Sullivan, C. (2007). Skinning with dual quaternions. *Proceedings of the 2007 Symposium on Interactive 3D Graphics and Games (I3D)*. https://users.cs.utah.edu/~ladislav/dq/
4. ✔ Kavan, L., Collins, S., Žára, J., & O'Sullivan, C. (2008). Geometric skinning with approximate dual quaternion blending. *ACM Transactions on Graphics, 27*(4), Article 105. PDF: https://users.cs.utah.edu/~ladislav/kavan08geometric/kavan08geometric.pdf
5. ✔ Jacobson, A., Baran, I., Popović, J., & Sorkine, O. (2011). Bounded biharmonic weights for real-time deformation. *ACM Transactions on Graphics, 30*(4), Article 78 (SIGGRAPH 2011). https://www.cs.toronto.edu/~jacobson/weblog/1784.html — Bobot otomatis yang mulus.
6. ○ Loper, M., Mahmood, N., Romero, J., Pons-Moll, G., & Black, M. J. (2015). SMPL: A skinned multi-person linear model. *ACM Transactions on Graphics, 34*(6), Article 248. — Model tubuh LBS + blend shape, rujukan struktur skeleton tubuh manusia.

## B. Rigging otomatis

7. ✔ Baran, I., & Popović, J. (2007). Automatic rigging and animation of 3D characters. *ACM Transactions on Graphics, 26*(3), Article 72 (SIGGRAPH 2007). PDF: https://people.csail.mit.edu/ibaran/papers/2007-SIGGRAPH-Pinocchio.pdf — Sistem "Pinocchio".
8. ✔ Xu, Z., Zhou, Y., Kalogerakis, E., Landreth, C., & Singh, K. (2020). RigNet: Neural rigging for articulated characters. *ACM Transactions on Graphics, 39*(4). arXiv: https://arxiv.org/abs/2005.00559 — Proyek + kode: https://zhan-xu.github.io/rig-net

## C. Rotasi dan inverse kinematics

9. ○ Shoemake, K. (1985). Animating rotation with quaternion curves. *ACM SIGGRAPH Computer Graphics, 19*(3), 245–254. — Quaternion & slerp.
10. ✔ Aristidou, A., & Lasenby, J. (2011). FABRIK: A fast, iterative solver for the inverse kinematics problem. *Graphical Models, 73*(5), 243–260. https://doi.org/10.1016/j.gmod.2011.05.003 — Halaman penulis: https://www.andreasaristidou.com/FABRIK

## D. Mesh low-poly, simplifikasi, noise

11. ○ Garland, M., & Heckbert, P. S. (1997). Surface simplification using quadric error metrics. *Proceedings of SIGGRAPH 97*, 209–216. — Dasar LOD otomatis.
12. ○ Perlin, K. (2002). Improving noise. *ACM Transactions on Graphics, 21*(3), 681–682.

## E. Proporsi figur

13. ○ Loomis, A. (1943). *Figure Drawing for All It's Worth*. Viking Press. — Sistem unit kepala.

## G. Pembentukan mesh dari nol (SDF, meshing, retopologi)

Dicek 2 Nov 2026. Hasil uji di proyek ini: `docs/11-eksperimen-topologi.md`.

14. ✔ Quilez, I. Smooth minimum. https://iquilezles.org/articles/smin — Rumus `smin` yang dipakai `head_lowpoly.py`.
15. ✔ Ju, T., Losasso, F., Schaefer, S., & Warren, J. (2002). Dual contouring of Hermite data. *ACM Transactions on Graphics, 21*(3), 339–346. PDF: https://www.cs.wustl.edu/~taoju/research/dualContour.pdf
16. ✔ Jakob, W., Tarini, M., Panozzo, D., & Sorkine-Hornung, O. (2015). Instant field-aligned meshes. *ACM Transactions on Graphics, 34*(6), 189. https://rgl.epfl.ch/publications/Jakob2015Instant
17. ✔ Huang, J., Zhou, Y., Nießner, M., Shewchuk, J. R., & Guibas, L. J. (2018). QuadriFlow: A scalable and robust method for quadrangulation. *Computer Graphics Forum, 37*(5), 147–160. https://doi.org/10.1111/cgf.13498 — Ada di Blender (`object.quadriflow_remesh`).
18. ○ Ji, Z., Liu, L., & Wang, Y. (2010). B-Mesh: A modeling system for base meshes of 3D articulated shapes. *Computer Graphics Forum, 29*(7). — Lihat juga roadmap §2.

## F. Spesifikasi dan repositori GitHub

| Sumber | Tautan | Dipakai untuk |
|---|---|---|
| ✔ glTF 2.0 spec (Khronos) | https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html (bagian *Skins*) | Format skin, inverse bind matrix, maks 4 bobot per set |
| ✔ glTF skin schema | https://github.com/KhronosGroup/glTF/blob/main/specification/2.0/schema/skin.schema.json | Struktur `joints`, `inverseBindMatrices`, `skeleton` |
| three.js | https://github.com/mrdoob/three.js | `SkinnedMesh`, `Skeleton`, `Bone`, `SkeletonHelper` |
| three.js CCDIKSolver | https://github.com/mrdoob/three.js/blob/dev/examples/jsm/animation/CCDIKSolver.js | IK alternatif |
| three.js SkeletonUtils | https://github.com/mrdoob/three.js/blob/dev/examples/jsm/utils/SkeletonUtils.js | Clone banyak zombie dengan skeleton sendiri |
| three.js GLTFExporter | https://github.com/mrdoob/three.js/blob/dev/examples/jsm/exporters/GLTFExporter.js | Ekspor `.glb` |
| ✔ Caliko (FABRIK, Java) | https://github.com/FedUni/caliko | Contoh implementasi FABRIK dengan batasan sendi |
| meshoptimizer | https://github.com/zeux/meshoptimizer | Simplifikasi (QEM) untuk LOD |
| glTF-Transform | https://github.com/donmccurdy/glTF-Transform | Optimasi / cek file `.glb` |
| Blender Rigify (manual) | https://docs.blender.org/manual/en/latest/addons/rigging/rigify/ | Contoh struktur rig humanoid dan penamaan |
