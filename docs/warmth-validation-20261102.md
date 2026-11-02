# Sky-protected warmth and preview status — 2 November 2026

Historical acceptance snapshot of the earlier linear-signal warmth rule. The current streamer-aware presentation rule is described in [streamer warmth](streamer-warmth-20261102.md); the preview-status changes below remain active.

Warmth now uses the same native sky-sample settings in preview and export, after optional colour calibration. Background Gradient equalization may remain off. At least six patches with 90% finite RGB support are required; otherwise warmth is bypassed. Patch medians and their channel-wise median limit the influence of isolated bright patches. Samples still need review for faint corona and residual sky gradients.

## Transition checks

For each channel, let `s = max(input - sky, 0)` and `w = 0.1 * max(sky_rgb)`. The warmed excess is `s*s/(2*w)` below `w`, then `s - w/2` above it. With zero sky, use `s` directly. Apply the original warm-gain reduction to this excess only.

This preserves the estimated sky and lower values and keeps every channel monotonic through the transition. With a positive sky level the join has continuous slope. Bright signal retains the original gain slope; faint streamers are retained with a gentler colour adjustment. Synthetic regressions cover the threshold, faint signals, arbitrary positive input scaling, missing patches, isolated bright outliers, inadequate sampling and zero warmth.

## Real-image acceptance

The supplied RGB float32 `master.tiff` is 5608 × 3744 pixels. A separate running application loaded its saved settings and displayed Warm 0, 50 and 100. The background remained blue while the corona warmed; no discrete colour boundary was apparent at the displayed scale.

Full-resolution export comparisons used the saved geometry, sky samples and gradient correction, with calibration on. Detail filters were off in this comparison to isolate warmth. Each setting produced RGB16 TIFF, JPEG and layered PSB files.

| Warm | Preview → TIFF | TIFF → stored PSB composite | JPEG mean absolute error, 8-bit levels | Full-resolution presentation |
| --- | --- | --- | --- | --- |
| 0 | Exact after 16-bit quantization | Exact | 1.33 | 6.13 s |
| 50 | Exact after 16-bit quantization | Exact | 1.33 | 5.34 s |
| 100 | Exact after 16-bit quantization | Exact | 1.36 | 5.38 s |

The timing includes presentation, calibration and pixel conversion, and was collected while other checks were running; it is not a controlled performance benchmark. Normal automatic PSB exposure was active, so displayed sky brightness can vary with warmth even when its sampled input colour is protected. PSB verification checks stored channels and the composite; native Photoshop recomposition was not checked in this run.

Local, ignored acceptance outputs are in `artifacts/warmth-step45/`: `comparison.png`, `real-image-results.json`, the test exports, the probe script and logs. The original TIFF and saved settings were not modified.

## Status timing

Filter calculation previously published “preview ready” before asynchronous colour composition, tone mapping and pixel conversion. It now publishes “Preparing preview…” and waits for the current presentation to install its display pixels. Stale presentations cannot clear a pending-settings message. Console idle reporting also counts running or queued presentation jobs.

Blocked-render regressions verify that readiness waits for the accepted display and that superseded renders cannot publish readiness. The running app was observed showing the amber preparation status before the new pixels and the green ready status afterward.

Geometry edits invalidate colour caches immediately but defer presentation for 100 ms, avoiding work on intermediate geometry. A prominence-preview regression also exposed GIL starvation in the Qt test wait loop. The helper now yields briefly to Python worker threads as well as processing Qt events, without increasing its timeout.

## Automated regression result

All **439 tests passed** in **102.73 s**, using the application CPU initialization followed by standard-library unittest discovery over `tests`. The final log is `artifacts/warmth-step45/unittest-final.log`. The initial run exposed an outdated idle-status expectation and the prominence wait timeout; both were investigated, corrected and covered by the passing final run. `git diff --check` also passed.
