"""Optional tse-tools neutralization and display-only RGB/mono composition."""
import numpy as np
from .presentation import stretch_image


def neutralize_tse(rgb, white=1.):
    """tse-tools color_calibrate recipe, adapted to explicitly exclude NaN.

    Reference: naavis/eclipsetools, commands/utils.py, revision
    14ae3f7d823d0ac66688a32bf27d0c4b9b8a0391 (MIT).
    Stride 10, joint (0,1) selection, P1/P99, green-reference ratios,
    shared negative shift and clipping match the reference for normalized data.
    This neutralizes assumed sky/corona colour; it is not an ICC calibration.
    """
    a = np.asarray(rgb, dtype=float)
    if a.ndim != 3 or a.shape[-1] != 3 or not np.isfinite(white) or white <= 0:
        raise ValueError('Colour calibration needs RGB and a positive input white')
    a = a/white
    valid = np.isfinite(a).all(axis=-1)
    small = a[::10, ::10]
    selected = small[np.isfinite(small).all(axis=-1) & (small > 0).all(axis=-1) & (small < 1).all(axis=-1)]
    if len(selected) < 2:
        raise ValueError('Not enough sampled RGB pixels strictly between 0 and 1 for calibration')
    background, foreground = np.percentile(selected, [1, 99], axis=0)
    span = foreground-background
    if np.any(span <= np.finfo(float).eps):
        raise ValueError('Colour calibration needs nonconstant sampled channels')
    ratios = span/span[1]
    ratios /= ratios.max()
    corrected = (a-background)/ratios
    minimum = min(float(corrected[valid].min()), 0.)
    corrected = np.where(valid[..., None], np.clip((corrected-minimum)/(1-minimum), 0, 1), np.nan)
    report = dict(method='tse-tools P1/P99 neutralization', reference_revision='14ae3f7d823d0ac66688a32bf27d0c4b9b8a0391',
                  white=float(white), background=background.tolist(), foreground=foreground.tolist(),
                  ratios=ratios.tolist(), negative_shift=minimum, sampled_pixels=len(selected), stride=10,
                  assumption='Declared linear input; neutral background and corona; not photometric/ICC calibration')
    return corrected.astype(np.float32), report


def colour_layer(rgb, source, display):
    """One luminance-guided stretch, equal factor on R/G/B; no channel stretch.

    Negative values are clipped for display only. A shared highlight factor keeps
    channels in gamut. Numerical source and optional balanced float remain separate.
    """
    a = np.asarray(rgb, dtype=float)
    if a.shape != (*source.shape, 3):
        raise ValueError('RGB and luminance must share a canvas')
    valid = np.isfinite(source) & np.isfinite(a).all(axis=-1)
    a = np.where(valid[..., None], np.maximum(a, 0), 0)
    luminance = a @ np.array([.299, .587, .114])
    target = stretch_image(source, display)
    factor = np.divide(target, luminance, out=np.zeros_like(target), where=luminance > 0)
    a *= factor[..., None]
    a /= np.maximum(a.max(axis=-1), 1)[..., None]
    return a


def set_luminosity(colour, luminance):
    """Nonseparable Color blend over mono, using SetLum/ClipColor equations.

    Legacy display-number coefficients (.30,.59,.11); native Photoshop colour
    management can differ, so its rendering still needs verification.
    """
    c = np.asarray(colour, dtype=float)
    weights = np.array([.30, .59, .11])
    c = c + (luminance-c@weights)[..., None]
    low, high = c.min(axis=-1), c.max(axis=-1)
    low_factor = np.divide(luminance, luminance-low, out=np.ones_like(luminance), where=luminance != low)
    c = np.where((low < 0)[..., None], luminance[..., None]+(c-luminance[..., None])*low_factor[..., None], c)
    high_factor = np.divide(1-luminance, high-luminance, out=np.ones_like(luminance), where=high != luminance)
    c = np.where((high > 1)[..., None], luminance[..., None]+(c-luminance[..., None])*high_factor[..., None], c)
    return np.clip(c, 0, 1)
