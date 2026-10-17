# Eclipse Image Processor

Desktop application for enhancing solar eclipse and corona images, written in Python with PySide6, NumPy, SciPy and OpenCV.

**Author:** Francisco Bitto  
**Version shown by the application:** 0.4.0  
**Repository:** https://github.com/fbitto/Eclipse-Image-Processor

## Requirements and installation

The project declares Python 3.14 or later. Use a Python installation compatible with the dependencies in `requirements.txt`. Memory use and processing time depend on image dimensions and enabled filters; full-resolution export requires more resources than the preview.

From the project directory, create a virtual environment:

```bash
python3 -m venv .venv
```

Activate it on macOS or Linux:

```bash
source .venv/bin/activate
```

On Windows, use `python` to create the environment and activate it in PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Install the declared dependencies and launch the application:

```bash
python -m pip install -r requirements.txt
python main.py
```

`requirements.txt` is the dependency list for installation. `main.py` also contains inline script metadata (PEP 723); keep both lists synchronized when changing dependencies.

| Package | Role |
| --- | --- |
| PySide6 | Desktop interface and background preview worker |
| NumPy | Image arrays and numerical operations |
| SciPy | Gaussian filtering, interpolation and numerical functions |
| opencv-python | Image decoding, resizing, filtering and circle detection |
| Pillow | Fallback image decoder |
| Astropy | FITS input |
| xisf | XISF input |
| tifffile | TIFF input and export |
| watroo 0.0.4 | WOW backend used by sunkit-image |

## Working with images

1. Click **Open Image** and select a supported image. Loading creates a grayscale `float32` working image, detects the lunar disk and populates geometry-dependent parameters.
2. Check the center coordinates and radius. Use **Auto-detect Lunar Disk** to repeat detection or edit the geometry manually. Geometry values are expressed in full-resolution image pixels.
3. Enable the desired filter sections and adjust their controls. **Auto Calculate** recomputes the preview when relevant controls are released or changed. Disable it while adjusting several settings and use the refresh button to process manually.
4. Use **View Original** to compare with the input. Adjust the final display stretch and blend to inspect structures.
5. Click **Export Final Image** and choose a TIFF destination.

### Input formats

The file dialog accepts TIFF (`.tif`, `.tiff`), FITS (`.fits`, `.fit`, `.fts`), XISF (`.xisf`), PNG, JPEG and BMP. Loading tries the astronomical readers where applicable, then TIFF, OpenCV and Pillow. Successful decoding depends on the installed reader and the file layout.

Color images are retained as float32 RGB for optional source export, with a derived grayscale image for processing. The original data type and all source metadata are not preserved. Eight-bit inputs are also accepted, although higher-bit-depth sources provide more intensity information.

### Preview and export

The preview buffer has a maximum dimension of 1500 pixels. A persistent Qt worker thread processes enabled preview filters. CPU thread counts are initialized from the detected logical CPU count, and selected filters use additional thread pools.

Export recalculates the enabled filters at full resolution, scaling spatial parameters.
The final 16-bit TIFF (RGB for colour input, grayscale otherwise) includes the selected Asinh, Logarithmic or GHS
presentation stretch and **Reveal Opacity**. The comparison button is transient and
is not saved. The companion `<name>_preview.jpg` uses the same display values,
without a second gamma transformation. Fine structure can differ from a reduced preview.

**Also export independent Photoshop layers** is enabled by default. It creates a
new `<destination>_PS_layers` folder (a numbered folder if one already exists):

- `<original>_SOURCE_float32.tif`: the loaded monochrome input, before any processing;
  this is not a copy preserving the original RGB/metadata or a declaration of linearity.
- `<original>_PREPARED_float32.tif`: shared optional pre-stretch/noise-gate/bilateral preparation.
- `<original>_01_BASE_Normal.tif`: a nonlinearly stretched presentation base.
- `<original>_02_<FILTER>_Overlay.tif`, etc.: active nonzero enhancement filters,
  each calculated independently from the shared preparation, with straight alpha.
- `<original>_PS_COMBINED.tif`: the composition reconstructed from those TIFF layers.
- `recipe.json`, `CAPAS.md` and `Cargar_capas_Photoshop.jsx`: effective parameters,
  normalizations, layer order, blend modes, opacities and a Photoshop import script.

In Photoshop use **File > Scripts > Browse** and select the generated JSX. It creates
a new unsaved document, preserves the TIFF alpha and sets the layer names and settings.
The number gives the order from bottom to top. The script does not run automatically.

The independent PS composition is distinct from the sequential pipeline final.
Contrast layers use a median-centred tanh mapping to neutral grey and Overlay;
USM and ACHF use their signed detail residuals (their base terms are removed).
Their recommended opacity is capped at 35% and
multiplied by Reveal, quantized to Photoshop's 1/255 steps. These are starting
recommendations, not a translation of sequential Strength into identical pixels.
Only the base receives the display stretch: stretching the grey layers would
move their neutral value, and stretching the combined image again would break
reconstruction. No forced pre-stretch is introduced at the start of the pipeline.

The detail layers are monochrome equal-channel RGB, with an additional top Color layer for RGB input, without calibrated ICC.
NaN/Inf samples are retained as missing data. Preview reduction averages only
observed samples and keeps partially missing pixels excluded. Floating source and
preparation TIFFs retain NaN; display TIFFs use alpha zero there. A separate VALID
TIFF accompanies the layer package. Images without missing data keep the original
filter backends. With an explicit validity mask, radial statistics ignore missing
samples and Gaussian/spatial operators normalize by observed support. WOW uses a
mask-aware normalized-starlet variant on these inputs, recorded in the recipe;
it is not byte-equivalent to watroo, and its noise thresholds are approximate.
Finite lunar observations are not automatically excluded from filter input.
If a closed circular missing region is used for lunar detection, its fitted radius
is the data boundary and should be checked against the original physical limb.
Native Photoshop rendering and colour-management settings still require verification.
Export runs in the GUI thread and may temporarily make the interface unresponsive.

### Optional sources for PixInsight

**Exportar también imágenes lineales** is off by default and independent of the
Photoshop layers option. Checking it reveals the input transfer-state selector.
Declare a linear input explicitly to use `LINEAR` filenames; unspecified or
already stretched inputs use `INPUT` filenames. This option never undoes an
existing stretch or infers linearity from float32 storage.

A new `<destination>_sources` folder contains the original loaded RGB (when present),
the derived luminance, a VALID mask and metadata. Both image files use float32,
without filters, pre-stretch, presentation stretch or min/max normalization.
Pixel units and missing-data NaN are retained. RGB is retained during loading. Filters operate on the derived monochrome
image; the screen preview stays monochrome. Colour is restored only in final
export and Photoshop as described below.
Source exports retain original values even when optional neutralization is enabled. The original input file is not modified.

### Colour and optional tse-tools neutralization

RGB inputs produce a monochrome screen preview, a colour final TIFF/JPEG and a top
`<original>_<order>_RGB_Color.tif` layer in the Photoshop package. The base and
independent filter layers remain monochrome; the top layer uses **Color, 100%**
to preserve their luminosity. The generated JSX sets this mode automatically.
The reference composite uses nonseparable SetLum/ClipColor blending in display
values. Native Photoshop colour-management settings can change its rendering.

The RGB colour layer receives one luminance-guided stretch, using equal R/G/B
multipliers and a shared highlight limit. Filter layers remain at neutral grey.
No camera matrix, photometric colour calibration or ICC assignment is inferred.

**Calibrar color (tse-tools)** is off by default and enabled only for RGB declared
linear in the input selector. It assumes neutral sky/corona: sample every tenth
pixel, select joint RGB values strictly between zero and one, subtract per-channel
P1 and balance the P99−P1 spans relative to green. It then uses tse-tools's shared
negative shift and [0,1] clipping. Integer inputs use their original dtype maximum
as white; float inputs use white=1, matching tse-tools's normalized-float assumption.
NaN/Inf are excluded explicitly. Insufficient samples or constant channels produce
an explanatory error and leave neutralization off.

This is a neutralization assumption, not a measured colour calibration. It affects
only exported presentation colour, is computed lazily at export, leaves the
monochrome preview and numerical luminance filters unchanged, and
never overwrites the original RGB/L source exports. The Photoshop folder includes
the colour working input in float32 and the recipe records backgrounds, gains,
negative shift, sampling and input white. Uncheck the option to restore source colour.

Reference: [tse-tools color_calibrate](https://github.com/naavis/eclipsetools/blob/14ae3f7d823d0ac66688a32bf27d0c4b9b8a0391/src/eclipsetools/commands/utils.py).
Adapted under MIT; see [the retained notice](docs/third-party/eclipsetools-MIT.txt).

## Filter pipeline

Enabled filters run in the following fixed order. Sections can be enabled independently; their execution order cannot be rearranged in the interface.

| Stage | Operation |
| --- | --- |
| Pre-stretch | Asinh or logarithmic intensity compression before filtering |
| Radial noise gate | Radius-dependent noise suppression |
| Bilateral denoise | Smoothing based on spatial and intensity similarity |
| FNRGF | Fourier-based radial normalization, with angular segmentation, radial bins, width estimation (`std` or `mad`), linear/logarithmic binning and masking controls |
| MGN | Multi-scale Gaussian normalization |
| WOW | À trous wavelet whitening across multiple scales |
| RHEF | Radial Histogram Equalizing Filter: percentile ranking within radial rings followed by an upsilon transform |
| USM | Unsharp masking for local detail enhancement |
| ACHF | Symmetric variable circular kernel with intensity rejection, lunar-region separation, adjustable detail gain and background attenuation |

FNRGF now uses separate finite Fourier series for sector means and widths, following the coefficient and default linear-attenuation conventions in [sunkit-image's implementation](https://docs.sunpy.org/projects/sunkit-image/en/latest/_modules/sunkit_image/radial.html#fnrgf). `Coefficients to Remove` zeros the final coefficients of both series; it is not a Gaussian cutoff. Sampling requires at least `2 * order + 1` angular segments, enforced by the GUI. The core function `fnrgf_normalize` accepts explicit radial edges and independent mean/width attenuation ranges. MAD replaces only the width statistic; the intensity summary remains the mean.

The array core returns signed, dimensionless normalized values and NaN outside its domain, without smoothing or rescaling. The application wrapper preserves the original outside `application_radius < r < R_max`, builds bins between these radii, and adds Strength and optional limb protection confined to 0.95–1.05 solar radii. Global min/max rescaling and Gaussian smoothing have been removed from the default path. Consequently, brightness differs from the previous implementation, particularly at partial Strength where input intensities and dimensionless output are mixed. The GUI blend differs from sunkit-image's `ratio_mix`; this application does not claim identical final output.

For numerical safety the core ignores nonfinite samples and replaces nonpositive reconstructed widths with 1; the published reference only substitutes exactly zero widths. Empty sectors contribute zero, as in the reference; partial annuli can therefore bias the reconstruction. No equivalence test against an installed SunPy/sunkit-image environment has been run. Synthetic tests compare a fully sampled annulus with an independent direct coefficient calculation and check radial bounds, cutoff and mask locality.

WOW now delegates to `watroo.utils.wow` (pinned to 0.0.4), the backend used by [sunkit-image](https://docs.sunpy.org/projects/sunkit-image/en/stable/api/sunkit_image.enhance.wow.html). See Auchère et al. (2023), [Image enhancement with wavelet-optimized whitening](https://doi.org/10.1051/0004-6361/202245345). B3-spline decomposition, whitening, significance and reconstruction are provided by the library. There is no fixed camera gain/read-noise model and no z-normalization of the result. The wrapper returns a copy for Strength zero; its backend result is affinely mapped to input intensity units before the external Strength blend. Constant images return zero detail explicitly to avoid a degenerate coarse normalization.

WOW controls include automatic scales (`0`, the default), three independent denoising significance levels (`0` disables that scale), and standard or bilateral (`1`) processing. Scales are capped to the image dimensions. Later detail scales are not implicitly denoised. Denoising defaults to disabled; when requested, watroo estimates noise from the current input. The API also accepts a calibrated nonnegative noise map in current input units. Noise estimates after nonlinear upstream filtering are not necessarily a detector-noise model. Export adjusts the preview scale count by the nearest integer to log2(export/preview size), capped to the target dimensions. Auto is resolved at preview resolution before this adjustment. Denoising thresholds move with their spatial bands; additional finer bands inherit the finest threshold. This is an approximate spatial match because starlet supports are powers of two. Tests compare the wrapper directly against installed watroo for standard/bilateral processing, denoising and supplied noise maps.

Strength controls default to 10% while filter sections remain disabled. Toggling a checkbox preserves the configured Strength, including zero. Releasing Strength at zero recalculates to remove its effect. PRE-STRETCH activation also requests processing. Worker exceptions are reported in the status label and release the processing state so subsequent requests can run. Manual mode still requires the refresh button. All nine filter sections have been exercised through the Qt background worker on synthetic data.

MGN uses `mgn_normalize`, following the numerical operations of [sunkit-image 0.7.0](https://docs.sunpy.org/projects/sunkit-image/en/stable/_modules/sunkit_image/enhance.html#mgn): six default sigmas `(1.25, 2.5, 5, 10, 20, 40)`, equal weights, nearest-edge Gaussian convolution, zero-deviation substitution, arctangent compression and global gamma combination. The reference publication is Morgan & Druckmüller (2014), DOI `10.1007/s11207-014-0523-9`. Nonpositive input values are replaced with a small positive value on a private copy, with no mask normalization, deviation floor or final percentile rescaling. NaNs propagate, as with the reference. The helper also accepts custom weights, clipping and gamma bounds. It preserves the caller's input and NumPy error settings.

MGN slider units map directly: Gamma / 10, k / 100 and h / 100; truncation values 1–6 are honored. Strength is an external application blend; the core result is affinely mapped to the input intensity range before mixing, including at 100%. The scientific core itself remains unchanged. Sigmas remain in input pixels in both preview and export, matching official parameter semantics rather than maintaining a common spatial scale between resolutions. Tests match a separate transcription of the published implementation exactly on synthetic inputs, including custom weights and multiple truncations; no installed-library comparison or real-image validation is claimed.

RHEF uses `rhef_normalize`, a separate array core following [sunkit-image RHEF](https://docs.sunpy.org/projects/sunkit-image/en/stable/api/sunkit_image.radial.rhef.html) and its `scipy` ranking method. The library cites Gilly's thesis (2022) and Gilly & Cranmer; its [example](https://docs.sunpy.org/projects/sunkit-image/en/stable/generated/gallery/radial_histogram_equalization.html) discusses dense radial bins and upsilon. Equal intensities receive average ranks divided by the number of valid pixels in the annulus. Application radius and the validity mask are applied before ranking; nonfinite pixels are excluded. The double-sided upsilon transform selects its branches using the mean rank of each annulus, following `sunkit-image`'s utility convention. This is a compatibility choice, not a claim that its mean-based split is a universal scientific definition.

The core accepts explicit radial edges, optional separate lower/upper upsilon exponents or `None` to bypass upsilon, and returns NaN outside its domain. Vignette is applied after ranking, as in the reference. The application wrapper preserves the original below the application radius, exposes an external Strength blend, and no longer rescales percentiles. At full Strength processed pixels are dimensionless; partial Strength mixes these with input intensities. The GUI's upsilon range 0.01–1.00 is honored without a hidden lower clamp. `Ring Width (×10 preview px)` controls bin spacing; export scales the width to full-resolution pixels, preserving approximate spatial scale while recalculating ranks from full-resolution samples. Preview and export are not expected to match pixel for pixel.

RHEF tests cover ties, constant rings, per-ring upsilon, radial and validity masks, vignette, ring independence and small exponents. The implementation has not been compared against an installed sunkit-image environment or validated for quantitative scientific inference.

ACHF is an original implementation of the variable-kernel principles in Druckmüller, Rušin and Minarovjech (2006), section 4.2, equation (7), not a reproduction of Corona 3.0: [original publication](https://www.astro.sk/caosp/Eedition/FullTexts/vol36no3/pp131-148.pdf). Opposite neighbors are accepted together when both satisfy the intensity threshold and belong to the center pixel's lunar/coronal region. The normalized spatial weights define a symmetric local kernel. The output is `background * image + gain * (image - local_mean)`, without clipping; Strength blends this output with the input. Threshold is a percentage of the current filter input's intensity range, and support radius is in tenths of pixels. Gaussian width is one third of the support radius. These choices are implementation parameters, not prescriptions from the paper.

ACHF has O(pixels × radius²) cost and O(pixels) working memory, so large full-resolution supports can be slow. Preview and export recalculate adaptive neighborhoods independently. Local spectral properties do not prove that the entire image-dependent operator is artifact-free; real-image validation remains necessary.

These are local implementations. Filter names do not establish numerical equivalence to external reference software or validation for quantitative scientific measurements.

Start with a small number of active filters and moderate strength. Check disk geometry before applying radial filters. Increase angular segments when increasing Fourier order, and inspect the result for amplified noise, clipping or radial artifacts. Recommended values populated by the application depend on the detected disk radius and image size; they are starting points for visual adjustment.

The final display offers Asinh, Logarithmic and Generalized Hyperbolic Stretch (GHS). GHS includes a symmetry-point picker, shape and black-point controls.

## Project structure

```text
main.py                       Application entry point and CPU setup
config.py                     Stylesheet, constants and legacy defaults
requirements.txt              Installation dependencies
core/
    __init__.py               Exports FilterWorker
    filters.py                Active preview and export filter implementations
    image_loader.py           Standalone image-loading helpers, currently unused by GUI
    image_export.py           Standalone TIFF-export helper, currently unused by GUI
    moon_detection.py         Standalone lunar detection, currently unused by GUI
gui/
    __init__.py               Package exports
    app.py                    Window, controls, geometry, loading, export and rendering
    components.py             Image canvas and collapsible filter sections
    factories.py              Slider and input factories
utils/
    __init__.py
    helpers.py                Resource path resolution
scripts/
    medir_g_r.py               Independent camera gain/noise estimation script
```

The active path is `main.py` → `gui.app.EclipseProcessorApp` → `core.filters.FilterWorker`. The GUI currently implements loading, export and lunar detection directly rather than calling the corresponding standalone modules in `core/`.

The application uses PySide6. Earlier documentation referring to PyQt5, `main_new.py`, 39 filters, additional GUI modules or guaranteed processing times does not describe this version. Many constants and legacy filter defaults in `config.py` are not consumed by the current GUI, whose controls define their own initial values.

`icono.ico` is selected when present, with `icono.png` as fallback. `icono.icns` is an additional macOS resource and is not selected by the current startup code.

### Development utilities

- `generate_code_dump.py` creates `project_code_dump.txt` from Python source files. The dump is generated material, not the authoritative source, and need not be committed.
- `scripts/medir_g_r.py` estimates a variance-versus-mean slope and noise term from paired NEF flats and dark frames. It requires `rawpy` in addition to NumPy; `rawpy` is not an application dependency. The script reads `dark/*.NEF` and `flat/*.NEF` relative to the working directory and uses a fixed ROI. Run it from the directory containing those folders, after checking the ROI and available frame pairs.
- Backup files such as `core/filters - copia.py` and `icono copia.png` are not used by the application.

For development, keep `.venv/`, Python caches, local image data and generated dumps out of version control. Preserve any original assets or backups you still need separately.

## Troubleshooting and verification

- **Missing module:** activate the intended environment and install `requirements.txt` with that environment's Python. Run `python main.py` from the project directory.
- **Dependency installation failure:** inspect the package named in the error and whether its declared version has a compatible distribution for your Python and platform. The declared minimum versions are not a record of a verified installation matrix.
- **Qt startup error on Linux:** inspect the Qt platform-plugin error and install the libraries required by that platform plugin. An offscreen platform does not provide an interactive desktop window.
- **Image loading failure:** inspect terminal output, check the image with its source application, and confirm the appropriate decoder is installed.
- **Slow processing:** disable Auto Calculate while changing settings, reduce Fourier order or wavelet scales, and enable only necessary filters. Full-resolution export takes longer than preview processing.
- **Unexpected radial artifacts:** verify disk center/radius and review radial binning, angular resolution and filter strength.

Before publishing a release, manually check startup, supported input formats, automatic and manual geometry, filter toggles, refresh, original comparison, display stretch, full-resolution export and window closure. Inspect both output files, including dimensions and TIFF bit depth. Run the filter synthetic checks with `python -m unittest discover -s tests -v`. They cover constant-background attenuation, edge isolation, kernel symmetry and frequency response, rotational consistency, bypass and invalid input. Visual validation on real eclipse images remains necessary.

## Algorithm credits, scientific references and acknowledgements

Eclipse Image Processor is developed by Francisco Bitto. Its enhancement tools build on the scientific work and open-source projects credited below. Credit for an algorithm belongs to its original authors; the application adds its own interface, parameter handling, masking, blending and export workflow. Please cite the relevant methods as well as this application when publishing processed images.

### Software and implementation sources

| Project / authors | Contribution to this application |
| --- | --- |
| [sunkit-image](https://github.com/sunpy/sunkit-image), the SunPy community and contributors | Numerical implementation reference for MGN, FNRGF, RHEF and Upsilon, particularly version 0.7.0. The array implementations here follow the documented conventions with the differences described above. SunPy and sunkit-image are reference projects, not application runtime dependencies. See their [documentation](https://docs.sunpy.org/projects/sunkit-image/en/stable/) and [license](https://github.com/sunpy/sunkit-image/blob/main/LICENSE). |
| [watroo / wavelets](https://github.com/frederic-auchere/wavelets), Frédéric Auchère and contributors | Direct runtime backend for standard and bilateral WOW, B3-spline à trous decomposition and wavelet noise tools; pinned to `watroo==0.0.4`. The explicit-mask path is an application-specific normalized-starlet variant, not an identical implementation. See the upstream [MIT license](https://github.com/frederic-auchere/wavelets/blob/master/LICENSE.rst). |
| [tse-tools / eclipsetools](https://github.com/naavis/eclipsetools), Samuli Vuorinen (`naavis`) | The optional RGB P1/P99 neutralization adapts `color_calibrate` from [revision `14ae3f7`](https://github.com/naavis/eclipsetools/blob/14ae3f7d823d0ac66688a32bf27d0c4b9b8a0391/src/eclipsetools/commands/utils.py), adding explicit nonfinite-data handling and application integration. Copyright © 2025 Samuli Vuorinen; the [MIT notice is retained locally](docs/third-party/eclipsetools-MIT.txt). The upstream package is not required at runtime. |
| [Agentic Eclipse Library (AEL)](https://github.com/PeterWar/Agentic-Eclipse-Library), Pere Guerra Serra (`PeterWar` / Peter War) | Acknowledged for the study of continuous radial statistics that inspired the independently implemented global continuous RHEF, and for research references concerning observed-pixel masks and adjustable corona layers. The comparison used AEL 1.3.2, [revision `5629b37`](https://github.com/PeterWar/Agentic-Eclipse-Library/tree/5629b37071ec87a32f3cf37b5ce6dfcc8b02ada1). AEL is MIT-licensed, copyright © 2026 Pere Guerra Serra; its package/modules are not bundled or required by this application. See the [comparison and attribution notes](docs/ael-filter-review.md) and [continuous RHEF implementation notes](docs/rhef-continuous.md). |
| [EclipseForgeHDR](https://github.com/naugustin77/EclipseForgeHDR), `naugustin77` and contributors | Additional comparative reference during the filter/export workflow review. This acknowledgement records the research source, not a runtime dependency or a claim that its detail algorithm is implemented here; see the [review](docs/pipeline-photoshop-review-20261017.md). |

### Scientific methods

| Method | Original scientific reference and relationship to this application |
| --- | --- |
| FNRGF | **Hana Druckmüllerová, Huw Morgan and Shadia Rifai Habbal (2011)**, *Enhancing Coronal Structures with the Fourier Normalizing-radial-graded Filter*, The Astrophysical Journal **737**, 88. [DOI: 10.1088/0004-637X/737/2/88](https://doi.org/10.1088/0004-637X/737/2/88). Fourier radial normalization; numerical conventions also informed by [sunkit-image FNRGF](https://docs.sunpy.org/projects/sunkit-image/en/stable/api/sunkit_image.radial.fnrgf.html), which cites Druckmüllerová's doctoral thesis, *Application of adaptive filters in processing of solar corona images*. |
| MGN | **Huw Morgan and Miloslav Druckmüller (2014)**, *Multi-scale Gaussian normalization for solar image processing*, Solar Physics **289**, 2945–2955. [DOI: 10.1007/s11207-014-0523-9](https://doi.org/10.1007/s11207-014-0523-9); [author preprint](https://arxiv.org/abs/1403.6613). Scientific basis of the multiscale Gaussian normalization core. |
| WOW | **Frédéric Auchère, Elie Soubrié, Gabriel Pelouze and Éric Buchlin (2023)**, *Image enhancement with wavelet-optimized whitening*, Astronomy & Astrophysics **670**, A66. [DOI: 10.1051/0004-6361/202245345](https://doi.org/10.1051/0004-6361/202245345); [open-access paper](https://www.aanda.org/articles/aa/full_html/2023/02/aa45345-22/aa45345-22.html). Scientific basis of standard/bilateral whitening and significance-based denoising supplied by watroo. |
| RHEF and Upsilon | **Chris R. Gilly and Steven R. Cranmer (2025)**, *Visualization of High Dynamic Range Solar Imagery and the Radial Histogram Equalizing Filter*, Solar Physics **300**, 174. [DOI: 10.1007/s11207-025-02578-x](https://doi.org/10.1007/s11207-025-02578-x); [author preprint](https://arxiv.org/abs/2511.02798). Credit for radial histogram equalization and the Upsilon redistribution function. The compatible mode follows sunkit-image's ranking/branch conventions; the continuous mode adds the AEL-inspired interpolation described above. |
| ACHF / adaptive circular high-pass | **Miloslav Druckmüller, Vojtech Rušin and Milan Minarovjech (2006)**, *A new numerical method of total solar eclipse photography processing*, Contributions of the Astronomical Observatory Skalnaté Pleso **36**, 131–148. [Original paper](https://www.astro.sk/caosp/Eedition/FullTexts/vol36no3/pp131-148.pdf), §4.2, equation (7). The application independently implements variable-kernel principles with its own symmetric acceptance, gain and background parameters; it does not reproduce Corona 3.0. |
| NRGF background | **Huw Morgan, Shadia Rifai Habbal and Richard Woo (2006)**, *The Depiction of Coronal Structure in White Light Images*, Solar Physics **236**, 263–272. [DOI: 10.1007/s11207-006-0113-6](https://doi.org/10.1007/s11207-006-0113-6); [author preprint](https://arxiv.org/abs/astro-ph/0602174). Foundational radial-normalization reference used in the research review; a separate NRGF stage is not currently exposed in the application. |

### Other processing and presentation credits

- **Unsharp masking (USM), Gaussian filtering, histogram ranking, Asinh and logarithmic stretches** are established image-processing techniques. Their application-specific composition and controls are implemented here using NumPy and SciPy; no single new scientific authorship is claimed for these standard operations.
- **Radial noise gate and the section labelled Bilateral denoise** use application-specific recipes. The latter currently mixes Gaussian smoothing according to gradient weights; it is not a canonical bilateral filter. The bilateral WOW backend is separately credited to Auchère and collaborators above.
- **Generalised Hyperbolic Stretch:** credit to **David Payne and Mike Cranfield** for the established GHS method and tools; see their [reference documentation](https://www.ghsastro.co.uk/doc/tools/GeneralizedHyperbolicStretch/GeneralizedHyperbolicStretch.html). The application's current `apply_ghs` uses its own Asinh-based curve with symmetry, shape and black-point controls; the UI label does not establish mathematical equivalence to their published GHS transformations.
- **Colour/Overlay compositing:** the reference layer reconstruction uses the nonseparable `SetLum` / `ClipColor` and Overlay blending conventions documented in [W3C Compositing and Blending Level 1](https://www.w3.org/TR/compositing-1/). The Photoshop JSX applies native blend modes; Adobe Photoshop is a separate product.

### Supporting open-source libraries

Thanks to the maintainers and contributors of [Python](https://github.com/python/cpython), [Qt / PySide6](https://code.qt.io/cgit/pyside/pyside-setup.git/), [NumPy](https://github.com/numpy/numpy), [SciPy](https://github.com/scipy/scipy), [OpenCV](https://github.com/opencv/opencv), [Pillow](https://github.com/python-pillow/Pillow), [Astropy](https://github.com/astropy/astropy), [xisf](https://pypi.org/project/xisf/) and [tifffile](https://github.com/cgohlke/tifffile). Their roles are listed under Requirements and installation. The optional camera-noise development script also uses [rawpy](https://github.com/letmaik/rawpy).

Each upstream project retains its own copyright and license. Scientific citations and acknowledgements supplement those notices; this repository's MIT license does not relicense its dependencies. Reference comparisons and independent adaptations do not imply endorsement or identical numerical output.

## Support, citation and license

Report reproducible problems through [GitHub Issues](https://github.com/fbitto/Eclipse-Image-Processor/issues), including Python and dependency versions, operating system, filter settings and terminal errors.

When citing the software, identify Francisco Bitto, *Eclipse Image Processor*, the repository URL and the exact release or commit used.

Licensed under the [MIT License](LICENSE).

MGN and WOW presentation blends use the full finite output range and input range to put both images in common intensity units. This avoids the original image overwhelming a dimensionless filter result below nearly 100% Strength. No percentile clipping is applied. Strength interpolates linearly from the original (0%) to the mapped filter result (100%), without a special discontinuity at 100%. Direct core/backend results remain available for numerical comparison; application outputs include this documented affine presentation step.

Preview, export and GUI now share this order: Pre-stretch → Radial Noise Gate → Denoise → FNRGF → MGN → WOW → RHEF → USM → ACHF. RHEF is optional after multiscale enhancement; this enables MGN → RHEF and WOW → RHEF without implying that all filters should be enabled together.

Spatial export parameters preserve preview footprints: MGN sigmas, RHEF ring widths, denoising and USM widths, ACHF support and its minimum Gaussian width, and radial noise-gate widths scale with resolution. FNRGF defaults to 4 pixels per ring at each processing resolution and recalculates its ring count on export. For logarithmic spacing this specifies the inner-ring width; outer rings are wider. Strengths, intensity thresholds, gains and angular controls remain unchanged.
