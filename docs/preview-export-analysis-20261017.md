# Analysis of preview versus prueba1.tiff

Analysis only; application code and source images were not changed.

## Files and recipe

The inspected export is `/Volumes/Astro/Imágenes/Eclipse_NEF/prueba1.tiff`,
2560 × 2560 RGB uint16. Its embedded metadata identifies
`Apilado_calibrado_lineal_32bit.xisf` as the source. The matching independent-layer
package is `prueba1_PS_layers_2`. Another same-named export in the calibrated-stack
subfolder uses different data/settings and was not used for this comparison.

Active sequential stages: WOW 32%, eight scales, bilateral=1, denoising thresholds
[0,0,0]; legacy RHEF 6%, Upsilon 0.60; ACHF 41%, gain 2, threshold 10%, background
retention 10%. Final presentation: GHS D=10, SP=0.247, b=2, BP=0, Reveal=100%.
Color neutralization is enabled for the export. FNRGF, MGN, USM and preprocessing
are disabled.

## Reproduction and matched-size comparison

Re-executing the full-resolution sequential pipeline and the recorded color
presentation reproduces the saved TIFF exactly: maximum and mean differences are
both **0 uint16 codes**. All three active stages run to completion. This does not
support missing stages as the cause of this particular export discrepancy.

The reconstructed preview uses a 1500 × 1500 area-reduced source and the inverse
of the recorded full-resolution parameter scaling. The exported RGB is projected
to the same Color-blend luminosity coefficients (0.30,0.59,0.11), then reduced to
1500 × 1500. This removes image-size and chromatic differences from the numerical
comparison. It reconstructs the preview from the saved recipe; it cannot establish
whether hidden controls were subsequently edited in the screenshot.

| Sequential result through stage | Mean absolute difference, equivalent 8-bit levels |
| --- | ---: |
| WOW | 0.54 |
| RHEF | 1.29 |
| ACHF | 3.54 |

Final normalized RMSE is 0.0173, equivalent to 4.42 levels out of 255. In the far
field beyond five reference disk radii, mean intensity is 0.1892 in the preview
and 0.1965 in the reduced export. Intensity standard deviation there is 0.0887
versus 0.0784. These are spatial intensity statistics, not calibrated noise or SNR.

## Causes identified in the implementation

1. **Processing a reduced image is not equivalent to reducing a processed image.**
   Area averaging changes faint structure, noise, extrema and statistical ranks
   before the nonlinear operations run.
2. **WOW's pixel scales are not compensated like Gaussian widths.** Both runs use
   eight dyadic scales, but one preview pixel represents 1.7067 native pixels.
   Thus identical scale counts do not describe the same physical spatial bands.
   Adding one integer scale would only approximate this ratio.
3. **RHEF ranks a different sample population at each resolution.** Its ring width
   scales from 1 preview pixel to 1.7067 native pixels, but the ranks and their
   populations cannot be identical after image reduction.
4. **ACHF amplifies the accumulated mismatch.** Its radius is scaled correctly
   (7 preview pixels to approximately 11.95 native pixels), but its adaptive
   neighbor acceptance and its threshold relative to input range depend on the
   preceding output. Its signed residual also changes the normalization limits.
5. **Global min/max normalization couples the display to negative extrema.**
   ACHF output ranges from -0.02137 to 0.29276 in the preview, versus -0.02359 to
   0.30947 at native resolution. Both are separately mapped to [0,1] before GHS.
   Therefore an identical GHS parameter set does not establish a shared physical
   black point or intensity mapping.

The source interior within 0.9 disk radii is exactly zero. In the final comparison
its mean display intensity is approximately 0.129 in the preview and 0.134 in the
export. The gray Moon is therefore a processing/presentation effect, not recovered
lunar detail. ACHF's negative extrema and the global normalization substantially
raise its displayed black level. WOW also processes the finite lunar zeros;
RHEF's application radius does not protect that region from the other stages.

The independent Photoshop stack follows a different composition model and should
not be confused with the sequential final TIFF.

## Recommended changes

- Provide a **native-resolution validation preview**, computed through exactly the
  export path and then reduced for display. Keep a fast preview, clearly identified
  as approximate. Both paths must use the same color/monochrome comparison basis.
- Define the display black point and scale explicitly, independently from each
  result's most negative and positive pixels. Preserve signed numerical outputs.
- Preserve the original lunar domain separately, with its validity and declared
  presentation, instead of interpreting normalized filter offsets as lunar signal.
  Do not enlarge the lunar mask to hide coronal artifacts.
- Standardize spatial units and quantify resolution dependence of wavelet scales,
  ranks and adaptive thresholds. This can reduce mismatch but cannot make all
  nonlinear operators commute with reduction.
- Judge the current grain at matched scale. Zero WOW denoising and substantial
  ACHF gain enhance weak fluctuations as well as structure; no claim of newly
  recovered coronal detail follows from stronger contrast alone.

The source and exported image were only read. Reproduction arrays and matched-size
comparisons were generated under `/tmp/preview-export-analysis`.
