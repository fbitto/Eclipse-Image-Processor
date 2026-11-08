# Source-relative Tangential contrast

**Standard/Expert → Tangential → Contrast: Source-relative (experimental)** selects the source-relative display mapping. The selector sits below Opacity. The default remains **Follow filter normalization**, preserving the existing Compatible/Revised choices. Basic mode still omits Tangential under its existing policy.

This is a local EIP display extension, not a new upstream AEL filter. It changes neither Tangential's signed angular-high-pass operator nor its missing-data alpha. It overrides the global Filter normalization setting for Tangential only; other filters are unaffected. It increases visibility and noise together, not the underlying SNR.

## Reference and encoding

Only allowed observed source samples contribute to the reference. The annular mean absolute source intensity is fitted as a continuous reference: interpolate populated one-target-pixel annuli (at least 12 samples each), then smooth their log values with a Gaussian of sigma 0.1 reference radius, at least one target pixel. At least eight populated annuli are required. The reference is a gain model, not filled or blurred source radiance.

Estimate empirical noise from horizontal adjacent observed differences outside eight reference radii: `1.4826*MAD(differences)/sqrt(2)`. With fewer than 64 such pairs, use all allowed adjacent pairs and record the fallback. Fewer than 64 pairs even after fallback raises an actionable error instead of inventing an estimate. This is not propagated detector uncertainty; correlated/directional noise, structures, quantization and broad coverage effects can bias the estimate.

```
scale = max(0.05*source_continuum, 3*noise_sigma)
z = gain*detail/(2.5*scale)
encoded = 0.5 + 0.5*z/hypot(1,z)
```

The curve is zero-centered, monotone at a fixed reference and bounded. It saturates more slowly than tanh. All source, detail and scale values use the same working linear intensity units. Zero gain returns neutral contrast. Positive unit rescaling of source and detail leaves the result unchanged. Source exclusions do not remove otherwise supported output targets; they cannot influence the estimated reference/noise.

The continuum uses an observed annular mean, so strong localized objects and incomplete angular coverage can change gain near their radius. The noise floor limits amplification but is empirical. Neither source-relative gain nor the curve proves that faint displayed structure is real. No new radial fade, lunar-geometry change or source RGB blur is introduced.

## Preview, settings and cache

Fast preview estimates its own continuum and empirical noise after resampling; it remains approximate. On the approved master, encoded preview versus reduced-native RMSE was 0.01610 of the 0–1 layer range. Noise sigma was 24.20 in preview and 37.68 natively. Check full-resolution preview before judging faint structure or exporting; these numbers are one dataset's measurements, not a universal error bound.

The optional v4 `combo_tangential_encoding` control collects `tangential_encoding=normalization` or `source_relative`. Missing controls reset to the original choice. Selection persists across UI modes. Changing encoding recalculates the Tangential layer; changing opacity reuses it. Once source-relative is selected, the global normalization choice does not invalidate this identical Tangential result. Receipts contain the local revision, formula, source fraction, noise multiple, measured sigma, population/fallback, profile support and smoothing scale.

## Qualification — 8 November 2026

- **546 repository tests passed**, including six new source-relative tests for reference-formula parity, units, masks, exclusions, immutability, constants/zero gain, support errors, cancellation/cache publication, UI/settings defaults and TIFF/PSB consistency.
- Ten synthetic cases included radial null, clean/noisy angular structure, three weak injections, correlated noise, a sky gradient, a bright point and a constant image.
- The implemented mapping matched the frozen research formula within two uint16 steps using the same allowed sample population. Weak injections at two, four and six radii had no negative/zero target responses; correlations were 0.99325, 0.99971 and 0.99986.
- The approved full-native master and preview preserved both existing encoded mappings pixel for pixel when those options were selected. Source-relative changed only display mapping: raw operator values and alpha were identical. Missing source pixels received no alpha.
- Actual native colour TIFF/JPEG/PSB export completed, with exact TIFF/verified-PSB merged pixel equality. Original prominence-layer hashes matched the prior validation. The saved v4 recipe restored the new selector.
- The Standard-mode control was rendered and visually inspected directly below Opacity.

All evidence is under `/Volumes/Astro/Imágenes/Eclipse-Filter-Quality-and-Default-Parameters-2026-11-08/10-Source-Relative-Tangential-Implementation-and-Validation/`. The implementation uses the approved e1c3c474 master; its source SHA-256 remained `33ff81c882a0e5e98771b8c00f627af5860b56464798e16dc38e75122b45a005`.

One master is not general scientific validation. No Windows run, native Photoshop recomposition, app/DMG rebuild or default change was performed. Review the full-native result before preferring this experimental mapping.
