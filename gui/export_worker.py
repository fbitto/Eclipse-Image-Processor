"""File export has no widgets and reports completion through QThread.finished."""
from PySide6.QtCore import QThread
from core.export import export_images


class ExportThread(QThread):
    def __init__(self, request, parent=None):
        super().__init__(parent)
        self.request = request
        self.message = None
        self.error = None

    def run(self):
        try:
            self.message = export_images(**self.request)
        except Exception as error:
            self.error = str(error)
