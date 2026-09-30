"""Main application window: EclipseProcessorApp."""

import os
import time
from typing import Optional, Tuple

import cv2
import numpy as np
from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtGui import QCloseEvent, QIcon, QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
)
import tifffile

from config import LIGHTROOM_QSS, CPU_CORES
from core.filters import FilterWorker
from gui.components import ClickableLabel, CollapsibleSection
from gui.factories import create_filter_group, create_slider, create_slider_float, create_stepper_input
from utils.helpers import resource_path


class EclipseProcessorApp(QMainWindow):
    """Main application window for solar eclipse processing."""

    request_processing_signal = Signal(np.ndarray, dict)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Solar Corona Enhancement Filters v1.3.1")
        self.resize(1180, 780)
        self.setMinimumSize(960, 600)

        icon_file = resource_path("icono.ico") if os.path.exists(resource_path("icono.ico")) else resource_path("icono.png")
        if os.path.exists(icon_file):
            self.setWindowIcon(QIcon(icon_file))

        self.raw_image: Optional[np.ndarray] = None
        self.processed_image: Optional[np.ndarray] = None
        self.full_raw_image: Optional[np.ndarray] = None
        self.preview_image: Optional[np.ndarray] = None
        self.preview_scale: float = 1.0
        self.show_original_mode: bool = False
        self.auto_calculate: bool = True
        self.is_processing: bool = False
        self.has_pending_request: bool = False
        self.sp_picker_active: bool = False

        self.persistent_thread = QThread()
        self.filter_worker = FilterWorker()
        self.filter_worker.moveToThread(self.persistent_thread)
        self.request_processing_signal.connect(self.filter_worker.process_pipeline)
        self.filter_worker.finished.connect(self.on_processing_finished)
        self.persistent_thread.start()

        self._build_ui()

    def _build_ui(self):
        """Build the main user interface."""
        main_widget = QWidget()
        main_widget.setObjectName("centralWidget")
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        self.image_label = ClickableLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("QLabel { background-color: #1c1c1c; border: 1px solid #333333; border-radius: 4px; }")
        self.image_label.image_clicked.connect(self.on_image_canvas_clicked)
        main_layout.addWidget(self.image_label, stretch=3)

        right_container = QWidget()
        right_container.setFixedWidth(380)
        right_container.setStyleSheet("background-color: #2b2b2b; border-radius: 6px;")
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(6, 6, 6, 6)
        right_layout.setSpacing(6)

        top_header_panel = QFrame()
        top_header_panel.setStyleSheet("QFrame { background-color: #303030; border: 1px solid #3c3c3c; border-radius: 4px; }")
        top_header_layout = QVBoxLayout(top_header_panel)
        top_header_layout.setContentsMargins(10, 8, 10, 8)
        top_header_layout.setSpacing(6)

        self.status_label = QLabel(f"Status: Ready ({CPU_CORES} CPU cores available)")
        self.status_label.setStyleSheet("color: #9cdcfe; font-weight: bold; font-size: 11px;")
        top_header_layout.addWidget(self.status_label)

        btn_row = QHBoxLayout()
        self.btn_load = QPushButton("📁 Open Image")
        self.btn_load.setToolTip("Load a 16-bit or 32-bit TIFF, FITS, or XISF solar master frame")
        self.btn_load.clicked.connect(self.load_image_action)
        btn_row.addWidget(self.btn_load)

        self.btn_compare = QPushButton("👁️ View Original")
        self.btn_compare.setCheckable(True)
        self.btn_compare.setToolTip("Toggle between filtered and original image for quick comparison")
        self.btn_compare.clicked.connect(self.toggle_compare_mode)
        btn_row.addWidget(self.btn_compare)

        self.btn_auto_calc = QPushButton("Auto Calculate")
        self.btn_auto_calc.setCheckable(True)
        self.btn_auto_calc.setChecked(True)
        self.btn_auto_calc.setToolTip("Toggle automatic pipeline recomputation on slider release")
        self.btn_auto_calc.clicked.connect(self.toggle_auto_calc_mode)
        btn_row.addWidget(self.btn_auto_calc)

        self.btn_recalc = QPushButton("🔄")
        self.btn_recalc.setFixedSize(32, 26)
        self.btn_recalc.setToolTip("Manually trigger full filter pipeline recalculation")
        self.btn_recalc.clicked.connect(self.dispatch_pipeline_request)
        self.btn_recalc.setVisible(False)
        btn_row.addWidget(self.btn_recalc)

        top_header_layout.addLayout(btn_row)
        right_layout.addWidget(top_header_panel)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        control_panel = QWidget()
        control_panel.setStyleSheet("background-color: transparent;")
        control_layout = QVBoxLayout(control_panel)
        control_layout.setContentsMargins(2, 2, 6, 2)
        control_layout.setSpacing(6)

        scroll_area.setWidget(control_panel)
        right_layout.addWidget(scroll_area, stretch=1)
        main_layout.addWidget(right_container)

        self._build_geometry_section(control_layout)
        self._build_filters_section(control_layout)
        self._build_stretch_section(control_layout)

    def _build_geometry_section(self, layout: QVBoxLayout):
        """Build the solar disk geometry section."""
        self.sec_geo = CollapsibleSection("SOLAR DISK GEOMETRY", has_checkbox=False, is_expanded=True)
        coord_layout = QHBoxLayout()
        self.txt_x = create_stepper_input(
            "Center X:", "0", coord_layout, "Horizontal (X) position of the lunar disk center in FULL-RESOLUTION pixels",
            on_change_callback=self.dispatch_pipeline_request_if_auto
        )
        self.txt_y = create_stepper_input(
            "Center Y:", "0", coord_layout, "Vertical (Y) position of the lunar disk center in FULL-RESOLUTION pixels",
            on_change_callback=self.dispatch_pipeline_request_if_auto
        )
        self.txt_r = create_stepper_input(
            "Radius R:", "300", coord_layout, "Radius of the lunar/solar disk in FULL-RESOLUTION pixels",
            on_change_callback=self.dispatch_pipeline_request_if_auto
        )
        self.sec_geo.content_layout.addLayout(coord_layout)

        self.lbl_scale_info = QLabel("Scale: 1.0x (100% resolution)")
        self.lbl_scale_info.setStyleSheet("color: #e5a00d; font-size: 10px; font-weight: bold;")
        self.sec_geo.content_layout.addWidget(self.lbl_scale_info)

        self.txt_x.textChanged.connect(self.trigger_circle_redraw)
        self.txt_y.textChanged.connect(self.trigger_circle_redraw)
        self.txt_r.textChanged.connect(self.trigger_circle_redraw)

        self.btn_auto_moon = QPushButton("🎯 Auto-detect Lunar Disk")
        self.btn_auto_moon.setToolTip("Automatically detect the lunar disk center and radius using Hough Circle Transform")
        self.btn_auto_moon.clicked.connect(self.auto_detect_moon_action)
        self.sec_geo.content_layout.addWidget(self.btn_auto_moon)
        layout.addWidget(self.sec_geo)

    def _build_filters_section(self, layout: QVBoxLayout):
        """Build all filter sections (PRE-STRETCH, DENOISING, RADIAL, MULTI-SCALE, SHARPENING)."""
        self.sec_pre_stretch = CollapsibleSection("PRE-STRETCH (ENTRY)", has_checkbox=True, is_expanded=False, is_active=False)
        
        mode_row = QHBoxLayout()
        mode_lbl = QLabel("Pre-stretch Type:")
        mode_lbl.setStyleSheet("color: #aaa; font-size: 11px;")
        self.combo_pre_mode = QComboBox()
        self.combo_pre_mode.addItems(["Asinh (Smooth Shadows)", "Logarithmic: ln(1 + Kx)"])
        self.combo_pre_mode.setToolTip("Asinh preserves darker background; Logarithmic aggressively compresses dynamic range up to 10^6")
        self.combo_pre_mode.currentIndexChanged.connect(self._on_pre_stretch_mode_changed)
        mode_row.addWidget(mode_lbl)
        mode_row.addWidget(self.combo_pre_mode)
        self.sec_pre_stretch.content_layout.addLayout(mode_row)

        self.sl_pre_stretch, self.lbl_pre_stretch = create_slider(
            "Factor (Asinh / Log Exp)", 1, 100, 10, self.sec_pre_stretch.content_layout,
            on_release_callback=self.dispatch_pipeline_request_if_auto,
            tooltip="Compression intensity factor (Asinh: 1–100 | Log: 10^0.0 to 10^6.0 exponent)"
        )
        self.sec_pre_stretch.toggled_active.connect(self.on_filter_toggled)
        layout.addWidget(self.sec_pre_stretch)

        denoising_group = create_filter_group("🔇 DENOISING & NOISE SUPPRESSION", layout)
        self.sec_noise_gate = CollapsibleSection("RADIAL NOISE GATE", has_checkbox=True, is_expanded=False, is_active=False)
        self.sl_noise_gate_str, _ = create_slider(
            "Gate Strength (%)", 0, 100, 0, self.sec_noise_gate.content_layout,
            on_release_callback=lambda: self.on_filter_slider_released(self.sec_noise_gate, self.sl_noise_gate_str),
            tooltip="Noise suppression strength in outer corona (Recommended: 50–70% for noisy images)"
        )
        self.sl_noise_gate_thr, _ = create_slider(
            "SNR Threshold (×100)", 1, 50, 10, self.sec_noise_gate.content_layout,
            on_release_callback=lambda: self.on_filter_slider_released(self.sec_noise_gate, self.sl_noise_gate_str),
            tooltip="Signal-to-noise ratio threshold (Recommended: 15–25 for outer corona, higher = more aggressive)"
        )
        self.sec_noise_gate.toggled_active.connect(self.on_filter_toggled)
        denoising_group.addWidget(self.sec_noise_gate)

        self.sec_bilateral = CollapsibleSection("EDGE-PRESERVING DENOISE", has_checkbox=True, is_expanded=False, is_active=False)
        self.sl_bilateral_str, _ = create_slider(
            "Strength (%)", 0, 100, 0, self.sec_bilateral.content_layout,
            on_release_callback=lambda: self.on_filter_slider_released(self.sec_bilateral, self.sl_bilateral_str),
            tooltip="Denoising strength (Recommended: 40–60% for smooth noise reduction without posterization)"
        )
        self.sl_bilateral_d, _ = create_slider(
            "Blur Radius (×10)", 3, 50, 5, self.sec_bilateral.content_layout,
            on_release_callback=lambda: self.on_filter_slider_released(self.sec_bilateral, self.sl_bilateral_str),
            tooltip="Gaussian blur radius in pixels (Recommended: 5–8 for 0.5–0.8 px, higher = more smoothing)"
        )
        self.sl_bilateral_ss, _ = create_slider(
            "Edge Sensitivity (×100)", 5, 100, 50, self.sec_bilateral.content_layout,
            on_release_callback=lambda: self.on_filter_slider_released(self.sec_bilateral, self.sl_bilateral_str),
            tooltip="Edge preservation strength (Recommended: 40–60, higher = preserve more filament edges, lower = more aggressive smoothing)"
        )
        self.sec_bilateral.toggled_active.connect(lambda active: self.on_filter_toggled(active, self.sl_bilateral_str))
        denoising_group.addWidget(self.sec_bilateral)

        radial_group = create_filter_group("🔄 RADIAL ENHANCEMENT", layout)
        self.sec_fnrgf = CollapsibleSection("FNRGF", has_checkbox=True, is_expanded=False, is_active=False)
        self.sl_fnrgf_str, _ = create_slider(
            "Strength (%)", 0, 100, 0, self.sec_fnrgf.content_layout,
            on_release_callback=lambda: self.on_filter_slider_released(self.sec_fnrgf, self.sl_fnrgf_str),
            tooltip="Blend percentage of the radial gradient filter (0=off, 100=full effect)"
        )
        self.sl_fnrgf_ord, _ = create_slider(
            "Fourier Order", 1, 50, 6, self.sec_fnrgf.content_layout,
            on_release_callback=lambda: self.on_filter_slider_released(self.sec_fnrgf, self.sl_fnrgf_str),
            tooltip="Maximum azimuthal Fourier harmonics to retain for fine filament detail"
        )
        self.sl_fnrgf_seg, _ = create_slider(
            "Angular Segments", 10, 360, 50, self.sec_fnrgf.content_layout,
            on_release_callback=lambda: self.on_filter_slider_released(self.sec_fnrgf, self.sl_fnrgf_str),
            tooltip="Number of angular subdivisions for radial analysis"
        )
        self.sl_fnrgf_cut, _ = create_slider(
            "Harmonic Cutoff", 0, 20, 0, self.sec_fnrgf.content_layout,
            on_release_callback=lambda: self.on_filter_slider_released(self.sec_fnrgf, self.sl_fnrgf_str),
            tooltip="Harmonic frequency cutoff to attenuate unwanted spatial oscillations"
        )
        self.sl_fnrgf_rad, _ = create_slider(
            "App Radius (×10)", 5, 25, 10, self.sec_fnrgf.content_layout,
            on_release_callback=lambda: self.on_filter_slider_released(self.sec_fnrgf, self.sl_fnrgf_str),
            tooltip="Application radius in tenths of solar radius for the filter envelope"
        )
        self.sl_fnrgf_rmax, _ = create_slider(
            "Outer Radius R_max (×10)", 15, 60, 30, self.sec_fnrgf.content_layout,
            on_release_callback=lambda: self.on_filter_slider_released(self.sec_fnrgf, self.sl_fnrgf_str),
            tooltip="Outer boundary radius in tenths of solar radius (1.5–6.0 R_sun)"
        )
        self.sl_fnrgf_nbins, _ = create_slider(
            "Radial Bin Count", 20, 300, 80, self.sec_fnrgf.content_layout,
            on_release_callback=lambda: self.on_filter_slider_released(self.sec_fnrgf, self.sl_fnrgf_str),
            tooltip="Number of concentric radial bins for harmonic decomposition"
        )

        w_row = QHBoxLayout()
        w_lbl = QLabel("Width Function:")
        w_lbl.setStyleSheet("color: #aaa; font-size: 11px;")
        self.combo_fnrgf_width = QComboBox()
        self.combo_fnrgf_width.addItems(["Standard Deviation (STD)", "Median Absolute Deviation (MAD)"])
        self.combo_fnrgf_width.setToolTip("STD = original, MAD = robust to cosmic rays and sharp artifacts (Recommended: MAD)")
        self.combo_fnrgf_width.currentIndexChanged.connect(lambda _: self.dispatch_pipeline_request_if_auto())
        w_row.addWidget(w_lbl)
        w_row.addWidget(self.combo_fnrgf_width)
        self.sec_fnrgf.content_layout.addLayout(w_row)

        b_row = QHBoxLayout()
        b_lbl = QLabel("Radial Binning:")
        b_lbl.setStyleSheet("color: #aaa; font-size: 11px;")
        self.combo_fnrgf_binning = QComboBox()
        self.combo_fnrgf_binning.addItems(["Linear", "Log-spaced (Corona Optimized)"])
        self.combo_fnrgf_binning.setToolTip("Log-spaced = optimal for solar corona inverse-square intensity falloff (Recommended: Log-spaced)")
        self.combo_fnrgf_binning.currentIndexChanged.connect(lambda _: self.dispatch_pipeline_request_if_auto())
        b_row.addWidget(b_lbl)
        b_row.addWidget(self.combo_fnrgf_binning)
        self.sec_fnrgf.content_layout.addLayout(b_row)

        self.sl_fnrgf_mask, _ = create_slider(
            "Apply Mask (%)", 0, 100, 0, self.sec_fnrgf.content_layout,
            on_release_callback=self.dispatch_pipeline_request_if_auto,
            tooltip="Lunar limb protection (0=off, 60% recommended to preserve limb transition)"
        )
        self.sec_fnrgf.toggled_active.connect(lambda active: self.on_filter_toggled(active, self.sl_fnrgf_str))
        radial_group.addWidget(self.sec_fnrgf)

        self.sec_rhef = CollapsibleSection("RHEF", has_checkbox=True, is_expanded=False, is_active=False)
        self.sl_rhef_str, _ = create_slider(
            "Strength (%)", 0, 100, 0, self.sec_rhef.content_layout,
            on_release_callback=lambda: self.on_filter_slider_released(self.sec_rhef, self.sl_rhef_str),
            tooltip="Radial Histogram Equalization blend strength (0=off, 100=full effect)"
        )
        self.sl_rhef_rad, _ = create_slider(
            "App Radius (×10)", 0, 40, 10, self.sec_rhef.content_layout,
            on_release_callback=lambda: self.on_filter_slider_released(self.sec_rhef, self.sl_rhef_str),
            tooltip="Application radius in tenths of solar radius"
        )
        self.sl_rhef_upsilon, _ = create_slider(
            "Upsilon Parameter (×100)", 1, 100, 35, self.sec_rhef.content_layout,
            on_release_callback=lambda: self.on_filter_slider_released(self.sec_rhef, self.sl_rhef_str),
            tooltip="Non-linear normalization exponent (higher = stronger contrast enhancement)"
        )
        self.sec_rhef.toggled_active.connect(lambda active: self.on_filter_toggled(active, self.sl_rhef_str))
        radial_group.addWidget(self.sec_rhef)

        multiscale_group = create_filter_group("📊 MULTI-SCALE / WAVELETS", layout)
        self.sec_mgn = CollapsibleSection("MGN", has_checkbox=True, is_expanded=False, is_active=False)
        self.sl_mgn_str, _ = create_slider(
            "Strength (%)", 0, 100, 0, self.sec_mgn.content_layout,
            on_release_callback=lambda: self.on_filter_slider_released(self.sec_mgn, self.sl_mgn_str),
            tooltip="Multi-Scale Gaussian Normalization blend strength"
        )
        self.sl_mgn_gam, _ = create_slider(
            "Gamma (×10)", 1, 100, 32, self.sec_mgn.content_layout,
            on_release_callback=lambda: self.on_filter_slider_released(self.sec_mgn, self.sl_mgn_str),
            tooltip="Gamma exponent for local contrast compression (higher = stronger)"
        )
        self.sl_mgn_k, _ = create_slider(
            "Factor k (×100)", 1, 200, 70, self.sec_mgn.content_layout,
            on_release_callback=lambda: self.on_filter_slider_released(self.sec_mgn, self.sl_mgn_str),
            tooltip="Arctangent steepness factor for normalized gradient mapping"
        )
        self.sl_mgn_h, _ = create_slider(
            "Global Weight h (×100)", 0, 100, 70, self.sec_mgn.content_layout,
            on_release_callback=lambda: self.on_filter_slider_released(self.sec_mgn, self.sl_mgn_str),
            tooltip="Global blending weight for multi-scale combination"
        )
        self.sl_mgn_trunc, _ = create_slider(
            "Kernel Truncation (Sigmas)", 1, 6, 3, self.sec_mgn.content_layout,
            on_release_callback=lambda: self.on_filter_slider_released(self.sec_mgn, self.sl_mgn_str),
            tooltip="Gaussian kernel truncation in standard deviations"
        )
        self.sec_mgn.toggled_active.connect(lambda active: self.on_filter_toggled(active, self.sl_mgn_str))
        multiscale_group.addWidget(self.sec_mgn)

        self.sec_wow = CollapsibleSection("WOW", has_checkbox=True, is_expanded=False, is_active=False)
        self.sl_wow_str, _ = create_slider(
            "Strength (%)", 0, 100, 0, self.sec_wow.content_layout,
            on_release_callback=lambda: self.on_filter_slider_released(self.sec_wow, self.sl_wow_str),
            tooltip="Wavelets Optimized Whitening blend strength"
        )
        self.sl_wow_scales, _ = create_slider(
            "Wavelet Scales", 3, 10, 6, self.sec_wow.content_layout,
            on_release_callback=lambda: self.on_filter_slider_released(self.sec_wow, self.sl_wow_str),
            tooltip="Number of wavelet decomposition scales for multi-frequency analysis"
        )
        self.sl_wow_gam, _ = create_slider(
            "Gamma (×10)", 1, 100, 32, self.sec_wow.content_layout,
            on_release_callback=lambda: self.on_filter_slider_released(self.sec_wow, self.sl_wow_str),
            tooltip="Gamma exponent for wavelet coefficient compression"
        )
        self.sl_wow_h, _ = create_slider(
            "Background Weight h (×100)", 0, 100, 20, self.sec_wow.content_layout,
            on_release_callback=lambda: self.on_filter_slider_released(self.sec_wow, self.sl_wow_str),
            tooltip="Global weighting for background suppression"
        )
        self.sec_wow.toggled_active.connect(lambda active: self.on_filter_toggled(active, self.sl_wow_str))
        multiscale_group.addWidget(self.sec_wow)

        sharpening_group = create_filter_group("✨ SHARPENING", layout)
        self.sec_usm = CollapsibleSection("USM", has_checkbox=True, is_expanded=False, is_active=False)
        self.sl_usm_str, _ = create_slider(
            "Strength (%)", 0, 100, 0, self.sec_usm.content_layout,
            on_release_callback=lambda: self.on_filter_slider_released(self.sec_usm, self.sl_usm_str),
            tooltip="Unsharp Mask blend strength (0=off, 100=full sharpening)"
        )
        self.sl_usm_radius, _ = create_slider(
            "Blur Radius (×10)", 5, 200, 10, self.sec_usm.content_layout,
            on_release_callback=lambda: self.on_filter_slider_released(self.sec_usm, self.sl_usm_str),
            tooltip="Radius of blur for high-pass extraction (0.5–20 px)"
        )
        self.sl_usm_amount, _ = create_slider(
            "Sharpening Amount (×10)", 5, 50, 20, self.sec_usm.content_layout,
            on_release_callback=lambda: self.on_filter_slider_released(self.sec_usm, self.sl_usm_str),
            tooltip="Amplification factor for high-pass component (0.5–5.0×)"
        )
        self.sec_usm.toggled_active.connect(lambda active: self.on_filter_toggled(active, self.sl_usm_str))
        sharpening_group.addWidget(self.sec_usm)

        self.sec_achf = CollapsibleSection("ACHF", has_checkbox=True, is_expanded=False, is_active=False)
        self.sl_achf_str, _ = create_slider(
            "Strength (%)", 0, 100, 0, self.sec_achf.content_layout,
            on_release_callback=lambda: self.on_filter_slider_released(self.sec_achf, self.sl_achf_str),
            tooltip="Adaptive Circular High-Pass Filter blend strength"
        )
        self.sl_achf_kernel, _ = create_slider(
            "Base Kernel Radius (×10)", 5, 200, 20, self.sec_achf.content_layout,
            on_release_callback=lambda: self.on_filter_slider_released(self.sec_achf, self.sl_achf_str),
            tooltip="Base Gaussian kernel radius in tenths of pixels (0.5–20.0 px)"
        )
        self.sl_achf_boost, _ = create_slider(
            "Contrast Gain (×10)", 10, 50, 20, self.sec_achf.content_layout,
            on_release_callback=lambda: self.on_filter_slider_released(self.sec_achf, self.sl_achf_str),
            tooltip="High-pass amplification factor for filament microcontrast (1.0–5.0×)"
        )
        self.sec_achf.toggled_active.connect(lambda active: self.on_filter_toggled(active, self.sl_achf_str))
        sharpening_group.addWidget(self.sec_achf)

    def _on_pre_stretch_mode_changed(self, index: int):
        """Handle pre-stretch mode change."""
        if index == 1:
            self.sl_pre_stretch.setRange(0, 60)
            self.sl_pre_stretch.setValue(10)
            self.lbl_pre_stretch.setText("1.0 (K=10^1.0)")
        else:
            self.sl_pre_stretch.setRange(1, 100)
            self.sl_pre_stretch.setValue(10)
            self.lbl_pre_stretch.setText("10")
        self.dispatch_pipeline_request_if_auto()

    def _build_stretch_section(self, layout: QVBoxLayout):
        """Build the tonal stretch & display section (screen-only)."""
        stretch_group = create_filter_group("🌟 TONAL STRETCH & DISPLAY (SCREEN ONLY)", layout)

        self.sec_stretch = CollapsibleSection("FINAL STRETCH MODE", has_checkbox=False, is_expanded=True)
        
        mode_row = QHBoxLayout()
        mode_lbl = QLabel("Stretch Algorithm:")
        mode_lbl.setStyleSheet("color: #aaa; font-size: 11px;")
        self.combo_stretch_mode = QComboBox()
        self.combo_stretch_mode.addItems(["Asinh (Smooth)", "Logarithmic: ln(1 + Kx)", "GHS (Hyperbolic Precision)"])
        self.combo_stretch_mode.setToolTip("Select final display curve: Smooth Asinh, fast outer corona Logarithmic, or professional GHS")
        self.combo_stretch_mode.currentIndexChanged.connect(self._on_stretch_mode_changed)
        mode_row.addWidget(mode_lbl)
        mode_row.addWidget(self.combo_stretch_mode)
        self.sec_stretch.content_layout.addLayout(mode_row)

        self.sl_stretch, self.lbl_stretch = create_slider(
            "Stretch Intensity", 1, 100, 10, self.sec_stretch.content_layout, connect_pipeline=False,
            on_release_callback=self.render_matrix_to_screen,
            tooltip="Stretch compression intensity factor"
        )

        self.ghs_container = QWidget()
        ghs_layout = QVBoxLayout(self.ghs_container)
        ghs_layout.setContentsMargins(0, 4, 0, 4)
        ghs_layout.setSpacing(6)

        sp_header = QHBoxLayout()
        sp_title = QLabel("Symmetry Point (SP Shadows)")
        sp_title.setToolTip("Brightness level where maximum contrast enhancement occurs (typically shadow region)")
        sp_header.addWidget(sp_title)
        self.lbl_ghs_sp = QLabel("0.050")
        self.lbl_ghs_sp.setStyleSheet("color: #e5a00d; font-size: 11px; font-weight: bold; font-family: 'Consolas', monospace;")
        sp_header.addStretch()
        sp_header.addWidget(self.lbl_ghs_sp)
        ghs_layout.addLayout(sp_header)

        self.sl_ghs_sp = QSlider(Qt.Orientation.Horizontal)
        self.sl_ghs_sp.setRange(0, 1000)
        self.sl_ghs_sp.setValue(100)
        self.sl_ghs_sp.setToolTip("Adjust the shadow brightness point for maximum contrast (0.000–0.500)")
        self.sl_ghs_sp.valueChanged.connect(self.on_sp_slider_changed)
        self.sl_ghs_sp.sliderReleased.connect(self.render_matrix_to_screen)
        ghs_layout.addWidget(self.sl_ghs_sp)

        self.btn_pick_sp = QPushButton("🎯 Set SP by Shadow Click")
        self.btn_pick_sp.setCheckable(True)
        self.btn_pick_sp.setToolTip("Click on shadow areas of the corona to automatically set the symmetry point")
        self.btn_pick_sp.setStyleSheet("""
            QPushButton {
                background-color: #3c3c3c;
                color: #e5a00d;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 6px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
                border: 1px solid #e5a00d;
            }
            QPushButton:pressed {
                background-color: #2a2a2a;
            }
            QPushButton:checked {
                background-color: #4CAF50;
                color: #ffffff;
                border: 1px solid #45a049;
            }
        """)
        self.btn_pick_sp.clicked.connect(self.toggle_sp_picker_mode)
        ghs_layout.addWidget(self.btn_pick_sp)

        self.sl_ghs_b, _ = create_slider_float(
            "Highlight Protection (b)", 0, 100, 20, 10.0, ghs_layout,
            on_release_callback=self.render_matrix_to_screen,
            tooltip="Slope reduction for bright areas to prevent blown-out highlights"
        )

        self.sl_ghs_bp, _ = create_slider_float(
            "Black Point (BP Shadows)", 0, 100, 0, 1000.0, ghs_layout,
            on_release_callback=self.render_matrix_to_screen,
            tooltip="Darkest level to preserve (clips darker values to black)"
        )

        self.sec_stretch.content_layout.addWidget(self.ghs_container)
        self.ghs_container.setVisible(False)
        stretch_group.addWidget(self.sec_stretch)

        self.sl_blend, _ = create_slider(
            "Reveal Opacity (%)", 0, 100, 100, stretch_group, connect_pipeline=False,
            on_release_callback=self.render_matrix_to_screen,
            tooltip="Opacity of processed result over original image (0=full original, 100=full processed)"
        )

        layout.addSpacing(8)

        self.btn_export = QPushButton("💾 Export Final Image")
        self.btn_export.setStyleSheet("""
            QPushButton {
                background-color: #0d6efd;
                color: #ffffff;
                font-weight: 700;
                font-size: 12px;
                padding: 8px;
                border: 1px solid #0b5ed7;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #0b5ed7;
                border-color: #0a58ca;
            }
            QPushButton:pressed {
                background-color: #0a58ca;
            }
        """)
        self.btn_export.setToolTip("Save the full-resolution processed image to 16-bit TIFF with exact scale compensation")
        self.btn_export.clicked.connect(self.export_image_action)
        layout.addWidget(self.btn_export)

    def _on_stretch_mode_changed(self, index: int):
        """Handle stretch mode change."""
        is_ghs = (index == 2)
        is_log = (index == 1)

        self.ghs_container.setVisible(is_ghs)
        if not is_ghs and hasattr(self, "btn_pick_sp") and self.btn_pick_sp.isChecked():
            self.btn_pick_sp.setChecked(False)
            self.image_label.setCursor(Qt.CursorShape.ArrowCursor)

        if is_log:
            self.sl_stretch.setRange(0, 60)
            self.sl_stretch.setValue(10)
            self.lbl_stretch.setText("1.0 (K=10^1.0)")
            self.status_label.setText("Status: Logarithmic Stretch Active")
            self.status_label.setStyleSheet("color: #e5a00d; font-weight: bold;")
        elif is_ghs:
            self.sl_stretch.setRange(1, 100)
            self.sl_stretch.setValue(10)
            self.lbl_stretch.setText("10")
            self.status_label.setText("Status: GHS Mode Active")
            self.status_label.setStyleSheet("color: #e5a00d; font-weight: bold;")
        else:
            self.sl_stretch.setRange(1, 100)
            self.sl_stretch.setValue(10)
            self.lbl_stretch.setText("10")
            self.status_label.setText("Status: Asinh Mode Active")
            self.status_label.setStyleSheet("color: #9cdcfe; font-weight: bold;")

        self.render_matrix_to_screen()

    # ===== EVENT HANDLERS & PIPELINE METHODS =====

    def on_sp_slider_changed(self, val: int):
        """Update GHS symmetry point label."""
        self.lbl_ghs_sp.setText(f"{(val / 1000.0) * 0.5:.3f}")

    def toggle_sp_picker_mode(self, checked: bool):
        """Toggle symmetry point picker mode."""
        if self.raw_image is None:
            self.btn_pick_sp.setChecked(False)
            return
        if checked:
            self.sp_picker_active = True
            self.image_label.setCursor(Qt.CursorShape.CrossCursor)
            self.status_label.setText("🎯 Click on corona shadows to set SP...")
            self.status_label.setStyleSheet("color: #e5a00d; font-weight: bold;")
        else:
            self.sp_picker_active = False
            self.image_label.setCursor(Qt.CursorShape.ArrowCursor)
            self.status_label.setText("Status: GHS Mode Active")
            self.status_label.setStyleSheet("color: #e5a00d; font-weight: bold;")

    def apply_ghs(self, mat: np.ndarray, D: float, SP: float, b: float, BP: float) -> np.ndarray:
        """Apply Generalized Hyperbolic Stretch."""
        D = max(0.01, float(D))
        SP = float(np.clip(SP, 0.0, 0.999))
        BP = float(np.clip(BP, 0.0, max(0.0, SP - 1e-4)))
        b = max(0.0, float(b))

        def evaluate_ghs(v):
            delta = v - SP
            scale = 1.0 + b * np.maximum(0.0, delta) if b > 0 else 1.0
            return np.arcsinh((D * delta) / scale)

        f_v = evaluate_ghs(mat)
        f_bp = evaluate_ghs(BP)
        f_1 = evaluate_ghs(1.0)
        denom = f_1 - f_bp
        if abs(denom) < 1e-7:
            return np.clip(mat, 0.0, 1.0)
        return np.clip((f_v - f_bp) / denom, 0.0, 1.0)

    def on_image_canvas_clicked(self, x: int, y: int):
        """Handle canvas click (SP picker or coordinate setting)."""
        if self.sp_picker_active and hasattr(self, "btn_pick_sp") and self.btn_pick_sp.isChecked():
            proc_mat = self.processed_image if self.processed_image is not None else self.raw_image
            if proc_mat is not None:
                h, w = proc_mat.shape[:2]
                clamped_x = int(np.clip(x, 0, w - 1))
                clamped_y = int(np.clip(y, 0, h - 1))
                proc_cleaned = np.nan_to_num(proc_mat, nan=0.0)
                p_min, p_max = float(np.min(proc_cleaned)), float(np.max(proc_cleaned))

                sample_norm = float(np.clip((proc_cleaned[clamped_y, clamped_x] - p_min) / (p_max - p_min + 1e-5), 0.0, 0.5))
                self.sl_ghs_sp.setValue(int(round((sample_norm / 0.5) * 1000)))
                self.lbl_ghs_sp.setText(f"{sample_norm:.3f}")
                self.btn_pick_sp.setChecked(False)
                self.sp_picker_active = False
                self.image_label.setCursor(Qt.CursorShape.ArrowCursor)
                self.status_label.setText(f"🎯 SP set to {sample_norm:.3f} (Sample: X:{clamped_x}, Y:{clamped_y})")
                self.status_label.setStyleSheet("color: #00ff00; font-weight: bold;")
                self.render_matrix_to_screen()
                return

        self.txt_x.setText(str(x))
        self.txt_y.setText(str(y))
        self.dispatch_pipeline_request_if_auto()

    def trigger_circle_redraw(self):
        """Redraw the solar disk circle on the canvas."""
        if self.raw_image is None or self.full_raw_image is None:
            return
        try:
            cx_full = int(self.txt_x.text())
            cy_full = int(self.txt_y.text())
            r_full = int(self.txt_r.text())
            h_full, w_full = self.full_raw_image.shape[:2]
            self.image_label.set_circle_parameters(cx_full, cy_full, r_full, native_w=w_full, native_h=h_full)
        except ValueError:
            pass

    def toggle_compare_mode(self, checked: bool):
        """Toggle between original and processed image display."""
        if self.raw_image is None:
            self.btn_compare.setChecked(False)
            return
        self.show_original_mode = checked
        if checked:
            self.btn_compare.setText("👁️ View Processed")
            self.status_label.setText("Status: Showing Original")
            self.status_label.setStyleSheet("color: #cc3335; font-weight: bold;")
        else:
            self.btn_compare.setText("👁️ View Original")
            self.status_label.setText("Status: Showing Processed")
            self.status_label.setStyleSheet("color: #00ff00; font-weight: bold;")
        self.render_matrix_to_screen()

    def toggle_auto_calc_mode(self, checked: bool):
        """Toggle automatic calculation mode."""
        self.auto_calculate = checked
        self.btn_auto_calc.setText("Auto Calculate" if checked else "Man Calc")
        self.btn_recalc.setVisible(not checked)
        self.status_label.setText("Status: Auto Calculate" if checked else "Status: Manual Calculate")
        if checked:
            self.dispatch_pipeline_request()

    def on_filter_toggled(self, is_active: bool, strength_slider=None):
        """Handle filter checkbox toggle.
        
        - If DISABLING: Always recalculate (to remove filter effect)
        - If ENABLING: Only recalculate if strength > 0 (filter will have visible effect)
        """
        if not is_active:
            # Disabling: always recalculate to remove filter effect
            self.dispatch_pipeline_request_if_auto()
        elif is_active and strength_slider is not None:
            # Enabling: only recalculate if strength > 0
            if strength_slider.value() > 0:
                self.dispatch_pipeline_request_if_auto()

    def on_filter_slider_released(self, section, strength_slider):
        """Handle filter slider release - only dispatch if filter is active."""
        if section.is_filter_active() and strength_slider.value() > 0:
            self.dispatch_pipeline_request_if_auto()

    def dispatch_pipeline_request_if_auto(self):
        """Dispatch pipeline request if auto-calculate is enabled."""
        if self.auto_calculate:
            self.dispatch_pipeline_request()

    def dispatch_pipeline_request(self):
        """Dispatch a new filter pipeline execution."""
        if self.raw_image is None or self.full_raw_image is None:
            return

        if self.is_processing:
            self.has_pending_request = True
            return

        try:
            sx_full = int(self.txt_x.text())
            sy_full = int(self.txt_y.text())
            sr_full = int(self.txt_r.text())
        except ValueError:
            return

        scale_factor = self.full_raw_image.shape[0] / float(self.preview_image.shape[0]) if self.preview_image is not None else 1.0
        sx_preview = int(round(sx_full / scale_factor))
        sy_preview = int(round(sy_full / scale_factor))
        sr_preview = int(round(sr_full / scale_factor))

        if self.btn_compare.isChecked():
            self.btn_compare.setChecked(False)
            self.show_original_mode = False

        self.is_processing = True
        self.has_pending_request = False
        self.status_label.setText("Status: Processing Filters...")
        self.status_label.setStyleSheet("color: #e5a00d; font-weight: bold;")

        pre_mode = "log" if self.combo_pre_mode.currentIndex() == 1 else "asinh"
        pre_val = (self.sl_pre_stretch.value() / 10.0) if pre_mode == "log" else float(self.sl_pre_stretch.value())

        params = {
            "pre_stretch_enabled": self.sec_pre_stretch.is_filter_active(),
            "pre_stretch_mode": pre_mode,
            "pre_stretch_val": pre_val,
            "noise_gate_enabled": self.sec_noise_gate.is_filter_active(),
            "noise_gate_str": self.sl_noise_gate_str.value(),
            "noise_gate_thr": self.sl_noise_gate_thr.value(),
            "bilateral_enabled": self.sec_bilateral.is_filter_active(),
            "bilateral_str": self.sl_bilateral_str.value(),
            "bilateral_d": self.sl_bilateral_d.value(),
            "bilateral_sc": 30,
            "bilateral_ss": self.sl_bilateral_ss.value(),
            "fnrgf_enabled": self.sec_fnrgf.is_filter_active(),
            "fnrgf_str": self.sl_fnrgf_str.value(),
            "fnrgf_ord": self.sl_fnrgf_ord.value(),
            "fnrgf_seg": self.sl_fnrgf_seg.value(),
            "fnrgf_cut": self.sl_fnrgf_cut.value(),
            "fnrgf_rad": self.sl_fnrgf_rad.value(),
            "fnrgf_rmax": self.sl_fnrgf_rmax.value(),
            "fnrgf_nbins": self.sl_fnrgf_nbins.value(),
            "fnrgf_width_func": "mad" if self.combo_fnrgf_width.currentIndex() == 1 else "std",
            "fnrgf_radial_binning": "log" if self.combo_fnrgf_binning.currentIndex() == 1 else "linear",
            "fnrgf_apply_mask": self.sl_fnrgf_mask.value(),
            "mgn_enabled": self.sec_mgn.is_filter_active(),
            "mgn_str": self.sl_mgn_str.value(),
            "mgn_gam": self.sl_mgn_gam.value(),
            "mgn_k": self.sl_mgn_k.value(),
            "mgn_h": self.sl_mgn_h.value(),
            "mgn_trunc": self.sl_mgn_trunc.value(),
            "rhef_enabled": self.sec_rhef.is_filter_active(),
            "rhef_str": self.sl_rhef_str.value(),
            "rhef_rad": self.sl_rhef_rad.value(),
            "rhef_upsilon": self.sl_rhef_upsilon.value(),
            "wow_enabled": self.sec_wow.is_filter_active(),
            "wow_str": self.sl_wow_str.value(),
            "wow_scales": self.sl_wow_scales.value(),
            "wow_gam": self.sl_wow_gam.value(),
            "wow_h": self.sl_wow_h.value(),
            "usm_enabled": self.sec_usm.is_filter_active(),
            "usm_str": self.sl_usm_str.value(),
            "usm_radius": self.sl_usm_radius.value(),
            "usm_sigma": self.sl_usm_amount.value() / 10.0,
            "achf_enabled": self.sec_achf.is_filter_active(),
            "achf_str": self.sl_achf_str.value(),
            "achf_kernel": self.sl_achf_kernel.value(),
            "achf_boost": self.sl_achf_boost.value(),
            "sx": sx_preview,
            "sy": sy_preview,
            "sr": sr_preview,
        }
        self.request_processing_signal.emit(self.raw_image, params)

    def on_processing_finished(self, output_matrix: np.ndarray):
        """Handle filter pipeline completion."""
        self.processed_image = output_matrix
        self.is_processing = False
        self.status_label.setText("Status: Pipeline Ready")
        self.status_label.setStyleSheet("color: #00ff00; font-weight: bold;")
        self.render_matrix_to_screen()

        if self.has_pending_request:
            self.has_pending_request = False
            self.dispatch_pipeline_request()

    def apply_recommended_parameters_to_gui(self, r_full: float, w_full: int, h_full: int):
        """Auto-populate sliders based on image resolution."""
        if r_full <= 5:
            return

        solar_angular_radius_arcsec = 960.0
        pixel_scale_arcsec = solar_angular_radius_arcsec / float(r_full)

        rec_bilateral_px = max(0.5, r_full * 0.005)
        rec_usm_radius_px = max(1.0, r_full * 0.012)
        rec_achf_kernel_px = max(1.5, r_full * 0.025)

        rec_fnrgf_nbins = int(np.clip(r_full * 0.20, 50, 300))
        rec_fnrgf_ord = int(np.clip(r_full * 0.015 + 4, 6, 24))
        rec_fnrgf_rmax = min(4.5, (min(w_full, h_full) / 2.0) / float(r_full))
        rec_wow_scales = int(np.clip(np.log2(r_full / 8.0), 3, 8))

        print(f"\n{'='*80}")
        print(f"🔬 RECOMMENDED SCIENTIFIC FILTER PARAMETERS (Based on R_sun = {r_full:.1f} px @ 100%)")
        print(f"{'='*80}")
        print(f"📊 Astrometric Properties:")
        print(f"   • Sensor Plate Scale : {pixel_scale_arcsec:.3f} arcsec/pixel")
        print(f"   • Full Sensor Size   : {w_full} × {h_full} px")
        print(f"   • Coronal Coverage   : up to ~{rec_fnrgf_rmax:.2f} R_sun (limited by frame bounds)")
        print(f"\n⚙️ Applied Initial Slider Positions:")
        print(f"   [0] PRE-STRETCH       : Log Exp = 1.0 (K=10^1.0) | Range: 0.0 to 6.0")
        print(f"   [1] BILATERAL DENOISE : Blur Radius ~ {rec_bilateral_px * 10:.0f} (slider value = {rec_bilateral_px:.1f} px)")
        print(f"   [2] FNRGF ENGINE      : Order = {rec_fnrgf_ord} | Radial Bins = {rec_fnrgf_nbins} | R_max = {rec_fnrgf_rmax:.1f} R_sun")
        print(f"   [3] RHEF ENGINE       : App Radius = 10 (1.0 R_sun) | Upsilon = 35")
        print(f"   [4] MGN ENGINE        : Gamma = 32 | k = 70 | h = 70 | Trunc = 3")
        print(f"   [5] WOW ENGINE        : Wavelet Scales = {rec_wow_scales} | Gamma = 32 | h = 20")
        print(f"   [6] USM SHARPENING    : Blur Radius ~ {rec_usm_radius_px * 10:.0f} (slider value = {rec_usm_radius_px:.1f} px)")
        print(f"   [7] ACHF FILTER       : Base Kernel ~ {rec_achf_kernel_px * 10:.0f} (slider value = {rec_achf_kernel_px:.1f} px)")
        print(f"{'='*80}\n")

        self.sl_bilateral_d.setValue(int(round(rec_bilateral_px * 10.0)))
        self.sl_fnrgf_ord.setValue(rec_fnrgf_ord)
        self.sl_fnrgf_nbins.setValue(rec_fnrgf_nbins)
        self.sl_fnrgf_rmax.setValue(int(round(rec_fnrgf_rmax * 10.0)))
        self.sl_wow_scales.setValue(rec_wow_scales)
        self.sl_usm_radius.setValue(int(round(rec_usm_radius_px * 10.0)))
        self.sl_achf_kernel.setValue(int(round(rec_achf_kernel_px * 10.0)))

    def auto_detect_moon_action(self):
        """Auto-detect lunar disk parameters."""
        if self.raw_image is None or self.full_raw_image is None:
            return
        self.status_label.setText("Status: Detecting lunar disk...")
        self.status_label.setStyleSheet("color: #e5a00d; font-weight: bold;")
        QApplication.processEvents()

        cx_prev, cy_prev, r_prev = self.detect_lunar_limb(self.raw_image)
        scale_factor = self.full_raw_image.shape[0] / float(self.raw_image.shape[0])

        cx_full = int(round(cx_prev * scale_factor))
        cy_full = int(round(cy_prev * scale_factor))
        r_full = int(round(r_prev * scale_factor))

        self.txt_x.setText(str(cx_full))
        self.txt_y.setText(str(cy_full))
        self.txt_r.setText(str(r_full))
        self.trigger_circle_redraw()

        self.status_label.setText(f"Status: Moon detected (Full-res X:{cx_full}, Y:{cy_full}, R:{r_full})")
        self.status_label.setStyleSheet("color: #00ff00; font-weight: bold;")

    def detect_lunar_limb(self, raw_img: np.ndarray) -> Tuple[int, int, int]:
        """Detect lunar disk center and radius using Hough Circle Transform."""
        if raw_img is None:
            return 0, 0, 100

        if raw_img.ndim == 3:
            if raw_img.shape[2] in (3, 4):
                img_gray = 0.299 * raw_img[:, :, 0] + 0.587 * raw_img[:, :, 1] + 0.114 * raw_img[:, :, 2]
            elif raw_img.shape[0] in (3, 4):
                img_gray = 0.299 * raw_img[0, :, :] + 0.587 * raw_img[1, :, :] + 0.114 * raw_img[2, :, :]
            else:
                img_gray = raw_img[:, :, 0]
        else:
            img_gray = raw_img

        h, w = img_gray.shape
        clean_img = np.nan_to_num(img_gray, nan=0.0)
        norm = cv2.normalize(clean_img, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)

        scale = 800.0 / max(h, w)
        sw, sh = int(w * scale), int(h * scale)
        small = cv2.resize(norm, (sw, sh), interpolation=cv2.INTER_AREA)
        filtered = cv2.bilateralFilter(small, 9, 75, 75)

        circles = cv2.HoughCircles(
            filtered,
            cv2.HOUGH_GRADIENT,
            dp=1.2,
            minDist=min(sw, sh) // 4,
            param1=100,
            param2=30,
            minRadius=int(min(sw, sh) * 0.04),
            maxRadius=int(min(sw, sh) * 0.48),
        )

        best_candidate = None
        if circles is not None:
            circles = np.round(circles[0, :]).astype(int)
            best_contrast = -1.0
            for cx, cy, r in circles:
                if cx - r < 0 or cx + r >= sw or cy - r < 0 or cy + r >= sh:
                    continue
                mask_in = np.zeros((sh, sw), dtype=np.uint8)
                mask_out = np.zeros((sh, sw), dtype=np.uint8)
                cv2.circle(mask_in, (cx, cy), int(r * 0.8), 255, -1)
                cv2.circle(mask_out, (cx, cy), int(r * 1.25), 255, -1)
                cv2.circle(mask_out, (cx, cy), int(r * 1.05), 0, -1)

                contrast = cv2.mean(small, mask=mask_out)[0] - cv2.mean(small, mask=mask_in)[0]
                if contrast > best_contrast and contrast > 5:
                    best_contrast = contrast
                    best_candidate = (int(cx / scale), int(cy / scale), int(r / scale))

        if best_candidate is None:
            return w // 2, h // 2, min(w, h) // 4

        init_cx, init_cy, init_r = best_candidate
        r_search = int(init_r * 0.15)
        radii = np.arange(max(10, init_r - r_search), min(min(w, h) // 2, init_r + r_search))
        angles = np.linspace(0, 2 * np.pi, 72, endpoint=False)

        edge_pts = []
        for ang in angles:
            xs = np.clip((init_cx + radii * np.cos(ang)).astype(int), 0, w - 1)
            ys = np.clip((init_cy + radii * np.sin(ang)).astype(int), 0, h - 1)
            profile = norm[ys, xs].astype(float)
            grad = np.diff(profile)
            if len(grad) > 0 and grad.max() > 5:
                best_r = radii[np.argmax(grad)]
                edge_pts.append((init_cx + best_r * np.cos(ang), init_cy + best_r * np.sin(ang)))

        if len(edge_pts) >= 12:
            pts = np.array(edge_pts)
            x_pts, y_pts = pts[:, 0], pts[:, 1]
            A = np.column_stack([x_pts, y_pts, np.ones_like(x_pts)])
            B = -(x_pts**2 + y_pts**2)
            try:
                sol, _, _, _ = np.linalg.lstsq(A, B, rcond=None)
                final_cx, final_cy = -sol[0] / 2.0, -sol[1] / 2.0
                final_r = np.sqrt(max(1.0, final_cx**2 + final_cy**2 - sol[2]))
                if abs(final_cx - init_cx) < init_r * 0.2 and abs(final_cy - init_cy) < init_r * 0.2:
                    return int(round(final_cx)), int(round(final_cy)), int(round(final_r))
            except Exception:
                pass

        return init_cx, init_cy, init_r

    def load_image_action(self):
        """Load an astronomical image (FITS, XISF, TIFF, etc)."""
        file_filter = (
            "All Supported Images (*.tiff *.tif *.fits *.fit *.fts *.xisf *.png *.jpg *.jpeg *.bmp);;"
            "Astronomical FITS (*.fits *.fit *.fts);;"
            "PixInsight XISF (*.xisf);;"
            "TIFF Images (*.tiff *.tif);;"
            "PNG Images (*.png);;"
            "All Files (*)"
        )
        file_path, _ = QFileDialog.getOpenFileName(self, "Load Solar Master Frame", "", file_filter)
        if not file_path:
            return

        try:
            img = None
            lower_path = file_path.lower()

            if lower_path.endswith(".xisf"):
                try:
                    import xisf
                    xisf_file = xisf.XISF(file_path)
                    img = xisf_file.read_image(0)
                except Exception as e:
                    print(f"XISF reader warning: {e}")

            if img is None and lower_path.endswith((".fits", ".fit", ".fts")):
                try:
                    from astropy.io import fits
                    with fits.open(file_path) as hdul:
                        for hdu in hdul:
                            if hdu.data is not None and isinstance(hdu.data, np.ndarray) and hdu.data.ndim >= 2:
                                img = np.squeeze(hdu.data)
                                break
                except Exception as e:
                    print(f"FITS reader warning: {e}")

            if img is None:
                try:
                    with tifffile.TiffFile(file_path) as tif:
                        img = tif.pages[0].asarray()
                except Exception:
                    pass

            if img is None:
                img = cv2.imread(file_path, cv2.IMREAD_UNCHANGED)

            if img is None:
                from PIL import Image
                with Image.open(file_path) as pil_img:
                    img = np.array(pil_img)

            if img is None:
                raise ValueError("Could not decode image with any available decoder.")

            if img.ndim == 3:
                if img.dtype != np.float32:
                    img = img.astype(np.float32)
                if img.shape[2] in (3, 4):
                    img = 0.299 * img[:, :, 0] + 0.587 * img[:, :, 1] + 0.114 * img[:, :, 2]
                elif img.shape[0] in (3, 4):
                    img = 0.299 * img[0, :, :] + 0.587 * img[1, :, :] + 0.114 * img[2, :, :]
            elif img.ndim > 3:
                img = np.squeeze(img)

            self.full_raw_image = np.ascontiguousarray(img, dtype=np.float32)
            h_full, w_full = self.full_raw_image.shape[:2]

            max_dim = 1500
            if max(h_full, w_full) > max_dim:
                self.preview_scale = max_dim / float(max(h_full, w_full))
                new_w, new_h = int(w_full * self.preview_scale), int(h_full * self.preview_scale)
                self.preview_image = cv2.resize(self.full_raw_image, (new_w, new_h), interpolation=cv2.INTER_AREA)
                self.raw_image = self.preview_image.copy()
            else:
                self.preview_scale = 1.0
                self.preview_image = self.full_raw_image.copy()
                self.raw_image = self.full_raw_image.copy()

            self.processed_image = self.raw_image.copy()
            scale_ratio = h_full / float(self.preview_image.shape[0])
            self.lbl_scale_info.setText(f"Scale: {scale_ratio:.1f}x (100% = {w_full}×{h_full}px)")

            cx_prev, cy_prev, r_prev = self.detect_lunar_limb(self.raw_image)
            cx_full = int(round(cx_prev * scale_ratio))
            cy_full = int(round(cy_prev * scale_ratio))
            r_full = int(round(r_prev * scale_ratio))

            self.txt_x.setText(str(cx_full))
            self.txt_y.setText(str(cy_full))
            self.txt_r.setText(str(r_full))

            self.apply_recommended_parameters_to_gui(r_full, w_full, h_full)

            self.render_matrix_to_screen()
            self.status_label.setText(f"Status: Loaded {os.path.basename(file_path)} (X:{cx_full}, Y:{cy_full}, R:{r_full})")
            self.status_label.setStyleSheet("color: #00ff00; font-weight: bold;")
        except Exception as e:
            self.status_label.setText(f"❌ Error loading file: {str(e)[:40]}")
            self.status_label.setStyleSheet("color: #ff3333; font-weight: bold;")
            print(f"Detailed file load error: {e}")

    def export_image_action(self):
        """Export the full-resolution processed image."""
        if self.raw_image is None or self.full_raw_image is None:
            self.status_label.setText("Status: No image loaded")
            return

        try:
            sx_full = int(self.txt_x.text())
            sy_full = int(self.txt_y.text())
            sr_full = int(self.txt_r.text())
        except ValueError:
            self.status_label.setText("Status: Invalid Sun center or radius")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "Export Filtered Image", "", "TIFF Files (*.tiff *.tif)")
        if not file_path:
            return

        if not file_path.lower().endswith((".tiff", ".tif")):
            file_path += ".tiff"

        try:
            export_start = time.time()
            worker = FilterWorker()
            scale_factor = self.full_raw_image.shape[0] / float(self.preview_image.shape[0]) if self.preview_image is not None else 1.0

            print(f"\n{'='*80}\n[EXPORT] Full-resolution pipeline starting (Scale: {scale_factor:.2f}x | Multithreaded: {CPU_CORES} CPUs)\n{'='*80}")
            self.status_label.setText(f"Status: Exporting full resolution ({scale_factor:.2f}x)...")
            self.status_label.setStyleSheet("color: #e5a00d; font-weight: bold;")
            QApplication.processEvents()

            img = self.full_raw_image.copy()

            # APPLY ALL ENABLED FILTERS (same as preview pipeline)
            if self.sec_pre_stretch.is_filter_active():
                t0 = time.time()
                pre_mode = "log" if self.combo_pre_mode.currentIndex() == 1 else "asinh"
                pre_val = (self.sl_pre_stretch.value() / 10.0) if pre_mode == "log" else float(self.sl_pre_stretch.value())
                if pre_mode == "log":
                    img = worker.run_pre_log(img, pre_val)
                    print(f"[EXPORT: PRE-LOG] Done in {time.time() - t0:.3f}s (K=10^{pre_val:.1f})")
                else:
                    img = worker.run_pre_asinh(img, pre_val)
                    print(f"[EXPORT: PRE-ASINH] Done in {time.time() - t0:.3f}s (Factor={pre_val})")

            if self.sec_noise_gate.is_filter_active():
                t0 = time.time()
                img = worker.run_radial_noise_gate(
                    img, self.sl_noise_gate_str.value(), self.sl_noise_gate_thr.value(), sx_full, sy_full, sr_full
                )
                print(f"[EXPORT: NOISE GATE] Done in {time.time() - t0:.3f}s")

            if self.sec_bilateral.is_filter_active():
                t0 = time.time()
                d_scaled = max(1, int(round(self.sl_bilateral_d.value() * scale_factor)))
                img = worker.run_bilateral_denoise(img, self.sl_bilateral_str.value(), d_scaled, 30, self.sl_bilateral_ss.value())
                print(f"[EXPORT: BILATERAL] Done in {time.time() - t0:.3f}s (d={d_scaled})")

            if self.sec_fnrgf.is_filter_active():
                t0 = time.time()
                img = worker.run_fnrgf_native(
                    img,
                    self.sl_fnrgf_str.value(),
                    self.sl_fnrgf_ord.value(),
                    self.sl_fnrgf_seg.value(),
                    self.sl_fnrgf_cut.value(),
                    self.sl_fnrgf_rad.value(),
                    self.sl_fnrgf_rmax.value(),
                    self.sl_fnrgf_nbins.value(),
                    sx_full,
                    sy_full,
                    sr_full,
                    width_function="mad" if self.combo_fnrgf_width.currentIndex() == 1 else "std",
                    radial_binning="log" if self.combo_fnrgf_binning.currentIndex() == 1 else "linear",
                    apply_mask=self.sl_fnrgf_mask.value(),
                )
                print(f"[EXPORT: FNRGF NATIVE] Done in {time.time() - t0:.3f}s")

            if self.sec_rhef.is_filter_active():
                t0 = time.time()
                img = worker.run_rhef_native(
                    img, self.sl_rhef_str.value(), self.sl_rhef_rad.value(), self.sl_rhef_upsilon.value(), sx_full, sy_full, sr_full
                )
                print(f"[EXPORT: RHEF NATIVE] Done in {time.time() - t0:.3f}s")

            if self.sec_mgn.is_filter_active():
                t0 = time.time()
                img = worker.run_mgn_native(
                    img,
                    self.sl_mgn_str.value(),
                    self.sl_mgn_gam.value(),
                    self.sl_mgn_k.value(),
                    self.sl_mgn_h.value(),
                    self.sl_mgn_trunc.value(),
                )
                print(f"[EXPORT: MGN NATIVE] Done in {time.time() - t0:.3f}s")

            if self.sec_wow.is_filter_active():
                t0 = time.time()
                img = worker.run_wow_native(
                    img, self.sl_wow_str.value(), self.sl_wow_scales.value(), self.sl_wow_gam.value(), self.sl_wow_h.value()
                )
                print(f"[EXPORT: WOW NATIVE] Done in {time.time() - t0:.3f}s")

            if self.sec_usm.is_filter_active():
                t0 = time.time()
                usm_rad_scaled = self.sl_usm_radius.value() * scale_factor
                usm_sigma_amount = self.sl_usm_amount.value() / 10.0
                img = worker.run_usm(img, self.sl_usm_str.value(), usm_rad_scaled, usm_sigma_amount)
                print(f"[EXPORT: USM] Done in {time.time() - t0:.3f}s (radius={usm_rad_scaled:.1f})")

            if self.sec_achf.is_filter_active():
                t0 = time.time()
                achf_kernel_scaled = max(1, int(round(self.sl_achf_kernel.value() * scale_factor)))
                img = worker.run_achf(
                    img, self.sl_achf_str.value(), achf_kernel_scaled, self.sl_achf_boost.value(), sx_full, sy_full, sr_full
                )
                print(f"[EXPORT: ACHF] Done in {time.time() - t0:.3f}s (kernel={achf_kernel_scaled})")

            img_clean = np.nan_to_num(img, nan=0.0)
            i_min, i_max = float(np.min(img_clean)), float(np.max(img_clean))
            if i_max - i_min > 1e-6:
                img_norm = (img_clean - i_min) / (i_max - i_min)
            else:
                img_norm = np.zeros_like(img_clean)

            img_16bit = np.clip(img_norm * 65535.0, 0, 65535).astype(np.uint16)

            t0 = time.time()
            tifffile.imwrite(file_path, img_16bit, compression="zlib", maxworkers=CPU_CORES, metadata={"scale_factor": scale_factor})
            print(f"[EXPORT: DISK WRITE] Done in {time.time() - t0:.3f}s")
            
            # Create JPEG copy with gamma 2.2 for easy viewing
            t0 = time.time()
            jpeg_path = file_path.rsplit('.', 1)[0] + "_gamma2_2.jpg"
            
            # Apply gamma 2.2 correction
            img_gamma = np.power(img_norm, 1.0 / 2.2)
            img_gamma = np.clip(img_gamma * 255.0, 0, 255).astype(np.uint8)
            
            # Save as JPEG with high quality
            cv2.imwrite(jpeg_path, img_gamma, [cv2.IMWRITE_JPEG_QUALITY, 95])
            print(f"[EXPORT: JPEG GAMMA 2.2] Done in {time.time() - t0:.3f}s")
            
            print(f"[EXPORT] Finished successfully in {time.time() - export_start:.3f}s\n{'='*80}\n")

            self.status_label.setText(f"Status: Exported to {os.path.basename(file_path)} + {os.path.basename(jpeg_path)}")
            self.status_label.setStyleSheet("color: #00ff00; font-weight: bold;")
        except Exception as e:
            print(f"Export failed with exception: {e}")
            self.status_label.setText(f"Status: Export failed - {str(e)[:40]}")
            self.status_label.setStyleSheet("color: #ff0000; font-weight: bold;")

    def render_matrix_to_screen(self):
        """Render the processed image to the screen with stretch applied."""
        if self.raw_image is None or self.full_raw_image is None:
            return

        proc_mat = self.processed_image if self.processed_image is not None else self.raw_image
        orig_mat = self.raw_image

        proc_cleaned = np.nan_to_num(proc_mat, nan=0.0)
        orig_cleaned = np.nan_to_num(orig_mat, nan=0.0)

        p_min, p_max = float(np.min(proc_cleaned)), float(np.max(proc_cleaned))
        o_min, o_max = float(np.min(orig_cleaned)), float(np.max(orig_cleaned))

        p_norm = (proc_cleaned - p_min) / (p_max - p_min + 1e-5)
        o_norm = (orig_cleaned - o_min) / (o_max - o_min + 1e-5)

        mode_idx = self.combo_stretch_mode.currentIndex()

        if mode_idx == 1:
            log_exp = self.sl_stretch.value() / 10.0
            k = 10.0 ** log_exp
            denom = float(np.log1p(k))
            p_stretch = np.log1p(k * p_norm) / denom
            o_stretch = np.log1p(k * o_norm) / denom
        elif mode_idx == 2:
            stretch_val = float(self.sl_stretch.value())
            sp_val = (self.sl_ghs_sp.value() / 1000.0) * 0.5
            b_val = self.sl_ghs_b.value() / 10.0
            bp_val = self.sl_ghs_bp.value() / 1000.0
            p_stretch = self.apply_ghs(p_norm, stretch_val, sp_val, b_val, bp_val)
            o_stretch = self.apply_ghs(o_norm, stretch_val, sp_val, b_val, bp_val)
        else:
            stretch_val = float(self.sl_stretch.value())
            p_stretch = np.arcsinh(p_norm * stretch_val) / np.arcsinh(stretch_val)
            o_stretch = np.arcsinh(o_norm * stretch_val) / np.arcsinh(stretch_val)

        final_norm = o_stretch if self.show_original_mode else cv2.addWeighted(
            p_stretch, float(self.sl_blend.value()) / 100.0, o_stretch, 1.0 - float(self.sl_blend.value()) / 100.0, 0
        )

        display_img = np.clip(final_norm * 255.0, 0, 255).astype(np.uint8)
        h, w = display_img.shape
        q_img = QImage(display_img.data, w, h, w, QImage.Format.Format_Grayscale8)
        pixmap = QPixmap.fromImage(q_img)

        viewport_size = self.image_label.size()
        scaled_pixmap = pixmap.scaled(
            viewport_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        )
        self.image_label.setPixmap(scaled_pixmap)

        h_full, w_full = self.full_raw_image.shape[:2]
        buffer_scale = h_full / float(self.preview_image.shape[0]) if self.preview_image is not None else 1.0
        display_w, display_h = scaled_pixmap.width(), scaled_pixmap.height()
        screen_scale = h_full / float(display_h) if display_h > 0 else 1.0

        self.lbl_scale_info.setText(
            f"Pipeline: {buffer_scale:.2f}x ({w}×{h}px) | Display: {screen_scale:.2f}x ({display_w}×{display_h}px)"
        )

        self.trigger_circle_redraw()

    def resizeEvent(self, event):
        """Handle window resize."""
        super().resizeEvent(event)
        self.render_matrix_to_screen()

    def closeEvent(self, event: QCloseEvent):
        """Handle window close."""
        if self.persistent_thread is not None and self.persistent_thread.isRunning():
            self.persistent_thread.quit()
            self.persistent_thread.wait()
        event.accept()
