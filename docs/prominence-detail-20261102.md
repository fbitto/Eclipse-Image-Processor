# Prominence detail and mask correction — 2 November 2026

Current controls: Basic EV 0…+5, Advanced EV −3…+5, Advanced contrast 0.5…2.0 (default 1.0). See the implemented-controls section for compatibility and final validation; earlier comparisons below record the decision process.

The owner reported flat prominence highlights and a conspicuous mask boundary on the supplied margin--2px master, at prominence +3 EV and saturation 43%. After reviewing before/after crops and a full-canvas candidate, the owner approved option C: smooth highlights and a softer existing mask boundary, with thin-feature retention checked.

## Cause and correction

The previous display divided each over-range RGB pixel by its own peak, making every sufficiently bright pixel reach the same maximum. This retained colour ratios but discarded bright intensity differences. The replacement applies `RGB / (1 + peak RGB)` after the independent prominence exposure and saturation. It has a smooth shoulder, preserves saturation-adjusted channel ratios and has no hard brightness plateau in the tested range. EV still multiplies input exposure; display values are now nonlinear, so -1 EV does not mean half the final display number.

The Normal layer still uses original, unprepared RGB. Its red-excess selection and geometric bounds remain the same. The existing mask is blended inward over up to three native pixels, limited by local feature thickness so an isolated one-pixel feature retains opacity. The image itself is not blurred. Mask support cannot expand into the corona or missing data, and the mask remains independent of exposure/saturation. Selection runs natively before preview reduction; preview, standalone export, TIFF package and PSB share the same helper and mask bytes.

## Should prominences use another stretch?

They use their own exposure and curve, independently of the corona presentation. A further Asinh stage was tested on the same native prominence crop with identical +3 EV, 43% saturation and mask. The diagnostic used a hue-preserving shared peak transform, followed by the same bounded shoulder.

| Curve | Peak P10 | Peak median | Peak P90 | P90 − P10 |
| --- | ---: | ---: | ---: | ---: |
| Approved soft shoulder | 0.443 | 0.642 | 0.767 | 0.324 |
| Asinh strength 1 + shoulder | 0.453 | 0.605 | 0.684 | 0.231 |
| Asinh strength 5 + shoulder | 0.475 | 0.555 | 0.602 | 0.127 |

Asinh lifted faint values slightly but compressed the bright structure more. Keep the approved shoulder for this correction; do not add another stretch control without a demonstrated need. The percentile span describes display separation on this crop, not recovered resolution or astronomical SNR. The input is a processed HDR master; no missing or sensor-clipped signal is reconstructed.

## Checks

On the actual 5608×3744 source, with recorded geometry (3013,1688,273), the tested prominence's fraction at the 16-bit display maximum fell from **71.1% to zero**. The corrected mask was everywhere less than or equal to the old mask. All **226,939** missing pixels remained excluded and source SHA-256 stayed `39f1544b4e7485f05e91b08282b74f0cdb48fde8c0810be781b3b5192dbf7ac1`.

A native export with the original RGB, +3 EV and 43% saturation exercised TIFF/JPEG, the editable PSB, separate prominence image/mask and float32 source products. No corona enhancement filters were active in this export-path check; visual comparisons instead used the earlier native corona presentation. The comparison background therefore differs from the owner's current screenshot. PSB verification checked channel/mask integrity, and the standalone exported mask matched the numerical result exactly. This is not a new native Photoshop recomposition check.

Focused tests cover ordered bright values at high EV, inward-only alpha, thin one-pixel retention, opaque interiors, missing/negative input handling, mask independence, unit rescaling, preview reduction and exact PSB/TIFF-package pixels/masks. Earlier tests requiring completely opaque edge pixels were updated to require retained positive coverage under the deliberately softer boundary; brightness/EV tests now check monotonic exposure rather than obsolete linear output scaling.

Local review artifacts remain outside Git under `/tmp/eclipse-prominence-review/`: `stretch-comparison.png`, `stretch-measurements.json`, `native/before-after.png`, native measurements, exports and logs. No private image was committed.

## Follow-up: EV range and independent contrast control

Evaluated the same native prominence crop at 43% saturation with a fixed mask. The current −3…+3 EV range is safe, but its upper endpoint is restrictive after the new shoulder:

| EV | Peak median | Peak P90 | P90 − P10 |
| --- | ---: | ---: | ---: |
| −6 | 0.0035 | 0.0064 | 0.0048 |
| −3 | 0.0273 | 0.0488 | 0.0365 |
| 0 | 0.1831 | 0.2910 | 0.2005 |
| +2 | 0.4727 | 0.6214 | 0.3369 |
| +3 | 0.6420 | 0.7665 | 0.3235 |
| +4 | 0.7820 | 0.8678 | 0.2538 |
| +5 | 0.8776 | 0.9292 | 0.1684 |
| +6 | 0.9348 | 0.9633 | 0.0992 |

Recommendation: extend the slider to **−3…+5 EV**, retaining its 0.01 EV steps and existing saved/default values. This is a practical range for the tested image, not a universal photographic limit. +6 did not hard-clip numerically, but 29% of selected pixels exceeded 95% display brightness and contrast visibly compressed. Extending the negative side to −6 offered little practical benefit on this source.

A separate **Prominence contrast** control could be useful in Advanced mode. Unlike another Asinh stage, a generalized shared shoulder `y = x^c / (1 + x^c)` adjusts the slope around mid-brightness, while EV shifts the input exposure. Here `x` is the saturation-adjusted peak after exposure, and the same `y/x` factor scales all channels; zero maps to zero. `c=1` reproduces the approved curve exactly. This is a diagnostic proposal, not an implemented setting.

At matched median output 0.642, to separate curve shape from simple brightness changes:

| Contrast c | Matched EV | P90 − P10 | Change from current |
| --- | ---: | ---: | ---: |
| 1.00 | +3.00 | 0.3235 | — |
| 1.25 | +2.83 | 0.3989 | +23% |
| 1.50 | +2.72 | 0.4700 | +45% |

Initial proposed control: **0.5…1.5**, default **1.0**, step **0.05**. This supplies independent global tonal contrast, not sharpening or recovered spatial detail. Higher contrast can exaggerate texture/noise, so start at 1.0; 1.25 is worth trying on this crop. A future implementation must keep masks independent of EV/contrast and use the same curve for preview, TIFF and PSB, with omitted legacy settings defaulting to 1.0.

That evaluation did not change application code or defaults; the subsequently approved implementation is described below. It uses one supplied source and an earlier fixed corona presentation, not independent observational validation. Review artifacts are `/tmp/eclipse-prominence-range-review/exposure-range.png`, `contrast-matched.png` and `measurements.json`.


## Implemented controls

The owner approved an upper contrast limit of **2.0**, with Basic EV **0…+5** and Advanced EV **−3…+5**. The implementation uses 0.05 contrast steps, default **1.0**, and retains exact approved-curve pixels at contrast 1. New sessions start at **0 EV**; existing negative recipes and the old omitted-exposure fallback are preserved. Switching to Basic cannot silently clamp those values: a notice identifies the active negative exposure until the user explicitly replaces it. Higher contrast remains active when hidden in Basic mode, like other Advanced parameters.

The new contrast recipe field is optional; old recipes default to 1.0. Original RGB, reference estimation, mask and geometry are independent of contrast. Preview, main TIFF/JPEG, standalone prominence image, editable PSB and TIFF layer package use the shared numerical helper. Settings metadata records the curve and contrast.

Targeted checks passed **15 tests**, including contrast endpoints, unity exactness, a fixed-midpoint shape change (independent of exposure), unchanged masks, new EV bounds, mode-switch preservation and legacy JSON defaults. The GUI test exercises negative EV and contrast 2.0 through preview and export request; editable PSB tests exercise +5 EV/contrast 2.0.

A full-native export at **+5 EV and contrast 2.0** on the supplied master passed PSB channel/mask verification; the standalone mask was exact, mask bytes matched contrast 1.0, all 226,939 missing pixels remained excluded and source SHA-256 was unchanged. Basic, retained-negative and Advanced layout captures were visually checked under `/tmp/eclipse-prominence-range-review/ui-*.png`. These are offscreen UI checks, not Windows acceptance. Native exports and logs are in `native-controls/` under that directory.

Final complete regression suite: **425 tests passed in 183.381 seconds**. The refreshed macOS app passed strict/deep signature verification and its DMG checksum verified. The source hash and new upper-setting native export were checked separately. No Windows run or native Photoshop rendering at contrast 2.0 is claimed.

## Adjustable mask softness

Prominence edge softness is available in Basic and Advanced modes: 0–20 native pixels in 0.1-pixel steps, default 3. It controls the existing inward, thickness-limited feather rather than blurring RGB or expanding mask support. Zero bypasses feathering. Recipes without the new field retain the previous 3-pixel behavior. Preview, standalone masks and editable Photoshop exports share the setting.

Validation: 16 prominence tests, 13 settings tests and 33 GUI interaction tests pass. On the supplied native margin--2px master at geometry (3013,1688,273), widths 0, 3, 8 and 20 produced progressively nonincreasing alpha; all missing RGB pixels remained excluded. Integrated alpha sums were 3348.91, 2272.09, 1801.38 and 1763.14 pixel equivalents. Large values can reduce apparent prominence brightness; local thickness protection limits the effective width. No app rebuild or new visual acceptance comparison was performed.
