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
from PySide6.QtWidgets import QApplication

from config import LIGHTROOM_QSS
from gui.app import EclipseProcessorApp
from utils.helpers import resource_path


def main():
    """Launch the application."""
    if sys.platform == "win32":
        myappid = "astronomy.eclipse.filters.v1_3"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(LIGHTROOM_QSS)

    icon_file = resource_path("icono.ico") if os.path.exists(resource_path("icono.ico")) else resource_path("icono.png")
    if os.path.exists(icon_file):
        app.setWindowIcon(QIcon(icon_file))

    window = EclipseProcessorApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
