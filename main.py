# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "astropy>=8.0.1",
#     "numpy>=2.5.3",
#     "opencv-python>=5.0.0.93",
#     "pillow>=12.3.0",
#     "pyside6>=6.11.2",
#     "scipy>=1.18.1",
#     "tifffile>=2026.9.20",
#     "xisf>=0.9.7",
#     "watroo==0.0.4",
# ]
# ///
"""
FiltrosEclipse v0.4.0 - Entry Point
Modular structure for token-efficient development.
"""

import os
import sys

# CPU optimization MUST come before numpy imports
CPU_CORES = os.cpu_count() or 4
os.environ["OMP_NUM_THREADS"] = str(CPU_CORES)
os.environ["OPENBLAS_NUM_THREADS"] = str(CPU_CORES)
os.environ["MKL_NUM_THREADS"] = str(CPU_CORES)
os.environ["VECLIB_MAXIMUM_THREADS"] = str(CPU_CORES)
os.environ["NUMEXPR_NUM_THREADS"] = str(CPU_CORES)

import ctypes
import cv2

cv2.setNumThreads(CPU_CORES)
cv2.setUseOptimized(True)

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from config import LIGHTROOM_QSS
from gui.app import EclipseProcessorApp
from utils.helpers import application_icon_path, resource_path


def main():
    """Launch the application."""
    if sys.platform == "win32":
        myappid = "astronomy.eclipse.filters.v1_3"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    app = QApplication(sys.argv)
    app.setApplicationName("Corona Enhance Filters")
    app.setApplicationDisplayName("Corona Enhance Filters")
    app.setStyle("Fusion")
    app.setStyleSheet(LIGHTROOM_QSS)

    app.setWindowIcon(QIcon(application_icon_path()))

    window = EclipseProcessorApp()
    if QSystemTrayIcon.isSystemTrayAvailable():
        # The small PNG is also readable by the macOS menu bar icon renderer.
        tray = QSystemTrayIcon(QIcon(resource_path("assets/icon-options/03-realce-coronal.png")), window)
        tray.setToolTip("Corona Enhance Filters")
        menu = QMenu(window)

        def show_window():
            if window.isMinimized():
                window.showNormal()
            else:
                window.show()
            window.raise_()
            window.activateWindow()

        menu.addAction("Mostrar ventana", show_window)
        menu.addSeparator()
        menu.addAction("Salir", window.close)
        tray.setContextMenu(menu)
        tray.show()

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
