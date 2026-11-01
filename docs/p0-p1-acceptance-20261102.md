# P0/P1 acceptance — 2 November 2026

Scope: current exports, current AEL-based numerical filters and optional support/log modes requested after b87d47f. Private source files and generated review artifacts remain outside Git under `/tmp/eclipse-p0p1-20261102/`. Windows acceptance is pending: the user confirmed no Windows environment is available. The two supplied products are the only available data; they are not established independent stacks.

## P0: native export and physical filesystem

A fresh 5608×3744 RGB16 TIFF and ten-layer PSB were exported from the supplied margin--2px float32 TIFF, using captured current application parameters and no reapplied sky fit. The original SHA-256 remained unchanged. The PSB is approximately 903 MiB.

Adobe Photoshop 2026 **27.11.0** opened the PSB with its embedded sRGB profile and 16-bit depth. Initial rendering and a forced recomposition (toggle/restore Edge Antialias) were saved as separate flattened TIFF copies. Both compared with the main TIFF:

| Measurement, uint16 channel levels | Initial | Recomputed |
| --- | ---: | ---: |
| Maximum absolute difference | 8 | 8 |
| Mean absolute difference | 1.195 | 1.195 |
| 99th percentile absolute difference | 4 | 4 |

This is native Photoshop evidence, not merely a cached-PSB comparison. Differences are small rendering/quantization differences; exact native equality is not claimed. Only owned test documents were opened/closed; no existing user document was modified.

On a separate 640×427 full-canvas reduction, Photoshop rendered the Color Correction group off and on. Off versus application TIFF: max 4, mean 0.630, p99 2 levels. On versus application TIFF: max 3294, mean 177.428, p99 2667. The latter is the intended Photoshop-only correction, not a matching application preview. Full-native Color Correction was not tested.

The float32 RGB source product matched every measured original pixel exactly; VALID matched all 226,939 missing pixels. Display TIFF/JPEG RGB profiles were checked. The scientific float product carries no display ICC profile.

A new test directory on the physically mounted **PC-MAC ExFAT USB volume** exercised PSB publication, reopening, repeated exports and cancellation. `result` and `result_2` each retained one coherent set of companion names. Cancellation before TIFF publication left no TIFF/JPEG; already completed PSB/source companions remained, as documented. Input hash remained unchanged. A second pair, `recipe` and `recipe_2`, verified all five product destinations including JSON, exact settings/decimal-geometry round-trip, and reopening a source on the Mac filesystem from the exFAT recipe. This verifies macOS writing to real exFAT, not Windows execution.

A real ExportThread and QApplication event loop also exercised close during calculation: cancellation completed without an error or published TIFF, about 0.16 seconds from worker start. This was an offscreen GUI check, not a manual desktop interaction benchmark.

An intermittent export regression exposed regenerated sRGB creation timestamps changing JPEG bytes between otherwise identical exports. The immutable profile is now cached per process. This changes no colour transform.

## Current upstream AEL

[Repository HEAD](https://github.com/PeterWar/Agentic-Eclipse-Library/commit/331196e225b758cb0ef90cbb93b4de7f1028d396) remains unchanged; current library is 1.4.1, last ael/ revision [17029c9](https://github.com/PeterWar/Agentic-Eclipse-Library/commit/17029c9284748c087adcd0d40241f7e3faf8d778). A separate technical audit compared live current-runtime outputs on even and odd/off-center masked scenes.

- NRGF, ACHF ISO 01, ISO 04, angular 4 and guided WOW: bit-exact encoded values and support with matched explicit parameters.
- Continuous global RHEF: the independent float64 implementation differed slightly from upstream float32 arithmetic. The application now selects current AEL reference precision, including its quantile inversion and accumulation order. Two frozen synthetic upstream fixtures verify exact rank output and actual worker dispatch. Fresh full-native comparisons against the live current runtime also matched exactly on both supplied masters (2-pixel rings, 257 quantiles, no Upsilon), taking 28.38 and 25.60 seconds for each upstream/application pair. Numerical API float64 defaults, custom quantiles, statistical targets and cancellation remain available.
- Provenance receipts now name current 1.4.1/17029c9. Experimental support separation remains an explicitly optional application extension, off by default.

Operator parity does not mean identical recipes. Application RHEF uses 1-native-pixel rings and Overlay by default; upstream bank uses 2-pixel rings and Multiply, and offers local angular rank variants outside the application's global mode. Application layer selection, opacities, custom support/confidence and approximate preview scaling remain application choices. No unrequested extra AEL filters were added.

## P1: native image comparisons

Native comparisons cover both supplied margin--2px TIFF and job 596a8739 master.fits: ISO 01/04, angular ACHF and guided WOW, compatibility versus optional support separation; linear/log Larson–Sekanina with nearby-angle delta 0 and 0.1 degrees. A deliberately excluded statistics-only sector (|angle| < 0.2 radians, 1.2–4 reference radii) tests restored target coverage without adopting a new mask in the user's recipe. Full-canvas views and native limb/outer/corner crops are retained, using the same 0–1 layer display. Diagnostic WOW used six scales (the native default export uses eight); ACHF used native preset scales. Larson used 3-degree rotations and 25% gain. These are matched diagnostic settings, not replacement finishing presets.

Geometry was held at the recorded (3013,1688,273) for comparison; this is not a new lunar fit. The FITS missing region extends farther than this reference disk. Missing support remains authoritative and is never filled.

Synthetic tests additionally cover same-mask AEL parity, finite zero/negative operator restrictions, faint-detail injection response and independent-noise nulls, plus log Larson–Sekanina invariance and interpolation controls. Independent-noise synthetic controls do not replace independent observational stacks.

The optional mode restored all **217,008** positive observed targets in the diagnostic sector for all four AEL layers on both products. Compatibility mode intentionally emitted no layer output there. On common support, encoded RMSE (fractions of the 0–1 layer range) was:

| Layer | Margin TIFF | Job FITS |
| --- | ---: | ---: |
| ISO 01 | 0.003587 | 0.003549 |
| ISO 04 | 0.002447 | 0.002437 |
| Angular 4 | 0.004480 | 0.004487 |
| Guided WOW | 0.005175 | 0.005118 |

All 226,939 TIFF and 273,060 FITS missing samples retained zero alpha. Both input hashes remained unchanged. Neither mono source contained nonpositive finite samples, so signed/zero domain claims rely on synthetic controls. Local kernels in optional mode may use observed statistical exclusions; only the designated fit/display statistics exclude them. This is an explicit policy change, not a claim that bright excluded stars cannot affect nearby residuals.

At 25% gain, median absolute encoded Larson detail was about 0.00536–0.00538 in log mode, versus 0.0000076–0.000038 in linear mode. Nearby-angle averaging reduced log median amplitude to about 0.00489; this does not separate noise reduction from signal attenuation. Linear mode is nearly neutral on these HDR settings. No optional mode is promoted based solely on greater contrast or recovered coverage.

Full-canvas and native crops were visually inspected. Optional mode removes the deliberate statistics-sector hole. Native layers still strongly enhance sky grain; angular ACHF shows directional texture, and compact stellar halos remain visible in full-frame displays. These observations agree with upstream limitations and do not justify cosmetic masking, new blur, or a claim of artifact-free detail. Compatibility defaults remain unchanged.

Review artifacts: `p1/ael-comparison.jpg`, `p1/native-crops.jpg`, `native-review.jpg`, `p1/measurements.json` and the per-case crops under the local artifact directory. Native Photoshop renders and source-integrity reports are there too.

## Automated evidence

Current bundled AEL self-test: **124/124 passed, zero skipped**. Application baseline before the RHEF change: 392 tests passed. RHEF/current-port focused checks: 47 tests plus 23 support/scaling regressions passed. Optional-support synthetic checks: 4 passed; Larson checks: 13 passed. The first updated full run exposed the ICC timestamp failure; the log is retained, and the corrected full run is recorded below.

Corrected final full suite: **394 tests passed in 174.660 seconds** (`verified-suite.log`). The profile check also passed independently. No failures were suppressed or acceptance thresholds loosened.
