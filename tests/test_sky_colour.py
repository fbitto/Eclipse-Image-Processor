"""General warmth + additive corona warmth acceptance tests.

"""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from copy import deepcopy
import inspect
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from gui_wait import close_window, wait_for_gui
from core import warmth
from core.colour import set_luminosity
from core.cancellation import ProcessingCancelled


def scene(green=False):
    y, x = np.indices((240, 360))
    sky = .08 + .015*x/360 + .01*y/240
    streamer = .06*np.exp(-((y-120)/5)**2)*np.clip((x-190)/35, 0, 1)*np.clip((345-x)/25, 0, 1)
    colour = [.04,.13,.10] if green else [.04,.08,.10]
    rgb = set_luminosity(np.broadcast_to(colour, (*sky.shape,3)), sky+streamer)
    background = dict(geometry=(180,120,12), radius=6., grid=16, points=None)
    return rgb, background


def compose(rgb, layers):
    for _, layer in layers:
        rgb = warmth.blend_warmth(rgb, layer)
    return rgb


def excess_green(rgb):
    return rgb[...,1]-(rgb[...,0]+rgb[...,2])/2


class ColourSceneTests(unittest.TestCase):
    """Ensure colour assertions use meaningful known-truth inputs."""
    def test_green_cast_and_neutral_control_are_distinct(self):
        green, _ = scene(green=True)
        neutral = np.full_like(green, .1)
        self.assertGreater(float(excess_green(green).min()), .01)
        np.testing.assert_array_equal(excess_green(neutral), 0)

    def test_scene_contains_real_sky_and_far_outer_corona_support(self):
        rgb, bg = scene()
        layer = warmth.warmth_layer(rgb, 1., bg)
        self.assertIsNotNone(layer)
        mask = layer[1]/65535.
        self.assertLess(float(mask[20:70].mean()), .01)
        self.assertGreater(float(mask[120,280]), .95)
        self.assertGreater(280-bg['geometry'][0], 6*bg['geometry'][2])

    def test_existing_corona_control_protects_sky_and_preserves_source(self):
        rgb, bg = scene()
        before = rgb.copy()
        output = warmth.blend_warmth(rgb, warmth.warmth_layer(rgb,1.,bg))
        np.testing.assert_array_equal(rgb, before)
        np.testing.assert_array_equal(output[20:70], before[20:70])
        self.assertGreater(float(np.max(abs(output-before))), .001)


class ColourNumericalAcceptance(unittest.TestCase):
    def setUp(self):
        self.rgb, self.bg = scene()

    def layers(self, rgb=None, **kwargs):
        kwargs.setdefault('background', self.bg)
        return warmth.colour_layers(self.rgb if rgb is None else rgb, **kwargs)

    def test_zero_off_defaults_are_exact_bypass(self):
        layers = self.layers()
        self.assertEqual(layers, [])
        self.assertIs(compose(self.rgb, layers), self.rgb)

    def test_general_warmth_reaches_sky_and_corona_without_sky_samples(self):
        layers = self.layers(general_warmth=.6, background=None)
        self.assertEqual([name for name,_ in layers], ['general_warmth'])
        output = compose(self.rgb, layers)
        for region in (np.s_[20:70,20:340], np.s_[118:123,260:300]):
            with self.subTest(region=region):
                delta = (output[...,0]-output[...,2])-(self.rgb[...,0]-self.rgb[...,2])
                self.assertGreater(float(delta[region].mean()), .001)

    def test_general_warmth_is_monotonic_at_zero_mid_and_full(self):
        previous = self.rgb
        for amount in (.25,.5,1.):
            output = compose(self.rgb, self.layers(general_warmth=amount))
            self.assertGreater(float(np.mean(output[...,0]-output[...,2])),
                               float(np.mean(previous[...,0]-previous[...,2])))
            previous = output

    def test_corona_only_is_identical_to_existing_warmth(self):
        for amount in (.25,.6,1.):
            with self.subTest(amount=amount):
                expected = warmth.warmth_layer(self.rgb, amount, self.bg)
                layers = self.layers(warmth=amount)
                self.assertEqual([name for name,_ in layers], ['warmth'])
                for actual, old in zip(layers[0][1], expected):
                    np.testing.assert_array_equal(actual, old)
                np.testing.assert_array_equal(compose(self.rgb,layers),
                                              warmth.blend_warmth(self.rgb,expected))

    def test_corona_is_additive_on_general_baseline_and_preserves_sky(self):
        baseline = compose(self.rgb,self.layers(general_warmth=.35))
        layers = self.layers(general_warmth=.35,warmth=.8)
        self.assertEqual([name for name,_ in layers], ['general_warmth','warmth'])
        output = compose(self.rgb,layers)
        np.testing.assert_array_equal(output[20:70], baseline[20:70])
        region = np.s_[118:123,260:300]
        delta = (output[...,0]-output[...,2])-(baseline[...,0]-baseline[...,2])
        self.assertGreater(float(delta[region].mean()), .001)

    def test_general_warmth_does_not_reclassify_corona_mask(self):
        old_mask = dict(self.layers(warmth=.7))['warmth'][1]
        for amount in (.2,.7,1.):
            new_mask = dict(self.layers(general_warmth=amount,warmth=.7))['warmth'][1]
            np.testing.assert_array_equal(new_mask, old_mask)

    def test_green_reduction_works_with_both_warmth_controls_at_zero(self):
        rgb, _ = scene(green=True)
        output = compose(rgb,self.layers(rgb,reduce_green_sky=True))
        sky = np.s_[20:70,20:340]
        self.assertLess(float(excess_green(output)[sky].mean()), float(excess_green(rgb)[sky].mean()))
        self.assertGreaterEqual(float(excess_green(output)[sky].min()), -3/65535)

    def test_green_reduction_preserves_neutral_and_magenta_sky(self):
        for colour in ([.08,.08,.08],[.10,.07,.11]):
            with self.subTest(colour=colour):
                rgb = np.broadcast_to(colour,self.rgb.shape).copy()
                output = compose(rgb,self.layers(rgb,reduce_green_sky=True))
                np.testing.assert_allclose(output,rgb,atol=2/65535,rtol=0)

    def test_green_reduction_protects_strong_outer_streamer(self):
        rgb, _ = scene(green=True)
        output = compose(rgb,self.layers(rgb,reduce_green_sky=True))
        np.testing.assert_allclose(output[120,280],rgb[120,280],atol=3/65535,rtol=0)
        layer = dict(self.layers(rgb,reduce_green_sky=True))['reduce_green_sky']
        alpha = layer[1]/65535.
        self.assertLess(float(alpha[120,280]), .05)
        self.assertLess(float(np.max(abs(np.diff(alpha[:,280])))), .3)

    def test_green_reduction_is_last_and_cannot_reintroduce_a_green_cast(self):
        rgb, _ = scene(green=True)
        baseline = compose(rgb,self.layers(rgb,general_warmth=.4,warmth=.6))
        layers = self.layers(rgb,general_warmth=.4,warmth=.6,reduce_green_sky=True)
        self.assertEqual([name for name,_ in layers], ['general_warmth','warmth','reduce_green_sky'])
        output = compose(rgb,layers)
        sky = np.s_[20:70,20:340]
        self.assertLess(float(excess_green(output)[sky].mean()),float(excess_green(baseline)[sky].mean()))

    def test_green_reduction_strength_zero_mid_full_and_validation(self):
        rgb,_=scene(green=True)
        original=float(excess_green(rgb)[20:70].mean())
        previous=original
        for strength in (0.,.25,.75,1.):
            output=compose(rgb,self.layers(rgb,reduce_green_sky=True,green_reduction=strength))
            measured=float(excess_green(output)[20:70].mean())
            if strength==0:np.testing.assert_array_equal(output,rgb)
            else:self.assertLess(measured,previous)
            self.assertGreaterEqual(measured,-3/65535)
            previous=measured
        self.assertLess(previous,3/65535)
        for bad in (-.1,1.1,np.nan,np.inf):
            with self.assertRaises(ValueError):self.layers(rgb,reduce_green_sky=True,green_reduction=bad)

    def test_full_warmth_is_orange_red_rather_than_yellow(self):
        from core.colour import warm_colour
        neutral=np.full((4,4,3),.15)
        orange=set_luminosity(warm_colour(neutral,1.),neutral @ [.30,.59,.11])
        import colorsys
        hue,_,_=colorsys.rgb_to_hsv(*orange[0,0])
        self.assertGreater(hue*360,20.)
        self.assertLess(hue*360,40.)
        self.assertGreater(float(orange[0,0,1]),float(orange[0,0,2]))

    def test_valid_pure_sky_does_not_require_nonzero_corona_mask(self):
        for green in (False, True):
            rgb = np.broadcast_to([.04,.13 if green else .08,.10],self.rgb.shape).copy()
            layers = self.layers(rgb,general_warmth=.4,reduce_green_sky=green)
            self.assertIn('general_warmth',dict(layers))
            if green:
                self.assertIn('reduce_green_sky',dict(layers))
            self.assertGreater(float(np.max(abs(compose(rgb,layers)-rgb))), .001)

    def test_failed_sky_fit_does_not_bypass_general_warmth_or_treat_everything_as_sky(self):
        for bg in (None,dict(self.bg,points=[]),dict(self.bg,points=[(20,20)]*8)):
            layers = self.layers(general_warmth=.5,warmth=.6,reduce_green_sky=True,background=bg)
            self.assertEqual([name for name,_ in layers], ['general_warmth'])

    def test_missing_and_explicitly_excluded_pixels_are_never_modified(self):
        rgb = self.rgb.copy(); rgb[20:30,20:30] = np.nan
        valid = np.isfinite(rgb).all(axis=-1); valid[40:50,40:50] = False
        original = rgb.copy()
        layers = self.layers(rgb,general_warmth=.5,warmth=.8,reduce_green_sky=True,valid=valid)
        for _, (_,alpha) in layers:
            self.assertTrue((alpha[~valid]==0).all())
        output = compose(rgb,layers)
        np.testing.assert_array_equal(output[~valid],original[~valid])
        np.testing.assert_array_equal(rgb,original)

    def test_colour_combinations_preserve_luminance_and_stay_finite(self):
        rgb, _ = scene(green=True)
        for general in (0.,.5,1.):
            for corona in (0.,.5,1.):
                for green in (False,True):
                    with self.subTest(general=general,corona=corona,green=green):
                        output=compose(rgb,self.layers(rgb,general_warmth=general,warmth=corona,reduce_green_sky=green))
                        np.testing.assert_allclose(output @ [.30,.59,.11],rgb @ [.30,.59,.11],atol=6/65535,rtol=0)
                        self.assertTrue(np.isfinite(output).all())
                        self.assertTrue(((output>=0)&(output<=1)).all())

    def test_black_sky_and_finite_black_moon_do_not_gain_signal(self):
        for flat in (True,False):
            rgb = np.zeros_like(self.rgb) if flat else self.rgb.copy()
            rgb[110:130,170:190]=0
            output=compose(rgb,self.layers(rgb,general_warmth=1.,warmth=1.,reduce_green_sky=True))
            np.testing.assert_array_equal(output[110:130,170:190],0)
            if flat:np.testing.assert_array_equal(output,0)

    def test_highlights_and_channel_extremes_are_bounded(self):
        rgb=self.rgb.copy()
        colours=np.array([[1,1,1],[1,0,0],[0,1,0],[0,0,1],[.999,.999,.999]])
        rgb[100,20:25]=colours
        output=compose(rgb,self.layers(rgb,general_warmth=1.,warmth=1.,reduce_green_sky=True))
        self.assertTrue(np.isfinite(output).all())
        self.assertTrue(((output>=0)&(output<=1)).all())

    def test_arguments_and_shapes_are_validated(self):
        for name in ('general_warmth','warmth'):
            for bad in (-.01,1.01,np.nan,np.inf):
                with self.subTest(name=name,bad=bad),self.assertRaises(ValueError):
                    self.layers(**{name:bad})
        for kw in (dict(valid=np.ones((1,1),bool)),dict(native_shape=(0,360)),
                   dict(background=dict(self.bg,geometry=(180,120,-1)))):
            with self.subTest(kw=kw.keys()),self.assertRaises(ValueError):
                self.layers(general_warmth=.5,reduce_green_sky=True,**kw)
        with self.assertRaises(ValueError):self.layers(self.rgb[...,0],general_warmth=.5)

    def test_reduced_preview_maps_native_sky_samples_consistently(self):
        from core.image_data import resize_observed
        rgb, _ = scene(green=True)
        reduced=np.stack([resize_observed(rgb[...,c],(180,120)) for c in range(3)],axis=-1)
        native=dict(self.layers(rgb,general_warmth=.4,warmth=.6,reduce_green_sky=True))
        preview=dict(self.layers(reduced,general_warmth=.4,warmth=.6,reduce_green_sky=True,native_shape=rgb.shape[:2]))
        self.assertEqual(set(native),set(preview))
        for name in native:
            expected=resize_observed(native[name][1].astype(float)/65535,(180,120))
            self.assertLess(float(np.mean(abs(preview[name][1]/65535-expected))),.02)

    def test_input_sampling_and_validity_arrays_are_immutable(self):
        valid=np.ones(self.rgb.shape[:2],bool)
        bg=deepcopy(self.bg);before=self.rgb.copy();mask=valid.copy()
        self.layers(general_warmth=.5,warmth=.5,reduce_green_sky=True,valid=valid,background=bg)
        np.testing.assert_array_equal(self.rgb,before)
        np.testing.assert_array_equal(valid,mask)
        self.assertEqual(bg,self.bg)

    def test_cancellation_propagates(self):
        with patch('core.warmth.check_cancelled',side_effect=ProcessingCancelled()):
            with self.assertRaises(ProcessingCancelled):
                self.layers(general_warmth=.5,warmth=.5,reduce_green_sky=True)


class ColourUIAcceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app=QApplication.instance() or QApplication([])

    def setUp(self):
        from gui.app import EclipseProcessorApp
        self.w=EclipseProcessorApp();self.w.auto_calculate=False

    def tearDown(self):close_window(self.w)

    def test_controls_defaults_ranges_order_and_mono_enablement(self):
        w=self.w
        self.assertEqual((w.sl_general_warmth.minimum(),w.sl_general_warmth.maximum(),w.sl_general_warmth.value()),(0,100,0))
        self.assertFalse(w.chk_reduce_green_sky.isChecked())
        self.assertEqual(w.sl_green_reduction.value(),75)
        self.assertFalse(w.sl_green_reduction.isEnabled())
        self.assertFalse(w.sl_general_warmth.isEnabled())
        self.assertFalse(w.chk_reduce_green_sky.isEnabled())
        layout=w.appearance_layout
        self.assertLess(layout.indexOf(w.sl_general_warmth.parameter_row),layout.indexOf(w.sl_warmth.parameter_row))
        self.assertLess(layout.indexOf(w.sl_warmth.parameter_row),layout.indexOf(w.chk_reduce_green_sky))
        self.assertIn('Corona',w.sl_warmth.title_label.text())

    def test_green_strength_enablement_settings_and_legacy_default(self):
        from gui.project_settings import capture_settings,restore_settings,validate_settings
        w=self.w;rgb,_=scene();w.full_source_rgb=rgb;w.on_input_state_changed()
        self.assertFalse(w.sl_green_reduction.isEnabled())
        w.chk_reduce_green_sky.setChecked(True)
        self.assertTrue(w.sl_green_reduction.isEnabled())
        w.sl_green_reduction.setValue(95)
        saved=capture_settings(w);restore_settings(w,saved)
        self.assertEqual(w.sl_green_reduction.value(),95)
        legacy=deepcopy(saved);legacy['controls'].pop('sl_green_reduction')
        restore_settings(w,legacy)
        self.assertEqual(w.sl_green_reduction.value(),75)
        for bad in (-1,101):
            invalid=deepcopy(saved);invalid['controls']['sl_green_reduction']['value']=bad
            with self.assertRaises(ValueError):validate_settings(w,invalid)
        w.chk_reduce_green_sky.setChecked(False)
        self.assertFalse(w.sl_green_reduction.isEnabled())

    def test_controls_visible_for_all_levels_and_enabled_for_rgb(self):
        w=self.w;rgb,_=scene()
        w.full_source_rgb=rgb;w.on_input_state_changed()
        for level in range(3):
            w.ui_level.setCurrentIndex(level)
            self.assertTrue(w.sl_general_warmth.isVisibleTo(w))
            self.assertTrue(w.chk_reduce_green_sky.isVisibleTo(w))
            self.assertTrue(w.sl_general_warmth.isEnabled())
            self.assertTrue(w.chk_reduce_green_sky.isEnabled())

    def test_new_recipe_roundtrip_and_legacy_defaults_keep_old_corona_amount(self):
        from gui.project_settings import capture_settings,restore_settings
        w=self.w;w.sl_warmth.setValue(43);w.sl_general_warmth.setValue(37);w.chk_reduce_green_sky.setChecked(True)
        saved=capture_settings(w);restore_settings(w,saved)
        self.assertEqual(capture_settings(w),saved)
        old=deepcopy(saved)
        for name in ('sl_general_warmth','chk_reduce_green_sky'):old['controls'].pop(name)
        restore_settings(w,old)
        self.assertEqual(w.sl_warmth.value(),43)
        self.assertEqual(w.sl_general_warmth.value(),0)
        self.assertFalse(w.chk_reduce_green_sky.isChecked())

    def test_control_edits_do_not_dispatch_numerical_filters(self):
        w=self.w
        with patch.object(w,'dispatch_pipeline_request_if_auto') as dispatch,patch.object(w,'render_matrix_to_screen') as render:
            w.sl_general_warmth.setValue(37);w.chk_reduce_green_sky.setChecked(True)
            dispatch.assert_not_called()
            self.assertGreaterEqual(render.call_count,2)

    def test_invalid_saved_values_are_rejected(self):
        from gui.project_settings import capture_settings,validate_settings
        saved=capture_settings(self.w)
        for name,value in (('sl_general_warmth',-1),('sl_general_warmth',101),('chk_reduce_green_sky','yes')):
            bad=deepcopy(saved);bad['controls'][name]['value']=value
            with self.subTest(name=name,value=value),self.assertRaises(ValueError):validate_settings(self.w,bad)

    def test_presentation_snapshot_copies_values_for_fit_half_and_native(self):
        from core.image_data import resize_observed
        w=self.w;rgb,bg=scene()
        w.full_source_rgb=rgb;w.original_source_rgb=rgb
        w.full_raw_image=(rgb @ [.299,.587,.114]).astype(np.float32)
        w.raw_image=resize_observed(w.full_raw_image,(180,120))
        w.preview_image=w.raw_image;w.processed_image=w.raw_image.copy()
        for name,value in zip(('x','y','r'),bg['geometry']):
            getattr(w,'txt_'+name).setText(str(value))
        w.chk_calibrate_colour.setChecked(False)
        wait_for_gui(w)
        for zoom in (None,.5,1.):
            with patch.object(w,'_start_presentation'):
                w.image_label.set_zoom(zoom)
                w.sl_general_warmth.setValue(37);w.chk_reduce_green_sky.setChecked(True)
                w.sl_green_reduction.setValue(95)
                w.render_matrix_to_screen()
                job=w._presentation_request
                try:
                    self.assertIsNotNone(job)
                    self.assertEqual(job['general_warmth'],.37)
                    self.assertIs(job['reduce_green_sky'],True)
                    self.assertEqual(job['green_reduction'],.95)
                    w.sl_general_warmth.setValue(81);w.chk_reduce_green_sky.setChecked(False)
                    self.assertEqual(job['general_warmth'],.37)
                    self.assertIs(job['reduce_green_sky'],True)
                    self.assertEqual(job['green_reduction'],.95)
                finally:
                    w._presentation_request=None

    def test_direct_image_load_resets_new_controls(self):
        import tifffile
        w=self.w;rgb,_=scene()
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'new.tif'
            tifffile.imwrite(source,rgb.astype(np.float32),photometric='rgb')
            w.sl_general_warmth.setValue(71);w.chk_reduce_green_sky.setChecked(True)
            with patch.object(w,'detect_lunar_limb',return_value=(180,120,12)):
                w.open_file(str(source));wait_for_gui(w)
            self.assertEqual(w.sl_general_warmth.value(),0)
            self.assertFalse(w.chk_reduce_green_sky.isChecked())

    def test_export_snapshot_copies_controls_without_starting_export(self):
        w=self.w;rgb,bg=scene()
        w.full_source_rgb=rgb;w.original_source_rgb=rgb
        w.full_raw_image=w.raw_image=w.preview_image=(rgb @ [.299,.587,.114]).astype(np.float32)
        for name,value in zip(('x','y','r'),bg['geometry']):
            getattr(w,'txt_'+name).setText(str(value))
        w.on_input_state_changed();wait_for_gui(w)
        w.background.dirty=False
        w.sl_general_warmth.setValue(37);w.chk_reduce_green_sky.setChecked(True)
        w.sl_green_reduction.setValue(95)
        wait_for_gui(w)
        with tempfile.TemporaryDirectory() as tmp, \
             patch('gui.app.QFileDialog.getSaveFileName',return_value=(str(Path(tmp)/'out.tif'),'')), \
             patch('gui.app.ExportThread.start'):
            w.export_image_action()
            thread=w._export_thread
            try:
                self.assertIsNotNone(thread,w.status_label.text())
                job=thread.request
                self.assertEqual(job['green_reduction'],.95)
                self.assertEqual(job['general_warmth'],.37)
                self.assertIs(job['reduce_green_sky'],True)
                w.sl_general_warmth.setValue(81);w.chk_reduce_green_sky.setChecked(False)
                self.assertEqual(job['general_warmth'],.37)
                self.assertIs(job['reduce_green_sky'],True)
            finally:
                w._export_thread=None
                if thread is not None:thread.deleteLater()
                w.control_sidebar.setEnabled(True);w.zoom_toolbar.setEnabled(True)

    def test_native_preview_matches_editable_package_without_recalculating_filters(self):
        from core.layer_engine import engine_for
        from core.layer_package import build_layer_package
        from core.presentation import psb_presentation_settings
        from core.result_cache import parameter_signature
        w=self.w;rgb,bg=scene(green=True)
        source=(rgb @ [.299,.587,.114]).astype(np.float32)
        w.full_raw_image=w.raw_image=w.preview_image=source
        w.full_source_rgb=w.original_source_rgb=rgb
        for name,value in zip(('x','y','r'),bg['geometry']):
            getattr(w,'txt_'+name).setText(str(value))
        w.chk_calibrate_colour.setChecked(False)
        w.sl_background_radius.setValue(60)
        w.sl_general_warmth.setValue(35);w.sl_warmth.setValue(60)
        w.chk_reduce_green_sky.setChecked(True)
        wait_for_gui(w)
        params=w.collect_filter_parameters(source.shape)
        engine=engine_for(w.filter_worker)
        composition=engine.render(w.filter_worker,source,params,w.collect_display_parameters())
        w.processed_image=composition
        w._full_cache=(source,parameter_signature(params),composition,w._preview_revision)
        with patch.object(engine,'_calculate',side_effect=AssertionError('Recalculated a numerical filter')):
            w.set_preview_zoom(1.);wait_for_gui(w)
            settings=psb_presentation_settings(source,rgb=rgb,params=params,exposure_ev=w.sl_psb_exposure.value()/100)
            package=build_layer_package(w.filter_worker,source,params,settings,'synthetic.fits',rgb=rgb,
                warmth=.6,general_warmth=.35,reduce_green_sky=True,warmth_background=w.background.warmth_parameters())
        expected=np.clip(package.combined.astype(float)/65535*255,0,255).astype(np.uint8)
        np.testing.assert_allclose(w.image_label._native_pixels,expected,atol=1,rtol=0)

    def test_combined_prominences_remain_visible_with_psb_presentation_off(self):
        from core.prominences import prominence_settings,prominence_layer,composite_prominences
        w=self.w;rgb,bg=scene()
        original=rgb.copy();original[118:123,192:197]=[.8,.01,.005]
        source=(rgb @ [.299,.587,.114]).astype(np.float32)
        w.full_source_rgb=rgb;w.original_source_rgb=original
        w.full_raw_image=w.raw_image=w.preview_image=source
        for name,value in zip(('x','y','r'),bg['geometry']):
            getattr(w,'txt_'+name).setText(str(value))
        w.on_input_state_changed();w.chk_calibrate_colour.setChecked(False)
        w.sl_general_warmth.setValue(35);w.sl_warmth.setValue(40)
        w.chk_reduce_green_sky.setChecked(True)
        w.sl_prominence_exposure.setValue(200);w.sl_prominence_edge_softness.setValue(0)
        for psb in (False,True):
            with self.subTest(psb=psb):
                w.btn_psb_preview.setChecked(psb)
                w.chk_prominences.setChecked(False);w.render_matrix_to_screen();wait_for_gui(w)
                baseline=w.last_preview_presentation.copy()
                w.chk_prominences.setChecked(True);w.render_matrix_to_screen();wait_for_gui(w)
                params=w.collect_filter_parameters(source.shape)
                image,mask=prominence_layer(original,params,prominence_settings(original,params,2.,.65,1.,0.))
                self.assertGreater(int(mask.max()),0)
                expected=composite_prominences(baseline,image,mask)
                np.testing.assert_allclose(w.last_preview_presentation,expected,atol=1e-7,rtol=0)
                self.assertGreater(float(np.max(abs(w.last_preview_presentation-baseline))),.1)

    def test_explicit_prominence_views_leave_original_comparison(self):
        w=self.w;rgb,bg=scene()
        original=rgb.copy();original[118:123,192:197]=[.8,.01,.005]
        source=(rgb @ [.299,.587,.114]).astype(np.float32)
        w.full_source_rgb=rgb;w.original_source_rgb=original
        w.full_raw_image=w.raw_image=w.preview_image=source
        for name,value in zip(('x','y','r'),bg['geometry']):
            getattr(w,'txt_'+name).setText(str(value))
        w.on_input_state_changed();w.chk_calibrate_colour.setChecked(False)
        w.sl_general_warmth.setValue(35);w.chk_reduce_green_sky.setChecked(True)
        w.sl_prominence_exposure.setValue(200);w.sl_prominence_edge_softness.setValue(0)
        w.chk_prominences.setChecked(True)
        for index in (1,2):
            w.prominence_view.setCurrentIndex(0)
            w.btn_compare.setChecked(True)
            self.assertTrue(w.show_original_mode)
            w.prominence_view.setCurrentIndex(index)
            wait_for_gui(w)
            self.assertFalse(w.show_original_mode)
            self.assertGreater(float(np.max(w.last_preview_presentation)),.1)

    def test_export_entry_point_accepts_both_controls(self):
        w=self.w
        # Signature check fails rather than silently accepting partial wiring.
        from core.export import export_images
        for name in ('general_warmth','reduce_green_sky','green_reduction'):
            self.assertIn(name,inspect.signature(export_images).parameters)


class ColourExportAcceptance(unittest.TestCase):
    def setUp(self):
        self.rgb,self.bg=scene(green=True)
        self.source=self.rgb @ [.299,.587,.114]
        self.params=dict(zip(('sx','sy','sr'),self.bg['geometry']))

    def package(self,**kwargs):
        from core.filters import FilterWorker
        from core.layer_package import build_layer_package
        return build_layer_package(FilterWorker(),self.source,self.params,{},'synthetic.fits',
            rgb=self.rgb,warmth_background=self.bg,**kwargs)

    def test_zero_off_export_is_pixel_and_layer_compatible(self):
        original=self.package(warmth=.4)
        bypass=self.package(warmth=.4,general_warmth=0.,reduce_green_sky=False)
        np.testing.assert_array_equal(bypass.combined,original.combined)
        self.assertEqual([r.record for r in bypass.layers],[r.record for r in original.layers])

    def test_editable_layer_order_and_original_prominences_are_unchanged(self):
        original=np.broadcast_to(np.array([65535,1200,0],np.uint16),self.rgb.shape).copy()
        mask=np.zeros(self.source.shape,np.uint16);mask[118:123,275:285]=65535
        package=self.package(general_warmth=.35,warmth=.6,reduce_green_sky=True,prominences=(original,mask,{}))
        filters=[layer.record['filter'] for layer in package.layers]
        selected=[name for name in filters if name in ('general_warmth','warmth','reduce_green_sky','prominences')]
        self.assertEqual(selected,['general_warmth','warmth','reduce_green_sky','prominences'])
        np.testing.assert_array_equal(package.combined[mask>0],original[mask>0])
        layer=package.layers[filters.index('prominences')]
        np.testing.assert_array_equal(layer.mask,mask)
        np.testing.assert_array_equal(np.dstack(layer.rgb),original)
        for name in ('general_warmth','warmth','reduce_green_sky'):
            self.assertIsNotNone(package.layers[filters.index(name)].mask)

    def test_native_tiff_jpeg_and_tiff_package_share_the_colour_treatment(self):
        from core.export import export_images
        import json
        import tifffile
        from PIL import Image
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)/'result.tif'
            export_images(self.source,self.params,{},str(target),'synthetic.fits',source_rgb=self.rgb,
                export_layers=True,layers_format='tiff',general_warmth=.35,warmth=.6,
                reduce_green_sky=True,warmth_background=self.bg)
            final=tifffile.imread(target)
            recipe=json.loads((Path(tmp)/'result_PS_layers/recipe.json').read_text())
            combined=tifffile.imread(Path(tmp)/'result_PS_layers'/recipe['combined'])
            np.testing.assert_allclose(final.astype(float),combined.astype(float),atol=3,rtol=0)
            with Image.open(Path(tmp)/'result_preview.jpg') as im:
                jpeg=np.asarray(im).astype(float)
            self.assertEqual(final.shape,jpeg.shape)
            self.assertLess(float(np.mean(abs(final/65535*255-jpeg))),3.)

    def test_psb_writer_verifies_the_editable_colour_layers(self):
        from core.psb_export import export_psb_layers,verify_psb_document
        package=self.package(general_warmth=.35,warmth=.6,reduce_green_sky=True)
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)/'result.psb'
            export_psb_layers(package,target)
            verify_psb_document(target,package)
