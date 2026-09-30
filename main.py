#!/usr/bin/env python3
"""Main entry point for FiltrosEclipse application."""

import sys
from PySide6.QtWidgets import QApplication
from gui.app import EclipseProcessorApp


def main():
    """Launch the application."""
    app = QApplication(sys.argv)
    window = EclipseProcessorApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
