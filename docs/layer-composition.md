# Independent filter composition

The desktop application now uses the same layer model for fast preview, native verification, final TIFF/JPEG, TIFF layer packages and PSB. The former sequential numerical pipeline remains an internal operator dispatcher and compatibility API; the GUI sets `layered_model=True`.

## Inputs and composition

Every filter receives the immutable original monochrome image at the requested resolution, with its validity and statistical support. Fast preview area-averages the original data to the preview size and scales spatial controls; no other enhancement or display curve is passed to a filter. A file already stretched before loading remains stretched: the linear declaration does not recover original measurements.

The original forms the base, normalized and stretched once with Asinh, Log or GHS. The GHS shadow picker samples this original base. Encoded detail layers are then composed in this order:

| Layer | Fixed Photoshop blend mode |
| --- | --- |
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

There is no additional normalization, gamma or stretch of the finished composition. A Color layer supplies RGB in native verification and export; fast preview remains monochrome. The PSB and TIFF loader add an opaque black background without modifying original layer alpha. Final TIFF/JPEG and the cached PSB composite show missing-data areas as black. Float source products and validity masks retain the distinction between missing observations and measured black pixels.

## Controls

Each filter has **Opacity (%) before Strength (%)**. Opacity defaults to **50% for every filter and ACHF variant** and is independently editable from 0 to 100%. Defaults are starting points, not measurements or AEL-author recommendations. Strength controls encoded layer contrast around the blend mode's neutral value; it participates in the filter cache signature. Opacity only mixes the cached layer. A zero Strength is neutral and exports hidden. Reveal scales each layer opacity; it does not trigger numerical filtering.

The ACHF selector selects the panel to edit. **Include in composition** checkboxes independently enable any combination of Adaptive, ISO 01, ISO 04 and Angular. The ACHF section's Active checkbox gates the entire family. Adaptive starts included; the three AEL variants start excluded. All values persist when switching panels. Layer export automatically writes all active variants and omits excluded variants, so the cached PSB image matches the selected composition.

## Cache and export

A worker retains at most two source identities (normally fast and native resolution), with one configuration per filter/variant. Keys include that filter's controls, geometry, spatial adaptation and support masks. Opacity, activation and display controls do not invalidate the numerical layers. Disabling/re-enabling a calculated filter retrieves its cached layer. Editing another filter leaves it reusable. Changing source, resolution, geometry or support invalidates the affected layers; changing Strength or a filter parameter replaces that filter's current configuration. Returning to an earlier parameter value after editing can require calculation again: this is not a history of every setting.

Only successfully completed, uncancelled layers enter the cache. Finished layers survive cancellation of a subsequent stage. Source arrays are immutable within a job; replacing a source creates a different identity. Export receives an isolated cache dictionary sharing read-only native layer arrays with its source snapshot. It builds layers/PSB first, then writes the final TIFF/JPEG; the final composition reuses the prepared layers. On worker completion, completed export layers are merged back into the window cache only if the original source identity still matches. This also retains ACHF variants that were first computed for all-variant export, avoiding their repetition on subsequent saves.

Layer RGB and alpha and the base are quantized to RGB16 for a common display reference; opacities are quantized to 1/255, matching Photoshop layer records. Composition uses float intermediates. TIFF and the PSB cached reference agree on the resulting 16-bit pixels. A native Photoshop recomposition may round differently or differ under color management; byte checks alone do not establish a native color-match guarantee.

The default fixed modes are Multiply, Overlay and Linear Light; Soft Light is not exposed by this change. The requested design retained fixed modes rather than adding a mode selector.

## Validation

Deterministic tests cover original input for every branch, blend equations, order, opacity-only changes, activation round trips, unrelated edits, Strength, source/geometry/mask invalidation, bounded caches, multiple ACHF variants, cancellation, GUI row order and final TIFF/PSB equality.

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
