# Revised filter normalization — 8 November 2026

The **Filter normalization** selector in Filter Statistics & Normalization, above Radial Enhancement, offers **Compatible** (the default) and **Revised (experimental)**. It is visible in Standard and Expert; Basic hides the control while retaining the selected value. Compatible retains current output and existing recipes. Revised applies the local corrections below to ACHF, Tangential and continuous FNRGF. Other filters, including both NAFE modes and WOW, are unchanged. Reference-compatible FNRGF remains the original path.

This is an EIP extension, not an upstream AEL algorithm update. The original AEL attribution and license remain in place. The selector is saved in v4 settings; missing selectors reset to Compatible. Switching modes invalidates only affected numerical layer caches; opacity still reuses calculated layers. Export receipts identify the local revision and mapping units.

## Signed detail without fitted display levels

The original ring encoder fits a median and MAD to each filtered layer. Re-estimating these statistics can reverse the displayed response to an injected structure even when its raw response has the correct sign. Revised encoding uses zero as its center and a fixed scale in stated units:

```
encoded = 0.5 + 0.5*tanh(gain*detail/(2.5*scale))
```

AEL ACHF scale is 0.05 in natural-log intensity-contrast units. Tangential and adaptive ACHF use 1% of the preserved native source normalization range in working linear intensity units. Direct numerical callers without that reference use the observed input range, recorded explicitly; they must supply a consistently rescaled reference when changing intensity units. Adaptive/Tangential gain is applied inside the bounded curve to avoid the previous post-encoding hard clipping.

These scales are presentation gains, not measured uncertainty or denoising thresholds. The linear reference range can be driven by extreme input pixels; this is a further reason to inspect contrast rather than assume an automatic improvement. The revised display does not equalize every radius to the same contrast. Consequently, especially for linear Tangential/adaptive detail, outer structures may look weaker at the same opacity. The result is not an appearance-matched denoising comparison. Compare full native output and choose the look before adopting revised normalization as a default. Quantization/saturation can still lose responses outside the tested dynamic range.

## ACHF radial fitting

Revised isotropic fitting pairs median log intensity with median log radius, instead of the compatibility path's mean log radius. The spline is evaluated to the observed extent of its first/last populated annuli; it no longer becomes artificially flat at their representative radii. Cubic fitting and missing/statistical support remain explicit. No lunar geometry, missing radiance, original RGB or prominence pixels are changed. Partial-coverage bias can remain; these changes do not certify every boundary.

The original helper behavior remains the numerical API default. In particular, the NAFE experimental reference model continues to use its original profile path.

## Continuous FNRGF

Three coupled model corrections address measured radial discretization bias:

- Estimate a sector's center value by a quadratic radial fit when at least six observed samples span a quarter of the bin and the fit is full rank; otherwise retain the measured mean. An average over a steep, partially observed bin is not its center value. Measured widths and population requirements remain intact.
- Preserve radial curvature with Gaussian-weighted quartic smoothing in revised mode. Compatibility and NRGF retain quadratic smoothing.
- Interpolate continuous model coefficients cubically within each contiguous populated run, including bounded endpoint evaluation within that run's application edges. Gaps are not bridged, and no missing observations are filled.

The dimensionless normalized residual uses a fixed zero-centered display scale of 1 rather than fitting a new MAD to tiny residual/model errors. The Multiply layer, its opacity, application limits and existing fades remain explicit; constant output retains neutral bypass. Reference-compatible FNRGF remains available with its original behavior.

## Validation

The final repository suite passed **540 tests**, including eight new tests covering signed mapping, injected responses across seeds/variants, radial endpoints, unit scaling, thread parity, cache separation/reuse, cancellation, invalid references, old settings, GUI levels and PSB receipts. Existing frozen AEL fixtures passed unchanged.

On the approved e1c3c474 master, 16 affected-mode preview/native comparisons reproduced the retained Compatible image and alpha bytes exactly. Revised mode retained identical alpha/support and assigned no alpha to missing source pixels. Affected modes were tested with 80 expanded synthetic cases (radial nulls, offset/centered limbs, coverage edges, noise, independent/correlated realizations, gradients, constants and point features), plus eight weaker-injection cases. Seven revised paths passed the frozen screening criteria; the eighth, reference-compatible FNRGF, intentionally retains the known original response.

Representative worst-sector radial-null scores, before → revised:

| Mode | Original | Revised |
| --- | ---: | ---: |
| Continuous FNRGF, STD | 0.11384 | 0.00085 |
| Continuous FNRGF, MAD | 0.11374 | 0.00067 |
| Tangential | 0.03860 | 0.00145 |
| Adaptive ACHF | 0.03176 | 0.00333 |
| ACHF ISO 01 | 0.07174 | 0.000033 |
| ACHF ISO 04 | 0.06958 | 0.000031 |
| Angular ACHF | 0.01899 | 0.000021 |

These are declared synthetic screening metrics, not an absolute guarantee against every ring or an astronomical SNR measurement. No negative or zero responses were measured on the selected strong and weaker injection targets in the seven revised paths. Correlations in the main injection control ranged from approximately 0.977 to 1.000. Raw FNRGF band reduction was checked separately from encoding; the first interpolation-only prototype failed a broader raw-null check, and cell-centering/curvature corrections were added without weakening that test.

Both policies completed actual full-native colour TIFF/JPEG/PSB exports with the affected filters, general/corona warmth, green reduction and source prominences enabled. The TIFF pixels matched each verified PSB merged composite exactly. Source FITS/RGB checksums and original prominence-layer hashes were unchanged. Settings round-tripped for both policies. The deliberately combined export exercises integration; it is not a recommended starter preset. Basic-mode selector layout was inspected offscreen.

All new evidence is under `/Volumes/Astro/Imágenes/Eclipse-Filter-Quality-and-Default-Parameters-2026-11-08/08-Normalization-Fixes-and-Extensive-Validation/`. Earlier failed research trials and the original study are retained. Only this approved real master was available; independent real-data truth, Windows, native Photoshop recomposition, and an app/DMG rebuild remain unperformed. The default remains Compatible pending review of the changed look.
