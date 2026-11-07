# AEL 1.4.2 NAFE oracle

Frozen from the installed plugin 1.1.6 runtime, `ael/filters.py` (`nafe_neighbourhood` and `nafe`) without modifications. Source SHA-256: `a0e31c8ae4ddb7b0c82e705acdb442e7485047f44f96783a83e7c554e134c88d`. The upstream package is not a test/runtime dependency.

The synthetic 32 × 40 input contains a ramp, Gaussian feature, seeded noise (692) and missing support; sigma 0.04 in input units, odd window 9, level step 0.005. Expected float32 E uses the upstream twelve Gaussians, c_m=1 and centre normalization 1. The port changes intensity coordinates for numerical stability; parity tolerance is 2e-6.

Copyright (c) 2026 Pere Guerra Serra, MIT; see `docs/third-party/AEL-MIT.txt`.
