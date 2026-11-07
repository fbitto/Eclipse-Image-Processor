# Processing settings JSON

Only **version 4** is accepted. Other schema versions and unknown controls are rejected; explicitly supported optional/retired keys have documented compatibility handling.

Save Settings Only writes controls and a source reference without running filters. Image export writes the same reloadable settings after TIFF/JPEG. Open Image / Settings restores the referenced original source and settings; pixels and numerical caches are not embedded.

## File envelope

`core/project_settings.py` owns the envelope:

| Field | Meaning |
| --- | --- |
| `format` | `eclipse-image-processor-settings` |
| `version` | Integer 4 |
| `source` | Absolute source path |
| `source_relative` | Relative source path, preferred on reopen; new writes use portable forward slashes; null across Windows drives |
| `settings` | Validated GUI snapshot |
| `parameters` | Numerical parameter receipt |
| `display` | Display receipt; not a second set of GUI controls |

The source must exist and cannot itself be JSON. The reader limits files to 2 MiB. Writes reject nonfinite JSON numbers and publish through a same-directory temporary file, fsync and replace. The image and JSON can move together using the relative source path, with the absolute path as fallback. Older Windows relative paths containing backslashes are also tried with portable separators; literal local paths are checked first.

## Relocating a missing original

If neither saved source path exists, the GUI validates the saved controls before opening **Locate original image**. Select the relocated original or an identical copy; loading continues through the normal image decoder and source-size-aware recipe restoration. JSON files cannot be selected as replacement images. Cancelling leaves the current image, controls and pending work unchanged.

The original JSON is not rewritten by loading. The active source path becomes the selected file; saving settings or exporting a new recipe records that location. The source pixels remain external to JSON, and selecting a different image is not automatically checked against an original content hash.

The core reader remains usable without a GUI: missing sources raise `MissingSourceImage`, a `FileNotFoundError` subclass carrying the saved source and settings. An explicit `source_override` selects a replacement without silently falling back to another image.

## GUI snapshot

`gui/project_settings.py` validates these top-level settings keys: `background_samples`, `controls`, `sections`, `geometry`, `auto_calculate`, `ui_mode`. The mode is `basic`, `standard` or `expert`; older v4 snapshots infer Standard or Expert from their Advanced checkbox.

- Controls identify widget kind and value; combo boxes also carry validated text/index information. Slider values use raw integer ticks, not formatted physical-unit labels.
- Non-filter/global controls are required. Filter controls and sections can be omitted: filters reset to prepared defaults first, absent filter sections remain disabled, and absent ACHF Include flags remain unchecked. Previous-image edits are never inherited for omitted filters.
- Geometry contains finite numeric strings for x, y and radius, including decimals, with positive radius. Their original text is preserved on reopening. Section states and auto-calculation are booleans. Geometry section state is required.
- Background samples are null or a list of native integer coordinate pairs, at most 5000 points.

Explicit values must match supported controls and types. Slider restoration respects current bounds, with the supported dynamic upper bounds for FNRGF maximum radius/MGN sigma. Image-dependent WOW limits use the referenced source's dimensions, even when a different image is currently open. Restoration uses two passes for linked slider bounds and rolls widgets/ranges back if restoration fails. Use a generated current JSON as a template rather than inventing control identifiers.

The PSB-preview toggle, exposure and export options are saved. Existing v4 recipes without the toggle restore it enabled. Disk-overlay visibility, zoom and View Original remain transient. Source load resets the red circle/cross to visible.

Directly loading another image is a separate action from restoring JSON: it retains current filter settings and active/include flags, detects new geometry and regenerates background samples. First-load defaults are listed in [layer composition](layer-composition.md).

## Export failure boundaries

Settings-only publication is atomic. Image export writes layers first, TIFF/JPEG next, JSON last. Failure at a later stage can leave previously completed outputs; the complete multi-file export is not a single atomic transaction. The JSON is a recipe for the original source, not an instruction to reprocess its rendered output.

The retired adaptive ACHF `sl_achf_background` control is ignored when opening existing v4 recipes and omitted when saving. Background retention remains available to direct numerical API callers, outside GUI detail-layer construction.

RHEF/FNRGF ring-width ticks now denote native pixels. Reopening an older v4 recipe retains its raw ticks but recalculates under the corrected units; earlier preview-pixel RHEF and target-pixel FNRGF previews are not reproduced. MGN and AEL isotropic fast previews omit unresolved subpixel bands; their native recipes are unchanged.

`chk_statistics_separate_ael` records the opt-in experimental AEL statistics/output policy. Missing fields default off. The mode retains observed positive operator samples while restricting ACHF radial fits and display statistics, rather than reconstructing missing pixels.

The optional Expert `combo_nrgf_partial_annuli` selector stores legacy shared-angle chaining (index 0, `chain`) or the EIP anchored variant (index 1, `chain_anchored`). New sessions and older v4 recipes without this control use legacy chaining, even if the preceding image used anchoring. Hiding Expert controls retains the selected algorithm. The numerical receipt records `nrgf_partial_annuli`; layer normalization receipts also identify the anchored revision and per-run fallback. The settings envelope remains version 4.

Exports now use the PSB presentation for TIFF/JPEG regardless of the viewport toggle. Exposure affects all display products, and GUI export includes a separate float32 working-source package. Existing recipes keep their raw controls but recalculate under this corrected output contract. The optional Larson–Sekanina log input selector defaults to linear when omitted.

## Prominence control compatibility

Prominence contrast is optional in older v4 recipes and restores to 1.0 when omitted. The new-session exposure is 0 EV; legacy recipes preserve saved negative EV values, including the historical −2 EV fallback when the exposure field is absent. Basic and Standard exposure edits cover 0…+5 EV, while Expert permits −3…+5 EV. A saved negative exposure remains active when switching to Basic or Standard, with a visible notice; moving the limited-range control explicitly replaces it. Mode changes do not alter exposure or hidden contrast. Preview and export use that same saved exposure and contrast.

## NAFE compatibility

The optional `sec_nafe`, `combo_nafe_sigma`, `combo_nafe_window` and `sl_nafe_*` controls use the existing version-4 envelope. Older recipes without them restore NAFE disabled, automatic residual-MAD sigma, multiplier 12, noise region 4 reference radii, residual guide sigma 4 native pixels and window 129. Manual `nafe_sigma` uses working linear input units; automatic mode records null in the parameter snapshot and the effective measured sigma in the layer receipt. `nafe_scale` identifies target/native resolution for the window and residual guide. Hidden Expert values persist. See [NAFE](nafe-ael.md) for noise fallbacks and the approximate-preview contract.
