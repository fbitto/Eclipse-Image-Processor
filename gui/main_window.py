"""
Main application window for Eclipse Processor.

Integrates all filter controls, image preview, and worker pipeline.
"""

import sys
import os
import numpy as np
from typing import Optional, Tuple
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtGui import QPixmap, QImage, QAction, QIcon
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QScrollArea,
    QPushButton,
    QLabel,
    QFileDialog,
    QMessageBox,
    QProgressBar,
    QStatusBar,
    QMenuBar,
    QMenu,
    QSplitter,
    QComboBox,
)

from core.image_loader import load_image, create_preview_image
from core.moon_detection import detect_lunar_limb
from core.image_export import export_image_as_tiff
from worker.filter_worker import FilterWorker
from gui.preview import ClickableLabel
from gui.sections import CollapsibleSection
from gui.widgets import create_slider, create_stepper_input, create_filter_group
from utils.styling import DARK_STYLESHEET
from config import FILTER_DEFAULTS, WINDOW_WIDTH, WINDOW_HEIGHT


class MainWindow(QMainWindow):
    """Main application window with filter controls and preview."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Eclipse Processor v1.4.0")
        self.setGeometry(100, 100, WINDOW_WIDTH, WINDOW_HEIGHT)
        
        # Image data
        self.original_image: Optional[np.ndarray] = None
        self.current_image: Optional[np.ndarray] = None
        self.preview_image: Optional[np.ndarray] = None
        self.preview_scale: float = 1.0
        self.sun_x: float = 0
        self.sun_y: float = 0
        self.sun_r: float = 100
        
        # Worker thread
        self.worker_thread: Optional[QThread] = None
        self.worker: Optional[FilterWorker] = None
        self.is_processing = False
        
        # Setup UI
        self._setup_ui()
        self._setup_stylesheet()
        self._create_menu_bar()
        self._connect_signals()
        
        self.statusBar().showMessage("Ready. Load an image to begin.")

    def _setup_ui(self):
        """Create main UI layout."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create splitter for resizable layout
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # LEFT: Preview panel
        left_panel = self._create_preview_panel()
        splitter.addWidget(left_panel)
        
        # RIGHT: Controls panel
        right_panel = self._create_controls_panel()
        splitter.addWidget(right_panel)
        
        # Set initial sizes (60% preview, 40% controls)
        splitter.setStretchFactor(0, 60)
        splitter.setStretchFactor(1, 40)
        
        main_layout.addWidget(splitter)

    def _create_preview_panel(self) -> QWidget:
        """Create image preview panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # Image viewer with clickable label
        self.preview_label = ClickableLabel()
        self.preview_label.setMinimumSize(400, 400)
        self.preview_label.image_clicked.connect(self._on_preview_clicked)
        layout.addWidget(self.preview_label)
        
        # Info label
        self.info_label = QLabel("No image loaded")
        self.info_label.setStyleSheet("color: #aaa; font-size: 10px;")
        layout.addWidget(self.info_label)
        
        # Load/Save buttons
        button_layout = QHBoxLayout()
        
        btn_load = QPushButton("Load Image")
        btn_load.clicked.connect(self._on_load_image)
        btn_load.setStyleSheet("""
            QPushButton {
                background-color: #1a5f7a;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #2a7f9a;
            }
            QPushButton:pressed {
                background-color: #0a4f6a;
            }
        """)
        button_layout.addWidget(btn_load)
        
        btn_save = QPushButton("Export Result")
        btn_save.clicked.connect(self._on_export_image)
        btn_save.setStyleSheet("""
            QPushButton {
                background-color: #5f7a1a;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #7f9a2a;
            }
            QPushButton:pressed {
                background-color: #4f6a0a;
            }
        """)
        button_layout.addWidget(btn_save)
        
        layout.addLayout(button_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #333;
                border-radius: 4px;
                background-color: #1e1e1e;
                text-align: center;
                color: #aaa;
            }
            QProgressBar::chunk {
                background-color: #e5a00d;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        return panel

    def _create_controls_panel(self) -> QWidget:
        """Create filter controls panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(0)
        
        # Scroll area for controls
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
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
            }
            QScrollBar::handle:vertical:hover {
                background-color: #555;
            }
        """)
        
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(2)
        
        # Moon Detection Section
        moon_section = CollapsibleSection("Moon Detection", has_checkbox=False, is_expanded=True)
        moon_layout = QVBoxLayout()
        
        btn_detect = QPushButton("Auto-Detect Lunar Disk")
        btn_detect.clicked.connect(self._on_detect_moon)
        btn_detect.setStyleSheet("""
            QPushButton {
                background-color: #2a3a4a;
                color: #ddd;
                border: 1px solid #3a4a5a;
                border-radius: 3px;
                padding: 6px;
                font-size: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3a4a5a;
            }
        """)
        moon_layout.addWidget(btn_detect)
        
        self.txt_sx = create_stepper_input("Center X", "512", moon_layout)
        self.txt_sy = create_stepper_input("Center Y", "512", moon_layout)
        self.txt_sr = create_stepper_input("Radius", "300", moon_layout)
        
        moon_section.content_layout.addLayout(moon_layout)
        scroll_layout.addWidget(moon_section)
        
        # PRE-STRETCH Section
        self.pre_stretch_section = CollapsibleSection("Pre-Stretch", has_checkbox=True, is_active=False)
        pre_layout = create_filter_group("Asinh", self.pre_stretch_section.content_layout)
        self.sld_pre_val, _ = create_slider("Factor", 1, 50, 10, pre_layout)
        pre_container = QWidget()
        pre_container.setLayout(pre_layout)
        self.pre_stretch_section.content_layout.addWidget(pre_container)
        scroll_layout.addWidget(self.pre_stretch_section)
        
        # NOISE GATE Section
        self.noise_gate_section = CollapsibleSection("Noise Gate", has_checkbox=True, is_active=False)
        ng_layout = create_filter_group("Radial Noise Gate", self.noise_gate_section.content_layout)
        self.sld_ng_str, _ = create_slider("Strength", 0, 100, 0, ng_layout)
        self.sld_ng_thr, _ = create_slider("Threshold", 0, 100, 50, ng_layout)
        self.sld_ng_rad, _ = create_slider("Radius (×10)", 1, 30, 10, ng_layout)
        ng_container = QWidget()
        ng_container.setLayout(ng_layout)
        self.noise_gate_section.content_layout.addWidget(ng_container)
        scroll_layout.addWidget(self.noise_gate_section)
        
        # BILATERAL Section
        self.bilateral_section = CollapsibleSection("Bilateral Denoise", has_checkbox=True, is_active=False)
        bil_layout = create_filter_group("Edge-Preserving", self.bilateral_section.content_layout)
        self.sld_bil_str, _ = create_slider("Strength", 0, 100, 0, bil_layout)
        self.sld_bil_d, _ = create_slider("Diameter", 5, 30, 15, bil_layout)
        self.sld_bil_ss, _ = create_slider("Space Sigma", 10, 100, 30, bil_layout)
        self.sld_bil_sr, _ = create_slider("Range Sigma (×10)", 1, 100, 10, bil_layout)
        bil_container = QWidget()
        bil_container.setLayout(bil_layout)
        self.bilateral_section.content_layout.addWidget(bil_container)
        scroll_layout.addWidget(self.bilateral_section)
        
        # FNRGF Section ⚠️ CORRECTED
        self.fnrgf_section = CollapsibleSection("FNRGF (Radial Gradient)", has_checkbox=True, is_active=True)
        fnrgf_layout = create_filter_group("Fourier Radial Normalization", self.fnrgf_section.content_layout)
        self.sld_fnrgf_str, _ = create_slider("Strength", 0, 100, 70, fnrgf_layout)
        self.sld_fnrgf_ord, _ = create_slider("Order", 1, 24, 6, fnrgf_layout)
        self.sld_fnrgf_seg, _ = create_slider("Segments", 10, 360, 50, fnrgf_layout)
        self.sld_fnrgf_cut, _ = create_slider("Cutoff", 0, 30, 0, fnrgf_layout)
        self.sld_fnrgf_rad, _ = create_slider("Radius (×10)", 5, 25, 10, fnrgf_layout)
        self.sld_fnrgf_rmax, _ = create_slider("R_max (×10)", 15, 60, 30, fnrgf_layout)
        self.sld_fnrgf_nbins, _ = create_slider("Bins", 20, 300, 80, fnrgf_layout)
        self.sld_fnrgf_amask, _ = create_slider("Apply Mask", 0, 100, 0, fnrgf_layout)
        
        # Width function dropdown
        width_layout = QHBoxLayout()
        width_lbl = QLabel("Width Function")
        width_lbl.setStyleSheet("background: transparent; color: #b8b8b8; font-size: 11px;")
        self.cmb_fnrgf_wf = QComboBox()
        self.cmb_fnrgf_wf.addItems(["std", "mad"])
        self.cmb_fnrgf_wf.setStyleSheet("""
            QComboBox {
                background-color: #1a1a1a;
                color: #ddd;
                border: 1px solid #333;
                border-radius: 3px;
                padding: 3px 5px;
            }
        """)
        width_layout.addWidget(width_lbl)
        width_layout.addStretch()
        width_layout.addWidget(self.cmb_fnrgf_wf)
        fnrgf_layout.addLayout(width_layout)
        
        # Radial binning dropdown
        radbin_layout = QHBoxLayout()
        radbin_lbl = QLabel("Radial Binning")
        radbin_lbl.setStyleSheet("background: transparent; color: #b8b8b8; font-size: 11px;")
        self.cmb_fnrgf_rb = QComboBox()
        self.cmb_fnrgf_rb.addItems(["linear", "log"])
        self.cmb_fnrgf_rb.setStyleSheet("""
            QComboBox {
                background-color: #1a1a1a;
                color: #ddd;
                border: 1px solid #333;
                border-radius: 3px;
                padding: 3px 5px;
            }
        """)
        radbin_layout.addWidget(radbin_lbl)
        radbin_layout.addStretch()
        radbin_layout.addWidget(self.cmb_fnrgf_rb)
        fnrgf_layout.addLayout(radbin_layout)
        
        fnrgf_container = QWidget()
        fnrgf_container.setLayout(fnrgf_layout)
        self.fnrgf_section.content_layout.addWidget(fnrgf_container)
        scroll_layout.addWidget(self.fnrgf_section)
        
        # RHEF Section
        self.rhef_section = CollapsibleSection("RHEF", has_checkbox=True, is_active=False)
        rhef_layout = create_filter_group("Radial Histogram Equalization", self.rhef_section.content_layout)
        self.sld_rhef_str, _ = create_slider("Strength", 0, 100, 0, rhef_layout)
        self.sld_rhef_rad, _ = create_slider("Radius (×10)", 5, 25, 10, rhef_layout)
        self.sld_rhef_ups, _ = create_slider("Upsilon (×10)", 5, 20, 10, rhef_layout)
        rhef_container = QWidget()
        rhef_container.setLayout(rhef_layout)
        self.rhef_section.content_layout.addWidget(rhef_container)
        scroll_layout.addWidget(self.rhef_section)
        
        # MGN Section
        self.mgn_section = CollapsibleSection("MGN (Multi-Scale)", has_checkbox=True, is_active=False)
        mgn_layout = create_filter_group("Gaussian Normalization", self.mgn_section.content_layout)
        self.sld_mgn_str, _ = create_slider("Strength", 0, 100, 0, mgn_layout)
        self.sld_mgn_gam, _ = create_slider("Gamma (×0.1)", 10, 100, 32, mgn_layout)
        self.sld_mgn_k, _ = create_slider("K (×0.01)", 10, 100, 70, mgn_layout)
        self.sld_mgn_h, _ = create_slider("H (×0.01)", 10, 100, 70, mgn_layout)
        self.sld_mgn_trunc, _ = create_slider("Truncation", 2, 5, 3, mgn_layout)
        mgn_container = QWidget()
        mgn_container.setLayout(mgn_layout)
        self.mgn_section.content_layout.addWidget(mgn_container)
        scroll_layout.addWidget(self.mgn_section)
        
        # WOW Section
        self.wow_section = CollapsibleSection("WOW (Wavelets)", has_checkbox=True, is_active=False)
        wow_layout = create_filter_group("Wavelet Whitening", self.wow_section.content_layout)
        self.sld_wow_str, _ = create_slider("Strength", 0, 100, 0, wow_layout)
        self.sld_wow_scales, _ = create_slider("Scales", 2, 8, 6, wow_layout)
        self.sld_wow_gam, _ = create_slider("Gamma (×0.1)", 5, 100, 32, wow_layout)
        self.sld_wow_h, _ = create_slider("H (×0.01)", 10, 100, 20, wow_layout)
        wow_container = QWidget()
        wow_container.setLayout(wow_layout)
        self.wow_section.content_layout.addWidget(wow_container)
        scroll_layout.addWidget(self.wow_section)
        
        # USM Section
        self.usm_section = CollapsibleSection("USM (Sharpening)", has_checkbox=True, is_active=False)
        usm_layout = create_filter_group("Unsharp Mask", self.usm_section.content_layout)
        self.sld_usm_str, _ = create_slider("Strength", 0, 100, 0, usm_layout)
        self.sld_usm_rad, _ = create_slider("Radius", 1, 30, 10, usm_layout)
        self.sld_usm_sig, _ = create_slider("Sigma (×0.1)", 5, 50, 20, usm_layout)
        usm_container = QWidget()
        usm_container.setLayout(usm_layout)
        self.usm_section.content_layout.addWidget(usm_container)
        scroll_layout.addWidget(self.usm_section)
        
        # ACHF Section
        self.achf_section = CollapsibleSection("ACHF (High-Pass)", has_checkbox=True, is_active=False)
        achf_layout = create_filter_group("Adaptive Circular", self.achf_section.content_layout)
        self.sld_achf_str, _ = create_slider("Strength", 0, 100, 0, achf_layout)
        self.sld_achf_kernel, _ = create_slider("Kernel", 5, 100, 20, achf_layout)
        self.sld_achf_boost, _ = create_slider("Boost", 5, 50, 20, achf_layout)
        achf_container = QWidget()
        achf_container.setLayout(achf_layout)
        self.achf_section.content_layout.addWidget(achf_container)
        scroll_layout.addWidget(self.achf_section)
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)
        
        # Process button
        btn_process = QPushButton("PROCESS PIPELINE")
        btn_process.clicked.connect(self._on_process)
        btn_process.setStyleSheet("""
            QPushButton {
                background-color: #7a1a1a;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 12px;
                font-weight: bold;
                font-size: 12px;
                letter-spacing: 1px;
            }
            QPushButton:hover {
                background-color: #9a2a2a;
            }
            QPushButton:pressed {
                background-color: #6a0a0a;
            }
            QPushButton:disabled {
                background-color: #3a3a3a;
                color: #666;
            }
        """)
        self.btn_process = btn_process
        layout.addWidget(btn_process)
        
        return panel

    def _setup_stylesheet(self):
        """Apply dark theme stylesheet."""
        self.setStyleSheet(DARK_STYLESHEET)

    def _create_menu_bar(self):
        """Create application menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        action_load = file_menu.addAction("Load Image...")
        action_load.triggered.connect(self._on_load_image)
        
        action_export = file_menu.addAction("Export Result...")
        action_export.triggered.connect(self._on_export_image)
        
        file_menu.addSeparator()
        
        action_exit = file_menu.addAction("Exit")
        action_exit.triggered.connect(self.close)
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        
        action_about = help_menu.addAction("About")
        action_about.triggered.connect(self._on_about)

    def _connect_signals(self):
        """Connect internal signals."""
        pass

    @Slot()
    def _on_load_image(self):
        """Load image from file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Eclipse Image",
            "",
            "Image Files (*.tif *.tiff *.fits *.xisf *.png *.jpg);;All Files (*)"
        )
        
        if not file_path:
            return
        
        self.statusBar().showMessage("Loading image...")
        
        # Load full image
        img = load_image(file_path)
        if img is None:
            QMessageBox.critical(self, "Error", f"Failed to load image: {file_path}")
            self.statusBar().showMessage("Ready.")
            return
        
        self.original_image = img
        self.current_image = img.copy()
        
        # Create preview
        preview, scale = create_preview_image(img, max_dimension=800)
        self.preview_image = preview
        self.preview_scale = scale
        
        # Auto-detect moon
        self._auto_detect_moon()
        
        # Update display
        self._update_preview()
        self.statusBar().showMessage(f"Loaded: {Path(file_path).name} ({img.shape[0]}×{img.shape[1]})")

    @Slot()
    def _on_export_image(self):
        """Export processed image."""
        if self.current_image is None:
            QMessageBox.warning(self, "Warning", "No image to export. Load an image first.")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Eclipse Image",
            "output.tif",
            "TIFF Files (*.tif *.tiff);;All Files (*)"
        )
        
        if not file_path:
            return
        
        self.statusBar().showMessage("Exporting...")
        
        if export_image_as_tiff(self.current_image, file_path):
            QMessageBox.information(self, "Success", f"Image exported to:\n{file_path}")
            self.statusBar().showMessage(f"Exported: {Path(file_path).name}")
        else:
            QMessageBox.critical(self, "Error", "Failed to export image.")
            self.statusBar().showMessage("Export failed.")

    @Slot()
    def _on_detect_moon(self):
        """Auto-detect lunar disk."""
        if self.preview_image is None:
            QMessageBox.warning(self, "Warning", "Load an image first.")
            return
        
        self.statusBar().showMessage("Detecting lunar disk...")
        
        try:
            cx, cy, r = detect_lunar_limb(self.preview_image)
            
            # Scale back to original coordinates
            cx_orig = int(cx / self.preview_scale)
            cy_orig = int(cy / self.preview_scale)
            r_orig = int(r / self.preview_scale)
            
            # Update controls
            self.sun_x = cx_orig
            self.sun_y = cy_orig
            self.sun_r = r_orig
            
            self.txt_sx.setText(str(int(cx_orig)))
            self.txt_sy.setText(str(int(cy_orig)))
            self.txt_sr.setText(str(int(r_orig)))
            
            self._update_preview()
            self.statusBar().showMessage(f"Detected: Center=({cx_orig}, {cy_orig}), Radius={r_orig}")
        except Exception as e:
            QMessageBox.warning(self, "Detection Failed", f"Could not detect lunar disk:\n{str(e)}")
            self.statusBar().showMessage("Detection failed.")

    def _auto_detect_moon(self):
        """Auto-detect moon on image load."""
        if self.preview_image is None:
            return
        
        try:
            cx, cy, r = detect_lunar_limb(self.preview_image)
            cx_orig = int(cx / self.preview_scale)
            cy_orig = int(cy / self.preview_scale)
            r_orig = int(r / self.preview_scale)
            
            self.sun_x = cx_orig
            self.sun_y = cy_orig
            self.sun_r = r_orig
            
            self.txt_sx.setText(str(int(cx_orig)))
            self.txt_sy.setText(str(int(cy_orig)))
            self.txt_sr.setText(str(int(r_orig)))
        except:
            pass

    @Slot(int, int)
    def _on_preview_clicked(self, x: int, y: int):
        """Handle preview click to set center."""
        self.sun_x = x
        self.sun_y = y
        self.txt_sx.setText(str(int(x)))
        self.txt_sy.setText(str(int(y)))
        self._update_preview()

    def _update_preview(self):
        """Update preview display."""
        if self.preview_image is None:
            return
        
        # Normalize for display
        img_min = np.min(self.preview_image)
        img_max = np.max(self.preview_image)
        img_norm = (self.preview_image - img_min) / (img_max - img_min + 1e-5)
        img_display = (img_norm * 255).astype(np.uint8)
        
        # Convert to QPixmap
        h, w = img_display.shape
        bytes_per_line = w
        q_img = QImage(img_display.data, w, h, bytes_per_line, QImage.Format.Format_Grayscale8)
        pixmap = QPixmap.fromImage(q_img)
        
        self.preview_label.setPixmap(pixmap.scaledToWidth(600, Qt.TransformationMode.SmoothTransformation))
        
        # Circle parameters in preview image coordinates (not scaled)
        self.preview_label.set_circle_parameters(
            self.sun_x * self.preview_scale,
            self.sun_y * self.preview_scale,
            self.sun_r * self.preview_scale,
            self.preview_image.shape[1],  # preview width
            self.preview_image.shape[0]   # preview height
        )
        
        # Update info
        self.info_label.setText(
            f"Image: {self.preview_image.shape[1]}×{self.preview_image.shape[0]} | "
            f"Moon: ({int(self.sun_x)}, {int(self.sun_y)}) R={int(self.sun_r)}"
        )

    @Slot()
    def _on_process(self):
        """Start filter pipeline processing."""
        if self.original_image is None:
            QMessageBox.warning(self, "Warning", "Load an image first.")
            return
        
        # Update sun position from text inputs
        try:
            self.sun_x = float(self.txt_sx.text())
            self.sun_y = float(self.txt_sy.text())
            self.sun_r = float(self.txt_sr.text())
        except ValueError:
            QMessageBox.warning(self, "Error", "Invalid moon coordinates. Please check Center X/Y and Radius.")
            return
        
        # Gather parameters from UI controls
        params = {
            # Pre-Stretch
            "pre_stretch_enabled": self.pre_stretch_section.is_active(),
            "pre_stretch_factor": self.sld_pre_val.value(),
            
            # Noise Gate
            "noise_gate_enabled": self.noise_gate_section.is_active(),
            "noise_gate_strength": self.sld_ng_str.value(),
            "noise_gate_threshold": self.sld_ng_thr.value(),
            "noise_gate_radius": self.sld_ng_rad.value(),
            
            # Bilateral
            "bilateral_enabled": self.bilateral_section.is_active(),
            "bilateral_strength": self.sld_bil_str.value(),
            "bilateral_d": self.sld_bil_d.value(),
            "bilateral_sigma_spatial": self.sld_bil_ss.value(),
            "bilateral_sigma_range": self.sld_bil_sr.value() / 10.0,
            
            # FNRGF
            "fnrgf_enabled": self.fnrgf_section.is_active(),
            "fnrgf_strength": self.sld_fnrgf_str.value(),
            "fnrgf_order": self.sld_fnrgf_ord.value(),
            "fnrgf_segments": self.sld_fnrgf_seg.value(),
            "fnrgf_cutoff": self.sld_fnrgf_cut.value(),
            "fnrgf_radius": self.sld_fnrgf_rad.value(),
            "fnrgf_rmax": self.sld_fnrgf_rmax.value(),
            "fnrgf_nbins": self.sld_fnrgf_nbins.value(),
            "fnrgf_apply_mask": self.sld_fnrgf_amask.value(),
            "fnrgf_width_function": self.cmb_fnrgf_wf.currentText(),
            "fnrgf_radial_binning": self.cmb_fnrgf_rb.currentText(),
            "fnrgf_sun_x": self.sun_x,
            "fnrgf_sun_y": self.sun_y,
            "fnrgf_sun_r": self.sun_r,
            
            # RHEF
            "rhef_enabled": self.rhef_section.is_active(),
            "rhef_strength": self.sld_rhef_str.value(),
            "rhef_radius": self.sld_rhef_rad.value(),
            "rhef_upsilon": self.sld_rhef_ups.value() / 10.0,
            "rhef_sun_x": self.sun_x,
            "rhef_sun_y": self.sun_y,
            "rhef_sun_r": self.sun_r,
            
            # MGN
            "mgn_enabled": self.mgn_section.is_active(),
            "mgn_strength": self.sld_mgn_str.value(),
            "mgn_gamma": self.sld_mgn_gam.value(),
            "mgn_k": self.sld_mgn_k.value(),
            "mgn_h": self.sld_mgn_h.value(),
            "mgn_trunc": self.sld_mgn_trunc.value(),
            
            # WOW
            "wow_enabled": self.wow_section.is_active(),
            "wow_strength": self.sld_wow_str.value(),
            "wow_n_scales": self.sld_wow_scales.value(),
            "wow_gamma": self.sld_wow_gam.value(),
            "wow_h": self.sld_wow_h.value(),
            
            # USM
            "usm_enabled": self.usm_section.is_active(),
            "usm_strength": self.sld_usm_str.value(),
            "usm_radius": self.sld_usm_rad.value(),
            "usm_sigma": self.sld_usm_sig.value() / 10.0,
            
            # ACHF
            "achf_enabled": self.achf_section.is_active(),
            "achf_strength": self.sld_achf_str.value(),
            "achf_kernel": self.sld_achf_kernel.value(),
            "achf_boost": self.sld_achf_boost.value(),
        }
        
        # Clean up previous thread if exists
        if self.worker_thread is not None:
            try:
                self.worker_thread.quit()
                self.worker_thread.wait()
            except:
                pass
        
        # Start worker thread
        self.worker_thread = QThread()
        self.worker = FilterWorker()
        self.worker.moveToThread(self.worker_thread)
        
        # Connect signals
        self.worker.finished.connect(self._on_processing_finished)
        self.worker.error.connect(self._on_processing_error)
        self.worker_thread.started.connect(
            lambda: self.worker.process_pipeline(self.original_image, params)
        )
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)
        
        self.is_processing = True
        self.btn_process.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.statusBar().showMessage("Processing... (this may take a minute)")
        
        self.worker_thread.start()

    @Slot(np.ndarray)
    def _on_processing_finished(self, result: np.ndarray):
        """Handle processing completion."""
        self.current_image = result
        self._update_preview()
        
        self.is_processing = False
        self.btn_process.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.statusBar().showMessage("Processing complete. Ready to export.")
        
        if self.worker_thread is not None:
            try:
                self.worker_thread.quit()
                self.worker_thread.wait()
            except:
                pass

    @Slot(str)
    def _on_processing_error(self, error_msg: str):
        """Handle processing error."""
        self.is_processing = False
        self.btn_process.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.statusBar().showMessage("Processing failed.")
        QMessageBox.critical(self, "Processing Error", error_msg)
        
        if self.worker_thread is not None:
            try:
                self.worker_thread.quit()
                self.worker_thread.wait()
            except:
                pass

    @Slot()
    def _on_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About Eclipse Processor",
            "Eclipse Processor v1.4.0\n\n"
            "Modular solar eclipse image processing application\n"
            "with corrected FNRGF filter.\n\n"
            "Features:\n"
            "• 10 advanced filters\n"
            "• Multi-scale enhancements\n"
            "• Interactive preview\n"
            "• Async processing\n\n"
            "© 2026 Solar Eclipse Research"
        )

    def closeEvent(self, event):
        """Handle window close event."""
        if self.is_processing:
            reply = QMessageBox.question(
                self,
                "Processing in Progress",
                "Processing is still running. Are you sure you want to exit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return
            
            if self.worker_thread is not None:
                try:
                    self.worker_thread.quit()
                    self.worker_thread.wait()
                except:
                    pass
        
        event.accept()
