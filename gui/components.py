"""Reusable UI components: ClickableLabel, CollapsibleSection."""

from typing import Optional

import numpy as np
from shiboken6 import isValid
from PySide6.QtCore import QEvent, QObject, QPoint, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
    QToolTip,
)


class InWindowTooltips(QObject):
    """Opaque child overlay: no native tooltip window or cross-app overlap."""

    class Panel(QWidget):
        def paintEvent(self, event):
            painter = QPainter(self)
            painter.fillRect(self.rect(), QColor("#151a21"))
            painter.setPen(QColor("#8796a8"))
            painter.drawRect(self.rect().adjusted(0, 0, -1, -1))

    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.panel = self.Panel(window)
        self.panel.setObjectName("inWindowTooltip")
        self.panel.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.panel.setAutoFillBackground(False)
        self.label = QLabel(self.panel)
        self.label.setTextFormat(Qt.TextFormat.PlainText)
        self.label.setWordWrap(True)
        self.label.setStyleSheet("QLabel { color: #f5f7fa; background: transparent; border: none; font-size: 12px; font-weight: normal; }")
        self.panel.hide()
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.panel.hide)
        QApplication.instance().installEventFilter(self)

    def show_text(self, widget, position):
        text = widget.toolTip()
        if not text:
            return
        width = min(420, max(1, self.window.width()-24))
        self.label.setFixedWidth(max(1, width-22))
        self.label.setText(text)
        height = min(self.window.height()-24,
                     self.label.heightForWidth(self.label.width())+18)
        self.panel.resize(width, max(24, height))
        self.label.setGeometry(11, 9, width-22, self.panel.height()-18)
        point = widget.mapTo(self.window, position)
        x = min(max(12, point.x()+12), self.window.width()-width-12)
        y = point.y()+20
        if y+self.panel.height() > self.window.height()-12:
            y = point.y()-self.panel.height()-16
        y = min(max(12, y), self.window.height()-self.panel.height()-12)
        self.panel.move(x, y)
        self.panel.raise_()
        self.panel.show()
        self.timer.start(10000)

    def detach(self):
        self.timer.stop()
        self.panel.hide()
        QApplication.instance().removeEventFilter(self)

    def eventFilter(self, watched, event):
        if not isValid(self.window) or not isValid(self.panel):
            return False
        belongs = isinstance(watched, QWidget) and (watched is self.window or self.window.isAncestorOf(watched))
        kind = event.type()
        if kind == QEvent.Type.ToolTip and belongs:
            QToolTip.hideText()
            self.show_text(watched, event.pos())
            event.accept()
            return True
        if kind in (QEvent.Type.MouseMove, QEvent.Type.MouseButtonPress, QEvent.Type.Wheel,
                    QEvent.Type.Leave, QEvent.Type.ApplicationDeactivate):
            self.panel.hide()
        if watched is self.window and kind in (QEvent.Type.Hide, QEvent.Type.Resize,
                                               QEvent.Type.Move, QEvent.Type.WindowDeactivate):
            self.panel.hide()
        return False


class FullRowCheckBox(QCheckBox):
    """Make label and trailing row whitespace one consistent click target."""

    def hitButton(self, position):
        return self.rect().contains(position)


class ClickableLabel(QLabel):
    """Interactive image viewer with dynamic geometric projection in real-time."""

    image_clicked = Signal(int, int)
    circle_center_requested = Signal(int, int)

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
                # Qt maps Command on macOS to ControlModifier by default.
                if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                    self.circle_center_requested.emit(orig_x, orig_y)
                else:
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
        self.toggle_btn.setToolTip(f"Expand or collapse {title} controls.")
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
            self.chk_active.setToolTip(f"Enable or bypass {title} without resetting its controls.")
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
