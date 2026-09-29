"""QSS stylesheets for the application."""

# Adobe Lightroom-inspired dark theme
DARK_STYLESHEET = """
QMainWindow {
    background-color: #1a1a1a;
    color: #e0e0e0;
}

QWidget {
    background-color: #1a1a1a;
    color: #e0e0e0;
}

QMenuBar {
    background-color: #2a2a2a;
    color: #e0e0e0;
    border-bottom: 1px solid #3a3a3a;
}

QMenuBar::item:selected {
    background-color: #3a3a3a;
}

QMenu {
    background-color: #2a2a2a;
    color: #e0e0e0;
    border: 1px solid #3a3a3a;
}

QMenu::item:selected {
    background-color: #1a5f7a;
}

QStatusBar {
    background-color: #2a2a2a;
    color: #aaa;
    border-top: 1px solid #3a3a3a;
}

QScrollArea {
    background-color: #1a1a1a;
    border: none;
}

QScrollBar:vertical {
    background-color: #1a1a1a;
    width: 10px;
    border: none;
}

QScrollBar::handle:vertical {
    background-color: #444;
    border-radius: 5px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background-color: #555;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    border: none;
    background: none;
}

QScrollBar:horizontal {
    background-color: #1a1a1a;
    height: 10px;
    border: none;
}

QScrollBar::handle:horizontal {
    background-color: #444;
    border-radius: 5px;
    min-width: 20px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #555;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    border: none;
    background: none;
}

QPushButton {
    background-color: #2a3a4a;
    color: #ddd;
    border: 1px solid #3a4a5a;
    border-radius: 3px;
    padding: 5px 10px;
    font-weight: bold;
    font-size: 11px;
}

QPushButton:hover {
    background-color: #3a4a5a;
    border: 1px solid #4a5a6a;
}

QPushButton:pressed {
    background-color: #1a2a3a;
    border: 1px solid #2a3a4a;
}

QPushButton:disabled {
    background-color: #1a1a1a;
    color: #666;
    border: 1px solid #333;
}

QLabel {
    color: #e0e0e0;
    background-color: transparent;
}

QLineEdit {
    background-color: #111;
    color: #fff;
    border: 1px solid #282828;
    border-radius: 4px;
    padding: 3px 5px;
    font-weight: bold;
    font-size: 11px;
    selection-background-color: #1a5f7a;
}

QLineEdit:focus {
    border: 1px solid #3a5f7a;
    background-color: #1a1a1a;
}

QSlider::groove:horizontal {
    background-color: #2a2a2a;
    border: 1px solid #3a3a3a;
    height: 6px;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background-color: #e5a00d;
    border: 1px solid #f5b025;
    width: 14px;
    margin: -4px 0;
    border-radius: 7px;
}

QSlider::handle:horizontal:hover {
    background-color: #f5b025;
}

QSlider::sub-page:horizontal {
    background-color: #1a5f7a;
    border-radius: 3px;
}

QCheckBox {
    background-color: transparent;
    color: #a0a0a0;
    font-size: 11px;
    font-weight: 600;
    spacing: 5px;
}

QCheckBox:hover {
    color: #fff;
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

QComboBox {
    background-color: #1a1a1a;
    color: #ddd;
    border: 1px solid #333;
    border-radius: 3px;
    padding: 3px 5px;
}

QComboBox:hover {
    border: 1px solid #444;
}

QComboBox::drop-down {
    border: none;
    background-color: transparent;
}

QComboBox::down-arrow {
    image: none;
    width: 10px;
    height: 10px;
}

QProgressBar {
    border: 1px solid #333;
    border-radius: 4px;
    background-color: #1e1e1e;
    text-align: center;
    color: #aaa;
    height: 20px;
}

QProgressBar::chunk {
    background-color: #e5a00d;
    border-radius: 3px;
}

QFrame {
    background-color: #1a1a1a;
    color: #e0e0e0;
}

QSplitter::handle {
    background-color: #2a2a2a;
    border: 1px solid #3a3a3a;
}

QSplitter::handle:hover {
    background-color: #3a3a3a;
}

QToolTip {
    background-color: #2a2a2a;
    color: #ddd;
    border: 1px solid #3a3a3a;
    border-radius: 3px;
    padding: 3px;
}

QMessageBox QLabel {
    color: #e0e0e0;
}

QMessageBox QDialogButtonBox QPushButton {
    min-width: 60px;
}

QFileDialog {
    background-color: #1a1a1a;
    color: #e0e0e0;
}

QFileDialog QLabel {
    color: #e0e0e0;
}

QFileDialog QPushButton {
    min-width: 60px;
}
"""
