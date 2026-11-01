"""Continuous FNRGF with threaded target chunks and a radix key sort gives the same values bit for bit."""
import unittest

import numpy as np

from core.continuous_fnrgf import continuous_fnrgf, stable_key_order
from core.parallelism import filter_budget


class ThreadedFnrgfTests(unittest.TestCase):
    def test_key_order_is_the_stable_argsort(self):
        rng = np.random.default_rng(2)
        for high in (2, 300, 9760, 65535, 70000):
            keys = rng.integers(0, high, 200001)
            with self.subTest(high=high):
                np.testing.assert_array_equal(stable_key_order(keys), np.argsort(keys, kind='stable'))

    def test_any_thread_count_gives_the_same_layer(self):
        rng = np.random.default_rng(9)
        yy, xx = np.indices((410, 397), dtype=float)
        cx, cy, radius = 201.3, 197.8, 40.
        r = np.hypot(xx-cx, yy-cy)
        theta = np.arctan2(yy-cy, xx-cx)
        image = (1 + 500*(np.maximum(r, 1)/radius)**-3*(1+.3*np.cos(5*theta))) * np.exp(.05*rng.standard_normal(r.shape))
        image[r < radius] = np.nan
        image[:, 380:] = np.nan
        valid = np.isfinite(image)
        edges = np.linspace(1.05*radius, 6*radius, 41)
        results = []
        for workers in (1, 3, 8):
            with filter_budget(workers):
                results.append(continuous_fnrgf(image, r, theta, edges, order=6, segments=32, valid=valid,
                                                target_valid=valid, smooth_px=8.))
        self.assertGreater(np.count_nonzero(np.isfinite(results[0])), 3*32768)
        for result in results[1:]:
            np.testing.assert_array_equal(result, results[0])


if __name__ == '__main__':
    unittest.main()
