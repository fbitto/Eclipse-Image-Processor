# Filter quality and default-parameter inspection plan

Prepared 8 November 2026. Planning only: no algorithms, defaults or saved user settings are changed by this document.

## Agreed objective and inputs

Start with the approved master and recommend a **balanced** result: useful coronal detail with restrained noise and artifacts. Broader validation follows later. Only the master FITS is available; there are no independent exposures, sub-stacks or noise/coverage products for scientific confirmation.

Approved source:

```
/Volumes/Astro/Imágenes/CoronaHDR_RAW/CoronaHDR_Work/.coronahdr-jobs/e1c3c474c41b4163b9c04099bb909948/result/master.fits
```

Expected SHA-256: `33ff81c882a0e5e98771b8c00f627af5860b56464798e16dc38e75122b45a005`.

Resolve symlinks and verify the hash before processing. Do not substitute the rejected `596a8739...` source or silently select another `master.fits`. Work in new ignored diagnostic directories, preserving original data, recipes, masks and manual edits. Record checkout/diff identity, dependency versions, CPU budget, source identity and every parameter. Existing reports are historical evidence, not qualification of a new checkout.

Use automatic protection geometry as the baseline; the earlier measurement was (2975, 1660, 272). Remeasure and record rather than silently hard-code it. This geometry describes the missing-data boundary and is not independent solar-center/lunar astrometry. Geometry perturbations belong only to labelled synthetic sensitivity controls; never retune real geometry to hide a ring.

## 1. Freeze the inventory and baseline

Extract current defaults and parameter units from the actual GUI snapshots, presets and numerical dispatchers. Include implementation selectors, hidden retained controls, scale choices, noise controls, exclusion masks, encodings, blend modes and opacity. Distinguish filter numerical parameters from composition defaults and filter enable flags.

| Family | Implementations to inspect | Principal initial questions |
| --- | --- | --- |
| NRGF | Median/MAD and mean/STD; legacy and anchored partial-annulus chaining | Partial coverage, radial profile/spread stability, limb bands and scale behavior |
| NAFE | AEL original; experimental limb-aware response | Broad bright band versus dark inner response, noise/window dependence, support and loss of radial structure |
| FNRGF | Continuous and reference-compatible | Annular steps, sector seams, regularization, width estimation and boundary effects |
| RHEF | Continuous global and legacy/compatible | Quantile/rank seams, artificial texture, tail contrast and optional confidence behavior |
| MGN | All configured scales and global/local mixture | Grain amplification, halos, scale weighting, and suppression of faint extended structure |
| WOW | Standard observed support, watroo bilateral, AEL guided edge-aware; AEL noise reduction off/on | Noise versus detail, local sign inversion, guide behavior, limb/coverage bands, display normalization |
| Tangential | Current angular-detail implementation | Directional bias, polar seams, support, angular width and noise threshold |
| Larson–Sekanina | Linear and log input | Positive/negative lobes, double edges, angle-dependent structure, noise and gain/clipping |
| ACHF | Adaptive circular, AEL ISO 01, ISO 04 and Angular | Rings, directional response, pair rejection, fine/coarse scales and boundary support |

Check every implementation at its defaults first; use targeted contrasts rather than an exhaustive Cartesian product of settings. Include base-only/no-filter controls. Freeze old output, so later tests can distinguish a repair from a presentation change.

## 2. Build a shared controlled test set

Reuse the repository's fixtures, synthetic utilities and real-image validation runner; extend the minimum needed for a common report. Consult the installed AEL runtime and tests through its bundled launcher. Run its self-test before processing, recording passes/failures/skips separately. The planning environment check identified AEL 1.4.2; dependencies for image processing are present, while rawpy/imageio are absent. No RAW work or installation is needed for the FITS-based first phase.

Synthetic scenes must cover:

- Smooth ring-free radial falloff, both centered and offset from the lunar missing-data disk; input with no angular structure or noise.
- Known angular streamers and radial structures at several widths, amplitudes and orientations, including near-noise-limit injections. Test positive and negative perturbations on an otherwise identical scene.
- White and spatially correlated noise at multiple levels, seeds and brightness levels; spatially varying noise and coverage steps.
- A smooth sky gradient and broad coronal emission, ensuring suppression does not confuse low-contrast signal with noise.
- Missing circular limbs, straight/rectangular edges, internal holes and partial angular coverage; test missing validity separately from statistical exclusions.
- Stars/spikes and sharp bright features, to reveal halos, double edges and guide-induced sign changes.
- Constants, signed/nonpositive inputs where supported, nonfinite values, unit rescaling, bypass settings and cancellation.

Use paired noisy scenes with exactly the same noise realization before/after an injected structure to measure incremental signal response. Use different noise seeds for independent-noise nulls. A denoiser must not pass just by producing a neutral image.

Declare masks, radial distance bands, sectors, scales, seeds, measurements and acceptance criteria before evaluating modifications. Retain deliberately bad baselines: stepped annuli, injected concentric rings and a known sign-inversion scene where applicable. The tests must detect these failures. Calibrate numerical tolerances against known truth and resolution; do not set thresholds after seeing a preferred candidate.

## 3. Measure three stages separately

Inspect raw operator values, encoded independent layers/alpha, then final compositions. A defect first introduced by layer normalization or blending needs a correction there, not an unrelated operator change. Freeze exposure, presentation scale, color, geometry and opacity during causal comparisons. Use monochrome first, then verify the accepted candidates with existing sunset color settings and prominence presentation.

| Quality | Measurements and controls |
| --- | --- |
| Noise/texture | Robust residual spread, spatial power by scale, spatial autocorrelation and coherent patterns; quantify both raw and displayed output. On the real master call this background texture, not measured sensor noise. |
| Detail | Paired injection response, sign agreement, width/position change, orientation/scale transfer, radial and angular feature retention; report faint and strong cases separately. |
| Contrast | Local feature/background separation, broad-gradient retention, highlight/shadow compression, neutral-layer bias, clipping and saturation fractions. |
| Rings/bands | Radial-profile residuals and multi-scale ring energy; inspect both solar-centered annuli and distance to the actual missing-data boundary. Report angular sectors and worst local failures, not just an azimuthal average. |
| Other defects | Straight-edge overshoot/undershoot, corner bands, seams, halos, ringing, double contours, stars/spikes and false coherent texture. |
| Support | Finite/alpha coverage by distance and sector; ensure an apparent improvement did not discard the difficult pixels or fill missing ones. |
| Operational cost | Runtime, peak memory, cancellation responsiveness, cache reuse and preview/native discrepancy. |

Filters have different units, encodings and blend modes. Do not rank them by raw RMS or independently auto-stretched screenshots. Provide both fixed-presentation comparisons and explicitly matched useful-feature-contrast comparisons, showing the noise/detail tradeoff. Keep opacities visible in every comparison. Avoid treating greater sharpness or higher apparent contrast as proof of more information.

## 4. Inspect the approved master

1. Establish fixed full-canvas, inner-limb, middle/outer-corona, candidate background, coverage-edge and corner views. Record ROI coordinates and masks once. Outside four radii is an operational sampling region, not proof that no corona exists there.
2. Run every implementation alone at current defaults in preview and full native resolution. Retain original operator/layer receipts and support. Compare with the untouched base and the same presentation. Native output decides final quality, not an enlarged preview.
3. Flag the first stage and location of each defect; reproduce it synthetically where possible. Separate source features, missing-support behavior, noise gain, radial-statistics errors and blend/display effects. Unknown cause stays unknown.
4. Screen the likely high-impact controls first, as described below; sweep only the controls shown to matter. Test a small set of finalists on the whole native canvas. Crops are diagnostic only; nonlinear statistics must not be refitted on a crop and presented as full-frame evidence.
5. Repeat finalist measurements under the current statistical mask and the opt-in support-separation mode where relevant. Do not silently change mask semantics between candidates.

The existing NAFE and WOW reports supply baseline cases, not automatic passes. In particular, compare NAFE's bright-band reduction against its dark inner response, and WOW's quieter sky against measured losses in weak injected structures. AEL's field lessons describe historical and current branches; confirm each mechanism in the actual local code instead of assuming a shared name implies a shared algorithm.

## 5. Rank parameter influence before tuning defaults

Do not vary every parameter. First use the code, existing measurements and default-output defects to shortlist the likely dominant controls for each filter. Start with one or two candidates per family, rather than a mandatory test of every available control. Possible candidates include scale/window size, noise threshold, local/global mixture or normalization; the baseline findings decide which are relevant.

Change one shortlisted control at a time around its default, using one meaningful lower and upper setting within its supported range. Keep other settings fixed. Compare numerical detail/noise/artifact changes at fixed opacity and display, then check whether the visual difference remains at useful matched contrast. Rank influence by the size and location of the effect relative to the tested parameter change and seed-to-seed variation. Report separate effects on detail, noise, contrast and defects: a large effect is not necessarily an improvement. Do not compare raw slider ticks across controls with different units or nonlinear mappings.

Deliver a short sensitivity table per filter: control, tested values, measured effects, worst local defect and whether further tuning is justified. Leave low-impact controls at their defaults. Expand the shortlist only when the first controls cannot explain or improve a demonstrated problem; low apparent sensitivity on one scene is not a universal claim.

Only then run a small targeted sweep of the dominant controls, and test interactions only between shortlisted controls with a plausible shared mechanism. Evaluate opacity separately as a composition control so simply weakening a filter is not mistaken for a numerical repair. Specify exact tested ranges before candidate evaluation. Use separate tuning and held-out synthetic scenes/seeds; reserve real ROIs for final checks so tuning does not repeatedly exploit the same view.

Select parameters on a noise/detail/defect tradeoff frontier, not a single opaque score. An average improvement cannot cancel a local sign reversal, a new ring or lost support. Report hard failures separately from appearance preferences. Lack of independent real observations limits claims even when all synthetic tests pass.

Produce two distinct recommendations:

- **Per-filter defaults:** conservative numerical settings and opacity when the user enables that filter; a filter can remain disabled by default.
- **Balanced starter composition:** a minimal complementary subset, with measured contributions. Adding several similar detail filters can amplify the same noise and artifacts; do not recommend enabling everything.

Run targeted interaction tests for likely combinations (for example radial flattening plus one detail layer), then ablate each layer from the finalist composition. Even independent numerical branches interact through blending, clipping and color presentation. Test normal working opacities as well as 100% diagnostic opacity.

## 6. Decide repairs, adaptations or alternatives

For each demonstrated failure, compare these choices in order:

1. Safer parameters or an existing implementation, if it preserves useful detail and meets the same checks.
2. A small shared correction at the first failing stage, validated with original parity/bypass tests and held-out controls.
3. An explicitly selectable alternative only when the tradeoff cannot be resolved by the current algorithm (for example different statistical support or signal-confidence weighting).
4. Keep a method experimental, narrow its documented use, or leave it disabled when evidence is insufficient.

Potential investigations—not predetermined changes—include stable continuous radial statistics, support-aware uncertainty/confidence on detail contributions, locally varying noise estimation when a single outer estimate fails, and shared display normalization fixes. Test whether a proposed denoising change works at matched contrast and preserves faint structures; do not add a denoiser to every filter by default.

Do not blur away a defect, introduce artificial radial fades to hide it, fill gaps, mirror texture, borrow pixels or move real lunar geometry. A legitimate support rule must be reported, not counted as a repaired pixel. Preserve failed candidates and fixed thresholds. Changes of familiar look require full-canvas comparisons and the user's selection before default adoption, following the AEL diagnosis skill.

## 7. Deliverables and acceptance

- A reproducible machine-readable results table with parameters, masks, hashes, versions and measurements at every stage.
- A filter/mode scorecard: recommended use, noise/detail tradeoff, local failures, support, cost, preview reliability and evidence limits.
- Labelled full-canvas comparisons plus matched limb/sky/feature crops, with before/after and failure controls.
- Proposed numerical defaults, enable flags and opacities as a reviewable recipe; current defaults remain intact until approval.
- A prioritized defect ledger: reproduced cause, minimal candidate correction, alternatives, tests and remaining uncertainty. Algorithm changes become separate reviewable work.
- Automated regression tests, real native/preview checks and TIFF/JPEG/PSB/recipe consistency for adopted changes. GUI controls must preserve old recipe defaults and remain responsive.

Evidence is labelled separately as file integrity, visual/operational checks, synthetic known-truth tests, upstream parity and independent real-data confirmation. The last category is unavailable with this input. Proposed defaults are qualified for this approved master and test suite; broader masters are required before calling them general defaults.

## Additional proposals

- A compact user-facing “Compare at native resolution” workflow with locked exposure and synchronized crops could prevent preview-driven parameter choices. First use existing views; add UI only if the evaluation demonstrates the need.
- Retain a small permanent quality regression set and worst-sector metrics, so a future performance change cannot silently reintroduce rings or sign reversal.
- Prefer one balanced starter recipe over numerous speculative presets. Consider an explicit-detail preset only if tests show a distinct useful tradeoff and the user wants it.
- If independent exposures/sub-stacks later become available, validate repeatability across them before upgrading claims about recovered faint detail. AEL parity alone is not independent truth.

## Execution checkpoints

First deliver the inventory and baseline defect map, followed by the short parameter-influence ranking. Freeze acceptance criteria before evaluating candidates; use the influence ranking to choose the few controls and ranges worth tuning. Present the balanced recipe and ranked repair proposals for user review. Implementation and changes to defaults follow approval of those concrete results, not this planning document alone.

## Follow-up execution

The approved-master study and optional normalization fixes have been executed. Evidence is retained in the dated Astro study folder, with fixes under `08-Normalization-Fixes-and-Extensive-Validation`. See [revised filter normalization](revised-filter-normalization.md) for the implemented paths, 540-test regression and limitations. Compatible remains the default pending review of the changed contrast; no general multi-image qualification is claimed.
