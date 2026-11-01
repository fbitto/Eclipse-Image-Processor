"""Adaptive pair rejection has local, unit-independent GUI semantics."""
import unittest
import numpy as np
from core.filters import adaptive_circular_highpass

class RelativeAdaptiveTests(unittest.TestCase):
    def setUp(self):
        self.a=np.random.default_rng(21).uniform(-3,20,(40,48)).astype('f4')
        self.a[15:18,20:23]=0

    def run_filter(self,a,t=.1):
        return adaptive_circular_highpass(a,3,t,gain=1,background=0,threshold_mode='relative')

    def test_relative_filter_is_invariant_to_positive_input_units(self):
        expected=self.run_filter(self.a)
        for units in (1e-12,1e12):
            np.testing.assert_allclose(self.run_filter(self.a*units)/units,expected,atol=2e-6)

    def test_far_outlier_does_not_change_local_rejection(self):
        expected=self.run_filter(self.a)
        changed=self.a.copy();changed[0,0]=1e20
        np.testing.assert_array_equal(self.run_filter(changed)[8:,8:],expected[8:,8:])

    def test_full_relative_range_accepts_signed_and_zero_pairs(self):
        expected=adaptive_circular_highpass(self.a,3,float(np.ptp(self.a)),gain=1,background=0)
        np.testing.assert_array_equal(self.run_filter(self.a,2.),expected)
        self.assertTrue(np.isfinite(self.run_filter(self.a)).all())
        np.testing.assert_array_equal(self.run_filter(np.zeros_like(self.a)),0)

    def test_masked_worker_forwards_relative_threshold_and_ignores_hidden_values(self):
        from core.masked_filters import MaskedWorker
        valid=np.ones(self.a.shape,bool);valid[12:16,17:21]=False
        worker=MaskedWorker(None,valid)
        first=worker.run_achf(self.a,100,30,10,24,20,5,intensity_threshold=10,
                              background=0,threshold_mode='relative')
        poisoned=self.a.copy();poisoned[~valid]=1e30
        second=worker.run_achf(poisoned,100,30,10,24,20,5,intensity_threshold=10,
                               background=0,threshold_mode='relative')
        np.testing.assert_array_equal(first[valid],second[valid])
        self.assertTrue(np.isfinite(second).all())

    def test_zero_threshold_is_background_only_and_unknown_mode_fails(self):
        np.testing.assert_array_equal(self.run_filter(self.a,0),0)
        with self.assertRaisesRegex(ValueError,'threshold mode'):
            adaptive_circular_highpass(self.a,3,.1,threshold_mode='unknown')

if __name__=='__main__':unittest.main()
