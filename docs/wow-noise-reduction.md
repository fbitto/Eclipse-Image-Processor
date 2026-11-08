# Optional noise reduction for AEL edge-aware WOW

The **Noise reduction** slider is available in Basic, Standard and Expert when AEL edge-aware WOW is selected. Its range is 0–5 and its default is **0**, preserving the original operator and layer encoding exactly. Start a comparison at 1. Higher values suppress more texture and can remove faint corona. Other WOW backends retain their existing watroo thresholds; this new control is disabled for them and its value is retained.

## Numerical method

This is an EIP extension to the bundled AEL guided WOW, not a new upstream AEL algorithm. It changes neither the input image nor the edge-aware guide or recursive decomposition. For each band, estimate sigma as 1.4826 MAD of the unwhitened coefficients on fully supported observed samples outside four reference-disk radii. Require at least 64 samples. If there are too few outer samples, use all fully supported allowed samples and record that fallback. If even that support is insufficient, report an error instead of inventing a noise estimate; reduce scales or disable suppression. Statistical exclusions remain effective.

Retain the original whitening, centering and local-level removal. Multiply each band contribution by the smooth significance weight

```
gain = 1 - exp(-0.5 * (coefficient / (strength * sigma))**2)
```

If sigma is zero, leave that band unchanged. Zero strength bypasses all noise estimation and weighting. The gain preserves each contribution's sign, but it is not a proof against every possible halo in the composed image. No Gaussian blur is applied to source RGB, and no missing pixels are filled.

Accumulate the original detail alongside the suppressed detail. Use the original detail's display scale to encode the suppressed result, so normalization does not amplify remaining noise to the former contrast. Receipts record strength, per-band sigma, sample counts, fallback region and display anchor. Settings and the existing `wow_*` cache signature retain strength; changing opacity reuses the numerical result. TIFF/JPEG and PSB use the same independent layer.

The empirical estimator is not propagated detector uncertainty. Correlated stacking noise, radial gradients and real structures can enter its statistics. In a tightly cropped field, the fallback is more vulnerable to coronal structure. Coarse bands remain subject to the same test; suppression is naturally stronger where coefficient amplitude is small relative to the estimated noise.

## Validation and interpretation

The research utility `scripts/research/diagnose_wow_noise.py` guards the approved source hash, runs smooth-versus-soft-threshold controls, and compares strengths 0, 1, 2 and 3 with fixed monochrome presentation and 100% WOW opacity. It writes only to a new diagnostic output directory and checks the source hash again on completion. `--native` includes full native calculations; preview is approximate and estimates its own per-band noise after resampling.

On the seeded synthetic scene at strength 2, smooth suppression left 28.3% of the original white-noise background variation while retaining 91.6% of the injected streamer's displayed contrast; correlated-noise figures were 27.1% and 93.0%. Soft thresholding at the same strength left less variation (7.0% / 6.1%) but retained less streamer contrast (81.4% / 78.4%). These are comparisons at the same parameter, not matched-denoising optimality claims.

A weaker 0.01-amplitude injection into 0.006-sigma noise retained approximately 85% of its original response at strength 1, 70% at strength 2, and 49% at strength 3. Thus the stronger-streamer result must not be generalized to near-noise-limit corona. The default remains off; assess the loss of faint detail as well as the reduction of grain.

Tests cover zero-strength parity, constants, intensity rescaling, nonfinite/excluded data, partial rectangular coverage, support failure, correlated noise, faint injections, serial/thread parity, original display anchoring, cancellation, cache identity, GUI visibility, settings defaults, resolution settings and TIFF/PSB package consistency. Existing frozen AEL fixtures remain the zero-strength oracle.

Local comparisons are in `build/diagnostics/wow-noise-20261107/` (ignored generated data). The master is the approved `e1c3c474c41b4163b9c04099bb909948/result/master.fits`, SHA-256 `33ff81c882a0e5e98771b8c00f627af5860b56464798e16dc38e75122b45a005`; no rejected master is used. These comparisons isolate WOW; they do not establish increased astronomical SNR or certify real fine structure.


Full-native approved-master comparison (5420 × 2908, eight bands, fixed original display scale):

| Strength | Remaining background texture variation | Numerical time |
| --- | --- | --- |
| 0 | 100% | 29.11 s |
| 1 | 65.9% | 30.46 s |
| 2 | 31.5% | 31.50 s |
| 3 | 17.2% | 31.45 s |

The corresponding preview values were 100%, 67.0%, 33.0% and 18.4% (six target bands). All bands used outer-region statistics without fallback. Finite support was identical at all strengths; the FITS hash remained unchanged. Timings are one sequential comparison on this machine, not a benchmark guarantee. Native limb crops and full-canvas comparisons were inspected; the pre-existing thin boundary strip remains. Suppression does not correct that separate boundary behavior, and broad background structure can remain visible after grain is reduced. These checks do not certify all limbs or every possible halo.

The Basic-mode control was rendered and inspected offscreen. No application/DMG rebuild, Windows check or native Photoshop acceptance was performed.

Final regression on 7 November 2026: **532 repository tests passed**, including five new noise-reduction tests. The focused AEL regression also passed 27 tests. `git diff --check` passed.
