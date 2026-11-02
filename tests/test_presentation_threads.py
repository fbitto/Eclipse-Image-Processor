"""Colour calibration, Asinh presentation and SetLum in threaded strips are exact.

The references below are the single-pass implementations they replace; the
threaded versions must match them bit for bit with one thread and with many.
"""
import unittest

import numpy as np

from core.colour import neutralize_tse, set_luminosity
from core.layer_export import to_u16
from core.parallelism import filter_budget
from core.presentation import PresentationCache, ael_tone_map, psb_base, psb_base_u16, psb_presentation_settings


def reference_neutralize(rgb, white=1.):
    a = np.asarray(rgb, dtype=float)
    valid = np.isfinite(a).all(axis=-1)
    if white is None:
        white = float(np.max(a, where=valid[..., None], initial=-np.inf)) * (1 + 1e-6)
    a = a/white
    small = a[::10, ::10]
    selected = small[np.isfinite(small).all(axis=-1) & (small > 0).all(axis=-1) & (small < 1).all(axis=-1)]
    background, foreground = np.percentile(selected, [1, 99], axis=0)
    span = foreground-background
    ratios = span/span[1]
    ratios /= ratios.max()
    corrected = np.maximum(a, 0)*(1/ratios)
    highlight = max(float(np.max(corrected[valid])), 1.)
    return np.where(valid[..., None], corrected/highlight, np.nan).astype(np.float32), highlight


def reference_tone_map(image, valid, settings):
    scale, strength, ceiling = settings['scale'], settings.get('strength', 10.), settings.get('highlight_ceiling', .9)
    block = np.asarray(image, dtype=float)
    mask = valid if block.ndim == 2 else valid[..., None]
    a = np.where(mask, np.maximum(block, 0.), 0.)
    u = np.arcsinh(a/scale*strength)/np.arcsinh(strength)
    peak = u if block.ndim == 2 else np.max(u, axis=-1)
    shoulder = ceiling*(-np.expm1(-peak/ceiling))
    factor = np.divide(shoulder, peak, out=np.zeros_like(peak), where=peak > 0)
    return (u*(factor if block.ndim == 2 else factor[..., None])).astype(np.float32)


def reference_set_luminosity(colour, luminance):
    c = np.asarray(colour, dtype=float)
    weights = np.array([.30, .59, .11])
    c = c + (luminance-c@weights)[..., None]
    low, high = c.min(axis=-1), c.max(axis=-1)
    low_factor = np.divide(luminance, luminance-low, out=np.ones_like(luminance), where=luminance != low)
    c = np.where((low < 0)[..., None], luminance[..., None]+(c-luminance[..., None])*low_factor[..., None], c)
    high_factor = np.divide(1-luminance, high-luminance, out=np.ones_like(luminance), where=high != luminance)
    c = np.where((high > 1)[..., None], luminance[..., None]+(c-luminance[..., None])*high_factor[..., None], c)
    return np.clip(c, 0, 1)


class ThreadedPresentationTests(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(12)
        h, w = 700, 611          # three strips with a short last one
        yy, xx = np.mgrid[:h, :w]
        r = np.hypot(xx-300.5, yy-350.2)
        lum = 440 + 5e7*np.maximum(r/40, 1)**-5 + rng.normal(0, 2, (h, w))
        lum[r <= 40] = np.nan
        lum[:3, :50] = 0.
        self.rgb = np.stack([lum*1.1, lum, lum*.85], axis=-1).astype(np.float32)
        self.rgb[5, 7, 1] = -3.
        self.mono = (self.rgb @ np.array([.299, .587, .114], np.float32)).astype(np.float32)
        self.params = dict(sx=300.5, sy=350.2, sr=40., valid_mask=np.isfinite(self.mono))

    def both(self, function, *args):
        with filter_budget(1):
            serial = function(*args)
        with filter_budget(7):
            threaded = function(*args)
        return serial, threaded

    def test_neutralize_matches_the_single_pass_reference(self):
        for white in (None, 6e7):
            (serial, report), (threaded, _) = self.both(neutralize_tse, self.rgb, white)
            expected, highlight = reference_neutralize(self.rgb, white)
            np.testing.assert_array_equal(serial, expected)
            np.testing.assert_array_equal(threaded, expected)
            self.assertEqual(report['highlight_scale'], highlight)
            self.assertEqual(serial.dtype, np.float32)

    def test_tone_map_base_and_set_luminosity_match_the_references(self):
        calibrated, _ = neutralize_tse(self.rgb, None)
        settings = psb_presentation_settings(self.mono, self.params['valid_mask'], rgb=calibrated, params=self.params)
        valid = np.isfinite(self.mono) & np.isfinite(calibrated).all(axis=-1)
        for image, mask in ((calibrated, valid), (self.mono, np.isfinite(self.mono))):
            serial, threaded = self.both(ael_tone_map, image, mask, settings)
            expected = reference_tone_map(image, mask, settings)
            np.testing.assert_array_equal(serial, expected)
            np.testing.assert_array_equal(threaded, expected)
        colour = to_u16(reference_tone_map(calibrated, valid, settings)).astype(float)/65535.
        base = to_u16(colour @ np.array([.30, .59, .11])).astype(float)/65535.
        (serial_base, serial_colour), (threaded_base, threaded_colour) = self.both(psb_base, self.mono, self.params, settings, calibrated)
        for actual in (serial_base, threaded_base):
            np.testing.assert_array_equal(actual, base)
        for actual in (serial_colour, threaded_colour):
            np.testing.assert_array_equal(actual, colour)
        luminance = (base*.97).astype(np.float32)
        serial, threaded = self.both(set_luminosity, colour, luminance)
        expected = reference_set_luminosity(colour, luminance)
        np.testing.assert_array_equal(serial, expected)
        np.testing.assert_array_equal(threaded, expected)

    def test_base_cache_follows_image_calibration_and_exposure(self):
        calibrated, _ = neutralize_tse(self.rgb, None)
        settings = psb_presentation_settings(self.mono, rgb=calibrated, params=self.params)
        cache = PresentationCache()
        first = cache.base_u16(self.mono, self.params, settings, calibrated)
        self.assertIs(cache.base_u16(self.mono, self.params, settings, calibrated)[0], first[0])
        self.assertFalse(first[0].flags.writeable)
        # Another exposure, another calibration or another image is never served from the cache.
        brighter = psb_presentation_settings(self.mono, rgb=calibrated, params=self.params, exposure_ev=1.)
        self.assertIsNone(cache.lookup(self.mono, calibrated, brighter))
        self.assertIsNone(cache.lookup(self.mono, calibrated.copy(), settings))
        self.assertIsNone(cache.lookup(self.mono.copy(), calibrated, settings))
        expected = psb_base_u16(self.mono, self.params, brighter, calibrated)
        actual = cache.base_u16(self.mono, self.params, brighter, calibrated)
        np.testing.assert_array_equal(actual[0], expected[0])
        np.testing.assert_array_equal(actual[1], expected[1])
        cache.clear()
        self.assertIsNone(cache.lookup(self.mono, calibrated, settings))


if __name__ == '__main__':
    unittest.main()
