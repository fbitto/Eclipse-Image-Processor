# CPU optimization — 2026-11-01

> Historical report. It records the speed changes, written on 1 November on top of `86f747c` and carried onto `f25cc6b` on 2 November, and how they were measured. Use the [current technical guides](README.md) for the active application.

These changes only affect how long calculations take and how the window responds. No image changes: every layer, the PSB pixels, the main TIFF, the JPEG and the TIFF layer package are the same, bit for bit, as with `f25cc6b`. The PSB file itself differs only in its recipe metadata (see below). No new dependencies were added.

## Changes

- **Threads inside a layer.** `core.parallelism.map_in_threads` runs fixed row strips, tiles or chunks on helper threads within the layer's CPU budget. Every strip performs the same operations as the whole-frame code, so the thread count never changes a value.
  - **AEL WOW (edge-aware):** the 128-row blocks of the paired B3 steps and of the local-power convolution, and the per-pixel steps between them. The 25 shifted taps of a block are views of one zero-padded copy, and the double-precision range weights are formed in place. The mean over the whole kernels stays one serial reduction.
  - **AEL ACHF:** the angular polar and inverse-mapping strips; two isotropic band means in flight; the radial spline evaluated by chunks of rows.
  - **MGN:** `strip_gaussian` runs SciPy's 1-D Gaussian along axis 0 by blocks of columns and along axis 1 by blocks of rows, exactly as `gaussian_filter` does it.
  - **Continuous FNRGF:** the chunks of target pixels; the stable ring-sector sort uses uint16 keys (radix sort) when they fit.
  - **Tangential detail:** the radial tiles.
  - **Fusion and presentation:** layer blending, the display base, the presentation finish, colour neutralization, the Asinh presentation, SetLum and 16-bit quantization.
- **Layer batches.** The longest layer starts first, and the CPU budget is asked again at every threaded step, so the last layer running takes the cores of those that have finished.
- **Memory.** The WOW blocks and the tangential tiles in flight are limited to what fits in a quarter of physical RAM (`memory_bounded_workers`); on a 64 GB machine this does not reduce the thread count.
- **PSB export.** The layers stay in memory: no TIFF is written, read back and hashed per layer. Every distinct channel plane is compressed once, on threads, with the same prediction and `zlib.compress` call as psd-tools, so the file is identical to adding layers one by one. Verification checks each distinct channel once, on threads, by blocks of rows. The 16-bit presentation base is computed once for the PSB and the main TIFF/JPEG, and cached for the views. The PSB metadata now records the SHA-256 of each layer's pixels instead of a TIFF file digest (`layer_sha256` in the recipe says how).
- **Progress.** Long operators report their steps through `core.progress.report` (WOW per scale and sub-step, PSB compression and verification). The GUI does not listen yet.

## Measurements

Input: a 10551 × 7506 RGB float32 stack with missing data around the Moon, on an Apple M4 Max (16 cores, 64 GB), macOS, Python 3.14.7, through the GUI without a window (`QT_QPA_PLATFORM=offscreen`). Five layers: FNRGF, MGN, WOW (AEL edge-aware), ACHF AEL ISO 04 and ACHF AEL Angular; export with the application defaults (PSB layers, PSB presentation). One run per version, the same session, nothing else running; these are illustrative timings, not benchmark medians.

| | `f25cc6b` | this change |
|---|---:|---:|
| Full-resolution verification preview | 228.0 s | 84.2 s |
| Export with the PSB | 182.3 s | 33.8 s |
| Longest GUI stall during the preview (20 ms timer) | 1.06 s | 0.08 s |
| Longest GUI stall during the export | 0.08 s | 0.36 s |

On `86f747c`, the day before, the same measurement gave 222.9 → 76.5 s for the preview and 177.6 → 31.3 s for the export; four runs of the change and its earlier states gave 71–94 s for the preview and 31–32 s for the export. The longest stall during the export is longer than before in every run (0.15–0.36 s, against 0.08–0.14 s); its cause was not found.

Layer times inside the preview (two layers run at once, so they overlap):

| Layer | `f25cc6b` | this change |
|---|---:|---:|
| WOW | 197.5 s | 80.8 s |
| ACHF Angular | 54.1 s | 20.7 s |
| MGN | 54.7 s | 22.2 s |
| FNRGF | 27.5 s | 18.5 s |
| ACHF ISO 04 | 16.2 s | 21.0 s |

The WOW runs in one place of the batch while the other four layers run one after another in the other place, so both take about as long. ACHF ISO 04 ran next to the WOW, which now uses many more cores; it was not measured on its own.

Export: the old route wrote the layer package as TIFF files (31.8 s) and then read, hashed and compressed each layer on one thread for the PSB (120.3 s, of which 31.5 s were the display base, 25.6 s the RGB Color layer and 14.6 s the verification). The new route builds the package in memory (6.5 s), compresses 20 distinct planes on 13 threads (10.8 s) and verifies them (4.1 s).

The WOW now sets the time of the preview. About half of it is OpenCV's level Gaussians (sigma 32–150 px, one call per frame); a faster Gaussian, such as an FFT one, would change the values. On macOS, OpenCV with GCD uses every core from two threads up (`cv2.setNumThreads(2)` in `main.py`); with one thread the sigma-150 Gaussian on this frame takes 60 s instead of 4.6 s.

## Checks

- Full test suite: 421 tests pass; the 394 tests of `f25cc6b` pass unchanged except six that patched replaced internals (`export_layer_package`, `export_psb_package`, `gaussian_filter` in the MGN cancellation tests) and now patch the new ones.
- New tests compare each threaded operator with the previous code (kept verbatim in the test where needed) or with SciPy, with one and several threads.
- On the stack above, the main TIFF, the JPEG, the settings JSON and the five files of the `_sources` folder have the same SHA-256 with both versions. The two PSB files have the same layers, modes, opacities, channel bytes and merged image; their recipes differ only in the per-layer digests, so the files differ by about 200 bytes of metadata.
- Five export cases with all eleven layer kinds on a synthetic image (first by an independent review on `86f747c`, again on `f25cc6b`): every TIFF, JPEG, package and source file was identical, and so were the PSB layers, masks, Color Correction group and merged image. The settings JSON differs only in the path of the source image, because each version ran from its own folder.
- The sRGB profile that `f25cc6b` embeds records the time it was created, so two separate runs differ in that byte even with the same code; for the byte-for-byte comparisons both versions were given the same profile bytes. Without that, the pixels and the profiles apart from the date are equal.
- A synthetic TIFF layer package (all of its 20 files, with prominences and an RGB Color layer) is identical byte for byte.

Not tested: Windows and Linux, and opening the new PSB in Photoshop (its pixels and structure are the same as before).
