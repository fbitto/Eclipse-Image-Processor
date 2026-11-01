"""Independent observed-tap references at frame boundaries and for WOW denoising."""
import unittest
from unittest.mock import patch
import numpy as np
from scipy.special import erf
from core.filters import FilterWorker,blend_filter_result
from core.masked_filters import MaskedWorker

class ObservedFilterEdgesTests(unittest.TestCase):
    def test_standard_starlet_matches_observed_scalar_taps_at_every_edge(self):
        a=np.random.default_rng(22).normal(size=(9,11));valid=np.ones(a.shape,bool);valid[2:4,3:6]=False
        a[~valid]=1e300;worker=MaskedWorker(None,valid);kernel=np.array([1,4,6,4,1])/16
        for step in (1,2,8):
            expected=np.zeros(a.shape)
            for y,x in zip(*np.nonzero(valid)):
                total=mass=0.
                for j,wy in enumerate(kernel):
                    for i,wx in enumerate(kernel):
                        yy,xx=y+(j-2)*step,x+(i-2)*step
                        if 0<=yy<a.shape[0] and 0<=xx<a.shape[1] and valid[yy,xx]:
                            total+=wy*wx*a[yy,xx];mass+=wy*wx
                expected[y,x]=total/mass
            np.testing.assert_allclose(worker.starlet_blur(a,step,None)[valid],expected[valid],atol=1e-14)

    def test_mgn_observed_route_matches_explicit_mask_and_changes_frame_edges(self):
        a=np.random.default_rng(31).uniform(1,20,(32,40)).astype('f4');worker=FilterWorker()
        args=(100,32,70,70,3)
        expected=MaskedWorker(worker,np.ones(a.shape,bool)).run_mgn_native(a,*args,sigmas=(1.,3.))
        actual=worker.run_mgn_native(a,*args,sigmas=(1.,3.),observed_edges=True)
        np.testing.assert_array_equal(actual,expected)
        reference=worker.run_mgn_native(a,*args,sigmas=(1.,3.))
        self.assertGreater(np.max(abs(actual-reference)),.01)

    def test_wow_significance_is_erf_weight_not_subtractive_threshold(self):
        a=np.random.default_rng(51).normal(10,1,(40,48));valid=np.ones(a.shape,bool)
        worker=MaskedWorker(None,valid);smooth=worker.starlet_blur(a,1,None);detail=a-smooth
        power=np.sqrt(worker.starlet_blur(detail**2,1,None));noise=np.full(a.shape,.7)
        from watroo import B3spline
        threshold=2*.7*B3spline(2).sigma_e()[0]
        from watroo.wavelets import Coefficients
        coefficients=Coefficients([detail],B3spline(2));coefficients.noise=noise
        np.testing.assert_array_equal(coefficients.significance(2,0),erf(abs(detail)/threshold))
        expected=np.divide(detail*coefficients.significance(2,0),power,out=np.zeros_like(detail),where=power>0)
        expected+=smooth/np.std(smooth)
        expected=blend_filter_result(a,expected,100)
        actual=worker.run_wow_native(a,n_scales=1,denoise_coefficients=[2],noise=noise)
        np.testing.assert_allclose(actual,expected,atol=1e-6)
        with self.assertRaises(ValueError):worker.run_wow_native(a,n_scales=1,denoise_coefficients=[-1])

if __name__=='__main__':unittest.main()
