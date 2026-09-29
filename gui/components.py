"""GUI components for EclipseProcessorApp."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLabel, QWidget, QVBoxLayout, QCheckBox, QPushButton
from PySide6.QtGui import QPainter, QPen, QColor


class ClickableLabel(QLabel):
    """QLabel that emits signals on click and Ctrl+click."""
    
    image_clicked = Signal(int, int)  # Normal click
    image_ctrl_clicked = Signal(int, int)  # Ctrl+Click
    
    def __init__(self):
        super().__init__()
        self.circle_cx = 0
        self.circle_cy = 0
        self.circle_r = 0
        self.native_w = 0
        self.native_h = 0
    
    def mousePressEvent(self, event):
        """Handle mouse click with modifier support."""
        if self.pixmap() is None:
            return
        
        # Get click position in label coordinates
        x = event.position().x()
        y = event.position().y()
        
        # Convert to image coordinates
        pixmap = self.pixmap()
        if pixmap.isNull():
            return
        
        label_w, label_h = self.width(), self.height()
        pixmap_w, pixmap_h = pixmap.width(), pixmap.height()
        
        # Calculate scaling (centered, aspect ratio preserved)
        scale_x = pixmap_w / label_w if label_w > 0 else 1.0
        scale_y = pixmap_h / label_h if label_h > 0 else 1.0
        
        # Offset for centered image
        offset_x = (label_w - pixmap_w / max(scale_x, scale_y)) / 2.0
        offset_y = (label_h - pixmap_h / max(scale_x, scale_y)) / 2.0
        
        # Convert to image coordinates
        img_x = int((x - offset_x) * max(scale_x, scale_y))
        img_y = int((y - offset_y) * max(scale_x, scale_y))
        
        # Convert preview coords to full resolution if needed
        if self.native_w > 0 and self.native_h > 0:
            preview_w = self.pixmap().width()
            preview_h = self.pixmap().height()
            scale_to_native = self.native_w / preview_w if preview_w > 0 else 1.0
            img_x = int(img_x * scale_to_native)
            img_y = int(img_y * scale_to_native)
        
        # Check for Ctrl modifier
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.image_ctrl_clicked.emit(img_x, img_y)
        else:
            self.image_clicked.emit(img_x, img_y)
    
    def set_circle_parameters(self, cx, cy, r, native_w=0, native_h=0):
        """Set circle parameters for overlay drawing."""
        self.circle_cx = cx
        self.circle_cy = cy
        self.circle_r = r
        self.native_w = native_w
        self.native_h = native_h
        self.update()
    
    def paintEvent(self, event):
        """Paint the label with circle overlay."""
        super().paintEvent(event)
        
        if self.circle_r <= 0 or self.pixmap() is None:
            return
        
        # Draw circle overlay
        painter = QPainter(self)
        pen = QPen(QColor(255, 165, 0, 200))  # Orange with transparency
        pen.setWidth(2)
        painter.setPen(pen)
        
        # Calculate scaling from native to display
        if self.native_w > 0 and self.native_h > 0:
            pixmap = self.pixmap()
            preview_w = pixmap.width()
            preview_h = pixmap.height()
            scale = preview_w / self.native_w if self.native_w > 0 else 1.0
            
            # Convert to preview coordinates
            cx_preview = int(self.circle_cx * scale)
            cy_preview = int(self.circle_cy * scale)
            r_preview = int(self.circle_r * scale)
            
            # Calculate label offset
            label_w, label_h = self.width(), self.height()
            scale_factor = max(preview_w / label_w, preview_h / label_h) if label_w > 0 and label_h > 0 else 1.0
            offset_x = (label_w - preview_w / scale_factor) / 2.0
            offset_y = (label_h - preview_h / scale_factor) / 2.0
            
            # Draw circle
            display_cx = offset_x + cx_preview / scale_factor
            display_cy = offset_y + cy_preview / scale_factor
            display_r = r_preview / scale_factor
            
            painter.drawEllipse(int(display_cx - display_r), int(display_cy - display_r),
                              int(display_r * 2), int(display_r * 2))
        
        painter.end()


class CollapsibleSection(QWidget):
    """Collapsible section with checkbox and content area."""
    
    toggled_active = Signal(bool)
    
    def __init__(self, title: str, has_checkbox: bool = True, is_expanded: bool = True, is_active: bool = False):
        super().__init__()
        self.title = title
        self.has_checkbox = has_checkbox
        self.is_expanded = is_expanded
        self.is_filter_active_flag = is_active
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header with expand/collapse and checkbox
        header_layout = QVBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(0)
        
        if has_checkbox:
            self.checkbox = QCheckBox(f"▼ {title}" if is_expanded else f"▶ {title}")
            self.checkbox.setChecked(is_active)
            self.checkbox.setStyleSheet("""
                QCheckBox {
                    color: #ffffff;
                    font-weight: bold;
                    font-size: 11px;
                    spacing: 6px;
                }
                QCheckBox::indicator {
                    width: 0px;
                    height: 0px;
                }
            """)
            self.checkbox.stateChanged.connect(self._on_checkbox_changed)
            header_layout.addWidget(self.checkbox)
        else:
            self.header_btn = QPushButton(f"▼ {title}" if is_expanded else f"▶ {title}")
            self.header_btn.setFlat(True)
            self.header_btn.setStyleSheet("""
                QPushButton {
                    color: #ffffff;
                    font-weight: bold;
                    font-size: 11px;
                    text-align: left;
                    padding: 4px;
                    border: none;
                }
                QPushButton:hover {
                    background-color: #3c3c3c;
                }
            """)
            self.header_btn.clicked.connect(self._toggle_expand)
            header_layout.addWidget(self.header_btn)
        
        layout.addLayout(header_layout)
        
        # Content area
        self.content_layout = QVBoxLayout()
        self.content_layout.setContentsMargins(12, 6, 6, 6)
        self.content_layout.setSpacing(6)
        layout.addLayout(self.content_layout)
        
        # Show/hide content based on expanded state
        if not is_expanded:
            self._set_content_visible(False)
    
    def _on_checkbox_changed(self, state):
        """Handle checkbox state change."""
        self.is_filter_active_flag = self.checkbox.isChecked()
        
        # Update arrow
        arrow = "▼" if self.is_expanded else "▶"
        self.checkbox.setText(f"{arrow} {self.title}")
        
        self.toggled_active.emit(self.is_filter_active_flag)
    
    def _toggle_expand(self):
        """Toggle expansion state."""
        self.is_expanded = not self.is_expanded
        arrow = "▼" if self.is_expanded else "▶"
        self.header_btn.setText(f"{arrow} {self.title}")
        self._set_content_visible(self.is_expanded)
    
    def _set_content_visible(self, visible: bool):
        """Show or hide content area."""
        for i in range(self.content_layout.count()):
            widget = self.content_layout.itemAt(i).widget()
            if widget:
                widget.setVisible(visible)
    
    def is_filter_active(self) -> bool:
        """Check if filter is active (checkbox checked)."""
        if self.has_checkbox:
            return self.checkbox.isChecked()
        return self.is_filter_active_flag
