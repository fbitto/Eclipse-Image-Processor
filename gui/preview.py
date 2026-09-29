"""Interactive image preview with circle overlay."""

from typing import Optional
from PySide6.QtCore import Qt, Signal, QRect, QPoint
from PySide6.QtGui import QPixmap, QPainter, QPen, QColor
from PySide6.QtWidgets import QLabel


class ClickableLabel(QLabel):
    """Label that displays image with circle overlay and emits click coordinates."""

    image_clicked = Signal(int, int)  # Emits (x, y) in image coordinates

    def __init__(self):
        super().__init__()
        self.pixmap_original: Optional[QPixmap] = None
        self.circle_x: float = 0
        self.circle_y: float = 0
        self.circle_r: float = 100
        self.image_width: int = 1
        self.image_height: int = 1
        self.show_circle: bool = False
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setCursor(Qt.CursorShape.CrossCursor)

    def set_circle_parameters(
        self,
        cx: float,
        cy: float,
        r: float,
        img_width: int,
        img_height: int,
    ):
        """Set circle parameters in image coordinates."""
        self.circle_x = cx
        self.circle_y = cy
        self.circle_r = r
        self.image_width = img_width
        self.image_height = img_height
        self.show_circle = True
        self.update()

    def setPixmap(self, pixmap: QPixmap):
        """Override to store original pixmap."""
        self.pixmap_original = pixmap
        super().setPixmap(pixmap)
        self.update()

    def paintEvent(self, event):
        """Paint image with circle overlay."""
        super().paintEvent(event)

        if not self.pixmap_original or not self.show_circle:
            return

        # Get displayed pixmap size and position
        displayed_pixmap = self.pixmap()
        if not displayed_pixmap:
            return

        # Calculate scaling factor from image to displayed pixmap
        display_width = displayed_pixmap.width()
        display_height = displayed_pixmap.height()
        scale_x = display_width / self.image_width
        scale_y = display_height / self.image_height

        # Convert circle center from image coordinates to display coordinates
        circle_x_display = self.circle_x * scale_x
        circle_y_display = self.circle_y * scale_y
        circle_r_display = self.circle_r * scale_x  # Use scale_x (assume square pixels)

        # Get label geometry
        label_rect = self.rect()
        label_width = label_rect.width()
        label_height = label_rect.height()

        # Calculate position of displayed pixmap within label (centered)
        x_offset = (label_width - display_width) / 2
        y_offset = (label_height - display_height) / 2

        # Convert display coordinates to label coordinates
        circle_x_label = x_offset + circle_x_display
        circle_y_label = y_offset + circle_y_display

        # Draw circle
        painter = QPainter(self)
        pen = QPen(QColor(255, 0, 0))  # Red circle
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawEllipse(
            int(circle_x_label - circle_r_display),
            int(circle_y_label - circle_r_display),
            int(2 * circle_r_display),
            int(2 * circle_r_display),
        )

        # Draw crosshair
        crosshair_size = 15
        pen.setColor(QColor(255, 100, 100))
        pen.setWidth(1)
        painter.setPen(pen)
        painter.drawLine(
            int(circle_x_label - crosshair_size),
            int(circle_y_label),
            int(circle_x_label + crosshair_size),
            int(circle_y_label),
        )
        painter.drawLine(
            int(circle_x_label),
            int(circle_y_label - crosshair_size),
            int(circle_x_label),
            int(circle_y_label + crosshair_size),
        )

        painter.end()

    def mousePressEvent(self, event):
        """Handle mouse click to get image coordinates."""
        if not self.pixmap_original or not self.show_circle:
            return

        displayed_pixmap = self.pixmap()
        if not displayed_pixmap:
            return

        # Get click position in label coordinates
        click_x_label = event.position().x()
        click_y_label = event.position().y()

        # Get displayed pixmap size and position
        display_width = displayed_pixmap.width()
        display_height = displayed_pixmap.height()

        # Get label geometry
        label_rect = self.rect()
        label_width = label_rect.width()
        label_height = label_rect.height()

        # Calculate offset of displayed pixmap within label
        x_offset = (label_width - display_width) / 2
        y_offset = (label_height - display_height) / 2

        # Convert click from label coordinates to display coordinates
        click_x_display = click_x_label - x_offset
        click_y_display = click_y_label - y_offset

        # Check if click is within displayed pixmap
        if (
            click_x_display < 0
            or click_x_display > display_width
            or click_y_display < 0
            or click_y_display > display_height
        ):
            return

        # Convert from display coordinates to image coordinates
        scale_x = display_width / self.image_width
        scale_y = display_height / self.image_height

        click_x_image = int(click_x_display / scale_x)
        click_y_image = int(click_y_display / scale_y)

        # Emit signal with image coordinates
        self.image_clicked.emit(click_x_image, click_y_image)
