"""Reusable UI components: ClickableLabel, CollapsibleSection."""

from typing import Optional

import numpy as np
from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class ClickableLabel(QLabel):
    """Interactive image viewer with dynamic geometric projection in real-time."""

    image_clicked = Signal(int, int)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.circle_x: Optional[float] = None
        self.circle_y: Optional[float] = None
        self.circle_r: Optional[float] = None
        self.native_w: Optional[int] = None
        self.native_h: Optional[int] = None

        self.setMinimumSize(1, 1)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)

    def set_circle_parameters(
        self,
        x: float,
        y: float,
        r: float,
        native_w: Optional[int] = None,
        native_h: Optional[int] = None,
    ):
        self.circle_x = x
        self.circle_y = y
        self.circle_r = r
        if native_w is not None and native_h is not None:
            self.native_w = native_w
            self.native_h = native_h
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pix = self.pixmap()
            if pix is None or pix.isNull() or not self.native_w or self.native_w <= 0:
                return

            w_widget, h_widget = self.width(), self.height()
            w_pix, h_pix = pix.width(), pix.height()
            bx = (w_widget - w_pix) // 2
            by = (h_widget - h_pix) // 2

            pos = event.position().toPoint()
            if bx <= pos.x() <= bx + w_pix and by <= pos.y() <= by + h_pix:
                scale = w_pix / float(self.native_w)
                orig_x = int((pos.x() - bx) / scale)
                orig_y = int((pos.y() - by) / scale)
                self.image_clicked.emit(orig_x, orig_y)

    def paintEvent(self, event):
        super().paintEvent(event)
        pix = self.pixmap()
        if pix is None or pix.isNull() or not self.native_w or self.native_w <= 0:
            return

        if self.circle_x is not None and self.circle_y is not None and self.circle_r is not None:
            w_widget, h_widget = self.width(), self.height()
            w_pix, h_pix = pix.width(), pix.height()
            bx = (w_widget - w_pix) // 2
            by = (h_widget - h_pix) // 2
            scale = w_pix / float(self.native_w)

            screen_x = int(self.circle_x * scale) + bx
            screen_y = int(self.circle_y * scale) + by
            screen_r = int(self.circle_r * scale)

            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            pen = QPen(QColor(255, 50, 50, 220), 2, Qt.PenStyle.SolidLine)
            painter.setPen(pen)

            painter.drawEllipse(QPoint(screen_x, screen_y), screen_r, screen_r)
            painter.drawLine(screen_x - 6, screen_y, screen_x + 6, screen_y)
            painter.drawLine(screen_x, screen_y - 6, screen_x, screen_y + 6)


class CollapsibleSection(QWidget):
    """Collapsible UI container with optional filter enable/bypass checkbox."""

    toggled_active = Signal(bool)

    def __init__(
        self,
        title: str,
        has_checkbox: bool = False,
        is_expanded: bool = True,
        is_active: bool = True,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.title_text = title
        self.has_checkbox = has_checkbox
        self.is_expanded = is_expanded

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 2, 0, 2)
        main_layout.setSpacing(2)

        self.header_frame = QFrame()
        self.header_frame.setStyleSheet("""
            QFrame {
                background-color: #333333;
                border: 1px solid #3d3d3d;
                border-radius: 3px;
            }
            QFrame:hover {
                background-color: #3a3a3a;
                border-color: #4a4a4a;
            }
        """)
        header_layout = QHBoxLayout(self.header_frame)
        header_layout.setContentsMargins(8, 4, 8, 4)
        header_layout.setSpacing(6)

        self.toggle_btn = QPushButton()
        self.toggle_btn.setFlat(True)
        self.toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #e0e0e0;
                font-weight: 700;
                font-size: 11px;
                border: none;
                text-align: left;
                padding: 0px;
                letter-spacing: 0.5px;
            }
            QPushButton:hover {
                color: #ffffff;
            }
        """)
        self.toggle_btn.clicked.connect(self.toggle_expanded)
        header_layout.addWidget(self.toggle_btn, stretch=1)

        if self.has_checkbox:
            self.chk_active = QCheckBox("Active")
            self.chk_active.setChecked(is_active)
            self.chk_active.setCursor(Qt.CursorShape.PointingHandCursor)
            self.chk_active.setStyleSheet("""
                QCheckBox {
                    background: transparent;
                    color: #a0a0a0;
                    font-size: 11px;
                    font-weight: 600;
                    spacing: 5px;
                }
                QCheckBox:hover {
                    color: #ffffff;
                }
                QCheckBox::indicator {
                    width: 13px;
                    height: 13px;
                    border-radius: 2px;
                    border: 1px solid #4a4a4a;
                    background-color: #1e1e1e;
                }
                QCheckBox::indicator:hover {
                    border: 1px solid #707070;
                    background-color: #282828;
                }
                QCheckBox::indicator:checked {
                    background-color: #e5a00d;
                    border: 1px solid #f5b025;
                }
            """)
            self.chk_active.toggled.connect(self._on_active_toggled)
            header_layout.addWidget(self.chk_active)
        else:
            self.chk_active = None

        main_layout.addWidget(self.header_frame)

        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("background-color: #282828; border-radius: 3px;")
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(6, 6, 6, 6)
        self.content_layout.setSpacing(5)
        self.content_widget.setVisible(self.is_expanded)
        # Note: We do NOT disable content_widget initially, even if not active.
        # Users should be able to configure filter parameters before enabling the filter.

        main_layout.addWidget(self.content_widget)
        self._update_header_text()

    def _update_header_text(self):
        arrow = "▼" if self.is_expanded else "▶"
        self.toggle_btn.setText(f"{arrow}  {self.title_text}")

    def toggle_expanded(self):
        self.is_expanded = not self.is_expanded
        self.content_widget.setVisible(self.is_expanded)
        self._update_header_text()

    def _on_active_toggled(self, checked: bool):
        """Handle checkbox toggle. Sliders remain enabled for configuration."""
        # Note: We do NOT disable content_widget when unchecked.
        # This allows users to adjust filter parameters even when the filter is inactive.
        # The pipeline will skip disabled filters anyway.
        self.toggled_active.emit(checked)

    def is_filter_active(self) -> bool:
        if self.has_checkbox and self.chk_active is not None:
            return self.chk_active.isChecked()
        return True
