"""Optional AEL ACHF bounded contrast: sign, saturation, compatibility and recipes."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from PySide6.QtWidgets import QApplication
from core.ael_achf import signed_detail_layer,ael_achf_layer
from core.filters import FilterWorker
from core.layer_engine import LayerEngine
from core.cancellation import ProcessingCancelled
from gui.app import EclipseProcessorApp
from gui.project_settings import capture_settings,restore_settings
from gui_wait import close_window


class ACHFBoundedTests(unittest.TestCase):
    def setUp(self):
        y,x=np.indices((256,256));self.r=np.hypot(x-128,y-128);self.theta=np.arctan2(y-128,x-128)
        self.mask=(np.hypot(x-135,y-124)>30)&(x<238)&(y>12)
        self.radial=(.05+np.maximum(self.r/30,1.)**-3).astype(np.float32)
        self.a=(self.radial*(1+.08*np.cos(5*self.theta))+np.random.default_rng(361).normal(0,.001,self.r.shape)).astype(np.float32)
        self.a[~self.mask]=np.nan
        self.signal=(.012*np.cos(12*self.theta)*np.exp(-((self.r-65)/12)**2)).astype(np.float32)
        self.p=dict(sx=128.,sy=128.,sr=30.,achf_str=100,achf_ael_scale=1.,statistics_exclude_lunar=True,
            achf_ael_parameters=dict(encoding='bounded',contrast=4.))

    def test_curve_formula_monotonicity_saturation_and_invalid_values(self):
        d=np.linspace(-1,1,4096).reshape(64,64);m=np.ones(d.shape,bool);m[0]=False;d[0]=np.nan
        q,info=signed_detail_layer(d,m,.05,4,curve='algebraic');z=4*d/(2.5*.05)
        np.testing.assert_allclose(q[m],(.5+.5*z/np.hypot(1,z))[m],atol=3e-8)
        changed,_=signed_detail_layer(d+.0001,m,.05,4,curve='algebraic')
        self.assertTrue(np.all(changed[m]>=q[m]));self.assertFalse(np.any((q[m]==0)|(q[m]==1)))
        tanh,_=signed_detail_layer(d,m,.05,4);self.assertTrue(np.any((tanh[m]==0)|(tanh[m]==1)))
        self.assertTrue(np.isnan(q[~m]).all());self.assertEqual(info['center'],0.)
        with self.assertRaises(ValueError):signed_detail_layer(d,m,.05,curve='invalid')
        for contrast in (0,4.1,np.nan,np.inf):
            with self.assertRaises(ValueError):ael_achf_layer(self.a,128,128,30,self.mask,parameters=dict(encoding='bounded',contrast=contrast))
        with self.assertRaises(ValueError):ael_achf_layer(self.a,128,128,30,self.mask,parameters=dict(encoding='invalid'))

    def test_revised_profile_and_injected_sign_for_all_ael_variants(self):
        region=self.mask&(self.r>48)&(self.r<82)&(abs(self.signal)>.006)
        for variant in ('ael_iso_01','ael_iso_04','ael_angular_4'):
            with self.subTest(variant=variant):
                contrast=2. if variant=='ael_iso_01' else 4.
                parameters=dict(encoding='bounded',contrast=contrast)
                first,info=ael_achf_layer(self.a,128,128,30,self.mask,variant=variant,parameters=parameters)
                changed,_=ael_achf_layer(self.a+self.signal,128,128,30,self.mask,variant=variant,parameters=parameters)
                delta=(changed-first)[region];truth=self.signal[region]
                self.assertLess(np.mean(delta*truth<0),.001);self.assertLess(np.mean(delta==0),.02)
                self.assertGreater(np.corrcoef(delta,truth)[0,1],.95)
                self.assertEqual(info['gain'],contrast);self.assertIn('operator_revision',info)
                if variant!='ael_angular_4':self.assertTrue(info['revised'])

    def test_masks_units_source_immutability_and_cancellation(self):
        before=self.a.copy();q,_=ael_achf_layer(self.a,128,128,30,self.mask,parameters=self.p['achf_ael_parameters'])
        poison=self.a.copy();poison[~self.mask]=1e20
        np.testing.assert_array_equal(q,ael_achf_layer(poison,128,128,30,self.mask,parameters=self.p['achf_ael_parameters'])[0])
        scaled,_=ael_achf_layer(self.a*7,128,128,30,self.mask,parameters=self.p['achf_ael_parameters'])
        np.testing.assert_allclose(q,scaled,atol=5e-5,equal_nan=True)
        np.testing.assert_array_equal(before,self.a)
        engine=LayerEngine();worker=FilterWorker()
        with patch('core.ael_achf.check_cancelled',side_effect=ProcessingCancelled):
            with self.assertRaises(ProcessingCancelled):engine.layer(worker,self.a,self.p,'achf','ael_iso_04')
        self.assertIsNone(engine.layer(worker,self.a,self.p,'achf','ael_iso_04',calculate=False))

    def test_cache_variant_isolation_global_policy_and_unused_contrast(self):
        worker=FilterWorker();engine=LayerEngine()
        with patch('core.ael_achf.ael_achf_layer',wraps=ael_achf_layer) as call:
            a=engine.layer(worker,self.a,self.p,'achf','ael_iso_04')
            same=engine.layer(worker,self.a,dict(self.p,normalization_mode='revised',achf_opacity=80),'achf','ael_iso_04')
            self.assertIs(a,same);self.assertEqual(call.call_count,1)
            engine.layer(worker,self.a,dict(self.p,achf_ael_parameters=dict(encoding='bounded',contrast=2.)),'achf','ael_iso_04')
            engine.layer(worker,self.a,self.p,'achf','ael_angular_4');self.assertEqual(call.call_count,3)
            p=dict(self.p,achf_ael_parameters=dict(encoding='normalization',contrast=1.))
            a=engine.layer(worker,self.a,p,'achf','ael_iso_04')
            same=engine.layer(worker,self.a,dict(p,achf_ael_parameters=dict(encoding='normalization',contrast=4.)),'achf','ael_iso_04')
            self.assertIs(a,same);self.assertEqual(call.call_count,4)

    def test_psb_recipe_and_tiff_pixel_equality(self):
        from core.layer_package import build_layer_package
        from core.psb_export import export_psb_layers,verify_psb_document
        from core.export import export_images
        import tifffile,json
        p=dict(self.p,achf_enabled=True,achf_variants={'adaptive':dict(enabled=False),'ael_iso_04':dict(enabled=True,opacity=10,encoding='bounded',contrast=4.)})
        worker=FilterWorker();package=build_layer_package(worker,self.a,p,{},'synthetic.fits')
        row=next(v for v in package.recipe['layers'] if v['filter']=='achf');self.assertEqual(row['normalization']['gain'],4.)
        self.assertEqual(row['normalization']['display'],'bounded signed algebraic contrast')
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp);export_psb_layers(package,path/'bounded.psb');verify_psb_document(path/'bounded.psb',package)
            export_images(self.a,p,{},str(path/'bounded.tif'),'synthetic.fits',export_layers=True,layer_cache=worker.layer_engine)
            recipe=json.loads((path/'bounded_PS_layers/recipe.json').read_text())
            np.testing.assert_array_equal(tifffile.imread(path/'bounded.tif'),tifffile.imread(path/'bounded_PS_layers'/recipe['combined']))


class ACHFBoundedGUI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])

    def test_per_variant_settings_basic_visibility_and_legacy_defaults(self):
        w=EclipseProcessorApp();w.auto_calculate=False
        try:
            a=np.ones((256,256),np.float32);w.full_raw_image=w.raw_image=w.preview_image=a
            for name,controls in w.achf_ael_controls.items():
                self.assertEqual(controls['encoding'].currentData(),'normalization');self.assertFalse(controls['contrast'].isEnabled())
            iso=w.achf_ael_controls['ael_iso_04'];iso['encoding'].setCurrentIndex(1);iso['contrast'].setValue(25)
            saved=capture_settings(w);restore_settings(w,saved)
            p=w.collect_filter_parameters(a.shape)
            self.assertEqual(p['achf_variants']['ael_iso_04']['encoding'],'bounded');self.assertEqual(p['achf_variants']['ael_iso_04']['contrast'],2.5)
            self.assertEqual(w.achf_ael_controls['ael_angular_4']['encoding'].currentData(),'normalization')
            for level in (1,2,0):
                w.ui_level.setCurrentIndex(level);self.assertFalse(iso['encoding'].isHidden());self.assertFalse(iso['contrast'].parameter_row.isHidden());self.assertTrue(iso['contrast'].isEnabled())
            saved['controls']={key:value for key,value in saved['controls'].items() if not key.endswith(('.encoding','.contrast'))}
            restore_settings(w,saved);self.assertEqual(iso['encoding'].currentData(),'normalization');self.assertEqual(iso['contrast'].value(),40)
        finally:close_window(w)
