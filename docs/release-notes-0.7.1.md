# Eclipse Image Processor v0.7.1

## Changes

- Basic starts the first directly opened image with the reviewed six-layer preset: NAFE original 40%, Reference-compatible FNRGF 15%, AEL guided WOW 10%, Source-relative Tangential 10%, and Bounded ISO04/Angular at contrast 3 and 10% each. FNRGF uses 2-native-pixel rings and an inner radius of 1 R. Experimental AEL support separation is enabled. NRGF and MGN remain available but off.
- Basic now exposes FNRGF and Tangential. Mode switches and subsequent direct image loads retain eligible filter settings; loading JSON restores its own controls rather than applying the starter.
- Optional Revised normalization, Source-relative Tangential and per-variant Bounded ACHF contrast provide alternative display mappings. Existing recipes retain their selected mappings; absent optional controls use compatibility defaults.
- AEL guided WOW gains optional noise reduction. NAFE preview scales its internal Gaussian widths with resolution, and offers an experimental Limb-aware response while retaining AEL original as the default method.
- General warmth sets a whole-image baseline, followed by additive Corona warmth and adjustable sky green reduction. Original prominence colors remain independently controlled. Prominence-preview switching and visibility were corrected.
- Filter Statistics & Normalization groups statistical exclusions, AEL support separation and normalization directly after Background Gradient. Basic hides the group; Standard shows normalization and Expert reveals the statistical controls. General warmth now appears before Corona warmth. Tooltips and the README reflect the current controls and defaults.

## Validation

All 552 repository tests passed on 8 November 2026 (84.539 seconds), including generated macOS/Windows version metadata, UI/settings behavior, filters and export checks. This source-level regression does not replace native testing of rebuilt release packages.

## Compatibility and limits

Settings remain version 4. The app title and generated macOS/Windows version metadata use 0.7.1. Standard/Expert first-load defaults retain their previous behavior.

The Basic recipe was visually selected on one master, accepting slight background noise and a visible but acceptable limb ring. Its GUI reload/re-save preserved all processing controls. This is not multi-image scientific validation. Fast preview remains approximate; inspect native detail, particularly ISO04. Small images may lack sufficient samples for eight-scale WOW noise reduction: reduce scales in Expert or set Noise reduction to zero when its support error appears.

Existing packages must be rebuilt to include these changes. Historical Windows/Photoshop and macOS package checks do not qualify a v0.7.1 build. The macOS arm64 app and DMG were subsequently built on 8 November 2026. Bundle versions are 0.7.1, the ad-hoc signature passed strict verification, and the DMG integrity check passed. DMG SHA-256: `882ef2b1b3a5733b2f0a73bdc9148a2a10744222a72a827128ee03a6e1772b10`. Native launch/image/export smoke testing of this package and a Windows build remain unperformed. No release was published.

See the [README](../README.md), [layer composition](layer-composition.md), [revised normalization](revised-filter-normalization.md), [bounded ACHF](achf-bounded-contrast.md), [Tangential mapping](tangential-source-relative.md), [WOW noise reduction](wow-noise-reduction.md), and [color controls](sky-colour-proposal.md).
