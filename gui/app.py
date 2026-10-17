"""Main application window: EclipseProcessorApp."""

import os
import time
from pathlib import Path
from typing import Optional, Tuple

import cv2
import numpy as np
from PySide6.QtCore import QThread, QTimer, Signal, Qt
from PySide6.QtGui import QFontDatabase, QCloseEvent, QIcon, QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QCheckBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListView,
    QStyledItemDelegate,
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
from core.pipeline import execute_pipeline, prepare_parameters
from core.presentation import apply_ghs, render_presentation
from core.layer_export import export_layer_package
from core.linear_export import export_linear_sources, split_source_channels
from core.colour import neutralize_tse, colour_layer, set_luminosity
from core.image_data import resize_observed, recipe_parameters, normalize_observed
from gui.components import ClickableLabel, CollapsibleSection, FullRowCheckBox, InWindowTooltips
from gui.factories import (
    create_filter_group,
    create_slider,
    create_slider_float,
    create_stepper_input,
    create_dyadic_slider,
)
from utils.helpers import application_icon_path, recommended_radial_bins


class EclipseProcessorApp(QMainWindow):
    """Main application window for solar eclipse processing."""

    request_processing_signal = Signal(np.ndarray, dict)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Corona Enhance Filters v0.4.0")
        self.resize(1180, 780)
        self.setMinimumSize(960, 600)

        self.setWindowIcon(QIcon(application_icon_path()))

        self.raw_image: Optional[np.ndarray] = None
        self.processed_image: Optional[np.ndarray] = None
        self.full_raw_image: Optional[np.ndarray] = None
        self.preview_image: Optional[np.ndarray] = None
        self.source_path: Optional[str] = None
        self.full_source_rgb: Optional[np.ndarray] = None
        self.source_rgb_white = 1.
        self._colour_cache = None
        self.preview_scale: float = 1.0
        self.show_original_mode: bool = False
        self.auto_calculate: bool = True
        self.is_processing: bool = False
        self.has_pending_request: bool = False
        # Only one worker job runs at a time; revisions reject obsolete results
        # without interrupting numerical work or losing the latest UI settings.
        self._preview_revision = 0
        self._running_revision = None
        self._running_image = None
        self._pending_manual = False
        self.sp_picker_active: bool = False
        self.recalculation_timer = QTimer(self)
        self.recalculation_timer.setSingleShot(True)
        self.recalculation_timer.setInterval(300)
        self.recalculation_timer.timeout.connect(self.dispatch_pipeline_request)

        self.persistent_thread = QThread()
        self.filter_worker = FilterWorker()
        self.filter_worker.moveToThread(self.persistent_thread)
        self.request_processing_signal.connect(self.filter_worker.process_pipeline)
        self.filter_worker.finished.connect(self.on_processing_finished)
        self.filter_worker.failed.connect(self.on_processing_failed)
        self.persistent_thread.start()

        self._build_ui()
        self.in_window_tooltips = InWindowTooltips(self)

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
        self.image_label.circle_center_requested.connect(self.on_circle_center_requested)
        self.image_label.setToolTip("Monochrome preview. Ctrl-click (Command-click on macOS) to move the disk center. With the shadow picker enabled, click to sample the processed intensity before display stretching.")
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
        self.status_label.setToolTip("Processing, pending changes and export status. Pipeline Ready means the latest requested preview has completed.")
        self.status_label.setStyleSheet("color: #9cdcfe; font-weight: bold; font-size: 11px;")
        top_header_layout.addWidget(self.status_label)

        btn_row = QHBoxLayout()
        self.btn_load = QPushButton("📁 Open Image")
        self.btn_load.setStyleSheet("QPushButton { background-color: #3c3c3c; color: #e5a00d; border: 1px solid #555555; border-radius: 4px; padding: 6px; font-weight: bold; font-size: 11px; } QPushButton:hover { background-color: #4a4a4a; border: 1px solid #e5a00d; }")
        self.btn_load.setToolTip("Open TIFF, FITS, XISF, PNG, JPEG or BMP. Filters use monochrome intensity; source RGB is retained for export. Missing samples remain excluded.")
        self.btn_load.clicked.connect(self.load_image_action)
        btn_row.addWidget(self.btn_load)

        self.btn_compare = QPushButton("👁️ View Original")
        self.btn_compare.setStyleSheet("QPushButton { background-color: #3c3c3c; color: #e5a00d; border: 1px solid #555555; border-radius: 4px; padding: 6px; font-weight: bold; font-size: 11px; } QPushButton:hover { background-color: #4a4a4a; border: 1px solid #e5a00d; }")
        self.btn_compare.setCheckable(True)
        self.btn_compare.setToolTip("Temporarily compare processed and original monochrome intensity with the selected display stretch. This comparison does not change the exported Reveal blend.")
        self.btn_compare.clicked.connect(self.toggle_compare_mode)
        btn_row.addWidget(self.btn_compare)

        self.btn_auto_calc = QPushButton("Auto Calculate")
        self.btn_auto_calc.setStyleSheet("QPushButton { background-color: #3c3c3c; color: #e5a00d; border: 1px solid #555555; border-radius: 4px; padding: 6px; font-weight: bold; font-size: 11px; } QPushButton:hover { background-color: #4a4a4a; border: 1px solid #e5a00d; }")
        self.btn_auto_calc.setCheckable(True)
        self.btn_auto_calc.setChecked(True)
        self.btn_auto_calc.setToolTip("Recalculate automatically after a 300 ms pause in geometry or filter adjustments")
        self.btn_auto_calc.clicked.connect(self.toggle_auto_calc_mode)
        btn_row.addWidget(self.btn_auto_calc)

        self.btn_recalc = QPushButton("🔄")
        self.btn_recalc.setFixedSize(32, 26)
        self.btn_recalc.setToolTip("Recalculate all enabled preview stages with the current settings. If processing is busy, queue the latest settings.")
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
        for section in (self.sec_pre_stretch, self.sec_noise_gate, self.sec_bilateral,
                        self.sec_fnrgf, self.sec_mgn, self.sec_wow, self.sec_rhef,
                        self.sec_usm, self.sec_achf):
            for slider in section.findChildren(QSlider):
                slider.valueChanged.connect(
                    lambda value, section=section: self.on_filter_slider_released(section, None))
        self._build_stretch_section(control_layout)
        section_help = {
            self.sec_geo: "Set the disk center and reference radius in native image pixels for radial filtering and the circle overlay.",
            self.sec_pre_stretch: "Optional nonlinear input compression before the enhancement stages.",
            self.sec_noise_gate: "Attenuate low local contrast with a radius-dependent SNR gate.",
            self.sec_bilateral: "Smooth noise using gradient-weighted Gaussian averaging.",
            self.sec_fnrgf: "Fourier Normalizing Radial Gradient Filter: model annular brightness and spread as functions of angle.",
            self.sec_mgn: "Multi-scale Gaussian Normalization: combine local contrast at several scales with a global gamma image.",
            self.sec_wow: "Wavelets Optimized Whitening: normalize multiscale contrast with optional noise suppression.",
            self.sec_rhef: "Radial Histogram Equalization: map intensities to ranks within radial distributions.",
            self.sec_usm: "Unsharp Mask: amplify the difference between the input and a Gaussian blur.",
            self.sec_achf: "Adaptive Circular High-Pass Filter: use symmetric accepted neighbor pairs to extract signed detail.",
            self.sec_stretch: "Presentation stretching after the sequential filters; the numerical source remains separate.",
        }
        for section, description in section_help.items():
            section.toggle_btn.setToolTip(description + " Click to expand or collapse controls; this does not enable the stage.")
            if section.chk_active is not None:
                section.chk_active.setToolTip(description + " Enable or bypass this stage without resetting its controls.")

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
        self.lbl_scale_info.setToolTip("Pipeline scale compares native image pixels with preview pixels; display scale compares native pixels with the fitted on-screen image. Geometry is entered in native pixels.")
        self.lbl_scale_info.setStyleSheet("color: #e5a00d; font-size: 10px; font-weight: bold;")
        self.sec_geo.content_layout.addWidget(self.lbl_scale_info)

        self.txt_x.textChanged.connect(self.trigger_circle_redraw)
        self.txt_y.textChanged.connect(self.trigger_circle_redraw)
        self.txt_r.textChanged.connect(self.trigger_circle_redraw)
        for field in (self.txt_x, self.txt_y, self.txt_r):
            field.textChanged.connect(lambda _: self.dispatch_pipeline_request_if_auto())

        self.btn_auto_moon = QPushButton("🎯 Auto-detect Lunar Disk")
        self.btn_auto_moon.setStyleSheet("QPushButton { background-color: #3c3c3c; color: #e5a00d; border: 1px solid #555555; border-radius: 4px; padding: 6px; font-weight: bold; font-size: 11px; } QPushButton:hover { background-color: #4a4a4a; border: 1px solid #e5a00d; }")
        self.btn_auto_moon.setToolTip("Estimate disk geometry from a closed circular missing-data boundary, or use robust contrast normalization, Hough detection and limb refinement. A missing-data boundary is not necessarily the physical lunar limb.")
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
        self.combo_pre_mode.setToolTip("Choose optional Asinh or logarithmic compression before noise reduction and enhancement. This changes filter input and is separate from the final display stretch.")
        self.combo_pre_mode.currentIndexChanged.connect(self._on_pre_stretch_mode_changed)
        mode_lbl.setToolTip(self.combo_pre_mode.toolTip())
        mode_row.addWidget(mode_lbl)
        mode_row.addWidget(self.combo_pre_mode)
        self.sec_pre_stretch.content_layout.addLayout(mode_row)

        self.sl_pre_stretch, self.lbl_pre_stretch = create_slider(
            "Factor (Asinh / Log Exp)", 1, 100, 10, self.sec_pre_stretch.content_layout,
            on_release_callback=self.dispatch_pipeline_request_if_auto,
            tooltip="Asinh uses the displayed factor (1–100). Log uses K = 10^(value/10), from 1 to 10^6. Applied only when this stage is active."
        )
        self.sec_pre_stretch.toggled_active.connect(self.on_filter_toggled)
        layout.addWidget(self.sec_pre_stretch)

        denoising_group = create_filter_group("🔇 DENOISING & NOISE SUPPRESSION", layout)
        self.sec_noise_gate = CollapsibleSection("RADIAL NOISE GATE", has_checkbox=True, is_expanded=False, is_active=False)
        self.sl_noise_gate_str, _ = create_slider(
            "Gate Strength (%)", 0, 100, 10, self.sec_noise_gate.content_layout,
            on_release_callback=lambda: self.on_filter_slider_released(self.sec_noise_gate, self.sl_noise_gate_str),
            tooltip="Blend the radial low-SNR attenuation with the input: 0 bypasses it; 100 applies the full gate. Check faint structures before increasing strength."
        )
        self.sl_noise_gate_thr, _ = create_slider(
            "SNR Threshold (×100)", 1, 50, 10, self.sec_noise_gate.content_layout,
            on_release_callback=lambda: self.on_filter_slider_released(self.sec_noise_gate, self.sl_noise_gate_str),
            tooltip="Base SNR threshold = value/100, multiplied by (1 + 2r/R) at each pixel. Higher values attenuate more low-SNR signal; this is a local contrast estimate, not calibrated detector SNR."
        )
        self.sec_noise_gate.toggled_active.connect(lambda active: self.on_filter_toggled(active, self.sl_noise_gate_str))
        denoising_group.addWidget(self.sec_noise_gate)

        self.sec_bilateral = CollapsibleSection("EDGE-PRESERVING DENOISE", has_checkbox=True, is_expanded=False, is_active=False)
        self.sl_bilateral_str, _ = create_slider(
            "Strength (%)", 0, 100, 10, self.sec_bilateral.content_layout,
            on_release_callback=lambda: self.on_filter_slider_released(self.sec_bilateral, self.sl_bilateral_str),
            tooltip="Blend gradient-weighted Gaussian smoothing with the input: 0 bypasses it; 100 applies the full smoothing result."
        )
        self.sl_bilateral_d, _ = create_slider(
            "Blur Radius (×10)", 3, 50, 5, self.sec_bilateral.content_layout,
            on_release_callback=lambda: self.on_filter_slider_released(self.sec_bilateral, self.sl_bilateral_str),
            tooltip="Gaussian sigma = max(0.5, value/10) in preview pixels, scaled for full-resolution export. Higher values smooth a wider area."
        )
        self.sl_bilateral_ss, _ = create_slider(
            "Edge Sensitivity (×100)", 5, 100, 50, self.sec_bilateral.content_layout,
            on_release_callback=lambda: self.on_filter_slider_released(self.sec_bilateral, self.sl_bilateral_str),
            tooltip="Reduce smoothing near strong intensity gradients. Higher values preserve edges more strongly; the displayed sensitivity is divided by 100."
        )
        self.sec_bilateral.toggled_active.connect(lambda active: self.on_filter_toggled(active, self.sl_bilateral_str))
        denoising_group.addWidget(self.sec_bilateral)

        radial_group = create_filter_group("🔄 RADIAL ENHANCEMENT", layout)
        self.sec_fnrgf = CollapsibleSection("FNRGF", has_checkbox=True, is_expanded=False, is_active=False)
        self.sl_fnrgf_str, _ = create_slider(
            "Strength (%)", 0, 100, 10, self.sec_fnrgf.content_layout,
            on_release_callback=lambda: self.on_filter_slider_released(self.sec_fnrgf, self.sl_fnrgf_str),
            tooltip="Blend percentage of the radial gradient filter (0=off, 100=full effect)"
        )
        self.sl_fnrgf_ord, _ = create_slider(
            "Fourier Order", 1, 50, 6, self.sec_fnrgf.content_layout,
            on_release_callback=lambda: self.on_filter_slider_released(self.sec_fnrgf, self.sl_fnrgf_str),
            tooltip="Highest angular Fourier harmonic in the annular brightness and spread models. Higher orders follow finer angular variations; they do not guarantee additional real detail."
        )
        self.sl_fnrgf_seg, _ = create_dyadic_slider(
            "Angular Segments", 4, 8, 4, self.sec_fnrgf.content_layout,
            on_release_callback=lambda: self.on_filter_slider_released(self.sec_fnrgf, self.sl_fnrgf_str),
            tooltip="Defaults to the smallest power of 2 ≥ 2×Fourier Order + 1; resets when Fourier Order changes."
        )
        self.sl_fnrgf_cut, _ = create_slider(
            "Coefficients to Remove", 0, 7, 0, self.sec_fnrgf.content_layout,
            on_release_callback=lambda: self.on_filter_slider_released(self.sec_fnrgf, self.sl_fnrgf_str),
            tooltip="Remove this many highest-order model coefficients. Zero retains them all; the maximum is Fourier order + 1."
        )
        def sync_fnrgf_limits(_=None):
            order = self.sl_fnrgf_ord.value()
            self.sl_fnrgf_cut.setMaximum(order + 1)
            exponent = (2 * order).bit_length()
            self.sl_fnrgf_seg.setMinimum(exponent)
            self.sl_fnrgf_seg.setValue(exponent)

        self.sl_fnrgf_ord.valueChanged.connect(sync_fnrgf_limits)
        sync_fnrgf_limits()
        self.sl_fnrgf_rad, _ = create_slider(
            "App Radius (×10)", 5, 25, 10, self.sec_fnrgf.content_layout,
            on_release_callback=lambda: self.on_filter_slider_released(self.sec_fnrgf, self.sl_fnrgf_str),
            tooltip="Process only above this radius, in tenths of solar radius"
        )
        self.sl_fnrgf_rmax, _ = create_slider(
            "Outer Radius R_max (×10)", 15, 60, 30, self.sec_fnrgf.content_layout,
            on_release_callback=lambda: self.on_filter_slider_released(self.sec_fnrgf, self.sl_fnrgf_str),
            tooltip="Outer boundary = value/10 disk radii. The load-time upper limit is estimated from half the image diagonal; verify coverage when the disk is off-center."
        )
        self.sl_fnrgf_rmax.setMinimum(self.sl_fnrgf_rad.value() + 1)
        self.sl_fnrgf_rad.valueChanged.connect(
            lambda value: self.sl_fnrgf_rmax.setMinimum(value + 1))
        self.sl_fnrgf_bin_px, _ = create_slider(
            "Ring Width (pixels)", 1, 32, 4, self.sec_fnrgf.content_layout,
            on_release_callback=lambda: self.on_filter_slider_released(self.sec_fnrgf, self.sl_fnrgf_str),
            tooltip="Ring width in pixels at each processing resolution (default 4). Export increases the ring count to retain this width. For logarithmic spacing this is the inner-ring width; outer rings are wider."
        )

        w_row = QHBoxLayout()
        w_lbl = QLabel("Width Function:")
        w_lbl.setStyleSheet("color: #aaa; font-size: 11px;")
        self.combo_fnrgf_width = QComboBox()
        self.combo_fnrgf_width.addItems(["Standard Deviation (STD)", "Median Absolute Deviation (MAD)"])
        self.combo_fnrgf_width.setToolTip("Estimate sector spread using standard deviation or 1.4826 times median absolute deviation. MAD makes the spread less sensitive to outliers; the brightness model still uses sector means.")
        self.combo_fnrgf_width.currentIndexChanged.connect(lambda _: self.dispatch_pipeline_request_if_auto())
        w_lbl.setToolTip(self.combo_fnrgf_width.toolTip())
        w_row.addWidget(w_lbl)
        w_row.addWidget(self.combo_fnrgf_width)
        self.sec_fnrgf.content_layout.addLayout(w_row)

        b_row = QHBoxLayout()
        b_lbl = QLabel("Radial Binning:")
        b_lbl.setStyleSheet("color: #aaa; font-size: 11px;")
        self.combo_fnrgf_binning = QComboBox()
        self.combo_fnrgf_binning.addItems(["Linear", "Log-spaced (Corona Optimized)"])
        self.combo_fnrgf_binning.setToolTip("Linear bins have equal radial widths. Log-spaced bins are finer near the inner boundary and wider farther out.")
        self.combo_fnrgf_binning.currentIndexChanged.connect(lambda _: self.dispatch_pipeline_request_if_auto())
        b_lbl.setToolTip(self.combo_fnrgf_binning.toolTip())
        b_row.addWidget(b_lbl)
        b_row.addWidget(self.combo_fnrgf_binning)
        self.sec_fnrgf.content_layout.addLayout(b_row)

        self.sl_fnrgf_mask, _ = create_slider(
            "Apply Mask (%)", 0, 100, 0, self.sec_fnrgf.content_layout,
            on_release_callback=self.dispatch_pipeline_request_if_auto,
            tooltip="Protect the original input near r/R = 1 with a triangular band from 0.95 to 1.05. Zero disables protection; 100 removes FNRGF at the band center. This is not the missing-data mask."
        )
        self.sec_fnrgf.toggled_active.connect(lambda active: self.on_filter_toggled(active, self.sl_fnrgf_str))
        radial_group.addWidget(self.sec_fnrgf)

        multiscale_group = create_filter_group("📊 MULTI-SCALE / WAVELETS", layout)
        self.sec_mgn = CollapsibleSection("MGN", has_checkbox=True, is_expanded=False, is_active=False)
        self.sl_mgn_str, _ = create_slider(
            "Strength (%)", 0, 100, 10, self.sec_mgn.content_layout,
            on_release_callback=lambda: self.on_filter_slider_released(self.sec_mgn, self.sl_mgn_str),
            tooltip="Multi-Scale Gaussian Normalization blend strength"
        )
        self.sl_mgn_gam, _ = create_slider(
            "Gamma (×10)", 1, 100, 32, self.sec_mgn.content_layout,
            on_release_callback=lambda: self.on_filter_slider_released(self.sec_mgn, self.sl_mgn_str),
            tooltip="Global gamma exponent: displayed value / 10 (32 = 3.2)"
        )
        self.sl_mgn_k, _ = create_slider(
            "Factor k (×100)", 1, 200, 70, self.sec_mgn.content_layout,
            on_release_callback=lambda: self.on_filter_slider_released(self.sec_mgn, self.sl_mgn_str),
            tooltip="Arctangent factor k: displayed value / 100 (70 = 0.70)"
        )
        self.sl_mgn_h, _ = create_slider(
            "Global Weight h (×100)", 0, 100, 70, self.sec_mgn.content_layout,
            on_release_callback=lambda: self.on_filter_slider_released(self.sec_mgn, self.sl_mgn_str),
            tooltip="Global gamma-image weight = value/100. At 0, use local multiscale normalization; at 100, use the global gamma image. Filter Strength is applied separately."
        )
        self.sl_mgn_trunc, _ = create_slider(
            "Kernel Truncation (Sigmas)", 1, 6, 3, self.sec_mgn.content_layout,
            on_release_callback=lambda: self.on_filter_slider_released(self.sec_mgn, self.sl_mgn_str),
            tooltip="Gaussian truncation in standard deviations; all values 1–6 are honored"
        )
        self.sec_mgn.toggled_active.connect(lambda active: self.on_filter_toggled(active, self.sl_mgn_str))
        multiscale_group.addWidget(self.sec_mgn)

        self.sec_wow = CollapsibleSection("WOW", has_checkbox=True, is_expanded=False, is_active=False)
        self.sl_wow_str, _ = create_slider(
            "Strength (%)", 0, 100, 10, self.sec_wow.content_layout,
            on_release_callback=lambda: self.on_filter_slider_released(self.sec_wow, self.sl_wow_str),
            tooltip="Wavelets Optimized Whitening blend strength"
        )
        self.sl_wow_scales, _ = create_slider(
            "Wavelet Scales (0 = Auto)", 0, 10, 0, self.sec_wow.content_layout,
            on_release_callback=lambda: self.on_filter_slider_released(self.sec_wow, self.sl_wow_str),
            tooltip="0 selects the preview maximum. Export adjusts the count to the nearest power-of-two spatial scale, capped by image dimensions."
        )
        self.sl_wow_denoise = []
        for scale in range(3):
            slider, _ = create_slider(
                f"Denoise Scale {scale+1} (sigma)", 0, 10, 0,
                self.sec_wow.content_layout,
                on_release_callback=lambda: self.on_filter_slider_released(self.sec_wow, self.sl_wow_str),
                tooltip="Noise-significance threshold for this preview wavelet scale; export shifts thresholds with the spatial bands. Zero disables thresholding; higher values suppress more weak detail. Noise is estimated from the current input, with approximate thresholds on masked inputs."
            )
            self.sl_wow_denoise.append(slider)
        self.combo_wow_bilateral = QComboBox()
        self.combo_wow_bilateral.addItems(["Standard WOW", "Edge-aware WOW (bilateral = 1)"])
        self.combo_wow_bilateral.setToolTip("Choose standard or edge-aware wavelet averaging. Masked images use the observed-support starlet variant recorded in the export recipe.")
        self.combo_wow_bilateral.setCurrentIndex(1)
        self.combo_wow_bilateral.currentIndexChanged.connect(self.dispatch_pipeline_request_if_auto)
        self.sec_wow.content_layout.addWidget(self.combo_wow_bilateral)
        self.sec_wow.toggled_active.connect(lambda active: self.on_filter_toggled(active, self.sl_wow_str))
        multiscale_group.addWidget(self.sec_wow)

        histogram_group = create_filter_group("📈 RADIAL HISTOGRAM EQUALIZATION", layout)
        self.sec_rhef = CollapsibleSection("RHEF", has_checkbox=True, is_expanded=False, is_active=False)
        self.combo_rhef_mode = QComboBox()
        self.combo_rhef_mode.addItem("Legacy / compatible", "legacy")
        self.combo_rhef_mode.addItem("Continuous global", "continuous")
        self.combo_rhef_mode.setToolTip("Legacy ranks samples independently within rings. Continuous global interpolates positive log-intensity quantiles across populated neighboring rings; nonpositive and sparse samples retain their input values.")
        self.combo_rhef_mode.currentIndexChanged.connect(lambda _: self.dispatch_pipeline_request_if_auto())
        self.sec_rhef.content_layout.addWidget(self.combo_rhef_mode)
        self.sl_rhef_str, _ = create_slider(
            "Strength (%)", 0, 100, 10, self.sec_rhef.content_layout,
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
            tooltip="Exponent = value/100, applied to both rank-distribution tails. Values below 1 compress the tails toward mid-grey; 100 leaves the rank curve unchanged."
        )
        self.sl_rhef_bin, _ = create_slider(
            "Ring Width (×10 preview px)", 5, 100, 10, self.sec_rhef.content_layout,
            on_release_callback=lambda: self.on_filter_slider_released(self.sec_rhef, self.sl_rhef_str),
            tooltip="Annular width in tenths of preview pixels; scaled to full resolution on export"
        )
        self.sec_rhef.toggled_active.connect(lambda active: self.on_filter_toggled(active, self.sl_rhef_str))
        histogram_group.addWidget(self.sec_rhef)

        sharpening_group = create_filter_group("✨ SHARPENING", layout)
        self.sec_usm = CollapsibleSection("USM", has_checkbox=True, is_expanded=False, is_active=False)
        self.sl_usm_str, _ = create_slider(
            "Strength (%)", 0, 100, 10, self.sec_usm.content_layout,
            on_release_callback=lambda: self.on_filter_slider_released(self.sec_usm, self.sl_usm_str),
            tooltip="Unsharp Mask blend strength (0=off, 100=full sharpening)"
        )
        self.sl_usm_radius, _ = create_slider(
            "Blur Radius (×10)", 5, 200, 10, self.sec_usm.content_layout,
            on_release_callback=lambda: self.on_filter_slider_released(self.sec_usm, self.sl_usm_str),
            tooltip="Gaussian sigma = value/10 in preview pixels (0.5–20), scaled for full-resolution export. The high-pass residual is input minus this blur."
        )
        self.sl_usm_amount, _ = create_slider(
            "Sharpening Amount (×10)", 5, 50, 20, self.sec_usm.content_layout,
            on_release_callback=lambda: self.on_filter_slider_released(self.sec_usm, self.sl_usm_str),
            tooltip="High-pass multiplier = value/10 (0.5–5). Strength blends the sharpened result with the input separately."
        )
        self.sec_usm.toggled_active.connect(lambda active: self.on_filter_toggled(active, self.sl_usm_str))
        sharpening_group.addWidget(self.sec_usm)

        self.sec_achf = CollapsibleSection("ACHF", has_checkbox=True, is_expanded=False, is_active=False)
        self.sl_achf_str, _ = create_slider(
            "Strength (%)", 0, 100, 10, self.sec_achf.content_layout,
            on_release_callback=lambda: self.on_filter_slider_released(self.sec_achf, self.sl_achf_str),
            tooltip="Adaptive Circular High-Pass Filter blend strength"
        )
        self.sl_achf_kernel, _ = create_slider(
            "Support Radius (×10)", 5, 200, 20, self.sec_achf.content_layout,
            on_release_callback=lambda: self.on_filter_slider_released(self.sec_achf, self.sl_achf_str),
            tooltip="Circular kernel radius = value/10 in preview pixels, scaled for full-resolution export. Larger supports increase processing cost."
        )
        self.sl_achf_boost, _ = create_slider(
            "Contrast Gain (×10)", 10, 50, 20, self.sec_achf.content_layout,
            on_release_callback=lambda: self.on_filter_slider_released(self.sec_achf, self.sl_achf_str),
            tooltip="Signed high-pass gain = value/10 (1–5). Background Retention controls the input component; Strength controls the final blend."
        )
        self.sl_achf_threshold, _ = create_slider(
            "Intensity Threshold (%)", 0, 100, 10, self.sec_achf.content_layout,
            on_release_callback=lambda: self.on_filter_slider_released(self.sec_achf, self.sl_achf_str),
            tooltip="Maximum neighbor difference as percent of current input intensity range; opposite pairs must both pass"
        )
        self.sl_achf_background, _ = create_slider(
            "Background Retention (%)", 0, 99, 10, self.sec_achf.content_layout,
            on_release_callback=lambda: self.on_filter_slider_released(self.sec_achf, self.sl_achf_str),
            tooltip="Input-image coefficient at full ACHF strength = value/100. The Photoshop ACHF detail layer removes this base component before normalization."
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
        """Build the presentation controls shared by screen and export."""
        stretch_group = create_filter_group("🌟 FINAL STRETCH (DISPLAY & EXPORT)", layout)

        self.sec_stretch = CollapsibleSection("FINAL STRETCH MODE", has_checkbox=False, is_expanded=True)
        
        mode_row = QHBoxLayout()
        mode_lbl = QLabel("Stretch Algorithm:")
        mode_lbl.setStyleSheet("color: #aaa; font-size: 11px;")
        self.combo_stretch_mode = QComboBox()
        self.combo_stretch_mode.addItems(["Asinh (Smooth)", "Logarithmic: ln(1 + Kx)", "GHS (Hyperbolic Precision)"])
        self.combo_stretch_mode.setToolTip("Choose Asinh, logarithmic or GHS presentation stretching after filtering. Applied to the monochrome preview and final export, and to the Photoshop base, not its neutral-grey detail layers.")
        self.combo_stretch_mode.currentIndexChanged.connect(self._on_stretch_mode_changed)
        mode_lbl.setToolTip(self.combo_stretch_mode.toolTip())
        mode_row.addWidget(mode_lbl)
        mode_row.addWidget(self.combo_stretch_mode)
        self.sec_stretch.content_layout.addLayout(mode_row)

        self.sl_stretch, self.lbl_stretch = create_slider(
            "Stretch Intensity", 1, 100, 10, self.sec_stretch.content_layout, connect_pipeline=False,
            on_release_callback=self.render_matrix_to_screen,
            tooltip="Asinh and GHS use the displayed intensity. Log uses K = 10^(value/10). This changes presentation stretching, not the numerical filter input."
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
        self.lbl_ghs_sp.setToolTip("GHS symmetry point in normalized processed intensity, from 0 to 0.5. Set it with the slider or shadow picker.")
        self.lbl_ghs_sp.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        self.lbl_ghs_sp.setStyleSheet("color: #e5a00d; font-size: 11px; font-weight: bold;")
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
        self.btn_pick_sp.setToolTip("Enable the picker, then click the preview to sample normalized processed intensity before display stretching. The symmetry point is limited to 0–0.5.")
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
            tooltip="GHS highlight-protection parameter b, shown directly from 0 to 10. Higher values compress intensity differences above the symmetry point."
        )

        self.sl_ghs_bp, _ = create_slider_float(
            "Black Point (BP Shadows)", 0, 100, 0, 1000.0, ghs_layout,
            on_release_callback=self.render_matrix_to_screen,
            tooltip="Black point in normalized intensity. Values below it are clipped for display; the effective black point is limited to below the GHS symmetry point."
        )

        self.sec_stretch.content_layout.addWidget(self.ghs_container)
        self.ghs_container.setVisible(False)
        stretch_group.addWidget(self.sec_stretch)

        self.sl_blend, _ = create_slider(
            "Reveal Opacity (%)", 0, 100, 100, stretch_group, connect_pipeline=False,
            on_release_callback=self.render_matrix_to_screen,
            tooltip="Mix the stretched processed and original images: 0 shows the original; 100 shows the processed result. Also scales the recommended Photoshop detail-layer opacities, which are capped at 35% before Reveal is applied."
        )

        layout.addSpacing(8)

        self.chk_export_layers = QCheckBox("Also export independent Photoshop layers")
        self.chk_export_layers.setChecked(True)
        self.chk_export_layers.setStyleSheet("QCheckBox { color: #dddddd; font-size: 11px; }")
        self.chk_export_layers.setToolTip("Export a Photoshop package with a stretched base, independent active nonzero filter layers, optional RGB Color layer, import script and recipe. Its composite differs from the sequential pipeline final.")
        layout.addWidget(self.chk_export_layers)
        self.chk_export_linear = QCheckBox("Also export linear images")
        self.chk_export_linear.setStyleSheet("QCheckBox { color: #dddddd; font-size: 11px; }")
        self.chk_export_linear.setToolTip("Save input RGB and luminance as float32 without filters or stretching. An already stretched image is not converted to linear.")
        layout.addWidget(self.chk_export_linear)
        self.combo_input_state = QComboBox()
        # Use a Qt list rather than the native macOS popup, whose light item
        # background can conflict with our inherited dark-theme text colours.
        self.combo_input_state.setStyleSheet("""
            QComboBox {
                combobox-popup: 0;
                color: #eeeeee;
                background-color: #333333;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 5px 8px;
            }
        """)
        input_view = QListView(self.combo_input_state)
        input_view.setItemDelegate(QStyledItemDelegate(input_view))
        input_view.setUniformItemSizes(True)
        input_view.setStyleSheet("""
            QListView {
                background-color: #282828;
                color: #eeeeee;
                border: 1px solid #606060;
                border-radius: 0;
                outline: 0;
                selection-background-color: #086eae;
                selection-color: #ffffff;
            }
            QListView::item {
                background-color: #282828;
                color: #eeeeee;
                padding: 7px 10px;
                border: none;
            }
            QListView::item:selected, QListView::item:hover {
                background-color: #086eae;
                color: #ffffff;
            }
        """)
        input_view.viewport().setStyleSheet("background-color: #282828; border-radius: 0;")
        self.combo_input_state.setView(input_view)
        self.combo_input_state.addItem("Input: linearity unspecified", "unknown")
        self.combo_input_state.addItem("Input: linear", "linear")
        self.combo_input_state.addItem("Input: already stretched / nonlinear", "nonlinear")
        self.combo_input_state.setToolTip("Declare input linearity for source-file labels and color-calibration availability. LINEAR requires a declared linear input; otherwise sources use INPUT. This does not undo or bypass stretching.")
        self.combo_input_state.setVisible(False)
        self.chk_calibrate_colour = FullRowCheckBox("Calibrate color")
        self.chk_calibrate_colour.setStyleSheet("QCheckBox { color: #dddddd; font-size: 11px; }")
        self.chk_calibrate_colour.setToolTip("Requires linear RGB. Assumes a neutral background and corona: subtracts P1 and balances P99 minus P1. This is not photometric or ICC calibration. Applies only when exporting color images; the screen preview stays monochrome. Preserves the original sources.")
        self.chk_calibrate_colour.setEnabled(False)
        self.chk_calibrate_colour.toggled.connect(self.on_colour_changed)
        self.combo_input_state.currentIndexChanged.connect(self.on_input_state_changed)
        layout.addWidget(self.chk_calibrate_colour)
        self.lbl_colour_hint = QLabel("Color calibration requires an RGB image.")
        self.lbl_colour_hint.setToolTip("Color calibration is available only for RGB input explicitly declared linear. It is calculated on export and does not change the monochrome preview.")
        self.lbl_colour_hint.setWordWrap(True)
        self.lbl_colour_hint.setStyleSheet("color: #aaaaaa; font-size: 10px;")
        layout.addWidget(self.lbl_colour_hint)
        self.chk_export_linear.toggled.connect(lambda _: self.combo_input_state.setVisible(self.chk_export_linear.isChecked() or self.full_source_rgb is not None))
        layout.addWidget(self.combo_input_state)
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
        self.btn_export.setToolTip("Save the full-resolution final TIFF with presentation stretch and Reveal blend, plus a matching JPEG preview. Color and optional calibration are applied only on export; checked options add separate source/layer packages.")
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
            self.status_label.setToolTip("Processing, pending changes and export status. Pipeline Ready means the latest requested preview has completed.")
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

    def on_input_state_changed(self, *_):
        allowed = self.full_source_rgb is not None and self.combo_input_state.currentData() == "linear"
        self.chk_calibrate_colour.setEnabled(allowed)
        self.lbl_colour_hint.setText(
            "Color calibration requires an RGB image." if self.full_source_rgb is None else
            "Color calibration is applied on export only." if allowed else
            "Select 'Input: linear' below to enable color calibration.")
        if not allowed:
            self.chk_calibrate_colour.setChecked(False)

    def on_colour_changed(self, *_):
        """Invalidate export colour data without computing or updating preview."""
        self._colour_cache = None

    def colour_data(self, original=False):
        """Prepare full-resolution colour lazily for export; no RGB preview."""
        if self.full_source_rgb is None:
            return None, None, None
        if original:
            return self.full_source_rgb, None, dict(method="none")
        if self._colour_cache is None:
            rgb = self.full_source_rgb
            report = dict(method="none")
            if self.chk_calibrate_colour.isChecked():
                rgb, report = neutralize_tse(rgb, self.source_rgb_white)
            self._colour_cache = (rgb, None, report)
        return self._colour_cache

    def apply_ghs(self, mat: np.ndarray, D: float, SP: float, b: float, BP: float) -> np.ndarray:
        """Compatibility wrapper for the shared presentation transform."""
        return apply_ghs(mat, D, SP, b, BP)

    def collect_display_parameters(self):
        mode = ("asinh", "log", "ghs")[self.combo_stretch_mode.currentIndex()]
        return dict(mode=mode, strength=float(self.sl_stretch.value()),
                    sp=self.sl_ghs_sp.value() / 2000., b=self.sl_ghs_b.value() / 10.,
                    bp=self.sl_ghs_bp.value() / 1000., blend=self.sl_blend.value() / 100.)

    def on_image_canvas_clicked(self, x: int, y: int):
        """Ordinary clicks only sample shadows when the SP picker is active."""
        if self.sp_picker_active and hasattr(self, "btn_pick_sp") and self.btn_pick_sp.isChecked():
            proc_mat = self.processed_image if self.processed_image is not None else self.raw_image
            if proc_mat is not None:
                h, w = proc_mat.shape[:2]
                clamped_x = int(np.clip(x, 0, w - 1))
                clamped_y = int(np.clip(y, 0, h - 1))
                sample_norm = float(np.clip(normalize_observed(proc_mat)[clamped_y, clamped_x], 0.0, 0.5))
                self.sl_ghs_sp.setValue(int(round((sample_norm / 0.5) * 1000)))
                self.lbl_ghs_sp.setText(f"{sample_norm:.3f}")
                self.btn_pick_sp.setChecked(False)
                self.sp_picker_active = False
                self.image_label.setCursor(Qt.CursorShape.ArrowCursor)
                self.status_label.setText(f"🎯 SP set to {sample_norm:.3f} (Sample: X:{clamped_x}, Y:{clamped_y})")
                self.status_label.setStyleSheet("color: #00ff00; font-weight: bold;")
                self.render_matrix_to_screen()
                return

    def on_circle_center_requested(self, x: int, y: int):
        """Only modified canvas clicks move the lunar center."""
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
            if r_full > 0:
                self.sl_fnrgf_rmax.setMaximum(max(
                    self.sl_fnrgf_rmax.minimum(),
                    int(np.ceil(10 * np.hypot(w_full, h_full) / (2 * r_full))),
                ))
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
        self.recalculation_timer.stop()
        self.has_pending_request = False
        self._pending_manual = False
        self.btn_auto_calc.setText("Auto Calculate" if checked else "Man Calc")
        self.btn_recalc.setVisible(not checked)
        self.status_label.setText("Status: Auto Calculate" if checked else "Status: Manual Calculate")
        if checked:
            self.dispatch_pipeline_request()

    def on_filter_toggled(self, is_active: bool, strength_slider=None):
        """Keep the configured strength, including an intentional zero."""
        self.dispatch_pipeline_request_if_auto()

    def on_filter_slider_released(self, section, strength_slider):
        # Releasing at zero must remove the previously rendered effect, too.
        if section.is_filter_active():
            self.dispatch_pipeline_request_if_auto()

    def dispatch_pipeline_request_if_auto(self):
        """Record edits immediately, dispatch only after the user pauses."""
        self._preview_revision += 1
        if self.auto_calculate and self.raw_image is not None:
            self.has_pending_request = True
            self.recalculation_timer.start()

    def dispatch_pipeline_request(self):
        """Run the latest complete recipe; snapshot errors never lock the worker."""
        self.recalculation_timer.stop()
        if self.raw_image is None or self.full_raw_image is None:
            return
        if self.is_processing:
            self.has_pending_request = True
            self._pending_manual = not self.auto_calculate
            return
        self.has_pending_request = False
        self._pending_manual = False
        try:
            params = self.collect_filter_parameters(self.raw_image.shape[:2])
            if not np.isfinite([params['sx'], params['sy'], params['sr']]).all() or params['sr'] <= 0:
                raise ValueError("Sun center must be finite and radius must be positive")
        except (ValueError, TypeError, OverflowError) as error:
            self.status_label.setText(f"Status: Invalid parameters — {error}")
            self.status_label.setStyleSheet("color: #ff3333; font-weight: bold;")
            return
        if self.btn_compare.isChecked():
            self.btn_compare.setChecked(False)
            self.show_original_mode = False
        self._running_revision = self._preview_revision
        self._running_image = self.raw_image
        self.is_processing = True
        self.status_label.setText("Status: Processing Filters...")
        self.status_label.setStyleSheet("color: #e5a00d; font-weight: bold;")
        self.request_processing_signal.emit(self.raw_image, params)

    def collect_filter_parameters(self, target_shape):
        """Snapshot UI once; prepare the same recipe for preview or export."""
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
            "fnrgf_seg": 2 ** self.sl_fnrgf_seg.value(),
            "fnrgf_cut": self.sl_fnrgf_cut.value(),
            "fnrgf_rad": self.sl_fnrgf_rad.value(),
            "fnrgf_rmax": self.sl_fnrgf_rmax.value(),
            "fnrgf_bin_px": self.sl_fnrgf_bin_px.value(),
            "fnrgf_width_func": "mad" if self.combo_fnrgf_width.currentIndex() == 1 else "std",
            "fnrgf_radial_binning": "log" if self.combo_fnrgf_binning.currentIndex() == 1 else "linear",
            "fnrgf_apply_mask": self.sl_fnrgf_mask.value(),
            "mgn_enabled": self.sec_mgn.is_filter_active(),
            "mgn_str": self.sl_mgn_str.value(),
            "mgn_gam": self.sl_mgn_gam.value(),
            "mgn_k": self.sl_mgn_k.value(),
            "mgn_h": self.sl_mgn_h.value(),
            "mgn_trunc": self.sl_mgn_trunc.value(),
            "rhef_mode": self.combo_rhef_mode.currentData(),
            "rhef_enabled": self.sec_rhef.is_filter_active(),
            "rhef_str": self.sl_rhef_str.value(),
            "rhef_rad": self.sl_rhef_rad.value(),
            "rhef_upsilon": self.sl_rhef_upsilon.value(),
            "rhef_bin_px": self.sl_rhef_bin.value()/10.0,
            "wow_enabled": self.sec_wow.is_filter_active(),
            "wow_str": self.sl_wow_str.value(),
            "wow_scales": self.sl_wow_scales.value(),
            "wow_denoise": [slider.value() for slider in self.sl_wow_denoise],
            "wow_bilateral": 1 if self.combo_wow_bilateral.currentIndex() else None,
            "usm_enabled": self.sec_usm.is_filter_active(),
            "usm_str": self.sl_usm_str.value(),
            "usm_radius": self.sl_usm_radius.value(),
            "usm_sigma": self.sl_usm_amount.value() / 10.0,
            "achf_enabled": self.sec_achf.is_filter_active(),
            "achf_str": self.sl_achf_str.value(),
            "achf_kernel": self.sl_achf_kernel.value(),
            "achf_boost": self.sl_achf_boost.value(),
            "achf_threshold": self.sl_achf_threshold.value(),
            "achf_background": self.sl_achf_background.value(),
            "sx": float(self.txt_x.text()),
            "sy": float(self.txt_y.text()),
            "sr": float(self.txt_r.text()),
        }
        params = prepare_parameters(params, self.full_raw_image.shape[:2],
                                    self.preview_image.shape[:2], target_shape)
        data = self.full_raw_image if tuple(target_shape) == self.full_raw_image.shape[:2] else self.preview_image
        params["valid_mask"] = np.isfinite(data)
        return params

    def _dispatch_pending_preview(self):
        # An edit restarted the debounce timer: don't execute early or lose it.
        if self.recalculation_timer.isActive():
            return
        if self.has_pending_request and (self.auto_calculate or self._pending_manual):
            self.dispatch_pipeline_request()

    def on_processing_failed(self, message: str):
        self.is_processing = False
        self._running_revision = None
        self._running_image = None
        self.status_label.setText(f"Status: Processing failed — {message}")
        self.status_label.setStyleSheet("color: #ff3333; font-weight: bold;")
        self._dispatch_pending_preview()

    def on_processing_finished(self, output_matrix: np.ndarray):
        """Never publish an obsolete image or recipe as the finished preview."""
        current = (self._running_revision is None or
                   (self._running_revision == self._preview_revision
                    and self._running_image is self.raw_image))
        self.is_processing = False
        self._running_revision = None
        self._running_image = None
        if current and not self.recalculation_timer.isActive():
            self.processed_image = output_matrix
            self.status_label.setText("Status: Pipeline Ready")
            self.status_label.setStyleSheet("color: #00ff00; font-weight: bold;")
            self.render_matrix_to_screen()
        else:
            self.status_label.setText("Status: Updated settings pending..." if
                                      (self.auto_calculate or self._pending_manual) else
                                      "Status: Settings changed — recalculate")
            self.status_label.setStyleSheet("color: #e5a00d; font-weight: bold;")
        self._dispatch_pending_preview()

    def apply_recommended_parameters_to_gui(self, r_full: float, w_full: int, h_full: int):
        """Auto-populate sliders based on image resolution."""
        if r_full <= 5:
            return

        solar_angular_radius_arcsec = 960.0
        pixel_scale_arcsec = solar_angular_radius_arcsec / float(r_full)

        rec_bilateral_px = max(0.5, r_full * 0.005)
        rec_usm_radius_px = max(1.0, r_full * 0.012)
        rec_achf_kernel_px = max(1.5, r_full * 0.025)

        rec_fnrgf_ord = int(np.clip(r_full * 0.015 + 4, 6, 24))
        # Half-diagonal reaches the corners for a disk at the frame center.
        # Round upwards to the slider's 0.1 R_sun step to include corner pixels.
        rmax_slider = int(np.ceil(10 * np.hypot(w_full, h_full) / (2 * r_full)))
        self.sl_fnrgf_rmax.setMaximum(max(self.sl_fnrgf_rmax.minimum(), rmax_slider))
        rec_fnrgf_rmax = self.sl_fnrgf_rmax.maximum() / 10.0
        rec_fnrgf_nbins = recommended_radial_bins(
            self.sl_fnrgf_rad.value() / 10.0 * r_full,
            rec_fnrgf_rmax * r_full,
            logarithmic=self.combo_fnrgf_binning.currentIndex() == 1,
            width_px=4,
        )
        rec_wow_scales = int(np.clip(np.log2(r_full / 8.0), 3, 8))

        print(f"\n{'='*80}")
        print(f"🔬 RECOMMENDED SCIENTIFIC FILTER PARAMETERS (Based on R_sun = {r_full:.1f} px @ 100%)")
        print(f"{'='*80}")
        print(f"📊 Astrometric Properties:")
        print(f"   • Sensor Plate Scale : {pixel_scale_arcsec:.3f} arcsec/pixel")
        print(f"   • Full Sensor Size   : {w_full} × {h_full} px")
        print(f"   • Coronal Coverage   : up to ~{rec_fnrgf_rmax:.2f} R_sun (half image diagonal)")
        print(f"\n⚙️ Applied Initial Slider Positions:")
        print(f"   [0] PRE-STRETCH       : Log Exp = 1.0 (K=10^1.0) | Range: 0.0 to 6.0")
        print(f"   [1] BILATERAL DENOISE : Blur Radius ~ {rec_bilateral_px * 10:.0f} (slider value = {rec_bilateral_px:.1f} px)")
        print(f"   [2] FNRGF ENGINE      : Order = {rec_fnrgf_ord} | Radial Bins = {rec_fnrgf_nbins} | R_max = {rec_fnrgf_rmax:.1f} R_sun")
        print(f"   [3] RHEF ENGINE       : App Radius = 10 (1.0 R_sun) | Upsilon = 35")
        print(f"   [4] MGN ENGINE        : Gamma = 32 | k = 70 | h = 70 | Trunc = 3")
        print(f"   [5] WOW ENGINE        : Wavelet Scales = {rec_wow_scales}")
        print(f"   [6] USM SHARPENING    : Blur Radius ~ {rec_usm_radius_px * 10:.0f} (slider value = {rec_usm_radius_px:.1f} px)")
        print(f"   [7] ACHF FILTER       : Base Kernel ~ {rec_achf_kernel_px * 10:.0f} (slider value = {rec_achf_kernel_px:.1f} px)")
        print(f"{'='*80}\n")

        self.sl_bilateral_d.setValue(int(round(rec_bilateral_px * 10.0)))
        self.sl_fnrgf_ord.setValue(rec_fnrgf_ord)
        self.sl_fnrgf_seg.setValue((2 * rec_fnrgf_ord).bit_length())
        self.sl_fnrgf_bin_px.setValue(4)
        self.sl_fnrgf_rmax.setValue(int(round(rec_fnrgf_rmax * 10.0)))
        self.sl_wow_scales.setValue(0)  # automatic, dimension-dependent scales
        self.sl_usm_radius.setValue(int(round(rec_usm_radius_px * 10.0)))
        self.sl_achf_kernel.setValue(int(round(rec_achf_kernel_px * 10.0)))

    def auto_detect_moon_action(self):
        """Auto-detect lunar disk parameters."""
        if self.raw_image is None or self.full_raw_image is None:
            return
        self.status_label.setText("Status: Detecting lunar disk...")
        self.status_label.setStyleSheet("color: #e5a00d; font-weight: bold;")
        QApplication.processEvents()

        cx_full, cy_full, r_full = self.detect_lunar_limb(self.full_raw_image)

        self.txt_x.setText(str(cx_full))
        self.txt_y.setText(str(cy_full))
        self.txt_r.setText(str(r_full))
        self.trigger_circle_redraw()

        self.status_label.setText(f"Status: Moon detected (Full-res X:{cx_full}, Y:{cy_full}, R:{r_full})")
        self.status_label.setStyleSheet("color: #00ff00; font-weight: bold;")

    def detect_lunar_limb(self, raw_img: np.ndarray) -> Tuple[int, int, int]:
        """Estimate a circular data boundary or a contrast-normalized lunar limb.

        The robust stretch below is a detection-only working image: it never
        modifies the linear source, filter input or display stretch settings.
        """
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
        # A calibrated stack can have an unobserved lunar disc instead of a
        # black disc. Fit only a closed, nearly circular missing-data boundary;
        # edge gaps and isolated defective pixels are not lunar candidates.
        missing = (~np.isfinite(img_gray)).astype(np.uint8)
        if missing.any():
            contours, _ = cv2.findContours(missing, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
            for contour in sorted(contours, key=cv2.contourArea, reverse=True):
                if cv2.contourArea(contour) < np.pi * (min(h, w) * .02)**2:
                    break
                points = contour[:, 0].astype(float)
                if (points[:, 0].min() <= 0 or points[:, 0].max() >= w-1
                        or points[:, 1].min() <= 0 or points[:, 1].max() >= h-1):
                    continue
                origin = points.mean(axis=0)
                offsets = points-origin
                matrix = np.column_stack([2*offsets, np.ones(len(points))])
                solution = np.linalg.lstsq(matrix, np.sum(offsets**2, axis=1), rcond=None)[0]
                center = origin+solution[:2]
                distances = np.linalg.norm(points-center, axis=1)
                radius = float(np.mean(distances))
                if radius > 0 and np.sqrt(np.mean((distances-radius)**2))/radius < .03:
                    print("Lunar geometry estimated from circular missing-data boundary; check radius against the original limb")
                    return int(round(center[0])), int(round(center[1])), int(round(radius))
        clean_img = np.nan_to_num(img_gray, nan=0.0, posinf=0.0, neginf=0.0)
        # A saturated star or prominence can dominate min/max scaling and leave
        # the actual limb below Hough's edge threshold. Ignore extreme tails and
        # compress the detection image before quantizing it to eight bits.
        observed = clean_img[np.isfinite(img_gray)]
        if not observed.size:
            return w // 2, h // 2, min(w, h) // 4
        lower, upper = np.percentile(observed, [1, 99.8])
        if upper <= lower:
            return w // 2, h // 2, min(w, h) // 4
        contrast = np.clip((clean_img.astype(np.float64)-lower)/(upper-lower), 0, 1)
        # Retain floating-point samples for full-resolution radial refinement.
        norm = (255*np.arcsinh(10*contrast)/np.arcsinh(10)).astype(np.float32)

        scale = min(1.0, 800.0 / max(h, w))
        sw, sh = max(1, int(w * scale)), max(1, int(h * scale))
        small = cv2.resize(norm, (sw, sh), interpolation=cv2.INTER_AREA).astype(np.uint8)
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
                    best_candidate = ((cx + 0.5) * w / sw - 0.5,
                                      (cy + 0.5) * h / sh - 0.5,
                                      float(r) / scale)

        if best_candidate is None:
            return w // 2, h // 2, min(w, h) // 4

        init_cx, init_cy, init_r = best_candidate
        r_search = int(init_r * 0.15)
        radii = np.arange(max(1, init_r - r_search), min(min(w, h) / 2, init_r + r_search), 0.5)
        angles = np.linspace(0, 2 * np.pi, 360, endpoint=False)

        edge_pts = []
        for ang in angles:
            xs = (init_cx + radii * np.cos(ang)).astype(np.float32)
            ys = (init_cy + radii * np.sin(ang)).astype(np.float32)
            if not len(radii) or xs.min() < 0 or xs.max() > w - 1 or ys.min() < 0 or ys.max() > h - 1:
                continue
            profile = cv2.remap(norm, xs[None, :], ys[None, :], cv2.INTER_LINEAR)[0]
            grad = np.diff(profile)
            if len(grad) > 0 and grad.max() > 2.5:
                index = np.argmax(grad)
                best_r = (radii[index] + radii[index + 1]) / 2
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

        return int(round(init_cx)), int(round(init_cy)), int(round(init_r))

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
                if img is not None and img.ndim == 3 and img.shape[-1] in (3, 4):
                    img = cv2.cvtColor(img, cv2.COLOR_BGRA2RGBA if img.shape[-1] == 4 else cv2.COLOR_BGR2RGB)

            if img is None:
                from PIL import Image
                with Image.open(file_path) as pil_img:
                    img = np.array(pil_img)

            if img is None:
                raise ValueError("Could not decode image with any available decoder.")

            white = float(np.iinfo(img.dtype).max) if np.issubdtype(img.dtype, np.integer) else 1.
            mono, source_rgb = split_source_channels(img)
            self.full_raw_image = np.ascontiguousarray(mono, dtype=np.float32)
            self.full_source_rgb = source_rgb
            self.source_rgb_white = white
            self._colour_cache = None
            self.chk_calibrate_colour.blockSignals(True)
            self.chk_calibrate_colour.setChecked(False)
            self.chk_calibrate_colour.blockSignals(False)
            self.combo_input_state.setCurrentIndex(0)
            self.on_input_state_changed()
            self.combo_input_state.setVisible(source_rgb is not None or self.chk_export_linear.isChecked())
            self.source_path = file_path
            h_full, w_full = self.full_raw_image.shape[:2]

            max_dim = 1500
            if max(h_full, w_full) > max_dim:
                self.preview_scale = max_dim / float(max(h_full, w_full))
                new_w, new_h = int(w_full * self.preview_scale), int(h_full * self.preview_scale)
                self.preview_image = resize_observed(self.full_raw_image, (new_w, new_h))
                self.raw_image = self.preview_image.copy()
            else:
                self.preview_scale = 1.0
                self.preview_image = self.full_raw_image.copy()
                self.raw_image = self.full_raw_image.copy()

            self.processed_image = self.raw_image.copy()
            scale_ratio = h_full / float(self.preview_image.shape[0])
            self.lbl_scale_info.setText(f"Scale: {scale_ratio:.1f}x (100% = {w_full}×{h_full}px)")

            cx_full, cy_full, r_full = self.detect_lunar_limb(self.full_raw_image)

            self.txt_x.setText(str(cx_full))
            self.txt_y.setText(str(cy_full))
            self.txt_r.setText(str(r_full))

            self.apply_recommended_parameters_to_gui(r_full, w_full, h_full)

            self.render_matrix_to_screen()
            self.dispatch_pipeline_request_if_auto()
            missing = np.count_nonzero(~np.isfinite(self.full_raw_image))
            self.status_label.setText(f"Status: Loaded {os.path.basename(file_path)} (X:{cx_full}, Y:{cy_full}, R:{r_full}); {missing} missing pixels")
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
            parameters = self.collect_filter_parameters(self.full_raw_image.shape[:2])
            display = self.collect_display_parameters()
            export_layers = self.chk_export_layers.isChecked()
            export_linear = self.chk_export_linear.isChecked()
            input_state = self.combo_input_state.currentData()
            source_rgb = self.full_source_rgb
            colour_rgb, _, colour_report = self.colour_data()
            original_path = self.source_path or file_path
            source = self.full_raw_image.copy()
            QApplication.processEvents()
            img = execute_pipeline(worker, source, parameters)

            img_norm = render_presentation(img, source, display)
            if colour_rgb is not None:
                img_norm = set_luminosity(colour_layer(colour_rgb, source, display), img_norm)

            img_16bit = np.clip(img_norm * 65535.0, 0, 65535).astype(np.uint16)

            t0 = time.time()
            valid = np.isfinite(source)
            if not valid.all():
                if img_16bit.ndim == 3:
                    img_16bit = np.concatenate([img_16bit, (valid.astype(np.uint16)*65535)[..., None]], axis=2)
                else:
                    img_16bit = np.stack([img_16bit, valid.astype(np.uint16)*65535], axis=-1)
            tifffile.imwrite(file_path, img_16bit, photometric="rgb" if colour_rgb is not None else "minisblack",
                             extrasamples=['unassalpha'] if not valid.all() else None,
                             compression="zlib", maxworkers=CPU_CORES,
                             metadata={"scale_factor": scale_factor, "source": original_path,
                                       "parameters": recipe_parameters(parameters), "display": display,
                                       "colour_calibration": colour_report,
                                       "role": "Sequential pipeline presentation; not a linear master"})
            print(f"[EXPORT: DISK WRITE] Done in {time.time() - t0:.3f}s")
            
            # Presentation is already stretched: JPEG uses the same display values.
            t0 = time.time()
            jpeg_path = file_path.rsplit('.', 1)[0] + "_preview.jpg"
            
            img_gamma = img_norm
            img_gamma = np.clip(img_gamma * 255.0, 0, 255).astype(np.uint8)
            
            # Save as JPEG with high quality
            if not cv2.imwrite(jpeg_path, cv2.cvtColor(img_gamma, cv2.COLOR_RGB2BGR) if img_gamma.ndim == 3 else img_gamma, [cv2.IMWRITE_JPEG_QUALITY, 95]):
                raise OSError("Could not write JPEG preview")
            print(f"[EXPORT: JPEG PREVIEW] Done in {time.time() - t0:.3f}s")
            
            layers_path = None
            if export_layers:
                candidate = Path(file_path).with_suffix("").with_name(Path(file_path).stem + "_PS_layers")
                suffix = 2
                while candidate.exists():
                    candidate = Path(file_path).with_suffix("").with_name(Path(file_path).stem + f"_PS_layers_{suffix}")
                    suffix += 1
                layers_path = export_layer_package(worker, source, parameters, display,
                                                   original_path, candidate, rgb=colour_rgb, colour_report=colour_report)

            linear_path = None
            if export_linear:
                candidate = Path(file_path).with_suffix("").with_name(Path(file_path).stem + "_sources")
                suffix = 2
                while candidate.exists():
                    candidate = Path(file_path).with_suffix("").with_name(Path(file_path).stem + f"_sources_{suffix}")
                    suffix += 1
                linear_path = export_linear_sources(source, source_rgb, original_path, candidate, input_state)

            print(f"[EXPORT] Finished successfully in {time.time() - export_start:.3f}s\n{'='*80}\n")

            self.status_label.setText(f"Status: Exported {os.path.basename(file_path)} + preview"
                                      + (f" + {layers_path.name}" if layers_path else "")
                                      + (f" + {linear_path.name}" if linear_path else ""))
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

        display = self.collect_display_parameters()
        if self.show_original_mode:
            display = dict(display, blend=0.)
        final_norm = render_presentation(proc_mat, orig_mat, display)

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
        self.recalculation_timer.stop()
        self.in_window_tooltips.detach()
        if self.persistent_thread is not None and self.persistent_thread.isRunning():
            self.persistent_thread.quit()
            self.persistent_thread.wait()
        event.accept()
