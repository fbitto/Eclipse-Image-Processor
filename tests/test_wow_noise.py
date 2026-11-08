"""Opt-in AEL WOW coefficient suppression: detail, support and integration."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from scipy.ndimage import gaussian_filter
from PySide6.QtWidgets import QApplication
from core.ael_wow import ael_wow_layer, wow_edge_aware
from core.cancellation import ProcessingCancelled
from core.filters import FilterWorker
from core.layer_engine import LayerEngine
from core.pipeline import prepare_parameters
from gui.app import EclipseProcessorApp
from gui.project_settings import capture_settings, restore_settings
from gui_wait import close_window


class WOWNoiseTests(unittest.TestCase):
    def setUp(self):
        y,x=np.indices((256,256));self.x=x;self.y=y
        self.r=np.hypot(x-128,y-128);self.m=self.r>30
        self.base=(1+.3*np.exp(-self.r/55)).astype(np.float32)
        self.signal=(.15*np.exp(-((x-120)/3)**2)*np.exp(-((y-75)/40)**2)).astype(np.float32)
        self.a=(self.base+self.signal+np.random.default_rng(94).normal(0,.006,self.base.shape)).astype(np.float32)
        self.a[~self.m]=np.nan
        self.p=dict(sx=128,sy=128,sr=30,wow_scales=4,wow_mode='ael_bilateral',wow_enabled=True,wow_opacity=100,wow_native_scales=True)
        self.sky=self.m&(self.r>110)&(x>160)
        self.stream=self.m&(abs(x-120)<2)&(y>45)&(y<90)

    def test_zero_parity_noise_reduction_and_injected_streamer(self):
        before=self.a.copy();q,old=ael_wow_layer(self.a,self.p,self.m)
        bypass,_=ael_wow_layer(self.a,dict(self.p,wow_noise_reduction=0),self.m)
        np.testing.assert_array_equal(q,bypass)
        b,info=ael_wow_layer(self.a,dict(self.p,wow_noise_reduction=2),self.m)
        self.assertLess(np.std(b[self.sky]),.4*np.std(q[self.sky]))
        self.assertGreater(np.median(b[self.stream]-.5),.85*np.median(q[self.stream]-.5))
        np.testing.assert_array_equal(np.isfinite(b),np.isfinite(q))
        np.testing.assert_array_equal(before,self.a)
        self.assertEqual(info['scale'],old['scale'])
        self.assertEqual(len(info['noise_estimates']),4)
        self.assertTrue(all(v['samples']>=64 for v in info['noise_estimates']))

    def test_correlated_noise_units_masks_and_flat_null(self):
        correlated=gaussian_filter(np.random.default_rng(14).normal(size=self.a.shape),1.)
        a=(self.base+self.signal+.02*correlated).astype(np.float32);a[~self.m]=np.nan
        p=dict(self.p,wow_noise_reduction=2)
        q,_=ael_wow_layer(a,self.p,self.m);b,_=ael_wow_layer(a,p,self.m)
        self.assertLess(np.std(b[self.sky]),np.std(q[self.sky]))
        scaled,_=ael_wow_layer(a*7,p,self.m)
        np.testing.assert_allclose(b,scaled,atol=.001,equal_nan=True)
        poisoned=a.copy();poisoned[~self.m]=1e15
        np.testing.assert_array_equal(b,ael_wow_layer(poisoned,p,self.m)[0])
        flat=np.ones_like(a);flat[~self.m]=np.nan
        output,receipt=ael_wow_layer(flat,p,self.m)
        np.testing.assert_allclose(output[self.m],.5,atol=1e-7)
        self.assertTrue(all(v['sigma']==0 for v in receipt['noise_estimates']))
        partial=self.m&(self.x<225)&(self.y>25)
        output,receipt=ael_wow_layer(a,p,partial)
        np.testing.assert_array_equal(np.isfinite(output),partial)
        fallback,_=ael_wow_layer(a,dict(p,sr=100),self.m)
        self.assertTrue(np.isfinite(fallback[self.m]).all())

    def test_faint_injection_thread_parity_and_reference_anchor(self):
        from core.parallelism import filter_budget
        noise=np.random.default_rng(94).normal(0,.006,self.a.shape)
        shape=np.exp(-((self.x-120)/3)**2)*np.exp(-((self.y-75)/40)**2)
        inputs=[(self.base+noise).astype(np.float32),(self.base+noise+.01*shape).astype(np.float32)]
        contrasts=[]
        for strength in (0,1):
            outputs=[]
            for a in inputs:
                a[~self.m]=np.nan
                outputs.append(ael_wow_layer(a,dict(self.p,wow_noise_reduction=strength),self.m)[0])
            contrasts.append(np.median((outputs[1]-outputs[0])[self.stream]))
        self.assertGreater(contrasts[1]/contrasts[0],.8)
        with filter_budget(1):
            serial,baseline,_=wow_edge_aware(self.a,self.m,n_scales=4,noise_reduction=2,return_reference=True)
            original=wow_edge_aware(self.a,self.m,n_scales=4)
        with filter_budget(4):
            parallel=wow_edge_aware(self.a,self.m,n_scales=4,noise_reduction=2)
        np.testing.assert_array_equal(serial,parallel)
        np.testing.assert_array_equal(original,baseline)

    def test_validation_cancellation_cache_and_export(self):
        p=dict(self.p,wow_noise_reduction=2,valid_mask=self.m)
        for value in (-1,6,np.nan,np.inf):
            with self.assertRaises(ValueError):ael_wow_layer(self.a,dict(p,wow_noise_reduction=value),self.m)
        with self.assertRaises(ValueError):wow_edge_aware(self.a,self.m,noise_reduction=1,noise_valid=np.ones((2,2)))
        with self.assertRaisesRegex(ValueError,'64 fully supported'):
            wow_edge_aware(np.ones((8,8),np.float32),np.ones((8,8),bool),n_scales=1,noise_reduction=1)
        worker=FilterWorker();engine=LayerEngine()
        with patch('core.ael_wow.check_cancelled',side_effect=ProcessingCancelled):
            with self.assertRaises(ProcessingCancelled):engine.layer(worker,self.a,p,'wow')
        with patch('core.ael_wow.ael_wow_layer',wraps=ael_wow_layer) as operator:
            engine.layer(worker,self.a,p,'wow')
            engine.layer(worker,self.a,dict(p,wow_opacity=50),'wow')
            engine.layer(worker,self.a,dict(p,wow_noise_reduction=1),'wow')
            self.assertEqual(operator.call_count,2)
        from core.layer_package import build_layer_package
        from core.psb_export import export_psb_layers,verify_psb_document
        from core.export import export_images
        import tifffile,json
        package=build_layer_package(worker,self.a,p,{},'synthetic.fits')
        row=next(v for v in package.recipe['layers'] if v['filter']=='wow')
        self.assertEqual(row['normalization']['noise_reduction'],2)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)
            export_psb_layers(package,path/'wow.psb');verify_psb_document(path/'wow.psb',package)
            export_images(self.a,p,{},str(path/'wow.tif'),'synthetic.fits',layer_cache=worker.layer_engine,export_layers=True)
            recipe=json.loads((path/'wow_PS_layers/recipe.json').read_text())
            np.testing.assert_array_equal(tifffile.imread(path/'wow.tif'),tifffile.imread(path/'wow_PS_layers'/recipe['combined']))
        prepared=prepare_parameters(p,self.a.shape,(128,128),(128,128))
        self.assertEqual(prepared['wow_noise_reduction'],2)
        self.assertEqual(prepared['wow_scales'],3)


class WOWNoiseGUI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])

    def test_basic_visibility_persistence_legacy_default_and_backend(self):
        w=EclipseProcessorApp();w.auto_calculate=False
        try:
            a=np.ones((256,256),np.float32);w.full_raw_image=w.raw_image=w.preview_image=a
            self.assertEqual(w.sl_wow_noise_reduction.value(),0)
            self.assertFalse(w.sl_wow_noise_reduction.parameter_row.isHidden())
            self.assertTrue(w.sl_wow_noise_reduction.isEnabled())
            w.sl_wow_noise_reduction.setValue(20)
            saved=capture_settings(w);restore_settings(w,saved)
            self.assertEqual(w.collect_filter_parameters(a.shape)['wow_noise_reduction'],2)
            for mode in (1,2,0):
                w.ui_level.setCurrentIndex(mode)
                self.assertEqual(w.sl_wow_noise_reduction.value(),20)
                self.assertFalse(w.sl_wow_noise_reduction.parameter_row.isHidden())
            w.ui_level.setCurrentIndex(2);w.combo_wow_bilateral.setCurrentIndex(0)
            self.assertFalse(w.sl_wow_noise_reduction.isEnabled())
            saved['controls'].pop('sl_wow_noise_reduction');restore_settings(w,saved)
            self.assertEqual(w.sl_wow_noise_reduction.value(),0)
        finally:close_window(w)
