"""Frozen AEL 1.4.1 radial_quantile_rank global oracles (Pere Guerra Serra, MIT)."""
from pathlib import Path
import unittest
import sys
from unittest.mock import patch
import numpy as np
from core.filters import FilterWorker
from core.radial_continuous import rhef_continuous_normalize


class CurrentAELRHEFTests(unittest.TestCase):
    def test_current_global_rank_and_application_dispatch_are_exact(self):
        name='ael_rhef_global_windows.npz' if sys.platform=='win32' else 'ael_rhef_global_141.npz'
        with np.load(Path(__file__).parent/'fixtures'/name) as fixture:
            for index in range(2):
                with self.subTest(scene=index):
                    a,valid,r,angles,geometry,expected=[fixture[f'{index}_{key}'] for key in
                        ('image','valid','radii','angles','geometry','expected')]
                    actual=rhef_continuous_normalize(a,r,valid=valid,reference_precision=True,position_angles=angles)
                    np.testing.assert_array_equal(actual,expected)
                    cx,cy,radius=geometry
                    application=FilterWorker().run_rhef_native(a,100,0,None,cx,cy,radius,
                        valid=valid,bin_px=2,mode='continuous',operator_output=True)
                    np.testing.assert_array_equal(application,expected)

    def test_custom_quantiles_targets_and_cancellation_remain_available(self):
        y,x=np.indices((48,64));r=np.hypot(x-31.3,y-23.7)
        a=(100+r+np.sin(x)).astype('f4');valid=np.ones(a.shape,bool);samples=valid.copy();samples[18:25,40:45]=False
        q=rhef_continuous_normalize(a,r,valid=samples,target_valid=valid,quantile_count=65,reference_precision=True)
        self.assertTrue(np.isfinite(q).all())
        self.assertTrue(((q>=0)&(q<=1)).all())
        from core.cancellation import ProcessingCancelled
        with patch('core.radial_continuous.check_cancelled',side_effect=ProcessingCancelled):
            with self.assertRaises(ProcessingCancelled):
                rhef_continuous_normalize(a,r,reference_precision=True)
        with self.assertRaises(ValueError):
            rhef_continuous_normalize(a,r,reference_precision=True,position_angles=np.ones((1,2)))
