"""Dimensionless HDR Larson–Sekanina is optional and independent of radiance units."""
import unittest
import numpy as np
from core.filters import FilterWorker,larson_sekanina_residual
from core.layer_engine import LayerEngine
from core.pipeline import apply_filter

class LogLarsonTests(unittest.TestCase):
    def setUp(self):
        y,x=np.indices((192,224));self.r=np.hypot(x-112,y-96);theta=np.arctan2(y-96,x-112)
        self.valid=self.r>24
        self.a=((np.maximum(self.r,1)/24)**-4*np.exp(.03*np.sin(17*theta))).astype('f4')
        self.a[~self.valid]=np.nan
        self.p=dict(sx=112,sy=96,sr=24,valid_mask=self.valid,larson_sekanina_str=100,
                    larson_sekanina_angular=3,larson_sekanina_mode='log')

    def test_log_residual_matches_linear_operator_on_logs(self):
        logged=np.zeros_like(self.a,dtype=float)
        np.log(self.a.astype(float),out=logged,where=self.valid)
        expected=larson_sekanina_residual(logged,112,96,24,valid=self.valid)
        actual=larson_sekanina_residual(self.a,112,96,24,valid=self.valid,input_mode='log')
        np.testing.assert_array_equal(actual,expected)

    def test_input_units_and_hidden_disk_outlier_do_not_change_log_layer(self):
        first=LayerEngine().layer(FilterWorker(),self.a,self.p,'larson_sekanina')
        for units in (1e-12,1e12):
            scaled=self.a*units
            scaled[~self.valid]=1e30
            other=LayerEngine().layer(FilterWorker(),scaled,self.p,'larson_sekanina')
            np.testing.assert_allclose(other['image'],first['image'],atol=1)
            np.testing.assert_array_equal(other['alpha'],first['alpha'])
            self.assertEqual(other['mapping']['scale'],1.)

    def test_log_nonpositive_is_operator_support_not_missing_data(self):
        a=self.a.copy();a[95,150]=0;a[96,150]=-1
        layer=LayerEngine().layer(FilterWorker(),a,self.p,'larson_sekanina')
        self.assertEqual(layer['alpha'][95,150],0);self.assertEqual(layer['alpha'][96,150],0)
        self.assertFalse(layer['alpha'][~self.valid].any())
        np.testing.assert_array_equal(a[95:97,150],[0,-1])
        with self.assertRaisesRegex(ValueError,'dimensionless'):
            apply_filter(FilterWorker(),a,dict(self.p,larson_sekanina_enabled=True),verbose=False)

if __name__=='__main__':unittest.main()
