"""Sky-sampled warmth on the enhanced presentation, independent of linear RGB colour."""
import numpy as np
from scipy.ndimage import gaussian_filter

from .background import sample_allowed, sample_grid
from .cancellation import check_cancelled
from .colour import set_luminosity, warm_colour
from .presentation import quantize_u16, row_strips


def warmth_layer(rgb, amount=0., background=None, *, native_shape=None, valid=None):
    """Return RGB16 tint and alpha16, or None when disabled/sky is unsupported.

    rgb is the enhanced display RGB in [0,1]. Sample positions/exclusion geometry
    are native pixels; native_shape maps them to a reduced preview. Fit a robust
    sky plane to smoothed display luminance and measure its residual noise in
    the sky patches. Coverage rises from 2.5 to 6 noise sigmas above that plane;
    features whiter than the sampled sky can enter at 1.5 to 3 sigmas. Colour
    is supporting evidence, never a required gate. There is no radial cutoff.
    """
    if not np.isfinite(amount) or not 0 <= amount <= 1:
        raise ValueError('Warmth must be between 0 and 1')
    if amount == 0 or background is None:
        return None
    model = _sky_model(rgb, background, native_shape=native_shape, valid=valid)
    return None if model is None else _corona_layer(np.asarray(rgb), amount, model)


def _sky_model(rgb, background, *, native_shape=None, valid=None):
    """Supported sky plane and strength-independent corona coverage, or None."""
    a = np.asarray(rgb)
    if a.ndim != 3 or a.shape[-1] != 3 or not a.size:
        raise ValueError('Presentation warmth needs RGB pixels')
    h,w = a.shape[:2]
    native_shape = a.shape[:2] if native_shape is None else native_shape
    if len(native_shape) != 2 or not np.isfinite(native_shape).all() or min(native_shape) <= 0:
        raise ValueError('Warmth needs positive native canvas dimensions')
    scale = np.array([w/native_shape[1], h/native_shape[0]])
    geometry = background['geometry']
    radius = background['radius']
    if (np.shape(geometry) != (3,) or not np.isfinite(geometry).all() or geometry[2] <= 0
            or not np.isfinite(radius) or radius < 1):
        raise ValueError('Warmth needs finite geometry and an exclusion radius of at least one disk radius')
    points = background.get('points')
    if points is None:
        points = sample_grid(native_shape, geometry, radius, background['grid'])
    observed = np.isfinite(a).all(axis=-1)
    if valid is not None:
        if np.shape(valid) != (h,w):
            raise ValueError('Warmth validity must match the display canvas')
        observed &= valid
    luminance = np.zeros((h,w), np.float32)
    white_distance = np.zeros((h,w), np.float32)
    for first,last in row_strips(h):
        check_cancelled()
        luminance[first:last] = np.where(observed[first:last], a[first:last] @ [.30,.59,.11], 0.)
        block = a[first:last]
        total = block.sum(axis=-1)
        distance = np.divide(np.ptp(block,axis=-1),total,out=np.zeros_like(total),where=total>0)
        white_distance[first:last] = np.where(observed[first:last],distance,0.)
    sigma = max(.5, .015*geometry[2]*float(np.sqrt(np.prod(scale))))
    support = gaussian_filter(observed.astype(np.float32), sigma)
    smooth = gaussian_filter(luminance, sigma)
    np.divide(smooth, support, out=smooth, where=support>0)
    white_distance = gaussian_filter(white_distance,sigma)
    np.divide(white_distance,support,out=white_distance,where=support>0)
    # A kernel touching the missing Moon must not exclude the observed inner limb.
    good = observed & (support > 0)
    half = max(1, round(max(2,min(32,int(min(native_shape)/200)))*float(scale.min())))
    patches, centres, values, colours = [], [], [], []
    for point in points:
        if not sample_allowed(point, native_shape, geometry, radius):
            continue
        x,y = np.rint((np.asarray(point)+.5)*scale-.5).astype(int)
        if not (half <= x < w-half and half <= y < h-half):
            continue
        region = (slice(y-half,y+half+1), slice(x-half,x+half+1))
        mask = good[region]
        if mask.sum() < .9*mask.size:
            continue
        patches.append(region)
        centres.append([1., (x+.5)/w*2-1, (y+.5)/h*2-1])
        values.append(float(np.median(smooth[region][mask])))
        colours.append(float(np.median(white_distance[region][mask])))
    if len(values) < 6:
        return None
    design = np.asarray(centres)
    values = np.asarray(values)
    keep = np.ones(len(values), bool)
    for _ in range(5):
        check_cancelled()
        if keep.sum() < 6 or np.linalg.matrix_rank(design[keep]) < 3:
            return None
        coefficients = np.linalg.lstsq(design[keep], values[keep], rcond=None)[0]
        residual = values-design@coefficients
        centre = np.median(residual[keep])
        noise = max(1/65535, 1.4826*float(np.median(abs(residual[keep]-centre))))
        updated = abs(residual-centre) <= 3*noise
        if np.array_equal(updated,keep):
            break
        keep = updated
    if (keep.sum() < 6 or np.linalg.matrix_rank(design[keep]) < 3
            or np.any(np.ptp(design[keep,1:],axis=0) < .4)):
        return None
    coefficients = np.linalg.lstsq(design[keep],values[keep],rcond=None)[0]
    xs = (np.arange(w)+.5)/w*2-1
    ys = (np.arange(h)+.5)/h*2-1
    sky = coefficients[0] + coefficients[1]*xs[None,:] + coefficients[2]*ys[:,None]
    excess = smooth-sky
    sampled = np.concatenate([excess[region][good[region]] for region,k in zip(patches,keep) if k])
    noise = max(noise, 1.4826*float(np.median(abs(sampled-np.median(sampled)))))
    sky_colour = float(np.median(np.asarray(colours)[keep]))
    # Neutral sky offers no colour discrimination; contrast alone must then suffice.
    white_cue = np.clip(1.-white_distance/sky_colour,0.,1.) if sky_colour > .02 else 0.
    low = (2.5-white_cue)*noise
    high = (6.-3.*white_cue)*noise
    coverage = np.clip((excess-low)/(high-low),0.,1.)
    coverage *= coverage*(3.-2.*coverage)
    feather = max(1.5,sigma)
    coverage = gaussian_filter(np.where(good,coverage,0.),feather)
    feather_support = gaussian_filter(good.astype(np.float32),feather)
    np.divide(coverage,feather_support,out=coverage,where=feather_support>0)
    return a, good, luminance, sky, coverage


def _corona_layer(a, amount, model):
    original, good, luminance, sky, coverage = model
    if a is not original:
        luminance = np.where(good, a @ [.30,.59,.11], 0.).astype(np.float32)
    h = a.shape[0]
    alpha = quantize_u16(np.where(good, coverage*amount, 0.))
    if not alpha.any():
        return None
    # Tint enhanced excess, retaining the sky's contribution to each RGB pixel.
    target = np.empty(a.shape, np.uint16)
    for first,last in row_strips(h):
        check_cancelled()
        lum = luminance[first:last]
        signal = np.maximum(lum-sky[first:last],0.)
        tint = warm_colour(np.repeat(signal[...,None],3,axis=-1),1.)
        tint = set_luminosity(tint,signal)
        colour = a[first:last] + tint-signal[...,None]
        target[first:last] = quantize_u16(set_luminosity(colour,lum))
    return target, alpha


def blend_warmth(rgb, layer):
    """Normal composite using exactly the RGB16 and alpha16 exported as a layer."""
    if layer is None:
        return rgb
    target,mask = layer
    result = np.empty(np.shape(rgb), np.float64)
    for first,last in row_strips(result.shape[0]):
        check_cancelled()
        alpha = mask[first:last,:,None].astype(float)/65535.
        result[first:last] = rgb[first:last]*(1.-alpha) + target[first:last].astype(float)/65535.*alpha
    return result


def colour_layers(rgb, general_warmth=0., warmth=0., reduce_green_sky=False,
                  background=None, *, native_shape=None, valid=None, green_reduction=.75):
    """Ordered RGB16/alpha16 display layers; masks come from the untinted input.

    General warmth establishes the whole-image baseline; corona warmth adds
    enhanced coronal excess. A configurable fraction of green excess above mean(R,B) is
    suppressed only in supported sky. Original prominences are composed later.
    """
    for amount in (general_warmth, warmth):
        if not np.isfinite(amount) or not 0 <= amount <= 1:
            raise ValueError('Warmth must be between 0 and 1')
    if not np.isfinite(green_reduction) or not 0 <= green_reduction <= 1:
        raise ValueError('Green reduction must be between 0 and 1')
    if not general_warmth and not warmth and not reduce_green_sky:
        return []
    a = np.asarray(rgb)
    if a.ndim != 3 or a.shape[-1] != 3 or not a.size:
        raise ValueError('Presentation colour needs RGB pixels')
    observed = np.isfinite(a).all(axis=-1)
    if valid is not None:
        if np.shape(valid) != a.shape[:2]:
            raise ValueError('Colour validity must match the display canvas')
        observed &= valid
    if native_shape is not None and (len(native_shape) != 2 or not np.isfinite(native_shape).all() or min(native_shape) <= 0):
        raise ValueError('Colour needs positive native canvas dimensions')
    model = (_sky_model(a, background, native_shape=native_shape, valid=observed)
             if background is not None and (warmth or reduce_green_sky) else None)
    layers = []
    if general_warmth:
        target = np.empty(a.shape, np.uint16)
        for first,last in row_strips(a.shape[0]):
            check_cancelled()
            block = a[first:last]
            target[first:last] = quantize_u16(set_luminosity(warm_colour(block,1.), block @ [.30,.59,.11]))
        layer = target, quantize_u16(observed*general_warmth)
        layers.append(('general_warmth', layer))
        a = blend_warmth(a, layer)
    if model is not None and warmth:
        layer = _corona_layer(a, warmth, model)
        if layer is not None:
            layers.append(('warmth', layer))
            a = blend_warmth(a, layer)
    if model is not None and reduce_green_sky and green_reduction:
        coverage = np.where(model[1], 1.-model[4], 0.)
        target = np.empty(a.shape, np.uint16)
        changed = False
        for first,last in row_strips(a.shape[0]):
            check_cancelled()
            block = a[first:last]
            excess = np.maximum(block[...,1]-(block[...,0]+block[...,2])/2, 0.)
            changed |= bool(np.any((excess>0) & (coverage[first:last]>0)))
            corrected = block.copy()
            corrected[...,1] -= green_reduction*excess
            target[first:last] = quantize_u16(set_luminosity(corrected, block @ [.30,.59,.11]))
        if changed:
            layers.append(('reduce_green_sky', (target, quantize_u16(coverage))))
    return layers
