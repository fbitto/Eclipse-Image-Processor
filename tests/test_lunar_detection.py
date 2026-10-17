import unittest

import numpy as np

from gui.app import EclipseProcessorApp


class LunarDetectionTests(unittest.TestCase):
    def test_off_center_disk_at_full_resolution(self):
        # Fractional limb coordinates on a non-square image larger than preview.
        y, x = np.indices((1601, 2203), dtype=np.float32)
        cx, cy, radius = 1037.4, 763.7, 281.2
        distance = np.hypot(x - cx, y - cy)
        image = np.clip((distance - radius) / 2 + 0.5, 0, 1)
        actual = EclipseProcessorApp.detect_lunar_limb(None, image)
        np.testing.assert_allclose(actual, (cx, cy, radius), atol=1)

    def test_uniform_and_nonfinite_images(self):
        image = np.zeros((240, 320), dtype=np.float32)
        image[0, :3] = (np.nan, np.inf, -np.inf)
        actual = EclipseProcessorApp.detect_lunar_limb(None, image)
        self.assertEqual(actual, (160, 120, 60))

    def test_linear_hdr_limb_is_not_lost_to_saturated_outliers(self):
        y, x = np.indices((801, 1003), dtype=np.float32)
        cx, cy, radius = 467.4, 413.7, 112.2
        distance = np.hypot(x-cx, y-cy)
        edge = np.clip((distance-radius)/2+.5, 0, 1)
        image = edge*(.003+.02*(radius/np.maximum(distance, radius))**4)
        image[40:43, 50:53] = 1000  # Saturated source far brighter than corona.
        before = image.copy()
        for scale, offset in ((1., 0.), (65535., -3.), (1e-8, 0.)):
            with self.subTest(scale=scale, offset=offset):
                actual = EclipseProcessorApp.detect_lunar_limb(None, image*scale+offset)
                np.testing.assert_allclose(actual, (cx, cy, radius), atol=1)
        np.testing.assert_array_equal(image, before)
