# NAFE limb-band investigation — 7 November 2026

The bright limb band is reproducible on the approved master. It is present in NAFE's numerical output before colour treatment or Photoshop blending, remains in a full native calculation, and is exaggerated by the current reduced-preview kernel scaling. The baseline measurements below preceded the production preview-scaling correction and optional experimental implementation described at the end.

## Input, identity and baseline

The supplied `artifacts/master.fits` symlink was resolved and verified against the approved file:

```text
/Volumes/Astro/Imágenes/CoronaHDR_RAW/CoronaHDR_Work/.coronahdr-jobs/e1c3c474c41b4163b9c04099bb909948/result/master.fits
```

- SHA-256 before and after processing: `33ff81c882a0e5e98771b8c00f627af5860b56464798e16dc38e75122b45a005`.
- Native canvas: 5420 × 2908; standard preview: 1500 × 804.
- User confirmed automatic geometry. The actual app detector returned **(2975, 1660, 272)**, fitted to the missing-data boundary. This is protection geometry, not independent physical lunar astrometry.
- Baseline NAFE: window 129 native pixels, automatic residual-noise gate, multiplier 12, region outside 4 reference radii, residual smoothing 4 native pixels, lunar statistical exclusion enabled, guard 0, bright-statistics exclusion off.
- Preview scale approximately 0.2767; effective preview support window 37 pixels.
- All filters except NAFE were omitted in the causal comparisons. The images use a fixed monochrome PSB presentation based on the native source, EV 0. They isolate the defect rather than exactly reproduce the screenshot's unspecified other filters, colour calibration and exposure.
- No colour warmth, green reduction or prominence manipulation enters the NAFE operator. Original arrays, validity, geometry and manually edited settings were not changed.

An initial comparison used the previously mentioned manual geometry (3013,1688,299). Once the user confirmed automatic geometry, the complete experiment was rerun. Those manual-geometry results are retained separately as a counterfactual and are **not the screenshot baseline**.

## Where the band first appears

NAFE computes a neighbourhood-weighted fuzzy cumulative distribution:

```text
E(p) = sum_q weight(p-q) * Phi((I(p)-I(q))/sigma) / sum_q weight(p-q)
```

Only allowed, observed neighbours enter the sums. E=0.5 is neutral in Overlay; E above 0.5 brightens it.

At the observed lunar boundary the kernel cannot see observations on its inner side. The inner corona also has a steep intensity gradient, so the remaining neighbours are predominantly dimmer than the target. This pushes E toward one in a coherent band around the missing disk. The output therefore contains a brightness structure that is not simply an extracted coronal detail layer.

The full-native run confirms this effect at the original pixel scale:

| Distance from observed missing-data edge, native pixels | Full-native median E | Current fast-preview median E |
| --- | ---: | ---: |
| 0–5 | 0.83106 | 0.92296 |
| 5–15 | 0.84895 | 0.86971 |
| 15–30 | 0.68210 | 0.71550 |
| 30–60 | 0.56429 | 0.58757 |
| 60–120 | 0.51619 | approximately 0.520 |
| 120–180 | 0.50454 | approximately 0.512 |

Bands are measured by distance transform from the actual observed/missing mask, restricted to the limb neighbourhood. They are not a fit to a desired ring profile. CSV output retains counts and 10th/90th percentiles; the report retains sector results so a median cannot hide local problems.

Overlay at 100% makes the band much more conspicuous. In the native crop, the median display change at 5–15 pixels was approximately **+0.161** on a 0–1 scale, versus **+0.039** at 30–60 pixels. Reducing opacity scales that display contribution; it does not correct the operator's boundary response.

## Controlled experiments

### Missing-boundary/gradient control

A labelled synthetic monotone radial scene has no input ring. With its inner observations masked, median E in the first 0–5 pixels was **0.82030**. With a finite, bounded analytical central continuation, it was **0.54690**. The 5–15-pixel band changed from 0.59947 to 0.53373; away from the boundary the outputs coincide.

The continuation is a synthetic known-truth control only. No lunar pixels were filled, mirrored, inferred or added to the real image. A separate flat scene with a missing disk returned **exactly E=0.5**, showing that a mask without an intensity gradient does not itself generate the bright band.

These controls establish a boundary/gradient mechanism. They do not prove that every structure in the original HDR is astronomical or that its calibration is artifact-free.

### Reference-circle statistics

Using all finite observed samples, with the **same frozen sigma**, lowered native-crop E from 0.84894 to **0.81247** at 5–15 pixels. The band remains. With automatic geometry, both versions support every observed target in the measured limb region: this is **not a recurrence of the earlier hard output-alpha cutoff**.

The oversized/manual-circle counterfactual is much worse: native E around the limb rose to about 0.97–1 in several sectors and 3,815 observed near-limb targets lacked adequate kernel support. This demonstrates why a reference circle that excludes actual corona can aggravate NAFE, but it does not explain the current automatic-geometry screenshot by itself. Do not change lunar geometry merely to improve a filter's appearance.

### Noise gate

Tripling the automatic sigma, while keeping input, support and window fixed, changed preview E at 5–15 pixels from **0.86971 to about 0.8693**. It barely changes the band. The local brightness structure dominates this gate; increasing the noise multiplier is not a demonstrated repair.

### Window size

Using window 65 lowered preview E at 5–15 pixels to **0.79369** and at 30–60 pixels to 0.51690. It narrows the affected neighbourhood and changes texture elsewhere. It is an appearance/scale tradeoff, not evidence of a ring-free boundary correction.

### Preview spatial scaling

The current code scales only the window half-width for preview. The twelve internal Gaussian sigmas remain 1.414–64 **target** pixels instead of scaling with the native pixel footprint. Thus the 37-pixel preview window uses a different relative weighting than the native 129-pixel window.

A diagnostic-only kernel with all twelve sigmas multiplied by the preview scale was compared against the actual full-native E field, conservatively reduced using the existing observed-data resampler. Over the same 8,529 valid pixels within 60 native pixels of the limb:

| Preview variant | Mean absolute E error versus reduced native E | Median E bias |
| --- | ---: | ---: |
| Current preview | 0.035986 | +0.035040 |
| Scaled internal-kernel candidate | 0.006681 | +0.004231 |
| All-observed samples, current kernel | 0.026009 | +0.020969 |

Scaling the internal kernel reduced this measured error by **81.4%**. This is a demonstrated cause of **extra preview amplification**. It does not remove the native boundary response. The candidate is still approximate: local equalization and downsampling do not commute, and the finest scaled Gaussian is below one preview pixel.

## Numerical and native checks

- **48 independent direct fuzzy-CDF witnesses**, covering twelve angles and four limb distances, agreed with the native operator to maximum absolute E error **0.00050346**. This is far smaller than the observed limb enhancement. The witness threshold was fixed at 0.01 before comparison.
- Full native computation: **5420 × 2908**, **82.96 seconds** for NAFE on this machine, including its automatic gate, excluding subsequent file rendering. No unsupported observed targets in the measured limb region.
- Full-native versus isolated native-crop maximum E difference within their common interior: **0.00236666**, consistent with different intensity-grid origins/interpolation. Native crop edges were outside the measured interior by more than the 64-pixel kernel radius.
- Full-native corner median E values: approximately 0.50107, 0.49975, 0.49995 and 0.49814. Full canvases and corners were retained for inspection.
- Automatic sigma: preview **247.7763**, native **569.5789**, in the source mono input units. Noise resampling changes the estimate, but the fixed-sigma experiments isolate the other effects.
- Existing application NAFE tests: **17 passed**.
- Bundled AEL 1.4.2 self-tests through the plugin launcher: **137 passed, 0 skipped**. These are implementation tests, not scientific certification of this eclipse.
- Source hash unchanged. At this initial measurement stage, no production NAFE, layer-engine or pipeline changes had been made. See the implemented comparison below for subsequent changes.

The numerical witnesses support the stated fuzzy-CDF calculation at the checked points; this is not a proof that no other numerical defects exist anywhere in the implementation.

## Comparisons and reproducibility

Local artifacts are in `build/diagnostics/nafe-limb-auto-20261107/` (ignored by Git):

- `opacity-comparison.png`: no NAFE, 40%, 100%, full fields and identical limb crops.
- `preview-candidate-native-comparison.png`: current preview, scaled-kernel candidate, full native; fixed 100% opacity. Full canvases above, diagnostic crops below.
- `limb-controls.png`: support, sigma and window controls.
- `profiles.svg` and `band-profiles.csv`: dimensionless E profiles, observed/supported counts and spread.
- `report.json`, `full-native-report.json`, `preview-native-comparison.json`: numerical receipts and input identity.
- `full-native.npz`, full-native PNGs and per-control NPZs: producer pixels and support, not screenshots of a final colour edit.

The earlier manual-geometry counterfactual is retained in `build/diagnostics/nafe-limb-20261107/`.

The case-specific scripts refuse a source whose hash differs from the approved master:

```sh
.venv/bin/python scripts/research/diagnose_nafe_limb.py \
  '/Volumes/Astro/Imágenes/CoronaHDR_RAW/CoronaHDR_Work/.coronahdr-jobs/e1c3c474c41b4163b9c04099bb909948/result/master.fits' \
  build/diagnostics/NEW_NAFE_CASE

.venv/bin/python scripts/research/diagnose_nafe_native.py \
  '/Volumes/Astro/Imágenes/CoronaHDR_RAW/CoronaHDR_Work/.coronahdr-jobs/e1c3c474c41b4163b9c04099bb909948/result/master.fits' \
  build/diagnostics/NEW_NAFE_CASE
```

The first refuses an existing output directory; the follow-up refuses an existing full-native output. The full-native run requires substantial memory. The scripts test the current code and freeze the experimental sigma within each resolution; they do not modify app settings or use the rejected master.

## Recommended next step and limits

**Correct preview kernel scaling first**, after reviewing the supplied full-canvas comparison. That addresses the demonstrated preview exaggeration while retaining the native operator. It should be tested for constant/boundary nulls, scaled support and cache identity before adopting it. No such production change is included here.

**Treat the native bright limb as an unresolved operator limitation.** Eliminating it would require a separately validated change to what NAFE measures near a missing boundary, or a different enhancement operator. Do not present lower opacity, a smaller window, an arbitrary radial fade, a cosmetic blur, a layer over the old band, filled lunar samples or altered geometry as a causal repair. Lower opacity remains a useful display choice with an explicit tradeoff.

Only an already stacked HDR was supplied. Without independent exposures and calibration/coverage products, this investigation cannot independently qualify fine coronal detail or rule out additional upstream artifacts. Native Photoshop and Windows presentation were not manually checked. The original source, existing colour work, default AEL method, compiled package and user edits remain unchanged; subsequent optional implementation work is described below.


## Implemented comparison

Both implementations now scale internal Gaussian widths with the preview window. Native AEL original remains unchanged and is the default. The optional limb-aware mode uses the measured radial-reference response and smooth unit-slope encoding, without source filling or geometry changes. Full-native medians: original/experimental 0–5 px 0.831/0.364; 5–15 px 0.849/0.498; 15–30 px 0.682/0.500; 30–60 px 0.564/0.500. The dark innermost response is a remaining limitation; the optional mode must not be described as universally artifact-free. Full-native reference evaluation took 42.39 seconds in this run, in addition to the original pass. Comparison arrays and images are under `build/diagnostics/nafe-limb-reference-soft-20261107/` (local ignored artifacts).
