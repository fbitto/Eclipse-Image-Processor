"""Utility helper functions."""

import os
import sys


def resource_path(relative_path: str) -> str:
    """Resolves absolute resource path compatible with dev and frozen executables."""
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base_path, relative_path)


def application_icon_path() -> str:
    """Use ICO on Windows and PNG elsewhere, avoiding Qt's ICNS decoder."""
    extension = "ico" if sys.platform == "win32" else "png"
    base = "assets/icon-options/03-realce-coronal"
    native_path = resource_path(f"{base}.{extension}")
    return native_path if os.path.isfile(native_path) else resource_path(f"{base}.png")
