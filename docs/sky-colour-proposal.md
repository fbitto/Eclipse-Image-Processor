# General warmth and additive corona warmth

Implemented after approval on 7 November 2026. The earlier sky-only warmth interpretation was superseded by general warmth across sky and corona, with extra corona warmth above that baseline.

## Controls and processing

Appearance displays **General warmth**, **Corona warmth**, then **Reduce green sky**. Both warmth sliders are linear, warm-only 0–100 controls, default 0. Green reduction is enabled by a checkbox, default off, with a linear 0–100% strength slider, default 75%. Controls are available at every interface level and disabled for mono input.

Processing order is independent of their visual placement:

1. General warmth establishes the baseline across the whole observed RGB image.
2. Corona warmth adds enhanced coronal excess above that baseline, protecting the sampled sky contribution.
3. Reduce green sky removes the chosen fraction of positive G − (R+B)/2 in supported sky, then restores luminance using the existing colour helper. It is SCNR-inspired, not an implementation of PixInsight SCNR.
4. Existing edge finishing and original prominence composition follow. Original prominence RGB and masks retain separate colour controls.

These are enhanced-presentation colour adjustments after calibration/display composition. They do not alter numerical filters or float working sources. Existing settings with both new controls neutral/off reproduce the historical corona-only results.

## Shared implementation

`core/warmth.py:colour_layers` returns ordered `(name, (RGB16 target, alpha16 mask))` entries for the enabled treatments. The same layers are used in preview and export. All-off returns an empty list and requires no sky model.

The existing sky model and strength-independent corona coverage are extracted into `_sky_model`. Masks are measured from the untinted presentation, so changing general warmth cannot redefine sky and corona. Pure sky with a supported fit remains usable for green reduction. A failed fit disables only the mask-dependent stages; general warmth works without sky samples. Missing and explicitly excluded pixels retain zero adjustment coverage; finite black pixels do not acquire signal.

Do not invert the old `warmth_layer` output alpha: it is multiplied by corona strength and its None return conflates unsupported sky with a valid scene without coronal signal. `warmth_layer` remains available and retains its existing numerical behaviour.

`general_warmth` and `reduce_green_sky` travel in presentation/export snapshots as scalar values. Changes refresh presentation without recalculating numerical filters. The new settings keys are optional `sl_general_warmth` , `chk_reduce_green_sky` and `sl_green_reduction`; legacy recipes restore warmth to 0, green enablement to off and strength to 75% and retain the original `sl_warmth` corona setting. Direct image loads reset the new controls.

Editable PSB and TIFF packages place General warmth, existing Corona warmth, then Reduce green sky above the RGB Color layer and below original prominences. Each treatment has an editable mask; bypassed stages are omitted. Old corona-only packages retain their layer names and metadata.

## Validation

The formerly pending tests now run without skip guards in [tests/test_sky_colour.py](../tests/test_sky_colour.py). They cover:

- Exact zero/off bypass and existing corona-only compatibility.
- General baseline across sky/corona, additive corona response and strength-independent masks.
- Pure sky, unsupported fits, far-out streamers and soft transitions.
- Green correction without warmth; neutral/magenta preservation; no green-to-magenta overshoot.
- All 18 zero/mid/full warmth and checkbox combinations, luminance/bounds, highlights, black pixels, NaNs, explicit exclusions and input immutability.
- Invalid arguments, native-to-reduced sample mapping and cancellation.
- UI defaults/order/levels, RGB enablement, legacy/new settings and direct-load reset.
- Presentation-only edits and immutable Fit/half/native/export scalar snapshots.
- Native preview/package agreement, TIFF/JPEG and PSB verification, unchanged original prominence RGB/masks and export compatibility.

See [the validation record](sky-colour-preparation-validation.md) for executed checks. Individual-operation tolerances are 2–3/65535; a three-stage combination allows 6/65535, and display comparison allows one 8-bit step. Preview-mask resampling tolerance is 0.02 mean absolute error. These are engineering tolerances, not photometric accuracy claims.

A read-only check on the supplied real FITS master also compares baseline, general warmth, general plus corona, and all controls. Preview/image tests do not establish all-platform native UI behaviour or a rebuilt package's compatibility. The existing DMG predates this feature and has not been replaced.

## Prominence preview and tint follow-up

Combined prominence composition no longer depends on PSB preview being enabled.
Explicit mask/on-black selection leaves View Original so the requested prominence
view is rendered. The original RGB and prominence selection algorithm are unchanged.
Warmth gains now use R=1, G=1−0.45a, B=1−0.95a rather than the former yellow-biased
gains; zero warmth remains exact bypass. Saved nonzero warmth amounts now render
with the requested stronger red/orange hue. Green strength is carried through
settings, immutable preview/export snapshots and editable layer metadata.


Validation source confirmed by the user: `/Volumes/Astro/Imágenes/CoronaHDR_RAW/CoronaHDR_Work/.coronahdr-jobs/e1c3c474c41b4163b9c04099bb909948/result/master.fits`. The different master in job `596a8739cfd846ef97b19c8408a73420` is excluded from application design/validation decisions. The selection-balance fallback and its three tests added for that file were removed; the original prominence-selection algorithm is retained. Warmth, adjustable sky green reduction and independently tested preview-visibility fixes remain.

## User visual references

The eclipse was observed at sunset. The supplied corona reference is amber/orange with a near-white bright inner rim; the sky reference is copper/brown with a reddish horizon glow and spatial gradients. Use these as visual guidance, not a universal colour calibration or a reason to modify source pixels. Do not globally neutralize sunset pink or flatten its gradients. The revised warmth gains [1, 1−0.45a, 1−0.95a] retain more green than the earlier rose-prone tint while suppressing blue more strongly. Only the explicitly approved e1c3c474 master is used for data-driven validation.
