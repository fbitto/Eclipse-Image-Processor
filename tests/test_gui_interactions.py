import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from gui.app import EclipseProcessorApp
from gui.components import ClickableLabel


class GuiInteractionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def setUp(self):
        self.window = EclipseProcessorApp()
        self.window.request_processing_signal.disconnect()
        self.requests = []
        self.window.request_processing_signal.connect(lambda a, p: self.requests.append(p))
        image = np.ones((64, 64), dtype=np.float32)
        self.window.raw_image = image
        self.window.preview_image = image
        self.window.full_raw_image = image
        self.window.processed_image = image
        self.window.txt_x.setText("32")
        self.window.txt_y.setText("32")
        self.window.txt_r.setText("8")
        self.window.recalculation_timer.stop()

    def tearDown(self):
        self.window.close()

    def test_linear_colour_and_verification_defaults_reset_on_loading(self):
        from pathlib import Path
        import tempfile
        from unittest.mock import patch
        import tifffile
        w = self.window
        self.assertEqual(w.combo_input_state.currentData(), "linear")
        self.assertTrue(w.chk_calibrate_colour.isChecked())
        self.assertTrue(w.chk_verify_preview.isChecked())
        w.auto_calculate = False
        yy, xx = np.mgrid[:80, :100]
        mono = (100 + 20000*np.exp(-np.hypot(xx-50, yy-40)/12)).astype(np.uint16)
        rgb = np.stack([mono, mono//2, mono//3], axis=-1)
        with tempfile.TemporaryDirectory() as tmp:
            for name, image in (("rgb", rgb), ("mono", mono), ("rgb_again", rgb)):
                path = Path(tmp)/f"{name}.tif"
                tifffile.imwrite(path, image, photometric="rgb" if image.ndim == 3 else "minisblack")
                w.combo_input_state.setCurrentIndex(2)
                w.chk_verify_preview.setChecked(False)
                with patch("gui.app.QFileDialog.getOpenFileName", return_value=(str(path), "")):
                    w.load_image_action()
                self.assertEqual(w.source_path, str(path), w.status_label.text())
                self.assertEqual(w.combo_input_state.currentData(), "linear")
                self.assertTrue(w.chk_verify_preview.isChecked())
                self.assertEqual(w.chk_calibrate_colour.isChecked(), image.ndim == 3)
                self.assertEqual(w.chk_calibrate_colour.isEnabled(), image.ndim == 3)
                np.testing.assert_array_equal(w.full_source_rgb, image if image.ndim == 3 else None)

    def test_colour_calibration_requires_declared_linear_rgb_and_is_reversible(self):
        self.assertFalse(self.window.chk_calibrate_colour.isEnabled())
        t = np.linspace(.01, .9, 64*64).reshape(64, 64)
        rgb = np.stack([.1+.6*t, .05+.3*t, .025+.15*t], axis=-1).astype(np.float32)
        self.window.full_source_rgb = rgb
        self.window.combo_input_state.setCurrentIndex(0)
        self.window.on_input_state_changed()
        self.assertFalse(self.window.chk_calibrate_colour.isEnabled())
        self.window.combo_input_state.setCurrentIndex(1)
        self.assertTrue(self.window.chk_calibrate_colour.isEnabled())
        from unittest.mock import patch
        with patch("gui.app.neutralize_tse") as calibrate, patch("gui.app.set_luminosity") as colorize:
            self.window.chk_calibrate_colour.setChecked(True)
            self.window.render_matrix_to_screen()
            self.window.show_original_mode = True
            self.window.render_matrix_to_screen()
            self.window.show_original_mode = False
            calibrate.assert_not_called()
            colorize.assert_not_called()
            self.assertTrue(self.window.image_label.pixmap().toImage().isGrayscale())
        calibrated, _, report = self.window.colour_data()
        self.assertIn("tse-tools", report["method"])
        np.testing.assert_allclose(calibrated[..., 0], calibrated[..., 1], atol=1e-6)
        original, _, original_report = self.window.colour_data(original=True)
        np.testing.assert_array_equal(original, rgb)
        self.assertEqual(original_report["method"], "none")
        self.window.combo_input_state.setCurrentIndex(2)
        self.assertFalse(self.window.chk_calibrate_colour.isChecked())
        restored, _, report = self.window.colour_data()
        np.testing.assert_array_equal(restored, rgb)
        self.assertEqual(report["method"], "none")

    def test_calibration_row_whitespace_toggles_once_per_click(self):
        self.window.full_source_rgb = np.ones((64, 64, 3), np.float32)
        self.window.combo_input_state.setCurrentIndex(1)
        self.window.on_input_state_changed()
        checkbox = self.window.chk_calibrate_colour
        checkbox.setChecked(False)
        checkbox.resize(350, 30)
        self.assertTrue(checkbox.isEnabled())
        point = QPoint(checkbox.width()-3, checkbox.height()//2)
        for expected in (True, False, True):
            QTest.mouseClick(checkbox, Qt.MouseButton.LeftButton, pos=point)
            self.assertEqual(checkbox.isChecked(), expected)

    def test_invalid_recipe_does_not_leave_pipeline_busy(self):
        from unittest.mock import patch
        with patch.object(self.window, "collect_filter_parameters", side_effect=ValueError("invalid control")):
            self.window.dispatch_pipeline_request()
        self.assertFalse(self.window.is_processing)
        self.assertEqual(self.requests, [])
        self.window.dispatch_pipeline_request()
        self.assertEqual(len(self.requests), 1)

    def test_edits_during_worker_run_publish_only_the_latest_recipe(self):
        original = self.window.processed_image.copy()
        self.window.dispatch_pipeline_request()
        self.window.txt_x.setText("25")
        # Debounce expires while worker is still running: queue exactly one run.
        self.window.recalculation_timer.stop()
        self.window.dispatch_pipeline_request()
        self.window.txt_y.setText("26")
        self.window.on_processing_finished(np.zeros_like(original))
        np.testing.assert_array_equal(self.window.processed_image, original)
        self.assertEqual(len(self.requests), 1)
        QTest.qWait(800)
        self.assertEqual(len(self.requests), 2)
        self.assertEqual((self.requests[-1]["sx"], self.requests[-1]["sy"]), (25, 26))
        result = np.full_like(original, 3)
        self.window.on_processing_finished(result)
        np.testing.assert_array_equal(self.window.processed_image, result)
        self.assertFalse(self.window.is_processing)

    def test_manual_recalculate_during_worker_run_is_not_lost(self):
        self.window.toggle_auto_calc_mode(False)
        self.window.dispatch_pipeline_request()
        self.window.txt_x.setText("24")
        self.window.dispatch_pipeline_request()
        self.window.on_processing_finished(np.zeros_like(self.window.raw_image))
        self.assertEqual(len(self.requests), 2)
        self.assertEqual(self.requests[-1]["sx"], 24)

    def test_old_image_result_is_ignored_after_loading_another_image(self):
        self.window.dispatch_pipeline_request()
        replacement = self.window.raw_image.copy()*7
        self.window.raw_image = replacement
        self.window.preview_image = replacement
        self.window.processed_image = replacement
        self.window.dispatch_pipeline_request_if_auto()
        self.window.on_processing_finished(np.zeros_like(replacement))
        np.testing.assert_array_equal(self.window.processed_image, replacement)
        QTest.qWait(800)
        self.assertEqual(len(self.requests), 2)

    def test_real_worker_finishes_with_latest_slider_values(self):
        from core.filters import FilterWorker
        from core.pipeline import execute_pipeline
        image = np.random.default_rng(51).uniform(.1, 1, (128, 160)).astype(np.float32)
        self.window.raw_image = image
        self.window.preview_image = image
        self.window.full_raw_image = image
        self.window.processed_image = image.copy()
        self.window.request_processing_signal.connect(self.window.filter_worker.process_pipeline)
        self.window.sec_mgn.chk_active.setChecked(True)
        self.window.dispatch_pipeline_request()
        self.window.sl_mgn_gam.setValue(45)
        self.window.sl_mgn_str.setValue(27)
        # Let queued Qt completion and debounce events run, with a bounded wait.
        import time
        for _ in range(300):
            self.application.processEvents()
            time.sleep(.01)  # Release the GIL so the Python Qt worker can progress.
            if len(self.requests) >= 2 and not self.window.is_processing and not self.window.recalculation_timer.isActive():
                break
        self.assertGreaterEqual(len(self.requests), 2)
        self.assertFalse(self.window.is_processing)
        self.assertFalse(self.window.recalculation_timer.isActive())
        expected = execute_pipeline(FilterWorker(), image, self.window.collect_filter_parameters(image.shape))
        np.testing.assert_array_equal(self.window.processed_image, expected)

    def test_all_user_controls_have_english_tooltips(self):
        import re
        from PySide6.QtWidgets import QWidget, QSlider, QComboBox, QPushButton, QLineEdit, QCheckBox
        controls = [widget for widget in self.window.findChildren(QWidget)
                    if isinstance(widget, (QSlider, QComboBox, QPushButton, QLineEdit, QCheckBox))]
        self.assertGreater(len(controls), 80)
        for control in controls:
            with self.subTest(control=control.objectName() or type(control).__name__, text=getattr(control, "text", lambda: "")()):
                help_text = control.toolTip().strip()
                self.assertTrue(help_text, "User control has no tooltip")
                self.assertIsNone(re.search(r"[áéíóúñ¿¡]|\b(entrada|imagen|calibrar|exportar|guardar|filtro|seleccionar)\b", help_text, re.I))
                self.assertNotIn("tse-tools", help_text)

    def test_tooltip_is_opaque_wrapped_and_contained_in_main_window(self):
        from PySide6.QtCore import QEvent
        from PySide6.QtGui import QHelpEvent
        self.window.show()
        self.application.processEvents()
        button = self.window.btn_export
        point = QPoint(button.width()-2, button.height()-2)
        help_event = QHelpEvent(QEvent.Type.ToolTip, point, button.mapToGlobal(point))
        self.application.sendEvent(button, help_event)
        panel = self.window.in_window_tooltips.panel
        self.assertTrue(panel.isVisible())
        self.assertFalse(panel.isWindow())
        self.assertTrue(self.window.rect().contains(panel.geometry()))
        self.assertTrue(self.window.in_window_tooltips.label.wordWrap())
        self.assertEqual(panel.grab().toImage().pixelColor(3, 3).name(), "#151a21")
        self.application.sendEvent(button, QEvent(QEvent.Type.Leave))
        self.assertFalse(panel.isVisible())

    def test_only_modified_click_requests_recentering(self):
        label = ClickableLabel()
        label.resize(100, 100)
        pixmap = QPixmap(100, 100)
        pixmap.fill(Qt.GlobalColor.black)
        label.setPixmap(pixmap)
        label.set_circle_parameters(50, 50, 10, 100, 100)
        centers, ordinary = [], []
        label.circle_center_requested.connect(lambda x, y: centers.append((x, y)))
        label.image_clicked.connect(lambda x, y: ordinary.append((x, y)))
        try:
            QTest.mouseClick(label, Qt.MouseButton.LeftButton, pos=QPoint(40, 60))
            self.assertEqual(centers, [])
            self.assertEqual(ordinary, [(40, 60)])
            # Qt ControlModifier corresponds to Command on macOS.
            QTest.mouseClick(label, Qt.MouseButton.LeftButton,
                             Qt.KeyboardModifier.ControlModifier, QPoint(40, 60))
            self.assertEqual(centers, [(40, 60)])
            self.window.on_image_canvas_clicked(20, 25)
            self.assertEqual(self.window.txt_x.text(), "32")
            self.window.on_circle_center_requested(20, 25)
            self.assertEqual(self.window.txt_x.text(), "20")
            self.assertEqual(self.window.txt_y.text(), "25")
            self.assertEqual(self.requests, [])
        finally:
            label.close()

    def test_rhef_mode_is_part_of_preview_and_export_recipe(self):
        self.assertEqual(self.window.combo_rhef_mode.currentData(), "legacy")
        self.window.combo_rhef_mode.setCurrentIndex(1)
        for shape in (self.window.raw_image.shape, self.window.full_raw_image.shape):
            params = self.window.collect_filter_parameters(shape)
            self.assertEqual(params["rhef_mode"], "continuous")

    def test_geometry_edits_restart_one_debounce_timer(self):
        self.window.txt_x.setText("20")
        QTest.qWait(350)
        self.window.txt_y.setText("25")
        QTest.qWait(350)
        self.assertEqual(self.requests, [])
        QTest.qWait(350)
        self.assertEqual(len(self.requests), 1)
        self.assertEqual(self.requests[0]["sx"], 20)
        self.assertEqual(self.requests[0]["sy"], 25)

    def test_active_slider_change_is_delayed_and_coalesced(self):
        # Enable without a recomputation; the worker is disconnected in setUp.
        from unittest.mock import patch
        with patch.object(self.window.sec_fnrgf, "is_filter_active", return_value=True):
            self.window.sl_fnrgf_str.setValue(30)
            QTest.qWait(350)
            self.window.sl_fnrgf_str.setValue(31)
            self.window.sl_fnrgf_str.sliderReleased.emit()
            QTest.qWait(350)
            self.assertEqual(self.requests, [])
            QTest.qWait(350)
            self.assertEqual(len(self.requests), 1)
            self.assertEqual(self.requests[0]["fnrgf_str"], 31)

    def test_edit_during_processing_waits_for_pause(self):
        self.window.is_processing = True
        self.window.has_pending_request = True
        self.window.txt_x.setText("21")
        self.window.on_processing_finished(self.window.raw_image.copy())
        self.assertEqual(self.requests, [])
        QTest.qWait(800)
        self.assertEqual(len(self.requests), 1)

    def test_manual_mode_does_not_schedule_and_explicit_calculate_cancels_timer(self):
        self.window.txt_x.setText("21")
        self.window.toggle_auto_calc_mode(False)
        QTest.qWait(800)
        self.assertEqual(self.requests, [])
        self.window.txt_y.setText("22")
        self.assertFalse(self.window.recalculation_timer.isActive())
        self.window.auto_calculate = True
        self.window.dispatch_pipeline_request_if_auto()
        self.window.dispatch_pipeline_request()
        self.assertEqual(len(self.requests), 1)
        self.assertFalse(self.window.recalculation_timer.isActive())

    def test_basic_mode_visibility_and_advanced_round_trip(self):
        from core.result_cache import parameter_signature
        w = self.window
        self.assertFalse(w.chk_advanced.isChecked())
        for slider in (*w.sl_mgn_sigmas, *w.sl_mgn_weights, w.sl_fnrgf_smooth,
                       w.sl_rhef_upsilon_high, w.sl_wow_scales, w.sl_ghs_lp):
            self.assertTrue(slider.isHidden())
            self.assertTrue(slider.title_label.isHidden())
            self.assertTrue(slider.value_label.isHidden())
        for slider in (w.sl_fnrgf_mask, w.sl_fnrgf_ord, w.sl_mgn_k, w.sl_mgn_h,
                       w.sl_tangential_denoise, w.sl_achf_threshold, w.sl_wow_noise):
            self.assertFalse(slider.isHidden())
        before = parameter_signature(w.collect_filter_parameters((64, 64)))
        w.chk_advanced.setChecked(True)
        self.assertFalse(w.sl_mgn_sigmas[0].isHidden())
        self.assertTrue(w.sl_wow_noise.isHidden())
        w.chk_advanced.setChecked(False)
        self.assertEqual(before, parameter_signature(w.collect_filter_parameters((64, 64))))
        self.assertIs(w.chk_advanced.parentWidget(), w.chk_calibrate_colour.parentWidget())

    def test_basic_wow_noise_updates_every_scale_and_advanced_values_survive(self):
        w = self.window
        self.assertEqual(w.sl_wow_noise.value(), 0)
        w.sl_wow_noise.setValue(23)
        self.assertTrue(all(s.value() == 23 for s in w.sl_wow_denoise))
        self.assertTrue(all(s.value_label.text() == '2.3' for s in w.sl_wow_denoise))
        self.assertTrue(all(x == 2.3 for x in w.collect_filter_parameters((64, 64))['wow_denoise']))
        w.chk_advanced.setChecked(True)
        w.sl_wow_denoise[0].setValue(41)
        w.chk_advanced.setChecked(False)
        self.assertEqual(w.sl_wow_denoise[0].value(), 41)
        self.assertFalse(w.lbl_advanced_values.isHidden())
        w.sl_wow_noise.setValue(24)
        self.assertTrue(all(s.value() == 24 for s in w.sl_wow_denoise))
        self.assertTrue(w.lbl_advanced_values.isHidden())

    def test_basic_rhef_edit_links_tails_without_resetting_on_mode_switch(self):
        w = self.window
        w.chk_advanced.setChecked(True)
        w.chk_rhef_symmetric.setChecked(False)
        w.sl_rhef_upsilon_high.setValue(77)
        w.chk_advanced.setChecked(False)
        self.assertEqual(w.sl_rhef_upsilon_high.value(), 77)
        self.assertFalse(w.lbl_advanced_values.isHidden())
        w.sl_rhef_upsilon.setValue(42)
        params = w.collect_filter_parameters((64, 64))
        self.assertEqual(params['rhef_upsilon_high'], params['rhef_upsilon'])
        self.assertTrue(w.chk_rhef_symmetric.isChecked())
        self.assertEqual(w.sl_rhef_upsilon_high.value(), 42)
