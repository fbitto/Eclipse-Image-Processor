# Colour-control preparation and implementation checks — 7 November 2026

Current status: implemented and refined after feedback. All 522 tests pass without feature skips; see the implementation and follow-up results below.

## Historical preparation, before implementation approval

Scope at that stage: prepare and recheck **general warmth plus additive corona warmth**, with sky-only green suppression. Production code remains at commit `be7d840`. No feature implementation, commit, README edit, rebuilt app or DMG was made during this preparation.

## Actual checks

| Check | Result |
| --- | --- |
| Existing full suite, `unittest discover -s tests -v`, Qt offscreen | **480 passed**, 58.288 seconds. |
| Proposed suite, `unittest discover -s tests/proposed -p sky_colour_acceptance.py -v` | **3 fixture checks passed; 34 feature tests skipped**, 0.060 seconds. Skipped because `core.warmth.colour_layers` does not exist. |
| Test-quality probe | Three selected tests reject an injected no-op implementation with assertion failures: monotonic general warmth, sky-green suppression with zero warmth, and additive corona relationship. The injected mock was removed immediately; no source files changed. |
| Real FITS baseline | Existing corona warmth passed zero bypass, array immutability, finite/missing support and luminance checks; input SHA-256 unchanged. |
| Whitespace | `git diff --check` passed. |
| Working-tree scope | Only the proposal, this validation record and `tests/proposed/` are new. No tracked production changes or staged changes. |

The three fixture checks establish: a known green cast distinguishable from neutral grey; a sampled sky area and a real synthetic streamer beyond six reference radii; and existing corona warmth protecting sky without mutating input.

The 34 pending tests cover numerical relationships, mask independence/support, invalid inputs, cancellation, reduced/native sampling, UI defaults/order/levels, settings compatibility, request snapshots, direct-image reset, numerical-cache reuse, native-preview/package agreement, TIFF/JPEG and PSB verification, original prominence preservation and zero/off compatibility. See [the proposal](sky-colour-proposal.md) and [the executable acceptance tests](../tests/test_sky_colour.py).

## Real-image baseline details

Input: `/Volumes/Astro/Imágenes/CoronaHDR_RAW/CoronaHDR_Work/.coronahdr-jobs/e1c3c474c41b4163b9c04099bb909948/result/master.fits`.

- Native canvas: **5420 × 2908**; reduced preview: **1500 × 804**.
- Reference geometry: `(2975, 1660, 272)` native pixels, from the earlier automatic detection; not independent astrometry.
- Source SHA-256 before and after: `33ff81c882a0e5e98771b8c00f627af5860b56464798e16dc38e75122b45a005`.
- Current corona layer supported by the sampled sky fit: **yes**.
- At full existing corona warmth, approximately **30.45%** of valid preview pixels had mask coverage above 0.5; approximately **51.70%** had exactly zero coverage. These describe this baseline, not a quality target for the new controls.
- Maximum absolute luminance change using the current helper's `.30/.59/.11` weights: **0.00000762951**, below the 3/65535 tolerance.
- Probe uses uncalibrated source colour on the PSB presentation base, without numerical filter layers. It does not validate a final enhanced image, export, or the proposed feature.

Reproduce with [the read-only baseline checker](../tests/proposed/check_sky_colour_baseline.py), supplying a new JSON output path. The run's detailed output is `/tmp/eclipse-sky-real-baseline.json`; full test logs are `/tmp/eclipse-sky-full-regression.log` and `/tmp/eclipse-sky-revised-tests.log`.

## Limits and next acceptance step

**At the preparation stage, the new controls did not exist and had not passed feature tests.** Thirty-four skips are intentional preparation markers, not successful implementation validation. The proposed API, masks and green-suppression strength remain implementation decisions subject to the documented behaviour.

The preparation acceptance plan was: implement the shared treatment and all callers, move the feature tests into normal discovery, run them without skips, rerun existing regression tests, and compare real native-scale previews and exports. Review noisy/green skies, faint outer streamers, mask transitions, clipping and unchanged prominence colours. Include native GUI/platform checks and PSB editable recomposition. No release artifact should claim support before that work is accepted.

## Implementation results after approval

Implemented the general baseline, additive corona tint and sky-only green reduction
in source; moved all 37 scene/feature checks into `tests/test_sky_colour.py` and
removed the pending skip guards. Updated existing tests for the renamed Corona
warmth label and shared export helper. Production wiring includes UI, legacy
settings, presentation snapshots, TIFF/JPEG and editable PSB/TIFF packages.

| Check | Actual result |
| --- | --- |
| Final full suite | **517 tests passed**, 66.501 seconds, Qt offscreen; no skipped feature tests. |
| Feature suite | All **37** passed, including settings, native preview/package, PSB, TIFF/JPEG, prominence RGB/masks and exact old corona-only compatibility. |
| Real FITS comparison | Baseline, general 35%, general 35% plus corona 60%, and those plus green reduction passed bounds, finite/missing support, source immutability and luminance checks. |
| Real native TIFF export | **5420 × 2908 RGB16**, exactly matched recomposition through the shared native colour path; no enhancement filters or calibration in this isolation test. |
| Real native JPEG | Dimensions and embedded ICC profile verified. |
| FITS source integrity | SHA-256 remained `33ff81c882a0e5e98771b8c00f627af5860b56464798e16dc38e75122b45a005`. |
| GUI rendering | Inspected actual Qt-rendered Basic UI on the master, with default enhancement layers, general 35%, corona 40% and green reduction enabled; all three controls visible in order. |
| Whitespace | `git diff --check` passed. |

The real reduced colour comparison's maximum absolute luminance errors were
0 for bypass, 0.00000267030 for general warmth, 0.00000649728 for general plus
corona and 0.00000961318 with all stages, within the 6/65535 combined tolerance.
These are display-compositing checks, not photometric measurements.

Detailed native export results and files are in `/tmp/eclipse-colour-native-export/`;
the four-way comparison is `/tmp/eclipse-colour-comparison.png`; the UI capture
is `/tmp/eclipse-colour-controls-ui.png`. Full-suite log:
`/tmp/eclipse-colour-full-final.log`.

The existing app/DMG and release notes have not been rebuilt or changed. Native
Windows/macOS interaction and manual Photoshop recomposition of these new controls
remain unchecked; automated editable PSB verification passed on synthetic data.
No commit or publishing action was made for this implementation.

## Prominence, green strength and orange-tint follow-up

After the reported missing prominence views and weak/yellow colour treatment:

- Removed PSB-presentation gating from combined prominence preview.
- Explicit on-black/mask selection exits View Original comparison; the prominence
  selection algorithm and original RGB are unchanged.
- Added Green reduction (%) from 0 to 100, default 75, gated by the RGB/green
  checkbox. Saved settings, worker snapshots, native export and editable layer
  metadata carry this strength. Missing legacy fields restore 75%.
- Warmth now uses red/orange gains [1, 1−0.45a, 1−0.95a]. Tests check the resulting
  neutral-patch hue (20–40 degrees) after luminance restoration and exact zero bypass.
- Final full suite: **522 tests passed**, 78.801 seconds, Qt offscreen.

Using the user's exact reference geometry (3013,1688,299) on master.fits,
raw native selection contained 4,644 pixels at softness 0 and 4,639 at softness 3,
with maximum mask 65535. The full Fit GUI path with the new controls enabled
produced a mask maximum of 1.0 and 653 nonzero reduced pixels; the on-black RGB
maximum was approximately 0.9538. Inspected the rendered on-black view and its
controls. Capture: `/tmp/eclipse-user-geometry-prominences-ui.png`; full test log:
`/tmp/eclipse-orange-green-final-all.log`.

The user's reported fully empty mask with View Original off was not reproduced
in the fresh source process at those settings. The verified preview blockers
were fixed; restarting the source app is required to load changed modules.
The compiled app/DMG remains unchanged. These checks do not establish the state
of an already-running older app instance or native Windows UI behaviour.


Validation source confirmed by the user: `/Volumes/Astro/Imágenes/CoronaHDR_RAW/CoronaHDR_Work/.coronahdr-jobs/e1c3c474c41b4163b9c04099bb909948/result/master.fits`. The different master in job `596a8739cfd846ef97b19c8408a73420` is excluded from application design/validation decisions. The selection-balance fallback and its three tests added for that file were removed; the original prominence-selection algorithm is retained. Warmth, adjustable sky green reduction and independently tested preview-visibility fixes remain.

## Approved-master-only sunset refinement

The prominence selection fallback and its three tests were removed at the user's
request. `core/prominences.py` and `tests/test_prominences.py` are identical to
HEAD; no selection-algorithm change remains. The approved explicit e1c3c474 source
produces 4,639 selected native pixels at geometry (3013,1688,299), softness 3.

Warmth now uses full-strength gains [1,0.55,0.05], following the user's amber corona
and copper sunset-sky references. In a calibrated reduced presentation of the
approved master, with general and corona warmth both at 50% and green reduction
off, the fraction of valid pixels with newly introduced min(R,B)−G above 0.005
fell from 0.0368912 under [1,0.4,0.1] to 0.0000824554. This is an engineering
comparison of the tint, not a scientific colour reconstruction or a guarantee
that every existing coloured feature becomes neutral. No blanket magenta clamp
was added, preserving real sunset colour and spatial gradients.

Final regression: **522 tests passed**, 76.895 seconds, no skips. Log:
`/tmp/eclipse-amber-final-tests.log`. Whitespace checks passed. These source
changes are uncommitted; the existing compiled app and DMG remain unchanged.
