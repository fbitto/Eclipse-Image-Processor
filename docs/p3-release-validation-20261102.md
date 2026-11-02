# P3 release regression — 2 November 2026

macOS portion completed; Windows build/run acceptance remains pending on the owner's separate machine. P4 is prepared as a [local response draft](issue-3-response-draft.md), not posted. Subsequent [P2 native cost and responsiveness checks](p2-native-performance-20261102.md) are complete; maximum-support completion time remains deliberately unmeasured.

## Source and regression checks

Base source: 5cfe084, with two tooltip-only corrections found during the bundled smoke test. No numerical behavior changed in this checkpoint. The presentation section no longer says the main TIFF is unchanged by exposure; the layer-export tooltip distinguishes its scaled 16-bit preview from separate float32 working sources. Current layer-support documentation no longer claims local/NRGF statistics and targets are still coupled.

- Complete suite: **394 tests passed in 178.151 seconds** (`/tmp/eclipse-p3p4-20261102/full-suite.log`).
- After tooltip corrections: **33 GUI interaction tests passed in 20.899 seconds** (`final-gui-tests.log`). No broad retest was needed for these two text-only changes.
- P4 draft checks: all items 1–50 appear exactly once; every application commit referenced by its table resolves locally.

## macOS build and package checks

Environment: macOS 27.2 arm64, Python 3.14.9, PyInstaller 6.22.3. Historical pre-0.7.0 application/bundle; these checks do not validate a rebuilt 0.7.0 package. The final build used `scripts/build_macos.py --dmg`. App and installer outputs are ignored by Git.

- `dist/Eclipse Image Processor.app`: Apple Silicon arm64 executable; ad-hoc signature passed `codesign --verify --deep --strict`.
- `dist/Eclipse Image Processor.dmg`: **155,744,738 bytes**; `hdiutil verify` passed.
- DMG SHA-256: `ee0f7efdde64c8442104aca88307e0a5ec3bd07652440b5f2243b460694cadef`.

The first sandboxed build completed the app but could not access Apple's disk-image service. The DMG step succeeded with the required execution access. The final complete build, including both tooltip corrections, also completed and verified successfully. No system protection was disabled.

## Bundled application smoke test

The actual final .app was launched and operated through its native UI, without the development interpreter. A representative legacy v4 recipe was constructed with:

- Decimal geometry `(320.25, 240.5, 60.75)` and a synthetic 640×480 RGB float32 source with a missing central disk.
- The retired adaptive Background Retention key and old `AEL bilateral` WOW selector label.
- Omitted new optional AEL-support checkbox and log-Larson selector.
- An active NRGF layer and editable PSB export enabled.

This is a compatibility fixture, not a claim that every archived recipe/version was replayed. The final package loaded it, displayed the exact geometry and reported successful export of all five product destinations: TIFF, JPEG, JSON, PSB and working-source folder.

Independent reading of `bundle-final.*` confirmed RGB uint16 640×480 TIFF, RGB16 PSB, embedded display profiles, exact TIFF/cached-PSB pixels, settings/decimal geometry restoration, exact measured float32 RGB source values and matching validity. Both the original build and final tooltip-corrected build passed; final verification is in `bundle-final-report.json`. The owned application instance was closed after the check.

The final app's accessibility state also confirmed both corrected export tooltips. Generated recipes, exports, reports and build logs remain under `/tmp/eclipse-p3p4-20261102/`; no private or generated images were added to Git.

## Windows handoff and release limits

The owner will test on a separate Windows machine. Use the same source revision and record Windows/Python/PyInstaller versions. On that machine:

1. Build with the documented Windows builder and launch the packaged executable.
2. Load a legacy recipe with decimal geometry, including a source on a different drive; verify parameters and missing support.
3. Export a small TIFF/JPEG/JSON/PSB/source package; reopen JSON and PSB; confirm dimensions, bit depth and matching names.
4. Repeat export and check every companion shares the new stem.
5. Export to physical exFAT if available, then cancel and close during an export; retain errors and report any completed companions.

Do not treat macOS-to-exFAT success or Windows path unit tests as Windows execution. No Windows binary was cross-built on macOS. Intel macOS, clean-machine installation, downloaded-file Gatekeeper quarantine, Developer ID signing and notarization were not tested. The local ad-hoc package is not a signed/notarized public release.
