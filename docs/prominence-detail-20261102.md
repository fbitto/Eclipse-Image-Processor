# Prominence detail and mask correction — 2 November 2026

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
