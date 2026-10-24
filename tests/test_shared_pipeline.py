import unittest
from unittest.mock import Mock
import numpy as np

from core.filters import FilterWorker
from core.pipeline import execute_pipeline, prepare_parameters


class SharedPipelineTests(unittest.TestCase):
    def test_rectangular_pixel_centres_and_resolution_units(self):
        source = dict(sx=103.7, sy=58.1, sr=20., bilateral_d=10, tangential_arc=20,
                      achf_kernel=30, rhef_bin_px=2, fnrgf_nbins=80, rhef_mode="continuous")
        preview = prepare_parameters(source, (121, 207), (60, 103), (60, 103))
        full = prepare_parameters(source, (121, 207), (60, 103), (121, 207))
        self.assertAlmostEqual(preview["sx"], (103.7 + .5) * 103 / 207 - .5)
        self.assertAlmostEqual(preview["sy"], (58.1 + .5) * 60 / 121 - .5)
        self.assertEqual(preview["rhef_bin_px"], 2)
        self.assertAlmostEqual(full["rhef_bin_px"], 2 * np.sqrt(121 / 60 * 207 / 103))
        self.assertEqual(full["rhef_mode"], "continuous")
        self.assertEqual(source["sr"], 20)
        self.assertNotIn("mgn_sigmas", source)

    def test_stage_order_and_scaled_controls_are_shared(self):
        image = np.ones((32, 32), np.float32)
        worker = Mock()
        order = []
        methods = ("run_fnrgf_native",
                   "run_rhef_native", "run_mgn_native", "run_wow_native", "run_tangential", "run_larson_sekanina", "run_achf")
        for name in methods:
            getattr(worker, name).side_effect = lambda a, *args, name=name, **kwargs: (order.append(name) or a.copy())
        p = dict(sx=16, sy=16, sr=4, pre_stretch_enabled=True, pre_stretch_mode="log", pre_stretch_val=1,
                 noise_gate_enabled=True, noise_gate_str=10, noise_gate_thr=10,
                 bilateral_enabled=True, bilateral_str=10, bilateral_d=10, bilateral_sc=30, bilateral_ss=50,
                 fnrgf_enabled=True, fnrgf_str=10, fnrgf_ord=6, fnrgf_seg=16, fnrgf_cut=0, fnrgf_rad=10,
                 mgn_enabled=True, mgn_str=10, mgn_gam=32, wow_enabled=True, wow_str=10,
                 rhef_enabled=True, rhef_str=10, rhef_rad=10, rhef_upsilon=35, rhef_mode="continuous",
                 tangential_enabled=True, tangential_str=10, tangential_arc=10, tangential_gain=2,
                 larson_sekanina_enabled=True, larson_sekanina_str=10,
                 achf_enabled=True, achf_str=10, achf_kernel=10, achf_boost=20)
        np.testing.assert_array_equal(execute_pipeline(worker, image, p), image)
        self.assertEqual(order, list(methods))
        worker.run_pre_log.assert_not_called()
        worker.run_radial_noise_gate.assert_not_called()
        worker.run_bilateral_denoise.assert_not_called()
        self.assertEqual(worker.run_rhef_native.call_args.kwargs["mode"], "continuous")

    def test_qt_preview_and_synchronous_export_have_identical_results(self):
        image = np.random.default_rng(45).uniform(1, 100, (80, 100)).astype(np.float32)
        worker = FilterWorker()
        params = dict(sx=50, sy=40, sr=10, rhef_enabled=True, rhef_mode="continuous",
                      rhef_str=50, rhef_rad=10, rhef_upsilon=35, rhef_bin_px=2,
                      mgn_enabled=True, mgn_str=10, mgn_gam=32)
        emitted, failed = [], []
        worker.finished.connect(emitted.append)
        worker.failed.connect(failed.append)
        worker.process_pipeline(image, params)
        self.assertEqual(failed, [])
        np.testing.assert_array_equal(emitted[0], execute_pipeline(worker, image, params))

    def test_invalid_resolution_and_missing_input(self):
        with self.assertRaises(ValueError):
            prepare_parameters({}, (0, 100), (50, 50), (100, 100))
        with self.assertRaises(ValueError):
            execute_pipeline(FilterWorker(), None, {})
