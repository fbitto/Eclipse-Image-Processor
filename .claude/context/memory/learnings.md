# Qt GUI patterns

- AEL ACHF bounded encoding/gain controls carry `bounded_contrast_control` so Basic retains them in ISO04/Angular cards. Enable the gain's whole parameter_row only in bounded mode. Keep per-variant settings optional; Follow ignores gain in cache keys, bounded ignores global normalization. ISO01 gain is capped at 2 after the unchanged injection-correlation criterion rejected 4; ISO04/Angular allow 4.

- Windows JSON tests must read UTF-8 explicitly when comparing persisted selector text. File readers (including TiffFile in tests) need context managers: Windows cannot remove open files. Layer scheduling must use physical_memory_bytes rather than assuming os.sysconf exists; the helper already supports GlobalMemoryStatusEx.
- Native Windows file-dialog accessibility focus can describe the search box while the screenshot shows the filename caret. Target the related dialog screenshot, inspect visible focus and entered text, and refresh after each action. Packaged recipe/export/cancel/close checks succeeded through the native UI using this workflow.

- PySide6 QThread tasks must receive snapshots of arrays and scalar settings; read widgets and install QPixmap only on the GUI thread.
- Coalesce presentation jobs and check both source identity and request revision before showing results. Colour caches can be reused only for the same source and colour revision.
- During close, ignore the event while workers finish and retry from their finished signals. Waiting synchronously prevents progress events and freezes the window.
- Offscreen GUI tests must process Qt events until asynchronous results and deferred closing complete.

- Native zoom uses source pixels per physical screen pixel: logical scale = zoom / devicePixelRatioF(). Paint only the visible QImage source rectangle; do not allocate a 200% QPixmap. Keep NumPy owners alive for zero-copy QImage buffers. Fit and native display bytes are separate from scientific/export arrays.

- Background equalization operates on preserved native linear sources in a TaskThread before any enhancement layers. A source change invalidates colour/native display caches; previews and export share the same prepared input. Sky-sample editing uses native coordinates and middle-button panning to keep left/right clicks available.

- Cache display normalization extrema on native source load/preparation in worker threads. Reuse the same levels for fast/native base stretch, RGB luminosity and GHS sampling; independently normalizing the reduced image can shift the entire sky brightness. Source identity guards prevent stale extrema after a new image.

- Keep GUI tone curves out of numerical/composition cache signatures. Cache the normalized uncurved mono composition; render the selected presentation in the background worker and for the JPEG export. Editable Photoshop presentation uses its own explicit receipt and hidden scaled linear reference.

- Photoshop exposure preview is a checkable button saved explicitly as btn_psb_preview alongside EV; v4 recipes omitting it default on. Native sampling chooses one scale for fast/native preview and export, after colour calibration, and tone mapping uses row tiles. The GUI now exposes only PSB presentation: old Display Stretch widgets and the GHS picker are removed, old JSON formats are rejected without migration, and PSB preview defaults on. Exposure affects JPEG as well as the screen and layers, but never the main TIFF.

- On source load, call dispatch_pipeline_request_if_auto before render_matrix_to_screen: dispatch invalidates the filter revision even in manual mode. Rendering first caused the initial presentation result to be rejected as stale, leaving manual loads blank. Cover source load with an actual installed preview assertion.

- The application pipeline always composes independent layers. Use apply_filter only for one numerical operator; it rejects multiple active filters. Do not reintroduce a sequential path or use the retired layered_model flag to switch behavior.

- Settings format v4 is the only supported JSON version. Do not restore legacy strength/opacity, Reveal, display-curve or MGN-unit migrations. Missing filter controls remain optional and reset inactive by current product behavior; current global controls are required.

- Disk-overlay visibility is transient viewport state: toggle only ImageView.update(), keep geometry and pixel buffers unchanged, and restore circle/cross visibility on every source load. Larson–Sekanina radial offset is fixed at zero by GUI parameter collection; no radial slider is constructed.

- Prominence presentation receives original_source_rgb, assigned only on file load; full_source_rgb may be replaced by background preparation. Snapshot the original reference and exposure on the GUI thread, calculate masks in render_snapshot/export workers, and keep the prominence view selector transient. New optional prominence settings default off when absent from v4 JSON.
- Select prominence masks at native resolution before area reduction. Red-excess thresholding after reducing RGB can erase thin features; reduce premultiplied RGB and coverage separately to avoid colour bleeding from excluded neighbours.
- Prominence presentation has no geometric lunar-disk exclusion. A fitted circle may enclose observed red pixels near a missing-data gap; preserve those pixels. Missing input pixels, including an upstream lunar margin, cannot be restored by exposure or mask changes.
- A warm orange corona can pass R-max(G,B) and turn the low-exposure Normal layer into a dark ring. Prominence selection discounts max(G-B,0) in both native masks and reference sampling; preserve original exposed RGB, and test orange continuum alongside pink and pure-red signal.
- Fractional OpenCV INTER_AREA footprints can sum below one at valid borders (2401→1500 gives 0.999167). Determine resized support from area-averaged missingness, not weights≈1; retain value/weight normalization and test an actual missing border pixel separately.

- Export overwrite confirmation covers TIFF, preview JPEG and settings JSON together; disable the native TIFF-only confirmation. Resume pending auto-preview when the dialog is cancelled or source protection rejects the destination, before creating an export worker.

- Warmth belongs to the colour revision/cache, not the numerical filter signature. Apply gains after neutralization in the presentation worker and export. Prominence saturation uses original RGB after mask selection; keep it independent of corona warmth.

- Do not infer numerical settings from isEnabled(): a disabled sidebar makes every descendant report disabled. Snapshot WOW thresholds using the selected scale count. Background tasks must copy their sample list and compare source identity plus fit settings before accepting a result; resume pending preview requests when exports finish.

- For cold native FITS GUI smoke checks, run the normal QApplication event loop with timer-based assertions. Tight QTest.qWait polling delayed the load worker beyond 60 s; the same native RGB source and saved recipe completed in 0.81 s with app.exec().

- When retiring a GUI-only filter control, remove its slider and advanced-mode registration together. Explicitly ignore that known retired key during both settings validation and application, so existing v4 recipes still load; omit it from new captures. ACHF background retention remains numerical-API-only.

- Route numerical control releases and value changes through their filter-section activation gate, including combo boxes and advanced scales. ACHF additionally gates excluded variant panels. Use toggled for compare-button state so programmatic unchecking updates its label/mode. Preserve geometry as one blocked-signals snapshot on source replacement.

- Keep Cancel export outside the disabled sidebar/zoom toolbar. Give export workers their own cooperative token; stop accepting cancellation at publication. Distinguish cancellation from exceptions and close by requesting cancellation, never terminating a QThread during a write.

- Experimental AEL support separation is an optional geometry/statistics checkbox, default off in omitted-field v4 recipes. Keep observed kernel support distinct from radial-fit/display samples, and gate the checkbox’s invalidation when no AEL layer is active. Coverage cannot override undefined model/kernel support or positivity restrictions.

- Audit explicit sliderReleased callbacks as well as generic valueChanged wiring: built-in NRGF geometry, FNRGF protection and Larson gain need the same inactive-family gate. When clarifying selector labels, whitelist old text at its original index so v4 recipes stay readable.

- Current-AEL RHEF parity includes float32 log/quantile/accumulation and even redundant angular interpolation terms. Keep the independent float64 numerical default explicit; application reference precision must be tested against frozen upstream values. Reuse immutable ICC bytes within a process: profile creation timestamps otherwise make identical JPEG exports differ across a second boundary.

- Package smoke checks must inspect section-level tooltip maps as well as individual sliders: stale presentation help can contradict corrected export semantics. Verify the rebuilt bundle, not only the development interpreter. On this macOS sandbox hdiutil needs elevated tool access to its disk-image service; app building/signature verification can succeed before the DMG step fails.

- Prominence highlight limiting by per-pixel peak normalization flattens every over-range intensity. Use a shared smooth shoulder after exposure/saturation and keep the selection independent. Any inward mask feather must limit its width by local feature thickness to retain isolated one-pixel chromosphere; never expand support or fill missing pixels. Preview selection remains native before reduction.

- A Basic QSlider cannot narrow its range without clamping a negative saved EV. Keep the canonical full-range recipe control and use an unpersisted Basic editor with a retained-value notice; block synchronization signals. Initialize prominence mode wiring after Advanced mode exists. New contrast fields default to unity for legacy recipes and must reach both render jobs and export requests.

- Missing-source recovery must catch its own FileNotFoundError subclass, not a missing/corrupt JSON. Validate recipe controls before asking to locate the image; cancel before changing revisions or stopping current work. Keep JSON untouched until explicit save and carry the relocated path into subsequent exports. Try legacy Windows backslash relatives after literal native paths.

- Prominence edge softness uses native pixels and must travel in both presentation jobs and export requests; optional recipe fields restore the historical 3-pixel feather. Keep the slider in both UI modes and gate it with the RGB prominence checkbox.

- Reparent canonical ACHF controls into independent cards rather than duplicating parameter state. Restore card expansion independently from canonical include flags so saved section activation cannot enable an omitted variant. Apply Basic restrictions after recipe restoration and source defaults, batching signals into one pipeline request. Persist UI levels by stable string; translate legacy combo text/index pairs before strict validation.

- File drops and the open dialog share EclipseProcessorApp.open_file and its asynchronous TaskThread loader. Accept one existing local image/JSON only; reject drops while loading, closing or the sidebar is disabled.

- Fresh windows start in Basic; saved ui_mode and legacy Advanced-to-Standard/Expert mapping still govern recipe restoration. Tests exercising all-filter controls must select Standard explicitly.

- OpacitySlider keeps QSlider values/signals in integer percentages for recipes, reset and keyboard/accessibility; custom painting and pointer mapping alone apply the 1.5 travel curve. All filter and ACHF opacity factories use it; Gain remains linear.

- General warmth and additive Corona warmth share colour_layers across render/export/packages. Derive sky/corona masks from the untinted presentation once; unsupported fits bypass only masked stages. Keep sl_warmth for old corona recipes, default new general/green fields to 0/off, and snapshot them without invalidating numerical filters.

- Prominence composition must not depend on PSB preview being on. Explicit mask/on-black selection exits View Original. Green-sky reduction now carries a separate 0–100% strength (75% default) through settings and worker/export snapshots; source prominence masks remain independent of warmth/green controls.

- Approved colour-validation source is the explicit CoronaHDR_Work/.coronahdr-jobs/e1c3c474c41b4163b9c04099bb909948/result/master.fits. Do not tune the app from the rejected artifacts/.coronahdr-jobs/596a8739cfd846ef97b19c8408a73420 master; its experimental prominence-selection fallback was removed. User warmth reference is amber/orange with a near-white inner rim, not rose/magenta.

- User clarified this is a sunset eclipse: visual references are amber/orange corona with a near-white inner rim and copper/brown sky with reddish horizon glow. Preserve sky gradients and genuine sunset colour; do not apply blanket magenta removal or tune from the rejected master.

- NAFE implementation selector stays visible in Basic mode: default AEL original; optional EIP limb-aware response uses the same radial spline/NAFE on observed support only. Preserve its experimental label and dark innermost-limb limitation. Preview scales both window and Gaussian widths; scale 1 stays native-exact.

- AEL WOW noise reduction is a separate numeric control, not a mix-only slider. Keep its row visible in Basic and disable it for watroo modes. Existing filter-widget snapshots supply optional-field reset-to-zero; do not alias the retired noise-floor or watroo threshold controls.

- Filter normalization is a global optional v4 combo in Geometry: missing recipes reset Compatible. Revised changes ACHF/Tangential and continuous FNRGF only. Exclude it from unrelated filter cache keys (especially expensive NAFE); keep it in affected signatures and export receipts. Basic must keep the selector visible; use native source normalization bounds for linear signed-detail scale in preview and export.

- Tangential source-relative encoding is an optional filter-owned combo below opacity (Standard/Expert), defaulting to Follow filter normalization. Its reference uses allowed source statistics independently of output limits. In source_relative mode, exclude global normalization_mode from its cache key/metadata; changing that unrelated setting must reuse the layer. Keep approximate preview and empirical-noise warnings explicit.

- Basic six-layer starter is applied only after first direct-image heuristics via apply_basic_starter. Never apply it in apply_ui_level or reset_filter_defaults: that would overwrite mode-switch edits or omitted controls in old JSON recipes. Basic now permits FNRGF and Tangential.
