"""Operator values stay separate from layer coverage and display blending."""
import unittest
from unittest.mock import patch
import numpy as np
from core.filters import FilterWorker
from core.layer_engine import LayerEngine
from core.layer_export import to_u16


class OperatorLayerTests(unittest.TestCase):
    def setUp(self):
        y,x=np.indices((96,96))
        self.r=np.hypot(x-48,y-48)
        self.source=(1000/(1+self.r)**2*(1+.1*np.cos(np.arctan2(y-48,x-48)))).astype('f4')
        self.p=dict(sx=48,sy=48,sr=10,fnrgf_str=100,fnrgf_ord=1,
                    fnrgf_seg=12,fnrgf_cut=0,fnrgf_rad=10,fnrgf_rmax=60,
                    fnrgf_nbins=25,fnrgf_mode='continuous',fnrgf_smooth=0,
                    rhef_str=100,rhef_rad=10,rhef_upsilon=35,rhef_mode='continuous')
        self.worker=FilterWorker()

    def layer(self,name,**kwargs):
        return LayerEngine().layer(self.worker,self.source,dict(self.p,**kwargs),name)

    def test_fnrgf_fade_changes_alpha_only(self):
        plain=self.layer('fnrgf',fnrgf_fade=0)
        faded=self.layer('fnrgf',fnrgf_fade=8)
        np.testing.assert_array_equal(plain['image'],faded['image'])
        ramp=np.clip(np.minimum(self.r-10,60-self.r)/8,0,1)
        np.testing.assert_array_equal(faded['alpha'],to_u16(plain['alpha']/65535*ramp*ramp*(3-2*ramp)))
        self.assertTrue(np.any((faded['alpha']>0)&(faded['alpha']<65535)))

    def test_undefined_fnrgf_and_rhef_never_encode_input(self):
        for name,method,core in [('fnrgf','run_fnrgf_native','core.continuous_fnrgf.continuous_fnrgf'),
                                 ('rhef','run_rhef_native','core.radial_continuous.rhef_continuous_normalize')]:
            with self.subTest(name=name),patch(core,return_value=np.full(self.source.shape,np.nan)):
                layer=self.layer(name)
                self.assertFalse(layer['alpha'].any())
                self.assertTrue(np.isfinite(layer['image']).all())

    def test_rhef_keeps_curved_ranks_and_confidence_only_changes_alpha(self):
        from core.radial_continuous import rhef_continuous_normalize
        q=rhef_continuous_normalize(self.source,self.r,bin_px=1,application_radius=10)
        q=np.where(q<.5,.5*(2*q)**.35,1-.5*(2-2*q)**.35)
        layer=self.layer('rhef')
        good=layer['alpha']>0
        np.testing.assert_array_equal(layer['image'][good],to_u16(q.astype(np.float32))[good])
        with patch('core.statistics_support.radial_confidence',return_value=np.full(q.shape,.25)):
            weighted=self.layer('rhef',rhef_noise_confidence=2)
        np.testing.assert_array_equal(weighted['image'],layer['image'])
        np.testing.assert_array_equal(weighted['alpha'],to_u16(layer['alpha']/65535*.25))

    def test_missing_pixels_stay_transparent(self):
        self.source[30:34,50:54]=np.nan
        for name in ('fnrgf','rhef'):
            layer=self.layer(name,statistics_exclude_lunar=True)
            self.assertFalse(layer['alpha'][30:34,50:54].any())

    def test_exported_rgba_keeps_operator_alpha(self):
        import json
        from pathlib import Path
        import tempfile
        import tifffile
        from core.layer_export import export_layer_package
        with tempfile.TemporaryDirectory() as tmp:
            p=dict(self.p,fnrgf_enabled=True,fnrgf_fade=8,rhef_enabled=True,rhef_noise_confidence=2)
            output=export_layer_package(self.worker,self.source,p,{},'source.fits',Path(tmp)/'layers')
            recipe=json.loads((output/'recipe.json').read_text())
            for record in recipe['layers']:
                if record['filter'] in ('fnrgf','rhef'):
                    expected=LayerEngine().layer(self.worker,self.source,p,record['filter'])
                    actual=tifffile.imread(output/record['file'])
                    np.testing.assert_array_equal(actual[...,3],expected['alpha'])
                    np.testing.assert_array_equal(actual[...,0],expected['image'])

    def test_native_helpers_preserve_legacy_input_mix_by_default(self):
        result=self.worker.run_rhef_native(self.source,100,10,35,48,48,10,mode='continuous')
        np.testing.assert_array_equal(result[self.r<10],self.source[self.r<10])
        raw=self.worker.run_rhef_native(self.source,100,10,35,48,48,10,mode='continuous',operator_output=True)
        self.assertTrue(np.isnan(raw[self.r<10]).all())
        zero_strength=self.worker.run_rhef_native(self.source,0,10,35,48,48,10,
                                                 mode='continuous',operator_output=True)
        np.testing.assert_array_equal(raw,zero_strength)


class DetailEncodingTests(unittest.TestCase):
    def test_gain_changes_encoded_contrast_and_zero_is_neutral(self):
        y,x=np.indices((192,192));r=np.hypot(x-96,y-96)
        a=(1000/(1+r)**2*(1+.15*np.sin(8*np.arctan2(y-96,x-96)))).astype('f4')
        p=dict(sx=96,sy=96,sr=20,tangential_str=100,tangential_fade=0,
               achf_str=100,achf_kernel=20,achf_threshold=100)
        for name,key,unit in [('tangential','tangential_gain',1),('achf','achf_boost',10)]:
            with self.subTest(name=name):
                layers=[LayerEngine().layer(FilterWorker(),a,dict(p,**{key:k*unit}),name,
                        'adaptive' if name=='achf' else None) for k in (0,1,2)]
                good=(layers[1]['alpha']>0)&(layers[1]['image']>22000)&(layers[1]['image']<43000)
                self.assertGreater(np.count_nonzero(good),100)
                self.assertTrue(np.all(layers[0]['image'][good]==32768))
                np.testing.assert_allclose(layers[2]['image'][good].astype(float)-32767.5,
                    2*(layers[1]['image'][good].astype(float)-32767.5),atol=1.5)

    def test_zero_mad_after_threshold_uses_nonzero_spread(self):
        from types import SimpleNamespace
        from core.ael_achf import display_detail_rings
        y,x=np.indices((128,128));r=np.hypot(x-64,y-64)
        d=np.zeros(r.shape);d[:,::8]=np.cos(y[:,::8])*10
        image,info=display_detail_rings(d,np.ones_like(d,bool),SimpleNamespace(radius_map=lambda:r),
                                      sparse_spread=True,noise_floor=1e-10)
        self.assertEqual(info['display'],'level and spread per ring')
        self.assertLess(np.mean((image==0)|(image==1)),.01)
        self.assertTrue(np.all(image[d==0]==.5))

    def test_statistics_exclusion_does_not_remove_radial_model_targets(self):
        case=OperatorLayerTests();case.setUp()
        support=np.ones(case.source.shape,bool);support[40:44,63:67]=False
        for name in ('fnrgf','rhef'):
            first=case.layer(name,statistics_mask=support)
            self.assertTrue(np.all(first['alpha'][40:44,63:67]>0))
            changed=case.source.copy();changed[40:44,63:67]*=10
            second=LayerEngine().layer(case.worker,changed,dict(case.p,statistics_mask=support),name)
            np.testing.assert_array_equal(first['image'][support],second['image'][support])
            self.assertTrue(np.any(first['image'][~support]!=second['image'][~support]))

if __name__=='__main__':
    unittest.main()
