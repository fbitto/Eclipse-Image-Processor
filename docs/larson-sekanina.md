# Classic Larson–Sekanina

The SHARPENING group places Larson–Sekanina between Tangential Detail and ACHF.
It is initially disabled; defaults are Strength 10%, radial increment 0 preview
pixels and angular increment 1 degree. The existing disk center/radius are used.

The numerical operator is

    D(r, theta) = 2 I(r, theta)
                  - I(r-dr, theta-da) - I(r-dr, theta+da)

Both angular samples use the same inward radial offset. The pipeline returns
`I + Strength/100 * D` in input units, without clipping, normalization, threshold,
deringing or dynamic-range extension. The sampling is bilinear, directly on the
Cartesian source, in cancellable row tiles. Both increments zero are identity.
The radial increment scales with preview/export resolution; the angle does not.
Only targets outside the reference lunar disk whose two interpolation footprints
are fully observed and outside the disk receive detail. Other targets retain
input. Explicit missing data remain missing. Statistical exclusions also restrict
sampling when enabled. These support rules protect data boundaries; they do not
alter the classic operator on supported pixels.

Reference formula: Vincent, *From observations and measurements to realistic
modeling of cometary nuclei*, section 2.2.2.1:
https://www2.mps.mpg.de/solar-system-school/alumni/vincent.pdf

## Photoshop

The independent layer branch computes the float64 residual from PREPARED, with
no preceding enhancement branch. It encodes `L = 0.5 + D/(2*S)`, where S is the
larger of the observed prepared-input range and maximum absolute exported
residual. This preserves zero and relative residual amplitudes; no median shift
or tanh is applied. The scale is recorded in recipe.json. TIFF is uint16 RGB
with unassociated alpha, as for the existing detail layers.

Use **Linear Light / Luz lineal**, with Fill at 100%. In display numeric values,
its full-strength blend is `clip(base + 2*L - 1, 0, 1)`, thus adding `D/S` before
clipping. Layer opacity and alpha mix that result with the base. Overlay instead
weights the effect by base brightness and does not perform this signed addition.
The JSX loader sets BlendMode.LINEARLIGHT; PS_COMBINED uses the same equation on
the quantized TIFF samples. Recommended opacity retains the package convention:
`min(Strength/100, 0.35) * Reveal`, quantized to 1/255.

Adobe's mode description:
https://helpx.adobe.com/photoshop/desktop/repair-retouch/adjust-light-tone/blending-mode-descriptions.html

The Photoshop stack is a display composition over a stretched base, not an exact
reproduction of the sequential numerical pipeline. Neutral 0.5 is quantized to
32768/65535 in TIFF, with the existing small neutral-gray rounding error. Native
Photoshop rendering/color management still needs manual verification. Small
angles, incorrect centers and bright structures can produce misleading residuals.
