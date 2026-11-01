"""Native normalization and the shared AEL-style PSB presentation.

The per-pixel work (Asinh curve and quantization) runs in fixed row strips on
helper threads. Every operation is per pixel and the strips never depend
on the number of threads, so the result is identical bit for bit to one thread.
"""
from collections import OrderedDict
from threading import RLock
import weakref

import numpy as np
from .cancellation import check_cancelled
from .image_data import normalize_observed
from .parallelism import map_in_threads

STRIP_ROWS = 256


def row_strips(height, rows=STRIP_ROWS):
    """Fixed strips (multiples of 128 rows), independent of the thread count."""
    return [(first, min(height, first+rows)) for first in range(0, height, rows)]


def normalized_base(image, settings):
    """Linearly normalize with native working levels shared by both resolutions."""
    return normalize_observed(image, settings.get('normalization_range'))


def composition_settings(settings):
    """Only native normalization and transient comparison affect the working base."""
    return dict(blend=settings.get('blend', 1.),
                **({'normalization_range': settings['normalization_range']}
                   if 'normalization_range' in settings else {}))


def psb_presentation_settings(source, valid=None, *, rgb=None, params=None, exposure_ev=0.):
    """Our automatic scale heuristic; AEL supplies the curve, not automatic exposure.

    P99.5 of positive sampled luminance outside 1.2 lunar radii resists isolated
    bright pixels. Native sampling (at most about 1024 per side) is shared by
    fast/native previews and export. EV adjusts the scale, never input pixels.
    """
    if not np.isfinite(exposure_ev) or not -6 <= exposure_ev <= 6:
        raise ValueError('PSB exposure must be finite, between -6 and +6 EV')
    stride=max(1, int(np.ceil(max(source.shape)/1024)))
    sample=np.asarray(source[::stride, ::stride], dtype=float)
    good=np.isfinite(sample)
    if valid is not None:
        good &= valid[::stride, ::stride]
    if rgb is not None:
        colour=np.asarray(rgb[::stride, ::stride], dtype=float)
        good &= np.isfinite(colour).all(axis=-1)
        sample=colour @ np.array([.25, .5, .25])
    good &= sample > 0
    params=params or {}
    radius=float(params.get('sr', 0.))
    if radius > 0:
        yy,xx=np.ogrid[:sample.shape[0], :sample.shape[1]]
        good &= np.hypot(xx*stride-params['sx'], yy*stride-params['sy']) > 1.2*radius
    values=sample[good]
    automatic_scale=float(np.percentile(values,99.5)) if values.size else 1.
    scale=automatic_scale * 2.**(-exposure_ev)
    return dict(mode='ael_presentation', strength=10., blend=1., scale=scale,
                normalization_range=[0.,scale], highlight_ceiling=.9,
                automatic_scale=automatic_scale, exposure_ev=float(exposure_ev),
                sampled_pixels=int(values.size), sampling_stride=stride,
                scale_policy='P99.5 positive native luminance outside 1.2 lunar radii; application heuristic')


def ael_tone_map(image, valid, settings):
    """AEL curve: per-channel Asinh, then shared shoulder; no positive pre-clipping."""
    scale=float(settings['scale'])
    strength=float(settings.get('strength',10.))
    ceiling=float(settings.get('highlight_ceiling',.9))
    if not np.isfinite([scale,strength,ceiling]).all() or scale <= 0 or strength <= 0 or not 0 < ceiling <= 1-1/65535:
        raise ValueError('Invalid PSB presentation scale, Asinh or highlight ceiling')
    image=np.asarray(image)
    valid=np.asarray(valid)
    if image.ndim not in (2,3) or (image.ndim == 3 and image.shape[-1] != 3) or valid.shape != image.shape[:2]:
        raise ValueError('PSB presentation needs matching mono/RGB and validity canvases')
    result=np.empty(image.shape,np.float32)
    def strip(bounds):
        check_cancelled()
        for first in range(bounds[0],bounds[1],128):
            stop=min(bounds[1],first+128)
            block=np.asarray(image[first:stop],dtype=float)
            observed=valid[first:stop]
            if not np.isfinite(block[observed]).all():
                raise ValueError('Nonfinite observed PSB presentation samples')
            mask=observed if image.ndim == 2 else observed[...,None]
            a=np.where(mask,np.maximum(block,0.),0.)
            with np.errstate(over='ignore',invalid='ignore'):
                u=np.arcsinh(a/scale*strength)/np.arcsinh(strength)
            if not np.isfinite(u).all():
                raise ValueError('PSB tone mapping overflow')
            peak=u if image.ndim == 2 else np.max(u,axis=-1)
            shoulder=ceiling*(-np.expm1(-peak/ceiling))
            factor=np.divide(shoulder,peak,out=np.zeros_like(peak),where=peak>0)
            result[first:stop]=u*(factor if image.ndim == 2 else factor[...,None])
    map_in_threads(strip,row_strips(image.shape[0]))
    return result


def quantize_u16(image):
    """to_u16 in fixed row strips on helper threads; identical to to_u16 element by element."""
    from .layer_export import to_u16
    a=np.asarray(image)
    result=np.empty(a.shape,np.uint16)
    def strip(bounds):
        check_cancelled()
        result[bounds[0]:bounds[1]]=to_u16(a[bounds[0]:bounds[1]])
    map_in_threads(strip,row_strips(a.shape[0]))
    return result


def u16_to_unit(a):
    """Exact float64 values of 16-bit display samples (value / 65535), in threaded strips."""
    if a is None:
        return None
    result=np.empty(a.shape,np.float64)
    def strip(bounds):
        np.divide(a[bounds[0]:bounds[1]],65535.,out=result[bounds[0]:bounds[1]])
    map_in_threads(strip,row_strips(a.shape[0]))
    return result


def psb_base_u16(source, params, settings, rgb=None):
    """16-bit mono presentation base and optional RGB Color samples (exact, threaded strips).

    The base is the 0.30/0.59/0.11 luminance of the quantized colour, quantized
    again; each strip performs the same per-row products as the whole array.
    """
    from .layer_export import to_u16
    valid=np.isfinite(source) & params.get('valid_mask',True)
    if rgb is None:
        return quantize_u16(ael_tone_map(source,valid,settings)), None
    valid &= np.isfinite(rgb).all(axis=-1)
    colour=quantize_u16(ael_tone_map(rgb,valid,settings))
    weights=np.array([.30,.59,.11])
    luminance=np.empty(colour.shape[:2],np.uint16)
    def strip(bounds):
        check_cancelled()
        block=colour[bounds[0]:bounds[1]].astype(float)/65535.
        luminance[bounds[0]:bounds[1]]=to_u16(block @ weights)
    map_in_threads(strip,row_strips(colour.shape[0]))
    return luminance, colour


def psb_base(source, params, settings, rgb=None):
    """Quantized mono presentation base and optional top Color layer for both routes."""
    base, colour = psb_base_u16(source, params, settings, rgb)
    return u16_to_unit(base), u16_to_unit(colour)


class PresentationCache:
    """16-bit PSB bases of the last sources, shared by the views and the export.

    The key holds the source and RGB objects (weakly) and the curve settings:
    another image, a new colour calibration (a new RGB array) or another
    exposure (another scale) never reuses an entry. Values are read-only.
    """

    def __init__(self, size=2):
        self._size=size
        self._entries=OrderedDict()
        self._lock=RLock()

    def clear(self):
        with self._lock:
            self._entries.clear()

    @staticmethod
    def _key(source, rgb, settings):
        return (id(source), None if rgb is None else id(rgb), float(settings['scale']),
                float(settings.get('strength',10.)), float(settings.get('highlight_ceiling',.9)))

    def lookup(self, source, rgb, settings):
        key=self._key(source,rgb,settings)
        with self._lock:
            entry=self._entries.get(key)
            if entry is None or entry[0]() is not source or (rgb is not None and entry[1]() is not rgb):
                return None
            self._entries.move_to_end(key)
            return entry[2], entry[3]

    def base_u16(self, source, params, settings, rgb=None):
        cached=self.lookup(source,rgb,settings)
        if cached is not None:
            return cached
        base,colour=psb_base_u16(source,params,settings,rgb)
        for array in (base,colour):
            if array is not None:
                array.setflags(write=False)
        key=self._key(source,rgb,settings)
        with self._lock:
            self._entries[key]=(weakref.ref(source),None if rgb is None else weakref.ref(rgb),base,colour)
            self._entries.move_to_end(key)
            while len(self._entries)>self._size:
                self._entries.popitem(last=False)
        return base,colour
