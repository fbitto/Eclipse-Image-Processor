"""Revised normalization controls: no annular sign feedback, no compatibility drift."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
from types import SimpleNamespace
import tempfile,unittest
from unittest.mock import patch
import numpy as np
from PySide6.QtWidgets import QApplication
from core.ael_achf import signed_detail_layer,radial_log_residual,ael_achf_layer
from core.continuous_fnrgf import continuous_fnrgf
from core.filters import FilterWorker
from core.layer_engine import LayerEngine
from core.cancellation import ProcessingCancelled
from core.parallelism import filter_budget
from gui.app import EclipseProcessorApp
from gui.project_settings import capture_settings,restore_settings
from gui_wait import close_window


class RevisedNormalizationTests(unittest.TestCase):
    def setUp(self):
        self.y,self.x=np.indices((256,256));self.r=np.hypot(self.x-128,self.y-128)
        self.valid=(np.hypot(self.x-135,self.y-124)>30)&(self.x<238)&(self.y>12)
        self.radial=(.05+np.maximum(self.r/30,1)**-3).astype(np.float32)
        self.signal=(.012*np.cos(12*np.arctan2(self.y-128,self.x-128))*np.exp(-((self.r-65)/12)**2)).astype(np.float32)
        self.base=(self.radial*(1+.08*np.cos(5*np.arctan2(self.y-128,self.x-128)))+np.random.default_rng(908).normal(0,.001,self.r.shape)).astype(np.float32)
        self.base[~self.valid]=np.nan
        self.p=dict(sx=128.,sy=128.,sr=30.,normalization_mode='revised',achf_ael_scale=1.,nrgf_scale=1.,spatial_scale=1.,
            statistics_exclude_lunar=True,achf_str=100,achf_kernel=19,achf_threshold=10,achf_threshold_mode='relative',achf_boost=20,
            tangential_str=100,tangential_arc=3.,tangential_denoise=0.,tangential_inner=1.,tangential_outer=0.,tangential_fade=0.,tangential_gain=1.,
            fnrgf_str=100,fnrgf_mode='continuous',fnrgf_ord=8,fnrgf_seg=32,fnrgf_cut=0,fnrgf_rad=10,fnrgf_rmax=50,fnrgf_nbins=30,
            fnrgf_width_func='std',fnrgf_radial_binning='linear',fnrgf_smooth=8.,fnrgf_fade=0.,layer_display=dict(normalization_range=[.04,1.1]))

    def layer(self,a,name,variant=None,params=None):
        return LayerEngine().layer(FilterWorker(),a,params or self.p,name,variant)

    def test_fixed_signed_mapping_monotonic_gain_units_and_invalid_data(self):
        a=np.linspace(-1,1,4096).reshape(64,64);m=np.ones(a.shape,bool);m[:3]=False;a[~m]=np.nan
        q,receipt=signed_detail_layer(a,m,.1,2)
        b,_=signed_detail_layer(a+.0001,m,.1,2)
        self.assertTrue(np.all(b[m]>=q[m]));self.assertTrue(np.isnan(q[~m]).all())
        np.testing.assert_allclose(q,signed_detail_layer(a*7,m,.7,2)[0],atol=1e-7,equal_nan=True)
        self.assertTrue(receipt['gain_inside_tanh'])
        for scale in (0,-1,np.nan):
            with self.assertRaises(ValueError):signed_detail_layer(a,m,scale)
        with self.assertRaises(ValueError):signed_detail_layer(a,np.ones((1,64)),.1)

    def test_injected_detail_signs_across_variants_and_noise_seeds(self):
        region=self.valid&(self.r>48)&(self.r<82)&(abs(self.signal)>.006)
        for seed in (908,731):
            a=self.base.copy()
            if seed!=908:a[self.valid]+=np.random.default_rng(seed).normal(0,.0005,self.valid.sum())
            for family,variant in [('tangential',None),('achf','adaptive'),('achf','ael_iso_01'),('achf','ael_iso_04'),('achf','ael_angular_4')]:
                with self.subTest(seed=seed,family=family,variant=variant):
                    p=dict(self.p,achf_variant=variant or 'adaptive')
                    b=self.layer(a,family,variant,p);c=self.layer(a+self.signal,family,variant,p)
                    common=region&(b['alpha']>64879)&(c['alpha']>64879)
                    response=(c['image'].astype(float)-b['image'])[common];truth=self.signal[common]
                    self.assertLess(np.mean(response*truth<0),.001)
                    self.assertLess(np.mean(response==0),.02)
                    self.assertGreater(np.corrcoef(response,truth)[0,1],.95)
                    self.assertFalse(c['alpha'][~self.valid].any())

    def test_radial_profile_power_law_endpoints_and_exclusion(self):
        r=self.r.astype(np.float32);valid=self.valid&(r>0)
        a=np.maximum(r/30,1e-6)**-3;a[~valid]=np.nan
        geometry=SimpleNamespace(sun_radius_px=30.,radius_map=lambda:r)
        residual,info=radial_log_residual(a,valid,geometry,revised=True)
        self.assertLess(np.nanpercentile(abs(residual),99),.002)
        bad=a.copy();bad[~valid]=1e20
        np.testing.assert_array_equal(residual,radial_log_residual(bad,valid,geometry,revised=True)[0])
        self.assertTrue(info['revised'])
        for variant in ('ael_iso_01','ael_iso_04'):
            q,_=ael_achf_layer(np.where(valid,self.radial,np.nan),128,128,30,valid,variant=variant,revised=True)
            self.assertLess(np.nanstd(q),.003)

    def test_fnrgf_cubic_improves_null_and_is_unit_thread_invariant(self):
        a=np.where(self.valid,self.radial,np.nan);theta=np.arctan2(self.y-128,self.x-128);edges=np.linspace(30,150,31)
        kw=dict(order=8,segments=32,valid=self.valid,target_valid=self.valid,smooth_px=8.,revised=True)
        with filter_budget(1):q=continuous_fnrgf(a,self.r,theta,edges,**kw)
        with filter_budget(4):parallel=continuous_fnrgf(a,self.r,theta,edges,**kw)
        np.testing.assert_array_equal(q,parallel)
        scaled=continuous_fnrgf(a*1e12,self.r,theta,edges,**kw)
        np.testing.assert_allclose(q,scaled,atol=1e-4,equal_nan=True)
        old=continuous_fnrgf(a,self.r,theta,edges,**dict(kw,revised=False))
        common=np.isfinite(q)&np.isfinite(old)&(self.r>35)&(self.r<120)
        self.assertLess(np.std(q[common]),.7*np.std(old[common]))
        self.assertTrue(np.isnan(q[~self.valid]).all())

    def test_linear_reference_units_and_invalid_bounds(self):
        first=self.layer(self.base,'tangential')
        p=dict(self.p,layer_display=dict(normalization_range=[.04*7,1.1*7]))
        scaled=self.layer(self.base*7,'tangential',params=p)
        np.testing.assert_allclose(first['image'].astype(float)/65535,scaled['image']/65535,atol=5e-5)
        np.testing.assert_array_equal(first['alpha'],scaled['alpha'])
        for bounds in ([1,0],[0,np.inf],[1]):
            with self.assertRaises(ValueError):self.layer(self.base,'tangential',params=dict(self.p,layer_display=dict(normalization_range=bounds)))

    def test_unaffected_nafe_reuses_cache_across_normalization_choices(self):
        from core.ael_nafe import nafe_layer
        with np.load(Path(__file__).parent/'fixtures/ael_nafe_142.npz') as fixture:a=fixture['image']
        p=dict(sx=20.,sy=16.,sr=3.,nafe_sigma=.04,nafe_window=9)
        engine=LayerEngine();worker=FilterWorker()
        with patch('core.ael_nafe.nafe_layer',wraps=nafe_layer) as call:
            original=engine.layer(worker,a,p,'nafe')
            same=engine.layer(worker,a,dict(p,normalization_mode='revised'),'nafe')
            self.assertIs(original,same)
            self.assertEqual(call.call_count,1)

    def test_cache_policy_cancellation_and_original_fixtures(self):
        worker=FilterWorker();engine=LayerEngine()
        with patch('core.ael_achf.ael_achf_layer',wraps=ael_achf_layer) as call:
            p=dict(self.p,normalization_mode='compatible')
            original=engine.layer(worker,self.base,p,'achf','ael_iso_04')
            revised=engine.layer(worker,self.base,self.p,'achf','ael_iso_04')
            engine.layer(worker,self.base,dict(self.p,achf_opacity=50),'achf','ael_iso_04')
            self.assertEqual(call.call_count,2)
            self.assertFalse(np.array_equal(original['image'],revised['image']))
        with patch('core.ael_achf.check_cancelled',side_effect=ProcessingCancelled):
            with self.assertRaises(ProcessingCancelled):self.layer(self.base,'achf','ael_iso_04')
        with self.assertRaises(ValueError):self.layer(self.base,'achf','ael_iso_04',dict(self.p,normalization_mode='invalid'))


class RevisedNormalizationGUI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])

    def test_policy_settings_legacy_reset_and_export_receipt(self):
        w=EclipseProcessorApp();w.auto_calculate=False
        try:
            a=np.ones((256,256),np.float32);w.full_raw_image=w.raw_image=w.preview_image=a
            self.assertEqual(w.combo_normalization_mode.currentData(),'compatible')
            w.combo_normalization_mode.setCurrentIndex(1);saved=capture_settings(w);restore_settings(w,saved)
            p=w.collect_filter_parameters(a.shape)
            self.assertEqual(p['normalization_mode'],'revised')
            for level in (1,2,0):
                w.ui_level.setCurrentIndex(level)
                self.assertEqual(w.combo_normalization_mode.currentData(),'revised')
                self.assertEqual(w.combo_normalization_mode.isHidden(),level==0)
                self.assertEqual(w.filter_settings_layout.parentWidget().parentWidget().isHidden(),level==0)
            saved['controls'].pop('combo_normalization_mode');restore_settings(w,saved)
            self.assertEqual(w.combo_normalization_mode.currentData(),'compatible')
            from core.layer_package import build_layer_package
            from core.psb_export import export_psb_layers,verify_psb_document
            p.update(achf_enabled=True,achf_variants={'ael_iso_04':dict(enabled=True,opacity=10)},normalization_mode='revised')
            for name in ('nrgf','nafe','fnrgf','rhef','mgn','wow','tangential','larson_sekanina'):p[name+'_enabled']=False
            y,x=np.indices(a.shape);source=(1+np.exp(-np.hypot(x-128,y-128)/50)).astype(np.float32)
            p.update(sx=128.,sy=128.,sr=30.)
            package=build_layer_package(FilterWorker(),source,p,{},'synthetic.fits')
            record=next(v for v in package.recipe['layers'] if v['filter']=='achf')
            self.assertIn('normalization_revision',record['normalization'])
            with tempfile.TemporaryDirectory() as tmp:
                path=Path(tmp)/'revised.psb';export_psb_layers(package,path);verify_psb_document(path,package)
        finally:close_window(w)
