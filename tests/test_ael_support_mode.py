"""Opt-in AEL support separation: compatibility, coverage, injected signal and nulls."""
import unittest
import numpy as np
from core.filters import FilterWorker
from core.layer_engine import LayerEngine

class AELSupportModeTests(unittest.TestCase):
    def setUp(self):
        y,x=np.indices((192,192));self.r=np.hypot(x-95.3,y-96.7);self.t=np.arctan2(y-96.7,x-95.3)
        self.valid=(self.r>24)&(self.r<90)
        self.samples=self.valid & ~((abs(self.t)<.2)&(self.r>27)&(self.r<60))
        self.source=((np.maximum(self.r,1)/24)**-3*(1+.1*np.cos(3*self.t))*
            np.exp(.005*np.random.default_rng(7).normal(size=self.r.shape))).astype('f4')
        self.source[~self.valid]=np.nan
        self.p=dict(sx=95.3,sy=96.7,sr=24,valid_mask=self.valid,statistics_mask=self.samples,
                    achf_str=100,wow_str=100,wow_mode='ael_bilateral',wow_scales=3)

    def layer(self,a,variant,experimental=True,samples=None):
        name='wow' if variant=='wow' else 'achf'
        p=dict(self.p,statistics_mask=self.samples if samples is None else samples,
               statistics_separate_ael=experimental)
        return LayerEngine().layer(FilterWorker(),a,p,name,None if name=='wow' else variant)

    def test_identical_masks_preserve_encoded_values_and_alpha(self):
        for variant in ('ael_iso_01','ael_iso_04','ael_angular_4','wow'):
            with self.subTest(variant=variant):
                baseline=self.layer(self.source,variant,False,self.valid)
                optional=self.layer(self.source,variant,True,self.valid)
                for key in ('image','alpha'):np.testing.assert_array_equal(optional[key],baseline[key])

    def test_optional_mode_keeps_observed_targets_and_preserves_missing_and_positivity(self):
        a=self.source.copy();a[90,150]=0;a[91,150]=-1
        excluded=self.valid & ~self.samples & (a>0)
        for variant in ('ael_iso_01','ael_iso_04','ael_angular_4','wow'):
            with self.subTest(variant=variant):
                baseline=self.layer(a,variant,False);optional=self.layer(a,variant,True)
                self.assertFalse(baseline['alpha'][excluded].any())
                complete=self.layer(self.source,variant,True)
                self.assertTrue(np.all(complete['alpha'][excluded]>0))
                self.assertFalse(optional['alpha'][~self.valid].any())
                self.assertEqual(optional['alpha'][90,150],0)
                self.assertEqual(optional['alpha'][91,150],0)

    def test_independent_noise_null_is_not_correlated_in_restored_sector(self):
        nulls=[]
        for seed in (19,31):
            a=((np.maximum(self.r,1)/24)**-3*np.exp(.03*np.random.default_rng(seed).normal(size=self.r.shape))).astype('f4')
            a[~self.valid]=np.nan;nulls.append(a)
        selection=self.valid & ~self.samples
        for variant in ('ael_iso_01','ael_iso_04','ael_angular_4','wow'):
            first,second=[self.layer(a,variant)['image'].astype(float) for a in nulls]
            self.assertLess(abs(np.corrcoef(first[selection],second[selection])[0,1]),.25)

    def test_injected_faint_detail_response_is_not_inverted_in_excluded_sector(self):
        signal=.005*np.sin(17*self.t)*np.exp(-((self.r-44)/15)**4)
        injected=(self.source*np.exp(signal)).astype('f4')
        selection=self.valid & ~self.samples
        for variant in ('ael_iso_04','ael_angular_4','wow'):
            with self.subTest(variant=variant):
                clean=self.layer(self.source,variant);changed=self.layer(injected,variant)
                response=changed['image'].astype(float)-clean['image'].astype(float)
                self.assertGreater(np.corrcoef(response[selection],signal[selection])[0,1],.1)

if __name__=='__main__':unittest.main()
