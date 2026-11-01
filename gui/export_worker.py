"""File export has no widgets and reports completion through QThread.finished."""
import traceback
from threading import Event
from PySide6.QtCore import QThread, Signal
from core.export import export_images
from core.cancellation import ProcessingCancelled,cancellation_scope


class ExportThread(QThread):
    progress = Signal(int,str)

    def __init__(self, request, parent=None):
        super().__init__(parent)
        self.request = request
        self.message = None
        self.error = None
        self.cancelled = False
        self.publishing = False
        self._cancel_event = Event()

    def cancel(self):
        if self.publishing:return False
        self._cancel_event.set()
        return True

    def report_progress(self,value,label):
        if label == 'Publishing export':self.publishing=True
        self.progress.emit(value,label)

    def run(self):
        try:
            with cancellation_scope(self._cancel_event,check_at_exit=False):
                self.message = export_images(**self.request,progress=self.report_progress)
        except ProcessingCancelled:
            self.cancelled=True
            self.message='Status: Export cancelled; completed companion packages may remain'
        except Exception as error:
            self.error = str(error)
            traceback.print_exc()
