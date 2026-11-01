# P2 native runtime and responsiveness — 2 November 2026

Completed against f25cc6b on macOS 27.2 arm64, Python 3.14.9. These are measurements on this machine and supplied master, not a portable runtime guarantee. No application code or default changed.

## Adaptive ACHF cost

Input: supplied margin--2px RGB float32 TIFF, application mono canvas 5608×3744. Source SHA-256 remained `39f1544b4e7485f05e91b08282b74f0cdb48fde8c0810be781b3b5192dbf7ac1`. No saved background fit was reapplied. Each case ran in a separate process with the real independent-layer path, 10% relative neighbor threshold and captured native geometry/settings. The selected branch was explicitly adaptive ACHF.

| Case | Radius, native px | Complete layer, seconds | Filter, seconds | Encoding, seconds | Peak process RSS |
| --- | ---: | ---: | ---: | ---: | ---: |
| Captured image default | 6.731 | 10.484 | 8.612 | 1.800 | 3.30 GiB |
| Twice the radius | 13.462 | 35.756 | 33.849 | 1.832 | 3.30 GiB |
| GUI maximum, cancelled | 74.773 | 3.073 before cancellation | Not completed | Not reached | 2.63 GiB |

The default is image-dependent: the first two radii correspond to 1.8 and 3.6 preview pixels for this canvas; the GUI maximum is 20 preview pixels. Peak RSS includes loading and encoding, not an isolated filter allocation. It does not predict peak use with multiple concurrently active filters.

Doubling radius increased measured filter cost by **3.93×**, consistent with the documented quadratic work. Both completed layers retained zero alpha at every missing pixel. Their support was 20,761,787 pixels. Source hashes were checked after each run.

For the maximum-support case, a separate timer requested cancellation after three seconds; the operation stopped **0.071 seconds** after that request. Its full completion time was deliberately not measured. A radius-squared extrapolation is still only an estimate, not a native maximum-runtime benchmark.

## Native GUI event-loop checks

A separate automated integration run used a real **Qt Cocoa desktop window**, source-load thread, numerical worker and normal `QApplication.exec()` event loop. Numerical operators were not mocked. The macOS sandbox initially could not access a screen; the same check then ran with the required window-service access. Only its owned test window was opened/closed.

1. Started full-native adaptive ACHF at 13.462 px radius.
2. Edited an inactive MGN parameter and emitted its release: preview revision stayed unchanged and the worker cancellation event remained clear.
3. Changed center X from 3013 to 3013.25 and reduced support to 6.731 px. The obsolete job cancelled once, the quiet-period queue resumed once, and the second request captured the new geometry/support.
4. Exactly one job finished; the accepted full-resolution cache matched the latest revision. No stale result was accepted, no failure was emitted, and the queue ended idle.

With a 50 ms heartbeat timer, the largest observed gap during processing was **65 ms**. Total scenario time was 13.87 seconds; the completed final layer took 10.46 seconds. This measures event-loop scheduling, not manual input latency or every presentation/export workload.

A further native Cocoa run exercised close during a real export worker calculation with a synthetic 1280×1024 input. It completed cooperative cancellation without publishing a TIFF or reporting an error. This complements the earlier physical exFAT pre-publication cancellation check; it does not claim that an active codec write is interruptible.

Existing cancellation/quiet-period/isolation regressions also passed: **4 tests in 1.274 seconds**. The preceding P3 full suite remains 394 passing tests; no application code changed here, so the full numerical suite was not repeated.

## Decision

Keep the current kernel and controls. Measured default runtime, bounded memory and cooperative cancellation do not justify a new implementation or another cost control. The current support tooltip already explains quadratic cost and recommends native verification/cancellation. Larger supports remain an explicit expensive choice; use the measured table as an example rather than showing an uncalibrated ETA on other machines.

P2's requested measurements and scheduling checks are complete. Windows acceptance remains with the owner's separate machine. Independent observational fine-detail acceptance remains unavailable without independent stacks. No issue comment was posted.

Artifacts and assert-based runners are outside Git in `/tmp/eclipse-p2-20261102/`: `default.json`, `double.json`, `extreme.json`, `native-gui.json`, `gui-close-report.json` and logs. Private images and generated output were not committed.
