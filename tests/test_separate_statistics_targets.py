"""Excluded observations remain evaluable without contaminating their neighbors."""
import unittest
import numpy as np
from core.filters import FilterWorker
from core.layer_engine import LayerEngine

class SeparateStatisticsTargetsTests(unittest.TestCase):
    def test_local_layers_keep_targets_and_ignore_them_in_statistics(self):
        y,x=np.indices((144,160));r=np.hypot(x-80,y-72);theta=np.arctan2(y-72,x-80)
        source=(1000/(1+r)**2*(1+.2*np.sin(8*theta))).astype('f4')
        valid=np.ones(source.shape,bool);valid[5:8,10:13]=False;source[~valid]=np.nan
        samples=valid.copy();samples[70:72,100:102]=False
        p=dict(sx=80,sy=72,sr=12,valid_mask=valid,statistics_mask=samples,
               mgn_str=100,mgn_gam=32,mgn_sigmas=(1.,3.),wow_str=100,wow_scales=3,
               tangential_str=100,tangential_fade=0,achf_str=100,achf_kernel=20,
               achf_threshold=200,achf_threshold_mode='relative',larson_sekanina_str=100,
               larson_sekanina_angular=15)
        excluded=valid & ~samples
        altered=source.copy();altered[excluded]*=10
        for name in ('mgn','wow','tangential','achf','larson_sekanina'):
            with self.subTest(name=name):
                variant='adaptive' if name=='achf' else None
                first=LayerEngine().layer(FilterWorker(),source,p,name,variant)
                second=LayerEngine().layer(FilterWorker(),altered,p,name,variant)
                self.assertTrue(np.all(first['alpha'][excluded]>0))
                self.assertFalse(first['alpha'][~valid].any())
                np.testing.assert_array_equal(first['image'][samples],second['image'][samples])
                self.assertTrue(np.any(first['image'][excluded]!=second['image'][excluded]))

    def test_adaptive_target_without_accepted_statistical_pairs_is_transparent(self):
        y,x=np.indices((64,80));a=(10+.01*x+.02*y).astype('f4')
        samples=np.ones(a.shape,bool);samples[30:32,50:52]=False
        p=dict(sx=40,sy=32,sr=8,statistics_mask=samples,achf_str=100,
               achf_kernel=20,achf_threshold=0,achf_threshold_mode='relative')
        layer=LayerEngine().layer(FilterWorker(),a,p,'achf','adaptive')
        self.assertFalse(layer['alpha'][~samples].any())

if __name__=='__main__':unittest.main()
