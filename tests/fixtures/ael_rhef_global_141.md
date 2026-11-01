# Current AEL 1.4.1 global RHEF oracle

`ael_rhef_global_141.npz` was generated directly by `ael.radial.radial_quantile_rank(image, valid, geometry)` from the installed runtime matching current upstream commit `17029c9284748c087adcd0d40241f7e3faf8d778` (repository HEAD `331196e225b758cb0ef90cbb93b4de7f1028d396`, checked 2 November 2026).

The two seeded synthetic positive power-law scenes have shapes 128×160 and 131×163, centers (79.3,63.7) and (126.7,44.3), and radius 17. Inputs include a missing lunar disk, missing rectangle/rows, a zero and a negative observation. Keys prefixed `0_`/`1_` retain input image, explicit validity, float32 radius/position-angle maps, geometry and complete float32 expected ranks. The global function uses 2-pixel rings, minimum population 12 and 257 quantiles. Missing/nonpositive output stays NaN.

The application's reference-precision path and actual continuous-RHEF worker are checked byte for byte against both outputs. The independent float64 numerical API remains available and is tested separately against scalar references. No private photographs or runtime AEL dependency are included.

Copyright (c) 2026 Pere Guerra Serra, MIT; see [retained attribution](../../docs/third-party/AEL-MIT.txt).
