# Validation and evidence boundaries

Updated 1 November 2026. Test counts describe a particular checkout, not a permanent feature guarantee.

## Automated checks

From the project root with runtime dependencies installed:

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest discover -s tests -v
```

On Windows set the environment variable using PowerShell syntax, or run with a desktop session. The complete suite passed **360 tests** in 94.537 seconds on the local macOS development environment during the P1 layer-values/support update.

Coverage includes numerical independent references and AEL fixtures, missing/statistical support, native/preview scaling, independent layer inputs/order/blends, bounded caches, cancellation, colour preparation, export separation, PSB structure/bytes, optional Color Correction, JSON v4 validation, GUI interaction/responsiveness, zoom and overlay painting. It does not establish astrophysical truth or pixel identity after native Photoshop recomposition.

## Real-image validation tool

Inspect the current options before running:

```bash
.venv/bin/python scripts/validate_real_image.py --help
```

For example, with a source file and an output directory that does not yet exist:

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/python scripts/validate_real_image.py /path/to/master.fits /path/to/new-validation-directory
```

The tool loads supported image input, exercises filters/combined output and writes validation artifacts to the requested output location. Use a separate output directory, keep source files unchanged and retain the generated measurements alongside exact settings and environment versions. Large native runs can take significant memory and time.

The most recent full real-data cleanup check used a 5608 × 3744 RGB float32 FITS with 273,060 missing pixels. Native and reduced tests exercised eight filter families and combined output; the source-file hash remained unchanged. The GUI-produced RGB16 TIFF matched the expected un-stretched composition pixel for pixel. The native JPEG differed from its expected floating presentation by mean absolute error 1.9881 levels on an 8-bit scale, consistent with lossy storage. Layer export was disabled in that check: it supplies no current native PSB/Photoshop evidence.

After the latest UI changes, 56 focused tests passed for interactions, image painting and responsiveness. Offscreen synthetic captures of Disk overlay on/off confirmed the circle and cross toggle together, without numerical recomputation, and reset visible when loading an image. These captures do not substitute for testing every native desktop/display configuration.

## Historical and unperformed checks

Earlier native Photoshop 2026 tests are preserved in [PSB validation history](psb-validation-history.md) and the [colour-correction report](propuesta-color-atardecer-psb.md). Their measured layer/pixel results belong to those older exports. Current automatic exposure/hidden-reference output has structural automated coverage but has not been opened and recomposed in Photoshop for this revision.

The [19 October filter report](filter-validation-20261019.md) and [21 October performance report](performance-optimization-20261021.md) retain historical datasets/timings. They are not benchmarks of the current full pipeline. No new performance benchmark, Windows/macOS package build, signing/notarization, external scientific-link check or native Photoshop run was performed for the documentation update.

## P1 layer values and real-image checks, 1 November 2026

Regressions cover operator NaNs and missing alpha, fade/confidence changing alpha only, RHEF ranks surviving encoding, post-encoding detail gain, zero-MAD thresholded detail, continuous radial-model targets excluded from statistics, retired-control recipe loading, RGBA layer-package values/alpha, and smoothing on a structure-free power-law corona. With radial smoothing 0 and 8 px, the synthetic 1.0–1.1 R median remains about −0.037; this measures the absence of the former smoothing bias, not exact reconstruction of a radial profile.

The supplied `nikon-lunar-margin-negative-trials/margin--2px/master.tiff` was checked read-only at 5608×3744 and preview 1500×1001 for NRGF, FNRGF, RHEF, MGN, WOW, tangential, Larson–Sekanina and all four ACHF variants. Geometry/filter settings came from its companion JSON; no saved sky correction was reapplied. Source SHA-256 remained `39f1544b4e7485f05e91b08282b74f0cdb48fde8c0810be781b3b5192dbf7ac1`. All 226,939 missing pixels retained zero layer alpha. There were no exact zeros; 40 RGB pixels contained a negative channel, while the derived mono intensity remained positive (403.1264–2,632,430.75), so this image does not test nonpositive mono operator support.

Encoded preview/native RMSE on common near-opaque support was 2.36% NRGF, 7.84% FNRGF, 2.72% RHEF, 8.49% MGN, 6.98% WOW, 9.27% tangential, 21.60% adaptive ACHF, 3.75% ISO 01, 4.73% ISO 04 and 3.54% angular ACHF. These are fractions of the 0–1 layer range, not scientific acceptance thresholds. Larson–Sekanina's 0.01% accompanies a nearly neutral layer and does not establish useful HDR contrast. Native verification remains necessary, especially for adaptive ACHF. WOW/ISO 04 show strong grain at the saved settings. No full-size Photoshop recomposition/export or astrophysical ground-truth validation was performed for this case.

Item 33 is addressed for continuous FNRGF/RHEF statistical models only; local operators, NRGF and compatible modes retain coupled sampling/output support. See [layer conventions](layer-composition.md#layer-values-and-support-issue-3-p1).
