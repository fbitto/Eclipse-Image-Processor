# Streamer-aware warmth — 2 November 2026

Warmth follows the enhanced corona, rather than the amount of coronal RGB signal left above the original linear sky level. Calibration and numerical filters remain independent of warmth. Warm 0 preserves the calibrated, whiter presentation exactly.

## Coverage and colour

`core/warmth.py` samples the enhanced luminance at the existing Background Gradient sky points, or a generated grid outside the exclusion radius. At least six usable patches spread across both image axes are required. A robust fitted sky plane accounts for a smooth gradient; patch residuals estimate the sky noise. Missing pixels are excluded from smoothing and sampling.

Coverage rises smoothly from 2.5 to 6 noise sigmas above this plane. A colour closer to neutral white than the sampled blue sky supports detection at lower contrast, down to a 1.5–3 sigma transition. This uses channel spread relative to summed RGB, compared with the sky's channel spread. The colour cue is disabled for an already neutral sky. Whiteness is supporting evidence, not a condition that would cut off blue-contaminated outer streamers. Gaussian feathering softens the mask, and no outer-radius cutoff is applied. The exclusion radius selects sky samples only.

The tint acts on **enhanced luminance excess above the fitted sky**, retaining the existing sky contribution to each RGB pixel. Gamut handling preserves displayed luminance within 16-bit quantization. This avoids replacing faint, sky-dominated pixels with a flat gold colour. The slider scales strength independently of the mask's detection thresholds.

Very faint structures indistinguishable from background noise can remain partly untinted. Curved sky gradients or contaminated samples may still need correction or sample editing. This is an artistic segmentation heuristic, not a scientific identification of coronal emission.

## Preview and editable exports

Fast and native previews map the same native sky settings onto their respective enhanced images. Their masks can differ because fast filtering and resampling are approximate. Exposure is computed from the un-warmed calibrated RGB, so changing Warm does not shift automatic exposure. Slider edits reuse the calibrated RGB cache.

TIFF/JPEG composition and layer packages use the same RGB16 tint and alpha16 mask. PSB and TIFF layer packages include **Warmth - enhanced corona**, a Normal layer with a separate editable mask, above RGB Color and below Edge Antialias and original prominences. TIFF packages store `WARMTH_MASK.tif`. Original prominence pixels and controls, the hidden linear reference and working float sources are unchanged by Warm.

## Checks

Synthetic checks cover long low-signal streamers beyond six disk radii, blue sky gradients and noise, the additional neutral-colour cue, calibrated white input, soft transitions, missing/outlier sky patches, insufficient/rank-deficient samples, preview-coordinate mapping and zero-strength bypass. Integration checks compare preview, TIFF, JPEG and PSB composites, verify the editable mask and preserve original prominence layers.

The real-image probe uses the supplied 5608 × 3744 RGB float32 TIFF with its saved gradient correction, calibration, FNRGF, MGN and AEL ACHF controls. Native and fast filter caches are calculated independently, then reused at Warm 0, 50 and 100. Local, ignored outputs and the probe are in `artifacts/warmth-streamers/`; final accepted comparison outputs are in its `final/` directory. Native Photoshop recomposition is outside this check; the PSB's stored composite and mask bytes are verified.

Final regression result: **448 tests passed in 146.94 seconds**, recorded in `artifacts/warmth-streamers/unittest-final.log`. `git diff --check` passed. At all three warmth settings, the full-resolution RGB16 TIFF matched the quantized native preview exactly and the PSB stored composite matched the TIFF exactly. Warm 50 and 100 PSBs contained editable Warmth masks; Warm 0 had no extra layer. JPEG mean absolute differences were 1.71, 1.73 and 1.75 levels on an 8-bit scale. The real TIFF and saved recipe were not modified.

Visual checks rejected an initial whole-pixel tint because it produced a hard gold fringe. The accepted blend retains the sky contribution and tints only enhanced signal above it. The running application was checked with the saved calibrated source at Warm 0 and 100; the generated native/fast comparisons additionally cover Warm 50. The background remained blue, the calibrated baseline remained white at zero warmth, and colour faded gradually along the enhanced rays.

## Inner-limb white-ring correction

The original mask required Gaussian support greater than 0.999, inadvertently excluding a band of observed corona beside the missing lunar disk. That band retained its white calibrated colour while the surrounding corona warmed. Both luminance smoothing and mask feathering now normalize over available observed pixels; touching the missing disk does not disqualify a valid coronal pixel. Missing pixels still have zero mask coverage and remain missing.

On the supplied TIFF, mean mask coverage in the first eight observed pixels outside the measured lunar radius rose from 10.34% to 100%. The local comparison `artifacts/warmth-streamers/inner-ring-comparison.png` shows the white annulus removed. All 13 focused warmth and presented-export tests passed, including a regression requiring full warmth up to an observed inner limb. This follow-up did not repeat the entire 448-test baseline run recorded above.
