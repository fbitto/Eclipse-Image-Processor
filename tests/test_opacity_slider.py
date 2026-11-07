"""Nonlinear pointer travel preserves percentage values and recipe semantics."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import unittest

from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest, QSignalSpy
from PySide6.QtWidgets import QApplication, QStyle, QVBoxLayout, QWidget

from gui.app import EclipseProcessorApp
from gui.components import OpacitySlider
from gui.factories import create_slider
from gui.project_settings import capture_settings, restore_settings
from gui_wait import close_window


class OpacitySliderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_styled_slider_paints_track_and_handle(self):
        host = QWidget()
        slider, _ = create_slider('Opacity (%)', 0, 100, 10, QVBoxLayout(host),
                                 slider_class=OpacitySlider)
        host.resize(460, 70)
        host.show()
        try:
            self.app.processEvents()
            option = slider._position_option()
            self.assertTrue(option.subControls & QStyle.SubControl.SC_SliderGroove)
            self.assertTrue(option.subControls & QStyle.SubControl.SC_SliderHandle)
            # The factory styles the handle light grey against a dark track.
            pixels = slider.grab().toImage()
            self.assertGreater(sum(
                pixels.pixelColor(x,y).red() >= 150
                and pixels.pixelColor(x,y).red() == pixels.pixelColor(x,y).green()
                for x in range(pixels.width()) for y in range(pixels.height())), 10)
        finally:
            host.close()

    def test_pointer_curve_endpoints_drag_and_keyboard(self):
        slider = OpacitySlider(Qt.Orientation.Horizontal)
        slider.setRange(0, 100)
        slider.resize(400, 32)
        slider.show()
        try:
            self.app.processEvents()
            option = slider._position_option()
            groove = slider.style().subControlRect(QStyle.ComplexControl.CC_Slider, option,
                                                    QStyle.SubControl.SC_SliderGroove, slider)
            handle = slider.style().subControlRect(QStyle.ComplexControl.CC_Slider, option,
                                                    QStyle.SubControl.SC_SliderHandle, slider)
            start = groove.x()+handle.width()/2
            span = groove.width()-handle.width()
            def point(x):
                return QPoint(round(start+x*span), slider.height()//2)
            released = QSignalSpy(slider.sliderReleased)
            for position, expected in ((0,0), (.25,13), (.5,35), (.75,65), (1,100)):
                QTest.mouseClick(slider, Qt.MouseButton.LeftButton, pos=point(position))
                self.assertAlmostEqual(slider.value(), expected, delta=1)
                self.assertFalse(slider.isSliderDown())
            self.assertEqual(released.count(), 5)
            QTest.mousePress(slider, Qt.MouseButton.LeftButton, pos=point(.5))
            QTest.mouseMove(slider, point(.75))
            QTest.mouseRelease(slider, Qt.MouseButton.LeftButton, pos=point(.75))
            self.assertAlmostEqual(slider.value(), 65, delta=1)
            slider.setValue(10)
            QTest.keyClick(slider, Qt.Key.Key_Right)
            self.assertEqual(slider.value(), 11)
            slider.setValue(25)
            self.assertAlmostEqual(slider._position_option().sliderPosition/10000, .25**(2/3), places=4)
        finally:
            slider.close()

    def test_all_opacities_keep_typed_reset_and_saved_percentages(self):
        window = EclipseProcessorApp()
        window.auto_calculate = False
        try:
            sliders = [getattr(window, 'sl_'+name+'_opacity') for name in
                       ('nrgf','nafe','fnrgf','rhef','mgn','wow','tangential','larson_sekanina','achf')]
            sliders += [controls['opacity'] for controls in window.achf_ael_controls.values()]
            self.assertNotIsInstance(window.sl_larson_sekanina_str, OpacitySlider)
            for slider in sliders:
                self.assertIsInstance(slider, OpacitySlider)
                slider.value_label.setText('37')
                slider.value_label.editingFinished.emit()
                self.assertEqual(slider.value(), 37)
                self.assertEqual(slider.value_label.text(), '37')
            saved = capture_settings(window)
            for slider in sliders:
                slider.setValue(80)
            restore_settings(window, saved)
            for slider in sliders:
                self.assertEqual(slider.value(), 37)
                QTest.mouseDClick(slider, Qt.MouseButton.LeftButton)
                self.assertEqual(slider.value(), slider.property('reset_value'))
        finally:
            close_window(window)
