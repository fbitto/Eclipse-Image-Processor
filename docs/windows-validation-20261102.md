# Windows validation — 2 November 2026

Requested regression, native packaged recipe/load/export/reopen, cross-drive
source and export-interruption checks are complete. Final full suite:
**429 tests passed in 329.295 seconds**. Native Photoshop rendering checks also
completed as recorded below. External-drive and exFAT testing are excluded from
this validation scope at the owner's explicit request; they are not pending
acceptance tasks. No public release or blanket Windows acceptance pass is claimed.

## Environment and fixes

Windows 11 build 26200, AMD64, 24 logical CPUs, 63.93 GiB RAM, Python 3.14.7,
NumPy 2.5.4, SciPy 1.18.1, OpenCV 5.0.0.93, PySide6 6.12.0,
PyInstaller 6.22.3; application 0.6.0. Baseline:
`43907e02f3c9f9438d74947f5d625ab6ecd44237` plus the changes below.
Existing runtime dependencies were retained; pinned packaging dependencies were
installed in the project virtual environment.

The initial full run completed 429 tests with eight failures and two errors.
Investigation resolved them as follows:

- **Numerical references:** all three ACHF variants and both RHEF scenes matched
  independently downloaded pinned upstream AEL exactly on this Windows runtime.
  Upstream itself differs from the frozen macOS outputs. ISO 04 showed roughly
  1.073e-6 maximum float difference and up to one encoded uint16 level; RHEF scene
  maxima were 6.765127e-6 and 1.949072e-5. Disabling NumPy AVX2/FMA3/AVX512F
  did not remove the ACHF differences; the exact backend operation was not
  isolated. Retained macOS fixtures and added Windows fixtures generated directly
  by upstream. Exact RHEF/export assertions and existing ACHF tolerances remain;
  no filter arithmetic changed. See [provenance](../tests/fixtures/ael_windows.md).
- **Recipe label:** the test decoded UTF-8 JSON with Windows' default encoding.
  The test now specifies UTF-8; production reading already did so.
- **File handle:** a test left TiffFile open, preventing Windows temporary-file
  cleanup. It now uses a context manager.
- **Paths:** resource_path normalizes separators, including frozen fallback
  resources. Native ICO and PNG fallback tests pass.
- **Scheduling:** layer_workers assumed os.sysconf existed and therefore used
  the unknown-memory fallback on Windows. It now uses physical_memory_bytes,
  including the existing Windows GlobalMemoryStatusEx query. Its test mocks this
  platform-neutral boundary and retains unknown-memory, CPU and size limits.

The colour-preview module appeared stalled while early logs were incomplete,
but its isolated five-test run passed in 82.029 seconds and the final full suite
passed it too. It was not a confirmed hang. Intermediate diagnostic runs are
retained; only the final complete suite is acceptance evidence.

## Rebuilt package and native UI

Rebuilt with `scripts/build_windows.py` after the production fixes. Output:
`dist/Eclipse Image Processor/Eclipse Image Processor.exe` with `_internal`.
Distribute the whole directory. This is a local unsigned build.

Executable: 21,082,545 bytes; SHA-256:
`2f9c6fc23d4028ff99bb77922d7380b33013971ad08bd032342e351c9041fbcd`.

The actual rebuilt executable was operated through the native Windows UI:

1. Opened a temporary v4 recipe on **C:** referencing the supplied TIFF on **D:**.
   The fixture derived from the supplied recipe with manual calculation,
   background fitting disabled and geometry (3013.25,1688.5,273.0). FNRGF, MGN
   and selected ACHF variants remained active. The window restored decimal
   geometry and reported all 226,939 missing pixels.
2. Exported the full **5608×3744** canvas with editable PSB, Color Correction,
   prominence products, TIFF/JPEG/JSON and working sources. The application
   reported successful completion of all destinations.
3. Reopened the exported JSON through the packaged Open dialog; the original
   TIFF and decimal geometry restored successfully.
4. Started another full-resolution export and clicked **Cancel export** during
   processing. The UI reported cancellation and returned idle; no files for
   `packaged-cancel` were published.
5. Started another full-resolution export and closed the window during
   processing. Cooperative shutdown completed and the owned window disappeared;
   no files for `packaged-close` were published and no error dialog was observed.

Cancellation/close were requested early during processing, not during a confirmed
codec write. They do not establish interruption of every export phase. The owned
packaged application was closed at the end.

Dialog accessibility focus sometimes described the search box while screenshots
showed the filename caret. Screenshot-guided input and checking entered text
resolved this automation issue without an application change.

## Independent output verification

Independent reading of `packaged-full` confirmed:

- RGB uint16 TIFF and matching JPEG dimensions with RGB display profiles.
- RGB16 PSB with 11 top-level entries and cached merged pixels exactly equal to
  the TIFF. Reopened with psd-tools, not native Photoshop.
- Every exported float32 RGB source value exactly matched the original after
  documented zero encoding of missing pixels; VALID matched all 226,939 missing
  samples. Exported JSON retained decimal geometry exactly.
- TIFF, FITS and supplied JSON SHA-256 hashes remained unchanged.

PSB: 975,773,458 bytes; TIFF: 117,528,499 bytes. The input TIFF matches the prior
macOS acceptance source hash:
`39f1544b4e7485f05e91b08282b74f0cdb48fde8c0810be781b3b5192dbf7ac1`.

Earlier source-runtime checks loaded the original recipe through the asynchronous
GUI loader, resolving its obsolete macOS path to the adjacent Windows TIFF.
The FITS application loader returned a 3744×5608 mono canvas, 3744×5608×3 RGB
and 273,060 missing samples. Two 700×600 crop exports verified coherent repeated
names `smoke`/`smoke_2`, RGB16 PSB/TIFF pixel equality and JSON source resolution.
Those checks are separate from the full-native packaged export above.

## Native Photoshop on Windows

Adobe Photoshop 2026 **27.11** (`20260929.r.26 8c16e56`) opened the full-native
`packaged-full_PS_layers.psb` successfully as RGB/16, 5608×3744. Its embedded
sRGB profile was retained when Photoshop reported a mismatch with the user's
Adobe RGB working space; no conversion or working-space preference change was
made. The native Layers panel showed the prominence image/mask, Color Correction
group and adjustment masks, Edge Antialias, RGB Color and enhancement layers.

Saved separate flattened, uncompressed RGB16 TIFF copies with the embedded RGB
profile. Color Correction was initially enabled in this export. Disabled it for
the comparison with the application's TIFF, then toggled Edge Antialias off/on
to force a fresh layer recomposition and saved a further copy. Measurements are
absolute uint16 channel-level differences over the full canvas:

| Photoshop render versus application TIFF | Maximum | Mean | 99th percentile |
| --- | ---: | ---: | ---: |
| Color Correction off | 7 | 1.128573 | 4 |
| Forced recomposition, correction off | 7 | 1.128573 | 4 |
| Color Correction on | 5473 | 257.003405 | 2359 |

The two correction-off Photoshop renders are pixel-identical. Their small
differences from the application TIFF are consistent with rendering/quantization;
exact native equality is not claimed. The correction-on result deliberately
changes colour and is not expected to match the application preview/TIFF. This
is full-native Windows Photoshop evidence, beyond cached-PSB inspection.

At 100% view, inspected the prominence/limb features and toggled the prominence
layer off/on. The layer changes those features as expected. Its linked mask is
editable; Photoshop reports density 100% and additional feather 0 px (the
application's 3-native-pixel softness is already encoded into the mask). This is
a rendering/interoperability check, not independent observational detail or
universal visual-quality acceptance. The export uses +3 EV, 25% saturation,
contrast 1 and softness 3; native Photoshop rendering at contrast 2/softness 20
was not checked.

The original PSB SHA-256 was checked before and after the work and is unchanged.
Only the owned validation document was opened and closed without saving edits
to the PSB; no existing user document was modified. Photoshop remains open at
its home screen. Separate renders and measurements remain ignored under
`artifacts/windows-validation/`: `ps-native-color-on.tif`,
`ps-native-color-off.tif`, `ps-native-recomputed.tif`,
`photoshop-comparison.json` and `photoshop-input-hash.json`.

## Evidence and limits

Ignored logs: `windows-validation-final-suite.log`,
`windows-validation-rebuild.log`, `windows-validation-packaged-inspection.log`.
Ignored `artifacts/windows-validation/` contains manifests, pinned upstream
checkout/comparisons, local runners, generated recipes/products,
`export-report.json`, `packaged-ui-report.json`, `native-report.json` and
`load-report.json`. The temporary C: recipe location is recorded in
`cross-drive-location.json`. Private images and generated outputs are not intended
for commits; fixture archives contain only synthetic scenes.

External-drive and exFAT testing were not performed and are explicitly excluded
at the owner's request. No further checks of external drives or exFAT are planned.
The C:/D: recipe check above verifies source-path handling only and does not
establish external-drive or filesystem compatibility.

Not tested: clean-machine installation, Authenticode signing, installer or public
release. Native Photoshop scope is limited to the case above.
Independent observational detail acceptance still requires independent stacks.
Numerical evidence covers this dependency/backend combination, not universal
cross-platform byte equality.
