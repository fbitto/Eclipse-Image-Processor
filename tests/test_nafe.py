"""AEL NAFE parity, known-truth controls and independent GUI/export integration."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import tempfile
from threading import Event, Lock, current_thread, enumerate as threads
import unittest
from unittest.mock import patch

import numpy as np
from scipy.special import ndtr
import tifffile
from PySide6.QtWidgets import QApplication

from core.ael_nafe import nafe, nafe_neighbourhood, nafe_layer, nafe_noise_sigma, _level_results
from core.cancellation import cancellation_scope, ProcessingCancelled
from core.filters import FilterWorker
from core.layer_engine import LayerEngine, requests
from core.parallelism import filter_budget, filter_cpu_budget
from core.pipeline import prepare_parameters, apply_filter
from core.progress import progress_scope
from gui.app import EclipseProcessorApp
from gui.project_settings import capture_settings, restore_settings
from gui_wait import close_window


class NAFETests(unittest.TestCase):
    def setUp(self):
        with np.load(Path(__file__).parent/'fixtures/ael_nafe_142.npz') as f:
            self.a=f['image'];self.m=f['valid'];self.expected=f['expected']
        self.p=dict(sx=20.,sy=16.,sr=3.,nafe_enabled=True,nafe_str=100,
                    nafe_sigma=.04,nafe_window=9,nafe_opacity=28,valid_mask=self.m)

    def test_upstream_oracle_support_and_input_immutability(self):
        before=self.a.copy()
        actual,info=nafe(self.a,self.m,.04,n=9)
        np.testing.assert_allclose(actual,self.expected,atol=2e-6,equal_nan=True)
        np.testing.assert_array_equal(self.a,before)
        self.assertTrue(np.isnan(actual[~self.m]).all())
        changed=self.a.copy();changed[~self.m]=1e30
        np.testing.assert_array_equal(nafe(changed,self.m,.04,n=9)[0],actual)
        self.assertEqual(info['centre_normalization'],1)
        self.assertEqual(len(info['internal_sigmas_target_px']),12)
        self.assertAlmostEqual(nafe_neighbourhood(9)[4,4],1.)

    def test_matches_direct_fuzzy_cdf_without_reflected_boundary_samples(self):
        a=np.arange(20,dtype=np.float32).reshape(4,5)/20
        m=np.ones(a.shape,bool);m[1,2]=False
        actual,_=nafe(a,m,.2,n=3)
        kernel=nafe_neighbourhood(3)
        for y,x in zip(*np.nonzero(m)):
            total=weight=0.
            for yy in range(max(0,y-1),min(a.shape[0],y+2)):
                for xx in range(max(0,x-1),min(a.shape[1],x+2)):
                    if m[yy,xx]:
                        w=kernel[yy-y+1,xx-x+1]
                        total+=w*ndtr((float(a[y,x])-float(a[yy,xx]))/.2);weight+=w
            # AEL interpolates at sigma/2: the Gaussian-CDF curvature bounds error by 0.008.
            self.assertAlmostEqual(float(actual[y,x]),total/weight,delta=.008)

    def test_constant_empty_nonfinite_and_invalid_parameters(self):
        for factor in (1e-20,1.,1e20):
            q,_=nafe(np.ones((8,9),np.float32)*factor,None,.1*factor,n=9)
            np.testing.assert_allclose(q,.5,atol=1e-6)
        q,info=nafe(self.a,np.zeros_like(self.m),.04,n=9)
        self.assertTrue(np.isnan(q).all());self.assertTrue(info['undefined'])
        a=self.a.copy();a[4,4]=np.inf
        self.assertTrue(np.isnan(nafe(a,None,.04,n=9)[0][4,4]))
        for kw in (dict(sigma=0),dict(sigma=-1),dict(sigma=np.inf),dict(sigma=np.nan),
                   dict(n=4),dict(n=0),dict(n=True),dict(n=3.5),dict(level_step=0),dict(level_step=np.nan),
                   dict(target_valid=np.ones((1,1),bool))):
            args=dict(sigma=.04,n=9);args.update(kw)
            with self.subTest(parameters=kw),self.assertRaises(ValueError):nafe(self.a,self.m,**args)
        with self.assertRaises(ValueError):nafe(self.a,np.ones((1,1),bool),.04,n=9)

    def test_intensity_units_pedestal_and_parallel_jobs(self):
        q,_=nafe(self.a,self.m,.04,n=9)
        for factor in (1e-20,1e20):
            scaled,_=nafe(self.a*factor,self.m,.04*factor,n=9)
            np.testing.assert_allclose(q,scaled,atol=2e-6,equal_nan=True)
        shifted,_=nafe(self.a+32,self.m,.04,n=9)
        np.testing.assert_allclose(q,shifted,atol=2e-5,equal_nan=True)
        def calculate(sigma):return nafe(self.a,self.m,sigma,n=9)[0]
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(calculate,(.04,.08)))
        np.testing.assert_array_equal(results[0],q)
        np.testing.assert_array_equal(results[1],calculate(.08))

    def test_noise_estimate_records_region_and_fallback_in_matching_units(self):
        rng=np.random.default_rng(735)
        a=rng.normal(1,.01,(96,96)).astype(np.float32);m=np.ones(a.shape,bool)
        sigma,info=nafe_noise_sigma(a,m,48,48,8)
        self.assertGreater(sigma,0)
        self.assertTrue(info['noise_region_fallback']);self.assertGreater(info['noise_pixels'],64)
        self.assertIsNone(info['noise_fallback'])
        scaled,_=nafe_noise_sigma(a*1e-20,m,48,48,8)
        self.assertAlmostEqual(scaled/sigma,1e-20,delta=1e-24)
        sigma,info=nafe_noise_sigma(np.ones((8,8),np.float32),np.ones((8,8),bool),4,4,2)
        self.assertGreater(sigma,0);self.assertEqual(info['noise_fallback'],'input-relative numerical floor')
        with self.assertRaises(ValueError):nafe_noise_sigma(a,m,48,48,0)

    def test_known_gaussian_sign_wings_and_independent_noise_null(self):
        y,x=np.mgrid[:129,:129]
        a=(.5+.2*np.exp(-((x-64)**2+(y-64)**2)/(2*12**2))).astype(np.float32)
        q,_=nafe(a,None,.12,n=257)
        detail=q-.5
        self.assertGreater(detail[64,64],0)
        self.assertLess(-detail.min()/detail[64,64],.1)
        rng=np.random.default_rng(51)
        a=rng.normal(.5,.01,(96,96)).astype(np.float32)
        b=rng.normal(.5,.01,(96,96)).astype(np.float32)
        qa,_=nafe(a,None,.12,n=65);qb,_=nafe(b,None,.12,n=65)
        self.assertLess(abs(np.corrcoef(qa.ravel(),qb.ravel())[0,1]),.1)

    def test_cache_mask_changes_and_opacity_only_recomposition(self):
        engine=LayerEngine();worker=FilterWorker();before=self.a.copy()
        with patch('core.ael_nafe.nafe_layer',wraps=nafe_layer) as operator:
            first=engine.render(worker,self.a,self.p,{})
            layer=engine.layer(worker,self.a,self.p,'nafe')
            second=engine.render(worker,self.a,dict(self.p,nafe_opacity=80),{})
            self.assertEqual(operator.call_count,1)
            self.assertGreater(np.max(abs(first-second)),.001)
            engine.layer(worker,self.a,dict(self.p,nafe_sigma=.08),'nafe')
            mask=self.m.copy();mask[18:23,20:25]=False
            altered=engine.layer(worker,self.a,dict(self.p,statistics_mask=mask),'nafe')
            self.assertEqual(operator.call_count,3)
        self.assertFalse(altered['alpha'][~self.m].any())
        self.assertTrue(altered['alpha'][self.m & ~mask].any())
        self.assertEqual(layer['mode'],'Overlay')
        np.testing.assert_array_equal(self.a,before)
        p=dict(self.p,nrgf_enabled=True)
        engine.prepare(worker,self.a,p)
        np.testing.assert_array_equal(engine.layer(worker,self.a,p,'nafe')['image'],layer['image'])
        self.assertEqual([row[0] for row in requests(p)],['nrgf','nafe'])
        with self.assertRaisesRegex(ValueError,'independent layer composition'):apply_filter(worker,self.a,self.p)

    def test_observed_limb_targets_are_not_clipped_by_reference_circle(self):
        y,x=np.mgrid[:64,:64];r=np.hypot(x-32,y-32)
        a=(1+.2*np.cos(x/5)+.01*y).astype(np.float32)
        valid=r>9.;a[~valid]=np.nan
        p=dict(self.p,sx=32.,sy=32.,sr=12.,valid_mask=valid,statistics_exclude_lunar=True)
        layer=LayerEngine().layer(FilterWorker(),a,p,'nafe')
        rim=valid & (r<=12)
        self.assertTrue((layer['alpha'][rim]>0).all())
        self.assertFalse(layer['alpha'][~valid].any())
        samples=valid & (r>12)
        query=nafe(a,samples,.04,n=9,target_valid=valid)[0]
        old=nafe(a,samples,.04,n=9)[0]
        np.testing.assert_array_equal(query[samples],old[samples])
        b=a.copy();b[rim]*=10
        changed=nafe(b,samples,.04,n=9,target_valid=valid)[0]
        np.testing.assert_allclose(changed[samples],old[samples],atol=1e-6,equal_nan=True)
        self.assertGreater(np.nanmax(abs(changed[rim]-query[rim])),.01)

    def test_query_only_targets_need_real_neighbors_and_match_fuzzy_cdf(self):
        a=np.arange(49,dtype=np.float32).reshape(7,7)/49
        samples=np.ones(a.shape,bool);samples[3,3]=False
        q,_=nafe(a,samples,.2,n=3,target_valid=np.ones(a.shape,bool))
        kernel=nafe_neighbourhood(3);weights=kernel.copy();weights[1,1]=0
        expected=np.sum(weights*ndtr((float(a[3,3])-a[2:5,2:5])/.2))/weights.sum()
        self.assertAlmostEqual(float(q[3,3]),float(expected),delta=.008)
        baseline=nafe(a,samples,.2,n=3)[0]
        a[3,3]=-1.
        extended=nafe(a,samples,.2,n=3,target_valid=np.ones(a.shape,bool))[0]
        np.testing.assert_allclose(extended[samples],baseline[samples],atol=1e-6,equal_nan=True)
        self.assertLess(extended[3,3],.001)
        samples[:]=False;samples[0,0]=True
        q,_=nafe(a,samples,.2,n=3,target_valid=np.ones(a.shape,bool))
        self.assertTrue(np.isnan(q[3:,3:]).all())
        a[0,1]=np.nan
        self.assertTrue(np.isnan(nafe(a,samples,.2,n=3,target_valid=np.ones(a.shape,bool))[0][0,1]))

    def test_fft_budget_and_cancellation_never_cache_partial_results(self):
        from core import ael_nafe
        with filter_budget(1),patch('core.ael_nafe.sfft.rfft2',wraps=ael_nafe.sfft.rfft2) as fft:
            nafe(self.a,self.m,.04,n=9)
            self.assertTrue(all(call.kwargs['workers']==1 for call in fft.call_args_list))
        engine=LayerEngine();event=Event()
        with cancellation_scope(event,check_at_exit=False),progress_scope(lambda *_:event.set()):
            with self.assertRaises(ProcessingCancelled):engine.layer(FilterWorker(),self.a,self.p,'nafe')
        self.assertIsNone(engine.layer(FilterWorker(),self.a,self.p,'nafe',calculate=False))

    def test_two_levels_preserve_sparse_interpolation_and_memory_fallback(self):
        sparse=self.a.copy()
        sparse[self.m & (sparse>.6)]=20.
        for a in (self.a,sparse,np.ones_like(self.a)):
            with filter_budget(1):serial,first=nafe(a,self.m,.04,n=9)
            with filter_budget(4),patch('core.parallelism.physical_memory_bytes',return_value=8*1024**3):
                parallel,second=nafe(a,self.m,.04,n=9)
            self.assertEqual(first['level_workers'],1)
            self.assertEqual(second['level_workers'],2)
            self.assertEqual(first['convolutions'],second['convolutions'])
            np.testing.assert_array_equal(parallel,serial)
        with filter_budget(4),patch('core.parallelism.physical_memory_bytes',return_value=1):
            fallback,info=nafe(self.a,self.m,.04,n=9)
        self.assertEqual(info['level_workers'],1)
        with filter_budget(1):serial,_=nafe(self.a,self.m,.04,n=9)
        np.testing.assert_array_equal(fallback,serial)

    def test_level_buffer_is_bounded_and_partial_consumption_joins_workers(self):
        started=[];lock=Lock();two_started=Event()
        def level(position):
            with lock:
                started.append(position)
                if len(started)>=2:two_started.set()
            return position,filter_cpu_budget()
        with filter_budget(4),_level_results(level,range(20),2) as results:
            self.assertTrue(two_started.wait(2))
            self.assertEqual(len(started),2)
            self.assertEqual(next(results),(0,2))
            self.assertEqual(next(results),(1,2))
        self.assertLessEqual(len(started),3)
        self.assertFalse(any(t.name.startswith('nafe-level') for t in threads()))

    def test_parallel_ffts_share_the_live_parent_budget(self):
        from core import ael_nafe
        budget=[4];calls=[];lock=Lock()
        real_fft=ael_nafe.sfft.rfft2
        def fft(*args,**kwargs):
            with lock:calls.append((current_thread().name,kwargs['workers']))
            return real_fft(*args,**kwargs)
        with filter_budget(lambda:budget[0]),patch('core.ael_nafe.sfft.rfft2',side_effect=fft),\
                progress_scope(lambda *_:budget.__setitem__(0,8)):
            nafe(self.a,self.m,.04,n=9)
        worker_calls=[n for name,n in calls if name.startswith('nafe-level')]
        self.assertTrue(worker_calls)
        self.assertTrue(all(n in (2,4) for n in worker_calls))
        self.assertIn(4,worker_calls)

    def test_level_worker_failure_is_joined_and_never_cached(self):
        engine=LayerEngine()
        with filter_budget(4),patch('core.ael_nafe.ndtr',side_effect=RuntimeError('failed level')):
            with self.assertRaisesRegex(RuntimeError,'failed level'):
                engine.layer(FilterWorker(),self.a,self.p,'nafe')
        self.assertIsNone(engine.layer(FilterWorker(),self.a,self.p,'nafe',calculate=False))
        self.assertFalse(any(t.name.startswith('nafe-level') for t in threads()))

    def test_preview_contract_and_native_window_receipt(self):
        p=prepare_parameters(dict(self.p,nafe_window=257),self.a.shape,self.a.shape,(16,20))
        self.assertEqual(p['nafe_sigma'],.04)
        q,info=nafe_layer(self.a,p,self.m)
        self.assertEqual(info['n'],129);self.assertEqual(info['native_window'],257)
        self.assertEqual(info['internal_sigmas_target_px'][-1],32)
        self.assertEqual(info['kernel_scale'],.5)
        self.assertIn('approximate',info['resolution'])
        p=prepare_parameters(dict(self.p,nafe_window=257),self.a.shape,(16,20),self.a.shape)
        self.assertEqual(nafe_layer(self.a,p,self.m)[1]['n'],257)

    def test_scaled_kernel_preserves_native_and_matches_physical_gaussians(self):
        native=nafe_neighbourhood(9)
        np.testing.assert_array_equal(native,nafe_neighbourhood(9,scale=1.))
        for scale in (.25,.5):
            kernel=nafe_neighbourhood(9,scale=scale)
            x=np.arange(9)-4;r2=x[:,None]**2+x[None,:]**2
            sigmas=2.**(np.arange(1,13)/2)*scale
            expected=sum(np.exp(-.5*r2/s**2)/(2*np.pi*np.sqrt(s)) for s in sigmas)
            expected/=expected[4,4]
            np.testing.assert_allclose(kernel,expected,atol=1e-15)
            self.assertAlmostEqual(kernel[4,4],1.)
            np.testing.assert_array_equal(kernel,kernel[::-1,::-1])
            self.assertLess(kernel[0,0],native[0,0])
        for bad in (0.,-1.,1.01,np.nan,np.inf,1e-300):
            with self.assertRaises(ValueError):nafe_neighbourhood(9,scale=bad)

    def test_scaled_direct_cdf_null_masks_and_cancellation(self):
        a=np.arange(49,dtype=np.float32).reshape(7,7)/49
        valid=np.ones(a.shape,bool);valid[3,3]=False
        q,_=nafe(a,valid,.2,n=3,target_valid=np.ones(a.shape,bool),kernel_scale=.5)
        weights=nafe_neighbourhood(3,scale=.5);weights[1,1]=0
        exact=np.sum(weights*ndtr((float(a[3,3])-a[2:5,2:5])/.2))/weights.sum()
        self.assertAlmostEqual(float(q[3,3]),float(exact),delta=.008)
        flat=np.ones((24,24),np.float32);y,x=np.indices(flat.shape)
        support=np.hypot(x-12,y-12)>4;flat[~support]=np.nan
        result,_=nafe(flat,support,.1,n=9,kernel_scale=.5)
        np.testing.assert_allclose(result[support],.5,atol=2e-6)
        self.assertTrue(np.isnan(result[~support]).all())
        with patch('core.ael_nafe.check_cancelled',side_effect=ProcessingCancelled()):
            with self.assertRaises(ProcessingCancelled):nafe(flat,support,.1,n=9,kernel_scale=.5)

    def test_layer_scales_kernel_and_native_receipt_stays_exact(self):
        params=dict(self.p,nafe_scale=.5)
        q,info=nafe_layer(self.a,params,self.m)
        expected,_=nafe(self.a,self.m,.04,n=5,kernel_scale=.5)
        np.testing.assert_array_equal(q,expected)
        np.testing.assert_allclose(info['internal_sigmas_target_px'],2.**(np.arange(1,13)/2)*.5)
        native,receipt=nafe_layer(self.a,self.p,self.m)
        direct,_=nafe(self.a,self.m,.04,n=9)
        np.testing.assert_array_equal(native,direct)
        self.assertEqual(receipt['kernel_scale'],1.)

    def test_limb_aware_null_signal_units_support_and_method_validation(self):
        y,x=np.indices((256,256));r=np.hypot(x-128,y-128)
        valid=r>55
        a=(.05+np.maximum(r/55,1)**-3).astype(np.float32);a[~valid]=np.nan
        p=dict(sx=128,sy=128,sr=55,nafe_sigma=.025,nafe_window=33,nafe_method='limb_aware')
        before=a.copy();q,info=nafe_layer(a,p,valid,valid)
        np.testing.assert_array_equal(a,before)
        np.testing.assert_array_equal(np.isfinite(q),valid)
        self.assertLess(abs(np.median(q[valid&(r<65)])-.5),.02)
        self.assertTrue(info['experimental'])
        units,_=nafe_layer(a*7+2,dict(p,nafe_sigma=.175),valid,valid)
        np.testing.assert_allclose(q,units,atol=.001,equal_nan=True)
        signal=(.02*np.cos(8*np.arctan2(y-128,x-128))*np.exp(-((r-65)/8)**2)).astype(np.float32)
        changed=a+signal
        enhanced,_=nafe_layer(changed,p,valid,valid)
        original,_=nafe_layer(a,dict(p,nafe_method='ael'),valid,valid)
        original_changed,_=nafe_layer(changed,dict(p,nafe_method='ael'),valid,valid)
        region=valid&(r>57)&(r<80)&(abs(signal)>.01)
        response=(original_changed-original)[region];actual=(enhanced-q)[region]
        self.assertAlmostEqual(float(np.dot(response,actual)/np.dot(response,response)),1.,delta=.1)
        self.assertGreater(np.mean(response*actual>=0),.98)
        with self.assertRaises(ValueError):nafe_layer(a,dict(p,nafe_method='unknown'),valid)
        with self.assertRaises(ValueError):nafe_layer(a,dict(p,sr=0),valid)
        legacy,_=nafe_layer(self.a,dict(nafe_sigma=.04,nafe_window=9),self.m)
        np.testing.assert_allclose(legacy,self.expected,atol=2e-6,equal_nan=True)

    def test_method_cache_isolation_and_experimental_export_receipt(self):
        from core.layer_package import build_layer_package
        from core.psb_export import export_psb_layers,verify_psb_document
        worker=FilterWorker();engine=LayerEngine()
        with patch('core.ael_nafe.nafe_layer',wraps=nafe_layer) as operator:
            original=engine.layer(worker,self.a,self.p,'nafe')
            p=dict(self.p,nafe_method='limb_aware')
            experimental=engine.layer(worker,self.a,p,'nafe')
            engine.layer(worker,self.a,dict(p,nafe_opacity=80),'nafe')
            self.assertEqual(operator.call_count,2)
        self.assertFalse(np.array_equal(original['image'],experimental['image']))
        package=build_layer_package(worker,self.a,p,{},'synthetic.fits')
        row=next(row for row in package.recipe['layers'] if row['filter']=='nafe')
        self.assertEqual(row['normalization']['method'],'limb_aware')
        self.assertTrue(row['normalization']['experimental'])
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'experimental.psb'
            export_psb_layers(package,path);verify_psb_document(path,package)
        with patch('core.ael_nafe._radial_reference',side_effect=ProcessingCancelled):
            with self.assertRaises(ProcessingCancelled):
                LayerEngine().layer(worker,self.a,p,'nafe')

    def test_tiff_jpeg_psb_and_recipe_share_the_independent_layer(self):
        from core.export import export_images
        from core.layer_package import build_layer_package
        from core.psb_export import export_psb_layers,verify_psb_document
        worker=FilterWorker();package=build_layer_package(worker,self.a,self.p,{},'synthetic.fits')
        row=next(row for row in package.recipe['layers'] if row['filter']=='nafe')
        self.assertEqual(row['normalization']['sigma'],.04)
        self.assertEqual(row['opacity_255'],71)
        self.assertEqual(row['mode'],'Overlay')
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            export_psb_layers(package,p/'nafe.psb');verify_psb_document(p/'nafe.psb',package)
            export_images(self.a,self.p,{},str(p/'nafe.tif'),'synthetic.fits',layer_cache=worker.layer_engine,export_layers=True)
            image=tifffile.imread(p/'nafe.tif')
            self.assertEqual(image.shape,(*self.a.shape,3));self.assertEqual(image.dtype,np.uint16)
            self.assertTrue((p/'nafe_preview.jpg').is_file())
            recipe=json.loads((p/'nafe_PS_layers/recipe.json').read_text())
            self.assertEqual(recipe['parameters']['nafe_window'],9)
            np.testing.assert_array_equal(image,tifffile.imread(p/'nafe_PS_layers'/recipe['combined']))


class NAFEGuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])

    def test_controls_snapshot_legacy_defaults_and_levels(self):
        w=EclipseProcessorApp();w.auto_calculate=False
        try:
            a=np.ones((32,40),np.float32);w.full_raw_image=w.raw_image=w.preview_image=a
            self.assertFalse(w.sec_nafe.is_filter_active())
            self.assertEqual(w.combo_nafe_method.currentData(),'ael')
            self.assertFalse(w.combo_nafe_method.isHidden())
            w.combo_nafe_method.setCurrentIndex(1)
            self.assertEqual(w.sl_nafe_opacity.value(),40)
            self.assertEqual(w.sl_nafe_opacity.property('reset_value'),40)
            self.assertTrue(w.sec_nafe.isVisibleTo(w))
            w.ui_level.setCurrentIndex(2)
            w.sec_nafe.chk_active.setChecked(True)
            w.combo_nafe_sigma.setCurrentIndex(1);w.sl_nafe_sigma.setValue(40000)
            w.combo_nafe_window.setCurrentIndex(2)
            saved=capture_settings(w);restore_settings(w,saved)
            self.assertEqual(capture_settings(w),saved)
            p=w.collect_filter_parameters(a.shape)
            self.assertEqual(p['nafe_method'],'limb_aware')
            self.assertTrue(p['nafe_enabled']);self.assertEqual(p['nafe_sigma'],.04)
            self.assertEqual(p['nafe_window'],257)
            w.ui_level.setCurrentIndex(1)
            self.assertTrue(w.sl_nafe_sigma.parameter_row.isHidden())
            self.assertEqual(w.combo_nafe_window.currentData(),257)
            w.ui_level.setCurrentIndex(0)
            self.assertTrue(w.sec_nafe.is_filter_active());self.assertFalse(w.sec_nafe.isHidden())
            self.assertTrue(w.sec_nafe.isVisibleTo(w))
            self.assertFalse(w.sec_rhef.isVisibleTo(w))
            self.assertFalse(w.sl_nafe_opacity.parameter_row.isHidden())
            self.assertTrue(w.sl_nafe_sigma.parameter_row.isHidden())
            self.assertTrue(w.combo_nafe_window.isHidden())
            basic=capture_settings(w)
            restore_settings(w,basic)
            self.assertTrue(w.sec_nafe.is_filter_active())
            self.assertEqual(w.ui_level.currentData(),'basic')
            self.assertEqual(w.combo_nafe_window.currentData(),257)
            old=json.loads(json.dumps(saved));old['sections'].pop('sec_nafe')
            old['controls']={k:v for k,v in old['controls'].items() if '_nafe_' not in k}
            restore_settings(w,old)
            self.assertFalse(w.sec_nafe.is_filter_active())
            self.assertEqual(w.combo_nafe_method.currentData(),'ael')
            self.assertEqual(w.combo_nafe_sigma.currentData(),'auto')
            self.assertEqual(w.combo_nafe_window.currentData(),129)
        finally:close_window(w)
