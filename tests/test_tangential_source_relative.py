"""Source-relative Tangential contrast: empirical reference, units, masks and integration."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from PySide6.QtWidgets import QApplication
from core.tangential_encoding import source_relative_detail
from core.filters import FilterWorker
from core.layer_engine import LayerEngine
from core.cancellation import ProcessingCancelled
from gui.app import EclipseProcessorApp
from gui.project_settings import capture_settings,restore_settings
from gui_wait import close_window


class SourceRelativeTests(unittest.TestCase):
    def setUp(self):
        self.y,self.x=np.indices((256,256));self.r=np.hypot(self.x-128,self.y-128)
        self.m=(self.r>25)&(self.x<240)&(self.y>10)
        self.a=(.05+np.maximum(self.r/25,1.)**-3+np.random.default_rng(73).normal(0,.001,self.r.shape)).astype(np.float32)
        self.a[~self.m]=np.nan
        self.detail=(.002*np.cos(8*np.arctan2(self.y-128,self.x-128))*np.exp(-((self.r-80)/15)**2)).astype(np.float32)
        self.p=dict(sx=128.,sy=128.,sr=25.,tangential_enabled=True,tangential_str=100,tangential_arc=3.,tangential_gain=1.,tangential_denoise=0.,tangential_inner=1.,tangential_outer=0.,tangential_fade=0.,tangential_encoding='source_relative',tangential_opacity=10,statistics_exclude_lunar=True,nrgf_scale=1.)

    def encode(self,a=None,detail=None,samples=None,targets=None,**kwargs):
        return source_relative_detail(self.detail if detail is None else detail,self.a if a is None else a,self.m if samples is None else samples,self.m if targets is None else targets,128.,128.,25.,**kwargs)

    def test_matches_frozen_research_formula_and_unit_scaling(self):
        from scipy.ndimage import gaussian_filter1d
        q,info=self.encode();bins=np.floor(self.r).astype(int);counts=np.bincount(bins[self.m]);sums=np.bincount(bins[self.m],weights=abs(self.a[self.m].astype(float)))
        indices=np.flatnonzero(counts>=12);profile=np.interp(np.arange(len(counts)),indices,sums[indices]/counts[indices]);log=gaussian_filter1d(np.log(profile),2.5)
        model=np.exp(np.interp(self.r,np.arange(len(counts)),log)).astype(np.float32)
        delta=np.diff(self.a.astype(float),axis=1)[self.m[:,1:]&self.m[:,:-1]];noise=float(1.4826*np.median(abs(delta-np.median(delta)))/np.sqrt(2))
        scale=np.maximum(.05*model,max(3*noise,np.finfo(np.float32).tiny));z=self.detail.astype(float)/(2.5*scale)
        expected=.5+.5*z/np.hypot(1.,z)
        np.testing.assert_allclose(q[self.m],expected[self.m],atol=1e-7)
        self.assertTrue(info['noise_fallback'])
        scaled,_=self.encode(a=self.a*7,detail=self.detail*7)
        np.testing.assert_allclose(q,scaled,atol=2e-6,equal_nan=True)
        self.assertTrue(np.isnan(q[~self.m]).all())

    def test_excluded_samples_immutability_missing_data_and_zero_gain(self):
        before=self.a.copy();q,_=self.encode()
        poisoned=self.a.copy();poisoned[~self.m]=1e20
        np.testing.assert_array_equal(q,self.encode(a=poisoned)[0])
        np.testing.assert_array_equal(before,self.a)
        reference=self.m&(self.x<210);q,_=self.encode(samples=reference)
        altered=self.a.copy();altered[self.m&~reference]*=100
        changed,_=self.encode(a=altered,samples=reference)
        np.testing.assert_array_equal(q,changed)
        flat,receipt=self.encode(gain=0.)
        np.testing.assert_array_equal(flat[self.m],.5);self.assertEqual(receipt['bypass'],'zero gain')
        zero,_=self.encode(a=np.where(self.m,1.,np.nan),detail=np.zeros(self.a.shape,np.float32))
        np.testing.assert_array_equal(zero[self.m],.5)

    def test_errors_cancellation_and_far_field_receipt(self):
        for kwargs in ({'gain':-1},{'gain':6}):
            with self.assertRaises(ValueError):self.encode(**kwargs)
        with self.assertRaises(ValueError):source_relative_detail(self.detail,self.a,self.m,np.ones((2,2)),128,128,25)
        with self.assertRaises(ValueError):self.encode(samples=np.zeros_like(self.m))
        with patch('core.tangential_encoding.check_cancelled',side_effect=ProcessingCancelled):
            with self.assertRaises(ProcessingCancelled):self.encode()
        y,x=np.indices((512,512));r=np.hypot(x-256,y-256);m=r>25
        a=np.where(m,1.+np.random.default_rng(8).normal(0,.001,r.shape),np.nan).astype(np.float32)
        _,receipt=source_relative_detail(np.zeros_like(a),a,m,m,256,256,25)
        self.assertFalse(receipt['noise_fallback']);self.assertGreater(receipt['noise_pairs'],64)

    def test_only_output_encoding_changes_and_cache_ignores_global_policy(self):
        engine=LayerEngine();worker=FilterWorker()
        with patch('core.tangential_encoding.source_relative_detail',wraps=source_relative_detail) as call:
            first=engine.layer(worker,self.a,self.p,'tangential')
            same=engine.layer(worker,self.a,dict(self.p,normalization_mode='revised',tangential_opacity=80),'tangential')
            self.assertIs(first,same);self.assertEqual(call.call_count,1)
        original=LayerEngine().layer(worker,self.a,dict(self.p,tangential_encoding='normalization'),'tangential')
        np.testing.assert_array_equal(first['alpha'],original['alpha'])
        self.assertEqual(first['mapping']['source_reference'],'allowed observed source, not filtered-layer statistics')
        with self.assertRaises(ValueError):engine.layer(worker,self.a,dict(self.p,tangential_encoding='unknown'),'tangential')
        engine=LayerEngine()
        with patch('core.tangential_encoding.check_cancelled',side_effect=ProcessingCancelled):
            with self.assertRaises(ProcessingCancelled):engine.layer(worker,self.a,self.p,'tangential')
        self.assertIsNone(engine.layer(worker,self.a,self.p,'tangential',calculate=False))

    def test_layer_package_psb_and_tiff_use_same_mapping(self):
        from core.layer_package import build_layer_package
        from core.psb_export import export_psb_layers,verify_psb_document
        from core.export import export_images
        import tifffile,json
        worker=FilterWorker();package=build_layer_package(worker,self.a,self.p,{},'synthetic.fits')
        row=next(v for v in package.recipe['layers'] if v['filter']=='tangential')
        self.assertEqual(row['normalization']['display'],'source-relative signed algebraic contrast')
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);export_psb_layers(package,folder/'tangential.psb');verify_psb_document(folder/'tangential.psb',package)
            export_images(self.a,self.p,{},str(folder/'tangential.tif'),'synthetic.fits',export_layers=True,layer_cache=worker.layer_engine)
            recipe=json.loads((folder/'tangential_PS_layers/recipe.json').read_text())
            np.testing.assert_array_equal(tifffile.imread(folder/'tangential.tif'),tifffile.imread(folder/'tangential_PS_layers'/recipe['combined']))


class SourceRelativeGUI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])

    def test_selector_preservation_legacy_default_and_inactive_change(self):
        w=EclipseProcessorApp();w.auto_calculate=False
        try:
            a=np.ones((256,256),np.float32);w.full_raw_image=w.raw_image=w.preview_image=a
            w.ui_level.setCurrentIndex(1)
            self.assertEqual(w.combo_tangential_encoding.currentData(),'normalization')
            self.assertFalse(w.combo_tangential_encoding.isHidden())
            w.combo_tangential_encoding.setCurrentIndex(1);saved=capture_settings(w);restore_settings(w,saved)
            self.assertEqual(w.collect_filter_parameters(a.shape)['tangential_encoding'],'source_relative')
            for level in (2,0,1):
                w.ui_level.setCurrentIndex(level)
                self.assertEqual(w.combo_tangential_encoding.currentData(),'source_relative')
            self.assertFalse(w.combo_tangential_encoding.isHidden())
            saved['controls'].pop('combo_tangential_encoding');restore_settings(w,saved)
            self.assertEqual(w.combo_tangential_encoding.currentData(),'normalization')
        finally:close_window(w)
