# ACHF AEL variants

Source authorship and the exact copied/adapted or imported components are listed in [ATTRIBUTIONS.md](../ATTRIBUTIONS.md).

Added 24 October 2026 as optional ISO 01, ISO 04 and Angular variants; Adaptive circular remains the initial selection.

The port in `core/ael_achf.py` follows Agentic Eclipse Library 1.3.3's `filterbank.achf_isotropic`, `radial_log_residual`, `display_detail`, `tangential_highpass`/linear polar mappings, and support-normalized Gaussian routines. Copyright © 2026 Pere Guerra Serra; [MIT notice](third-party/AEL-MIT.txt). No plugin path or AEL installation is needed at runtime.

On full-resolution positive observed luminance, it subtracts the upstream cubic spline fitted to annular log-intensity medians in log radius, averages five Gaussian high-pass residuals and applies an outer Gaussian. ISO 01 starts at native sigmas 2/4/8/16/32 and outer sigma 3; ISO 04 starts at 1/2/4/8/16 and outer sigma 1.5. These are independently editable for each preset. Angular subtracts a 1° angular Gaussian on log-luminance in a linear polar grid, maps the detail back with complete bilinear observed support, and starts with outer sigma 4 native px. Its two widths are also editable. Polar rows are tiled for bounded intermediate memory. It uses the upstream MAD floor 1e-5 and `0.5 + 0.5*tanh(detail/(2.5*scale))` encoding without median subtraction. Gaussian approximations for wide supports also follow upstream. Nonpositive values do not enter the logarithm and remain unchanged; missing values are not filled. Sparse scenes produce an explicit error when the radial fit lacks support.

The desktop layer model computes each variant from the original linear input. Strength controls encoded detail contrast, and its separate Opacity controls Overlay blending over the stretched original base. The completed composition is not stretched again. The legacy numerical `apply_ael_achf` API still returns a blend in input units for compatibility; the GUI no longer chains preceding filters into it.

Scale controls are in native source pixels, with target/full scaling for fast preview. Radial annulus sampling in fast preview remains approximate. Full-resolution verification/export runs the native operator. The reference geometry can be a protective circle enclosing a missing region rather than a physically measured solar disk, which limits interpretation of the radial profile.

Each variant retains independent parameters, Strength, Opacity and Include state when changing the editing panel. Multiple variants may be composed simultaneously under the ACHF master Active checkbox. Layer export includes all active ACHF variants; excluded variants are omitted and zero-Strength variants are hidden. TIFF/JPEG, native verification and the cached PSB use the same selected composition. See [the layer model](layer-composition.md). Angular 8 is excluded.

Independent Photoshop export computes the encoded AEL layer from the prepared input and preserves its encoding, domain and provenance. It does not subtract adaptive ACHF's Background Retention or apply the application's other neutral-layer normalization. The same encoded layers are used by preview and export. The layer recipe records sigmas, outer sigma, target scale, spline diagnostics, display scale and variant.

Known upstream limitation: radial-profile bias near partial coverage and the Moon can create boundary bands. This port does not claim to remove them. Do not use it as a calibrated photometric product.

Validation:

- Frozen synthetic upstream fixtures for all three variants match all finite pixels within absolute 1e-7 (observed exact equality with the installed source). Fixture generation is documented in `tests/fixtures/ael_achf_iso04.md`.
- Tests cover ignored-pixel contamination, nonpositive values, bypass, constant and sparse inputs, geometry, Overlay blending, scaling, GUI selection and 16-bit exported layer pixels/alpha.
- 186 application tests pass.
- Installed AEL self-test: 81 passed, 3 skipped; no failures. Skipped checks are not validated.
- User-selected master.fits, 5608×3744: full-resolution runs of all three variants at Strength 10% completed, preserved all 20,723,292 finite pixels and the missing-data mask, and left the source SHA-256 unchanged. Full-canvas comparison inspected; not a scientific certification or native Photoshop check.

**Credit:** Pere Guerra Serra (2026), *Agentic Eclipse Library*, version 1.3.3. These filters contain code copied and adapted from AEL under the MIT license; see [full attribution](../ATTRIBUTIONS.md).
