# Issue #3 response draft

Draft only — not posted. Commit identifiers below are local until published. Prepared 2 November 2026; Windows results and P2 native-cost qualification remain pending. This is an item-by-item response to the original 35d555f review, not a claim that every concern is independently accepted.

---

Thank you for the detailed review. I have worked through the 50 items, separating numerical fixes from deliberate presentation choices and outstanding validation. AEL-based operators are checked against current AEL 1.4.1, last ael/ revision 17029c9. App recipes and the optional support policy remain separate from upstream defaults.

The changes are summarized below. “Documented choice” means the behavior was retained and explained, rather than claiming a new numerical fix. “Partial” identifies remaining qualification.

| Item | Disposition and resulting behavior | Main commit(s) |
| --- | --- | --- |
| 1 | Fixed: FNRGF edge fade changes alpha, not operator values. | 86f747c |
| 2 | Fixed: undefined FNRGF/RHEF operator values remain NaN and transparent. | 86f747c |
| 3 | Fixed: local quadratic radial-model smoothing replaces nearest-padded coefficient smoothing; structure-free controls retained. | 86f747c |
| 4 | Fixed: partial-support Fourier fits protect low harmonics from excessive regularization. | 690328d |
| 5 | Fixed: main RGB16 TIFF uses the PSB presentation; float32 working data are separate. | 1fe3c5c |
| 6 | Fixed: tangential/adaptive detail uses annular display statistics, not one global spread. | 86f747c |
| 7 | Optional remedy: dimensionless log-intensity Larson–Sekanina; linear mode retained for recipes. Native contrast measured, SNR improvement not claimed. | 1fe3c5c |
| 8 | Fixed for approximate previews: omit Gaussian scales below 0.5 target pixels without reweighting other contributions. | 00e588f |
| 9 | Fixed: RHEF layer preserves Upsilon-curved ranks without a second normalization. | 86f747c |
| 10 | Fixed: adaptive gain acts after encoding. Redundant Background Retention removed from GUI, retained numerically. | 86f747c |
| 11 | Fixed: tangential gain acts after encoding and changes the layer. | 86f747c |
| 12 | Fixed: canonical AEL layer preset strength is 100, matching GUI; opacity remains the layer mix. | b87d47f |
| 13 | Documented choice: Larson gain and opacity coincide before clipping; differ when Linear Light clips. Explicit regression demonstrates this. | b87d47f |
| 14 | Verified: every integer Gaussian truncation 1–6 is honored and matches the independent Gaussian reference. | b87d47f |
| 15 | Fixed: adaptive GUI uses local symmetric relative differences, supporting signed/zero measurements; numerical absolute API retained. | 4f86a5e |
| 16 | Partial: measured quadratic support cost and documented extrapolation; cooperative cancellation works. Full-native large-support timing remains P2. | 4f86a5e, 8ff96ed |
| 17 | Fixed: RHEF noise confidence attenuates alpha only; no ranks/input-unit mixture. | 86f747c |
| 18 | Fixed: RHEF ring widths use native pixels, with preview adaptation. | 00e588f |
| 19 | Documented choice: Upsilon 0.35 attributed to sunkit-image; wider range explicitly custom. | b87d47f |
| 20 | Fixed: FNRGF native physical ring width determines matching preview bins. | 00e588f |
| 21 | Fixed: application MGN uses normalized observed-support convolution at frame edges. Reference numerical backend remains available. | 32d8402 |
| 22 | Documented choice: keep expert gamma range, explain usual 2.5–4 range and global-weight behavior. | b87d47f |
| 23 | Fixed: application non-AEL WOW frame boundaries use absent support rather than mirrored samples. | 32d8402 |
| 24 | Fixed: masked bilateral WOW uses local variance for range weighting. | 32d8402 |
| 25 | Fixed: WOW masked denoising uses erf significance, checked against upstream watroo. | 32d8402 |
| 26 | Fixed labels: distinguish Standard, watroo bilateral and AEL guided WOW; legacy selector text still loads. | b87d47f |
| 27 | Documented choice: retain expert 180° endpoint; explain small-angle use and opposite-side interpretation. | b87d47f |
| 28 | Optional remedy: nearby-angle delta averages three rotations; zero retains classic behavior. Signal/noise tradeoff remains explicit. | 690328d |
| 29 | Documented choice: NRGF Multiply retains base radial brightness; neutral-layer darkening explained. | b87d47f |
| 30 | Fixed explanation: median/MAD identified as AEL/application default; paper mean/STD distinguished. | b87d47f |
| 31 | Documented choice: app tangential defaults and linear operator are distinct from Voillot and logarithmic angular ACHF; sources credited. | b87d47f |
| 32 | Fixed: sparse thresholded residuals with zero MAD use a supported nonzero spread, avoiding near-binary scaling. | 86f747c |
| 33 | Extended: radial and local operators separate statistical samples from targets. AEL compatibility default preserved; validated optional separation remains off. | 37d04f1, c25fd50, ce2f231 |
| 34 | Fixed validity: finite zeros are observations, including background patches/correction; NaNs/explicit masks mark missing data. Log/positive-only support remains operator-specific. | 690328d |
| 35 | Fixed: decimal geometry round-trips, draws and increments correctly. | eaa0091 |
| 36 | Fixed: inactive/excluded control edits no longer cancel numerical work, including explicit slider releases. | b214a5e, b87d47f |
| 37 | Fixed: background-fit results rejected when source, geometry or fit state is stale. | eaa0091 |
| 38 | Fixed: pending recalculation resumes after export rather than remaining stuck. | eaa0091 |
| 39 | Fixed: WOW threshold capture follows selected scale count, independent of disabled sidebar state. | eaa0091 |
| 40 | Fixed: cooperative export/close cancellation with safe checkpoints; already completed companion packages may remain. Publication itself is not interruptible. | 8ff96ed |
| 41 | Fixed: full-frame FNRGF extent follows new source/geometry; deliberate smaller limits preserved. | b214a5e |
| 42 | Fixed: Original label/state follows programmatic toggles. | b214a5e |
| 43 | Fixed: viewport presentation choice round-trips. Current presented exports no longer depend on that viewport toggle. | eaa0091, 1fe3c5c |
| 44 | Fixed: recipe validation/restoration uses incoming source dimensions. | eaa0091 |
| 45 | Fixed: PSB publication fallback for unsupported hard links; physical exFAT tested on macOS. | eaa0091 |
| 46 | Fixed: one unused stem for all export companions, including JSON and source package. | eaa0091 |
| 47 | Remedy: hidden 16-bit input preview labelled as quantized; authoritative signed float32 working products exported separately. PSB16 is not represented as a float master. | 1fe3c5c |
| 48 | Fixed cross-drive path fallback with Windows path regression. Actual Windows acceptance pending. | eaa0091 |
| 49 | Fixed: RGB display profiles in TIFF/JPEG/PSB; working float data remain separate. Profile bytes reused to avoid timestamp-only export differences. | 1fe3c5c, 5cfe084 |
| 50 | Fixed rejection: unsupported/multipage TIFFs fail clearly before geometry processing; multipage interpretation not added. | eaa0091 |

Evidence includes the complete application suite, current AEL 124/124 self-tests, synthetic operator/support/null/injection controls and both supplied native masters. Current continuous global RHEF matches the live AEL runtime exactly on both full-native inputs with matched parameters. ISO/angular ACHF, NRGF and guided WOW match current AEL on the tested synthetic scenes.

Photoshop 2026 opened and recomposed the full-native PSB: maximum difference from main TIFF was 8/65535 levels, p99 four levels. Float32 RGB and VALID matched the source exactly. Physical macOS-to-exFAT tests covered publication, repeated names, settings/decimal geometry and cancellation. Optional support restored observed targets without filling missing data; it is not promoted by default. Log Larson's stronger display response is not evidence of better astronomical SNR.

Remaining: Windows execution on the owner's separate machine; native large-support adaptive cost qualification (item 16/P2); independent observational fine-detail validation (no split stacks available); Developer ID signing/notarization. The local macOS package is ad-hoc signed. I am not asking to close the issue solely from the local dispositions, and would welcome independent review of these choices and residual limitations.

Detailed evidence: [P0/P1 acceptance](p0-p1-acceptance-20261102.md), [P3 package regression](p3-release-validation-20261102.md), [execution record](issue-3-follow-up-plan.md).
