"""Control placement, AEL Basic restrictions and current-project compatibility."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from copy import deepcopy
import unittest
from unittest.mock import patch
import numpy as np
from PySide6.QtWidgets import QApplication,QLabel
from gui.app import EclipseProcessorApp
from gui.project_settings import capture_settings,restore_settings,validate_settings
from gui_wait import close_window,wait_for_gui


class UILevelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])

    def setUp(self):
        self.w=EclipseProcessorApp();self.w.auto_calculate=False
        self.w.txt_r.setText('12')

    def tearDown(self):close_window(self.w)

    def test_layout_and_two_declared_input_types(self):
        w=self.w
        self.assertEqual([w.combo_input_state.itemData(i) for i in range(w.combo_input_state.count())],['linear','nonlinear'])
        self.assertEqual(w.combo_input_state.currentData(),'linear')
        self.assertEqual(w.ui_level.currentData(),'standard')
        self.assertTrue(w.chk_advanced.isHidden())
        layout=w.appearance_layout
        self.assertLess(layout.indexOf(w.chk_calibrate_colour),layout.indexOf(w.sl_warmth.parameter_row))
        self.assertLess(layout.indexOf(w.sl_psb_exposure.parameter_row),layout.indexOf(w.chk_calibrate_colour))
        self.assertEqual(w.sl_warmth.title_label.text(),'Warmth')
        self.assertIsInstance(w.sl_warmth.title_label,QLabel)
        self.assertIsNot(w.chk_verify_preview.parentWidget(),w.status_label.parentWidget())
        self.assertIs(w.combo_input_state.parentWidget(),w.preparation_layout.parentWidget())

    def test_basic_uses_ael_preserves_on_off_and_disables_excluded_filters_once(self):
        w=self.w
        for name in ('fnrgf','rhef','tangential','larson_sekanina','mgn'):
            getattr(w,'sec_'+name).chk_active.setChecked(True)
        w.sec_nrgf.chk_active.setChecked(False);w.sec_wow.chk_active.setChecked(True)
        w.achf_ael_controls['ael_iso_04']['enabled'].setChecked(True)
        w.achf_ael_controls['ael_angular_4']['enabled'].setChecked(False)
        w.achf_ael_controls['ael_iso_01']['enabled'].setChecked(True)
        w.chk_achf_adaptive.setChecked(True)
        w.sl_mgn_sigmas[0].setValue(175)
        w.combo_wow_bilateral.setCurrentIndex(1)
        w.combo_nrgf_statistics.setCurrentIndex(1)
        with patch.object(w,'dispatch_pipeline_request_if_auto') as dispatch:
            w.ui_level.setCurrentIndex(0)
            dispatch.assert_called_once()
        self.assertFalse(w.sec_nrgf.is_filter_active())
        self.assertTrue(w.sec_mgn.is_filter_active());self.assertTrue(w.sec_wow.is_filter_active())
        self.assertEqual(w.combo_wow_bilateral.currentIndex(),2)
        self.assertEqual(w.combo_nrgf_statistics.currentIndex(),0)
        self.assertTrue(w.achf_ael_controls['ael_iso_04']['enabled'].isChecked())
        self.assertFalse(w.achf_ael_controls['ael_angular_4']['enabled'].isChecked())
        for name in ('fnrgf','rhef','tangential','larson_sekanina'):
            self.assertFalse(getattr(w,'sec_'+name).is_filter_active())
            self.assertTrue(getattr(w,'sec_'+name).isHidden())
        self.assertFalse(w.chk_achf_adaptive.isChecked())
        self.assertFalse(w.achf_ael_controls['ael_iso_01']['enabled'].isChecked())
        self.assertFalse(w.achf_cards['ael_iso_04'].isHidden())
        self.assertFalse(w.achf_cards['ael_angular_4'].isHidden())
        self.assertTrue(w.achf_cards['adaptive'].isHidden())
        self.assertTrue(w.sl_mgn_sigmas[0].parameter_row.isHidden())
        w.ui_level.setCurrentIndex(1)
        self.assertFalse(w.sec_fnrgf.is_filter_active())
        self.assertEqual(w.sl_mgn_sigmas[0].value(),175)

    def test_cards_share_canonical_inclusion_and_opacity(self):
        w=self.w
        w.achf_cards['ael_iso_04'].chk_active.setChecked(True)
        self.assertTrue(w.sec_achf.is_filter_active())
        self.assertTrue(w.achf_ael_controls['ael_iso_04']['enabled'].isChecked())
        w.achf_cards['ael_iso_04'].chk_active.setChecked(False)
        self.assertFalse(w.sec_achf.is_filter_active())
        self.assertTrue(w.achf_cards['ael_iso_04'].isAncestorOf(
            w.achf_ael_controls['ael_iso_04']['opacity'].parameter_row))

    def test_level_round_trip_and_legacy_input_mapping(self):
        w=self.w
        for mode in ('basic','standard','expert'):
            w.ui_level.setCurrentIndex(w.ui_level.findData(mode))
            saved=capture_settings(w)
            restore_settings(w,saved)
            self.assertEqual(capture_settings(w),saved)
        for index,text,expected in [(0,'Input: linearity unspecified','linear'),
                                    (1,'Input: linear','linear'),(2,'Input: already stretched / nonlinear','nonlinear')]:
            old=deepcopy(saved);old.pop('ui_mode')
            old['controls']['combo_input_state']=dict(kind='combo',value=index,text=text)
            old['controls']['chk_advanced']['value']=False
            restore_settings(w,old)
            self.assertEqual(w.combo_input_state.currentData(),expected)
            self.assertEqual(w.ui_level.currentData(),'standard')
            self.assertNotIn('ui_mode',old)
        old['controls']['chk_advanced']['value']=True
        restore_settings(w,old)
        self.assertEqual(w.ui_level.currentData(),'expert')

    def test_loading_basic_enforces_restrictions_after_all_saved_values(self):
        w=self.w
        saved=capture_settings(w);saved['ui_mode']='basic'
        saved['sections']['sec_fnrgf']['active']=True
        saved['controls']['combo_wow_bilateral']=dict(kind='combo',value=1,text=w.combo_wow_bilateral.itemText(1))
        restore_settings(w,saved)
        self.assertFalse(w.sec_fnrgf.is_filter_active())
        self.assertEqual(w.combo_wow_bilateral.currentIndex(),2)
        bad=deepcopy(saved);bad['ui_mode']='automatic'
        with self.assertRaises(ValueError):validate_settings(w,bad)

    def test_new_image_defaults_cannot_enable_hidden_basic_filters(self):
        from pathlib import Path
        import tempfile,tifffile
        w=self.w
        w.ui_level.setCurrentIndex(0)
        image=np.linspace(.01,1.,64*80,dtype=np.float32).reshape(64,80)
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'linear.tif'
            tifffile.imwrite(source,image)
            with patch('gui.app.QFileDialog.getOpenFileName',return_value=(str(source),'')), \
                 patch.object(w,'detect_lunar_limb',return_value=(40,32,8)):
                w.load_image_action();wait_for_gui(w)
        self.assertEqual(w.ui_level.currentData(),'basic')
        params=w.collect_filter_parameters(w.full_raw_image.shape)
        self.assertFalse(params['fnrgf_enabled'])
        self.assertEqual(params['wow_mode'],'ael_bilateral')
        self.assertFalse(params['achf_variants']['adaptive']['enabled'])
        self.assertFalse(params['achf_variants']['ael_iso_01']['enabled'])
