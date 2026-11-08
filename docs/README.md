# Technical documentation

Current implementation: Eclipse Image Processor 0.7.1. Updated 8 November 2026 from the application source. See the [v0.7.1 release notes](release-notes-0.7.1.md). The guides below describe the active pipeline; dated reports record earlier experiments and do not override these guides.

## Current guides

| Guide | Scope |
| --- | --- |
| [Application README](../README.md) | Installation, workflow, initial settings, outputs and scientific credits |
| [v0.7.1 release notes](release-notes-0.7.1.md) | Basic starter, contrast mappings, color controls and UI changes |
| [Revised normalization](revised-filter-normalization.md) | Optional contrast policy and radial-model corrections |
| [Bounded ACHF contrast](achf-bounded-contrast.md) | Independent contrast mapping and gain per AEL variant |
| [Source-relative Tangential](tangential-source-relative.md) | Source-based contrast reference and empirical noise floor |
| [WOW noise reduction](wow-noise-reduction.md) | Optional AEL guided suppression and faint-detail tradeoffs |
| [Color controls](sky-colour-proposal.md) | General warmth, additive Corona warmth and sky green reduction |
| [Architecture](architecture.md) | Modules, working data, threads, cancellation and resolution handling |
| [Layer composition](layer-composition.md) | Independent filters, blend modes, controls and caches |
| [Background extraction](background-extraction.md) | Sky samples, robust plane fitting and slope subtraction |
| [Settings JSON](settings.md) | Version 4 schema, restoration and source paths |
| [Control levels](ui-levels-20261103.md) | Layout, Basic AEL filters and project compatibility |
| [PSB export](psb-export.md) | Presentation, layer files, verification, colour correction and limits |
| [AEL NAFE](nafe-ael.md) | Fuzzy equalization, noise units, approximate preview and independent Overlay export |
| [AEL ACHF](achf-ael.md) | ISO 01, ISO 04 and Angular implementation |
| [Larson–Sekanina](larson-sekanina.md) | Rotational residual, Gain and Linear Light encoding |
| [Continuous RHEF](rhef-continuous.md) | Quantile interpolation and support rules |
| [P0/P1 acceptance, 2 November](p0-p1-acceptance-20261102.md) | Native Photoshop/exFAT, current AEL parity and native-image support checks |
| [Prominence detail correction](prominence-detail-20261102.md) | Separate highlight curve, inward mask edge blend and Asinh comparison |
| [P2 native performance](p2-native-performance-20261102.md) | Measured adaptive ACHF cost, cancellation and Cocoa scheduling |
| [P3 release checks](p3-release-validation-20261102.md) | macOS app/DMG and legacy recipe/export smoke; Windows follow-up recorded separately |
| [Windows validation, 2 November](windows-validation-20261102.md) | Passing regression suite, packaged export/reopen, cross-drive loading, cancellation and native Photoshop checks |
| [Issue #3 response draft](issue-3-response-draft.md) | Item-by-item local review response; not posted |
| [Validation](validation.md) | Reproducible checks and the limits of existing evidence |
| [Streamer-aware warmth, 2 November](streamer-warmth-20261102.md) | Enhanced streamer coverage, neutral-colour support and editable warmth masks |
| [Earlier warmth/status checks, 2 November](warmth-validation-20261102.md) | Historical linear-signal warmth and active preview-ready status fix |
| [macOS build](build-macos.md) / [Windows build](build-windows.md) | Platform packaging |
| [Third-party attribution](../ATTRIBUTIONS.md) | Copied/adapted code and retained licence notices |

## Historical research and implementation reports

These documents retain their original measurements and design decisions. They can mention removed controls, sequential processing, previous defaults and export contracts that no longer apply.

- [AEL filter review](ael-filter-review.md): AEL 1.3.2 research.
- [External filter ideas, 19 October](external-filter-ideas-20261019.md).
- [Filter controls, 19 October](filter-controls-20261019.md).
- [Filter validation, 19 October](filter-validation-20261019.md).
- [GHS reference, 19 October](ghs-reference-20261019.md): retired presentation path.
- [Performance measurements, 21 October](performance-optimization-20261021.md).
- [Performance measurements, 1 November](performance-optimization-20261101.md).
- [Photoshop colour proposal](propuesta-color-atardecer-psb.md): design and earlier native checks.
- [PSB writer probe](psb-writer-probe.md): feasibility experiment using an installed AEL runtime.
- [Earlier native PSB measurements](psb-validation-history.md): previous transparent, black-backed and antialiased exports.

Screenshots are illustrative captures, not an inventory of current controls. Scientific references identify sources used during development; their external URLs have not been revalidated in this documentation update.
