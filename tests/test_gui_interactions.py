import os
import unittest
from unittest.mock import patch

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

    def test_pipeline_completion_log_distinguishes_idle_pending_and_running(self):
        w=self.window
        w.recalculation_timer.stop();w.presentation_timer.stop()
        w.has_pending_request=False;w.is_processing=False
        with patch('builtins.print') as output:
            w._log_processing_end('PIPELINE','Complete')
            self.assertIn('Idle — no processing running or queued',output.call_args.args[0])
            w.recalculation_timer.start(1000)
            w._log_processing_end('PIPELINE','Complete')
            self.assertIn('Waiting for pending update',output.call_args.args[0])
            w.is_processing=True
            w._log_processing_end('PIPELINE','Complete')
            self.assertIn('Another process is running',output.call_args.args[0])
        w.is_processing=False;w.recalculation_timer.stop()

    def test_stretch_mode_switch_formats_only_new_mode_ticks(self):
        w=self.window
        # Direct calls propagate errors that Qt signal handlers otherwise swallow.
        for previous in range(3):
            for target in range(3):
                w._on_stretch_mode_changed(previous)
                w.sl_stretch.setValue(w.sl_stretch.maximum())
                w._on_stretch_mode_changed(target)
                self.assertEqual(w.sl_stretch.value(),2000 if target==2 else 10)
                self.assertEqual(w.lbl_stretch.text(),'2' if target==2 else '10')

    def test_larson_sekanina_controls_are_available_and_collected(self):
        w = self.window
        w.auto_calculate = False
        w.chk_advanced.setChecked(False)
        w.sec_larson_sekanina.chk_active.setChecked(True)
        w.sl_larson_sekanina_str.setValue(25)
        w.sl_larson_sekanina_radial.setValue(15)
        w.sl_larson_sekanina_angular.setValue(23)
        params = w.collect_filter_parameters((64, 64))
        self.assertTrue(params['larson_sekanina_enabled'])
        self.assertEqual(params['larson_sekanina_str'], 25)
        self.assertEqual(params['larson_sekanina_radial'], 1.5)
        self.assertEqual(params['larson_sekanina_angular'], 2.3)
        self.assertFalse(w.sl_larson_sekanina_radial.isHidden())
        self.assertFalse(w.sl_larson_sekanina_angular.isHidden())

    def test_linear_colour_and_verification_defaults_reset_on_loading(self):
        from pathlib import Path
        import tempfile
        from unittest.mock import patch
        import tifffile
        w = self.window
        self.assertEqual(w.combo_input_state.currentData(), "linear")
        self.assertTrue(w.chk_calibrate_colour.isChecked())
        self.assertFalse(w.chk_verify_preview.isChecked())
        w.auto_calculate = False
        yy, xx = np.mgrid[:80, :100]
        mono = (100 + 20000*np.exp(-np.hypot(xx-50, yy-40)/12)).astype(np.uint16)
        rgb = np.stack([mono, mono//2, mono//3], axis=-1)
        with tempfile.TemporaryDirectory() as tmp:
            for name, image in (("rgb", rgb), ("mono", mono), ("rgb_again", rgb), ("rgb_hdr",rgb.astype(np.float32)*10)):
                path = Path(tmp)/f"{name}.tif"
                tifffile.imwrite(path, image, photometric="rgb" if image.ndim == 3 else "minisblack")
                w.combo_input_state.setCurrentIndex(2)
                w.chk_verify_preview.setChecked(True)
                with patch("gui.app.QFileDialog.getOpenFileName", return_value=(str(path), "")):
                    w.load_image_action()
                self.assertEqual(w.source_path, str(path), w.status_label.text())
                self.assertEqual(w.combo_input_state.currentData(), "linear")
                self.assertFalse(w.lbl_input_linearity.isHidden())
                self.assertEqual(w.lbl_input_linearity.text(), "Assumed linear; not confirmed.")
                self.assertFalse(w.lbl_input_linearity.wordWrap())
                header=w.combo_input_state.parentWidget().layout()
                self.assertEqual(header.indexOf(w.lbl_input_linearity), header.indexOf(w.combo_input_state)+1)
                self.assertFalse(w.combo_input_state.isHidden())
                self.assertFalse(w.chk_verify_preview.isChecked())
                self.assertEqual(w.chk_calibrate_colour.isChecked(), image.ndim == 3)
                self.assertEqual(w.chk_calibrate_colour.isEnabled(), image.ndim == 3)
                np.testing.assert_array_equal(w.full_source_rgb, image if image.ndim == 3 else None)
                if name == 'rgb_hdr':
                    self.assertIsNone(w.source_rgb_white)
                    balanced, _, report = w.colour_data()
                    self.assertTrue(np.isfinite(balanced).all())
                    self.assertIn('shared observed maximum',report['white_source'])
                    self.assertTrue(w.chk_calibrate_colour.isChecked())

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

    def test_version_and_layer_model_tooltips_match_current_behavior(self):
        from config import APP_VERSION
        w=self.window
        self.assertEqual(APP_VERSION,'0.6.0')
        self.assertIn('v'+APP_VERSION,w.windowTitle())
        self.assertIn('original base',w.combo_stretch_mode.toolTip())
        self.assertIn('normalized original base',w.btn_pick_sp.toolTip())
        self.assertIn('filter-layer opacities',w.sl_blend.toolTip())
        self.assertIn('original-image pixels',w.sl_mgn_sigmas[0].toolTip())

    def test_all_user_controls_have_english_tooltips(self):
        import re
        from PySide6.QtWidgets import QWidget, QSlider, QComboBox, QPushButton, QLineEdit, QCheckBox, QLabel, QProgressBar
        controls = [widget for widget in self.window.findChildren(QWidget)
                    if isinstance(widget, (QSlider, QComboBox, QPushButton, QLineEdit, QCheckBox, QProgressBar))
                    or (isinstance(widget,QLabel) and widget.text().strip())]
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
        self.assertFalse(panel.isVisible())
        QTest.qWait(self.window.in_window_tooltips.hover_delay_ms + 100)
        self.assertTrue(panel.isVisible())
        self.assertFalse(panel.isWindow())
        self.assertTrue(self.window.rect().contains(panel.geometry()))
        self.assertTrue(self.window.in_window_tooltips.label.wordWrap())
        self.assertEqual(panel.grab().toImage().pixelColor(3, 3).name(), "#151a21")
        self.application.sendEvent(button, QEvent(QEvent.Type.Leave))
        self.assertFalse(panel.isVisible())

    def test_tooltip_hover_is_cancelled_and_restarted_for_another_control(self):
        from PySide6.QtCore import QEvent
        from PySide6.QtGui import QHelpEvent
        self.window.show()
        self.application.processEvents()
        tips = self.window.in_window_tooltips
        tips.hover_delay_ms = 100
        def hover(widget):
            point = QPoint(2, 2)
            self.application.sendEvent(widget, QHelpEvent(QEvent.Type.ToolTip, point, widget.mapToGlobal(point)))
        hover(self.window.btn_load)
        QTest.qWait(40)
        self.application.sendEvent(self.window.btn_load, QEvent(QEvent.Type.Leave))
        QTest.qWait(120)
        self.assertFalse(tips.panel.isVisible())
        hover(self.window.btn_load)
        QTest.qWait(60)
        hover(self.window.btn_compare)
        QTest.qWait(60)
        self.assertFalse(tips.panel.isVisible())
        QTest.qWait(70)
        self.assertTrue(tips.panel.isVisible())
        self.assertEqual(tips.label.text(), self.window.btn_compare.toolTip())

    def test_disk_overlay_preserves_subpixel_center_and_both_axis_scales(self):
        from unittest.mock import patch
        label = ClickableLabel()
        label.resize(120, 100)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setPixmap(QPixmap(101, 67))
        label.set_circle_parameters(301.3, 188.7, 42.4, 1003, 661)
        with patch('gui.components.QPainter') as painter:
            label.grab()
        center, rx, ry = painter.return_value.drawEllipse.call_args.args
        self.assertAlmostEqual(center.x(), (301.3 + .5)*101/1003 + 10)
        self.assertAlmostEqual(center.y(), (188.7 + .5)*67/661 + 17)
        self.assertAlmostEqual(rx, 42.4*101/1003)
        self.assertAlmostEqual(ry, 42.4*67/661)
        label.close()

    def test_overlay_origin_matches_actual_qlabel_pixels(self):
        from unittest.mock import patch
        from PySide6.QtGui import QImage
        for height in (100, 101):
            with self.subTest(height=height):
                label = ClickableLabel()
                label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                label.setStyleSheet('QLabel { background: black; border: 1px solid #333333; }')
                label.resize(120, height)
                pixmap = QPixmap(81, 67)
                pixmap.fill(Qt.GlobalColor.white)
                label.setPixmap(pixmap)
                rendered = label.grab().toImage().convertToFormat(QImage.Format.Format_RGBA8888)
                pixels = np.frombuffer(rendered.bits(), np.uint8).reshape(height, 120, 4)
                ys, xs = np.where(pixels[..., 0] == 255)
                rect = label._pixmap_rect()
                self.assertEqual((rect.x(), rect.y()), (xs.min(), ys.min()))
                label.set_circle_parameters(40, 33, 10, 81, 67)
                with patch('gui.components.QPainter') as painter:
                    label.grab()
                center = painter.return_value.drawEllipse.call_args.args[0]
                self.assertEqual(center.x(), xs.min()+40.5)
                self.assertEqual(center.y(), ys.min()+33.5)
                label.close()

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
        self.assertEqual(self.window.combo_rhef_mode.currentData(), "continuous")
        for index, expected in ((1, "continuous"), (0, "legacy")):
            self.window.combo_rhef_mode.setCurrentIndex(index)
            for shape in (self.window.raw_image.shape, self.window.full_raw_image.shape):
                params = self.window.collect_filter_parameters(shape)
                self.assertEqual(params["rhef_mode"], expected)

    def test_opacity_rows_precede_strength_and_only_recompose_cached_filters(self):
        from core.layer_engine import engine_for
        from unittest.mock import patch
        w=self.window
        w.chk_statistics_lunar.setChecked(False)
        w.sec_mgn.chk_active.setChecked(True)
        p=w.collect_filter_parameters(w.raw_image.shape)
        engine=engine_for(w.filter_worker)
        with patch.object(w.filter_worker,'run_mgn_native', wraps=w.filter_worker.run_mgn_native) as operator:
            engine.render(w.filter_worker,w.raw_image,p,w.collect_display_parameters())
            self.assertEqual(operator.call_count,1)
            w.sl_mgn_opacity.setValue(25)
            w.render_matrix_to_screen()
            w.sl_mgn_opacity.setValue(70)
            w.render_matrix_to_screen()
            self.assertEqual(operator.call_count,1)
        for name in ('fnrgf','rhef','mgn','wow','tangential','larson_sekanina','achf'):
            strength=getattr(w,'sl_'+name+'_str')
            opacity=getattr(w,'sl_'+name+'_opacity')
            layout=strength.parameter_row.parentWidget().layout()
            self.assertLess(layout.indexOf(opacity.parameter_row),layout.indexOf(strength.parameter_row))
        for controls in w.achf_ael_controls.values():
            layout=controls['panel'].layout()
            self.assertLess(layout.indexOf(controls['opacity'].parameter_row),layout.indexOf(controls['strength'].parameter_row))

    def test_ael_achf_selection_reaches_preview_and_export(self):
        w = self.window
        self.assertEqual(w.combo_achf_variant.currentData(), 'adaptive')
        w.combo_achf_variant.setCurrentIndex(w.combo_achf_variant.findData('ael_iso_04'))
        for shape in (w.raw_image.shape, w.full_raw_image.shape):
            self.assertEqual(w.collect_filter_parameters(shape)['achf_variant'], 'ael_iso_04')
        self.assertFalse(w.sl_achf_kernel.isEnabled())
        self.assertTrue(w.achf_ael_controls['ael_iso_04']['strength'].isEnabled())
        w.combo_achf_variant.setCurrentIndex(0)
        self.assertTrue(w.sl_achf_kernel.isEnabled())

    def test_ael_variants_keep_independent_settings_and_export_snapshot(self):
        w = self.window
        variants = ('ael_iso_01','ael_iso_04','ael_angular_4')
        self.assertEqual(w.combo_achf_variant.count(), 4)
        for i, variant in enumerate(variants):
            w.combo_achf_variant.setCurrentIndex(w.combo_achf_variant.findData(variant))
            controls = w.achf_ael_controls[variant]
            controls['strength'].setValue(11+i)
            controls['outer_sigma'].setValue(21+i)
            if 'sigmas' in controls:
                controls['sigmas'][0].setValue(30+i)
            else:
                controls['angular_sigma'].setValue(15)
        for i, variant in enumerate(variants):
            w.combo_achf_variant.setCurrentIndex(w.combo_achf_variant.findData(variant))
            params = w.collect_filter_parameters(w.raw_image.shape)
            self.assertEqual(params['achf_str'],11+i)
            self.assertEqual(params['achf_ael_parameters']['outer_sigma'],(21+i)/10)
            self.assertEqual(set(params['achf_variants']),set(variants)|{'adaptive'})
            self.assertEqual(params['achf_adaptive_strength'],10)
        w.combo_achf_variant.setCurrentIndex(0)
        self.assertEqual(w.sl_achf_str.value(),10)

    def test_achf_starts_with_full_background_retention(self):
        w = self.window
        self.assertEqual(w.sl_achf_background.value(), 100)
        self.assertFalse(w.sec_achf.is_filter_active())
        self.assertEqual(w.sl_achf_str.value(), 10)
        for shape in (w.raw_image.shape, w.full_raw_image.shape):
            self.assertEqual(w.collect_filter_parameters(shape)['achf_background'], 100)

    def test_adaptive_defaults_reset_to_loaded_values_and_log_actual_settings(self):
        from contextlib import redirect_stdout
        from io import StringIO
        w = self.window
        w.auto_calculate = False
        # A large radius exercises clamping of the automatically chosen support.
        w.full_raw_image = np.ones((1800, 2400), dtype=np.float32)
        w.preview_image = np.ones((900, 1200), dtype=np.float32)
        w.txt_x.setText('1200')
        w.txt_y.setText('900')
        output = StringIO()
        with redirect_stdout(output):
            w.apply_recommended_parameters_to_gui(2000, 2400, 1800)
        for slider in (w.sl_fnrgf_ord, w.sl_fnrgf_seg,
                       w.sl_fnrgf_bin_px, w.sl_fnrgf_rmax, w.sl_wow_scales,
                       w.sl_achf_kernel):
            expected = slider.value()
            slider.setValue(slider.minimum() if expected != slider.minimum() else slider.maximum())
            QTest.mouseDClick(slider, Qt.MouseButton.LeftButton)
            self.assertEqual(slider.value(), expected)
        self.assertEqual(w.sl_achf_kernel.value(), w.sl_achf_kernel.maximum())
        self.assertIn(f'Auto ({w.sl_wow_scales.maximum()} native scales', output.getvalue())
        self.assertIn('support radius = 20.0 preview px', output.getvalue())
        self.assertNotIn('arcsec/pixel', output.getvalue())

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
