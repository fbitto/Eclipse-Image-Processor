"""Colour neutralization, gamut handling and Photoshop Color layer composition."""
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
import tifffile

from core.colour import neutralize_tse, colour_layer, set_luminosity
from core.filters import FilterWorker
from core.layer_export import export_layer_package, overlay, to_u16


class ColourTests(unittest.TestCase):
    def setUp(self):
        self.t = np.linspace(.02, .95, 80*100).reshape(80, 100)
        self.rgb = np.stack([.1+.6*self.t, .05+.3*self.t, .025+.15*self.t], axis=-1).astype(np.float32)
        self.mono = self.rgb @ np.array([.299, .587, .114])

    def test_tse_percentiles_ratios_shift_and_integer_white_equivalence(self):
        a, report = neutralize_tse(self.rgb)
        np.testing.assert_allclose(report['ratios'], [1, .5, .25], atol=1e-6)
        np.testing.assert_allclose(a[..., 0], a[..., 1], atol=1e-6)
        np.testing.assert_allclose(a[..., 1], a[..., 2], atol=1e-6)
        # Independent direct expression of tse-tools's normalized-data recipe.
        sample = self.rgb[::10, ::10].astype(float)
        low, high = np.percentile(sample.reshape(-1, 3), [1, 99], axis=0)
        ratio = (high-low)/(high-low)[1]
        ratio /= ratio.max()
        expected = (self.rgb.astype(float)-low)/ratio
        minimum = min(expected.min(), 0)
        expected = np.clip((expected-minimum)/(1-minimum), 0, 1)
        np.testing.assert_allclose(a, expected, atol=1e-7)
        scaled, _ = neutralize_tse(self.rgb*65535, 65535)
        np.testing.assert_allclose(a, scaled, atol=2e-7)
        np.testing.assert_array_equal(self.rgb, np.stack([.1+.6*self.t, .05+.3*self.t, .025+.15*self.t], axis=-1).astype(np.float32))

    def test_calibration_excludes_missing_and_rejects_undetermined_balance(self):
        rgb = self.rgb.copy(); rgb[0, 0] = np.nan
        result, report = neutralize_tse(rgb)
        self.assertTrue(np.isnan(result[0, 0]).all())
        self.assertTrue(np.isfinite(result[1:]).all())
        with self.assertRaises(ValueError):
            neutralize_tse(np.ones((30, 30, 3))*.5)
        with self.assertRaises(ValueError):
            neutralize_tse(np.ones((30, 30, 3))*2)

    def test_colour_blend_preserves_luminosity_and_is_in_gamut(self):
        rng = np.random.default_rng(7)
        colours = rng.uniform(0, 1, (80, 100, 3))
        for target in (np.zeros((80, 100)), np.ones((80, 100)), rng.uniform(0, 1, (80, 100))):
            output = set_luminosity(colours, target)
            np.testing.assert_allclose(output @ [.30, .59, .11], target, atol=1e-14)
            self.assertTrue(np.all((output >= 0) & (output <= 1)))
        display = colour_layer(self.rgb, self.mono, dict(mode='asinh', strength=10))
        self.assertEqual(display.shape, self.rgb.shape)
        self.assertTrue(np.isfinite(display).all())

    def test_exported_color_layer_matches_combined_and_loader_mode(self):
        params = dict(sx=50., sy=40., sr=10., usm_enabled=True, usm_str=15, usm_radius=10, usm_sigma=2)
        display = dict(mode='asinh', strength=10, blend=1)
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)/'layers'
            export_layer_package(FilterWorker(), self.mono, params, display, 'original.tif', output, rgb=self.rgb)
            recipe = json.loads((output/'recipe.json').read_text())
            self.assertEqual([r['mode'] for r in recipe['layers']], ['Normal', 'Overlay', 'Color'])
            self.assertEqual(recipe['layers'][-1]['file'], 'original_03_RGB_Color.tif')
            base = tifffile.imread(output/recipe['layers'][0]['file'])[..., 0]/65535.
            detail = tifffile.imread(output/recipe['layers'][1]['file'])/65535.
            mono = overlay(base, detail[..., 0], detail[..., 3], recipe['layers'][1]['opacity_255']/255.)
            colour = tifffile.imread(output/recipe['layers'][2]['file'])[..., :3]/65535.
            expected = to_u16(set_luminosity(colour, mono))
            np.testing.assert_array_equal(tifffile.imread(output/recipe['combined']), expected)
            self.assertIn('BlendMode.COLOR', (output/'Cargar_capas_Photoshop.jsx').read_text())
