"""Physical filter footprints should follow preview-to-export resizing."""
import unittest
from unittest.mock import patch
import numpy as np

from core.pipeline import prepare_parameters
from core.filters import FilterWorker


class ExportSpatialScaleTests(unittest.TestCase):
    def parameters(self, target, **overrides):
        p = dict(sx=750, sy=750, sr=200, bilateral_d=3,
                 achf_kernel=5, rhef_bin_px=1, fnrgf_nbins=80,
                 wow_scales=8, wow_denoise=[1, 2, 3], wow_str=32,
                 achf_threshold=10, mgn_gam=30)
        p.update(overrides)
        return prepare_parameters(p, (3000, 3000), (1500, 1500), (target, target))

    def test_native_export_preserves_physical_widths_and_dimensionless_controls(self):
        p = self.parameters(3000)
        self.assertNotIn("bilateral_d", p)
        self.assertEqual(p["achf_kernel"], 10)
        self.assertEqual(p["rhef_bin_px"], 1)
        self.assertEqual(p["fnrgf_nbins"], 160)
        self.assertEqual(p["wow_scales"], 9)
        self.assertEqual(p["wow_denoise"], [1, 1, 2, 3])
        self.assertEqual((p["wow_str"], p["achf_threshold"], p["mgn_gam"]), (32, 10, 30))

    def test_mgn_uses_native_pixel_sigmas_independent_of_preview_size(self):
        sigmas=(1.25,2.5,5,10,20,40)
        p=dict(sx=100,sy=100,sr=20,mgn_sigmas=sigmas,mgn_weights=(1,)*6)
        for preview in ((1500,1500),(750,750)):
            native=prepare_parameters(p,(3000,3000),preview,(3000,3000))
            self.assertEqual(native['mgn_sigmas'],sigmas)
            small=prepare_parameters(p,(3000,3000),preview,preview)
            np.testing.assert_allclose(small['mgn_sigmas'],np.array(sigmas)*preview[0]/3000)
            self.assertEqual(small['mgn_weights'],tuple(0 if s < .5 else 1 for s in small['mgn_sigmas']))
        self.assertEqual(p['mgn_sigmas'],sigmas)

    def test_noninteger_resize_and_preview_auto(self):
        p = self.parameters(2560)
        self.assertEqual(p["wow_scales"], 9)
        self.assertAlmostEqual(p["mgn_sigmas"][0], 1.25 * 2560 / 3000)
        self.assertEqual(self.parameters(3000, wow_scales=0)["wow_scales"], 9)
        self.assertEqual(self.parameters(1500)["wow_denoise"], [1, 2, 3])
        self.assertEqual(self.parameters(1500)["wow_scales"], 8)

    def test_downscale_and_backend_cap(self):
        p = self.parameters(750)
        self.assertEqual(p["wow_scales"], 7)
        self.assertEqual(p["wow_denoise"], [2, 3])
        self.assertEqual(self.parameters(3000, wow_scales=10)["wow_scales"], 9)
        self.assertEqual(self.parameters(3000, wow_denoise=[])["wow_denoise"], [])

    def test_fnrgf_native_width_preserves_count_across_resolutions(self):
        for target, expected in ((1500, 100), (2560, 100), (3000, 100)):
            p = self.parameters(target, fnrgf_bin_px=4, fnrgf_rad=10, fnrgf_rmax=30)
            self.assertEqual(p["fnrgf_nbins"], expected)
            width = 2 * p["sr"] / p["fnrgf_nbins"] * 3000/target
            self.assertLessEqual(width, 4)
            self.assertGreater(width, 3.9)

    def test_fnrgf_log_width_refers_to_inner_ring(self):
        for target in (1500, 2560, 3000):
            p = self.parameters(target, fnrgf_bin_px=4, fnrgf_rad=10,
                                fnrgf_rmax=30, fnrgf_radial_binning="log")
            width = p["sr"] * (3 ** (1 / p["fnrgf_nbins"]) - 1) * 3000/target
            self.assertLessEqual(width, 4)
            self.assertGreater(width, 3.8)

    def test_unresolved_mgn_bands_do_not_run_gaussians_or_increase_other_weights(self):
        from core.filters import mgn_normalize
        p=self.parameters(300)
        self.assertEqual(p['mgn_weights'],(0.,0.,1.,1.,1.,1.))
        image=np.random.default_rng(12).uniform(1,2,(32,40)).astype('f4')
        from scipy.ndimage import gaussian_filter
        with patch('core.filters.gaussian_filter',wraps=gaussian_filter) as gaussian:
            result=mgn_normalize(image,sigma=p['mgn_sigmas'],weights=p['mgn_weights'])
        self.assertTrue(all(call.args[1]>=.5 for call in gaussian.call_args_list))
        self.assertEqual(len(gaussian.call_args_list),8)
        self.assertTrue(np.isfinite(result).all())
        with patch('core.filters.gaussian_filter',side_effect=AssertionError('Unresolved band ran')):
            only_global=mgn_normalize(image,sigma=(.1,.2),weights=(0.,0.))
        np.testing.assert_allclose(only_global,.7*((image-image.min())/np.ptp(image))**(1/3.2),atol=1e-6)

    def test_achf_preview_omits_subpixel_bands_but_native_keeps_presets(self):
        from core.ael_achf import ael_achf_layer
        y,x=np.indices((192,192));r=np.hypot(x-96,y-96)
        image=(np.maximum(r,1)/20)**-3
        for scale,omitted in ((1.,[]),(.25,[.25])):
            _,info=ael_achf_layer(image,96,96,20,scale=scale,variant='ael_iso_04')
            self.assertEqual(info['omitted_sigmas_px'],omitted)
            self.assertTrue(all(s>=.5 for s in info['sigmas_px']))

    def test_achf_receives_scaled_minimum_width(self):
        image = np.arange(81, dtype=np.float32).reshape(9, 9) / 80
        with patch("core.filters.adaptive_circular_highpass", return_value=image) as operator:
            FilterWorker.run_achf(None, image, 50, 10, 20, 4, 4, 2, spatial_scale=2)
        self.assertEqual(operator.call_args.args[1], 1)
        self.assertEqual(operator.call_args.kwargs["spatial_scale"], 2)


if __name__ == "__main__":
    unittest.main()
