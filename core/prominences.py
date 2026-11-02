"""Display-only prominence layer from the unprepared original RGB, in input units."""
import numpy as np
from scipy.ndimage import distance_transform_edt, maximum_filter
from .cancellation import check_cancelled


def _smooth(value):
    t = np.clip(value, 0., 1.)
    return t*t*(3.-2.*t)


def _red_excess(rgb):
    # Discount yellow/orange continuum as well as neutral/blue light.
    red, green, blue = (rgb[..., c] for c in range(3))
    return red-np.maximum(green, blue)-np.maximum(green-blue, 0.)


def prominence_settings(rgb, geometry, exposure_ev=-2., saturation=1., contrast=1., edge_softness=3.):
    """Native reference shared by preview/export; no corona filters or colour gains.

    The red-excess selection is a presentation heuristic, not an H-alpha measurement.
    EV is relative to P99.5 peak RGB in red candidates near the measured lunar limb.
    """
    a = np.asarray(rgb)
    if a.ndim != 3 or a.shape[-1] != 3 or not a.size:
        raise ValueError('Prominences require the original RGB image')
    cx, cy, radius = (float(geometry[k]) for k in ('sx', 'sy', 'sr'))
    if not np.isfinite([cx, cy, radius, exposure_ev]).all() or radius <= 0 or not -3 <= exposure_ev <= 5:
        raise ValueError('Prominences need finite geometry, positive radius and exposure from -3 to +5 EV')
    if not np.isfinite(saturation) or not 0 <= saturation <= 1:
        raise ValueError('Prominence saturation must be between 0 and 1')
    if not np.isfinite(contrast) or not .5 <= contrast <= 2.:
        raise ValueError('Prominence contrast must be between 0.5 and 2.0')
    if not np.isfinite(edge_softness) or not 0 <= edge_softness <= 20:
        raise ValueError('Prominence edge softness must be between 0 and 20 native pixels')
    stride = max(1, int(np.ceil(max(a.shape[:2])/2048)))
    sample = np.asarray(a[::stride, ::stride], dtype=np.float64)
    y, x = np.ogrid[:sample.shape[0], :sample.shape[1]]
    r = np.hypot(x*stride-cx, y*stride-cy)/radius
    peak = np.max(sample, axis=-1)
    red = _red_excess(sample)
    good = np.isfinite(sample).all(axis=-1) & (peak > 0) & (r >= .9) & (r < 1.5)
    candidates = good & (red > .05*peak)
    values = peak[candidates] if candidates.any() else peak[good]
    reference = float(np.percentile(values, 99.5)) if values.size else 1.
    return dict(reference=reference, exposure_ev=float(exposure_ev), saturation=float(saturation), contrast=float(contrast),
                source='original loaded RGB; no background extraction, filters or colour neutralization',
                method='linear exposure then shared soft shoulder; inward red-mask edge blend; no lunar-disk exclusion',
                highlight_curve='peak**contrast / (1 + peak**contrast), common RGB gain after exposure and saturation',
                mask_edge_width_native_px=float(edge_softness),
                red_excess='R-max(G,B)-max(G-B,0)',
                red_fraction_range=[.05, .25], intensity_range=[.005, .03],
                outer_radii=[1.3, 1.5], review_required=True)


def prominence_layer(rgb, geometry, settings):
    """Return unmasked RGB16 and mask16 on the same canvas; never modify source.

    Mask is independent of EV/contrast. Contrast 1 retains the original soft curve.
    No geometric lunar-disk exclusion is applied.
    Negative/missing samples cannot contribute. Saturation is a display adjustment; the selection uses original RGB.
    """
    a = np.asarray(rgb)
    if a.ndim != 3 or a.shape[-1] != 3 or not a.size:
        raise ValueError('Prominences require the original RGB image')
    cx, cy, radius = (float(geometry[k]) for k in ('sx', 'sy', 'sr'))
    reference, ev = float(settings['reference']), float(settings['exposure_ev'])
    if not np.isfinite([cx, cy, radius, reference, ev]).all() or min(radius, reference) <= 0 or not -3 <= ev <= 5:
        raise ValueError('Invalid prominence geometry, reference scale or exposure')
    saturation = settings.get('saturation', 1.)
    if not np.isfinite(saturation) or not 0 <= saturation <= 1:
        raise ValueError('Prominence saturation must be between 0 and 1')
    contrast = float(settings.get('contrast', 1.))
    if not np.isfinite(contrast) or not .5 <= contrast <= 2.:
        raise ValueError('Prominence contrast must be between 0.5 and 2.0')
    edge_softness = float(settings.get('mask_edge_width_native_px', 3.))
    if not np.isfinite(edge_softness) or not 0 <= edge_softness <= 20:
        raise ValueError('Prominence edge softness must be between 0 and 20 native pixels')
    image = np.empty(a.shape, np.uint16)
    mask = np.empty(a.shape[:2], np.uint16)
    x = np.arange(a.shape[1], dtype=float)[None, :]-cx
    for first in range(0, a.shape[0], 128):
        check_cancelled()
        block = np.asarray(a[first:first+128], dtype=np.float64)
        valid = np.isfinite(block).all(axis=-1)
        block = np.where(valid[..., None], np.maximum(block, 0.), 0.)
        peak = np.max(block, axis=-1)
        red = _red_excess(block)
        fraction = np.divide(red, peak, out=np.zeros_like(peak), where=peak > 0)
        y = np.arange(first, first+len(block), dtype=float)[:, None]-cy
        r = np.hypot(x, y)
        # shortcut: exclude beyond 1.5 lunar radii; widen only if real prominences require it.
        coverage = 1.-_smooth((r/radius-1.3)/.2)
        coverage *= _smooth((fraction-.05)/.20)*_smooth((peak/reference-.005)/.025)*valid
        mask[first:first+len(block)] = np.rint(coverage*65535).astype(np.uint16)
        exposed = block/reference*2.**ev
        luminance = exposed @ np.array([.299, .587, .114])
        exposed = luminance[..., None] + saturation*(exposed-luminance[..., None])
        peak_exposed = np.max(exposed, axis=-1)
        if contrast == 1.:
            exposed /= (1. + peak_exposed)[..., None]
        else:
            power = peak_exposed**contrast
            mapped = power/(1.+power)
            factor = np.divide(mapped,peak_exposed,out=np.zeros_like(peak_exposed),where=peak_exposed>0)
            exposed *= factor[..., None]
        image[first:first+len(block)] = np.rint(np.clip(exposed, 0., 1.)*65535).astype(np.uint16)
    # Work only near the existing selection; no image blur or expansion of mask support.
    y0, y1 = max(0,int(np.floor(cy-1.5*radius))-1), min(a.shape[0],int(np.ceil(cy+1.5*radius))+2)
    x0, x1 = max(0,int(np.floor(cx-1.5*radius))-1), min(a.shape[1],int(np.ceil(cx+1.5*radius))+2)
    if y1 > y0 and x1 > x0:
        mask[y0:y1,x0:x1] = _soften_mask(mask[y0:y1,x0:x1], edge_softness)
    return image, mask


def _soften_mask(mask, edge_softness=3.):
    """Inward native-pixel blend; retain ridges of thin chromosphere features."""
    if edge_softness == 0 or not mask.any():
        return mask
    check_cancelled()
    distance = distance_transform_edt(np.pad(mask > 0, 1))[1:-1,1:-1]
    # Limit feather width by local thickness so isolated one-pixel detail stays visible.
    width = np.minimum(edge_softness, maximum_filter(distance, size=7, mode='constant'))
    coverage = _smooth((distance-.5)/np.maximum(width-.5,.5))
    check_cancelled()
    return np.rint(mask*coverage).astype(np.uint16)


def composite_prominences(base, rgb16, mask16):
    """Normal blend in display numbers, with exactly the exported 16-bit mask."""
    base = np.asarray(base)
    if base.ndim == 2:
        base = np.repeat(base[..., None], 3, axis=-1)
    if base.shape != rgb16.shape or mask16.shape != base.shape[:2]:
        raise ValueError('Prominence layer and composition must share a canvas')
    alpha = mask16.astype(np.float32)[..., None]/65535.
    return base*(1.-alpha)+(rgb16.astype(np.float32)/65535.)*alpha
