"""Physical slider labels and wheel routing through the real sidebar widgets."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import unittest
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtTest import QSignalSpy, QTest
from PySide6.QtWidgets import QApplication, QComboBox, QScrollArea, QSlider
from gui.app import EclipseProcessorApp
from gui.components import ScrollSafeComboBox, ScrollSafeSlider


class SliderInteractionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.window = EclipseProcessorApp()
        self.window.auto_calculate = False
        self.window.request_processing_signal.disconnect()

    def tearDown(self):
        self.window.presentation_timer.stop()
        self.window.close()
        self.window.deleteLater()
        self.app.processEvents()

    def test_all_controls_use_wheel_safe_widgets_and_unencoded_labels(self):
        sliders = self.window.findChildren(QSlider)
        self.assertGreater(len(sliders), 70)
        for slider in sliders:
            self.assertIsInstance(slider, ScrollSafeSlider)
            if hasattr(slider, 'title_label'):
                self.assertNotIn('×10', slider.title_label.text())
                self.assertNotIn('/10', slider.toolTip())
                self.assertNotIn('value /', slider.toolTip())
                for tick in (slider.minimum(), slider.maximum()):
                    slider.setValue(tick)
                    self.assertEqual(float(slider.value_label.text()),
                                     float(slider.display_formatter(tick)) if slider.display_formatter
                                     else tick / slider.display_divisor)
        for combo in self.window.findChildren(QComboBox):
            self.assertIsInstance(combo, ScrollSafeComboBox)

    def test_known_physical_values_and_finest_symmetry_step(self):
        w = self.window
        for name, expected in {
            'noise_gate_thr': '0.1', 'bilateral_d': '0.5', 'bilateral_ss': '0.5',
            'fnrgf_rad': '1', 'mgn_gam': '3.2', 'mgn_k': '0.7', 'mgn_h': '0.7',
            'rhef_upsilon': '0.35', 'rhef_bin': '1', 'achf_kernel': '2',
            'achf_boost': '2',
        }.items():
            self.assertEqual(getattr(w, 'sl_' + name).value_label.text(), expected, name)
        w.sl_fnrgf_seg.setValue(5)
        self.assertEqual(w.sl_fnrgf_seg.value_label.text(), '32')
        w.sl_ghs_sp.setValue(101)
        self.assertEqual(w.lbl_ghs_sp.text(), '0.0505')
        self.assertEqual(w.collect_display_parameters()['sp'], 0.0505)

    def test_log_modes_display_actual_k_and_refresh_at_unchanged_tick(self):
        w = self.window
        for combo, slider in ((w.combo_pre_mode, w.sl_pre_stretch),
                              (w.combo_stretch_mode, w.sl_stretch)):
            combo.setCurrentIndex(1)
            for tick, expected in ((0, '1'), (10, '10'), (20, '100'), (60, '1000000')):
                slider.setValue(tick)
                self.assertEqual(slider.value_label.text(), expected)
            slider.setValue(10)
            combo.setCurrentIndex(0)
            self.assertEqual(slider.value_label.text(), '10')
            self.assertNotIn('Log', slider.title_label.text())
            combo.setCurrentIndex(1)
            self.assertEqual(slider.title_label.text(), 'Logarithmic K')
            self.assertEqual(slider.value_label.text(), '10')

    def test_ghs_original_ranges_units_and_constraints(self):
        w = self.window
        w.combo_stretch_mode.setCurrentIndex(2)
        self.assertEqual((w.sl_stretch.minimum(), w.sl_stretch.maximum()), (0, 20000))
        self.assertEqual(w.sl_stretch.value_label.text(), '2')
        self.assertEqual(w.collect_display_parameters()['strength'], 2.)
        self.assertEqual((w.sl_ghs_b.minimum(), w.sl_ghs_b.maximum()), (-500, 1500))
        w.sl_ghs_b.setValue(-100)
        self.assertEqual(w.sl_ghs_b.value_label.text(), '-1')
        self.assertEqual(w.collect_display_parameters()['b'], -1.)
        w.sl_ghs_sp.setValue(1700)
        self.assertEqual(w.lbl_ghs_sp.text(), '0.85')
        self.assertEqual(w.sl_ghs_lp.maximum(), 1700)
        self.assertEqual(w.sl_ghs_hp.minimum(), 1700)
        w.sl_ghs_lp.setValue(1600)
        w.sl_ghs_hp.setValue(1800)
        p = w.collect_display_parameters()
        self.assertEqual((p['lp'], p['sp'], p['hp']), (.8, .85, .9))
        w.sl_ghs_sp.setValue(0)
        self.assertEqual(w.sl_ghs_lp.value(), 0)
        w.sl_ghs_sp.setValue(2000)
        self.assertEqual(w.sl_ghs_hp.value(), 2000)
        w.sl_stretch.setValue(0)
        self.assertEqual(w.collect_display_parameters()['strength'], 0.)
        w.combo_stretch_mode.setCurrentIndex(0)
        self.assertEqual(w.sl_stretch.value_label.text(), '10')
        w.combo_stretch_mode.setCurrentIndex(1)
        self.assertEqual(w.sl_stretch.value_label.text(), '10')

    def wheel(self, widget, angle=QPoint(0, -120), pixels=QPoint()):
        event = QWheelEvent(QPointF(widget.rect().center()),
                            QPointF(widget.mapToGlobal(widget.rect().center())),
                            pixels, angle, Qt.MouseButton.NoButton,
                            Qt.KeyboardModifier.NoModifier, Qt.ScrollPhase.NoScrollPhase, False)
        QApplication.sendEvent(widget, event)
        self.app.processEvents()

    def test_wheel_scrolls_sidebar_without_parameter_changes_and_keyboard_still_works(self):
        w = self.window
        w.sec_mgn.toggle_expanded()
        w.sec_mgn.chk_active.setChecked(True)
        w.show()
        self.app.processEvents()
        scroll = w.findChild(QScrollArea)
        bar = scroll.verticalScrollBar()
        self.assertGreater(bar.maximum(), 0)
        slider = w.sl_mgn_gam
        for focused in (False, True):
            slider.setFocus() if focused else slider.clearFocus()
            bar.setValue(bar.maximum() // 2)
            previous = bar.value()
            value = slider.value()
            spy = QSignalSpy(slider.valueChanged)
            self.wheel(slider)
            self.assertGreater(bar.value(), previous)
            self.assertEqual(slider.value(), value)
            self.assertEqual(spy.count(), 0)
            self.wheel(slider, QPoint(0, 120))
            self.assertEqual(bar.value(), previous)
        # Pixel deltas from touchpads are forwarded as well.
        bar.setValue(bar.maximum() // 2)
        previous = bar.value()
        self.wheel(slider, QPoint(0, -120), QPoint(0, -24))
        self.assertGreater(bar.value(), previous)
        combo = w.combo_stretch_mode
        combo.setFocus()
        index = combo.currentIndex()
        bar.setValue(bar.maximum() // 2)
        previous = bar.value()
        self.wheel(combo)
        self.assertEqual(combo.currentIndex(), index)
        self.assertGreater(bar.value(), previous)
        slider.setFocus()
        before = slider.value()
        QTest.keyClick(slider, Qt.Key.Key_Right)
        self.assertEqual(slider.value(), before + 1)
        self.assertEqual(slider.value_label.text(), '3.3')
