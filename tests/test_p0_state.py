"""Issue #3: fractional geometry, recipe snapshots and stale asynchronous jobs."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from copy import deepcopy
from pathlib import Path
from threading import Event
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import tifffile
from PySide6.QtWidgets import QApplication,QWidget,QVBoxLayout

from core.project_settings import write_settings,read_settings
from gui.app import EclipseProcessorApp
from gui.factories import create_stepper_input
from gui.project_settings import capture_settings,restore_settings
from gui_wait import wait_for_gui,close_window


class ReliableStateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])

    def setUp(self):
        self.w=EclipseProcessorApp();self.w.auto_calculate=False
        self.install(np.ones((32,48),np.float32))
        self.w.chk_calibrate_colour.setChecked(False)
        self.w.txt_x.setText('24.25');self.w.txt_y.setText('16.5');self.w.txt_r.setText('5.75')

    def install(self,image):
        self.w.full_raw_image=self.w.raw_image=self.w.preview_image=image

    def tearDown(self):
        self.w.is_processing=False
        close_window(self.w)

    def test_decimal_geometry_overlay_stepper_and_recipe(self):
        w=self.w
        self.assertEqual((w.image_label.circle_x,w.image_label.circle_y,w.image_label.circle_r),(24.25,16.5,5.75))
        host=QWidget();layout=QVBoxLayout(host)
        field=create_stepper_input('X','24.25',layout)
        row=layout.itemAt(0).layout().itemAt(1).layout()
        row.itemAt(2).widget().click()
        self.assertEqual(float(field.text()),25.25)
        row.itemAt(0).widget().click()
        self.assertEqual(float(field.text()),24.25)
        field.setText('10000.1234567');row.itemAt(2).widget().click()
        self.assertAlmostEqual(float(field.text()),10001.1234567,places=9)
        host.close()
        w.txt_x.setText('nan')
        self.assertEqual(w.image_label.circle_x,24.25)
        w.txt_x.setText('24.25')
        saved=capture_settings(w)
        w.txt_x.setText('1');restore_settings(w,saved)
        self.assertEqual(capture_settings(w),saved)
        for value in ('nan','inf','-inf'):
            broken=deepcopy(saved);broken['geometry']['x']=value
            with self.assertRaises(ValueError):restore_settings(w,broken)
            self.assertEqual(capture_settings(w),saved)

    def test_disabled_sidebar_preserves_wow_threshold_snapshot(self):
        w=self.w;w.combo_wow_bilateral.setCurrentIndex(0);w.sl_wow_scales.setValue(3)
        for slider,ticks in zip(w.sl_wow_denoise,(10,20,30)):slider.setValue(ticks)
        before=w.collect_filter_parameters(w.full_raw_image.shape)
        w.control_sidebar.setEnabled(False)
        after=w.collect_filter_parameters(w.full_raw_image.shape)
        self.assertEqual(before['wow_denoise'],[1.,2.,3.])
        self.assertEqual(before['wow_denoise'],after['wow_denoise'])

    def test_presentation_toggle_round_trips_and_older_recipe_defaults_on(self):
        w=self.w;w.btn_psb_preview.setChecked(False);saved=capture_settings(w)
        w.btn_psb_preview.setChecked(True);restore_settings(w,saved)
        self.assertFalse(w.btn_psb_preview.isChecked())
        older=deepcopy(saved);older['controls'].pop('btn_psb_preview')
        restore_settings(w,older)
        self.assertTrue(w.btn_psb_preview.isChecked())

    def test_recipe_uses_loaded_image_limits_instead_of_previous_image(self):
        w=self.w
        w.ui_level.setCurrentIndex(1)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'large.tif'
            image=np.ones((320,384),np.float32);tifffile.imwrite(source,image)
            self.install(image);w.combo_wow_bilateral.setCurrentIndex(0);w.update_wow_controls()
            w.sl_wow_scales.setValue(6);saved=capture_settings(w)
            path=write_settings(root/'large.json',source,saved,{}, {})
            self.install(np.ones((16,20),np.float32));w.update_wow_controls()
            self.assertLess(w.sl_wow_scales.maximum(),6)
            with patch('gui.app.QFileDialog.getOpenFileName',return_value=(str(path),'')):
                w.load_image_action();wait_for_gui(w)
            self.assertEqual(w.full_raw_image.shape,image.shape,w.status_label.text())
            self.assertEqual(capture_settings(w),saved,w.status_label.text())
            self.assertEqual(w.sl_wow_scales.value(),6)
            self.assertEqual(w.image_label.circle_x,24.25)

    def test_rejected_tiff_keeps_current_source_and_geometry(self):
        w=self.w;original=w.full_raw_image;saved=capture_settings(w)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'pages.tif';tifffile.imwrite(path,np.zeros((6,8,2),np.float32))
            with patch('gui.app.QFileDialog.getOpenFileName',return_value=(str(path),'')):
                w.load_image_action();wait_for_gui(w)
        self.assertIs(w.full_raw_image,original)
        self.assertEqual(capture_settings(w),saved)
        self.assertIn('Multi-page TIFF',w.status_label.text())
        self.assertTrue(w.control_sidebar.isEnabled())

    def test_cross_drive_relative_path_failure_keeps_absolute_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'source.tif';source.touch()
            with patch('core.project_settings.os.path.relpath',side_effect=ValueError('different drives')):
                path=write_settings(root/'settings.json',source,capture_settings(self.w),{}, {})
            loaded,settings=read_settings(path)
            self.assertEqual(loaded,source.resolve())
            self.assertEqual(settings,capture_settings(self.w))

    def test_background_result_cannot_replace_source_after_geometry_edit(self):
        w=self.w;original=w.full_raw_image
        w.background.base=dict(full=original,rgb=None,preview=original)
        w.chk_background.setChecked(True);w.recalculation_timer.stop()
        entered,release=Event(),Event()
        def delayed(base,*args):
            entered.set()
            if not release.wait(3):raise RuntimeError('test fit timed out')
            return dict(full=original*2,rgb=None,preview=original*2,points=[],report={})
        try:
            with patch('gui.background_controls.equalize_background',side_effect=delayed),patch.object(w,'dispatch_pipeline_request') as dispatch:
                w.background.start();self.assertTrue(entered.wait(1))
                w.auto_calculate=True
                w.on_circle_center_requested(25,15);w.recalculation_timer.stop()
                release.set();wait_for_gui(w)
                dispatch.assert_called_once()
            self.assertIs(w.full_raw_image,original)
            self.assertTrue(w.background.dirty)
            self.assertIsNone(w.background.report)
        finally:release.set()

    def test_invalid_background_geometry_fails_without_starting_a_retry_loop(self):
        w=self.w;w.chk_background.setChecked(True);w.txt_x.setText('nan')
        with patch('gui.background_controls.TaskThread') as worker:
            w.background.start()
        worker.assert_not_called()
        self.assertIsNone(w.background.thread)
        self.assertTrue(w.background.dirty)
        self.assertIn('finite',w.lbl_background_fit.text())

    def test_export_completion_resumes_geometry_edit_queued_during_export(self):
        w=self.w;w.chk_export_layers.setChecked(False);w.auto_calculate=True
        release,entered=Event(),Event();requests=[]
        w.request_processing_signal.disconnect()
        w.request_processing_signal.connect(lambda image,params:requests.append(params))
        def delayed(**kwargs):
            entered.set()
            if not release.wait(3):raise RuntimeError('test export timed out')
            return 'Export complete'
        try:
            with tempfile.TemporaryDirectory() as tmp,patch('gui.export_worker.export_images',side_effect=delayed),patch('gui.app.QFileDialog.getSaveFileName',return_value=(str(Path(tmp)/'out.tif'),'')):
                w.export_image_action();self.assertTrue(entered.wait(1))
                w.on_circle_center_requested(25,15)
                w.dispatch_pipeline_request()
                self.assertTrue(w.has_pending_request)
                thread=w._export_thread;release.set();self.assertTrue(thread.wait(3000));self.app.processEvents()
                self.assertIsNone(w._export_thread)
                self.assertEqual(len(requests),1)
                self.assertEqual((requests[0]['sx'],requests[0]['sy']),(25.,15.))
                self.assertFalse(w.has_pending_request)
        finally:release.set()
