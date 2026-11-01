"""Tangential detail with radial tiles on threads gives the same result bit for bit."""
import unittest

import numpy as np

from core.parallelism import filter_budget
from core.tangential import tangential_detail


class ThreadedTangentialTests(unittest.TestCase):
    def test_any_thread_count_gives_the_same_detail(self):
        rng = np.random.default_rng(17)
        yy, xx = np.indices((520, 610), dtype=float)
        cx, cy, radius = 300.4, 251.7, 45.
        r = np.hypot(xx-cx, yy-cy)
        image = (1 + 800*(np.maximum(r, 1)/radius)**-3) * np.exp(.04*rng.standard_normal(r.shape))
        image[r < radius] = np.nan
        image[:12] = np.nan
        for arc in (3., 20.):                                  # direct and FFT angular kernels
            results = []
            for workers in (1, 8):
                with filter_budget(workers):
                    results.append(tangential_detail(image, cx, cy, radius, arc_sigma_deg=arc, gain=2.,
                                                     denoise=.5, outer_radius=8.))
            with self.subTest(arc=arc):
                np.testing.assert_array_equal(results[1], results[0])


if __name__ == '__main__':
    unittest.main()
