# Qt GUI patterns

- PySide6 QThread tasks must receive snapshots of arrays and scalar settings; read widgets and install QPixmap only on the GUI thread.
- Coalesce presentation jobs and check both source identity and request revision before showing results. Colour caches can be reused only for the same source and colour revision.
- During close, ignore the event while workers finish and retry from their finished signals. Waiting synchronously prevents progress events and freezes the window.
- Offscreen GUI tests must process Qt events until asynchronous results and deferred closing complete.

- Native zoom uses source pixels per physical screen pixel: logical scale = zoom / devicePixelRatioF(). Paint only the visible QImage source rectangle; do not allocate a 200% QPixmap. Keep NumPy owners alive for zero-copy QImage buffers. Fit and native display bytes are separate from scientific/export arrays.

- Background equalization operates on preserved native linear sources in a TaskThread before any enhancement layers. A source change invalidates colour/native display caches; previews and export share the same prepared input. Sky-sample editing uses native coordinates and middle-button panning to keep left/right clicks available.

- Cache display normalization extrema on native source load/preparation in worker threads. Reuse the same levels for fast/native base stretch, RGB luminosity and GHS sampling; independently normalizing the reduced image can shift the entire sky brightness. Source identity guards prevent stale extrema after a new image.

- Keep GUI tone curves out of numerical/composition cache signatures. Cache the normalized uncurved mono composition; render the selected presentation in the background worker and for the JPEG export. Editable Photoshop presentation uses its own explicit receipt and hidden scaled linear reference.

- Photoshop exposure preview is a transient checkable button, excluded from saved controls. Save only the EV slider; the current JSON format stores it explicitly. Native sampling chooses one scale for fast/native preview and export, after colour calibration, and tone mapping uses row tiles. The GUI now exposes only PSB presentation: old Display Stretch widgets and the GHS picker are removed, old JSON formats are rejected without migration, and PSB preview defaults on. Exposure affects JPEG as well as the screen and layers, but never the main TIFF.

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
