"""The threaded MGN blur is SciPy's gaussian_filter, bit for bit."""
import unittest

import numpy as np
from scipy.ndimage import gaussian_filter

from core.filters import strip_gaussian


class StripGaussianTests(unittest.TestCase):
    def test_strips_equal_scipy_for_any_thread_count(self):
        rng = np.random.default_rng(21)
        image = rng.uniform(1e-3, 9., (521, 511))
        image[200:260, 100:400] = 0.
        for dtype in (np.float32, np.float64):
            a = image.astype(dtype)
            for sigma, truncate, mode in ((1.25, 3, 'nearest'), (40., 3, 'nearest'), (5., 4., 'constant')):
                expected = gaussian_filter(a, sigma, truncate=truncate, mode=mode)
                for workers in (2, 3, 8):
                    with self.subTest(dtype=dtype, sigma=sigma, mode=mode, workers=workers):
                        actual = strip_gaussian(a, sigma, truncate=truncate, mode=mode, workers=workers)
                        self.assertEqual(actual.dtype, expected.dtype)
                        np.testing.assert_array_equal(actual, expected)

    def test_small_images_and_one_thread_call_scipy_directly(self):
        a = np.random.default_rng(4).uniform(0, 1, (64, 80))
        np.testing.assert_array_equal(strip_gaussian(a, 2., truncate=3, workers=8),
                                      gaussian_filter(a, 2., truncate=3, mode='nearest'))


if __name__ == '__main__':
    unittest.main()
