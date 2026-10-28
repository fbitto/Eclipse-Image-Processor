"""Export runs away from Qt's GUI thread and always restores its controls."""
from gui_wait import close_window

import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import tempfile
from pathlib import Path
from threading import Event
import unittest
from unittest.mock import patch
import numpy as np
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from PySide6.QtCore import QTimer
from gui.app import EclipseProcessorApp


class ExportWorkerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_missing_attribute_reports_full_console_traceback(self):
        import io
        from contextlib import redirect_stderr
        from gui.export_worker import ExportThread
        thread=ExportThread({})
        output=io.StringIO()
        with patch('gui.export_worker.export_images',side_effect=AttributeError("'LayerEngine' object has no attribute 'prepare'")):
            with redirect_stderr(output):
                thread.run()
        self.assertIn("has no attribute 'prepare'",thread.error)
        self.assertIn('Traceback (most recent call last)',output.getvalue())
        self.assertIn("has no attribute 'prepare'",output.getvalue())

    def test_source_destination_is_rejected_and_pending_preview_resumes(self):
        w = EclipseProcessorApp()
        w.auto_calculate = False
        image = np.ones((8, 10), np.float32)
        w.full_raw_image = image
        w.raw_image = image.copy()
        w.preview_image = image.copy()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                source = Path(tmp)/'source.tif'
                source.write_bytes(b'original')
                w.source_path = str(source)
                w.recalculation_timer.start(10000)
                with patch('gui.app.QFileDialog.getSaveFileName', return_value=(str(source), '')), \
                     patch('gui.app.QMessageBox.question') as question, \
                     patch('gui.app.ExportThread') as worker, \
                     patch.object(w, 'dispatch_pipeline_request_if_auto') as resume:
                    w.export_image_action()
                    worker.assert_not_called()
                    question.assert_not_called()
                    resume.assert_called_once()
                    self.assertIn('original image', w.status_label.text())
                    self.assertEqual(source.read_bytes(), b'original')
        finally:
            close_window(w)

    def test_companion_collisions_require_one_confirmation_before_worker(self):
        from PySide6.QtWidgets import QMessageBox
        w = EclipseProcessorApp()
        w.auto_calculate = False
        image = np.ones((8, 10), np.float32)
        w.full_raw_image = image
        w.raw_image = image.copy()
        w.preview_image = image.copy()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                target = Path(tmp)/'new.tif'
                jpeg = Path(tmp)/'new_preview.jpg'
                settings = Path(tmp)/'new.json'
                jpeg.write_bytes(b'old preview')
                settings.write_bytes(b'old settings')
                for answer in (QMessageBox.StandardButton.No, QMessageBox.StandardButton.Yes):
                    with patch('gui.app.QFileDialog.getSaveFileName', return_value=(str(target), '')), \
                         patch('gui.app.QMessageBox.question', return_value=answer) as question, \
                         patch('gui.app.ExportThread') as worker:
                        w.export_image_action()
                        question.assert_called_once()
                        self.assertIn(str(jpeg), question.call_args.args[2])
                        self.assertIn(str(settings), question.call_args.args[2])
                        self.assertEqual(worker.called, answer == QMessageBox.StandardButton.Yes)
                        if worker.called:
                            worker.return_value.start.assert_called_once()
                            w._export_thread = None
                self.assertEqual(jpeg.read_bytes(), b'old preview')
                self.assertEqual(settings.read_bytes(), b'old settings')
        finally:
            close_window(w)

    def test_snapshot_worker_keeps_event_loop_running_and_handles_failure(self):
        for fail in (False, True):
            w = EclipseProcessorApp()
            w.auto_calculate = False
            a = np.ones((32, 40), np.float32)
            w.full_raw_image = a
            w.raw_image = a.copy()
            w.preview_image = a.copy()
            w.txt_x.setText('20'); w.txt_y.setText('16'); w.txt_r.setText('4')
            entered, release = Event(), Event()
            captured = []
            def export(**request):
                captured.append(request)
                request["progress"](35,"Calculating filters")
                entered.set()
                if not release.wait(3):
                    raise AssertionError('Test did not release export')
                if fail:
                    raise OSError('simulated write failure')
                return 'Status: Exported test.tiff + preview'
            try:
                with tempfile.TemporaryDirectory() as tmp, \
                     patch('gui.app.QFileDialog.getSaveFileName', return_value=(str(Path(tmp)/'test.tiff'), '')), \
                     patch('gui.export_worker.export_images', side_effect=export):
                    w.export_image_action()
                    self.assertTrue(entered.wait(3))
                    self.assertFalse(w.control_sidebar.isEnabled())
                    ticks = []
                    QTimer.singleShot(0, lambda: ticks.append('responsive'))
                    QTest.qWait(30)
                    self.assertEqual(ticks, ['responsive'])
                    self.assertEqual(w.export_progress.value(),35)
                    self.assertIn('Calculating filters',w.export_progress.format())
                    # Work owns a source copy and a captured recipe.
                    a[:] = 9
                    np.testing.assert_array_equal(captured[0]['source'], 1)
                    self.assertEqual(captured[0]['parameters']['sx'], 20)
                    self.assertFalse(captured[0].get('export_linear', False))
                    self.assertEqual(captured[0]['layers_format'],'psb')
                    self.assertFalse(hasattr(w, 'chk_export_linear'))
                    release.set()
                    self.assertTrue(w._export_thread.wait(3000))
                    self.app.processEvents()
                    self.assertIsNone(w._export_thread)
                    self.assertEqual(w.export_progress.format(),'Export failed' if fail else 'Export complete')
                    self.assertTrue(w.control_sidebar.isEnabled())
                    self.assertIn('simulated write failure' if fail else 'Exported test.tiff', w.status_label.text())
                    self.assertIn('simulated write failure' if fail else 'Exported test.tiff', w.status_label.toolTip())
            finally:
                release.set()
                close_window(w)
