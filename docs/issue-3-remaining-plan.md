# Issue #3: remaining acceptance plan

Prepared 2 November 2026 against local commit b87d47f and the current [issue #3](https://github.com/fbitto/Eclipse-Image-Processor/issues/3), still open and last updated 31 October. The original review targets 35d555f; it has not yet been reconciled upstream with the local fixes.

All 50 items have a local disposition. This means implemented, verified, or explicitly resolved by a documented design choice—not that all have independent acceptance. See the [execution record](issue-3-follow-up-plan.md) and [validation boundaries](validation.md).

## Ordered work

| Priority | Scope / issue items | Work | Completion criteria |
| --- | --- | --- | --- |
| P0 — Export acceptance | #5, #40, #45–49 | Open a newly generated native PSB in Photoshop; compare its initial composite and recomposed visible layers with the main TIFF, with Color Correction disabled first. Separately exercise Color Correction and record the expected difference. On real Windows, test cross-drive recipe reopening and export to exFAT, repeated names, cancellation and close during export. | TIFF and uncorrected PSB agree within a stated measured quantization tolerance; profiles and source/VALID products are verified; cross-drive recipes reopen; repeated exports have coherent stems; cancellation leaves no corrupt published files and reports any completed companions. Record application/Photoshop/OS versions. |
| P1 — Image-quality acceptance | #7–8, #15–16, #28, #33–34 | Compare native compatibility and optional AEL support modes on the supplied margin TIFF plus a second independent eclipse case if available. Use fixed settings and common display mappings. Inspect limb, stars, excluded sectors, missing boundaries and faint outer rays. Include signed/zero synthetic observations, injected faint structure and independent-noise controls. Compare linear/log Larson–Sekanina and nearby-angle averaging separately. | Publish per-layer coverage, contrast/response and noise measurements with crops and settings. No missing pixels filled, no excluded-sample poisoning, same-mask AEL parity retained. Record artifacts and failures. Keep AEL support off and LS linear by default unless evidence and a separate decision justify promotion. |
| P2 — Native runtime and responsiveness | #16, #36, #40 | Measure adaptive ACHF on the native image at default and a larger practical support. Cancel an extreme setting rather than waiting on an extrapolated full run. Exercise inactive edits, geometry changes, queued recalculation and export cancellation in a normal desktop session. | Record wall time, cancellation latency and memory where measurable; latest queued work resumes and stale results cannot replace it. Decide whether a cost hint or optimization is necessary from measurements; no speculative rewrite. |
| P3 — Release regression | #35–50 plus support/export changes | Run the full suite on the final checkout, including the two late tests previously run separately. Build and launch macOS and Windows packages; load a legacy recipe and export a small package on each. Correct stale documentation about item 33 and distinguish historical checks from current checks. | One final full-suite count/log, successful package smoke checks, reproducible recipes and consistent current documentation. Build/signing credentials or unavailable hardware are recorded as explicit blockers, not simulated passes. |
| P4 — Review closeout | All 50; especially #13–14, #19, #22, #27, #29–31 | Prepare an item-by-item response with fix commit, regression evidence and remaining limitations. Label documented design choices clearly. Send/post only when requested. | A reviewable response covers every item without claiming code changes for documentation-only resolutions. Upstream acceptance remains the reviewer's decision. |

## Execution sequence and dependencies

1. Refresh the final automated baseline and reconcile documentation (the machine-local portion of P3). This is an inexpensive prerequisite to manual acceptance, not a higher risk priority.
2. Generate one reproducible native acceptance package for P0, preserving the source and recording source hash, recipe, output paths and expected pixels. Reuse it for Photoshop and Windows/exFAT checks where possible.
3. Complete P0 tests on available applications/hardware. Continue independent image-quality work if either platform is unavailable; do not substitute mocked filesystem tests for physical acceptance.
4. Run P1 comparisons, then P2 performance checks. Fix only demonstrated failures, each with a focused regression and a separate commit.
5. Run final regressions/package smoke checks after fixes. Assemble the P4 response and list any unmet acceptance criteria.

Existing private artifacts remain outside Git. Start from `/tmp/eclipse-follow-up-real-20261101/` if still present; regenerate from the source and captured recipe if absent. The earlier `/tmp/eclipse-p1-margin-check/report.md` contains historical P1 measurements, not the final export contract.

## Decisions and boundaries

- No new filters, automatic default promotion, or broad numerical refactor is planned.
- Native Photoshop, Windows and exFAT access determine which manual acceptance steps can actually be completed. Ask for missing resources only after checking available local capabilities.
- Consult AEL locally first. Its last verified runtime was 1.4.1 with 124/124 self-tests on 1 November; refresh provenance if an upstream comparison is needed. This plan does not claim a new upstream filter audit.
- Existing evidence: 390 full-suite tests passed, with two additional checks passing in targeted suites; native presented TIFF pixels and float32 source/VALID products matched expectations. These do not replace the acceptance gates above.

## Execution update — 2 November 2026

P0 native Photoshop, physical macOS-to-exFAT, source/profile integrity and cooperative close checks completed; Windows remains unavailable by user confirmation. P1 native comparisons completed on both supplied products, with compatibility defaults retained and current AEL operator fidelity checked. Independent observational fine-detail acceptance remains unavailable (no independent split stacks). See [measurements and limitations](p0-p1-acceptance-20261102.md).
