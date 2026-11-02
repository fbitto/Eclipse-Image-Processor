"""Original-only prominence extraction, editable masks, exports and Qt preview."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import tifffile
from psd_tools import PSDImage
from psd_tools.constants import ChannelID
from core.prominences import prominence_settings, prominence_layer, composite_prominences, _soften_mask
from core.export import export_images
from core.layer_export import to_u16


def scene():
    y,x=np.indices((128,160));r=np.hypot(x-80,y-64)
    corona=.02*np.exp(-np.maximum(r-20,0)/20)
    rgb=np.repeat(corona[...,None],3,axis=-1).astype(np.float32)
    rgb[r<=20]=0
    # A thin red chromosphere plus one taller prominence; outer red noise is excluded.
    rgb[(r>20)&(r<22)]=[1.,.15,.1]
    rgb[(x>=101)&(x<=105)&(abs(y-64)<=2)]=[1.,.15,.1]
    rgb[10,10]=[1.,0.,0.]
    rgb[64,104]=np.nan
    return rgb,dict(sx=80.,sy=64.,sr=20.)


class ProminenceTests(unittest.TestCase):
    def test_soft_highlights_keep_order_at_high_exposure(self):
        rgb=np.zeros((32,48,3),np.float32)
        for x,value in enumerate((.25,.5,1.,2.,4.),start=20):rgb[16,x]=np.array([1.,.15,.1])*value
        image,mask=prominence_layer(rgb,dict(sx=24,sy=16,sr=12),dict(reference=1.,exposure_ev=3.,saturation=.43))
        peaks=image[16,20:25].max(axis=-1).astype(int)
        self.assertTrue(np.all(np.diff(peaks)>0),peaks)
        self.assertLess(peaks.max(),65535)
        self.assertTrue(mask[16,20:25].all())

    def test_edge_blend_preserves_thin_features_without_expanding_support(self):
        mask=np.zeros((64,80),np.uint16)
        mask[5,10:30]=65535;mask[20:55,35:70]=65535
        softened=_soften_mask(mask)
        self.assertFalse(softened[mask==0].any())
        self.assertTrue(np.all(softened<=mask))
        np.testing.assert_array_equal(softened[5,10:30],mask[5,10:30])
        self.assertGreater(softened[20,50],0)
        self.assertLess(softened[20,50],65535)
        self.assertEqual(softened[35,50],65535)

    def test_adjustable_edge_softness_changes_only_mask_and_preserves_support(self):
        mask=np.zeros((80,90),np.uint16)
        mask[10:70,20:80]=65535;mask[3,5:15]=65535
        np.testing.assert_array_equal(_soften_mask(mask,0),mask)
        normal=_soften_mask(mask,3);soft=_soften_mask(mask,10)
        self.assertLess(soft[13,40],normal[13,40])
        self.assertFalse(soft[mask==0].any())
        np.testing.assert_array_equal(soft[3,5:15],mask[3,5:15])
        rgb,p=scene()
        settings=prominence_settings(rgb,p)
        image,default=prominence_layer(rgb,p,settings)
        settings['mask_edge_width_native_px']=0
        sharp,unfeathered=prominence_layer(rgb,p,settings)
        np.testing.assert_array_equal(image,sharp)
        self.assertTrue(np.all(default<=unfeathered))
        for bad in (-.1,20.1,np.nan):
            with self.assertRaises(ValueError):prominence_settings(rgb,p,edge_softness=bad)
            with self.assertRaises(ValueError):prominence_layer(rgb,p,dict(settings,mask_edge_width_native_px=bad))

    def test_contrast_changes_curve_shape_without_changing_mask(self):
        rgb=np.zeros((32,48,3),np.float32)
        for x,value in enumerate((.25,.5,1.,2.,4.),start=20):rgb[16,x]=np.array([1.,.15,.1])*value
        rgb[0,0]=np.nan;before=rgb.copy();p=dict(sx=24,sy=16,sr=12)
        settings=dict(reference=1.,exposure_ev=0.,saturation=1.)
        normal,mask=prominence_layer(rgb,p,settings)
        unity,unity_mask=prominence_layer(rgb,p,dict(settings,contrast=1.))
        stronger,strong_mask=prominence_layer(rgb,p,dict(settings,contrast=2.))
        softer,_=prominence_layer(rgb,p,dict(settings,contrast=.5))
        self.assertGreater(softer[16,21,0],normal[16,21,0])
        np.testing.assert_array_equal(unity,normal)
        np.testing.assert_array_equal(unity_mask,mask)
        np.testing.assert_array_equal(strong_mask,mask)
        self.assertLess(stronger[16,21,0],normal[16,21,0])
        np.testing.assert_array_equal(stronger[16,22],normal[16,22])
        self.assertGreater(stronger[16,23,0],normal[16,23,0])
        self.assertEqual(strong_mask[0,0],0)
        np.testing.assert_array_equal(rgb,before)
        for bad in (.49,2.01,np.nan):
            with self.assertRaises(ValueError):prominence_settings(rgb,p,contrast=bad)
            with self.assertRaises(ValueError):prominence_layer(rgb,p,dict(settings,contrast=bad))

    def test_exposure_limits(self):
        rgb,p=scene()
        for ev in (-3.,5.):
            settings=prominence_settings(rgb,p,ev)
            image,mask=prominence_layer(rgb,p,settings)
            self.assertTrue(mask.any())
        for ev in (-3.01,5.01,np.nan):
            with self.assertRaises(ValueError):
                prominence_settings(rgb,p,ev)
            with self.assertRaises(ValueError):
                prominence_layer(rgb,p,dict(reference=1.,exposure_ev=ev))


    def test_neutral_corona_black_pixels_missing_and_outer_noise_are_excluded(self):
        rgb,p=scene();rgb[63,103]=[1.,.85,.85];before=rgb.copy()
        settings=prominence_settings(rgb,p)
        image,mask=prominence_layer(rgb,p,settings)
        y,x=np.indices(mask.shape);r=np.hypot(x-80,y-64)
        self.assertEqual(image.dtype,np.uint16)
        self.assertEqual(mask.dtype,np.uint16)
        self.assertFalse(mask[r<=20].any())
        self.assertFalse(mask[r>=30].any())
        self.assertEqual(mask[64,104],0)
        self.assertGreater(mask[64,103],0)
        self.assertFalse(mask[(r>23)&(abs(y-64)>3)].any())
        self.assertTrue(((mask>0)&(mask<65535)).any())
        np.testing.assert_array_equal(rgb,before)
        black=composite_prominences(np.zeros(mask.shape),image,mask)
        self.assertFalse(black[mask==0].any())
        self.assertGreater(black[64,103,0],black[64,103,1])

    def test_orange_corona_does_not_become_a_dark_normal_blend_ring(self):
        rgb,p=scene()
        y,x=np.indices(rgb.shape[:2]);r=np.hypot(x-p['sx'],y-p['sy'])
        ring=(r>p['sr'])&(r<1.3*p['sr'])
        rgb[ring]=[1.,.7,.3]
        rgb[64,103]=[1.,.2,.4]  # Pink prominence on the orange continuum.
        rgb[65,103]=[1.,.1,.05]  # Pure red emission must also survive.
        _,mask=prominence_layer(rgb,p,prominence_settings(rgb,p))
        ring[64:66,103]=False
        self.assertFalse(mask[ring].any())
        self.assertGreater(mask[64,103],0)
        self.assertEqual(mask[65,103],65535)

    def test_observed_red_pixels_inside_geometry_are_retained_without_filling_missing_data(self):
        rgb,p=scene()
        rgb[64,99]=[1.,.15,.1]  # Observed red detail just inside the fitted circle.
        rgb[64,80]=[.00001,.000001,.000001]  # Original dark lunar signal stays faint.
        rgb[64,98]=np.nan
        image,mask=prominence_layer(rgb,p,prominence_settings(rgb,p))
        self.assertGreater(mask[64,99],0)
        self.assertEqual(mask[64,98],0)
        self.assertFalse(image[64,98].any())
        self.assertEqual(mask[64,80],0)
        self.assertGreater(image[64,99,0],0)

    def test_saturation_preserves_mask(self):
        rgb,p=scene()
        original,mask=prominence_layer(rgb,p,prominence_settings(rgb,p))
        soft,other=prominence_layer(rgb,p,prominence_settings(rgb,p,saturation=.65))
        np.testing.assert_array_equal(mask,other)
        self.assertLess(np.ptp(soft.astype(float),axis=-1).max(),
                        np.ptp(original.astype(float),axis=-1).max())
        for bad in (-1,2,np.nan):
            with self.assertRaises(ValueError):prominence_settings(rgb,p,saturation=bad)

    def test_ev_is_independent_of_mask_and_input_units(self):
        rgb,p=scene()
        image,mask=prominence_layer(rgb,p,prominence_settings(rgb,p,-2))
        darker,other=prominence_layer(rgb,p,prominence_settings(rgb,p,-3))
        np.testing.assert_array_equal(mask,other)
        self.assertTrue(np.all(darker <= image))
        self.assertTrue(np.any(darker < image))
        scaled,scaled_mask=prominence_layer(rgb*1000,p,prominence_settings(rgb*1000,p,-2))
        np.testing.assert_array_equal(image,scaled)
        np.testing.assert_array_equal(mask,scaled_mask)
        neutral=np.ones_like(rgb)
        _,empty=prominence_layer(neutral,p,prominence_settings(neutral,p))
        self.assertFalse(empty.any())
        for bad in (np.nan,6,-4):
            with self.assertRaises(ValueError):prominence_settings(rgb,p,bad)
        with self.assertRaises(ValueError):prominence_settings(rgb[...,0],p)
        with self.assertRaises(ValueError):prominence_settings(rgb,dict(p,sr=0))

    def test_original_pixels_reach_psb_mask_standalone_and_presented_tiff(self):
        rgb,p=scene()
        source=np.nan_to_num(rgb @ np.array([.299,.587,.114]),nan=0).astype(np.float32)
        # The corona working RGB is deliberately different from the original.
        prepared=np.repeat(source[...,None],3,axis=-1)*np.array([.7,1.,1.2])
        expected,mask=prominence_layer(rgb,p,prominence_settings(rgb,p,5,contrast=2.))
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for correction in (False,True):
                target=root/f'final{correction}.tif'
                export_images(source,p,{},str(target),'original.tif',source_rgb=prepared,
                              original_rgb=rgb,export_prominences=True,export_layers=True,
                              layers_format='psb',processed=source,psb_preview_jpeg=True,
                              color_correction=correction,prominence_exposure_ev=5,prominence_contrast=2.)
                doc=PSDImage.open(root/f'final{correction}_PS_layers.psb')
                layer=doc[-1]
                self.assertEqual(layer.name,'Prominences and chromosphere')
                self.assertTrue(layer.has_mask())
                channels={int(i.id):c for i,c in zip(layer._record.channel_info,layer._channels)}
                for c in range(3):
                    actual=np.frombuffer(channels[c].get_data(160,128,16,2),dtype='>u2').reshape(source.shape)
                    np.testing.assert_array_equal(actual,expected[...,c])
                actual=np.frombuffer(channels[int(ChannelID.USER_LAYER_MASK)].get_data(160,128,16,2),dtype='>u2').reshape(source.shape)
                np.testing.assert_array_equal(actual,mask)
                self.assertEqual(layer.opacity,255)
                if correction:self.assertEqual(doc[-2].name,'Color Correction')
                folder=root/f'final{correction}_prominences'
                np.testing.assert_array_equal(tifffile.imread(folder/'PROMINENCES_MASK.tif'),mask)
                black=tifffile.imread(folder/'PROMINENCES.tif')
                np.testing.assert_array_equal(black,to_u16(composite_prominences(np.zeros(source.shape),expected,mask)))
                self.assertEqual(black.shape,rgb.shape)
            export_images(source,p,{},str(root/'plain.tif'),'original.tif',source_rgb=prepared,processed=source)
            plain=tifffile.imread(root/'plain.tif');presented=tifffile.imread(root/'finalFalse.tif')
            self.assertFalse(np.array_equal(plain,presented))
            np.testing.assert_array_equal(plain[mask==0],presented[mask==0])
            self.assertEqual(sorted(v.name for v in root.glob('*prominences')),['finalFalse_prominences','finalTrue_prominences'])

    def test_tiff_package_preserves_unmasked_rgb_and_editable_mask_receipt(self):
        from core.layer_package import export_layered_package
        from core.filters import FilterWorker
        rgb,p=scene();source=np.nan_to_num(rgb[...,0])
        settings=prominence_settings(rgb,p);image,mask=prominence_layer(rgb,p,settings)
        with tempfile.TemporaryDirectory() as tmp:
            package=export_layered_package(FilterWorker(),source,p,{},'original.tif',Path(tmp)/'layers',
                                           prominences=(image,mask,settings))
            recipe=json.loads((package/'recipe.json').read_text())
            row=recipe['layers'][-1]
            self.assertEqual(row['filter'],'prominences')
            np.testing.assert_array_equal(tifffile.imread(package/row['file']),image)
            np.testing.assert_array_equal(tifffile.imread(package/row['mask_file']),mask)
            self.assertIn('entry.mask_file',(package/'Load_layers_Photoshop.jsx').read_text())
            corona=tifffile.imread(package/recipe['corona_combined'])/65535.
            expected=to_u16(composite_prominences(corona,image,mask))
            np.testing.assert_allclose(tifffile.imread(package/recipe['combined']),expected,atol=1)

    def test_standalone_export_without_photoshop_keeps_previous_products(self):
        rgb,p=scene();source=np.nan_to_num(rgb[...,0])
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);target=root/'out.tif'
            for _ in range(2):
                export_images(source,p,{},str(target),'original.tif',original_rgb=rgb,
                              export_prominences=True,processed=source)
            self.assertTrue((root/'out_prominences/PROMINENCES.tif').is_file())
            self.assertTrue((root/'out_2_prominences/PROMINENCES.tif').is_file())
            self.assertTrue((root/'out_2.tif').is_file())
            self.assertTrue((root/'out_2_preview.jpg').is_file())
            self.assertFalse(list(root.glob('*.psb')))
            with self.assertRaisesRegex(ValueError,'original loaded RGB'):
                export_images(source,p,{},str(root/'bad.tif'),'mono.tif',export_prominences=True)
            self.assertFalse((root/'bad.tif').exists())


from PySide6.QtWidgets import QApplication
from gui.app import EclipseProcessorApp
from gui.project_settings import capture_settings,restore_settings
from gui_wait import wait_for_gui,close_window


class ProminenceGuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])

    def test_fast_preview_preserves_thin_red_structures_before_reduction(self):
        from core.image_data import resize_observed
        w=EclipseProcessorApp();w.auto_calculate=False
        try:
            rgb=np.full((512,512,3),.1,np.float32)
            rgb[256,310]=[.12,.1,.1]
            p=dict(sx=256.,sy=256.,sr=50.)
            w.original_source_rgb=w.full_source_rgb=rgb
            w.full_raw_image=rgb[...,0].copy()
            w.raw_image=w.preview_image=resize_observed(w.full_raw_image,(64,64))
            w.processed_image=w.raw_image
            w.txt_x.setText('256');w.txt_y.setText('256');w.txt_r.setText('50')
            w.chk_calibrate_colour.setChecked(False);w.on_input_state_changed()
            w.chk_prominences.setChecked(True);w.prominence_view.setCurrentIndex(2)
            w.render_matrix_to_screen();wait_for_gui(w)
            image,mask=prominence_layer(rgb,p,prominence_settings(rgb,p,0,saturation=.65))
            expected=resize_observed(mask.astype(np.float32)/65535.,(64,64))
            self.assertGreater(float(expected.max()),.005)
            np.testing.assert_allclose(w.last_preview_presentation,expected,atol=1e-7)
            w.prominence_view.setCurrentIndex(1)
            w.render_matrix_to_screen();wait_for_gui(w)
            native=composite_prominences(np.zeros(mask.shape),image,mask)
            expected_rgb=np.stack([resize_observed(native[...,c],(64,64)) for c in range(3)],axis=-1)
            np.testing.assert_allclose(w.last_preview_presentation,expected_rgb,atol=1e-7)
        finally:close_window(w)

    def test_basic_ev_preserves_negative_recipes_and_advanced_contrast(self):
        w=EclipseProcessorApp();w.auto_calculate=False
        try:
            rgb,p=scene();w.original_source_rgb=w.full_source_rgb=rgb
            w.full_raw_image=w.raw_image=w.preview_image=np.nan_to_num(rgb[...,0])
            w.txt_x.setText('80');w.txt_y.setText('64');w.txt_r.setText('20')
            w.chk_prominences.setEnabled(True);w.chk_prominences.setChecked(True)
            self.assertEqual(w.sl_prominence_exposure.value(),0)
            self.assertEqual((w.prominence_exposure_basic.minimum(),w.prominence_exposure_basic.maximum()),(0,500))
            self.assertTrue(w.sl_prominence_contrast.parameter_row.isHidden())
            w.chk_advanced.setChecked(True);w.sl_prominence_exposure.setValue(-200)
            w.sl_prominence_contrast.setValue(40);w.sl_prominence_edge_softness.setValue(85);saved=capture_settings(w)
            self.assertNotIn('prominence_exposure_basic',saved['controls'])
            w.chk_advanced.setChecked(False)
            self.assertEqual(w.sl_prominence_exposure.value(),-200)
            self.assertEqual(w.sl_prominence_contrast.value(),40)
            self.assertFalse(w.lbl_prominence_ev_retained.isHidden())
            w.prominence_exposure_basic.sliderReleased.emit()
            self.assertEqual(w.sl_prominence_exposure.value(),0)
            self.assertTrue(w.lbl_prominence_ev_retained.isHidden())
            restore_settings(w,saved)
            self.assertEqual(w.sl_prominence_exposure.value(),-200)
            self.assertEqual(w.sl_prominence_contrast.value(),40)
            self.assertEqual(w.sl_prominence_edge_softness.value(),85)
            saved['controls'].pop('sl_prominence_edge_softness')
            saved['controls'].pop('sl_prominence_contrast');saved['controls']['chk_advanced']['value']=False
            saved['ui_mode']='standard'
            restore_settings(w,saved)
            self.assertEqual(w.sl_prominence_contrast.value(),20)
            self.assertEqual(w.sl_prominence_edge_softness.value(),30)
            self.assertEqual(w.sl_prominence_exposure.value(),-200)
            self.assertFalse(w.lbl_prominence_ev_retained.isHidden())
        finally:close_window(w)

    def test_load_preserves_original_through_working_changes_and_preview_export(self):
        w=EclipseProcessorApp();w.auto_calculate=False
        try:
            rgb,p=scene()
            with tempfile.TemporaryDirectory() as tmp:
                original=Path(tmp)/'original.tif';target=Path(tmp)/'out.tif'
                tifffile.imwrite(original,rgb,photometric='rgb')
                w.txt_x.setText('80');w.txt_y.setText('64');w.txt_r.setText('20')
                with patch('gui.app.QFileDialog.getOpenFileName',return_value=(str(original),'')), \
                     patch.object(w,'detect_lunar_limb',return_value=(80,64,20)):
                    w.load_image_action();wait_for_gui(w)
                self.assertEqual((w.sl_prominence_exposure.minimum(),w.sl_prominence_exposure.maximum()),(-300,500))
                self.assertTrue(w.chk_prominences.isEnabled())
                np.testing.assert_array_equal(w.original_source_rgb,rgb)
                # Replace the working source exactly as background preparation does.
                w.full_source_rgb=np.ones_like(rgb)*.01
                w.chk_calibrate_colour.setChecked(False)
                w.chk_prominences.setChecked(True)
                w.sl_prominence_exposure.setValue(-300)
                w.sl_prominence_contrast.setValue(40)
                w.sl_prominence_edge_softness.setValue(80)
                w.prominence_view.setCurrentIndex(1)
                w.render_matrix_to_screen();wait_for_gui(w)
                image,mask=prominence_layer(rgb,p,prominence_settings(rgb,p,-3,saturation=.65,contrast=2.,edge_softness=8.))
                np.testing.assert_allclose(w.last_preview_presentation,composite_prominences(np.zeros(mask.shape),image,mask),atol=1e-7)
                w.prominence_view.setCurrentIndex(2)
                w.render_matrix_to_screen();wait_for_gui(w)
                np.testing.assert_allclose(w.last_preview_presentation,mask/65535.,atol=1e-7)
                w.sl_warmth.setValue(70)
                saved=capture_settings(w)
                self.assertNotIn('prominence_view',saved['controls'])
                w.sl_prominence_exposure.setValue(100);restore_settings(w,saved)
                self.assertEqual(w.sl_prominence_exposure.value(),-300)
                self.assertEqual(w.prominence_view.currentData(),'composition')
                self.assertEqual(w.sl_warmth.value(),70)
                # This fixture already supplies a prepared working RGB.
                w.background.dirty=False
                with patch('gui.app.QFileDialog.getSaveFileName',return_value=(str(target),'')), \
                     patch('gui.export_worker.export_images',return_value='done') as export:
                    w.export_image_action()
                    wait_for_gui(w)
                    if w._export_thread is not None:
                        self.assertTrue(w._export_thread.wait(10000));self.app.processEvents()
                    export.assert_called_once()
                    self.assertIs(export.call_args.kwargs['original_rgb'],w.original_source_rgb)
                    self.assertIsNot(export.call_args.kwargs['original_rgb'],w.full_source_rgb)
                    self.assertTrue(export.call_args.kwargs['export_prominences'])
                    self.assertEqual(export.call_args.kwargs['warmth'],.7)
                    self.assertEqual(export.call_args.kwargs['prominence_saturation'],.65)
                    self.assertEqual(export.call_args.kwargs['prominence_contrast'],2.)
                    self.assertEqual(export.call_args.kwargs['prominence_edge_softness'],8.)
                # Mono input must turn the feature off, with no fabricated red image.
                w.original_source_rgb=None;w.on_input_state_changed()
                self.assertFalse(w.chk_prominences.isChecked())
                self.assertFalse(w.chk_prominences.isEnabled())
                # Existing v4 recipes without the new option still load, defaulting off.
                saved['controls'].pop('chk_prominences')
                saved['controls'].pop('sl_prominence_exposure')
                saved['controls'].pop('sl_warmth')
                saved['controls'].pop('sl_prominence_saturation')
                saved['controls'].pop('sl_prominence_contrast')
                restore_settings(w,saved)
                self.assertFalse(w.chk_prominences.isChecked())
                self.assertEqual(w.sl_prominence_exposure.value(),-200)
                self.assertEqual(w.sl_warmth.value(),0)
                self.assertEqual(w.sl_prominence_saturation.value(),65)
                self.assertEqual(w.sl_prominence_contrast.value(),20)
        finally:close_window(w)
