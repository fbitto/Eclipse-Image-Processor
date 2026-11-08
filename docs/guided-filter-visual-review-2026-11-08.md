# Guided filter visual review — 8 November 2026

Status: Paused for conclusions at user request under Q164. Final six-layer preset accepted and GUI reload/re-save verified; only Geometry card expansion differs. No question pending. Export remains unchecked.

## Purpose and method

Choose useful contrast mappings and candidate settings for balanced detail with restrained noise and artifacts. Use the approved e1c3c474 master only. Existing defaults remain unchanged during this review. Numerical qualification is separate from the user's visual judgments; no conclusion about physical reality follows from visibility alone.

Ask one question at a time. Record each answer verbatim, the viewed artifact or app settings, interpretation and any follow-up needed. Allow “no difference”, “uncertain” and “cannot assess”; do not force a winner. Save each answer before asking the next question. Adapt follow-ups to reported defects instead of sweeping every parameter.

## Script

1. Establish review method: saved comparisons or running app.
2. Establish baseline: confirm the exact comparison/source, native view and fixed presentation/opacity. If using the app, record relevant settings before judging.
3. ISO04: overall preference between Compatible, Revised and Bounded; then separate questions on limb rings/halos, middle-corona detail, outer structure, and background noise. Reference one region and one issue per question.
4. ISO04: inspect corresponding native crops; assess whether the preference survives native detail. Compare fast/native preview separately if using the app. If artifacts dominate, record their location before changing anything.
5. Repeat targeted comparisons for ISO01 and Angular. Skip redundant questions only when the answer has already been explicitly recorded for that variant.
6. For promising bounded mappings, compare a small gain ladder at fixed opacity. Then assess opacity separately. Record unsupported settings as untested; request/generate additional comparisons only as needed.
7. Compare a restrained combined preset against its baseline; assess each added filter's contribution and cumulative noise. Do not infer combined quality from isolated layers.
8. Confirm the preferred candidate and unacceptable defects with the user. Summarize per-filter mapping/gain/opacity recommendations, evidence, uncertainty and remaining validation. Treat recommendations as provisional until another master is tested.

## Evidence

Study folder: `/Volumes/Astro/Imágenes/Eclipse-Filter-Quality-and-Default-Parameters-2026-11-08/`.

Bounded ACHF evidence: `11-AEL-ACHF-Bounded-Contrast-Implementation-and-Validation/`. The three-path sheets compare Compatible, Revised and Bounded at the same working opacity. They are overviews derived from native calculations, not 100% native-pixel crops. Current sheets use bounded gain 2 for ISO01 and 4 for ISO04/Angular. Gain is not identical between all mapping methods, so a preference selects a complete tested configuration, not the curve alone.

Known limit: bounded ISO04 encoded preview/native RMSE was 0.07492 on this master. Native output is the reference for acceptance. No Windows/Photoshop execution or app/DMG rebuild is established by this review.

## Questions and answers

### Q01 — Review method

Question: Would you like to start with the saved comparison images, or test interactively in the running app?

Options: Saved comparisons (recommended); Running app.

Answer (verbatim): “2”

Interpretation: Running app. Guide settings explicitly and record them before visual judgments.

### Q02 — Source confirmation

Question: Is the running app using the approved master at `/Volumes/Astro/Imágenes/CoronaHDR_RAW/CoronaHDR_Work/.coronahdr-jobs/e1c3c474c41b4163b9c04099bb909948/result/master.fits`?

Answer (verbatim): “yes”

Interpretation: User confirms the approved source is loaded. This is user confirmation, not an independent inspection of app state.

### Q03 — Control availability

Question: Expand ACHF ISO 04. Below Opacity, do you see the Contrast selector with a Bounded signed (experimental) option?

Answer (verbatim): “yes”

Interpretation: User confirms the running app exposes the new selector; packaged build identity has not been independently checked.

### Q04 — Isolate ISO04

Instruction: Preserve current settings in a separate settings JSON if they need to be retained. Enable only ACHF ISO04 among enhancement filters; disable the other enhancement filters, including other ACHF variants. Set ISO04 Opacity to 10%. Leave colour, exposure, background preparation and geometry unchanged for now; these still need to be recorded before comparisons.

Question: Is ISO04 now the only active enhancement filter, with Opacity at 10%?

Answer (verbatim): “yes”

Interpretation: User confirms ISO04 isolated at 10% opacity. Saving the preceding settings was suggested but not independently confirmed. Colour, exposure, preparation and geometry remain unrecorded.

### Q05 — Native-preview baseline

Instruction: Set ISO04 Contrast to Follow filter normalization. In Geometry, select Compatible for Filter normalization (switch to Standard/Expert if needed). Turn View Original off. Enable Full-resolution preview, keep zoom at Fit, and wait for processing to finish; use Auto Calculate if necessary. Keep presentation and other settings fixed throughout subsequent comparisons.

Question: Has the Compatible image finished rendering with Full-resolution preview enabled?

Answer (verbatim): “i dont see Geometry **Filter normalization → Compatible**; i'm in expert mode”

Interpretation: Baseline not yet confirmed. Do not treat this as an image-quality observation. Source inspection locates the selector in SOLAR DISK GEOMETRY; it is appended after that section's other controls.

### Q05a — Locate global normalization

Instruction: Expand SOLAR DISK GEOMETRY near the top of the controls, then scroll to the bottom of that section, below the statistics/limb controls. Look for the dropdown displaying Filter normalization: Compatible or Filter normalization: Revised (experimental).

Question: Can you see that dropdown there?

Answer (verbatim): “yes”

Interpretation: User located the global normalization selector. Its selected value and completed native render remain unconfirmed.

### Q05b — Finish baseline setup

Instruction: Select Filter normalization: Compatible; keep ISO04 Contrast at Follow filter normalization, ISO04 alone active at 10% opacity, View Original off, Full-resolution preview on and zoom Fit. Wait for processing to finish, calculating manually if needed.

Question: Is this baseline now fully rendered?

Answer (verbatim): “yes”

Interpretation: User confirms the isolated ISO04 Compatible baseline is rendered at native calculation resolution, Fit display, 10% opacity, Follow normalization, View Original off. Presentation, geometry and spatial filter values have not been captured; retain them unchanged. Fit display is not a native-pixel inspection.

### Q06 — Compatible limb at native-pixel display

Instruction: Keeping all settings fixed, change zoom to 100% and pan to the lunar edge. Inspect several parts of the circumference for a distinct bright ring or dark halo rather than the broader coronal glow. The observation describes appearance only, not its cause; attribution requires comparison with filter off.

Question: Around the lunar edge, do you see a distinct ring or halo: none, bright ring, dark halo, both, or uncertain?

Answer (verbatim): “none at 10% opacity. a narrow bright rim at 100%”

Interpretation: No visible limb artifact reported at the tested 10% opacity. A narrow bright rim is reported at “100%”, provisionally interpreted as filter opacity 100% from the contrast with 10% opacity; verify this interpretation in the next instruction. No causal attribution yet. Zoom was requested at 100% but not separately confirmed.

### Q07 — Filter-off control for the bright rim

Instruction: For the rim check, use ISO04 opacity 100% and zoom 100%; if the preceding “100%” meant zoom rather than opacity, clarify that instead. Keep the same limb region and all presentation settings fixed. Toggle only ISO04 Active off/on, waiting for each image to finish updating.

Question: When ISO04 is off, does the narrow bright rim disappear, become weaker, stay the same, or are you uncertain?

Answer (verbatim): “i meant 100% opacity. with iso04 off the ring disappears”

Interpretation: User confirms the stress-test opacity is 100%. The narrow bright rim disappears with ISO04 disabled under the current presentation. This supports an ISO04-dependent visible rim in Compatible mode, but does not isolate its numerical cause or establish that the underlying source edge is absent. No rim was reported at 10% opacity.

### Q08 — Revised limb comparison

Instruction: Re-enable ISO04 at 100% opacity, retaining Follow filter normalization, full-resolution preview, the same limb region and presentation. Change only the global Filter normalization to Revised (experimental), wait for recalculation, and compare against Compatible by switching back if necessary. The contrast mappings differ in strength; this is an appearance comparison at equal opacity, not equal local contrast.

Question: Compared with Compatible, is the narrow bright rim absent, weaker, about the same, stronger, or uncertain in Revised?

Answer (verbatim): “weaker”

Interpretation: At 100% ISO04 opacity, Revised reduces the visible rim relative to Compatible, but the user has not reported its complete removal. This compares appearance at equal opacity, not equal local contrast.

### Q09 — Bounded limb comparison

Instruction: Keep ISO04 alone active at 100% opacity, full-resolution preview and the same limb region/presentation. Change ISO04 Contrast to Bounded signed (experimental) and explicitly set Detail contrast to 4. Leave global normalization at Revised (bounded overrides it for ISO04). Wait for processing. Compare with the preceding Follow/Revised image, toggling the per-card selector if needed.

Question: Compared with Revised, is the narrow bright rim absent, weaker, about the same, stronger, or uncertain in Bounded at Detail contrast 4?

Answer (verbatim): “about the same”

Interpretation: At 100% opacity, Bounded at gain 4 has approximately the same visible rim as Follow/Revised. No additional limb improvement was observed from the bounded mapping. This judgment concerns the rim only, not overall detail or noise.

### Q10 — Bounded at working opacity

Instruction: Keep Bounded signed selected at Detail contrast 4. Reduce only ISO04 opacity to 10%, keeping full-resolution preview and the same 100%-zoom limb region. Wait for the image to update.

Question: At 10% opacity, is the narrow bright rim visible, absent, or uncertain?

Answer (verbatim): “absent”

Interpretation: User reports no visible narrow bright rim with ISO04 Bounded gain 4 at 10% opacity in the inspected limb view. This is a local visual observation, not proof of artifact-free output.

### Q11 — Outer detail at working opacity

Instruction: Keep ISO04 alone active at 10% opacity and full-resolution preview. At 100% zoom, choose a faint outer streamer region and retain the same framing. With global normalization still Revised, compare per-card Follow filter normalization against Bounded signed at Detail contrast 4, waiting for each calculation. Keep presentation fixed. Judge recognizable streamer edges/filaments separately from increased grain; this compares complete settings, not equal-strength curves.

Question: Which gives more useful outer-streamer detail: Follow/Revised, Bounded at 4, no meaningful difference, or uncertain?

Answer (verbatim): “bounded at 4”

Interpretation: User prefers ISO04 Bounded gain 4 over Follow/Revised for useful outer-streamer detail at 10% opacity in the selected region. This does not establish improved SNR or physical reality of the enhanced structure.

### Q12 — Background-noise comparison

Instruction: Keep ISO04 alone active at 10% opacity, full-resolution preview and 100% zoom. Pan to a quiet background patch away from the lunar limb and obvious streamers. Compare the same patch between Follow/Revised and Bounded gain 4, keeping presentation fixed and waiting for calculation.

Question: Compared with Follow/Revised, is the background noise with Bounded at 4 about the same, more visible but acceptable, distractingly stronger, or uncertain?

Answer (verbatim): “more visible, a little bit distracting”

Interpretation: Bounded gain 4 increases visible background noise relative to Follow/Revised, with mild distraction. Do not categorize this as fully acceptable or severely distracting. Its outer-detail benefit has a reported noise cost; test a lower gain before recommending it.

### Q13 — Lower-gain balance

Instruction: Keep Bounded signed at 10% opacity, full-resolution preview and 100% zoom. Compare Detail contrast 3 against 4, waiting for each calculation. Revisit the same quiet-background and outer-streamer regions; keep presentation and framing consistent within each comparison.

Question: Which gives the better balance of useful streamer detail and distracting noise: contrast 3, contrast 4, no meaningful difference, or uncertain?

Answer (verbatim): “3”

Interpretation: User prefers Bounded gain 3 over 4 for the combined detail/noise balance at 10% opacity. This is a candidate setting, not confirmation that noise is now fully acceptable.

### Q14 — Check the next lower gain

Instruction: Keep ISO04 Bounded signed at 10% opacity, full-resolution preview and 100% zoom. Compare Detail contrast 2 against 3 using the same background and outer-streamer regions. Wait for each calculation and keep all other settings fixed.

Question: Which gives the better detail/noise balance: contrast 2, contrast 3, no meaningful difference, or uncertain?

Answer (verbatim): “3”

Interpretation: User prefers Bounded gain 3 over both tested neighbors, 2 and 4, at 10% opacity. This supports gain 3 as the current candidate, without establishing absolute noise acceptability.

### Q15 — Noise acceptance at the candidate setting

Instruction: Leave ISO04 Bounded signed at Detail contrast 3 and 10% opacity. With full-resolution preview and 100% zoom, inspect the same quiet background patch.

Question: At this setting, is background noise acceptable, still slightly distracting, clearly distracting, or uncertain?

Answer (verbatim): “still sightly distracting”

Interpretation: At Bounded gain 3 and 10% opacity, background noise remains slightly distracting. The preferred gain has not yet produced an accepted overall balance; test reduced opacity independently.

### Q16 — Lower opacity at fixed contrast

Instruction: Keep ISO04 Bounded signed at Detail contrast 3, full-resolution preview and 100% zoom. Compare Opacity 7% against 10% in the same quiet background and outer-streamer regions, waiting for each update. Keep all other settings fixed.

Question: Which gives the better overall detail/noise balance: 7% opacity, 10%, neither is satisfactory, or uncertain?

Answer (verbatim): “more or less the same”

Interpretation: No clear overall balance preference between 7% and 10% opacity at Bounded gain 3. This does not establish that their noise is identical or that either is satisfactory. Avoid further fine opacity steps without a clearer benefit.

### Q17 — Is ISO04 worth including?

Instruction: Set ISO04 Bounded signed to Detail contrast 3 and Opacity 10% for a consistent reference. Keep other enhancement filters off and all presentation settings fixed. At full-resolution preview and 100% zoom, compare ISO04 Active on/off in the previously inspected outer-streamer and quiet-background regions, waiting for each update.

Question: Overall, do you prefer ISO04 on, ISO04 off, no meaningful difference, or uncertain?

Answer (verbatim): “on”

Interpretation: User prefers ISO04 Bounded gain 3 at 10% opacity enabled over disabled, considering the inspected outer-detail/background balance. This establishes a net preference despite previously reported slight noise distraction, not absence of noise or acceptance as a universal default.

### Q18 — Inner-corona detail preservation

Instruction: Keep ISO04 Bounded signed at Detail contrast 3 and 10% opacity, other enhancement filters off, full-resolution preview and 100% zoom. Pan to a bright inner-corona region just outside the limb and toggle ISO04 Active off/on, keeping presentation fixed and waiting for each update. Look for fine streaks merging into a smooth bright patch or losing separation when enabled.

Question: With ISO04 on, do inner-corona streaks remain distinct, become flattened/merged, or are you uncertain?

Answer (verbatim): “distinct”

Interpretation: User reports inner-corona streaks remain distinct with ISO04 Bounded gain 3 at 10% opacity. No flattening/merging was reported in the inspected region; other regions and stronger settings are not covered by this observation.

### Q19 — Tuned candidate versus Compatible

Instruction: Keep ISO04 alone active at 10% opacity, full-resolution preview, and all spatial/presentation settings fixed. Set global Filter normalization to Compatible. Compare the per-card Contrast choices Follow filter normalization (now Compatible) and Bounded signed at Detail contrast 3 (which overrides global normalization). Revisit the same inner-corona, outer-streamer and quiet-background regions at 100% zoom, waiting for each calculation.

Question: Overall, which do you prefer: Compatible, Bounded at 3, no meaningful difference, or uncertain?

Answer (verbatim): “bounded at 3”

Interpretation: User prefers the tuned ISO04 Bounded gain 3 configuration over Follow/Compatible overall at equal 10% opacity in the inspected regions. This is a preference between complete configurations, not equal-local-contrast evidence that the curve alone is better.

### Q20 — Tuned candidate versus Revised

Instruction: Keep ISO04 alone active at 10% opacity and all spatial/presentation settings fixed. Change global Filter normalization to Revised (experimental). Compare the per-card choices Follow filter normalization (now Revised) and Bounded signed at Detail contrast 3. Keep full-resolution preview and inspect the same inner-corona, outer-streamer and background regions at 100% zoom, waiting for each calculation.

Question: Overall, which do you prefer: Revised, Bounded at 3, no meaningful difference, or uncertain?

Answer (verbatim): “bounded at 3”

Interpretation: User prefers ISO04 Bounded gain 3 over Follow/Revised overall at equal 10% opacity. Together with Q19, this supports Bounded gain 3 as the preferred tested ISO04 configuration for this master and presentation, despite slight background-noise distraction.

### Q21 — Confirm the final candidate at the limb

Instruction: Select ISO04 Bounded signed, Detail contrast 3, Opacity 10%, with other enhancement filters off and full-resolution preview enabled. At 100% zoom inspect several parts of the lunar circumference, keeping all presentation settings fixed. Previous working-opacity limb confirmation was at gain 4, not this final gain 3.

Question: At this final setting, do you see a distinct narrow bright rim or dark halo: none, bright rim, dark halo, both, or uncertain?

Answer (verbatim): “none”

Interpretation: No distinct bright rim or dark halo reported in the inspected limb regions for the final ISO04 candidate, Bounded gain 3 at 10% opacity. This completes the individual ISO04 review, conditional on the user's unchanged presentation/spatial settings and this master.

### Q22 — Isolate ACHF Angular

Instruction: Retain ISO04's chosen controls for later combination but turn its Active off. Enable only ACHF Angular among enhancement filters. Set Angular Opacity to 10%, Contrast to Follow filter normalization, and global Filter normalization to Compatible. Keep spatial controls, source, geometry, colour and exposure unchanged, View Original off, full-resolution preview on and zoom 100%. Wait for processing, calculating manually if necessary.

Question: Is ACHF Angular now the only active enhancement filter at 10% opacity, with Follow/Compatible fully rendered?

Answer (verbatim): “yes”

Interpretation: User confirms the isolated Angular Follow/Compatible baseline at 10% opacity has rendered with full-resolution preview. ISO04's candidate settings are retained but inactive as instructed; app state has not been independently inspected.

### Q23 — Angular Compatible limb at working opacity

Instruction: Keep Angular alone active at 10% opacity, Follow/Compatible, full-resolution preview and 100% zoom. Inspect several parts of the lunar edge for a distinct narrow bright rim or dark halo, keeping all other settings fixed.

Question: What do you see: none, bright rim, dark halo, both, or uncertain?

Answer (verbatim): “none”

Interpretation: No distinct narrow bright rim or dark halo reported for Angular Follow/Compatible at 10% opacity in the inspected limb regions. No full-opacity stress test or filter-off attribution was needed for this absence observation.

### Q24 — Angular Compatible versus Bounded

Instruction: Keep Angular alone active at 10% opacity, global normalization Compatible, full-resolution preview and 100% zoom. Compare per-card Follow filter normalization with Bounded signed at Detail contrast 4, waiting for each calculation. Inspect the same outer-streamer and quiet-background regions; keep spatial and presentation settings fixed.

Question: Which gives the better overall detail/noise balance: Compatible, Bounded at 4, no meaningful difference, or uncertain?

Answer (verbatim): “bounded at 4”

Interpretation: User prefers Angular Bounded gain 4 over Follow/Compatible for overall detail/noise balance at 10% opacity in the inspected regions. Absolute noise acceptance and comparison with Revised remain pending.

### Q25 — Angular candidate noise acceptance

Instruction: Leave Angular alone active at 10% opacity, Bounded signed, Detail contrast 4, full-resolution preview and 100% zoom. Inspect the same quiet-background patch without changing presentation.

Question: Is the background noise acceptable, slightly distracting, clearly distracting, or uncertain?

Answer (verbatim): “slightly distracting”

Interpretation: Angular Bounded gain 4 at 10% opacity has slightly distracting background noise. Its preference over Compatible does not establish absolute noise acceptance. Test gain 3 at fixed opacity before recommending a setting.

### Q26 — Angular lower-gain balance

Instruction: Keep Angular alone active at 10% opacity, Bounded signed, full-resolution preview and 100% zoom. Compare Detail contrast 3 against 4 in the same outer-streamer and quiet-background regions, waiting for each calculation and keeping all other settings fixed.

Question: Which gives the better detail/noise balance: contrast 3, contrast 4, no meaningful difference, or uncertain?

Answer (verbatim): “3. for the next questions, give me a selectable list if possible”

Interpretation: User prefers Angular Bounded gain 3 over 4 at 10% opacity. Use selectable answers for subsequent questions, one question at a time. Noise acceptance at gain 3 is not yet established.

### Q27 — Angular gain 2 versus 3

Instruction: Keep Angular alone active, Bounded signed at 10% opacity, full-resolution preview and 100% zoom. Compare Detail contrast 2 against 3 in the same background and outer-streamer regions, waiting for each calculation. Keep all other settings fixed.

Question: Which gives the better detail/noise balance: contrast 2, contrast 3, no meaningful difference, or uncertain?

Answer (verbatim): “Contrast 3”

Interpretation: Angular Bounded gain 3 is preferred over both tested neighbors, 2 and 4, at 10% opacity. Absolute noise acceptance remains unconfirmed.

### Q28 — Angular noise at gain 3

Instruction: Leave Angular alone active at Bounded signed, Detail contrast 3, Opacity 10%, full-resolution preview and 100% zoom. Inspect the same quiet-background patch without changing presentation.

Question: Is the remaining background noise acceptable, slightly distracting, clearly distracting, or uncertain?

Answer (verbatim): “Slightly distracting”

Interpretation: Angular Bounded gain 3 at 10% opacity still has slightly distracting background noise. Relative gain preference does not imply full noise acceptance. Check whether including the candidate has a net visual benefit.

### Q29 — Angular candidate versus off

Instruction: Keep Angular Bounded signed, Detail contrast 3, Opacity 10%, other enhancement filters off, full-resolution preview and 100% zoom. Compare Angular Active on/off in the same outer-streamer and quiet-background regions. Wait for updates and keep all other settings fixed.

Question: Overall, do you prefer Angular on, Angular off, no meaningful difference, or uncertain?

Answer (verbatim): “Angular on”

Interpretation: User prefers the Angular Bounded gain-3, 10%-opacity candidate enabled over disabled, despite slightly distracting noise. This establishes a net preference in the inspected regions, not absence of artifacts or improved SNR.

### Q30 — Angular candidate limb check

Instruction: Keep Angular alone active at Bounded signed, Detail contrast 3 and Opacity 10%, with full-resolution preview and 100% zoom. Inspect several parts of the lunar edge, keeping presentation and all spatial settings unchanged.

Question: Do you see a distinct narrow bright rim or dark halo: none, bright rim, dark halo, both, or uncertain?

Answer (verbatim): “None”

Interpretation: No distinct narrow bright rim or dark halo reported for Angular Bounded gain 3 at 10% opacity in the inspected limb regions. This is not proof that all image regions are artifact-free.

### Q31 — Angular inner-corona detail preservation

Instruction: Keep Angular alone active at Bounded signed, Detail contrast 3 and Opacity 10%, full-resolution preview and 100% zoom. Inspect bright inner-corona streaks just outside the limb while toggling Angular Active off/on. Keep spatial/presentation settings fixed and wait for each update.

Question: With Angular on, do the streaks remain distinct, become flattened/merged, or are you uncertain?

Answer (verbatim): “Remain distinct”

Interpretation: User reports inner-corona streaks remain distinct with Angular Bounded gain 3 at 10% opacity. No flattening/merging reported in the inspected region.

### Q32 — Angular tuned candidate versus Compatible

Instruction: Keep Angular alone active at 10% opacity, full-resolution preview and 100% zoom. Set global Filter normalization to Compatible. Compare Angular Contrast Follow filter normalization against Bounded signed at Detail contrast 3 in the same inner-corona, outer-streamer and quiet-background regions. Keep other settings fixed and wait for each calculation.

Question: Overall, which do you prefer: Compatible, Bounded at 3, no meaningful difference, or uncertain?

Answer (verbatim): “Bounded at 3”

Interpretation: User prefers Angular Bounded gain 3 over Follow/Compatible overall at equal 10% opacity. This is a complete-configuration preference, not an equal-local-contrast comparison.

### Q33 — Angular tuned candidate versus Revised

Instruction: Keep Angular alone active at 10% opacity, full-resolution preview and 100% zoom. Set global Filter normalization to Revised (experimental). Compare Angular Contrast Follow filter normalization against Bounded signed at Detail contrast 3 in the same inner-corona, outer-streamer and quiet-background regions. Keep all other settings fixed and wait for each calculation.

Question: Overall, which do you prefer: Revised, Bounded at 3, no meaningful difference, or uncertain?

Answer (verbatim): “Bounded at 3”

Interpretation: Angular Bounded gain 3 at 10% opacity is preferred over Follow/Revised, completing the tested mapping comparisons. Slightly distracting noise remains an acknowledged tradeoff. This supports a provisional setting for this master, not a universal default.

### Q34 — Isolate ACHF ISO01

Instruction: Leave Angular's chosen controls at Bounded signed, Detail contrast 3 and Opacity 10%, but disable Angular Active. Enable only ACHF ISO01, at Opacity 10%, Contrast Follow filter normalization, with global Filter normalization Compatible. Keep full-resolution preview on, View Original off, spatial/presentation settings unchanged and wait for processing. Use Expert mode to access ISO01 if needed.

Question: Is the isolated ISO01 Follow/Compatible baseline at 10% opacity fully rendered?

Answer (verbatim): “Yes”

Interpretation: User confirms the isolated ISO01 Follow/Compatible baseline at 10% opacity has rendered with full-resolution preview. No ISO01 visual observations recorded yet.

### Q35 — ISO01 Compatible limb check

Instruction: Keep ISO01 alone active at 10% opacity, Follow/Compatible and full-resolution preview. At 100% zoom inspect several parts of the lunar edge without changing other settings.

Question: Do you see a distinct narrow bright rim or dark halo: none, bright rim, dark halo, both, or uncertain?

Answer (verbatim): “None”

Interpretation: No distinct narrow bright rim or dark halo reported for ISO01 Follow/Compatible at 10% opacity in the inspected limb regions.

### Q36 — ISO01 Compatible versus Bounded

Instruction: Keep ISO01 alone active at 10% opacity, global normalization Compatible, full-resolution preview and 100% zoom. Compare ISO01 Contrast Follow filter normalization against Bounded signed at Detail contrast 2 (ISO01's maximum). Inspect the same outer-streamer and quiet-background regions, keeping other settings fixed and waiting for each calculation.

Question: Which gives the better overall detail/noise balance: Compatible, Bounded at 2, no meaningful difference, or uncertain?

Answer (verbatim): “Bounded at 2”

Interpretation: User prefers ISO01 Bounded gain 2 over Follow/Compatible for overall detail/noise balance at 10% opacity in the inspected regions. Absolute noise acceptance remains unconfirmed.

### Q37 — ISO01 candidate noise acceptance

Instruction: Leave ISO01 alone active at Bounded signed, Detail contrast 2, Opacity 10%, full-resolution preview and 100% zoom. Inspect the same quiet-background patch without changing presentation.

Question: Is the background noise acceptable, slightly distracting, clearly distracting, or uncertain?

Answer (verbatim): “Acceptable”

Interpretation: User accepts the visible background noise of ISO01 Bounded gain 2 at 10% opacity in the inspected patch. No noise-driven gain reduction is currently indicated; candidate limb/detail checks and comparison with Revised remain pending.

### Q38 — ISO01 candidate limb check

Instruction: Keep ISO01 alone active at Bounded signed, Detail contrast 2 and Opacity 10%, full-resolution preview and 100% zoom. Inspect several parts of the lunar edge, keeping all spatial and presentation settings fixed.

Question: Do you see a distinct narrow bright rim or dark halo: none, bright rim, dark halo, both, or uncertain?

Answer (verbatim): “None”

Interpretation: No distinct narrow bright rim or dark halo reported for ISO01 Bounded gain 2 at 10% opacity in the inspected limb regions. This does not establish absence of all defects elsewhere.

### Q39 — ISO01 inner-corona detail preservation

Instruction: Keep ISO01 alone active at Bounded signed, Detail contrast 2 and Opacity 10%, full-resolution preview and 100% zoom. Inspect bright inner-corona streaks just outside the limb while toggling ISO01 Active off/on. Keep all other settings fixed and wait for each update.

Question: With ISO01 on, do those streaks remain distinct, become flattened/merged, or are you uncertain?

Answer (verbatim): “Remain distinct”

Interpretation: User reports inner-corona streaks remain distinct with ISO01 Bounded gain 2 at 10% opacity. No flattening/merging reported in the inspected region.

### Q40 — ISO01 candidate versus Revised

Instruction: Keep ISO01 alone active at 10% opacity, full-resolution preview and 100% zoom. Set global Filter normalization to Revised (experimental). Compare ISO01 Contrast Follow filter normalization against Bounded signed at Detail contrast 2 in the same inner-corona, outer-streamer and quiet-background regions. Keep all other settings fixed and wait for each calculation.

Question: Overall, which do you prefer: Revised, Bounded at 2, no meaningful difference, or uncertain?

Answer (verbatim): “No meaningful difference”

Interpretation: User reports no meaningful overall visual difference between ISO01 Follow/Revised and Bounded gain 2 at equal 10% opacity. Do not declare Bounded the winner over Revised. Bounded was preferred over Compatible; this does not independently establish a direct Revised-versus-Compatible ranking.

### Q41 — ISO01 candidate versus off

Instruction: Select ISO01 Bounded signed at Detail contrast 2 and Opacity 10% as the already inspected reference, with other enhancement filters off. Keep full-resolution preview, 100% zoom and all other settings fixed. Toggle ISO01 Active off/on in the same outer-streamer and quiet-background regions, waiting for updates.

Question: Overall, do you prefer ISO01 on, ISO01 off, no meaningful difference, or uncertain?

Answer (verbatim): “ISO01 on”

Interpretation: User prefers the isolated ISO01 Bounded gain-2, 10%-opacity candidate enabled over disabled. Its contribution alongside other ACHF variants remains untested. Revised remains visually tied with Bounded, not inferior.

### Q42 — Does ISO01 add value alongside ISO04?

Instruction: Enable ISO04 at its chosen Bounded signed, Detail contrast 3, Opacity 10%. Leave Angular and all other enhancement filters off. Keep ISO01 at Bounded signed, Detail contrast 2, Opacity 10% as the previously inspected reference. With full-resolution preview, 100% zoom and presentation fixed, toggle only ISO01 Active off/on. Compare the same inner-corona, outer-streamer and quiet-background regions, waiting for updates.

Question: Which gives the better overall detail/noise balance: ISO04 alone, ISO04 plus ISO01, no meaningful difference, or uncertain?

Answer (verbatim): “ISO04 alone”

Interpretation: User prefers ISO04 alone over ISO04 plus ISO01 at the tested settings. ISO01's individual benefit does not translate into a preferred addition to ISO04. The answer does not establish whether redundancy, noise or another effect caused that preference, nor rule out other ISO01 settings.

### Q43 — Does Angular add value alongside ISO04?

Instruction: Disable ISO01. Keep ISO04 active at Bounded signed, Detail contrast 3, Opacity 10%. Keep all other enhancement filters off except Angular for the comparison. Set Angular to its chosen Bounded signed, Detail contrast 3, Opacity 10%, then toggle only Angular Active off/on. Keep full-resolution preview, 100% zoom and presentation fixed; inspect the same inner-corona, outer-streamer and quiet-background regions, waiting for updates.

Question: Which gives the better overall detail/noise balance: ISO04 alone, ISO04 plus Angular, no meaningful difference, or uncertain?

Answer (verbatim): “ISO04 plus Angular”

Interpretation: User prefers adding Angular to ISO04 at Bounded gain 3 and 10% opacity each. This supports the pair over ISO04 alone, but does not establish absolute combined-noise acceptance or absence of artifacts.

### Q44 — Combined background-noise acceptance

Instruction: Leave only ISO04 and Angular active, both Bounded signed, Detail contrast 3 and Opacity 10%. Keep full-resolution preview, 100% zoom and all presentation settings fixed. Inspect the same quiet-background patch with both enabled.

Question: Is the combined background noise acceptable, slightly distracting, clearly distracting, or uncertain?

Answer (verbatim): “Slightly distracting”

Interpretation: The preferred ISO04-plus-Angular pair at gain 3 and 10% opacity each retains slightly distracting background noise. Net preference over ISO04 alone does not imply full noise acceptance. Test one component's opacity at a time.

### Q45 — Reduce Angular contribution only

Instruction: Keep ISO04 fixed at Bounded signed, Detail contrast 3, Opacity 10%. Keep Angular Bounded signed at Detail contrast 3 and compare only its Opacity 5% versus 10%. Other enhancement filters stay off. Use full-resolution preview at 100% zoom and inspect the same outer-streamer and quiet-background regions, waiting for updates and keeping presentation fixed.

Question: Which gives the better overall detail/noise balance: Angular 5%, Angular 10%, no meaningful difference, or uncertain?

Answer (verbatim): “Angular 10%”

Interpretation: With ISO04 fixed at gain 3/10%, Angular gain 3 at 10% is preferred over 5% for overall detail/noise balance. The lower contribution did not yield a preferred balance; slightly distracting noise remains an acknowledged cost of the current pair. Do not infer absolute noise acceptance.

### Q46 — Combined limb check

Instruction: Leave only ISO04 and Angular active, both Bounded signed, Detail contrast 3, Opacity 10%. With full-resolution preview and 100% zoom, inspect several parts of the lunar circumference. Keep all other settings unchanged.

Question: Do you see a distinct narrow bright rim or dark halo: none, bright rim, dark halo, both, or uncertain?

Answer (verbatim): “None”

Interpretation: No distinct narrow bright rim or dark halo reported for ISO04 plus Angular, both Bounded gain 3 at 10% opacity, in inspected limb regions. This does not establish absence of other defects.

### Q47 — Combined inner-corona detail check

Instruction: Keep only ISO04 and Angular active, both Bounded signed, Detail contrast 3 and Opacity 10%. With full-resolution preview and 100% zoom, inspect bright inner-corona streaks just outside the limb. Compare the pair against ISO04 alone by toggling only Angular, waiting for updates and keeping presentation fixed.

Question: With both filters on, do the streaks remain distinct, become flattened/merged, or are you uncertain?

Answer (verbatim): “Remain distinct”

Interpretation: User reports inner-corona streaks remain distinct with ISO04 and Angular together at Bounded gain 3 and 10% opacity each. No merging/flattening reported in the inspected region.

### Q48 — Whole-image acceptance of the ACHF candidate

Instruction: Enable both ISO04 and Angular at Bounded signed, Detail contrast 3 and Opacity 10%, with all other enhancement filters off. Keep full-resolution preview on and switch display zoom to Fit. Keep presentation fixed and inspect the whole composition. This is an overall presentation judgment, complementing the preceding native-pixel checks.

Question: Would you keep this pair as the provisional ACHF preset for this master, accepting the slight noise distraction, prefer further adjustment, reject it, or are you uncertain?

Answer (verbatim): “Keep this pair”

Interpretation: User accepts ISO04 plus Angular, each Bounded gain 3 at 10% opacity, as the provisional ACHF preset for this master, with slight noise distraction acknowledged. This is not authorization to change application defaults.

### Q49 — Capture the actual accepted settings

Instruction: Keep the accepted pair selected and save the app settings to a new JSON file named `ACHF-Visual-Review-ISO04-and-Angular-Bounded-3-Opacity-10.json`, without overwriting a previous recipe. Record its full path so presentation, geometry and spatial controls can be inspected alongside the answers.

Question: What is the full path of the saved JSON settings file?

Answer (verbatim): “/Volumes/Astro/Imágenes/CoronaHDR_RAW/CoronaHDR_Work/ACHF-Visual-Review-ISO04-and-Angular-Bounded-3-Opacity-10.json”

Verification: Read the v4 JSON and asserted approved source, ISO04/Angular enabled at Bounded/3/10%, ISO01/adaptive and all other enhancement filters disabled, and full-resolution preview enabled. Checks passed. Recipe SHA-256: `06ead45461c0b6934503385dcb59f3687a920c397f6045029d3830159275b543`.

Captured setup: center (2975,1660), radius 272 native px; ISO04 Gaussian sigmas [1,2,4,8,16] native px and final smoothing 1.5 px; Angular sigma 1 degree and final smoothing 4 native px. Input Linear; colour calibration on; sky/corona warmth both 0; green suppression off; background extraction off; original prominences off; PSB presentation on at EV 0. Global normalization Revised (overridden by the selected bounded mappings). Separate AEL statistics enabled; lunar exclusion on, guard 0, bright exclusion off. Display normalization range [695.68896484375,2399511.75]. Recipe records the final setup, not independent proof that every earlier comparison used identical presentation or zoom.

### Q50 — Next review segment

Question: Which filter should the guided review cover next: WOW noise reduction, NAFE limb/noise, Tangential, or pause here?

Answer (verbatim): “WOW noise reduction”

Interpretation: Begin with an isolated WOW baseline, then evaluate suppression versus faint-detail loss before testing its contribution alongside the accepted ACHF pair. Preserve the saved ACHF recipe and current presentation.

### Q51 — Isolated WOW baseline

Instruction: Disable ISO04 and Angular without changing their chosen settings. Enable only WOW, select AEL edge-aware (guided), set Opacity 10% and Noise reduction 0. Retain the saved eight scales and other spatial controls; keep full-resolution preview enabled, View Original off, and source, geometry, background and presentation unchanged. Wait for calculation.

Question: Is this isolated WOW baseline fully rendered?

Answer (verbatim): “Yes”

Interpretation: User confirms the isolated AEL edge-aware WOW baseline at 10% opacity, Noise reduction 0 and eight scales is rendered with full-resolution preview. No WOW visual judgment recorded yet.

### Q52 — WOW baseline background noise

Instruction: Keep only WOW active at AEL edge-aware (guided), Opacity 10%, Noise reduction 0 and eight scales. With full-resolution preview at 100% zoom, inspect the same quiet-background patch used earlier. Keep all other settings fixed.

Question: Is the background noise acceptable, slightly distracting, clearly distracting, or uncertain?

Answer (verbatim): “Clearly distracting”

Interpretation: Isolated WOW at 10% opacity and Noise reduction 0 has clearly distracting noise in the inspected background patch. A suppression comparison is warranted; no conclusion about the best strength or preservation of faint detail yet.

### Q53 — WOW Noise reduction 0 versus 1

Instruction: Keep only WOW active at AEL edge-aware (guided), Opacity 10% and eight scales, with full-resolution preview at 100% zoom. Compare only Noise reduction 0 versus 1, waiting for each calculation. Inspect the same quiet background and faint outer streamer, keeping presentation and spatial settings fixed. Consider loss of faint streaks as well as reduced grain.

Question: Which gives the better overall detail/noise balance: Noise reduction 0, Noise reduction 1, no meaningful difference, or uncertain?

Answer (verbatim): “Noise reduction 1”

Interpretation: User prefers WOW Noise reduction 1 over 0 at 10% opacity for overall detail/noise balance. This does not yet establish acceptable residual noise or absence of faint-detail loss.

### Q54 — WOW Noise reduction 1 versus 2

Instruction: Keep only AEL edge-aware WOW active at Opacity 10%, eight scales, full-resolution preview and 100% zoom. Compare only Noise reduction 1 versus 2 in the same quiet background and faint outer-streamer regions. Wait for calculation and keep all other settings fixed. Look for faint streaks disappearing or becoming less distinct as well as reduced grain.

Question: Which gives the better overall detail/noise balance: Noise reduction 1, Noise reduction 2, no meaningful difference, or uncertain?

Answer (verbatim): “Noise reduction 2”

Interpretation: User prefers WOW Noise reduction 2 over 1 at 10% opacity for overall detail/noise balance. Residual-noise acceptance and specific faint-detail retention have not yet been separately confirmed.

### Q55 — WOW Noise reduction 2 versus 3

Instruction: Keep only AEL edge-aware WOW active at Opacity 10%, eight scales, full-resolution preview and 100% zoom. Compare only Noise reduction 2 versus 3 in the same quiet background and faint outer-streamer regions, waiting for each calculation. Keep all other settings fixed and consider faint streaks disappearing or losing separation as well as reduced grain.

Question: Which gives the better overall detail/noise balance: Noise reduction 2, Noise reduction 3, no meaningful difference, or uncertain?

Answer (verbatim): “Noise reduction 3”

Interpretation: User prefers WOW Noise reduction 3 over 2 at 10% opacity for overall detail/noise balance. This does not establish absolute noise acceptance or preservation of all faint detail. Check residual noise before escalating strength further.

### Q56 — WOW noise acceptance at strength 3

Instruction: Leave only AEL edge-aware WOW active at Opacity 10%, Noise reduction 3 and eight scales. Keep full-resolution preview and 100% zoom; inspect the same quiet-background patch without changing presentation.

Question: Is the remaining background noise acceptable, slightly distracting, clearly distracting, or uncertain?

Answer (verbatim): “Acceptable”

Interpretation: User accepts residual background noise at WOW Noise reduction 3 and 10% opacity in the inspected patch. No noise-driven escalation beyond 3 is currently needed. Specific faint-detail retention remains unconfirmed.

### Q57 — WOW faint-detail retention

Instruction: Keep only AEL edge-aware WOW active at Opacity 10%, eight scales, full-resolution preview and 100% zoom. In the same faint outer-streamer region, compare Noise reduction 0 against 3, waiting for each calculation and keeping presentation fixed. Judge identifiable streaks rather than grain; this is visual retention, not proof that unsuppressed structure is solar.

Question: At Noise reduction 3, is identifiable faint streamer detail retained, slightly reduced but acceptable, substantially lost, or uncertain?

Answer (verbatim): “Slightly reduced but acceptable”

Interpretation: Relative to suppression off, the user reports a slight but acceptable reduction of identifiable faint streamer detail at WOW Noise reduction 3, 10% opacity. This is an accepted visual tradeoff, not evidence of lossless denoising or improved astronomical SNR.

### Q58 — WOW candidate limb check

Instruction: Leave only AEL edge-aware WOW active at Opacity 10%, Noise reduction 3 and eight scales. With full-resolution preview and 100% zoom inspect several parts of the lunar edge, keeping other settings fixed.

Question: Do you see a distinct narrow bright rim or dark halo: none, bright rim, dark halo, both, or uncertain?

Answer (verbatim): “None”

Interpretation: No distinct narrow bright rim or dark halo reported for isolated AEL edge-aware WOW at 10% opacity, Noise reduction 3 and eight scales in inspected limb regions. Other defects and regions remain unassessed.

### Q59 — WOW inner-corona detail preservation

Instruction: Keep only AEL edge-aware WOW active at Opacity 10%, Noise reduction 3 and eight scales, with full-resolution preview at 100% zoom. Inspect bright inner-corona streaks just outside the limb while toggling WOW Active off/on. Keep all other settings fixed and wait for each update.

Question: With WOW on, do those streaks remain distinct, become flattened/merged, or are you uncertain?

Answer (verbatim): “Remain distinct”

Interpretation: User reports bright inner-corona streaks remain distinct with isolated WOW at Noise reduction 3, 10% opacity and eight scales. No flattening/merging reported in the inspected region. Its contribution to the accepted ACHF pair remains untested.

### Q60 — WOW contribution alongside the accepted ACHF pair

Instruction: Re-enable ISO04 and Angular at their accepted Bounded signed, Detail contrast 3 and Opacity 10% each. Keep ISO01 and all other enhancement filters off. Leave WOW at AEL edge-aware (guided), Noise reduction 3, Opacity 10% and eight scales. With full-resolution preview at 100% zoom and all presentation settings fixed, toggle only WOW Active off/on. Compare the same inner-corona, outer-streamer and quiet-background regions, waiting for updates. WOW suppression applies to WOW's own layer, not to noise from the ACHF layers.

Question: Which gives the better overall detail/noise balance: ACHF pair alone, ACHF pair plus WOW, no meaningful difference, or uncertain?

Answer (verbatim): “ACHF pair plus WOW”

Interpretation: User prefers adding WOW (AEL edge-aware, eight scales, Noise reduction 3, opacity 10%) to the accepted ACHF pair for overall detail/noise balance. Combined noise acceptance and artifact checks remain unconfirmed; WOW suppression does not denoise the separate ACHF layers.

### Q61 — ACHF-plus-WOW combined noise

Instruction: Leave ISO04 and Angular active, each Bounded signed, Detail contrast 3 and Opacity 10%, plus WOW at AEL edge-aware, eight scales, Noise reduction 3 and Opacity 10%. Keep other enhancement filters off, full-resolution preview on and zoom at 100%. Inspect the same quiet-background patch without changing presentation.

Question: Is the combined background noise acceptable, slightly distracting, clearly distracting, or uncertain?

Answer (verbatim): “Slightly distracting”

Interpretation: The preferred ACHF-plus-WOW candidate retains slightly distracting background noise. The ACHF pair alone received the same qualitative rating earlier, but this is not a direct measurement of equal noise. Do not assume stronger WOW suppression will remove noise from the ACHF layers.

### Q62 — ACHF-plus-WOW limb check

Instruction: Leave ISO04 and Angular active at Bounded signed, Detail contrast 3 and Opacity 10% each, plus WOW at AEL edge-aware, eight scales, Noise reduction 3 and Opacity 10%. Other enhancement filters remain off. With full-resolution preview and 100% zoom, inspect several parts of the lunar edge, keeping other settings fixed.

Question: Do you see a distinct narrow bright rim or dark halo: none, bright rim, dark halo, both, or uncertain?

Answer (verbatim): “None”

Interpretation: No distinct narrow bright rim or dark halo reported in inspected regions for the ACHF pair plus WOW at the candidate settings. Other defects and regions are not excluded by this observation.

### Q63 — ACHF-plus-WOW inner-corona detail

Instruction: Keep ISO04 and Angular at Bounded signed, Detail contrast 3 and Opacity 10% each. Keep WOW at AEL edge-aware, eight scales, Noise reduction 3 and Opacity 10%; other enhancement filters remain off. At full-resolution preview and 100% zoom, inspect bright inner-corona streaks while toggling only WOW off/on, waiting for updates and keeping presentation fixed.

Question: With all three layers on, do the streaks remain distinct, become flattened/merged, or are you uncertain?

Answer (verbatim): “Remain distinct”

Interpretation: User reports bright inner-corona streaks remain distinct with the accepted ACHF pair plus candidate WOW enabled. No flattening/merging reported in the inspected region; whole-image acceptance remains pending.

### Q64 — Whole-image acceptance of ACHF plus WOW

Instruction: Enable ISO04 and Angular at Bounded signed, Detail contrast 3 and Opacity 10% each, plus WOW at AEL edge-aware, eight scales, Noise reduction 3 and Opacity 10%. Keep other enhancement filters off, full-resolution preview on and presentation fixed. Switch zoom to Fit and inspect the whole composition.

Question: Would you keep this three-layer combination as the provisional preset for this master, accepting the slight noise distraction and the previously reported slight faint-detail loss from WOW suppression, prefer further adjustment, prefer the ACHF pair alone, or are you uncertain?

Answer (verbatim): “Keep all three”

Interpretation: User accepts ISO04 plus Angular plus WOW as the provisional combined preset for this master, with the stated noise/detail tradeoffs. This is not authorization to change application defaults. Preserve a separate recipe without overwriting the earlier ACHF-only reference.

### Q65 — Save the accepted three-layer recipe

Instruction: Keep the accepted three layers enabled and save app settings as a new JSON named `Visual-Review-ISO04-Angular-WOW-NR3-Opacity10.json`. Retain the earlier ACHF-only recipe; do not overwrite it. Provide the full path so the actual combined controls can be verified.

Question: What is the full path of the newly saved JSON file?

Answer (verbatim): “/Volumes/Astro/Imágenes/CoronaHDR_RAW/CoronaHDR_Work/Visual-Review-ISO04-Angular-WOW-NR3-Opacity10.json”

Verification: Read the saved v4 JSON and asserted approved source, ISO04/Angular Bounded gain 3 at 10% each, WOW AEL edge-aware (`ael_bilateral`), eight scales, Noise reduction 3 and opacity 10%, other enhancement filters disabled, and full-resolution preview enabled. All assertions passed. SHA-256: `82de6bd6e89bbca455c67b09960d202ccbe9170c032dc4f0b45700b671383501`.

Comparison with Q49 recipe: geometry and non-control/non-section settings unchanged. Only saved control differences are WOW Noise reduction 0 → 3 (stored ticks 0 → 30) and WOW opacity 4 → 10. WOW section activation also changes as expected. Earlier ACHF-only recipe remains readable. This verifies the saved final state, not each earlier visual comparison or a reload/export roundtrip.

### Q66 — Next review segment

Question: Which segment should we test next: NAFE limb/noise, Tangential detail, or pause and review conclusions?

Answer (verbatim): “NAFE limb and noise”

Interpretation: Review NAFE in isolation, then test its contribution to the accepted combination. Compare original and Limb-aware under fixed settings on the approved source; do not assume previous ring findings on other inputs apply unchanged.

### Q67 — Isolated original NAFE baseline

Instruction: Disable ISO04, Angular and WOW, retaining their accepted settings. Enable only NAFE. Select AEL original, Opacity 40%, Automatic noise sigma (AEL), 129 × 129 native-pixel window, Noise multiplier 12, Noise region starts 4 R and Noise residual sigma 4 native px. Keep the approved source, geometry and presentation unchanged, View Original off and full-resolution preview on. Wait for calculation. These noise/window controls match the captured recipe; only method, opacity and activation change.

Question: Has the isolated original NAFE baseline finished rendering?

Answer (verbatim): “Yes”

Interpretation: User confirms isolated AEL original NAFE at 40% opacity has rendered with the specified automatic-noise/window settings and full-resolution preview. No visual observations yet for this baseline.

### Q68 — Original NAFE limb check

Instruction: Keep only NAFE active at AEL original, Opacity 40%, and the baseline settings. At full-resolution preview and 100% zoom, inspect several parts of the lunar circumference. Keep geometry and presentation unchanged. Observe a distinct narrow bright rim/dark halo separately from the broader coronal glow; attribution will require a filter-off comparison if a defect is reported.

Question: Do you see a distinct narrow bright rim or dark halo: none, bright rim, dark halo, both, or uncertain?

Answer (verbatim): “None”

Interpretation: No distinct narrow bright rim or dark halo reported for original NAFE at 40% opacity in inspected regions of the approved master. This does not rule out a higher-opacity effect or defects elsewhere.

### Q69 — Original versus Limb-aware NAFE

Instruction: Keep only NAFE active at 40% opacity and the same noise/window settings, full-resolution preview and 100% zoom. Compare AEL original against Limb-aware (experimental), waiting for each calculation. Inspect the same inner corona, outer streamer and quiet background, keeping geometry and presentation fixed.

Question: Which gives the better overall detail/noise balance: AEL original, Limb-aware, no meaningful difference, or uncertain?

Answer (verbatim): “No meaningful difference”

Interpretation: User reports no meaningful overall difference between original and Limb-aware NAFE at 40% opacity under the current setup. Do not declare either superior or infer equivalence at other settings. Retain AEL original as the baseline reference, not as a proven quality winner.

### Q70 — NAFE background-noise acceptance

Instruction: Select AEL original NAFE, leaving only NAFE active at 40% opacity and all baseline noise/window settings unchanged. Keep full-resolution preview at 100% zoom and inspect the same quiet-background patch without changing presentation.

Question: Is the background noise acceptable, slightly distracting, clearly distracting, or uncertain?

Answer (verbatim): “Acceptable”

Interpretation: Original NAFE at 40% opacity has acceptable visible noise in the inspected background patch. No noise-driven tuning is indicated; whether it contributes to the accepted preset remains untested.

### Q71 — NAFE contribution alongside the accepted preset

Instruction: Re-enable ISO04 and Angular at Bounded signed, Detail contrast 3 and Opacity 10% each, plus WOW at AEL edge-aware, eight scales, Noise reduction 3 and Opacity 10%. Keep ISO01 and all remaining enhancement filters off. Leave NAFE at AEL original, Opacity 40% and its baseline noise/window settings. In full-resolution preview at 100% zoom, toggle only NAFE Active off/on while comparing the same inner corona, outer streamer and quiet background. Wait for updates and keep presentation fixed.

Question: Which gives the better overall balance: accepted three-layer preset alone, preset plus NAFE, no meaningful difference, or uncertain?

Answer (verbatim): “Preset plus NAFE”

Interpretation: User prefers adding AEL original NAFE at 40% opacity to the accepted ISO04/Angular/WOW preset at the tested settings. Combined limb, noise, inner-detail and whole-image acceptance are not yet confirmed.

### Q72 — Preset-plus-NAFE limb check

Instruction: Leave ISO04 and Angular at Bounded signed, Detail contrast 3 and Opacity 10% each, WOW at AEL edge-aware/eight scales/Noise reduction 3/Opacity 10%, and NAFE at AEL original/Opacity 40% with baseline noise/window settings. Keep other enhancement filters off. In full-resolution preview at 100% zoom inspect several parts of the lunar edge, keeping geometry and presentation unchanged.

Question: Do you see a distinct narrow bright rim or dark halo: none, bright rim, dark halo, both, or uncertain?

Answer (verbatim): “None”

Interpretation: No distinct narrow bright rim or dark halo reported for the four-layer candidate in inspected limb regions. This does not establish absence of all defects or cover uninspected regions.

### Q73 — Preset-plus-NAFE background noise

Instruction: Keep ISO04 and Angular at Bounded signed, Detail contrast 3 and Opacity 10% each, WOW at AEL edge-aware/eight scales/Noise reduction 3/Opacity 10%, and NAFE at AEL original/Opacity 40% with baseline noise/window settings. Other enhancement filters remain off. With full-resolution preview at 100% zoom, inspect the same quiet-background patch without changing presentation.

Question: Is the combined background noise acceptable, slightly distracting, clearly distracting, or uncertain?

Answer (verbatim): “Slightly distracting”

Interpretation: The four-layer candidate has slightly distracting background noise. The same qualitative rating was given to the three-layer preset, but this does not establish equal noise or noise reduction from adding NAFE.

### Q74 — Preset-plus-NAFE inner-corona detail

Instruction: Keep ISO04 and Angular at Bounded signed, Detail contrast 3 and Opacity 10% each, WOW at AEL edge-aware/eight scales/Noise reduction 3/Opacity 10%, and NAFE at AEL original/Opacity 40% with baseline noise/window settings. Other enhancement filters remain off. At full-resolution preview and 100% zoom inspect bright inner-corona streaks while toggling only NAFE Active off/on. Keep presentation fixed and wait for updates.

Question: With all four layers on, do those streaks remain distinct, become flattened/merged, or are you uncertain?

Answer (verbatim): “Remain distinct”

Interpretation: Bright inner-corona streaks remain distinct with the four-layer candidate in the inspected region. No flattening/merging was reported. Whole-image acceptance remains pending.

### Q75 — Four-layer whole-image acceptance

Instruction: Leave ISO04 and Angular active at Bounded signed, Detail contrast 3 and Opacity 10% each, WOW at AEL edge-aware/eight scales/Noise reduction 3/Opacity 10%, and NAFE at AEL original/Opacity 40% with baseline noise/window settings. Other enhancement filters remain off. Keep full-resolution preview on, switch zoom to Fit and inspect the whole composition without changing presentation.

Question: Would you keep all four as the provisional preset for this master, accepting the slight background-noise distraction, prefer further adjustment, prefer the previous three-layer preset, or are you uncertain?

Answer (verbatim): “Keep all four”

Interpretation: User accepts the four-layer combination as the provisional preset for this master, acknowledging slight background-noise distraction. This does not authorize application-default changes or establish general suitability. Preserve earlier accepted recipes as comparison references.

### Q76 — Save the accepted four-layer recipe

Instruction: Leave the accepted four layers enabled and save app settings to a new JSON named `Visual-Review-ISO04-Angular-WOW-NR3-NAFE-Original40.json`. Keep the earlier ACHF-only and three-layer recipes unchanged. Provide the full path so the final saved controls can be verified.

Question: What is the full path of the newly saved JSON file?

Answer (verbatim): “/Volumes/Astro/Imágenes/CoronaHDR_RAW/CoronaHDR_Work/Visual-Review-ISO04-Angular-WOW-NR3-NAFE-Original40.json”

Verification: Read v4 JSON and asserted approved source; ISO04/Angular Bounded gain 3 at 10% each; WOW AEL edge-aware, eight scales, Noise reduction 3 and opacity 10%; NAFE original at 40%, automatic sigma, window 129, noise multiplier 12, region 4 R and residual sigma 4 native px; all other enhancement filters off; full-resolution preview on. All passed. Recipe SHA-256: `c002814890ccbe52518663460dfb460e2ad9b2ef60d6a7dea9e8e400c8471faf`.

Compared with the retained three-layer recipe, changed controls are NAFE method Limb-aware → AEL original and opacity 100 → 40; NAFE activation changes as intended. Geometry and other non-control/non-section settings are unchanged. This verifies the final saved state, not a reload/export roundtrip or all earlier observations.

### Q77 — Isolated Tangential baseline

Instruction: Disable ISO04, Angular, WOW and NAFE, retaining their accepted settings. In Standard/Expert enable only Tangential, set Opacity 10%, Contrast Follow filter normalization and global Filter normalization Compatible. Leave its spatial/gain controls as saved; keep approved source, geometry and presentation unchanged, full-resolution preview on and View Original off. Wait for calculation.

Question: Has this isolated Tangential baseline finished rendering?

Answer (verbatim): “Yes”

Interpretation: User confirms isolated Tangential at 10% opacity, Follow/Compatible, full-resolution preview and unchanged remaining controls has rendered. No visual findings for this baseline yet.

### Q78 — Tangential Compatible limb check

Instruction: Keep only Tangential active at 10% opacity, Follow/Compatible and full-resolution preview. At 100% zoom inspect several parts of the lunar edge, keeping other settings unchanged.

Question: Do you see a distinct narrow bright rim or dark halo: none, bright rim, dark halo, both, or uncertain?

Answer (verbatim): “None”

Interpretation: No distinct narrow bright rim or dark halo reported for Tangential Follow/Compatible at 10% opacity in inspected limb regions.

### Q79 — Tangential Compatible versus Source-relative

Instruction: Keep only Tangential active at 10% opacity, global normalization Compatible, full-resolution preview and 100% zoom. Compare its Contrast selector Follow filter normalization against Source-relative (experimental), waiting for each calculation. Keep gain and spatial controls fixed and inspect the same outer-streamer and quiet-background regions without changing presentation.

Question: Which gives the better overall detail/noise balance: Compatible, Source-relative, no meaningful difference, or uncertain?

Answer (verbatim): “Source-relative”

Interpretation: User prefers Tangential Source-relative over Follow/Compatible at 10% opacity for overall detail/noise balance in inspected regions. Absolute noise acceptance and comparison with Revised remain pending.

### Q80 — Tangential Source-relative background noise

Instruction: Leave only Tangential active at 10% opacity and Source-relative contrast, with gain/spatial controls unchanged. With full-resolution preview at 100% zoom, inspect the same quiet-background patch without changing presentation.

Question: Is the background noise acceptable, slightly distracting, clearly distracting, or uncertain?

Answer (verbatim): “Acceptable”

Interpretation: User accepts the background noise of isolated Tangential Source-relative at 10% opacity in the inspected patch. No noise-driven tuning is indicated; candidate limb/detail checks and comparison with Revised remain pending.

### Q81 — Tangential Source-relative limb check

Instruction: Keep only Tangential active at 10% opacity and Source-relative contrast, with gain/spatial controls and presentation unchanged. With full-resolution preview at 100% zoom inspect several parts of the lunar edge.

Question: Do you see a distinct narrow bright rim or dark halo: none, bright rim, dark halo, both, or uncertain?

Answer (verbatim): “None”

Interpretation: No distinct narrow bright rim or dark halo reported for isolated Tangential Source-relative at 10% opacity in inspected limb regions. This does not establish absence of all defects.

### Q82 — Tangential inner-corona detail preservation

Instruction: Keep only Tangential active at Source-relative contrast and Opacity 10%, with gain/spatial controls unchanged. At full-resolution preview and 100% zoom inspect bright inner-corona streaks just outside the limb while toggling Tangential Active off/on. Keep presentation fixed and wait for each update.

Question: With Tangential on, do those streaks remain distinct, become flattened/merged, or are you uncertain?

Answer (verbatim): “Remain distinct”

Interpretation: User reports bright inner-corona streaks remain distinct with isolated Tangential Source-relative at 10% opacity. No flattening/merging reported in the inspected region.

### Q83 — Tangential Source-relative versus Revised

Instruction: Keep Tangential alone active at Opacity 10%, full-resolution preview and 100% zoom. Set global Filter normalization to Revised (experimental). Compare Tangential Contrast Follow filter normalization (now Revised) against Source-relative (experimental), waiting for each calculation. Inspect the same inner-corona, outer-streamer and quiet-background regions with gain/spatial controls and presentation fixed.

Question: Overall, which do you prefer: Revised, Source-relative, no meaningful difference, or uncertain?

Answer (verbatim): “Source-relative”

Interpretation: User prefers isolated Tangential Source-relative over Follow/Revised at 10% opacity. Along with Q79 this establishes a tested mapping preference over Compatible and Revised, not improved SNR or universal suitability.

### Q84 — Tangential contribution alongside the accepted preset

Instruction: Re-enable ISO04 and Angular at Bounded signed/Detail contrast 3/Opacity 10% each, WOW at AEL edge-aware/eight scales/Noise reduction 3/Opacity 10%, and NAFE at AEL original/Opacity 40% with its baseline settings. Keep ISO01 and other enhancement filters off. Set Tangential to Source-relative, Opacity 10%, leaving gain/spatial controls unchanged. With full-resolution preview at 100% zoom, toggle only Tangential off/on and compare the same inner-corona, outer-streamer and background regions. Wait for updates and keep presentation fixed.

Question: Which gives the better overall balance: accepted four-layer preset alone, preset plus Tangential, no meaningful difference, or uncertain?

Answer (verbatim): “Preset plus Tangential”

Interpretation: User prefers adding Source-relative Tangential at 10% opacity to the accepted four-layer preset at the tested settings. Combined noise, limb/detail behavior and whole-image acceptance remain pending.

### Q85 — Five-layer background noise

Instruction: Leave the accepted ISO04/Angular/WOW/NAFE settings enabled, plus Tangential Source-relative at Opacity 10% with unchanged gain/spatial controls. Other enhancement filters remain off. With full-resolution preview at 100% zoom inspect the same quiet-background patch without changing presentation.

Question: Is the combined background noise acceptable, slightly distracting, clearly distracting, or uncertain?

Answer (verbatim): “Slightly distracting”

Interpretation: Background noise remains slightly distracting with the five-layer candidate. Earlier presets received the same qualitative category; this does not establish identical noise or no incremental noise from Tangential.

### Q86 — Five-layer limb check

Instruction: Keep ISO04/Angular Bounded gain 3 at 10% each, WOW AEL edge-aware/eight scales/Noise reduction 3/10%, NAFE AEL original/40%, and Tangential Source-relative/10% with unchanged gain/spatial controls. Other enhancement filters stay off. With full-resolution preview at 100% zoom inspect several parts of the lunar edge, keeping presentation and geometry fixed.

Question: Do you see a distinct narrow bright rim or dark halo: none, bright rim, dark halo, both, or uncertain?

Answer (verbatim): “None”

Interpretation: No distinct narrow bright rim or dark halo reported for the five-layer candidate in inspected regions. This does not establish absence of all defects or cover uninspected regions.

### Q87 — Five-layer inner-corona detail

Instruction: Keep ISO04/Angular Bounded gain 3 at 10% each, WOW AEL edge-aware/eight scales/Noise reduction 3/10%, NAFE original/40%, and Tangential Source-relative/10%, with other enhancement filters off. With full-resolution preview at 100% zoom, inspect bright inner-corona streaks while toggling only Tangential off/on. Keep presentation and spatial settings fixed and wait for updates.

Question: With all five layers on, do the streaks remain distinct, become flattened/merged, or are you uncertain?

Answer (verbatim): “Remain distinct”

Interpretation: User reports bright inner-corona streaks remain distinct with the five-layer candidate in the inspected region. No flattening/merging reported; whole-image acceptance remains pending.

### Q88 — Five-layer whole-image acceptance

Instruction: Leave ISO04/Angular Bounded gain 3 at 10% each, WOW AEL edge-aware/eight scales/Noise reduction 3/10%, NAFE original/40%, and Tangential Source-relative/10% enabled, with all other enhancement filters off. Keep full-resolution preview on, switch zoom to Fit and inspect the whole composition without changing presentation.

Question: Would you keep all five as the provisional preset for this master, accepting the slight noise distraction, prefer further adjustment, prefer the previous four-layer preset, or are you uncertain?

Answer (verbatim): “Keep all five”

Interpretation: User accepts the five-layer combination as the provisional preset for this master, acknowledging slight background-noise distraction. This does not authorize application-default changes. Preserve the earlier recipes as references.

### Q89 — Save the accepted five-layer recipe

Instruction: Leave the accepted five layers enabled and save app settings to a new JSON named `Visual-Review-ISO04-Angular-WOW-NR3-NAFE40-Tangential10.json`. Keep earlier recipes unchanged. Provide its full path so the final controls can be verified.

Question: What is the full path of the newly saved JSON file?

Answer (verbatim): “/Volumes/Astro/Imágenes/CoronaHDR_RAW/CoronaHDR_Work/4-plus-Tan10.json”

Verification: Read the saved v4 JSON and asserted approved source; ISO04/Angular Bounded gain 3/10% each; WOW AEL edge-aware/eight scales/Noise reduction 3/10%; NAFE original/40% with automatic sigma/window 129/multiplier 12/region 4 R/residual sigma 4 native px; Tangential Source-relative/10%; ISO01, adaptive ACHF and other enhancement filters off; full-resolution preview on. All assertions passed. SHA-256: `09dd56bd8258995643f41a8e57d3f293798a776a68e0d26a874eec59180086e0`.

Captured Tangential settings: arc 3 degrees, gain 1, denoise 0, inner radius 1 R, outer restriction off; fade parameter 28.920991475518807 native-target px in the collected parameters (GUI setting unchanged). Compared with Q76, saved control differences are Tangential encoding Follow → Source-relative and global normalization Revised → Compatible, plus Tangential activation. Global normalization is overridden by both selected bounded ACHF mappings and Source-relative Tangential; it does not alter those current layers. Geometry and non-control/non-section settings are unchanged. Earlier recipes remain readable. Reload/export of this exact file has not been checked.

### Q90 — Next review segment

Question: Which remaining segment should we review next: NRGF, FNRGF, MGN, RHEF, or pause and review conclusions?

Answer (verbatim): “Pause and review conclusions”

Interpretation: Pause the guided questions and summarize findings. Resume only when requested; do not start another filter segment now.

### Q91 — Resume review: next filter

Question: Which filter should we review next, continuing from Q90 with the accepted five-layer preset as our reference?

Answer (verbatim): “NRGF”

Interpretation: Resume with isolated NRGF, then assess its contribution alongside the accepted five-layer preset. Preserve the saved reference recipe and existing presentation, geometry and spatial settings.

### Q92 — Isolated NRGF baseline

Instruction: Disable ISO04, Angular, WOW, NAFE and Tangential without changing their chosen settings. Enable only NRGF at Opacity 40%. Retain its current numerical controls, the approved source, geometry, colour, exposure and background settings. Keep View Original off and Full-resolution preview on; wait for calculation. Do not overwrite the accepted five-layer recipe. NRGF's numerical settings still need to be captured before interpreting comparisons.

Question: Has the isolated NRGF baseline at 40% opacity finished rendering?

Answer (verbatim): “Still processing”

Interpretation: NRGF baseline calculation is not yet confirmed complete. Await completion before asking for visual judgments.

Follow-up answer (verbatim): “ready”

Interpretation: User confirms the isolated NRGF baseline has finished rendering. Numerical controls remain uncaptured; no visual finding yet.

### Q93 — NRGF baseline limb check

Instruction: Keep only NRGF active at 40% opacity, Full-resolution preview on and all other settings unchanged. At 100% zoom, inspect several parts of the lunar circumference for a distinct narrow bright rim or dark halo, separately from the broad coronal glow. A reported defect will need a filter-off comparison before attribution.

Question: Around the lunar edge, do you see none, a bright rim, a dark halo, both, or are you uncertain?

Answer (verbatim): “Bright rim”

Interpretation: User reports a distinct bright rim with isolated NRGF at 40% opacity in inspected limb regions. Attribution to NRGF is not yet established; compare with the filter disabled.

### Q94 — NRGF filter-off control

Instruction: Keep the same limb region, 100% zoom, Full-resolution preview and all settings fixed. Toggle only NRGF Active off/on, retaining its opacity at 40%, and wait for each update.

Question: With NRGF off, does the bright rim disappear, become weaker, stay the same, become stronger, or are you uncertain?

Answer (verbatim): “Disappear”

Interpretation: The bright rim disappears when NRGF is disabled at the tested 40% opacity. This supports an NRGF-dependent visible effect under the current presentation, without establishing its numerical cause. Capture numerical settings before adjusting controls.

### Q95 — Capture NRGF baseline settings

Instruction: Re-enable only NRGF at 40% opacity, retaining all numerical and presentation settings. Save Settings Only to a new file named `Visual-Review-NRGF-Baseline40.json`, preserving the accepted five-layer recipe and earlier references.

Question: What is the full path of the saved NRGF baseline JSON?

Answer (verbatim): “/Volumes/Astro/Imágenes/CoronaHDR_RAW/CoronaHDR_Work/NRGF-Baseline40.json”

Verification: Read the v4 recipe and asserted approved e1c3c474 source, isolated NRGF enabled at 40%, all other enhancement filters/ACHF variants disabled and Full-resolution preview enabled. All assertions passed. SHA-256: `c1aab8a5d61c3c102dd1ed3e6e89448444646cf40af57ef13a65433ba9a14478`.

Captured NRGF: Median/MAD, Legacy shared-angle chain (`chain`), bin width 2 native px, minimum 12 samples, profile smoothing 0, inner-radius control 10 (1 R). Geometry (2975,1660,272); lunar statistics exclusion on, guard 0, bright exclusion off. Compatible global normalization; Linear input, colour calibration on, EV 0, PSB presentation on; background extraction, warmth, green suppression and prominences off. This verifies saved settings, not a reload/export or the numerical cause of the reported rim.

### Q96 — Anchored-chain limb comparison

Instruction: Keep only NRGF active at 40%, Full-resolution preview on, the same limb region at 100% zoom and all other controls fixed. In Expert, change NRGF's Legacy shared-angle chain selector to Anchored shared-angle chain (EIP). Wait for recalculation; switch back if needed to compare the same region. This tests an existing alternative, without assuming chaining causes the rim.

Question: Compared with Legacy, is the bright rim absent, weaker, about the same, stronger, or uncertain with Anchored?

Answer (verbatim): “About the same”

Interpretation: No meaningful visible rim reduction reported from Anchored chaining at 40% opacity in the inspected region. This does not establish identical numerical outputs or isolate the cause. Return to Legacy for the next single-control comparison.

### Q97 — NRGF statistics and limb appearance

Instruction: Return NRGF to Legacy shared-angle chain. Keep NRGF alone active at 40%, Full-resolution preview on, the same limb region at 100% zoom and all remaining controls fixed. Compare Median/MAD against Mean/STD using the statistics selector, waiting for each calculation. This compares appearance at equal opacity, not matched local contrast.

Question: Compared with Median/MAD, is the bright rim absent, weaker, about the same, stronger, or uncertain with Mean/STD?

Answer (verbatim): “About the same”

Interpretation: Mean/STD gives no reported visible rim improvement over Median/MAD at 40% opacity in the inspected region. Neither tested selector change is a demonstrated remedy. Retain the captured Median/MAD/Legacy baseline for an opacity comparison; lower opacity is a presentation tradeoff, not an operator correction.

### Q98 — NRGF limb at lower opacity

Instruction: Return statistics to Median/MAD and retain Legacy shared-angle chain. Keep only NRGF active, Full-resolution preview on, the same limb region at 100% zoom and all numerical/presentation settings fixed. Reduce only NRGF opacity from 40% to 20% and wait for the update.

Question: At 20% opacity, is the bright rim absent, visible but acceptable, still distracting, or uncertain?

Answer (verbatim): “Still distracting”

Interpretation: Reducing NRGF opacity to 20% does not make the bright rim acceptable in the inspected region. Check 10% as a further restrained contribution before assessing usefulness; opacity reduction is not a causal correction.

### Q99 — NRGF limb at 10% opacity

Instruction: Keep only NRGF active with Median/MAD and Legacy shared-angle chain, Full-resolution preview on, the same limb region at 100% zoom and all other settings fixed. Reduce only opacity from 20% to 10% and wait for the update.

Question: At 10% opacity, is the bright rim absent, visible but acceptable, still distracting, or uncertain?

Answer (verbatim): “Visible but acceptable”

Interpretation: User accepts the visible rim at NRGF 10% opacity in the inspected region. The rim remains present; this is an accepted presentation tradeoff, not a numerical correction. Overall usefulness and noise remain unassessed.

### Q100 — Isolated NRGF usefulness at 10%

Instruction: Keep NRGF at Median/MAD, Legacy shared-angle chain and 10% opacity, with other enhancement filters off. Keep Full-resolution preview on and presentation fixed. At 100% zoom, toggle only NRGF Active off/on, waiting for each update. Compare the same outer-streamer and quiet-background regions, considering useful structure, noise and the accepted visible limb rim.

Question: Overall, do you prefer NRGF on, NRGF off, no meaningful difference, or are you uncertain?

Answer (verbatim): “No meaningful difference”

Interpretation: No meaningful overall preference reported between isolated NRGF on/off at 10%, considering detail, noise and the visible but acceptable rim. This does not establish identical pixels or rule out an interaction with the accepted preset. Check its combined contribution before selecting inclusion.

### Q101 — NRGF contribution alongside the accepted preset

Instruction: Re-enable the accepted five layers: ISO04 and Angular Bounded signed/contrast 3/10% each; WOW AEL edge-aware/eight scales/noise reduction 3/10%; NAFE AEL original/40%; Tangential Source-relative/10%. Retain their saved spatial settings. Keep NRGF Median/MAD, Legacy chaining, opacity 10%, and all remaining filters off. With Full-resolution preview, 100% zoom and presentation fixed, toggle only NRGF off/on, waiting for updates. Compare inner-corona, outer-streamer and quiet-background regions, including the limb tradeoff.

Question: Which gives the better overall balance: accepted five-layer preset alone, preset plus NRGF, no meaningful difference, or uncertain?

Answer (verbatim): “No meaningful difference”

Interpretation: Adding NRGF at 10% gives no meaningful overall preference over the accepted five-layer preset alone. Omit NRGF from the provisional preset: no demonstrated benefit at the acceptable-rim setting. This is not rejection of all NRGF settings or a universal quality judgment.

### Q102 — Next review segment

Instruction: Disable NRGF, retaining its tested settings, and keep the accepted five-layer preset as the reference.

Question: Which segment should we review next: FNRGF, MGN, RHEF, or pause and review conclusions?

Answer (verbatim): “FNRGF”

Interpretation: Review isolated FNRGF, then assess its contribution alongside the accepted five-layer preset. The Q95 recipe captured retained FNRGF opacity 29%, Continuous observed-support mode, MAD width, log binning and global Compatible normalization; confirm baseline before visual judgments.

### Q103 — Isolated FNRGF baseline

Instruction: Disable ISO04, Angular, WOW, NAFE and Tangential without changing their accepted settings. Keep NRGF and all other enhancement filters off. Enable only FNRGF at 29% opacity, Continuous observed-support mode, with global Filter normalization Compatible. Retain its other numerical controls, source, geometry and presentation. Keep View Original off and Full-resolution preview on; wait for calculation. Preserve the accepted recipe.

Question: Has the isolated FNRGF baseline finished rendering?

Answer (verbatim): “Yes”

Interpretation: User confirms the isolated FNRGF baseline at 29% opacity, Continuous observed-support mode and Compatible normalization is rendered with Full-resolution preview. No visual findings yet.

### Q104 — FNRGF Compatible limb check

Instruction: Keep only FNRGF active at 29%, Continuous observed-support mode, Compatible normalization and Full-resolution preview. At 100% zoom, inspect several parts of the lunar circumference without changing other settings. Distinguish a narrow bright rim or dark halo from the broad coronal glow; any reported defect needs a filter-off control before attribution.

Question: Do you see a distinct narrow bright rim or dark halo: none, bright rim, dark halo, both, or uncertain?

Answer (verbatim): “faint ring”

Evidence: User supplied a limb screenshot showing a thin bright edge around portions of the black disk, with pink limb features also visible. Screenshot alone does not identify which processing stage produces the edge or independently confirm the running controls.

Interpretation: Faint ring reported under the requested FNRGF baseline. Bright-edge appearance is visible in the screenshot; no filter attribution yet. Do not assume the pink features are artifacts or infer their origin from this screenshot.

### Q105 — FNRGF filter-off control

Instruction: Keep the same limb framing, 100% zoom, Full-resolution preview and all numerical/presentation settings fixed. Toggle only FNRGF Active off/on, retaining opacity 29%, and wait for each update. Compare the thin ring separately from the pink limb features.

Question: With FNRGF off, does the faint ring disappear, become weaker, stay the same, become stronger, or are you uncertain?

Answer (verbatim): “Disappear”

Interpretation: User reports the faint ring disappears with FNRGF disabled at the tested 29% opacity. This supports a FNRGF-dependent visible effect under the current presentation, without identifying its numerical cause.

### Q106 — FNRGF Revised-normalization limb comparison

Instruction: Re-enable only FNRGF at 29% opacity in Continuous observed-support mode. Keep the same limb framing at 100% zoom, Full-resolution preview and all other settings fixed. Change Geometry → Filter normalization from Compatible to Revised (experimental), wait for recalculation, and switch back if needed to compare. This compares complete model/encoding policies at equal opacity, not matched local contrast.

Question: Compared with Compatible, is the faint ring absent, weaker, about the same, stronger, or uncertain with Revised?

Answer (verbatim): “Weaker”

Interpretation: Revised normalization reduces the visible ring relative to Compatible at equal 29% opacity. Complete removal and absolute acceptability are not established; this is not a matched-local-contrast comparison or proof of the numerical cause.

### Q107 — FNRGF Revised residual-ring acceptance

Instruction: Keep only FNRGF active at 29%, Continuous observed-support mode, Revised normalization and Full-resolution preview. At 100% zoom inspect several parts of the lunar edge without changing other settings.

Question: Is the remaining ring absent, visible but acceptable, still distracting, or uncertain?

Answer (verbatim): “Still distracting”

Interpretation: Revised reduces the ring but does not make it acceptable at 29% opacity. Test a lower contribution; opacity reduction is a presentation tradeoff, not a causal correction.

### Q108 — FNRGF Revised limb at lower opacity

Instruction: Keep only FNRGF active in Continuous observed-support mode with Revised normalization, Full-resolution preview and the same limb framing at 100% zoom. Reduce only opacity from 29% to 15%, retaining all other settings, and wait for the update.

Question: At 15% opacity, is the ring absent, visible but acceptable, still distracting, or uncertain?

Answer (verbatim): “Visible but acceptable”

Interpretation: User accepts the remaining visible ring at FNRGF Revised/15% in the inspected region. The ring is not eliminated; overall detail/noise usefulness remains unassessed.

### Q109 — Isolated FNRGF usefulness at 15%

Instruction: Keep only FNRGF active at 15%, Continuous observed-support mode, Revised normalization and Full-resolution preview. At 100% zoom, toggle only FNRGF Active off/on, waiting for each update. Keep presentation fixed and compare inner-corona structure, outer streamers and quiet-background noise, also considering the accepted visible ring.

Question: Overall, do you prefer FNRGF on, FNRGF off, no meaningful difference, or uncertain?

Answer (verbatim): “check this settings. It is better”

Evidence: Supplied screenshot shows FNRGF active, opacity 29%, Reference-compatible mode; Fourier order 16, angular segments 64, remove coefficients 0, inner radius 0.9 R, outer radius 12.6 R, ring width 4 native px, MAD spread, Log radial spacing, limb protection 0%. Global normalization displays Revised (experimental); NRGF is inactive. Other filter activation states and Full-resolution preview are outside the screenshot.

Interpretation: User reports this configuration is better, but does not answer the requested Continuous/Revised/15% on/off comparison. Treat Reference-compatible/29% as a new preferred candidate; the exact comparison reference is unspecified. Revised normalization does not modify Reference-compatible FNRGF. Multiple fine concentric bands are visible across the displayed corona, separately from the narrow limb edge; their origin is not established by the screenshot. Do not attribute them causally without a fixed-view control or assume the preferred candidate is artifact-free.

Follow-up answer to the selectable Q109 prompt (verbatim): “FNRGF on”

Interpretation: User prefers FNRGF enabled, but the answer arrived after the screenshot of a different configuration. Clarify which mode/opacity this preference describes before assigning it to Continuous/15% or Reference-compatible/29%. Concentric-band acceptance remains unassessed.

### Q110 — Clarify preferred FNRGF configuration

Question: Does “FNRGF on” refer to Continuous with Revised normalization at 15%, Reference-compatible at 29% as shown in the screenshot, or both separately?

Answer (verbatim): “Reference-compatible at 29%”

Interpretation: The enabled-over-disabled preference applies to Reference-compatible FNRGF at 29%. No on/off preference is established for Continuous/Revised at 15%. This does not yet establish acceptance of the screenshot's concentric bands or the candidate's contribution to the accepted preset.

### Q111 — Reference-compatible concentric bands at native view

Instruction: Keep only FNRGF active at the shown Reference-compatible settings and 29% opacity, retaining source, geometry and presentation. Enable Full-resolution preview, wait for calculation and inspect the middle corona at 100% zoom. Look separately at the repeated fine concentric bands visible in the screenshot, rather than the narrow lunar rim.

Question: Are the repeated concentric bands absent at this view, visible but acceptable, distracting, or uncertain?

Answer (verbatim): “Absent at this view”

Interpretation: User reports the repeated concentric bands are absent with Full-resolution preview at 100% zoom for Reference-compatible FNRGF at 29%. The screenshot appearance is not established as a native-output defect; its cause remains untested. This observation does not answer the separate narrow limb-ring check.

### Q112 — Reference-compatible limb-ring acceptance

Instruction: Keep only FNRGF active at Reference-compatible, 29% opacity and the shown numerical settings, Full-resolution preview on. At 100% zoom inspect several parts of the lunar edge without changing presentation or geometry. Judge the narrow limb ring separately from broad coronal glow.

Question: Is the narrow limb ring absent, visible but acceptable, still distracting, or uncertain?

Answer (verbatim): “Concentric rings are vissible”

Evidence: New screenshot clearly displays repeated concentric rings across the corona. UI shows “200% · native · PSB preview”, Full-resolution preview enabled and “Full-resolution verification ready”. FNRGF is active at 29%, Reference-compatible, order 16, segments 64, removed coefficients 0, inner/outer radii 0.9/12.6 R, ring width 4 native px, MAD, Log spacing, limb protection 0; global normalization Revised. NRGF is inactive. Model smoothing and boundary fade display 8 preview px, harmonic regularization 0.01.

Interpretation: This updates the earlier absence observation: repeated rings are visible in the current full-resolution display at 200%. They cannot be dismissed as a fast-preview-only effect. Q111 described the earlier requested 100% view; visibility may differ with zoom. Narrow limb-ring acceptance remains unanswered. Establish whether these repeated rings depend on FNRGF with a separate fixed-view off/on control; Q105 tested the earlier narrow ring in Continuous mode.

### Q113 — Reference-compatible concentric-ring control

Instruction: Keep the current 200% zoom, framing, Full-resolution preview, presentation and numerical settings unchanged. Toggle only FNRGF Active off/on, retaining Reference-compatible and 29% opacity, and wait for each update. Inspect the repeated rings across the corona separately from the thin lunar edge.

Question: With FNRGF off, do the repeated concentric rings disappear, become weaker, stay the same, become stronger, or are you uncertain?

Answer (verbatim): “Disappear”

Interpretation: Repeated concentric rings disappear when Reference-compatible FNRGF at 29% is disabled in the fixed 200% full-resolution view. This supports dependence on the filter configuration, without isolating operator, encoding or composition as the first failing stage. Acceptance of the rings has not been established.

### Q114 — Continuous/Revised concentric-ring comparison

Instruction: Re-enable only FNRGF at 29%. Keep global normalization Revised, the same 200% framing, Full-resolution preview and all other settings fixed. Change only FNRGF implementation from Reference-compatible to Continuous observed-support, wait for full-resolution verification to finish, and compare the repeated rings across the corona. This is a complete implementation comparison at equal opacity, not matched local contrast.

Question: Compared with Reference-compatible, are the repeated concentric rings absent, weaker, about the same, stronger, or uncertain in Continuous/Revised?

Answer (verbatim): “Absent”

Interpretation: User reports the repeated concentric rings are absent in Continuous/Revised at the same 29% opacity and 200% full-resolution view. This establishes a useful implementation distinction for the inspected region, not universal artifact freedom. The separate narrow limb ring was previously distracting at 29% (Q107), but visible and acceptable at 15% (Q108). The earlier enabled preference was explicitly for Reference-compatible/29%, so Continuous/Revised/15% usefulness still needs an answer.

### Q115 — Continuous/Revised usefulness at acceptable limb opacity

Instruction: Retain Continuous observed-support and Revised normalization. Reduce only FNRGF opacity to 15%, the previously accepted limb-ring setting. Keep other enhancement filters off, Full-resolution preview on and presentation fixed. At 100% zoom toggle only FNRGF off/on, waiting for updates, and compare inner-corona structure, outer streamers and quiet-background noise, considering the visible limb ring.

Question: Overall, do you prefer Continuous/Revised FNRGF on at 15%, off, no meaningful difference, or uncertain?

Answer (verbatim): “FNRGF on at 15%”

Interpretation: User prefers isolated Continuous/Revised FNRGF enabled at 15%, considering detail, noise and the previously accepted visible limb ring. Its contribution and artifact behavior alongside the accepted five-layer preset remain untested.

### Q116 — Continuous/Revised FNRGF contribution to the preset

Instruction: Re-enable the accepted five layers with their retained settings: ISO04 and Angular Bounded signed/contrast 3/10% each; WOW AEL edge-aware/eight scales/noise reduction 3/10%; NAFE AEL original/40%; Tangential Source-relative/10%. Keep NRGF and all remaining filters off. Retain FNRGF Continuous observed-support, Revised normalization and 15% opacity. With Full-resolution preview, 100% zoom and presentation fixed, toggle only FNRGF off/on and wait for updates. The selected bounded ACHF and source-relative Tangential mappings override global normalization, so retaining Revised does not change those reference mappings.

Question: Considering inner/outer detail, background noise and the limb ring, which gives the better overall balance: accepted five-layer preset alone, preset plus FNRGF, no meaningful difference, or uncertain?

Answer (verbatim): “first check this”

Evidence: Screenshot shows full-resolution verification ready, 200% native PSB preview, Reference-compatible FNRGF active at 29%, ring width 2 native px (previous Reference-compatible screenshot: 4). Other visible principal controls retain order 16, segments 64, removed coefficients 0, radii 0.9/12.6 R, MAD, Log, limb protection 0, global Revised. NRGF is off; other filter activations are not visible.

Interpretation: Defer Q116; no combined-preset preference recorded. Broad concentric bands appear less pronounced than in the earlier 4-px screenshot, with fine concentric texture still visible. These separate screenshots do not establish a controlled single-parameter comparison or numerical cause. Assess this user-selected width candidate before resuming the preset test.

### Q117 — Reference-compatible ring width 2 versus 4

Instruction: Keep only FNRGF active at Reference-compatible/29%, Full-resolution preview on, the same 200% framing and all other settings fixed. Compare ring width 2 versus 4 native px, waiting for full-resolution verification after each change. Assess useful coronal detail, repeated bands and background texture together.

Question: Which gives the better overall balance: width 2 px, width 4 px, no meaningful difference, or uncertain?

Answer (verbatim): “Width 2 px”

Interpretation: User prefers Reference-compatible FNRGF at 29% with 2-native-pixel ring width over 4 px for the tested detail/banding/background balance. Relative preference does not establish acceptable residual artifacts or superiority over Continuous/Revised.

### Q118 — Width-2 residual concentric-texture acceptance

Instruction: Keep only FNRGF active at Reference-compatible, opacity 29%, ring width 2 native px, Full-resolution preview on and the same 200% framing. Retain all other settings. Inspect repeated concentric texture across the corona separately from the narrow lunar rim.

Question: Is the remaining concentric texture absent, visible but acceptable, distracting, or uncertain?

Answer (verbatim): “Absent”

Interpretation: User reports no remaining concentric texture in the inspected 200% full-resolution view with Reference-compatible FNRGF/29%/2-native-pixel rings. This qualifies the current local visual observation, not all regions or a universal numerical repair. Narrow limb-ring acceptance remains separate.

### Q119 — Width-2 candidate narrow limb ring

Instruction: Keep only FNRGF active at Reference-compatible, 29% opacity, ring width 2 native px and Full-resolution preview. Inspect several parts of the lunar edge at the current 200% zoom, retaining all other settings. Judge the thin limb ring separately from broad coronal glow and pink limb features.

Question: Is the narrow limb ring absent, visible but acceptable, still distracting, or uncertain?

Answer (verbatim): “Still distracting”

Interpretation: The narrow limb ring remains unacceptable at Reference-compatible/29%/2 px, despite absent concentric texture in the inspected view. Test lower opacity independently; this is a presentation tradeoff, not a numerical correction.

### Q120 — Reference-compatible width-2 limb at 15%

Instruction: Keep only FNRGF active at Reference-compatible with ring width 2 native px, Full-resolution preview and the same 200% limb framing. Reduce only opacity from 29% to 15%, retain all other settings and wait for the update.

Question: At 15% opacity, is the thin limb ring absent, visible but acceptable, still distracting, or uncertain?

Answer (verbatim): “Visible but acceptable”

Interpretation: User accepts the remaining visible narrow limb ring for Reference-compatible FNRGF/2 px at 15% in the inspected 200% full-resolution view. Overall usefulness at this lower opacity has not been established.

### Q121 — Reference-compatible width-2 usefulness at 15%

Instruction: Keep only FNRGF active at Reference-compatible, ring width 2 native px, opacity 15% and Full-resolution preview. At 100% zoom, toggle only FNRGF Active off/on, waiting for updates. Keep all other settings fixed and compare inner-corona detail, outer streamers and quiet-background noise, considering the accepted visible limb ring.

Question: Overall, do you prefer FNRGF on at these settings, FNRGF off, no meaningful difference, or uncertain?

Answer (verbatim): “FNRGF on at these settings”

Interpretation: User prefers isolated Reference-compatible FNRGF with 2-native-pixel ring width and 15% opacity enabled, considering detail, noise and the accepted limb ring. No direct ranking against Continuous/Revised/15% is established. Test this current candidate's combined contribution next.

### Q122 — Reference-compatible width-2 contribution to the preset

Instruction: Re-enable the accepted five layers with retained settings: ISO04 and Angular Bounded signed/contrast 3/10% each; WOW AEL edge-aware/eight scales/noise reduction 3/10%; NAFE AEL original/40%; Tangential Source-relative/10%. Keep NRGF and all remaining filters off. Retain FNRGF Reference-compatible, ring width 2 native px and opacity 15%; leave global normalization Revised. With Full-resolution preview at 100% zoom and presentation fixed, toggle only FNRGF off/on, waiting for updates. Compare inner/outer detail, quiet-background noise and the limb ring.

Question: Which gives the better overall balance: accepted five-layer preset alone, preset plus FNRGF, no meaningful difference, or uncertain?

Answer (verbatim): “Preset plus FNRGF”

Interpretation: User prefers adding Reference-compatible FNRGF with 2-native-pixel ring width at 15% opacity to the accepted five-layer preset. Combined noise, limb/texture behavior, inner-detail preservation and whole-image acceptance remain unconfirmed; this is a six-layer candidate, not a final accepted preset.

### Q123 — Six-layer background noise

Instruction: Leave the accepted five layers enabled plus FNRGF Reference-compatible/2-native-pixel ring width/15%. Keep NRGF and other filters off, Full-resolution preview on, zoom 100% and presentation fixed. Inspect the same quiet-background patch used for earlier comparisons.

Question: Is the combined background noise acceptable, slightly distracting, clearly distracting, or uncertain?

Answer (verbatim): “Slightly distracting”

Interpretation: Six-layer background noise is slightly distracting. The five-layer reference received the same qualitative category, but this does not establish equal noise or no incremental noise from FNRGF. Combined artifact and whole-image acceptance remain unconfirmed.

### Q124 — Six-layer narrow limb ring

Instruction: Keep the five accepted layers plus FNRGF Reference-compatible/2-native-pixel ring width/15% enabled, with NRGF and other filters off. Retain Full-resolution preview and all settings. At 200% zoom inspect several parts of the lunar edge, judging the thin ring separately from pink limb features and broad coronal glow.

Question: In the six-layer combination, is the narrow limb ring absent, visible but acceptable, still distracting, or uncertain?

Answer (verbatim): “Visible but acceptable”

Interpretation: User accepts the visible narrow limb ring in the inspected 200% full-resolution six-layer view. This does not establish absence of concentric texture elsewhere or preservation of inner-corona detail.

### Q125 — Six-layer inner-corona detail

Instruction: Keep the five accepted layers enabled and FNRGF at Reference-compatible/2-native-pixel ring width/15%, with other filters off. At Full-resolution preview and 100% zoom inspect bright inner-corona streaks while toggling only FNRGF off/on. Keep framing and presentation fixed and wait for each update.

Question: With all six layers on, do the inner-corona streaks remain distinct, become flattened/merged, or are you uncertain?

Answer (verbatim): “Remain distinct”

Interpretation: User reports bright inner-corona streaks remain distinct with all six candidate layers enabled in the inspected region. No flattening/merging reported there. Combined concentric-texture and whole-image acceptance remain unconfirmed.

### Q126 — Six-layer concentric texture

Instruction: Leave all six candidate layers enabled, including FNRGF Reference-compatible/2-native-pixel ring width/15%, with other filters off. Keep Full-resolution preview and settings fixed. At 200% zoom inspect the middle corona for repeated fine concentric bands, separately from the narrow lunar rim.

Question: In the combined image, is repeated concentric texture absent, visible but acceptable, distracting, or uncertain?

Answer (verbatim): “Absent”

Interpretation: User reports no repeated concentric texture in the inspected 200% full-resolution combined view. This is a local visual observation, not a universal artifact guarantee. Whole-image acceptance remains pending.

### Q127 — Six-layer whole-image acceptance

Instruction: Leave the accepted five layers plus FNRGF Reference-compatible/2-native-pixel ring width/15% enabled. Keep NRGF and other filters off, Full-resolution preview on and presentation fixed. Switch zoom to Fit and inspect the whole composition.

Question: Would you keep all six as the provisional preset for this master, accepting the slightly distracting background noise and visible but acceptable limb ring, prefer the previous five-layer preset, prefer further adjustment, or are you uncertain?

Answer (verbatim): “Keep all six”

Interpretation: User accepts the six-layer combination as the provisional preset for this master at Fit, acknowledging slightly distracting background noise and the visible but acceptable limb ring. This adds Reference-compatible FNRGF/2-native-pixel ring width/15% to the prior five-layer preset. No application-default change is authorized. Preserve earlier recipes and capture the final saved state.

### Q128 — Save the accepted six-layer recipe

Instruction: Leave all six accepted layers enabled and use Save Settings Only to create a new `Visual-Review-Six-Layers-FNRGF-Reference-2px-15.json`. Preserve the five-layer and earlier reference recipes; do not overwrite them.

Question: What is the full path of the newly saved six-layer JSON?

Answer (verbatim): “/Volumes/Astro/Imágenes/CoronaHDR_RAW/CoronaHDR_Work/FNRGF-2px-15.json”

Verification: Read v4 JSON and asserted approved e1c3c474 source; ISO04/Angular enabled at Bounded/contrast 3/10% each; WOW AEL edge-aware/eight scales/noise reduction 3/10%; NAFE original/40%; Tangential Source-relative/10%; FNRGF Reference-compatible (`legacy`)/2-native-pixel ring width/15%; NRGF, MGN, RHEF, Larson–Sekanina, ISO01 and adaptive ACHF disabled; Full-resolution preview enabled. All assertions passed. SHA-256: `4b6cdac927e6d6bfffcdaa768aa7c7c4ed425fad8383d0241f9120609d642689`.

Captured geometry: (2975,1660,272). Compared with the retained five-layer recipe, changed controls are FNRGF inner radius 0.9 → 1.0 R, width 4 → 2 native px, implementation Continuous → Reference-compatible, opacity 29 → 15%; global normalization Compatible → Revised; inactive NRGF opacity 64 → 10%. Six-layer activations match the accepted combination. The saved inner radius differs from the supplied screenshots and was not explicitly recorded during the questions; do not attribute all visual changes solely to ring width or opacity. Exact recipe reload/export remains unchecked. Earlier five-layer recipe remains readable.

### Q129 — Confirm saved inner radius

Question: The saved recipe uses FNRGF inner radius 1.0 R, while your screenshots showed 0.9 R. Was 1.0 R the setting used for the six-layer image you accepted at Fit?

Answer (verbatim): “Yes, accepted at 1.0 R”

Interpretation: User confirms the saved 1.0 R inner radius matches the six-layer image accepted at Fit. Final recipe state is reconciled; the timing of the radius change during earlier comparisons remains unrecorded. Do not infer single-parameter causality across those comparisons.

### Q130 — Next review segment

Question: Which segment should we review next: MGN, RHEF, or pause and review conclusions?

Answer (verbatim): “RHEF”

Interpretation: Begin isolated RHEF review, then assess contribution alongside the accepted six-layer reference. Preserve the verified recipe and retained settings.

### Q131 — Isolated RHEF baseline

Instruction: Disable ISO04, Angular, WOW, NAFE, Tangential and FNRGF without changing their accepted settings. Keep NRGF, MGN and other enhancement filters off. Enable only RHEF at 20% opacity in Continuous global mode, retaining all other numerical controls and the approved source, geometry and presentation. Keep View Original off and Full-resolution preview on; wait for calculation. Preserve the accepted six-layer recipe.

Question: Has the isolated RHEF baseline finished rendering?

Answer (verbatim): “Yes”

Interpretation: User confirms isolated RHEF at 20% opacity in Continuous global mode has rendered with Full-resolution preview. No visual findings yet.

### Q132 — RHEF baseline limb check

Instruction: Keep only RHEF active at 20%, Continuous global mode and Full-resolution preview, with all other settings fixed. At 100% zoom inspect several parts of the lunar edge. Distinguish a narrow bright rim or dark halo from broad coronal glow and pink limb features. Any reported defect needs a filter-off control before attribution.

Question: Do you see a distinct narrow bright rim or dark halo: none, bright rim, dark halo, both, or uncertain?

Answer (verbatim): “None”

Interpretation: No distinct narrow bright rim or dark halo reported for isolated RHEF Continuous global at 20% in the inspected 100% full-resolution limb regions. This does not establish absence of artifacts elsewhere.

### Q133 — RHEF baseline background noise

Instruction: Keep only RHEF active at 20%, Continuous global mode, Full-resolution preview and 100% zoom. Inspect the same quiet-background patch used for earlier comparisons, retaining all numerical and presentation settings.

Question: Is the background noise acceptable, slightly distracting, clearly distracting, or uncertain?

Answer (verbatim): “Acceptable”

Interpretation: User accepts background noise for isolated RHEF Continuous global at 20% in the inspected patch. No noise-driven tuning is indicated; overall usefulness remains unassessed.

### Q134 — Isolated RHEF usefulness

Instruction: Keep RHEF at Continuous global, 20% opacity, with other enhancement filters off. Retain Full-resolution preview, 100% zoom and all numerical/presentation settings. Toggle only RHEF Active off/on, waiting for updates, and compare inner-corona structure, outer streamers and quiet-background texture.

Question: Overall, do you prefer RHEF on, RHEF off, no meaningful difference, or uncertain?

Answer (verbatim): “RHEF on”

Interpretation: User prefers isolated RHEF Continuous global at 20% enabled for overall detail/background balance. Its combined contribution remains untested.

### Q135 — RHEF contribution to the accepted six-layer preset

Instruction: Re-enable the accepted six layers with retained settings: ISO04/Angular Bounded contrast 3/10% each; WOW AEL edge-aware/eight scales/noise reduction 3/10%; NAFE original/40%; Tangential Source-relative/10%; FNRGF Reference-compatible/2-native-pixel ring width/inner radius 1.0 R/15%. Keep NRGF, MGN and remaining filters off. Retain RHEF Continuous global/20%. With Full-resolution preview at 100% zoom and presentation fixed, toggle only RHEF off/on and wait for updates. Compare inner/outer detail, background texture and the limb.

Question: Which gives the better overall balance: accepted six-layer preset alone, preset plus RHEF, no meaningful difference, or uncertain?

Answer (verbatim): “Preset plus RHEF”

Interpretation: User prefers adding RHEF Continuous global at 20% to the accepted six-layer preset. This is a seven-layer candidate; combined noise, artifacts, inner-detail preservation and whole-image acceptance remain unconfirmed.

### Q136 — Seven-layer background noise

Instruction: Leave the accepted six layers plus RHEF Continuous global/20% enabled. Keep NRGF, MGN and other filters off, Full-resolution preview on, zoom 100% and presentation fixed. Inspect the same quiet-background patch used earlier.

Question: Is the combined background noise acceptable, slightly distracting, clearly distracting, or uncertain?

Answer (verbatim): “Slightly distracting”

Interpretation: Seven-layer background noise is slightly distracting. The six-layer reference received the same category, but this does not establish equal noise or no incremental noise from RHEF. Combined artifact and whole-image acceptance remain unconfirmed.

### Q137 — Seven-layer limb assessment

Instruction: Leave the accepted six layers plus RHEF Continuous global/20% enabled, with NRGF, MGN and other filters off. Keep Full-resolution preview and all settings fixed. At 200% zoom inspect several parts of the lunar edge, separately from pink limb features and broad coronal glow. The six-layer reference had a visible but acceptable narrow limb ring.

Question: With all seven layers enabled, is the limb ring/halo absent, visible but acceptable, distracting, or uncertain?

Answer (verbatim): “Visible but acceptable”

Interpretation: User accepts the visible limb ring/halo in the inspected seven-layer 200% full-resolution view. This does not establish unchanged artifact strength relative to six layers or preservation of inner-corona detail.

### Q138 — Seven-layer inner-corona detail

Instruction: Keep the accepted six layers enabled plus RHEF Continuous global/20%, with other filters off. At Full-resolution preview and 100% zoom inspect bright inner-corona streaks while toggling only RHEF off/on. Keep framing and presentation fixed and wait for updates.

Question: With all seven layers on, do the inner-corona streaks remain distinct, become flattened/merged, or are you uncertain?

Answer (verbatim): “Remain distinct”

Interpretation: User reports inner-corona streaks remain distinct with all seven candidate layers enabled in the inspected region. No flattening/merging reported there. Combined concentric-band and whole-image acceptance remain unconfirmed.

### Q139 — Seven-layer concentric bands

Instruction: Leave all seven candidate layers enabled, including RHEF Continuous global/20%, with other filters off. Keep Full-resolution preview and all settings fixed. At 200% zoom inspect the middle corona for repeated concentric bands, separately from the narrow lunar rim.

Question: Is repeated concentric banding absent, visible but acceptable, distracting, or uncertain?

Answer (verbatim): “Absent”

Interpretation: User reports no repeated concentric banding in the inspected seven-layer 200% full-resolution middle-corona view. This is a local observation, not a universal artifact guarantee. Whole-image acceptance remains pending.

### Q140 — Seven-layer whole-image acceptance

Instruction: Leave the accepted six layers plus RHEF Continuous global/20% enabled, with NRGF, MGN and other filters off. Keep Full-resolution preview on and presentation fixed. Switch zoom to Fit and inspect the whole composition.

Question: Would you keep all seven as the provisional preset for this master, accepting the slightly distracting background noise and visible but acceptable limb ring/halo, prefer the previous six-layer preset, prefer further adjustment, or are you uncertain?

Answer (verbatim): “Keep all seven”

Interpretation: User accepts the seven-layer combination at Fit for this master, adding RHEF Continuous global/20% to the accepted six-layer preset. Slightly distracting background noise and a visible but acceptable limb ring/halo are acknowledged. No application-default change is authorized. Preserve previous recipes and capture the saved final state.

### Q141 — Save the accepted seven-layer recipe

Instruction: Leave all seven accepted layers enabled. Use Save Settings Only to create a new `Visual-Review-Seven-Layers-RHEF20.json`, preserving the six-layer and earlier reference recipes.

Question: What is the full path of the newly saved seven-layer JSON?

Answer (verbatim): “/Volumes/Astro/Imágenes/CoronaHDR_RAW/CoronaHDR_Work/RHEF20.json”

Verification: Read v4 JSON and asserted source matches the previously verified approved master, RHEF Continuous global/20% enabled, the six accepted layers enabled with bounded ISO04/Angular contrast 3/10% each, other enhancement filters disabled and Full-resolution preview enabled. All assertions passed. SHA-256: `adf3729326294db8a750f483dee3b41e9302653e28d8e2d8cd422f1c3627e6d5`.

Compared with `FNRGF-2px-15.json`, the only control change is global normalization Revised → Compatible; the only section change is RHEF activation. Numerical receipt differences are correspondingly `rhef_enabled` and `normalization_mode`. All other controls, geometry and non-control/non-section settings match exactly. Global normalization does not affect the selected Reference-compatible FNRGF, RHEF, NAFE, WOW, bounded ACHF mappings or source-relative Tangential. This verifies the saved state, not each earlier comparison or an exact recipe reload/export. Earlier six-layer recipe remains readable.

### Q142 — Next review segment

Question: Would you like to review MGN next, or pause and review conclusions?

Answer (verbatim): “Review MGN”

Interpretation: Begin isolated MGN review, then assess contribution alongside the accepted seven-layer reference. Preserve the verified recipe and retained numerical/presentation settings.

### Q143 — Isolated MGN baseline

Instruction: Disable ISO04, Angular, WOW, NAFE, Tangential, FNRGF and RHEF without changing their accepted settings. Keep NRGF and all remaining enhancement filters off. Enable only MGN at its retained 20% opacity. Leave all MGN numerical controls, source, geometry and presentation unchanged. Keep View Original off and Full-resolution preview on; wait for calculation. Preserve the accepted seven-layer recipe.

Question: Has the isolated MGN baseline finished rendering?

Answer (verbatim): “Yes”

Interpretation: User confirms isolated MGN at 20% opacity has rendered with Full-resolution preview. No visual findings yet.

### Q144 — MGN baseline limb check

Instruction: Keep only MGN active at 20% with Full-resolution preview and all other settings fixed. At 100% zoom inspect several parts of the lunar edge. Distinguish a narrow bright rim or dark halo from broad coronal glow and pink limb features. Any reported defect needs a filter-off control before attribution.

Question: Do you see a distinct narrow bright rim or dark halo: none, bright rim, dark halo, both, or uncertain?

Answer (verbatim): “None”

Interpretation: No distinct narrow bright rim or dark halo reported for isolated MGN at 20% in the inspected 100% full-resolution limb regions. This does not establish absence of artifacts elsewhere.

### Q145 — MGN baseline background noise

Instruction: Keep only MGN active at 20%, Full-resolution preview on and zoom 100%. Inspect the same quiet-background patch used for earlier comparisons, retaining all numerical and presentation settings.

Question: Is the background noise acceptable, slightly distracting, clearly distracting, or uncertain?

Answer (verbatim): “Acceptable”

Interpretation: User accepts background noise for isolated MGN at 20% in the inspected patch. No noise-driven tuning is indicated; overall usefulness remains unassessed.

### Q146 — Isolated MGN usefulness

Instruction: Keep MGN at 20% opacity, with other enhancement filters off. Retain Full-resolution preview, 100% zoom and all numerical/presentation settings. Toggle only MGN Active off/on, waiting for updates, and compare inner-corona structure, outer streamers and quiet-background texture.

Question: Overall, do you prefer MGN on, MGN off, no meaningful difference, or uncertain?

Answer (verbatim): “MGN on”

Interpretation: User prefers isolated MGN at 20% enabled for overall detail/background balance. Its contribution alongside the accepted seven-layer preset remains untested.

### Q147 — MGN contribution to the accepted seven-layer preset

Instruction: Re-enable the accepted seven layers with retained settings: ISO04/Angular Bounded contrast 3/10% each; WOW AEL edge-aware/eight scales/noise reduction 3/10%; NAFE original/40%; Tangential Source-relative/10%; FNRGF Reference-compatible/2-native-pixel ring width/inner radius 1.0 R/15%; RHEF Continuous global/20%. Keep NRGF and remaining filters off. Retain MGN at 20%. With Full-resolution preview at 100% zoom and presentation fixed, toggle only MGN off/on and wait for updates. Compare inner/outer detail, background texture and the limb.

Question: Which gives the better overall balance: accepted seven-layer preset alone, preset plus MGN, no meaningful difference, or uncertain?

Answer (verbatim): “No meaningful difference”

Interpretation: Adding MGN at 20% gives no meaningful overall preference over the accepted seven-layer preset alone. Leave MGN out of the provisional preset; its isolated benefit does not establish a useful addition to this combination. Other MGN settings and replacement combinations remain untested.

### Q148 — Next review step

Instruction: Disable MGN and retain the accepted seven-layer preset as the reference.

Question: Would you like to review conclusions, test whether every retained layer is still useful in the final combination, or review Larson–Sekanina next?

Answer (verbatim): “Check each retained layer’s contribution”

Interpretation: Assess each retained layer against the complete accepted seven-layer reference, holding the other six fixed. Preserve `RHEF20.json`. Test ISO04, Angular, WOW, NAFE, Tangential, FNRGF and RHEF individually; restore each layer before testing the next so comparisons share the same reference. Record removal preferences before constructing and accepting any reduced combination. These checks assess current marginal contributions, not all possible combinations or a globally optimal subset.

### Q149 — ISO04 contribution in the complete preset

Instruction: Use the accepted seven-layer settings from `RHEF20.json`, with MGN, NRGF and other filters off. Keep Full-resolution preview on, View Original off, presentation fixed and zoom 100%. Toggle only ISO04 Active off/on, retaining Bounded contrast 3 and opacity 10%. Wait for updates and inspect the same inner-corona, outer-streamer and quiet-background regions, including the limb. Other six layers remain enabled and unchanged.

Question: Which gives the better overall balance: all seven layers, the preset without ISO04, no meaningful difference, or uncertain?

Answer (verbatim): “All seven layers”

Interpretation: User prefers retaining ISO04 Bounded contrast 3/10% within the complete seven-layer preset. This establishes a marginal preference against its removal at the tested settings, not universal necessity.

### Q150 — Angular contribution in the complete preset

Instruction: Restore ISO04 enabled at its accepted settings. Keep all seven accepted layers enabled, MGN/NRGF and other filters off, Full-resolution preview on, View Original off and zoom 100%. Toggle only Angular Active off/on, retaining Bounded contrast 3 and opacity 10%; wait for updates. Keep the other six fixed and inspect the same inner-corona, outer-streamer, quiet-background and limb regions.

Question: Which gives the better overall balance: all seven layers, the preset without Angular, no meaningful difference, or uncertain?

Answer (verbatim): “All seven layers”

Interpretation: User prefers retaining Angular Bounded contrast 3/10% within the complete seven-layer preset. Restore it before assessing WOW.

### Q151 — WOW contribution in the complete preset

Instruction: Restore Angular enabled at its accepted settings. Keep the complete seven-layer reference, Full-resolution preview on, View Original off and zoom 100%. Toggle only WOW Active off/on, retaining AEL edge-aware, eight scales, noise reduction 3 and opacity 10%; wait for updates. Keep the other six enabled and fixed. Compare the same inner-corona, outer-streamer, quiet-background and limb regions. WOW suppression affects only its own layer.

Question: Which gives the better overall balance: all seven layers, the preset without WOW, no meaningful difference, or uncertain?

Answer (verbatim): “All seven layers”

Interpretation: User prefers retaining WOW AEL edge-aware/eight scales/noise reduction 3/10% within the complete seven-layer preset. Restore it before assessing NAFE.

### Q152 — NAFE contribution in the complete preset

Instruction: Restore WOW enabled at its accepted settings. Keep the complete seven-layer reference, Full-resolution preview on, View Original off and zoom 100%. Toggle only NAFE Active off/on, retaining AEL original, opacity 40% and the saved automatic-noise/window settings; wait for updates. Keep the other six enabled and fixed. Compare the same inner-corona, outer-streamer, quiet-background and limb regions.

Question: Which gives the better overall balance: all seven layers, the preset without NAFE, no meaningful difference, or uncertain?

Answer (verbatim): “All seven layers”

Interpretation: User prefers retaining NAFE AEL original/40% with saved automatic-noise/window settings within the complete seven-layer preset. Restore it before assessing Tangential.

### Q153 — Tangential contribution in the complete preset

Instruction: Restore NAFE enabled at its accepted settings. Keep the complete seven-layer reference, Full-resolution preview on, View Original off and zoom 100%. Toggle only Tangential Active off/on, retaining Source-relative encoding, opacity 10% and saved spatial/gain settings; wait for updates. Keep the other six enabled and fixed. Compare the same inner-corona, outer-streamer, quiet-background and limb regions.

Question: Which gives the better overall balance: all seven layers, the preset without Tangential, no meaningful difference, or uncertain?

Answer (verbatim): “All seven layers”

Interpretation: User prefers retaining Tangential Source-relative/10% with saved spatial/gain settings within the complete seven-layer preset. Restore it before assessing FNRGF.

### Q154 — FNRGF contribution in the complete preset

Instruction: Restore Tangential enabled at its accepted settings. Keep the complete seven-layer reference, Full-resolution preview on, View Original off and zoom 100%. Toggle only FNRGF Active off/on, retaining Reference-compatible mode, ring width 2 native px, inner radius 1.0 R, opacity 15% and other saved settings; wait for updates. Keep the other six enabled and fixed. Compare the same inner-corona, outer-streamer, quiet-background and limb regions, including the accepted visible limb ring.

Question: Which gives the better overall balance: all seven layers, the preset without FNRGF, no meaningful difference, or uncertain?

Answer (verbatim): “All seven layers”

Interpretation: User prefers retaining FNRGF Reference-compatible/2-native-pixel ring width/inner radius 1.0 R/15% within the complete seven-layer preset, considering its limb tradeoff. Restore it before assessing RHEF.

### Q155 — RHEF contribution in the complete preset

Instruction: Restore FNRGF enabled at its accepted settings. Keep the complete seven-layer reference, Full-resolution preview on, View Original off and zoom 100%. Toggle only RHEF Active off/on, retaining Continuous global mode, opacity 20% and saved numerical settings; wait for updates. Keep the other six enabled and fixed. Compare the same inner-corona, outer-streamer, quiet-background and limb regions.

Question: Which gives the better overall balance: all seven layers, the preset without RHEF, no meaningful difference, or uncertain?

Answer (verbatim): “No meaningful difference”

Interpretation: Removing RHEF Continuous global/20% from the complete preset gives no meaningful overall preference in this later comparison, despite the earlier addition preference under Q135. Preserve both observations; current removal evidence supports trying the six-layer subset without RHEF. All other retained layers were individually preferred present. Confirm the reduced whole image before adopting it; these checks do not establish global optimality.

### Q156 — Six-layer subset after removal review

Instruction: Leave RHEF disabled. Keep ISO04/Angular Bounded contrast 3/10% each; WOW AEL edge-aware/eight scales/noise reduction 3/10%; NAFE original/40%; Tangential Source-relative/10%; FNRGF Reference-compatible/2-native-pixel ring width/inner radius 1.0 R/15% enabled. Keep MGN, NRGF and other filters off. Retain Full-resolution preview and all presentation settings. Switch zoom to Fit and inspect the whole image; toggle only RHEF if needed for comparison, waiting for updates.

Question: Would you keep the six-layer subset without RHEF, retain the seven-layer preset, adjust further, or are you uncertain?

Answer (verbatim): “Keep six layers without RHEF”

Interpretation: User accepts the six-layer subset without RHEF at Fit after the retained-layer removal review. ISO04, Angular, WOW, NAFE, Tangential and FNRGF remain enabled at their accepted settings. RHEF, MGN and NRGF are omitted. Preserve the seven-layer reference; capture the final saved state without changing application defaults.

### Q157 — Save the accepted six-layer subset

Instruction: Keep the accepted six layers enabled and RHEF, MGN, NRGF and other filters off. Use Save Settings Only to create a new `Visual-Review-Six-Layers-After-Removal-Review.json`, preserving `RHEF20.json`, `FNRGF-2px-15.json` and earlier references.

Question: What is the full path of the newly saved final six-layer JSON?

Answer (verbatim): “/Volumes/Astro/Imágenes/CoronaHDR_RAW/CoronaHDR_Work/Six-layers.json”

Verification: Read v4 JSON and asserted the previously verified approved source, accepted six layers enabled, RHEF/MGN/NRGF/Larson–Sekanina/adaptive ACHF/ISO01 disabled, bounded ISO04/Angular contrast 3/10% each and Full-resolution preview enabled. Assertions passed. SHA-256: `cc8f31664dafb9782f2fa3a9037893dcae1a43759c8ca759b8458a33c12e308d`.

Compared with `RHEF20.json`, all controls, geometry and other settings match exactly. Only RHEF section activation and `rhef_enabled` change from true to false. Thus all retained numerical settings and presentation are preserved. Earlier seven-layer recipe remains readable. Exact final-recipe reload/export remains unchecked.

### Q158 — Next step after final recipe verification

Question: Would you like to review conclusions, check that the saved final recipe reloads correctly, or review Larson–Sekanina?

Answer (verbatim): “Check saved-recipe reload”

Interpretation: Check reopening the exact verified `Six-layers.json` through the app, then confirm restored controls and rendered appearance. File inspection alone has not established GUI restoration or export equivalence.

### Q159 — Reopen the verified final recipe

Instruction: Without changing current controls, note the accepted image at Fit for comparison. Use Open Image / Settings to open `/Volumes/Astro/Imágenes/CoronaHDR_RAW/CoronaHDR_Work/Six-layers.json`. Wait for source loading and full-resolution calculation to finish; keep View Original off and zoom Fit. Do not overwrite the recipe.

Question: Has the recipe reopened and finished rendering without an error?

Answer (verbatim): “An error occurred”

Interpretation: GUI reload did not complete successfully according to the user. Exact error and failure stage are unknown; do not claim recipe roundtrip success. Preserve the verified JSON and capture the error before changing controls or retrying.

### Q160 — Capture reload error

Question: What is the exact error message shown when opening Six-layers.json? Include any Details or traceback text if available.

Answer (verbatim): “no”

Clarification question: Does “no” mean no error occurred and the recipe loaded successfully, or that it failed without showing an error message?

Clarification answer (verbatim): “Loaded successfully; no error”

Interpretation: User corrects the earlier error selection: the recipe loaded successfully without an error. No reload failure is established and no diagnosis is required. Restored appearance and controls still need confirmation.

### Q161 — Reloaded appearance

Instruction: Keep the reloaded Six-layers.json settings unchanged, View Original off and Full-resolution preview on. Wait for calculation to finish, then inspect at Fit and revisit the previously used inner-corona, outer-streamer and quiet-background regions at 100% zoom.

Question: Does the reloaded image look the same as the six-layer result you accepted before reopening?

Answer (verbatim): “Looks the same”

Interpretation: User reports the reloaded image visually matches the accepted six-layer result in the requested views. This is visual reload confirmation, not pixel equality or export verification. Restored layer activations still need confirmation.

### Q162 — Restored layer activations

Instruction: Without changing any controls, inspect the Active states after reload. ISO04, Angular, WOW, NAFE, Tangential and FNRGF should be enabled. RHEF, MGN, NRGF, ISO01, adaptive ACHF and Larson–Sekanina should be disabled. Expanding a card to inspect it does not require activation.

Question: Do the restored Active states match this list?

Answer (verbatim): “All match”

Interpretation: User confirms all expected enabled/disabled layer states after reload. To verify remaining controls, compare a separately saved snapshot of the reloaded state with the original recipe; expansion/view-only differences should be distinguished from processing changes.

### Q163 — Capture reloaded settings for comparison

Instruction: Without changing numerical or presentation controls, use Save Settings Only to create a separate `Six-layers-reloaded.json`. Preserve the original `Six-layers.json`. Card expansion changes made during inspection are allowed and should be identified separately in the comparison.

Question: What is the full path of the separately saved reloaded-settings JSON?

Answer (verbatim): “/Volumes/Astro/Imágenes/CoronaHDR_RAW/CoronaHDR_Work/reloaded.json”

Verification: Read and recursively compared the complete parsed JSON against `Six-layers.json`. All controls, numerical parameters, display receipts, source references, geometry, activation states and remaining fields match exactly. The sole difference is `settings.sections.sec_geo.expanded`: true → false (Geometry card collapsed). Re-saved file SHA-256: `244b5816939be080d60255fee7d03591b47f6c6341dd76c8782144db1343163f`. Original recipe retained.

Interpretation: Together with the user-confirmed successful load, matching appearance and matching Active states, this verifies the GUI settings reload/re-save for this recipe. It does not establish pixel-exact preview equality, final export equivalence or behavior on another platform/master.

### Q164 — Next step after reload verification

Question: Would you like to review conclusions, check export consistency, or review Larson–Sekanina?

Answer (verbatim): “Review conclusions”

Interpretation: Pause guided questions and summarize the final six-layer preset, removal findings, reload verification and remaining limits. Do not start another review segment without a request.

## Basic-mode default adoption

Validation: all **552 repository tests passed** after adoption (82.676 s; `/tmp/eclipse-basic-defaults-tests-final.log`). First Basic image loading, exact selected parameters/activation, eligible mode-switch preservation and settings restoration are covered. Standard export fixtures explicitly retain Standard defaults. Actual Basic Qt layout was rendered and inspected offscreen; no native platform interaction or app/DMG rebuild was performed.

After Q164, the user requested: “make this the defaults for basic mode, if possible”. The accepted six-layer settings are now applied after first-image heuristics on a first direct image load in Basic. FNRGF and Tangential are available in Basic; mode switches and JSON restoration do not reapply the starter. Standard/Expert first-load defaults remain unchanged. Source geometry and viewport resolution are not copied from the study. No app/DMG rebuild accompanies this source change. Small images may lack the fully supported samples required by eight-scale WOW noise reduction; reduce scales in Expert or disable suppression if its actionable support error occurs. Earlier statements about unchanged defaults describe the review before this explicit adoption request.

## Conclusions

### Final six-layer reload verification — Q159–Q163

`Six-layers.json` loaded successfully; user reports matching appearance and all expected layer activations. Re-saving as `reloaded.json` preserved every control, numerical parameter, display receipt and source/geometry field exactly. Only Geometry card expansion changed. GUI recipe roundtrip is verified for this case; pixel equality and export consistency remain unchecked.

### Retained-layer removal review — Q148–Q156

The complete seven-layer preset was preferred over individually removing ISO04, Angular, WOW, NAFE, Tangential or FNRGF. Removing RHEF gave no meaningful difference in this later comparison, despite its earlier addition preference. User then accepted the six-layer subset without RHEF at Fit. Current accepted layers are ISO04/Angular Bounded contrast 3/10% each, WOW AEL edge-aware/eight scales/noise reduction 3/10%, NAFE original/40%, Tangential Source-relative/10%, and FNRGF Reference-compatible/2-native-pixel ring width/inner radius 1.0 R/15%. RHEF, MGN and NRGF remain off. Seven-layer and earlier recipes remain historical references. Final subset recipe capture is pending under Q157; exact reload/export and generalization beyond this master remain unchecked. Individual removal preferences do not establish a globally optimal subset.

### MGN review — Q142–Q147

MGN at 20% has acceptable background noise, no reported narrow limb rim/halo in inspected regions, and is preferred enabled in isolation. Adding it to the accepted seven-layer preset gives no meaningful overall preference, so MGN remains off. The verified `RHEF20.json` remains the accepted reference. This does not reject other MGN settings or establish whether MGN could replace another retained layer; those comparisons remain untested.

### Accepted seven-layer preset — Q140–Q141

Verified recipe: `/Volumes/Astro/Imágenes/CoronaHDR_RAW/CoronaHDR_Work/RHEF20.json`, SHA-256 `adf3729326294db8a750f483dee3b41e9302653e28d8e2d8cd422f1c3627e6d5`.

The accepted six-layer configuration is retained, adding RHEF Continuous global at 20%. Global normalization is saved as Compatible; the selected implementations/mappings are unaffected by this change. NRGF, MGN and other enhancement filters remain off. Adding RHEF is preferred; all seven are accepted at Fit, with slightly distracting noise and a visible but acceptable limb ring/halo. Inner-corona streaks remain distinct and repeated concentric banding is absent in inspected regions. These are local visual judgments on the approved master, not scientific-detail confirmation or universal defaults. Exact final-recipe reload/export remains unchecked; earlier recipes are retained and no application defaults changed.

### Accepted six-layer preset — Q127–Q129

Verified recipe: `/Volumes/Astro/Imágenes/CoronaHDR_RAW/CoronaHDR_Work/FNRGF-2px-15.json`, SHA-256 `4b6cdac927e6d6bfffcdaa768aa7c7c4ed425fad8383d0241f9120609d642689`.

The accepted five-layer configuration is retained, adding Reference-compatible FNRGF at 15% opacity, ring width 2 native px and confirmed inner radius 1.0 R. Other captured FNRGF settings: order 16, 64 angular segments, removed coefficients 0, outer radius 12.6 R, MAD, Log spacing, limb protection 0. Global normalization is Revised, which does not modify Reference-compatible FNRGF or the selected bounded ACHF/source-relative Tangential mappings. NRGF and other enhancement filters remain off.

User prefers the FNRGF addition and accepts all six at Fit. Background noise is slightly distracting; the narrow limb ring is visible but acceptable; inner-corona streaks remain distinct; no repeated concentric texture is reported in the inspected combined 200% full-resolution view. These are local visual findings on the approved master, not universal defaults or scientific-detail qualification. Earlier screenshots used inner radius 0.9 R; the timing of its change to 1.0 R is not recorded, so earlier improvements cannot all be assigned solely to width/opacity. Exact final-recipe reload/export and broader-data/platform checks remain unperformed. Earlier recipes remain references; no application defaults changed.

### NRGF review — Q91–Q101

NRGF is omitted from the provisional preset. At 40% opacity, a bright rim disappeared when NRGF was disabled; changing Legacy to Anchored chaining or Median/MAD to Mean/STD gave no reported rim improvement. With Median/MAD and Legacy, the rim remained distracting at 20%, and was visible but acceptable at 10%. At 10%, neither isolation nor addition to the accepted five-layer preset produced a meaningful overall preference. The accepted five-layer reference remains unchanged. The baseline recipe and hash are recorded under Q95. These findings cover the tested settings and inspected regions only; numerical cause, other parameter choices and independent data remain untested.

### Pause summary — accepted final candidate

Verified recipe: `/Volumes/Astro/Imágenes/CoronaHDR_RAW/CoronaHDR_Work/4-plus-Tan10.json`.

| Filter | Selected method | Setting | Opacity |
| --- | --- | --- | --- |
| ACHF ISO04 | Bounded signed | Detail contrast 3 | 10% |
| ACHF Angular | Bounded signed | Detail contrast 3 | 10% |
| WOW | AEL edge-aware | Eight scales; Noise reduction 3 | 10% |
| NAFE | AEL original | Automatic sigma; window 129; multiplier 12; region 4 R; residual sigma 4 native px | 40% |
| Tangential | Source-relative | Gain 1; arc 3 degrees; denoise 0 | 10% |

ISO01/adaptive ACHF and all other enhancement filters are off. This is the accepted candidate for the approved master and captured presentation, not new app defaults. Each addition (Angular, WOW, NAFE, Tangential) was preferred in the tested cumulative sequence; this does not establish a globally optimal combination or prove each remains essential after subsequent additions.

Visual acceptance: no distinct narrow bright rim/dark halo reported for the final combination in inspected regions; bright inner-corona streaks remain distinct. Combined background noise is slightly distracting but explicitly accepted at Fit. WOW suppression 3 yields acceptable isolated background noise while slightly reducing faint detail, an accepted tradeoff. It only suppresses its own layer.

Mapping conclusions: ISO04/Angular Bounded gain 3 was preferred over Compatible and Revised. ISO01 Bounded gain 2 tied Revised and was preferred over Compatible individually; adding it to ISO04 was less preferred than ISO04 alone. NAFE original and Limb-aware tied visually at 40%; original is a reference choice, not a demonstrated superior algorithm. Tangential Source-relative was preferred over Compatible and Revised individually.

Artifact conclusion: ISO04 Compatible produced a narrow bright rim at 100% opacity that disappeared with ISO04 off. Revised reduced it; Bounded at gain 4 was similar to Revised. Working-opacity checks were clear in inspected regions. Original NAFE's previously reported ring was not reproduced at the tested 40% opacity on the approved master; no full-opacity NAFE conclusion follows.

Still untested: NRGF/FNRGF/MGN/RHEF/Larson–Sekanina and adaptive ACHF in this guided review; alternate filter order/subsets; whether all five additions remain necessary in the final combination; second-master generalization; final-recipe reload/export; the ISO04 preview/native mismatch; platform/Photoshop checks. Do not generalize a local visual preference into scientific validation or universal defaults. Future work should start by reproducing the saved final candidate before modifying it.


Latest accepted provisional preset: ISO04 and Angular each Bounded signed/Detail contrast 3/Opacity 10%, WOW AEL edge-aware/eight scales/Noise reduction 3/Opacity 10%, NAFE AEL original/Opacity 40% with baseline noise/window settings, and Tangential Source-relative/Opacity 10% with unchanged gain/spatial settings. All other enhancement filters off. The user prefers adding Tangential to the four-layer preset and accepts all five at Fit. Background noise remains slightly distracting; no distinct limb rim/halo is reported and bright inner-corona streaks remain distinct in inspected regions. The five-layer recipe is verified under Q89; earlier recipes remain references and no application defaults changed. Its exact reload/export remains unchecked.

Tangential individual candidate: Source-relative at 10% opacity, preferred over both Follow/Compatible and Follow/Revised, with acceptable background noise, no distinct narrow bright rim/dark halo and distinct bright inner-corona streaks in inspected regions. Contribution alongside the accepted four-layer preset remains pending. No distinct rim or halo was reported for Follow/Compatible at 10% opacity either.

Latest accepted provisional preset: ISO04 and Angular each Bounded signed/contrast 3/opacity 10%, WOW AEL edge-aware/eight scales/Noise reduction 3/opacity 10%, and NAFE AEL original/opacity 40% with the baseline noise/window settings. Other enhancement filters off. Adding NAFE is preferred over the three-layer preset, and the user accepts the whole image at Fit. No distinct narrow limb rim/halo is reported and inner-corona streaks remain distinct in inspected regions. Slightly distracting background noise is an accepted tradeoff. The saved three-layer preset remains a retained reference; the new four-layer recipe is verified under Q76. Its exact reload/export remains unchecked. No application defaults changed.

NAFE findings: AEL original at 40% opacity has acceptable background noise and no reported distinct narrow bright rim or dark halo in inspected regions. Original and Limb-aware are visually tied for overall balance at this opacity; original is retained as the reference. Its contribution alongside the accepted three-layer preset remains pending. Earlier ring reports are not automatically reproduced by this working-opacity observation; no general implementation preference is established.

Accepted combined provisional preset for this master: ISO04 and Angular each Bounded signed, Detail contrast 3, Opacity 10%, plus WOW AEL edge-aware, eight scales, Noise reduction 3, Opacity 10%. All other enhancement filters off. User prefers adding WOW over the ACHF pair alone and accepts the whole image at Fit. Combined noise remains slightly distracting; no distinct limb rim/halo is reported and bright inner-corona streaks remain distinct in inspected regions. Slight faint-detail loss with WOW suppression was judged acceptable in isolation. The separate combined v4 recipe has been inspected and matches the accepted setup (Q65); no application defaults changed. Reload/export of this exact recipe remains unchecked.

WOW findings: AEL edge-aware WOW alone at 10% opacity, eight scales and Noise reduction 0 produces clearly distracting background noise. Successive comparisons prefer 1 over 0, 2 over 1 and 3 over 2 for overall balance. At strength 3, residual background noise is acceptable, identifiable faint detail is slightly reduced but acceptably so, no distinct limb rim/halo is reported, and bright inner streaks remain distinct. Its net contribution alongside the accepted ACHF pair remains pending; no final combined WOW preset is selected.

### Accepted provisional ACHF preset for this master

| Filter | Active | Mapping | Detail contrast | Opacity |
| --- | --- | --- | --- | --- |
| ACHF ISO04 | Yes | Bounded signed | 3 | 10% |
| ACHF Angular | Yes | Bounded signed | 3 | 10% |
| ACHF ISO01 | No | Not selected for this pair | — | — |

The user accepted the pair at Fit after native-calculation, 100%-zoom region checks. The pair is preferred over ISO04 alone, has no reported narrow bright rim/dark halo in inspected regions, and preserves distinct inner-corona streaks. Slightly distracting background noise remains an explicitly accepted tradeoff for this provisional preset, not a claim that the noise is absent or improved in SNR.

ISO04 and Angular individually: Bounded gain 3 at 10% is preferred over both Follow/Compatible and Follow/Revised. Gain 3 beats tested neighboring gains 2 and 4. ISO04 opacity 7% versus 10% produced no clear balance preference. With ISO04 fixed at 10%, Angular 10% was preferred over 5%.

ISO01 individually: Bounded gain 2 at 10% is preferred over Compatible and over disabled, with acceptable noise, no reported rim/halo and distinct inner streaks. It is visually tied with Revised. Adding ISO01 to ISO04 was less preferred than ISO04 alone, so ISO01 is omitted from the candidate. Its addition to the accepted ISO04-plus-Angular pair was not tested; neither was every possible alternative combination.

Limb diagnosis: ISO04 Compatible at 100% opacity shows a narrow bright rim that disappears when ISO04 is off. Revised makes it weaker; Bounded gain 4 looks about the same as Revised at that stress-test opacity. No rim was reported at working 10% opacity for Compatible, Bounded gain 4 or the final gain-3 setting. This supports a visible filter-dependent limb effect at high opacity, not its exact numerical cause or proof of artifact-free behavior elsewhere.

### Limits and next steps

All judgments are user observations on the approved e1c3c474 master under the unchanged running-app setup. The final saved v4 recipe has been inspected and matches the accepted filter setup, approved source and full-resolution preview; its geometry, spatial controls and presentation are recorded under Q49. Reproducibility by reloading/exporting this exact recipe has not yet been tested. No application defaults or numerical code were changed during this review. No new export equivalence check was performed for these exact user settings.

This completes the AEL ACHF visual selection, not the review of all filters. Other filter families, the interaction with a broader preset, ISO04 fast/native preview mismatch, a second master, Windows behavior and Photoshop recomposition remain outside this completed segment. Do not generalize the accepted pair into universal defaults yet.
