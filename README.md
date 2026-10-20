# Eclipse Image Processor

Desktop application for enhancing solar eclipse and corona images, written in Python with PySide6, NumPy, SciPy and OpenCV.

**Author:** Francisco Bitto  
**Version:** v0.5.0

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

To build a standalone macOS application (`.app`) or a drag-to-install disk image (`.dmg`), see the [macOS build instructions](docs/build-macos.md).

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
3. Enable the desired filter sections and adjust their controls. Sliders display actual parameter values and units. Drag or use keyboard arrows to adjust them; the mouse wheel scrolls the sidebar without changing sliders or dropdown selections. **Auto Calculate** waits 650 ms after the last relevant adjustment before recomputing the preview. Changing a filter during processing requests cancellation and schedules only the latest settings after the pause. Cancellation is checked between operations and within long filter loops; an active native/library operation finishes before the next check. Obsolete results are discarded. Disable it while adjusting several settings and use the refresh button to process manually.
4. Keep **Full-resolution verification preview** enabled to inspect the native calculation after display stretching and reduction. Disable it for a faster, approximate monochrome preview. Use **View Original** to compare, then adjust the final stretch and blend.
5. Click **Export Final Image** and choose a TIFF destination.

### Input formats

The file dialog accepts TIFF (`.tif`, `.tiff`), FITS (`.fits`, `.fit`, `.fts`), XISF (`.xisf`), PNG, JPEG and BMP. Loading tries the astronomical readers where applicable, then TIFF, OpenCV and Pillow. Successful decoding depends on the installed reader and the file layout.

Color images are retained as float32 RGB for optional source export, with a derived grayscale image for processing. The original data type and all source metadata are not preserved. Eight-bit inputs are also accepted, although higher-bit-depth sources provide more intensity information.

### Preview and export

The preview buffer has a maximum dimension of 1500 pixels. By default, a persistent Qt worker computes enabled filters at native resolution, applies the final presentation there and reduces the rendered result for display. This verification view includes source color and optional neutralization. Native numerical output is cached for export; changing the image, geometry, masks or filter parameters invalidates it. Display controls reuse the numerical result. Disabling verification selects a faster, approximate monochrome calculation on the reduced input. CPU thread counts are initialized from the detected logical CPU count.

Export uses a matching cached native result or calculates the enabled filters at full resolution, scaling spatial parameters.
The final 16-bit TIFF (RGB for color input, grayscale otherwise) includes the selected Asinh, Logarithmic or GHS
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
Contrast layers use a median-centered tanh mapping to neutral gray and Overlay;
Tangential detail and ACHF use their signed detail residuals (their base terms are removed).
Their recommended opacity is capped at 35% and
multiplied by Reveal, quantized to Photoshop's 1/255 steps. These are starting
recommendations, not a translation of sequential Strength into identical pixels.
Only the base receives the display stretch: stretching the gray layers would
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
The lunar-statistics exclusion is enabled by default: finite lunar samples remain unchanged and do not constrain enhancement statistics. An optional bright-limb percentile exclusion retains those samples too. Both are separate from missing-data validity; the layer package includes a STATISTICS_SUPPORT TIFF. Statistics exclusions also select the observed-support WOW variant.
If a closed circular missing region is used for lunar detection, its fitted radius
is the data boundary and should be checked against the original physical limb.
Native Photoshop rendering and color-management settings still require verification.
Export runs in the GUI thread and may temporarily make the interface unresponsive.

### Optional sources for PixInsight

**Also export linear images** is off by default and independent of the
Photoshop layers option. Checking it reveals the input transfer-state selector.
The input selector defaults to linear, which uses `LINEAR` filenames; select unspecified or
already stretched input to use `INPUT` filenames. This option never undoes an
existing stretch or infers linearity from float32 storage.

A new `<destination>_sources` folder contains the original loaded RGB (when present),
the derived luminance, a VALID mask and metadata. Both image files use float32,
without filters, pre-stretch, presentation stretch or min/max normalization.
Pixel units and missing-data NaN are retained. RGB is retained during loading. Filters operate on the derived monochrome
image; the fast preview stays monochrome. Source color is included in the verification preview, final export and Photoshop as described below.
Source exports retain original values even when optional neutralization is enabled. The original input file is not modified.

### Color and optional tse-tools neutralization

RGB inputs produce a monochrome fast preview, a color verification preview and final TIFF/JPEG, and a top
`<original>_<order>_RGB_Color.tif` layer in the Photoshop package. The base and
independent filter layers remain monochrome; the top layer uses **Color, 100%**
to preserve their luminosity. The generated JSX sets this mode automatically.
The reference composite uses nonseparable SetLum/ClipColor blending in display
values. Native Photoshop color-management settings can change its rendering.

The RGB color layer receives one luminance-guided stretch, using equal R/G/B
multipliers and a shared highlight limit. Filter layers remain at neutral gray.
No camera matrix, photometric color calibration or ICC assignment is inferred.

New images default to **Input: linear**, **Calibrate color** enabled for RGB,
and **Full-resolution verification preview** enabled. The input selector can
still be changed for already stretched data. Color neutralization requires RGB
input declared linear. Selecting unspecified or already stretched input unchecks
and disables **Calibrate color**; monochrome input also disables it.

**Calibrate color (tse-tools)** assumes neutral sky/corona: sample every tenth
pixel, select joint RGB values strictly between zero and one, subtract per-channel
P1 and balance the P99−P1 spans relative to green. It then uses tse-tools's shared
negative shift and [0,1] clipping. Integer inputs use their original dtype maximum
as white; float inputs use white=1, matching tse-tools's normalized-float assumption.
NaN/Inf are excluded explicitly. Insufficient samples or constant channels produce
an explanatory error and leave neutralization off.

This is a neutralization assumption, not a measured color calibration. It affects
presentation color in verification/export, is computed lazily when needed, leaves the
numerical luminance filters unchanged, and
never overwrites the original RGB/L source exports. The Photoshop folder includes
the color working input in float32 and the recipe records backgrounds, gains,
negative shift, sampling and input white. Uncheck the option to restore source color.

Reference: [tse-tools color_calibrate](https://github.com/naavis/eclipsetools/blob/14ae3f7d823d0ac66688a32bf27d0c4b9b8a0391/src/eclipsetools/commands/utils.py).
Adapted under MIT; see [the retained notice](docs/third-party/eclipsetools-MIT.txt).

## Filters and parameters, in interface order

**Advanced mode**, below **Calibrate color**, is off by default. Basic mode shows
the usual controls; advanced mode reveals all parameters, including MGN scales
and weights. FNRGF keeps its original controls through **Apply Mask (%)** visible
in basic mode. The parameter tables below list both basic and advanced controls.

Basic WOW has one noise threshold, initially zero: editing it sets the same
threshold for every scale. Advanced mode exposes individual thresholds. Basic
RHEF has one Upsilon control: editing it links both tails. Switching modes alone
preserves all settings; a notice appears in basic mode if individual WOW
thresholds or separate RHEF tails remain active from advanced editing. Editing
the corresponding basic control replaces those individual settings. Hidden
parameters remain active with their current values; changing modes does not
reset them or recalculate the image.

### Basic and advanced controls

**Active** and **Strength** remain visible for every enhancement. The table lists
the other controls available in basic mode and those added by advanced mode.

| Section | Basic mode | Additional controls in advanced mode |
| --- | --- | --- |
| Geometry | Center X/Y, Radius, scale information and automatic lunar detection | Lunar/statistics exclusions, lunar guard, bright-limb percentile and annulus radius |
| Pre-stretch | Active, type and intensity | No additional controls |
| Radial Noise Gate | SNR Threshold | Local sigma and Gate sigma |
| Edge-preserving Denoise | Blur Sigma and Edge Sensitivity | No additional controls |
| FNRGF | Model, Fourier Order, Angular Segments, Coefficients to Remove, Application Radius, Outer Radius, Ring Width, Width Function, Radial Binning and Apply Mask (%) | Model smoothing, Boundary fade, Harmonic regularization, Minimum width fraction, Robust fit iterations, Minimum samples per sector and highest-harmonic mean/width weights |
| MGN | Gamma, Factor k and Global Weight h | Kernel Truncation, all six scales and their individual weights |
| WOW | One Noise threshold (all scales, sigma), initially 0 | Native wavelet scale count, individual denoising thresholds, Standard/Edge-aware mode and Bilateral intensity scale |
| RHEF | One Upsilon control, linked to both tails when edited | Algorithm mode, Application Radius, Ring Width, separate upper-tail exponent and linking checkbox, minimum samples, quantile samples and Noise confidence |
| Tangential Detail | Angular Gaussian sigma and Noise threshold | Detail gain, inner/outer radii, Limit outer radius and Boundary fade |
| ACHF | Support Radius and Intensity Threshold | Contrast Gain and Background Retention |
| Final Stretch | Algorithm, intensity and Reveal Opacity; GHS also shows SP, its image picker and Local Intensity (b) | GHS shadow/highlight protection (LP/HP) and post-stretch black/white points |

Input transfer state, color calibration, preview verification and export options
are independent of Advanced mode. Controls that require a particular algorithm,
RGB input or an available wavelet scale retain their normal availability rules.

The interface and sequential pipeline use this order:

**Pre-stretch → Radial Noise Gate → Edge-preserving Denoise → FNRGF → MGN → WOW → RHEF → Tangential Detail → ACHF → Final Stretch.**

Filter sections start inactive. Each enhancement's **Strength** spans 0–100% and starts at 10%: zero is an exact bypass; 100% uses the complete application filter result. **Active** enables the section without resetting its controls. Pre-stretch has an enable checkbox and its own factor instead of Strength. Using every filter together is optional.

All displayed slider values are actual parameter values. **Preview px** means pixels in the reduced working buffer: spatial widths scale to native pixels for verification/export. Geometry uses native pixels; normalized radii use the reference disk radius R. FNRGF ring width is the exception: it uses pixels of each processing resolution. Angular widths, dimensionless coefficients and percentages do not scale with resolution. Loading an image populates geometry-dependent starting values; the tables describe available ranges rather than universal recommended settings.

### Geometry and statistics support

These controls appear above the filters and affect their geometry and sample selection.
Statistics-support controls are visible only in advanced mode. Lunar exclusion
remains enabled by default and effective in basic mode.

| Parameter | Range / units | Effect |
| --- | --- | --- |
| Center X / Y and Radius | Native image pixels; radius must be positive | Define the center and reference radius for radial processing and the circle overlay. Automatic detection estimates these values; check the fit at the limb. |
| Exclude lunar disk from filter statistics | On by default | Excludes finite lunar samples from enhancement statistics while preserving their input values. |
| Lunar guard | 0–64 preview px | Extends the lunar statistics exclusion beyond the reference limb. |
| Exclude bright limb samples from statistics | Off by default | Excludes selected bright samples from statistics and preserves those pixels. This is a brightness heuristic, not a prominence classifier. |
| Bright-limb percentile | 90–100; default 99.5 | Samples above this percentile are excluded within the limb annulus. A value of 100 excludes none. |
| Limb annulus outer radius | 1.1–3 R; default 1.5 R | Sets the outer edge of the bright-sample selection annulus; its inner edge is 1 R. |

Statistics support is separate from missing-data validity. NaN/Inf remain missing; finite excluded samples remain observed input pixels. The support-aware paths normalize spatial operators by observed support. In WOW, these exclusions select the application's normalized-starlet variant.

### 1. Pre-stretch (entry)

Compresses input intensity before noise suppression and enhancement. Asinh uses `asinh(factor × x)/asinh(factor)`; logarithmic mode uses `log(1 + K × x)/log(1 + K)` on normalized input. The result is mapped back to input units. This changes what subsequent filters receive; it is independent of Final Stretch.

| Parameter | Range | Effect |
| --- | --- | --- |
| Pre-stretch Type | Asinh / Logarithmic | Selects the compression curve. |
| Asinh Factor | 1–100 | Higher values lift faint normalized intensities more strongly. |
| Logarithmic K | 1–1000000, logarithmic steps | Controls logarithmic compression; K itself is displayed. |
| Active | Off by default | Enables entry compression. |

### 2. Radial Noise Gate

Estimates a local signal-to-residual-spread ratio and attenuates low-ratio pixels. The effective threshold increases with radius as `base threshold × (1 + 2r/R)`. This is an application-specific local contrast gate, not a calibrated detector SNR measurement.

| Parameter | Range | Effect |
| --- | --- | --- |
| Gate Strength | 0–100% | Blends the attenuation with the input. |
| SNR Threshold | 0–5 | Higher thresholds attenuate more low-ratio signal; zero bypasses the gate. |
| Local sigma | 0.5–20 preview px; default 3 | Gaussian width for local signal and residual-spread estimates. |
| Gate sigma | 0–20 preview px; default 2 | Smooths the attenuation map; zero disables that smoothing. |

### 3. Edge-preserving Denoise

Uses Gaussian smoothing with a gradient-dependent blend: stronger gradients retain more input signal. Despite the historical internal name `bilateral`, this stage is **gradient-weighted Gaussian smoothing**, not a full bilateral neighborhood filter. The edge-aware option inside WOW is a separate algorithm.

| Parameter | Range | Effect |
| --- | --- | --- |
| Strength | 0–100% | Blends denoised and input images. |
| Blur Sigma | 0.5–20 preview px | Sets the Gaussian smoothing width. |
| Edge Sensitivity | 0–1 | Higher values retain more original signal at strong gradients; zero removes gradient-dependent protection. |

### 4. FNRGF — Fourier Normalizing Radial Gradient Filter

Removes a modeled radial/angular brightness background and normalizes by modeled spread to reveal coronal structure. The scientific basis is [Druckmüllerová, Morgan & Habbal (2011)](https://doi.org/10.1088/0004-637X/737/2/88).

**Continuous / support-aware** is the default application variant: observed sectors constrain population-weighted, regularized Fourier models of mean intensity and log-width. Optional robust passes reduce outlier influence. Radial smoothing and interpolation connect populated models; absent sectors do not become zero observations. Width estimates require at least two samples in each contributing sector and at least three measured sector widths in a ring. Sparse model regions retain the input.

**Reference-compatible** follows the separate finite Fourier series and attenuation conventions in [sunkit-image](https://docs.sunpy.org/projects/sunkit-image/en/stable/api/sunkit_image.radial.fnrgf.html). Empty sectors follow the compatible zero-contribution convention and can bias partial annuli. This application uses its own output scaling and Strength blend, rather than the reference `ratio_mix`; final pixels are not claimed identical to sunkit-image.

| Parameter | Range | Effect |
| --- | --- | --- |
| Model | Continuous / support-aware; Reference-compatible | Selects the modeling convention. |
| Strength | 0–100% | Blends the input with normalized structure mapped into input intensity units. |
| Fourier Order | 1–24 | Highest angular harmonic in the mean and width models; higher orders follow finer angular variations. |
| Angular Segments | Powers of two, up to 1024 | Samples each ring angularly. The minimum is raised to satisfy segments ≥ `2 × order + 1`; higher manual values are retained. |
| Coefficients to Remove | 0–order+1 | Zeros the last model harmonic weights; zero removes none. Continuous log-width retains its DC term to preserve a positive scale. |
| Application Radius | 0.5–2.5 R | Inner processing boundary; input below it is preserved. |
| Outer Radius | Greater than inner radius by at least 0.1 R | Outer processing boundary; maximum adjusts to reach the farthest image corner. |
| Ring Width | 1–32 processing pixels; default 4 | Determines radial bin count at each resolution. In logarithmic binning this specifies the inner-ring width. |
| Width Function | STD / MAD | Uses standard deviation or scaled median absolute deviation for sector spread; the intensity summary remains the mean. |
| Radial Binning | Linear / Log-spaced | Equal-width rings or rings growing wider outward. |
| Apply Mask | 0–100% | Protects original signal in a triangular band from 0.95 to 1.05 R; maximum protection occurs at 1 R. This is separate from validity/statistics masks. |
| Model smoothing | 0–64 preview px; default 8 | Continuous mode only: radial Gaussian sigma of background-model coefficients, not of the photograph. |
| Boundary fade | 0–128 preview px; default 8 | Continuous mode only: smooth transition at inner/outer processing boundaries. |
| Harmonic regularization | 0–1; default 0.01 | Continuous mode only: damps high harmonics; penalty increases automatically with incomplete angular coverage. |
| Minimum width fraction | 0–1; default 0.05 | Floors modeled spread relative to typical annular spread, limiting division by very small widths. |
| Robust fit iterations | 0–5; default 2 | Continuous mode only: residual-based reweighting passes; zero uses the initial regularized fit. |
| Minimum samples per sector | 1–32 | Rejects sectors below this population. Continuous spread estimates additionally require at least two samples. |
| Highest-harmonic mean weight | 0–1 | Endpoint of the linear attenuation applied to mean-model harmonics. |
| Highest-harmonic width weight | 0–1 | Endpoint of width-harmonic attenuation; continuous mode models log-width. |

Continuous-only controls are disabled in compatible mode. The array cores return dimensionless structure; application wrappers preserve pixels outside the supported processing domain and map usable output to input units before blending.

### 5. MGN — Multi-scale Gaussian Normalization

Normalizes local contrast at six Gaussian scales, compresses it with an arctangent, averages the local contributions and combines them with a global gamma image. The core follows [Morgan & Druckmüller (2014)](https://doi.org/10.1007/s11207-014-0523-9) and sunkit-image's numerical conventions. With complete support it uses nearest-edge Gaussian convolution and substitutes zero deviations. Statistics/missing-data exclusions use support-normalized operations.

| Parameter | Range | Effect |
| --- | --- | --- |
| Strength | 0–100% | Blends the input with the MGN result mapped to input intensity units. |
| Gamma | 0.1–10; default 3.2 | Controls the global gamma component. |
| Factor k | 0–5; default 0.7 | Controls arctangent compression of locally normalized contrast. |
| Global Weight h | 0–1; default 0.7 | Zero selects the local multiscale component; one selects the global gamma component. |
| Kernel Truncation | 1–6 sigma; default 3 | Sets the Gaussian support cutoff in standard deviations. |
| Scale 1–6 sigma | Each 0.25–128 preview px | Six independent Gaussian widths; defaults are 1.25, 2.5, 5, 10, 20 and 40 preview px. |
| Scale 1–6 weight | Each 0–2; default 1 | Weights each local contribution. Zero removes that contribution; normalization still divides by six scales. |

The application performs an affine range mapping before Strength blending, without percentile clipping; the dimensionless core remains available separately for numerical comparisons.

### 6. WOW — Wavelet-optimized Whitening

Whitens and combines à trous wavelet scales, with optional significance-based noise suppression. [Auchère et al. (2023)](https://doi.org/10.1051/0004-6361/202245345) describe the method. Standard and edge-aware processing on complete unmasked input use `watroo.utils.wow`, pinned to 0.0.4. Explicit missing-data/statistics exclusions instead use the application's observed-support normalized-starlet variant; its noise factors are approximate and it is not byte-equivalent to watroo.

| Parameter | Range | Effect |
| --- | --- | --- |
| Strength | 0–100% | Blends the input with the backend output mapped to input intensity units. |
| Native wavelet scales | 0 = Auto; otherwise available scales up to 10 | Auto uses the native-image maximum. Available count depends on image dimensions; unavailable controls are disabled. |
| Denoise Scale 1–10 | Each 0–10 estimated sigma; default 0 | Independent soft significance threshold for each available native band. Zero disables suppression in that band; larger values reject weaker detail. |
| Processing mode | Standard WOW / Edge-aware WOW | Selects standard or bilateral wavelet processing; edge-aware is the initial selection. |
| Bilateral intensity scale | 0.1–5; default 1 | Intensity sensitivity of the edge-aware backend; disabled in standard mode. |

Verification and export use identical native bands. Fast preview shifts bands and thresholds approximately to its reduced resolution. Noise is estimated from the current input when thresholds require it; after stacking or nonlinear upstream filters this is not a calibrated camera-noise model. Constant inputs are handled explicitly to avoid degenerate normalization.

### 7. RHEF — Radial Histogram Equalizing Filter

Replaces intensity by its rank within radial distributions, then redistributes ranks with lower/upper Upsilon exponents. The reference method is [Gilly & Cranmer (2025)](https://doi.org/10.1007/s11207-025-02578-x).

**Legacy / compatible** uses per-ring average ranks for ties and sunkit-image's mean-rank Upsilon branch convention. **Continuous global** interpolates positive log-intensity quantiles between populated neighboring rings before inversion. This independently implemented variant is inspired by the continuous-statistics work in AEL; nonpositive or insufficiently sampled regions retain their input. See [continuous RHEF notes](docs/rhef-continuous.md).

| Parameter | Range | Effect |
| --- | --- | --- |
| Mode | Legacy / compatible; Continuous global | Chooses independent ring rankings or interpolated radial distributions. |
| Strength | 0–100% | Blends rank-based output, mapped into the input range, with the input. |
| Application Radius | 0–10 R | Inner processing radius; preserves the input inside it. |
| Lower-tail Upsilon | 0.01–5; default 0.35 | Shapes the lower rank tail. Below one compresses it toward mid-gray; one leaves it unchanged; above one expands it. |
| Ring Width | 0.5–10 preview px | Sets radial sampling width; scales to native resolution for verification/export. |
| Upper-tail exponent | 0.01–5; default 0.35 | Shapes the upper tail independently when the linking checkbox is off. |
| Minimum samples per ring | 2–128; default 12 | Continuous mode only: minimum positive sample population for a usable ring. |
| Quantile samples | 17–1025; default 257 | Continuous mode only: number of intensity-distribution nodes used for interpolation. |
| Noise confidence | 0–10; default 0 = off | Attenuates the blend when ring contrast is near an approximate noise estimate; does not modify the ranking core. |
| Use the same exponent for both tails | On by default | Links the upper exponent to Lower-tail Upsilon. |

Constant/tied populations, radial boundaries, sparse support and missing samples are handled explicitly. Noise-confidence estimates are approximate on correlated stacks.

### 8. Tangential Detail

Subtracts a Gaussian blur along angle in polar coordinates, applies optional soft thresholding and adds the signed residual to the original Cartesian base. Angular boundaries are periodic; blur weights use observed support. Only the detail residual is resampled back. The method was independently implemented after studying Laurent Voillot's Eclipse_HDR tangential-detail approach; it replaces USM in the interface. Historical USM APIs remain for compatibility.

| Parameter | Range | Effect |
| --- | --- | --- |
| Strength | 0–100% | Blends signed angular enhancement with the input. |
| Angular Gaussian sigma | 0.1–30 degrees; default 3 | Angular blur width. Its footprint in Cartesian pixels grows with radius. |
| Detail gain | 0–5; default 1 | Multiplies the signed residual before Strength blending. |
| Noise threshold | 0–10 estimated sigma; default 0 | Soft-thresholds detail using a robust adjacent-pixel noise estimate; zero bypasses thresholding. |
| Inner radius | 0–4 R; default 1 R | Starts tangential processing outside this radius. |
| Outer radius | Greater than inner radius; up to 20 R | Sets the outer boundary when Limit outer radius is enabled. |
| Boundary fade | 0–128 preview px; default 8 | Smooths the radial blend at the application boundaries. |
| Limit outer radius | Off by default | When off, processing extends to observed frame edges. |

### 9. ACHF — Adaptive Circular High-pass Filter

Uses a symmetric circular neighborhood with adaptive intensity rejection. Opposite neighbors must both pass the intensity test and belong to the center pixel's lunar/coronal region. Accepted Gaussian spatial weights form the local mean. The filter computes `background × input + gain × (input − local mean)` before Strength blending.

This is an independent implementation of variable-kernel principles in [Druckmüller, Rušin & Minarovjech (2006), §4.2](https://www.astro.sk/caosp/Eedition/FullTexts/vol36no3/pp131-148.pdf), with application-specific acceptance, gain and background settings. It does not reproduce the Corona 3.0 program.

| Parameter | Range | Effect |
| --- | --- | --- |
| Strength | 0–100% | Blends the complete ACHF result with the input. |
| Support Radius | 1–20 preview px | Radius of the adaptive circular neighborhood. Gaussian sigma is one third of the support, subject to the implementation's spatial floor. |
| Contrast Gain | 0–5; default 2 | Amplifies signed high-pass detail. |
| Intensity Threshold | 0–100%; default 10% | Maximum accepted neighbor difference as a percentage of the current input intensity span; opposite neighbors must both pass. |
| Background Retention | 0–100%; default 10% | Fraction of the original base retained at full Strength. Gain zero with background 100% is identity. |

The neighborhood cost grows approximately with pixels × radius², so large native supports can be slow. No clipping is applied to the signed numerical detail. The Photoshop detail layer removes the base component before its separate Overlay encoding.

### 10. Final Stretch and Reveal

Final Stretch changes presentation after the numerical filters and is shared by verification preview and final export. Finite intensities are normalized before the selected curve. **View Original** is a temporary comparison; **Reveal Opacity** is saved in the output.

| Parameter | Range | Effect |
| --- | --- | --- |
| Stretch Algorithm | Asinh / Logarithmic / GHS | Selects the final presentation curve. |
| Asinh Stretch Intensity | 1–100 | Controls `asinh(intensity × x)/asinh(intensity)`. |
| Logarithmic K | 1–1000000 | Controls `log(1 + K × x)/log(1 + K)`, with logarithmic slider steps and K displayed directly. |
| Reveal Opacity | 0–100%; default 100% | Blends separately stretched processed and original inputs; zero shows the original and 100% the processed result. |

#### GHS — Generalized Hyperbolic Stretch

Implements the original scalar forward equations developed by **David Payne and Mike Cranfield**, using the logarithmic, integral, exponential and hyperbolic branches, symmetry around SP and tangent extensions beyond LP/HP. See the [official equations](https://www.ghsastro.co.uk/doc/tools/GeneralizedHyperbolicStretch/GeneralizedHyperbolicStretch.html) and [implementation/validation notes](docs/ghs-reference-20261019.md).

| Parameter | Range / default | Effect |
| --- | --- | --- |
| Stretch Factor ln(D+1) | 0–20; default 2; step 0.001 | Original GHS control. The mathematical D is `exp(factor) − 1`; zero is identity. |
| Symmetry Point (SP) | 0–1; default 0.05; step 0.0005 | Intensity around which contrast is concentrated. The picker samples normalized processed intensity before presentation stretching. |
| Local Intensity (b) | −5–15; default 0; step 0.01 | Negative values distribute contrast more broadly; positive values concentrate it around SP. −1 is logarithmic, 0 exponential and 1 harmonic. |
| Protect Shadows (LP) | 0–SP; default 0; step 0.0005 | Below LP, follows the tangent at LP, preserving shadow contrast without clipping. |
| Protect Highlights (HP) | SP–1; default 1; step 0.0005 | Above HP, follows the tangent at HP, preserving highlight contrast. |
| Post-stretch Black Point | −1 to below WP; default 0; step 0.001 | Optional separate linear adjustment after GHS. Values below BP are clipped. It is not constrained by SP. |
| Post-stretch White Point | Above BP to 2; default 1; step 0.001 | Upper endpoint of the separate linear adjustment; values above WP are clipped. BP=0/WP=1 leaves GHS unchanged. |

GHS uses float64 intermediate calculations and stable logarithm/exponential evaluations. Its scalar curve follows the published method; the application retains its own luminance/color composition and does not reproduce all PixInsight module modes or the inverse transformation. Settings from the former Asinh-based approximation do not produce the same image with the corrected curve.

### Color defaults after final stretch

**Input: linear**, **Calibrate color** for RGB and **Full-resolution verification preview** are selected by default when a new image is loaded. The input selector can be changed for already stretched data, and neutralization can be disabled to retain source color. See [color processing](#color-and-optional-tse-tools-neutralization) for the P1/P99 method, assumptions and export behavior.

Start with a few active filters and moderate Strength, check geometry, and inspect limb transitions, fine structure and noise at native resolution. Numerical tests and preview/export agreement establish implementation consistency, not photometric calibration or freedom from every possible artifact. See the [control and validation report](docs/filter-controls-20261019.md) for additional implementation details.

## Troubleshooting and verification

- **Missing module:** activate the intended environment and install `requirements.txt` with that environment's Python. Run `python main.py` from the project directory.
- **Dependency installation failure:** inspect the package named in the error and whether its declared version has a compatible distribution for your Python and platform. The declared minimum versions are not a record of a verified installation matrix.
- **Qt startup error on Linux:** inspect the Qt platform-plugin error and install the libraries required by that platform plugin. An offscreen platform does not provide an interactive desktop window.
- **Image loading failure:** inspect terminal output, check the image with its source application, and confirm the appropriate decoder is installed.
- **Slow processing:** disable Auto Calculate while changing settings, reduce Fourier order or wavelet scales, and enable only necessary filters. Full-resolution export takes longer than preview processing.
- **Unexpected radial artifacts:** verify disk center/radius and review radial binning, angular resolution and filter strength.

Before publishing a release, manually check startup, supported input formats, automatic and manual geometry, filter toggles, refresh, original comparison, display stretch, full-resolution export and window closure. Inspect both output files, including dimensions and TIFF bit depth. Run the filter synthetic checks with `python -m unittest discover -s tests -v`. They cover constant-background attenuation, edge isolation, kernel symmetry and frequency response, rotational consistency, bypass and invalid input. Visual validation on real eclipse images remains necessary.

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
