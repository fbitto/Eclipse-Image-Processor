# PSB presentation and export

The application uses independent encoded layers for fast/native preview and export. **The main TIFF/JPEG and PSB share the presentation base.** No installed AEL runtime is required. The PSB writer adapts AEL 1.3.3 by Pere Guerra Serra under MIT and uses pinned psd-tools 1.26.0; see [attribution](../ATTRIBUTIONS.md).

## Output contracts

| Product | Base / presentation |
| --- | --- |
| Main full-resolution TIFF | RGB16 PSB presentation plus active filter layers, exposure and optional prominences; embedded sRGB |
| Preview JPEG | Same presented RGB composition; native dimensions, 8-bit, quality 95, embedded sRGB |
| PSB or TIFF layer package | PSB presentation base plus active filter layers, independent of preview toggle |
| Hidden scaled input preview | Working RGB/mono scaled for 16-bit storage; quantized preview only, not a linear master |
| Working float source and validity | Numerical working mono units, missing samples zero plus separate support |

The main TIFF is an enhanced composition, not a photometric linear master. JPEG has no additional gamma transform. PSB Exposure changes the presented TIFF/JPEG and layer export. The preview toggle affects only the viewport. GUI exports always add a float32 working-source package; layer exports through the numerical API include it too. Direct image-only API callers can omit that companion explicitly.

## Automatic presentation

Preview PSB presentation starts enabled, with exposure 0 EV. Controls sit above export options and remain usable when layer export is off. Double-click Exposure restores 0 EV; no separate reset button or Display Stretch selector exists.

`core/presentation.py` estimates P99.5 from positive native luminance outside 1.2 reference-disk radii, sampled at stride `ceil(max(shape)/1024)`. RGB estimation uses weights 0.25/0.5/0.25 and follows enabled background preparation/calibration. The scale is `automatic_scale * 2**(-EV)`, with EV from −6 to +6. Empty positive sample domains fall back to scale 1. **Automatic scale selection is an application heuristic, not an AEL default.** The native scale is shared across resolutions and export.

The tone curve follows AEL 1.3.3 `ael.develop.tone_map`:

```text
u = asinh(max(RGB, 0) / scale * 10) / asinh(10)
peak = max(u across RGB channels)
shoulder = 0.9 * (1 - exp(-peak / 0.9))
mapped = u * shoulder / peak       # zero at peak = 0
```

Positive values above scale are not pre-clipped. A shared shoulder preserves the post-Asinh channel ratios. Row tiles bound float temporary storage. Mapped RGB is quantized to 16 bits; its 0.30/0.59/0.11 luminance forms Display base and a Color layer supplies RGB. This mono-base/Color architecture is application-specific, not a copy of AEL's complete workflow. Fast preview tone-maps reduced data; native verification tone-maps natively before reducing, so the latter is authoritative.

## Package and layers

Enable Also export editable Photoshop layers and select PSB (the default) or the TIFF package. The stack contains:

1. Opaque **00_BACKGROUND_Black**.
2. Hidden **Linear reference / receipt scale**.
3. Visible **Display base**.
4. Active filter layers in [fixed order](layer-composition.md), with their modes, opacity and alpha.
5. RGB Color layer when applicable.
6. Display-only **Edge Antialias** when needed.
7. Optional Photoshop-only **Color Correction** group.
8. Optional **Prominences and chromosphere**, Normal at 100%, with an editable 16-bit pixel mask. Its RGB comes from the original loaded file, before any working-source preparation or neutralization. The correction group's snapshot excludes this layer, so native colour adjustments remain below the original red prominences.

Prominence image and mask previews run in the presentation worker. Selection always runs at native resolution before reducing the mask and premultiplied RGB for the fast view, so narrow red features are not erased by averaging RGB with neutral neighbours before selection. The native original supplies a shared P99.5 peak-RGB reference in red candidates between 0.9 and 1.5 lunar radii (fallback: all positive observed pixels in that annulus). Exposure is linear, independent of corona exposure, with a shared RGB highlight limit. The initial mask uses smooth red-excess fractions 0.05–0.25 and peak/reference levels 0.005–0.03 and fades out from 1.3 to 1.5 lunar radii. It applies no geometric lunar-disk exclusion: valid pixels inside the fitted circle are retained according to their original colour and intensity, while missing pixels remain excluded. A margin already removed from the loaded HDR cannot be recovered. These are presentation heuristics requiring review on real images. The mask does not change with EV.

The TIFF layer package stores unmasked RGB and a separate mask; its JSX imports that mask as an editable Photoshop layer mask. The separate `PROMINENCES.tif` is instead composited onto black for viewing. PSB verification checks mask bounds, enabled/non-inverted flags and exact 16-bit mask bytes as well as RGB and transparency. The preview JPEG includes prominences when PSB presentation is selected; the main TIFF does not.

The mask's red score is `(R - max(G,B) - max(G-B,0)) / peak(RGB)`. The extra green-minus-blue term discounts yellow/orange continuum, which otherwise passes a simple red-dominance test and creates a dark Normal-blend ring around a warm corona. This score only selects pixels; exposed RGB channel ratios remain unchanged. The same score supplies reference candidates and the native mask, with the existing 0.05–0.25 smooth transition. Strong pure red and pink signals remain selected in synthetic controls; this is not a calibrated emission-line measurement.

The working linear reference includes enabled background correction and RGB calibration. Its positive observed maximum is divided by 0.98 to obtain the recorded storage scale. Mono is repeated into RGB when needed. Negative values clip in this 16-bit reference; it is not an untouched original or a replacement for floating input.

The TIFF package includes `01_LINEAR_REFERENCE_Normal.tif`, numbered base/filter files, `REFERENCE_COMBINED.tif` (the PSB presentation), `SOURCE_float32.tif` (working mono), `VALID.tif`, `STATISTICS_SUPPORT.tif`, `recipe.json`, `Load_layers_Photoshop.jsx` and `Layers.md`. Missing float samples store zero; VALID distinguishes missing observations from measured black. GUI export always adds the matching `_sources` folder with float32 mono/RGB, a validity mask and preprocessing receipt. The original source remains unchanged; numerical source files do not carry a display profile.

The PSB route keeps the layers in memory and writes no temporary TIFF package; a selected TIFF directory persists. The PSB pixels, layer order, names, modes and opacities are the same on both routes. Without layer files, each recipe row in the PSB metadata records the sha256 of its uint16 pixels (`layer_sha256` in the recipe says how), not of a TIFF file. The layer package and the main TIFF/JPEG use the same presentation, so the export computes the 16-bit presentation base once for both. Hide the black background to inspect transparency; original layer alpha remains separate.

## Optional Color Correction and profile

Add Color Correction to PSB (sRGB) starts off, appears directly below Also export, and is enabled only for PSB layer export. It adds a **Color Correction** group in Normal at byte opacity 128/255, containing a base snapshot, a Copper Gold Ivory Gradient Map (Color, 30%), Color Balance (Color, 30%) and sky Hue/Saturation (Normal, 100%). Native editable 16-bit masks separate sky/corona and exclude the lunar region; inspect them in Photoshop.

Color Balance uses midtones `(8, -2, -8)` and highlights `(4, 0, -6)` with luminosity preserved. Sky saturation reduces cyan by 10 and blue by 20. The group uses the palette in `core/color_correction.py`; the [historical design](propuesta-color-atardecer-psb.md) explains its origin.

All display TIFF/JPEG/PSB products embed **sRGB** for assumed-sRGB application display RGB, including PSBs without Color Correction. This is profile assignment, not general camera/source-ICC conversion. The group is absent from GUI preview and main TIFF/JPEG. Its cached merged RGB is the uncorrected reference and is explicitly marked as requiring native Photoshop recomposition. Third-party flattened previews may omit the correction. Rebuild the snapshot group after changing underlying filter layers.

## Verification and publication

The writer creates PSB version 2, RGB16, full-canvas layers, separate 16-bit alpha and Lr16 records; its current opaque merged RGB needs no Mt16 merged-transparency block. Recipe metadata is embedded in XMP. Reopening verifies dimensions, names, modes, visibility, byte opacity, original channel bytes, hashes when supplied, background and cached reference. Every distinct channel plane is compressed once, on helper threads (zlib releases the GIL), with the same row prediction and zlib call as psd-tools, so the file is byte-identical to adding the layers one at a time. Verification decompresses each distinct stored channel once, on threads, by blocks of rows; thread counts are bounded by an eighth of physical memory. Optional adjustment/profile structures are verified separately. This is structural/pixel verification, not proof of Photoshop colour-managed recomposition.

Layers are generated/verified before final TIFF/JPEG. A layer failure prevents new final images; a later image/JSON failure can leave earlier completed outputs. PSB publication prefers an atomic same-directory hard link. Filesystems without hard links use exclusive creation and a copy of the verified temporary PSB, followed by fsync; failed copies are removed and existing destinations are never overwritten. This fallback is not atomic to external readers.

Exports containing layers, source packages or prominence products choose one unused stem for the entire bundle: if any requested companion exists, `<name>_2.tif`, `<name>_2_preview.jpg`, `<name>_2.json` and `<name>_2_PS_layers.psb` (or the TIFF layer directory) are selected together. Earlier exports are preserved. TIFF/JPEG/JSON-only exports may replace their selected destinations after confirmation. Settings JSON is published atomically last; the overall multi-file export is not atomic.

Progress reports completed stages rather than remaining time. Filter timings overlap when prepared in parallel; PSB/package totals include nested stages. Memory and disk demands can be substantial. Files above 2 GB and the 300,000-pixel dimension limit have not been stress-tested.

## Validation boundary

Current automated tests cover writer bytes, masks, blend modes, cancellation, output separation, settings and optional adjustments. Historical full real-image checks predate the presented-TIFF contract. Current synthetic export tests verify TIFF/PSB pixel equality, profiles and preserved float32 sources. Earlier exports opened successfully in Photoshop 2026, but those measurements predate the current automatic presentation and hidden reference. **The current presentation/reference combination has not been revalidated by opening it in Photoshop.** See [current validation](validation.md) and [archived native measurements](psb-validation-history.md).

Export cancellation is cooperative. Cancel export remains available beside the viewport while settings are locked; closing also requests cancellation. Operators and export stages stop at safe checkpoints. A compression/write call finishes before the next checkpoint. TIFF, JPEG and settings JSON are prepared in temporary files before their publication begins; cancellation then stops being accepted. Existing files are preserved on pre-publication cancellation. Already completed layer, source or prominence packages may remain, and the cancellation message states this. Publication remains atomic per file, not across the complete bundle.
