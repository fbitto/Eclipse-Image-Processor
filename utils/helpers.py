"""Utility helper functions."""

import os
import sys


def resource_path(relative_path: str) -> str:
    """Resolves absolute resource path compatible with dev and frozen executables."""
    base_path = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base_path, relative_path)
