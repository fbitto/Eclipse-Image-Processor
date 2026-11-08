"""Optional gain-only neutralization derived from tse-tools and display-only RGB/mono composition.

neutralize_tse and set_luminosity work per pixel; they run in fixed row strips
on helper threads. Global maxima are reduced over the strips, which does
not depend on order, so the results are identical bit for bit to one thread.
"""
import numpy as np
from .cancellation import check_cancelled
from .parallelism import map_in_threads
from .presentation import normalized_base, row_strips


def neutralize_tse(rgb, white=1.):
    """Gain-only display neutralization using sampled P99-P1 channel spans.

    Derived from tse-tools color_calibrate, revision
    14ae3f7d823d0ac66688a32bf27d0c4b9b8a0391 (MIT), with NaN exclusion.
    Unlike that recipe, do not subtract channel backgrounds or add a pedestal:
    additive offsets can turn intensity gradients into chromatic gradients.
    A single global highlight scale preserves positive channel ratios.
    white=None uses a shared HDR working scale, not measured sensor saturation.
    This assumes neutral sky/corona statistics; it is not ICC calibration.
    """
    source = np.asarray(rgb)
    if source.ndim != 3 or source.shape[-1] != 3:
        raise ValueError('Colour calibration needs an RGB image')
    strips = row_strips(source.shape[0])
    def block(bounds):
        a = np.asarray(source[bounds[0]:bounds[1]], dtype=float)
        return a, np.isfinite(a).all(axis=-1)
    def observed_maximum(bounds):
        check_cancelled()
        a, valid = block(bounds)
        return bool(valid.any()), float(np.max(a, where=valid[..., None], initial=-np.inf))
    automatic = white is None
    if automatic:
        found = map_in_threads(observed_maximum, strips)
        if not any(any_valid for any_valid, _ in found):
            raise ValueError('Colour calibration needs finite RGB observations')
        # One common scale preserves channel ratios and arbitrary input units.
        maximum = max(value for _, value in found)
        white = maximum * (1 + 1e-6)
    if not np.isfinite(white) or white <= 0:
        raise ValueError('Colour calibration needs a positive input white or positive HDR observations')
    small = np.asarray(source[::10, ::10], dtype=float)/white
    selected = small[np.isfinite(small).all(axis=-1) & (small > 0).all(axis=-1) & (small < 1).all(axis=-1)]
    if len(selected) < 2:
        raise ValueError('Not enough sampled RGB pixels strictly between 0 and 1 for calibration')
    background, foreground = np.percentile(selected, [1, 99], axis=0)
    span = foreground-background
    if np.any(span <= np.finfo(float).eps):
        raise ValueError('Colour calibration needs nonconstant sampled channels')
    ratios = span/span[1]
    ratios /= ratios.max()
    gains=1/ratios
    def gained(bounds):
        a, valid = block(bounds)
        return np.maximum(a/white, 0)*gains, valid
    def gained_maximum(bounds):
        check_cancelled()
        corrected, valid = gained(bounds)
        return float(np.max(corrected, where=valid[..., None], initial=-np.inf))
    # One common factor avoids independent channel clipping in bright pixels.
    highlight_scale=max(max(map_in_threads(gained_maximum, strips)),1.)
    corrected=np.empty(source.shape, np.float32)
    def write(bounds):
        check_cancelled()
        values, valid = gained(bounds)
        corrected[bounds[0]:bounds[1]] = np.where(valid[..., None], values/highlight_scale, np.nan)
    map_in_threads(write, strips)
    report = dict(method='gain-only P1/P99-span neutralization', reference_revision='14ae3f7d823d0ac66688a32bf27d0c4b9b8a0391',
                  white=float(white), white_source=('shared observed maximum with headroom' if automatic else 'declared input white'),
                  sample_p1=background.tolist(), sample_p99=foreground.tolist(),
                  ratios=ratios.tolist(), gains=gains.tolist(), highlight_scale=highlight_scale,
                  background_subtracted=False, sampled_pixels=len(selected), stride=10,
                  assumption='Declared linear input; neutral channel spans; not photometric/ICC calibration')
    return corrected, report


def colour_layer(rgb, source, display):
    """Match the normalized base luminance with an equal factor on R/G/B.

    Negative values are clipped for display only. A shared highlight factor keeps
    channels in gamut. Numerical source and optional balanced float remain separate.
    """
    a = np.asarray(rgb, dtype=float)
    if a.shape != (*source.shape, 3):
        raise ValueError('RGB and luminance must share a canvas')
    valid = np.isfinite(source) & np.isfinite(a).all(axis=-1)
    a = np.where(valid[..., None], np.maximum(a, 0), 0)
    luminance = a @ np.array([.299, .587, .114])
    target = normalized_base(source, display)
    factor = np.divide(target, luminance, out=np.zeros_like(target), where=luminance > 0)
    a *= factor[..., None]
    a /= np.maximum(a.max(axis=-1), 1)[..., None]
    return a


def set_luminosity(colour, luminance):
    """Nonseparable Color blend over mono, using SetLum/ClipColor equations.

    Legacy display-number coefficients (.30,.59,.11); native Photoshop colour
    management can differ, so its rendering still needs verification.
    Fixed row strips run on helper threads; every operation is per pixel.
    """
    colour = np.asarray(colour)
    luminance = np.asarray(luminance)
    if colour.ndim != 3 or luminance.shape != colour.shape[:2]:
        return _set_luminosity(colour, luminance)
    result = np.empty(colour.shape, np.float64)
    def strip(bounds):
        check_cancelled()
        result[bounds[0]:bounds[1]] = _set_luminosity(colour[bounds[0]:bounds[1]], luminance[bounds[0]:bounds[1]])
    map_in_threads(strip, row_strips(colour.shape[0]))
    return result


def _set_luminosity(colour, luminance):
    c = np.asarray(colour, dtype=float)
    weights = np.array([.30, .59, .11])
    c = c + (luminance-c@weights)[..., None]
    low, high = c.min(axis=-1), c.max(axis=-1)
    low_factor = np.divide(luminance, luminance-low, out=np.ones_like(luminance), where=luminance != low)
    c = np.where((low < 0)[..., None], luminance[..., None]+(c-luminance[..., None])*low_factor[..., None], c)
    high_factor = np.divide(1-luminance, high-luminance, out=np.ones_like(luminance), where=high != luminance)
    c = np.where((high > 1)[..., None], luminance[..., None]+(c-luminance[..., None])*high_factor[..., None], c)
    return np.clip(c, 0, 1)


def warm_colour(rgb, amount=0., *, sky_rgb=None):
    """Artistic RGB gains, 0 = unchanged, 1 = sunset; preserve missing pixels.

    Optional sky_rgb is a finite nonnegative (3,) background estimate in the
    same linear units and colour space as rgb (..., 3). Warm only positive
    channel excess above that level; retain the background and lower values.
    Ease in over 10% of the largest sky channel, with continuous slope and
    monotonic channel output so faint gradients cannot acquire a threshold edge.
    No normalization or clipping is applied. None retains legacy global gains.
    """
    if not np.isfinite(amount) or not 0 <= amount <= 1:
        raise ValueError('Warmth must be between 0 and 1')
    if amount == 0:
        return rgb
    gains = np.array([1., 1.-.45*amount, 1.-.95*amount])
    if sky_rgb is None:
        return np.asarray(rgb) * gains
    sky = np.asarray(sky_rgb, dtype=float)
    if sky.shape != (3,) or not np.isfinite(sky).all() or np.any(sky < 0):
        raise ValueError('Sky colour must contain three finite nonnegative channel levels')
    a = np.asarray(rgb)
    if a.ndim < 1 or a.shape[-1] != 3:
        raise ValueError('Warmth sky protection needs RGB pixels')
    width = .1*float(sky.max())
    def adjust(values):
        check_cancelled()
        signal = np.maximum(values-sky, 0)
        if width > 0:
            # Integrate a slope rising from zero to one; never reverse a gradient.
            fraction = np.minimum(signal/width, 1.)
            signal *= .5*fraction
            signal += np.maximum(values-sky-width, 0)*.5
        return values + signal*(gains-1)
    if a.ndim != 3:
        return adjust(a)
    result = np.empty(a.shape, np.float64)
    # Bound scratch memory while processing full-resolution RGB masters.
    for first, last in row_strips(a.shape[0]):
        result[first:last] = adjust(a[first:last])
    return result
