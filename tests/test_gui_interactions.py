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

    def test_geometry_edits_restart_one_debounce_timer(self):
        self.window.txt_x.setText("20")
        QTest.qWait(180)
        self.window.txt_y.setText("25")
        QTest.qWait(180)
        self.assertEqual(self.requests, [])
        QTest.qWait(180)
        self.assertEqual(len(self.requests), 1)
        self.assertEqual(self.requests[0]["sx"], 20)
        self.assertEqual(self.requests[0]["sy"], 25)

    def test_active_slider_change_is_delayed_and_coalesced(self):
        # Enable without a recomputation; the worker is disconnected in setUp.
        from unittest.mock import patch
        with patch.object(self.window.sec_fnrgf, "is_filter_active", return_value=True):
            self.window.sl_fnrgf_str.setValue(30)
            QTest.qWait(180)
            self.window.sl_fnrgf_str.setValue(31)
            self.window.sl_fnrgf_str.sliderReleased.emit()
            QTest.qWait(180)
            self.assertEqual(self.requests, [])
            QTest.qWait(180)
            self.assertEqual(len(self.requests), 1)
            self.assertEqual(self.requests[0]["fnrgf_str"], 31)

    def test_edit_during_processing_waits_for_pause(self):
        self.window.is_processing = True
        self.window.has_pending_request = True
        self.window.txt_x.setText("21")
        self.window.on_processing_finished(self.window.raw_image.copy())
        self.assertEqual(self.requests, [])
        QTest.qWait(400)
        self.assertEqual(len(self.requests), 1)

    def test_manual_mode_does_not_schedule_and_explicit_calculate_cancels_timer(self):
        self.window.txt_x.setText("21")
        self.window.toggle_auto_calc_mode(False)
        QTest.qWait(400)
        self.assertEqual(self.requests, [])
        self.window.txt_y.setText("22")
        self.assertFalse(self.window.recalculation_timer.isActive())
        self.window.auto_calculate = True
        self.window.dispatch_pipeline_request_if_auto()
        self.window.dispatch_pipeline_request()
        self.assertEqual(len(self.requests), 1)
        self.assertFalse(self.window.recalculation_timer.isActive())
