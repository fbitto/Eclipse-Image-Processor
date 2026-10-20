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
Eclipse Image Processor v0.5.0 - Application entry point
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

from PySide6.QtGui import QColor, QIcon, QPalette
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon, QToolTip

from config import LIGHTROOM_QSS
from gui.app import EclipseProcessorApp
from utils.helpers import application_icon_path, resource_path


def main():
    """Launch the application."""
    if sys.platform == "win32":
        myappid = "astronomy.eclipse.filters.v1_3"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    app = QApplication(sys.argv)
    app.setApplicationName("Eclipse Image Processor")
    app.setApplicationDisplayName("Eclipse Image Processor")
    app.setStyle("Fusion")
    app.setStyleSheet(LIGHTROOM_QSS)
    # Tooltips use the inactive palette on some platforms. Set every group so
    # native tooltip painting also keeps the same opaque, high-contrast colours.
    tooltip_palette = QToolTip.palette()
    for group in (QPalette.ColorGroup.Active, QPalette.ColorGroup.Inactive, QPalette.ColorGroup.Disabled):
        tooltip_palette.setColor(group, QPalette.ColorRole.ToolTipBase, QColor("#151a21"))
        tooltip_palette.setColor(group, QPalette.ColorRole.ToolTipText, QColor("#f5f7fa"))
    QToolTip.setPalette(tooltip_palette)

    app.setWindowIcon(QIcon(application_icon_path()))

    window = EclipseProcessorApp()
    if QSystemTrayIcon.isSystemTrayAvailable():
        # The small PNG is also readable by the macOS menu bar icon renderer.
        tray = QSystemTrayIcon(QIcon(resource_path("assets/icon-options/03-realce-coronal.png")), window)
        tray.setToolTip("Eclipse Image Processor")
        menu = QMenu(window)

        def show_window():
            if window.isMinimized():
                window.showNormal()
            else:
                window.show()
            window.raise_()
            window.activateWindow()

        show_action = menu.addAction("Show window", show_window)
        show_action.setToolTip("Show or restore the main application window")
        menu.addSeparator()
        quit_action = menu.addAction("Quit", window.close)
        quit_action.setToolTip("Close the application after the current worker finishes")
        tray.setContextMenu(menu)
        tray.show()

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
