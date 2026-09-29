"""Collapsible section widget for filter controls."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QCheckBox,
    QWidget,
)


class CollapsibleSection(QFrame):
    """Collapsible section with optional checkbox."""

    toggled = Signal(bool)  # Emitted when expanded/collapsed or checkbox toggled

    def __init__(
        self,
        title: str,
        has_checkbox: bool = False,
        is_active: bool = False,
        is_expanded: bool = True,
    ):
        super().__init__()
        self.title = title
        self.is_expanded = is_expanded
        self.has_checkbox = has_checkbox
        self.checkbox: QCheckBox = None

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background-color: #2b2b2b;
                border-top: 1px solid #3d3d3d;
                border-bottom: 1px solid #3d3d3d;
            }
        """)
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(8, 6, 8, 6)
        header_layout.setSpacing(6)

        # Expand/collapse button
        self.btn_toggle = QPushButton()
        self.btn_toggle.setFixedSize(16, 16)
        self.btn_toggle.setFlat(True)
        self.btn_toggle.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                color: #888;
                font-weight: bold;
                font-size: 12px;
                padding: 0;
            }
            QPushButton:hover {
                color: #aaa;
            }
        """)
        self.btn_toggle.clicked.connect(self._toggle_expansion)
        self._update_button_text()
        header_layout.addWidget(self.btn_toggle)

        # Title label
        title_label = QLabel(title.upper())
        title_label.setStyleSheet("""
            QLabel {
                background: transparent;
                color: #e5a00d;
                font-weight: 700;
                font-size: 11px;
                letter-spacing: 0.8px;
            }
        """)
        header_layout.addWidget(title_label)

        # Checkbox (if enabled)
        if has_checkbox:
            self.checkbox = QCheckBox()
            self.checkbox.setChecked(is_active)
            self.checkbox.setStyleSheet("""
                QCheckBox {
                    background-color: transparent;
                    color: #888;
                    font-size: 10px;
                    spacing: 3px;
                }
                QCheckBox::indicator {
                    width: 12px;
                    height: 12px;
                    border-radius: 2px;
                    border: 1px solid #4a4a4a;
                    background-color: #1e1e1e;
                }
                QCheckBox::indicator:hover {
                    border: 1px solid #707070;
                }
                QCheckBox::indicator:checked {
                    background-color: #e5a00d;
                    border: 1px solid #f5b025;
                }
            """)
            self.checkbox.stateChanged.connect(lambda: self.toggled.emit(self.is_active()))
            header_layout.addWidget(self.checkbox)

        header_layout.addStretch()
        main_layout.addWidget(header_frame)

        # Content area
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(2)
        main_layout.addWidget(self.content_widget)

        # Set initial visibility
        self.content_widget.setVisible(is_expanded)
        self.is_expanded = is_expanded

    def _toggle_expansion(self):
        """Toggle expanded/collapsed state."""
        self.is_expanded = not self.is_expanded
        self.content_widget.setVisible(self.is_expanded)
        self._update_button_text()

    def _update_button_text(self):
        """Update button text based on expansion state."""
        self.btn_toggle.setText("▼" if self.is_expanded else "▶")

    def is_active(self) -> bool:
        """Check if section is active (checkbox checked or no checkbox)."""
        if self.has_checkbox and self.checkbox:
            return self.checkbox.isChecked()
        return True  # If no checkbox, always active

    def is_filter_active(self) -> bool:
        """Alias for is_active() for backward compatibility."""
        return self.is_active()

    def set_active(self, active: bool):
        """Set active state if has checkbox."""
        if self.has_checkbox and self.checkbox:
            self.checkbox.setChecked(active)
