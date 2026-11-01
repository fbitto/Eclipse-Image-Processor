# Issue #3 follow-up execution

Started 1 November 2026, after commit 86f747c. Scope: the 27 open items and the remaining part of item 33 in [issue #3](https://github.com/fbitto/Eclipse-Image-Processor/issues/3).

## Agreed decisions

- Consult installed AEL code, docs and fixtures first; do not post to its maintainer at this stage.
- Main TIFF should match PSB presentation; preserve linear data separately as float32.
- Validate an optional log-intensity Larson–Sekanina mode, retaining the linear mode for existing recipes.
- Keep logarithmic AEL ACHF unchanged. Do not add AEL's experimental filters during these fixes.

## Ordered checkpoints

1. **36, 41, 42**: inactive edits preserve ongoing work; full-frame FNRGF extent follows source/geometry while smaller explicit limits remain; Original button tracks programmatic changes. **Implemented**; 33 GUI tests passed, including replacement-source coverage and inactive/excluded-control cancellation guards.
2. **40**: cooperative export/close cancellation, safe temporary cleanup and explicit outcome. **Implemented**; 53 export tests and 8 settings tests passed. Completed companion packages may remain; TIFF/JPEG/JSON cancellation ends before publication.
3. **8, 18, 20**: unresolved preview scales and consistent physical radial-bin widths. Implemented; 9 scale tests, 4 dispatcher tests and 21 AEL fixture tests passed. Full suite reached 369 tests with one outdated export-thread test double; it was updated to exercise cancellation on close.
4. **15, 16**: adaptive ACHF threshold units and measured support cost. Implemented local relative GUI rejection with signed/zero support; numerical API keeps absolute defaults. Benchmarked radii 2/4/8/16 on 384×512 and documented quadratic cost; 5 new relative tests and 3 independent/boundary tests passed. On the supplied native TIFF, adaptive encoded preview/native RMSE fell from 21.60% to 14.40%, still approximate; missing alpha and source checksum were preserved.
5. **21, 23–25, 33**: observed Gaussian/B3 canvas edges, local bilateral variance and upstream erf significance implemented; 8 masked tests, 3 observed-edge/significance tests and direct reference tests passed. Item 33 remains the next substep, subject to the requested AEL support-policy clarification.
6. **5, 7, 47, 49**: presented main TIFF, optional log Larson–Sekanina, full-precision reference and display colour profiles.
7. **12–14, 19, 22, 26–27, 29–31**: remaining controls, practical ranges, citations and documented conventions.

For each checkpoint: regression tests, relevant real-image checks, small commit, update this record. Reuse the supplied margin--2px TIFF; private images and generated outputs stay outside Git. Native Photoshop and physical Windows/exFAT validation remain separate checks.

## AEL status checked

Upstream HEAD: `331196e225b758cb0ef90cbb93b4de7f1028d396` (31 October 2026). Last ael/ revision: `17029c9284748c087adcd0d40241f7e3faf8d778`, AEL 1.4.1, installed Codex bundle 1.1.5. Installed and current upstream `filterbank.py` and `filters.py` are byte-identical (Git blob hashes checked).

Defaults: `nrgf`, `wow_edge_aware`, `achf_iso_04`. Five extra filters (`hessian_ridge`, `steerable_g2`, `mmt`, `noise_gate`, `coherence_diffusion`) are explicitly outside both defaults and “all”. Their documented benefits have limitations: thin faint rays can be removed by noise gating, ridge weighting can deepen stellar rings, and coarse reductions require padding to avoid spatial shifts. No automatic adoption is warranted.

The installed AEL self-test passed **124/124**, no skipped checks. The application's AEL fidelity/default tests passed **21 tests**. Upstream positive-only operator support is not a general image-validity rule. Its existing domain semantics do not by themselves resolve our item 33.
