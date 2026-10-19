"""UI widget factories for creating sliders, inputs, and groups."""

from typing import Optional, Tuple

from gui.components import ScrollSafeSlider

from PySide6.QtCore import Qt
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)


def create_slider(
    label_text: str,
    min_v: int,
    max_v: int,
    default_v: int,
    target_layout: QVBoxLayout,
    connect_pipeline=True,
    tooltip: Optional[str] = None,
    on_release_callback=None,
    divisor=1,
    formatter=None,
) -> Tuple[QSlider, QLabel]:
    """Create a labeled horizontal slider with value display."""
    row = QHBoxLayout()
    lbl_name = QLabel(label_text)
    lbl_name.setStyleSheet("background: transparent; color: #b8b8b8; font-size: 11px;")
    if tooltip:
        lbl_name.setToolTip(tooltip)

    lbl_val = QLabel(str(default_v))
    lbl_val.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
    lbl_val.setStyleSheet("background: transparent; color: #e0e0e0; font-size: 11px; font-weight: bold;")
    if tooltip:
        lbl_val.setToolTip(tooltip)

    row.addWidget(lbl_name)
    row.addStretch()
    row.addWidget(lbl_val)

    slider = ScrollSafeSlider(Qt.Orientation.Horizontal)
    slider.setRange(min_v, max_v)
    slider.setValue(default_v)
    if tooltip:
        slider.setToolTip(tooltip)

    slider.value_label = lbl_val
    slider.title_label = lbl_name
    slider.display_divisor = divisor
    slider.display_formatter = formatter
    slider.valueChanged.connect(lambda _: update_slider_display(slider))
    update_slider_display(slider)
    if on_release_callback:
        slider.sliderReleased.connect(on_release_callback)

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
    tooltip: Optional[str] = None,
    on_release_callback=None,
) -> Tuple[QSlider, QLabel]:
    """Create a slider displaying its physical value instead of integer ticks."""
    return create_slider(
        label_text, min_v, max_v, default_v, target_layout,
        tooltip=tooltip, on_release_callback=on_release_callback, divisor=divisor,
    )


def update_slider_display(slider, *, divisor=None, formatter=None, title=None):
    """Refresh a physical value, including when a mode changes at the same tick."""
    if divisor is not None:
        slider.display_divisor = divisor
    if formatter is not None:
        slider.display_formatter = formatter
    if title is not None:
        slider.title_label.setText(title)
    value = slider.value()
    text = (slider.display_formatter(value) if slider.display_formatter else
            f"{value / slider.display_divisor:.10f}".rstrip('0').rstrip('.'))
    slider.value_label.setText(text)


def create_stepper_input(
    label_text: str,
    default_value: str,
    target_layout: QHBoxLayout,
    tooltip: Optional[str] = None,
    on_change_callback=None,
) -> QLineEdit:
    """Create a stepper input with +/- buttons."""
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
    btn_minus.setToolTip(f"Decrease {label_text.rstrip(':')} by 1. {tooltip or ''}".strip())
    btn_minus.setFixedSize(24, 24)
    btn_minus.setAutoRepeat(True)
    btn_minus.setAutoRepeatInterval(40)
    btn_minus.setAutoRepeatDelay(280)
    btn_minus.setStyleSheet("QPushButton { background-color: #1e1e1e; color: #ccc; border: 1px solid #333; border-radius: 4px; font-weight: bold; font-size: 14px; padding: 0; }")

    txt = QLineEdit(default_value)
    txt.setStyleSheet("QLineEdit { background-color: #111; color: white; border: 1px solid #282828; border-radius: 4px; padding: 3px 2px; text-align: center; font-weight: bold; font-size: 11px; }")
    if tooltip:
        txt.setToolTip(tooltip)

    btn_plus = QPushButton("+")
    btn_plus.setToolTip(f"Increase {label_text.rstrip(':')} by 1. {tooltip or ''}".strip())
    btn_plus.setFixedSize(24, 24)
    btn_plus.setAutoRepeat(True)
    btn_plus.setAutoRepeatInterval(40)
    btn_plus.setAutoRepeatDelay(280)
    btn_plus.setStyleSheet("QPushButton { background-color: #1e1e1e; color: #ccc; border: 1px solid #333; border-radius: 4px; font-weight: bold; font-size: 14px; padding: 0; }")

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


def create_filter_group(group_title: str, control_layout: QVBoxLayout) -> QVBoxLayout:
    """Create a labeled filter group with header."""
    group_frame = QFrame()
    group_layout = QVBoxLayout(group_frame)
    group_layout.setContentsMargins(0, 10, 0, 0)
    group_layout.setSpacing(0)

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
    group_layout.addWidget(group_header)

    inner_container = QWidget()
    inner_layout = QVBoxLayout(inner_container)
    inner_layout.setContentsMargins(0, 2, 0, 0)
    group_layout.addWidget(inner_container)
    control_layout.addWidget(group_frame)
    return inner_layout


def create_dyadic_slider(
    label_text: str,
    min_exp: int,
    max_exp: int,
    default_exp: int,
    target_layout: QVBoxLayout,
    tooltip: Optional[str] = None,
    on_release_callback=None,
) -> Tuple[QSlider, QLabel]:
    """Display the actual segment count while retaining power-of-two steps."""
    return create_slider(
        label_text, min_exp, max_exp, default_exp, target_layout,
        tooltip=tooltip, on_release_callback=on_release_callback,
        formatter=lambda exponent: str(2 ** exponent),
    )
