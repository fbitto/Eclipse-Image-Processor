# AEL 1.4.1 partial-annulus NRGF oracle

`ael_nrgf_chain_141.npz` contains 290 output probes generated directly from the bundled upstream AEL runtime at commit `17029c9284748c087adcd0d40241f7e3faf8d778`. The upstream function is `ael.filters.nrgf(..., bin_px=2, min_count=12, partial_annuli='chain')`.

The deterministic 900 × 1400 synthetic scene is AEL's `test_nrgf_chain_keeps_a_cut_corona_flat_and_leaves_whole_annuli_alone` control: center (820, 330), radius 150, a power-law corona with two smooth angular harmonics and seeded noise. `tests/test_nrgf.py` reconstructs the input. The archive stores integer `coordinates` (y, x) at every 4096th finite output pixel and the corresponding float32 `expected` values. Full-array comparison against upstream was also exact when the fixture was generated. No astronomical data or runtime AEL dependency is included.

The independent radial-variation gate requires less than half the historical variation and a standard deviation below 0.06 in each of three sectors. Complete-annulus comparisons require exact equality, including NaN support. Historical AEL 1.3.3 fixtures remain in use for the numerical API's observed-annulus default.

Copyright (c) 2026 Pere Guerra Serra, MIT; see the [retained notice](../../docs/third-party/AEL-MIT.txt).
