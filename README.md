# Eclipse Image Processor

Desktop application for enhancing solar eclipse and corona images with Python and PySide6. It combines radial normalization, multiscale enhancement, sharpening and presentation stretches, with native-resolution TIFF export and independent Photoshop layers.

**Author:** Francisco Bitto  
**Version:** v0.5.0  
**Repository:** [fbitto/Eclipse-Image-Processor](https://github.com/fbitto/Eclipse-Image-Processor)

## Installation and launch

The project declares **Python 3.14 or later**. Use an interpreter for which the dependencies in `requirements.txt` are available. Memory requirements depend on image dimensions, enabled filters and native-resolution layer exports.

From the project directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

On Windows, create the environment with `python` and activate it in PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

| Dependency | Role |
| --- | --- |
| PySide6 | Desktop interface and background processing workers |
| NumPy / SciPy | Arrays, statistics, convolution, interpolation and FFTs |
| OpenCV / Pillow | Image decoding, resizing and geometry detection |
| Astropy / xisf | FITS and XISF input |
| tifffile | TIFF reading and export |
| watroo 0.0.4 | WOW wavelet backend |

`requirements.txt` and the inline script metadata in `main.py` declare the runtime dependencies. Keep them synchronized when changing dependencies. For a standalone macOS `.app` or `.dmg`, follow the [macOS build instructions](docs/build-macos.md). Local builds require separate signing and notarization for public distribution.

## Basic workflow

1. Click **Open Image**. Supported extensions are TIFF, FITS, XISF, PNG, JPEG and BMP; successful decoding depends on the reader and file layout.
2. Check **Input: linear**, directly below the opening button when applicable. This is a user declaration; it neither detects nor converts the image transfer function.
3. Check the detected lunar center and radius. Repeat automatic detection, edit the native-pixel geometry, or Ctrl-click / Command-click the image to move the center.
4. Enable the desired filters and adjust their strength. **Auto Calculate** is enabled by default and waits 650 ms after the latest numerical adjustment. Disable it while editing several settings and refresh manually when ready.
5. Enable **Full-resolution verification preview** to inspect the native calculation. It is **off by default**; the normal preview is a faster, approximate monochrome calculation with a maximum dimension of 1500 pixels.
6. Choose the final stretch and **Reveal Opacity**, then click **Export Final Image**.

Filter sections and pre-stretch start inactive. The sidebar uses aligned labels, sliders and editable numeric values. Parenthetical units or qualifiers can occupy a second line. Double-clicking a slider restores its default; the mouse wheel scrolls the sidebar without changing slider or dropdown values. Tooltips appear after **800 ms** over a control.

**Advanced mode** starts off. Hiding advanced controls retains their values. Basic WOW noise-threshold edits update all bands; advanced controls allow separate thresholds. Basic RHEF Upsilon edits link the two tails, while switching modes alone retains existing values.

### Image data and masks

Processing uses a monochrome float32 image. RGB input is retained separately as float32 for color presentation and optional source export; monochrome conversion uses `0.299R + 0.587G + 0.114B`. Loading does not preserve every source metadata field or the original storage type.

Nonfinite samples and zero-alpha pixels are missing data. Their support is retained separately from finite pixels excluded only from statistical estimation. Lunar statistical exclusion starts enabled; bright-limb exclusion starts disabled. Check the geometry: a detected circular missing-data boundary is not necessarily the physical lunar limb.

Float products retain missing samples as NaN; display TIFFs carry transparency and exported validity masks identify observed pixels. JPEG cannot retain transparency. Statistical exclusion has a separate support mask and does not turn finite input pixels into missing observations.

## Processing pipeline

Enabled stages run in this order:

```text
Pre-stretch → Radial Noise Gate → Edge-preserving Denoise
            → FNRGF → MGN → WOW → RHEF
            → Tangential Detail → Larson–Sekanina → ACHF
            → Final Stretch / Reveal
```

Spatial settings labelled **preview px** are scaled for native processing. Geometry is always expressed in native pixels; angular settings remain in degrees. Preview adaptation is approximate, especially for wavelet bands. Full-resolution verification and final export use the native filter definitions.

| Stage | Purpose and principal controls |
| --- | --- |
| Pre-stretch | Optional Asinh or logarithmic preparation before enhancement. |
| Radial Noise Gate | Attenuates weak local contrast; strength, threshold, local scale and gate smoothing. This is an application-specific contrast gate, not a calibrated camera-noise model. |
| Edge-preserving Denoise | Gradient-weighted Gaussian smoothing, controlled by strength, blur scale and sensitivity. |
| FNRGF | Fourier radial normalization; model, Fourier order, angular segments, radial bounds, ring width, spread estimator and spacing. |
| MGN | Multiscale Gaussian normalization; six independently adjustable Gaussian scales and weights, gamma, k, h and kernel truncation. |
| WOW | Wavelet-optimized whitening; native scale count, noise thresholds and standard or edge-aware processing. |
| RHEF | Radial histogram equalization; compatible or continuous model, radial sampling and Upsilon redistribution. |
| Tangential Detail | Signed angular Gaussian-blur residual; angular scale, gain, noise threshold and radial blending. |
| Larson–Sekanina | Classical symmetric rotational/radial difference; radial and angular increments. |
| ACHF | Adaptive circular high-pass; support radius, gain, intensity threshold and background retention. |
| Final Stretch / Reveal | Asinh, logarithmic or GHS presentation and blend with the separately stretched original. |

### FNRGF

The default model is **Continuous · observed support**, with **MAD** spread estimation and **Log** radial spacing. Continuous statistics fit regularized angular models using observed samples; missing sectors are not treated as zero observations. **Reference-compatible** mode retains the alternative sector convention based on sunkit-image.

- Fourier order: 1–24. Angular segments are offered as powers of two, with at least `2 × order + 1` segments; the UI raises the count when required.
- Ring width: 1–32 processing pixels, default 4. Check inner/outer radii and limb protection against the detected geometry.
- Advanced controls expose model smoothing, boundary fade, ridge regularization, minimum width, robust iterations, minimum sector population and highest-harmonic weights.

The application's range mapping and strength blend differ from the reference implementation's complete output recipe.

### MGN

The six default Gaussian scales are **1.25, 2.5, 5, 10, 20 and 40 preview pixels**, each with weight 1. Default gamma is 3.2, k is 0.7, h is 0.7 and truncation is 3 sigma. Doubling the scales is a useful progression, not a required constraint. A zero scale weight removes its contribution while retaining the fixed six-scale normalization.

The dimensionless normalization result is mapped into input units before strength blending. Missing-data and statistical-support paths use normalized filtering.

### WOW

**Native wavelet scales** accepts **Auto** or an integer count, up to the panel's image-dependent maximum of 10. Auto selects the largest count supported by that panel. The count itself does not need to be a power of two: the internal wavelet dilation doubles between bands.

Edge-aware processing is the default, with bilateral scale 1. Noise thresholds default to zero; basic mode sets one threshold for all bands, and advanced mode exposes each band separately. Fast preview adapts native physical bands approximately.

Complete-support processing uses `watroo==0.0.4`. Explicit-mask processing uses an application-specific support-normalized starlet variant, whose noise thresholds and output are not identical to watroo.

### RHEF

**Legacy / compatible** is the default; **Continuous** is optional. Continuous mode interpolates positive-intensity quantile distributions across radius, retaining input where support is insufficient. It differs from independent per-ring ranking.

Default Upsilon values are 0.35 for both tails, linked in basic mode. Continuous-model **Quantile samples** accepts **every integer from 17 to 1025**, default **257**. It does not require `2^n + 1`; an odd count includes the median, and 257 provides 256 quantile intervals. Noise confidence defaults to zero.

See [continuous RHEF notes](docs/rhef-continuous.md).

### Tangential Detail

The filter subtracts an angular Gaussian blur from the image, using observed-support normalization and periodic angular sampling. Only the signed detail is resampled onto the Cartesian input. Defaults include angular sigma 3°, gain 1 and noise threshold 0. Optional radial limits and boundary fade restrict the effect.

### Classical Larson–Sekanina

The radial/rotational shift-difference method is credited to **S. M. Larson and Z. Sekanina (1984)**, originally developed to enhance cometary structure. See the [original paper](https://doi.org/10.1086/113551) and the full citation under Scientific methods.

For radial increment `dr` and angular increment `dθ`, the signed detail is:

```text
D(r, θ) = 2 I(r, θ) − I(r − dr, θ − dθ) − I(r − dr, θ + dθ)
output  = I + (Strength / 100) × D
```

The default increments are **0 preview pixels** and **1°**. Both zero produce an exact bypass. The implementation uses bilinear sampling and fully observed footprints outside the lunar disk; unsupported positions retain the input. Signed values are not clipped internally.

This implements the classical operator with the existing geometry. PixInsight-specific threshold, deringing and dynamic-range extensions are not included. The independent Photoshop layer uses **Linear Light**. See [implementation and export notes](docs/larson-sekanina.md).

### ACHF

The adaptive neighborhood accepts symmetric opposite pairs according to their intensity difference. Controls cover support radius (1–20 preview pixels), contrast gain (default 2), intensity threshold (default 10%) and background retention (default 10%), followed by the filter strength blend.

This independently implements adaptive circular high-pass principles rather than reproducing Corona 3.0. Cost grows approximately with image pixels × support radius², so large native supports can be expensive.

### Final stretch and color

Asinh and logarithmic stretches provide simple presentation curves. GHS implements the scalar forward equations by David Payne and Mike Cranfield, with symmetry around SP and tangent protections outside LP/HP.

| GHS control | Range / default |
| --- | --- |
| Stretch factor ln(D+1) | 0–20 / 2 |
| Symmetry point SP | 0–1 / 0.05 |
| Local intensity b | −5–15 / 0 |
| Shadow protection LP | 0–SP / 0 |
| Highlight protection HP | SP–1 / 1 |
| Post-stretch black point | −1 to below white point / 0 |
| Post-stretch white point | Above black point to 2 / 1 |

The SP picker samples normalized processed intensity before presentation stretching. Black/white points apply a separate linear adjustment after GHS. See [GHS equations and validation](docs/ghs-reference-20261019.md).

Finite intensities are normalized for presentation. **Reveal Opacity**, default 100%, blends separately stretched original and processed images. **View Original** is a temporary comparison and is not saved in exports. The final stretched TIFF is a display product, not a linear scientific master.

For RGB input declared linear, **Calibrate color** starts enabled. The optional tse-tools-derived neutralization uses jointly valid samples, P1 subtraction and P99−P1 channel spans relative to green, followed by range handling. It requires sufficient nonconstant samples. It is disabled for monochrome or input declared nonlinear/unknown. Source exports retain the uncalibrated working input.

Fast preview is monochrome; native verification and final export include source color and optional neutralization. Luminance-guided presentation and color-layer reconstruction operate on display values and do not constitute an ICC-managed Photoshop color-match guarantee.

## Export products

Export runs calculation and file writing in a background worker with a snapshot of the current settings. Sidebar controls are disabled during export; closing waits for completion. A matching cached native result is reused, otherwise native processing is calculated again.

The chosen destination produces:

- **16-bit TIFF**, monochrome or RGB according to the input, with alpha for missing data.
- **`<name>_preview.jpg`**, using the same display values without a second gamma transformation.
- Optional Photoshop and source packages in separate folders; existing package folders receive a numbered alternative.

### Independent Photoshop layers

**Also export independent Photoshop layers** starts enabled. The package is named `<destination>_PS_layers`. Layer filenames contain only **two-digit number, filter and blend mode**, for example:

```text
01_BASE_Normal.tif
02_FNRGF_Overlay.tif
03_MGN_Overlay.tif
04_WOW_Overlay.tif
05_RHEF_Overlay.tif
06_TANGENTIAL_Overlay.tif
07_LARSON_SEKANINA_LinearLight.tif
08_ACHF_Overlay.tif
09_RGB_Color.tif
```

This example includes all enhancement filters and RGB. Only active, nonzero filters are exported, and numbering is contiguous from bottom to top. RHEF's selected model is recorded in the recipe rather than added to its filename.

Each enhancement branch starts from the same prepared input, after optional pre-stretch, noise gate and denoise. These independent branches differ from the sequential final pipeline, so the Photoshop composition is a separate result.

Most detail layers use neutral-centered **Overlay** encoding. Tangential Detail and ACHF remove their base component before encoding. Larson–Sekanina preserves zero-centered signed detail using `L = 0.5 + D/(2S)` for **Linear Light**, where S bounds the input span and detail magnitude. Recommended detail opacity is capped at 35%, incorporates Reveal and is quantized to 1/255. The optional RGB layer uses **Color** at 100%.

The package also contains:

- `<original>_SOURCE_float32.tif` and `<original>_PREPARED_float32.tif`: monochrome working input and shared preparation.
- `<original>_RGB_COLOUR_INPUT_float32.tif` when RGB is available.
- `<original>_VALID.tif` and `<original>_STATISTICS_SUPPORT.tif`: observation and statistical support masks.
- `<original>_PS_COMBINED.tif`: reference composition reconstructed from the exported layers.
- `recipe.json`, `Layers.md` and `Load_layers_Photoshop.jsx`: parameters, encodings, order, blend modes, opacities and import script.

In Photoshop, use **File > Scripts > Browse** and select the generated JSX. It creates a new unsaved document with the layer settings; existing open documents remain available. Do not apply a fresh stretch or gamma to the neutral detail layers before blending.

### Source working images

**Also export linear images** starts disabled. It creates `<destination>_sources`, containing float32 monochrome/RGB working inputs, a validity mask, `sources.json` and `LEEME.txt`.

Names use `_LINEAR_L_float32.tif` / `_LINEAR_RGB_float32.tif` when the input is declared linear, and `_INPUT_...` otherwise. These are loaded working arrays before filters, presentation and color calibration; they are not byte-for-byte copies of the source file. The linear label reflects the user's declaration, not an inferred calibration.

## CPU performance and responsiveness

Processing currently uses the **CPU**. CPU thread limits are initialized before numerical-library imports; the detected logical CPU count does not mean every operation uses every core. Pipeline stages retain their sequential dependencies.

Independent MGN scales use up to four workers, with a size-dependent memory limit and deterministic ordered reduction. Masked MGN reuses Gaussian support. Masked standard WOW uses sparse five-tap filtering at large dilations. Tangential Detail switches to circular FFT convolution for wide angular kernels; Larson–Sekanina uses rotation matrices instead of per-pixel polar angles.

Native numerical output is cached for verification/export. Numerical recipe changes invalidate the cache; display adjustments reuse it. Preview cancellation is cooperative: active library operations finish before the next cancellation check, and obsolete results are discarded. Display rendering still includes work on the GUI thread.

See the [CPU optimization report](docs/performance-optimization-20261021.md) for measured timings, numerical comparisons and limits. Those measurements describe specific images and settings, not a universal speedup.

## Development and verification

```bash
python -m unittest discover -s tests -v
```

Tests use deterministic synthetic images and cover numerical behavior, masks, bypasses, presentation, export and GUI controls. Real-image checks remain necessary for lunar geometry, artifacts, interaction and output appearance. For a release, also inspect exported dimensions, TIFF bit depth/alpha, companion JPEG and Photoshop import. Dependency minimums are not a verified platform compatibility matrix.

| Location | Responsibility |
| --- | --- |
| `main.py` | CPU initialization and application startup |
| `gui/app.py`, `gui/factories.py`, `gui/filter_controls.py` | Window, shared controls and filter panels |
| `core/filters.py` | Active filters and preview worker; edit this rather than the backup copy |
| `core/continuous_fnrgf.py`, `core/radial_continuous.py`, `core/masked_filters.py` | Continuous and support-aware numerical paths |
| `core/export.py`, `gui/export_worker.py` | Export calculation, orchestration and background worker |
| `core/layer_export.py`, `core/linear_export.py` | Photoshop and source packages |
| `tests/`, `scripts/`, `docs/` | Automated checks, development tools and implementation reports |

`config.py` contains shared styling/constants and legacy defaults. Active GUI defaults are defined by the current controls; legacy defaults are not authoritative for the window.

For slow processing, disable Auto Calculate while editing and reduce unnecessary scales or supports. For radial seams or limb fringes, check geometry, support masks, radial sampling and strength before increasing enhancement. For startup/decoder errors, check the active environment and the terminal error from the relevant dependency.

## Algorithm credits, scientific references and acknowledgments

Eclipse Image Processor is developed by Francisco Bitto. Its enhancement tools build on the scientific work and software projects credited below. Credit for an algorithm belongs to its original authors; the application adds its own interface, parameter handling, masking, blending and export workflow. Please cite the relevant methods as well as this application when publishing processed images.

### Software and implementation sources

| Project / authors | Contribution to this application |
| --- | --- |
| [sunkit-image](https://github.com/sunpy/sunkit-image), the SunPy community and contributors | Numerical implementation reference for MGN, FNRGF, RHEF and Upsilon, particularly version 0.7.0. The array implementations here follow the documented conventions with the differences described above. SunPy and sunkit-image are reference projects, not application runtime dependencies. See their [documentation](https://docs.sunpy.org/projects/sunkit-image/en/stable/) and [license](https://github.com/sunpy/sunkit-image/blob/main/LICENSE). |
| [watroo / wavelets](https://github.com/frederic-auchere/wavelets), Frédéric Auchère and contributors | Direct runtime backend for standard and bilateral WOW, B3-spline à trous decomposition and wavelet noise tools; pinned to `watroo==0.0.4`. The explicit-mask path is an application-specific normalized-starlet variant, not an identical implementation. See the upstream [MIT license](https://github.com/frederic-auchere/wavelets/blob/master/LICENSE.rst). |
| [tse-tools / eclipsetools](https://github.com/naavis/eclipsetools), Samuli Vuorinen (`naavis`) | The optional RGB P1/P99 neutralization adapts `color_calibrate` from [revision `14ae3f7`](https://github.com/naavis/eclipsetools/blob/14ae3f7d823d0ac66688a32bf27d0c4b9b8a0391/src/eclipsetools/commands/utils.py), adding explicit nonfinite-data handling and application integration. Copyright © 2025 Samuli Vuorinen; the [MIT notice is retained locally](docs/third-party/eclipsetools-MIT.txt). The upstream package is not required at runtime. |
| [Agentic Eclipse Library (AEL)](https://github.com/PeterWar/Agentic-Eclipse-Library), Pere Guerra Serra (`PeterWar` / Peter War) | Acknowledged for the study of continuous radial statistics that inspired the independently implemented global continuous RHEF, and for research references concerning observed-pixel masks and adjustable corona layers. The comparison used AEL 1.3.2, [revision `5629b37`](https://github.com/PeterWar/Agentic-Eclipse-Library/tree/5629b37071ec87a32f3cf37b5ce6dfcc8b02ada1). AEL is MIT-licensed, copyright © 2026 Pere Guerra Serra; its package/modules are not bundled or required by this application. See the [comparison and attribution notes](docs/ael-filter-review.md) and [continuous RHEF implementation notes](docs/rhef-continuous.md). |
| [EclipseForgeHDR](https://github.com/naugustin77/EclipseForgeHDR), `naugustin77` and contributors | Source-available research reference, reviewed at [revision `8d68626`](https://github.com/naugustin77/EclipseForgeHDR/tree/8d68626077bff056c8b8773a210b0226325b8699). Comparative reference for support-aware radial models and native-layer preview architecture. The new continuous FNRGF and verification workflow are independently implemented; no upstream source is bundled. See the [research notes](docs/external-filter-ideas-20261019.md) and [implementation checks](docs/filter-controls-20261019.md). |
| [Eclipse_HDR](https://github.com/LaurentVoillot/Eclipse_HDR), Laurent Voillot | Reviewed at [revision `1d5b9b1`](https://github.com/LaurentVoillot/Eclipse_HDR/tree/1d5b9b10ce0320ad7a331fab65763d50fd3827c0). Comparative reference for radial-model continuity, tangential angular detail, processing masks and optional RHEF noise confidence. The application implements these ideas independently and does not bundle the upstream GPL scripts; see the [research notes](docs/external-filter-ideas-20261019.md). |
| [GHS](https://github.com/mikec1485/GHS), David Payne and Mike Cranfield | Original GHS method, equations and PixInsight script. The scalar curve here is independently implemented from the [published mathematical specification](https://www.ghsastro.co.uk/doc/tools/GeneralizedHyperbolicStretch/GeneralizedHyperbolicStretch.html), with the author’s script used as a reference; upstream GPL source is not bundled. See [GHS implementation and tests](docs/ghs-reference-20261019.md). |

### Scientific methods

| Method | Original scientific reference and relationship to this application |
| --- | --- |
| FNRGF | **Hana Druckmüllerová, Huw Morgan and Shadia Rifai Habbal (2011)**, *Enhancing Coronal Structures with the Fourier Normalizing-radial-graded Filter*, The Astrophysical Journal **737**, 88. [DOI: 10.1088/0004-637X/737/2/88](https://doi.org/10.1088/0004-637X/737/2/88). Fourier radial normalization; numerical conventions also informed by [sunkit-image FNRGF](https://docs.sunpy.org/projects/sunkit-image/en/stable/api/sunkit_image.radial.fnrgf.html), which also cites Hana Druckmüllerová’s doctoral thesis, [*Application of Adaptive Filters in Processing of Solar Corona Images*](https://www.vut.cz/studenti/zav-prace?zp_id=69016). |
| MGN | **Huw Morgan and Miloslav Druckmüller (2014)**, *Multi-scale Gaussian normalization for solar image processing*, Solar Physics **289**, 2945–2955. [DOI: 10.1007/s11207-014-0523-9](https://doi.org/10.1007/s11207-014-0523-9); [author preprint](https://arxiv.org/abs/1403.6613). Scientific basis of the multiscale Gaussian normalization core. |
| WOW | **Frédéric Auchère, Elie Soubrié, Gabriel Pelouze and Éric Buchlin (2023)**, *Image enhancement with wavelet-optimized whitening*, Astronomy & Astrophysics **670**, A66. [DOI: 10.1051/0004-6361/202245345](https://doi.org/10.1051/0004-6361/202245345); [open-access paper](https://www.aanda.org/articles/aa/full_html/2023/02/aa45345-22/aa45345-22.html); [author preprint](https://arxiv.org/abs/2212.10134). Scientific basis of standard/bilateral whitening and significance-based denoising supplied by watroo. |
| RHEF and Upsilon | **Chris R. Gilly and Steven R. Cranmer (2025)**, *Visualization of High Dynamic Range Solar Imagery and the Radial Histogram Equalizing Filter*, Solar Physics **300**, 174. [DOI: 10.1007/s11207-025-02578-x](https://doi.org/10.1007/s11207-025-02578-x); [author preprint](https://arxiv.org/abs/2511.02798). Credit for radial histogram equalization and the Upsilon redistribution function. The compatible mode follows sunkit-image's ranking/branch conventions; the continuous mode adds the AEL-inspired interpolation described above. |
| Larson–Sekanina | **S. M. Larson and Z. Sekanina (1984)**, *Coma morphology and dust-emission pattern of periodic Comet Halley. I. High-resolution images taken at Mount Wilson in 1910*, The Astronomical Journal **89**, 571–578. [DOI: 10.1086/113551](https://doi.org/10.1086/113551); [original paper via NASA ADS](https://articles.adsabs.harvard.edu/pdf/1984AJ.....89..571L). Credit for the radial/rotational shift-difference method. This application implements a symmetric signed-difference operator for solar-corona enhancement, with its own sampling, support masks, strength blend and Photoshop layer encoding; it does not reproduce PixInsight-specific extensions. |
| ACHF / adaptive circular high-pass | **Miloslav Druckmüller, Vojtech Rušin and Milan Minarovjech (2006)**, *A new numerical method of total solar eclipse photography processing*, Contributions of the Astronomical Observatory Skalnaté Pleso **36**, 131–148. [Original paper](https://www.astro.sk/caosp/Eedition/FullTexts/vol36no3/pp131-148.pdf), §4.2, equation (7). The application independently implements variable-kernel principles with its own symmetric acceptance, gain and background parameters; it does not reproduce Corona 3.0. |
| GHS | **David Payne and Mike Cranfield**, *GeneralizedHyperbolicStretch*, [official method and equations, §5.2](https://www.ghsastro.co.uk/doc/tools/GeneralizedHyperbolicStretch/GeneralizedHyperbolicStretch.html) and [original script](https://github.com/mikec1485/GHS). Credit for the five-parameter stretch, symmetry and tangent protections. This is a documented mathematical method/software reference; no separate journal-paper citation is implied. |
| NRGF background | **Huw Morgan, Shadia Rifai Habbal and Richard Woo (2006)**, *The Depiction of Coronal Structure in White Light Images*, Solar Physics **236**, 263–272. [DOI: 10.1007/s11207-006-0113-6](https://doi.org/10.1007/s11207-006-0113-6); [author preprint](https://arxiv.org/abs/astro-ph/0602174). Foundational radial-normalization reference used in the research review; a separate NRGF stage is not currently exposed in the application. |

### Other processing and presentation credits

- **Gaussian filtering, histogram ranking, Asinh and logarithmic stretches** are established image-processing techniques. Their application-specific composition and controls are implemented here using NumPy and SciPy; no single new scientific authorship is claimed for these standard operations.
- **Radial Noise Gate and Edge-preserving Denoise** use application-specific recipes. The Edge-preserving Denoise section mixes Gaussian smoothing according to gradient weights; it is not a canonical bilateral filter. The bilateral WOW backend is separately credited to Auchère and collaborators above.
- **Tangential Detail:** credit to Laurent Voillot’s Eclipse_HDR for the angular-blur residual approach studied during implementation; the support normalization, periodic sampling, threshold and radial blend here are independently implemented. USM is retained only in legacy APIs.
- **Color/Overlay compositing:** the reference layer reconstruction uses the nonseparable `SetLum` / `ClipColor` and Overlay blending conventions documented in [W3C Compositing and Blending Level 1](https://www.w3.org/TR/compositing-1/). The Photoshop JSX applies native blend modes; Adobe Photoshop is a separate product.

### Supporting open-source libraries

Thanks to the maintainers and contributors of [Python](https://github.com/python/cpython), [Qt / PySide6](https://code.qt.io/cgit/pyside/pyside-setup.git/), [NumPy](https://github.com/numpy/numpy), [SciPy](https://github.com/scipy/scipy), [OpenCV](https://github.com/opencv/opencv), [Pillow](https://github.com/python-pillow/Pillow), [Astropy](https://github.com/astropy/astropy), [xisf](https://pypi.org/project/xisf/) and [tifffile](https://github.com/cgohlke/tifffile). Their roles are listed under Requirements and installation. The optional camera-noise development script also uses [rawpy](https://github.com/letmaik/rawpy).

Each upstream project retains its own copyright and license. Scientific citations and acknowledgments supplement those notices; this repository's MIT license does not relicense its dependencies. Reference comparisons and independent adaptations do not imply endorsement or identical numerical output.

## Support, citation and license

Report reproducible problems through [GitHub Issues](https://github.com/fbitto/Eclipse-Image-Processor/issues), including Python and dependency versions, operating system, filter settings and terminal errors.

When citing the software, identify Francisco Bitto, *Eclipse Image Processor*, **v0.5.0** (or the exact release/commit used) and the repository URL. Include the relevant scientific-method citations above for the filters used.

Licensed under the [MIT License](LICENSE).
