"""Reusable GUI widgets and factories."""

from typing import Optional, Tuple
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)


def create_stepper_input(
    label_text: str,
    default_value: str,
    target_layout: QVBoxLayout,
    on_change_callback=None,
    tooltip: Optional[str] = None,
) -> QLineEdit:
    """
    Create a stepper input with +/- buttons.
    
    Args:
        label_text: Label for the input
        default_value: Default numeric value
        target_layout: Parent layout to add to
        on_change_callback: Callback function on value change
        tooltip: Optional tooltip text
        
    Returns:
        QLineEdit widget
    """
    vbox = QVBoxLayout()
    vbox.setSpacing(3)
    
    lbl = QLabel(label_text)
    lbl.setStyleSheet("color: #aaa; font-size: 11px; font-weight: bold;")
    if tooltip:
        lbl.setToolTip(tooltip)
    vbox.addWidget(lbl)

    row = QHBoxLayout()
    row.setSpacing(3)

    btn_minus = QPushButton("−")
    btn_minus.setFixedSize(24, 24)
    btn_minus.setAutoRepeat(True)
    btn_minus.setAutoRepeatInterval(40)
    btn_minus.setAutoRepeatDelay(280)
    btn_minus.setStyleSheet(
        "QPushButton { background-color: #1e1e1e; color: #ccc; border: 1px solid #333; "
        "border-radius: 4px; font-weight: bold; font-size: 14px; padding: 0; }"
    )

    txt = QLineEdit(default_value)
    txt.setStyleSheet(
        "QLineEdit { background-color: #111; color: white; border: 1px solid #282828; "
        "border-radius: 4px; padding: 3px 2px; text-align: center; font-weight: bold; font-size: 11px; }"
    )
    if tooltip:
        txt.setToolTip(tooltip)

    btn_plus = QPushButton("+")
    btn_plus.setFixedSize(24, 24)
    btn_plus.setAutoRepeat(True)
    btn_plus.setAutoRepeatInterval(40)
    btn_plus.setAutoRepeatDelay(280)
    btn_plus.setStyleSheet(
        "QPushButton { background-color: #1e1e1e; color: #ccc; border: 1px solid #333; "
        "border-radius: 4px; font-weight: bold; font-size: 14px; padding: 0; }"
    )

    def step_val(delta: int):
        try:
            curr = int(txt.text())
        except ValueError:
            curr = 0
        txt.setText(str(max(0, curr + delta)))
        if on_change_callback:
            on_change_callback()

    btn_minus.clicked.connect(lambda: step_val(-1))
    btn_plus.clicked.connect(lambda: step_val(1))

    row.addWidget(btn_minus)
    row.addWidget(txt)
    row.addWidget(btn_plus)
    vbox.addLayout(row)
    target_layout.addLayout(vbox)
    return txt


def create_slider(
    label_text: str,
    min_v: int,
    max_v: int,
    default_v: int,
    target_layout: QVBoxLayout,
    on_change_callback=None,
    tooltip: Optional[str] = None,
) -> Tuple[QSlider, QLabel]:
    """
    Create a slider with label.
    
    Args:
        label_text: Label text
        min_v: Minimum value
        max_v: Maximum value
        default_v: Default value
        target_layout: Parent layout
        on_change_callback: Callback on slider release
        tooltip: Optional tooltip
        
    Returns:
        Tuple of (slider, value_label)
    """
    row = QHBoxLayout()
    lbl_name = QLabel(label_text)
    lbl_name.setStyleSheet("background: transparent; color: #b8b8b8; font-size: 11px;")
    if tooltip:
        lbl_name.setToolTip(tooltip)

    lbl_val = QLabel(str(default_v))
    lbl_val.setStyleSheet(
        "background: transparent; color: #e0e0e0; font-size: 11px; font-weight: bold; "
        "font-family: 'Consolas', monospace;"
    )
    if tooltip:
        lbl_val.setToolTip(tooltip)

    row.addWidget(lbl_name)
    row.addStretch()
    row.addWidget(lbl_val)

    slider = QSlider(Qt.Orientation.Horizontal)
    slider.setRange(min_v, max_v)
    slider.setValue(default_v)
    if tooltip:
        slider.setToolTip(tooltip)

    slider.valueChanged.connect(lambda val: lbl_val.setText(str(val)))
    if on_change_callback:
        slider.sliderReleased.connect(on_change_callback)

    target_layout.addLayout(row)
    target_layout.addWidget(slider)
    return slider, lbl_val


def create_slider_float(
    label_text: str,
    min_v: int,
    max_v: int,
    default_v: int,
    divisor: float,
    target_layout: QVBoxLayout,
    on_change_callback=None,
    tooltip: Optional[str] = None,
) -> Tuple[QSlider, QLabel]:
    """
    Create a slider with float display.
    
    Args:
        label_text: Label text
        min_v: Minimum value
        max_v: Maximum value
        default_v: Default value
        divisor: Divisor for float conversion
        target_layout: Parent layout
        on_change_callback: Callback on slider release
        tooltip: Optional tooltip
        
    Returns:
        Tuple of (slider, value_label)
    """
    row = QHBoxLayout()
    lbl_name = QLabel(label_text)
    lbl_name.setStyleSheet("background: transparent; color: #b8b8b8; font-size: 11px;")
    if tooltip:
        lbl_name.setToolTip(tooltip)

    init_float = default_v / divisor
    fmt = f"{init_float:.2f}" if divisor < 100 else f"{init_float:.3f}"
    lbl_val = QLabel(fmt)
    lbl_val.setStyleSheet(
        "background: transparent; color: #e0e0e0; font-size: 11px; font-weight: bold; "
        "font-family: 'Consolas', monospace;"
    )
    if tooltip:
        lbl_val.setToolTip(tooltip)

    row.addWidget(lbl_name)
    row.addStretch()
    row.addWidget(lbl_val)

    slider = QSlider(Qt.Orientation.Horizontal)
    slider.setRange(min_v, max_v)
    slider.setValue(default_v)
    if tooltip:
        slider.setToolTip(tooltip)

    def update_label(val):
        fmt = f"{val/divisor:.2f}" if divisor < 100 else f"{val/divisor:.3f}"
        lbl_val.setText(fmt)

    slider.valueChanged.connect(update_label)
    if on_change_callback:
        slider.sliderReleased.connect(on_change_callback)

    target_layout.addLayout(row)
    target_layout.addWidget(slider)
    return slider, lbl_val


def create_filter_group(group_title: str, target_layout: QVBoxLayout) -> QVBoxLayout:
    """
    Create a filter group header and return layout for adding controls.
    
    Args:
        group_title: Title of the group
        target_layout: Parent layout to add header to
        
    Returns:
        Inner layout for adding widgets
    """
    # Create header frame
    group_header = QFrame()
    group_header.setStyleSheet("""
        QFrame {
            background-color: #2b2b2b;
            border-top: 1px solid #3d3d3d;
            border-bottom: 1px solid #3d3d3d;
        }
    """)
    header_layout = QHBoxLayout(group_header)
    header_layout.setContentsMargins(8, 4, 8, 4)

    title_label = QLabel(group_title.upper())
    title_label.setStyleSheet("""
        QLabel {
            background: transparent;
            color: #e5a00d;
            font-weight: 700;
            font-size: 10px;
            letter-spacing: 0.8px;
        }
    """)
    header_layout.addWidget(title_label)
    header_layout.addStretch()
    
    # Add header to parent layout
    target_layout.addWidget(group_header)
    
    # Create and return inner layout for controls
    inner_layout = QVBoxLayout()
    inner_layout.setContentsMargins(0, 4, 0, 4)
    inner_layout.setSpacing(2)
    
    return inner_layout
