# Independent filter composition

The desktop application now uses the same layer model for fast preview, native verification, final TIFF/JPEG, TIFF layer packages and PSB. The former sequential numerical pipeline remains an internal operator dispatcher and compatibility API; the GUI sets `layered_model=True`.

## Inputs and composition

Every filter receives the immutable original monochrome image at the requested resolution, with its validity and statistical support. Fast preview area-averages the original data to the preview size and scales spatial controls; no other enhancement or display curve is passed to a filter. A file already stretched before loading remains stretched: the linear declaration does not recover original measurements.

The original forms the base, normalized and stretched once with Asinh, Log or GHS. The GHS shadow picker samples this original base. Encoded detail layers are then composed in this order:

| Layer | Fixed Photoshop blend mode |
| --- | --- |
| NRGF | Multiply |
| FNRGF | Multiply |
| RHEF | Overlay |
| MGN | Overlay |
| WOW | Overlay |
| Tangential Detail | Overlay |
| Larson–Sekanina | Linear Light |
| ACHF Adaptive | Overlay |
| ACHF ISO 01 | Overlay |
| ACHF ISO 04 | Overlay |
| ACHF Angular | Overlay |

There is no additional normalization, gamma or stretch of the finished composition. A Color layer supplies RGB in fast preview, native verification and export. Calibration is calculated once on the native RGB source; fast preview caches an observed-data reduction of that same calibrated RGB. Colour toggles update the display without recalculating luminance filters. Fast colour display is approximate because it stretches the reduced source; native verification still applies display operations before reducing the result. The PSB and TIFF loader add an opaque black background without modifying original layer alpha. Final TIFF/JPEG and the cached PSB composite show missing-data areas as black. Float source products store missing samples as zero; the separate VALID mask retains the distinction between missing observations and measured black pixels. Processing continues to exclude missing observations internally.

## Controls

Each filter has **Opacity (%) before Strength (%)**. Opening the first image directly enables **FNRGF 25% Strength / 75% Opacity**, **MGN 25% / 75%**, **AEL bilateral WOW 100% / 35%**, **ACHF ISO 04 100% / 10%**, and **ACHF Angular 100% / 10%**. NRGF starts disabled with prepared values of 100% Strength / 40% Opacity. The initial base stretch is logarithmic with K=1000. Subsequent image loads without JSON retain all current filter parameters, activations and ACHF inclusion flags, including settings last loaded from JSON. Geometry is detected for the new image; filter heuristics are not reapplied. The remaining filters and ACHF variants are disabled/excluded with **25% Strength / 75% Opacity**, except for the prepared NRGF values above. The initial opacities are application defaults adapted from AEL, not calibrated measurements. Strength controls encoded layer contrast around the blend mode's neutral value; it participates in the filter cache signature. Opacity only mixes the cached layer. A zero Strength is neutral and exports hidden. Reveal scales each layer opacity; it does not trigger numerical filtering.

NRGF is an independent layer before FNRGF; either or both can be enabled. Its defaults are Strength 100%, 2 native-pixel annuli, median/MAD statistics, 12 samples per annulus and zero profile smoothing. It adapts AEL 1.3.3's continuous NRGF and MAD/tanh display encoding (2.5, floor 1e-5), with attribution in `core/nrgf.py`. The inner radius defaults to one reference disk radius; only observed samples outside it enter statistics. The entire observed rectangle beyond it is processed, with no outer-radius cutoff. Sparse, constant or purely radial annuli without measurable angular spread remain transparent; no data is fabricated. Minimum samples and optional profile-node smoothing are advanced controls. Ring widths use original-image pixels and scale for fast preview, which remains approximate. Signed sky-subtracted input is supported.

The WOW selector retains Standard and Edge-aware modes and adds **AEL bilateral**. AEL uses six native B3-starlet scales with equal contributions, subtracts a smooth radial profile from ln(luminance), uses symmetric observed pairs and sets the whitening noise-floor multiplier to 3. The AEL noise-floor control is distinct from the existing per-band significance thresholds; the controls belonging to other modes are disabled. Native-scale counts adapt approximately for resized previews. `core/ael_wow.py` carries the AEL attribution and frozen upstream outputs are tested. As in AEL, boundary bands and changes in faint structure remain possible.

The ACHF selector selects the panel to edit. **Include in composition** checkboxes independently enable any combination of Adaptive, ISO 01, ISO 04 and Angular. The ACHF section's Active checkbox gates the entire family. The first direct image load selects the ISO 04 panel and includes both ISO 04 (sigmas 1/2/4/8/16 native px, final smoothing 1.5 px) and Angular (angular sigma 1 degree, final smoothing 4 native px). Both start at Strength 100% / Opacity 10%. All values persist when switching panels. Layer export automatically writes all active variants and omits excluded variants, so the cached PSB image matches the selected composition.

Loading a settings JSON applies its explicit controls, activations and inclusion flags after resetting filters. Filter controls/sections may be omitted; an absent filter section stays disabled and an absent ACHF inclusion flag stays unchecked. Missing parameters use prepared defaults, without inheriting the preceding image's edits. Unknown controls or malformed explicit values remain errors; geometry and non-filter settings are still required. Full settings retain exact round-trip behavior, including older Standard/Edge-aware WOW selectors.

## Cache and export

A worker retains at most two source identities (normally fast and native resolution), with one configuration per filter/variant. Keys include that filter's controls, geometry, spatial adaptation and support masks. Opacity, activation and display controls do not invalidate the numerical layers. Disabling/re-enabling a calculated filter retrieves its cached layer. Editing another filter leaves it reusable. Changing source, resolution, geometry or support invalidates the affected layers; changing Strength or a filter parameter replaces that filter's current configuration. Returning to an earlier parameter value after editing can require calculation again: this is not a history of every setting.

Only successfully completed, uncancelled layers enter the cache. Finished layers survive cancellation of a subsequent stage. Source arrays are immutable within a job; replacing a source creates a different identity. Export receives an isolated cache dictionary sharing read-only native layer arrays with its source snapshot. It builds layers/PSB first, then writes the final TIFF/JPEG; the final composition reuses the prepared layers. On worker completion, completed export layers are merged back into the window cache only if the original source identity still matches. This also retains ACHF variants that were first computed for all-variant export, avoiding their repetition on subsequent saves.

Layer RGB and alpha and the base are quantized to RGB16 for a common display reference; opacities are quantized to 1/255, matching Photoshop layer records. Composition uses float intermediates. TIFF and the PSB cached reference agree on the resulting 16-bit pixels. A native Photoshop recomposition may round differently or differ under color management; byte checks alone do not establish a native color-match guarantee.

The default fixed modes are Multiply, Overlay and Linear Light; Soft Light is not exposed by this change. The requested design retained fixed modes rather than adding a mode selector.

## Validation

Deterministic tests cover original input for every branch, blend equations, order, opacity-only changes, activation round trips, unrelated edits, Strength, source/geometry/mask invalidation, bounded caches, multiple ACHF variants, cancellation, GUI row order and final TIFF/PSB equality.

NRGF adds frozen AEL 1.3.3 oracles for robust, signed mean/STD and smoothed profiles, radial/constant nulls, sparse annuli, validity/statistics exclusions, cancellation, native-width scaling, cache reuse, simultaneous FNRGF, settings migration and TIFF/JPEG export. An offscreen GUI check and a 640×427 real linear-image export confirmed NRGF before FNRGF, transparent missing support, 16-bit TIFF and exact PSB cached-composite parity. This checks integration at reduced resolution; it does not establish native Photoshop recomposition or full-resolution performance.

A 640×427 reduction of the user's real linear master was processed with all filters and all four ACHF variants. Final RGB16 TIFF and cached PSB composite matched exactly. Artifacts and layer metadata are in `/tmp/eip-independent-validation`. The generated 13-layer PSB was opened in Photoshop 2026; its Color layer was hidden/restored to force recomposition and a separate copy was saved. All layer names, modes, opacities and visibility were retained. Native recomposition differed by at most 24/65535 (0.037% of full scale), with means about 1.6–1.7 levels and 99th percentiles six levels per channel. Measurements are in `native_compare.json`. This reduced case does not validate native-resolution performance.

## Parallel calculations

`LayerEngine.prepare` computes cache misses in a bounded thread pool for preview, native verification and layer-package export. Threads share the immutable original image. Completed layers are stored under a cache lock, but composition and output layer numbering always follow the recipe order, irrespective of completion order. Cached-only opacity/display updates do not create a pool.

The automatic limit is four concurrent filters for up to four million pixels, two for larger images, bounded further by logical CPUs and a scratch estimate of 128 bytes/pixel/filter within one third of physical RAM. Unknown-memory platforms fall back to a 512 MiB scratch budget. This estimates transient filter allocations rather than measuring free RAM or per-operator peak RSS; it cannot guarantee avoidance of swapping under external memory pressure.

Each filter receives a context-local helper CPU budget, inherited by its scale workers. The launcher initializes BLAS/OpenMP to one thread and OpenCV to at most two before the numerical processing starts. These global initialization limits require restarting the application; direct Python API users must configure their own native pools. Only numerical preparation is parallelized: compositing and package/PSB publication retain their deterministic order.

Cancellation contexts propagate into every filter task and nested helpers. A failed task signals its running siblings, cancels queued work and waits for running tasks to exit before returning. Valid layers completed before a failure remain reusable; unfinished or cancelled layers are not published. Per-filter timings overlap; use the `[FILTERS] Calculation finished` summary for wall-clock preparation time, rather than summing concurrent durations.

### Native-resolution measurement

On the supplied real master (green channel, 5608×3744, missing-data support retained), MGN and WOW were calculated with identical parameters and fresh caches in serial and parallel modes. The MGN sigmas were scaled by 5608/1500 and WOW used ten native scales with bilateral intensity 1. Lunar statistical exclusion was enabled. Both runs used the same native-thread limits on this 10-logical-CPU, 24 GiB machine.

| Preparation | Wall time |
| --- | ---: |
| Serial MGN + WOW | 83.610 s |
| Two concurrent filters | 51.892 s |

The measured speedup was 1.61×, about 38% less wall time for these two filters. Encoded RGB and alpha were byte-identical. This is a measured two-filter preparation result, not a promise for the entire export or every filter combination. Script, timings and report are in `/tmp/eip-parallel-validation`. Actual RAM availability and other applications affect performance.

GUI integration tests count actual filter calculations across native verification and PSB/TIFF saves: all ten previously calculated filters require zero new calculations, including after opacity/base-stretch changes. If only Adaptive ACHF was verified, the first all-variant export computes exactly the three missing AEL variants; the next save computes none. A replaced source never receives the earlier export cache.

The routine log emits one `[FILTER: name] Calculated` line per new calculation (total, filter and encoding timings). Cache lookups are silent. A calculation batch has one start and one wall-time summary; a cached composition reports `[FUSION] ... no filters recalculated`. Internal dispatcher banners and GUI revision announcements are suppressed for this path. Export writing and PSB verification retain their separate timings.

MGN sigmas are specified in original-image pixels (defaults: 1.25, 2.5, 5, 10, 20, 40). Full-resolution processing uses them directly; fast preview reduces them by the geometric mean of the image resize factors. Weights are unchanged. Settings JSON version 2 records this convention; version 1 projects convert their former preview-pixel controls to native pixels on load, preserving export footprints to slider precision. The benchmark above predates this convention.

The GUI logs completion after the full preview/verification pipeline and after export. `Idle — no processing running or queued` confirms that no processing job or timed update remains; otherwise the completion line reports running or pending work. Cancellation and failure also report the resulting state.

Colour neutralization now applies gains from sampled P99−P1 channel spans, without subtracting per-channel backgrounds or adding a pedestal. One common highlight scale avoids independent channel clipping. For positive inputs this does not turn a brightness-only variation into a chromaticity variation. The global balance can differ from earlier exports; existing source chromaticity differences remain. Source data is untouched, and negative samples are clipped only in the colour display copy.


## Optional PSB Color Correction

The export-only checkbox **Add Color Correction to PSB (sRGB)** starts off and is enabled only for layered PSB export. It creates a top-level **Color Correction** group (Normal, 50%) containing a snapshot base, Gradient Map and Color Balance in Color mode at 30%, and sky Hue/Saturation at 100%. The three adjustments have editable native 16-bit masks; the group uses the supplied Photoshop guide's palette and values. Automatic mask membership uses observed display luminance, a robust outer-field sky estimate and an independent lunar exclusion. Inspect the initial masks in Photoshop.

The PSB embeds sRGB for the application's assumed-sRGB display RGB. This is not general source-ICC conversion. Preview, filter recipes/caches, final TIFF/JPEG and original linear data are unchanged. JSON stores the checkbox; older JSON without it restores it off.

With this option enabled, the stored merged RGB remains the uncorrected reference and Version Info explicitly marks it as not a real merged rendering. Photoshop performs native adjustment recomposition on open. A Photoshop-saved copy then carries its rendered correction. This is an intentional exception to the ordinary cached-composite equality above; third-party flattened previews need not display the correction. The group snapshot must be regenerated after edits to underlying filter layers.

See `propuesta-color-atardecer-psb.md` for parameters, implementation scope and native validation.


## Black export storage and edge antialias

Final TIFF/JPEG and the PSB reference are opaque, finite images: missing/nonfinite display samples are zero. Optional LINEAR/INPUT and layer-package SOURCE/PREPARED/RGB float TIFF files also store zero for missing samples, retaining observed values and units. VALID still records the original support; stored zero does not mean an observation was recovered. Input files, in-memory sources, scientific masks and numerical filter results are unchanged.

Presentation applies a narrow smoothstep transition on the supported side of lunar/missing boundaries: two original-image pixels, with a minimum of one target pixel in fast previews. Exactly-black lunar pixels connected to the reference disk centre are included in the display-only black region, including mixed NaN/zero lunar disks; isolated measured zeros elsewhere are not turned into missing data. The support estimate does not replace the measured boundary with a perfect circle. No neighbour averaging of coronal intensity, radiance extrapolation or reconstruction of absent pixels is performed. Pixels farther than the transition band are unchanged.

A cached uint16 coverage map is shared by preview and export and is independent of filter strength/opacity/display colour edits. The PSB/TIFF package adds an editable **Edge Antialias** black Normal layer above the colour/filter layers and below optional Color Correction. This implements the same display fade while retaining each original layer's validity alpha. No extra edge layer is added when no such boundary exists. Native verification composes at full resolution before reducing the result.

Validation uses synthetic curved masks, mixed NaN/zero disks, isolated zeros, bypass/no-hole cases, finite float exports with VALID, edge-cache reuse and final TIFF/PSB equality. A 200×200 crop in original pixels from a real 2750×2084 source was inspected at 3×: the black/corona stair-step is reduced without blurring the surrounding corona. Photoshop 2026 opened the PSB in 16 bits and retained Edge Antialias in Normal at 100%; native recomposition differed from the TIFF by at most 3/65535. Artifacts: `/private/tmp/eip-native-edge-_v59e5o4/`. Whole-image native-resolution performance was not measured in this validation.
