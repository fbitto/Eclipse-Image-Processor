# config.py - Global Configuration & Styling for FiltrosEclipse v1.4.0

import os

# ============================================================================
# SYSTEM CONFIGURATION
# ============================================================================
CPU_CORES = os.cpu_count() or 4  # Auto-detect CPU cores, default to 4

# ============================================================================
# WINDOW CONFIGURATION
# ============================================================================
WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 900

CANVAS_WIDTH = 600
CANVAS_HEIGHT = 600

# ============================================================================
# PERFORMANCE SETTINGS
# ============================================================================
FNRGF_THREADS = CPU_CORES  # Number of threads for FNRGF - match your CPU core count
HISTOGRAM_LEVELS = 256
PREVIEW_SCALE = 0.5  # Scale factor for faster preview updates

# ============================================================================
# DEFAULT FILTER PARAMETERS (39 total)
# ============================================================================
FILTER_DEFAULTS = {
    # FNRGF (Radial Normalization - High Performance)
    'fnrgf_enabled': True,
    'fnrgf_sigma': 100.0,
    'fnrgf_power': 1.0,
    
    # Histogram Equalization (CLAHE-like)
    'histogram_enabled': True,
    'histogram_clip_limit': 0.03,
    'histogram_grid_size': 8,
    
    # Gaussian Blur (Smoothing)
    'gaussian_enabled': False,
    'gaussian_sigma': 1.0,
    
    # Bilateral Filter (Edge-preserving smoothing)
    'bilateral_enabled': False,
    'bilateral_d': 9,
    'bilateral_sigma_color': 75.0,
    'bilateral_sigma_space': 75.0,
    
    # Median Filter (Noise reduction)
    'median_enabled': False,
    'median_kernel': 5,
    
    # Morphological Operations
    'morph_enabled': False,
    'morph_operation': 'open',  # 'open', 'close', 'gradient'
    'morph_kernel_size': 5,
    
    # Edge Detection (Sobel)
    'sobel_enabled': False,
    'sobel_ksize': 3,
    
    # Canny Edge Detection
    'canny_enabled': False,
    'canny_threshold1': 50.0,
    'canny_threshold2': 150.0,
    'canny_aperturesize': 3,
    
    # Unsharp Mask (Sharpening)
    'unsharp_enabled': False,
    'unsharp_sigma': 1.0,
    'unsharp_strength': 1.5,
    
    # Contrast Enhancement
    'contrast_enabled': False,
    'contrast_factor': 1.5,
    
    # Brightness Adjustment
    'brightness_enabled': False,
    'brightness_factor': 0.0,
    
    # Saturation
    'saturation_enabled': False,
    'saturation_factor': 1.0,
    
    # Color Balance
    'color_balance_enabled': False,
    'color_balance_red': 0.0,
    'color_balance_green': 0.0,
    'color_balance_blue': 0.0,
    
    # Gamma Correction
    'gamma_enabled': False,
    'gamma_value': 1.0,
    
    # CLAHE (Contrast Limited Adaptive Histogram Equalization)
    'clahe_enabled': False,
    'clahe_clip_limit': 2.0,
    'clahe_tile_size': 8,
    
    # Wavelet Denoising
    'wavelet_enabled': False,
    'wavelet_sigma': 0.1,
    
    # Normalize (0-1 range)
    'normalize_enabled': False,
}

# ============================================================================
# QT STYLESHEET - Dark theme with Siemens blue accent
# ============================================================================
# Alias for backward compatibility with main_new.py
LIGHTROOM_QSS = '''
    QMainWindow {
        background-color: #2b2b2b;
        color: #ffffff;
    }
    
    QWidget {
        background-color: #2b2b2b;
        color: #ffffff;
    }
    
    QLabel {
        color: #ffffff;
    }
    
    QSlider::groove:horizontal {
        background: #444444;
        height: 4px;
        margin: 2px 0;
        border-radius: 2px;
    }
    
    QSlider::handle:horizontal {
        background: #0082c9;
        width: 12px;
        margin: -4px 0;
        border-radius: 6px;
        border: 1px solid #0066a1;
    }
    
    QSlider::handle:horizontal:hover {
        background: #00a8ff;
    }
    
    QSlider::sub-page:horizontal {
        background: #0082c9;
        border-radius: 2px;
    }
    
    QPushButton {
        background-color: #0082c9;
        color: white;
        border: none;
        padding: 6px 12px;
        border-radius: 3px;
        font-weight: bold;
    }
    
    QPushButton:hover {
        background-color: #00a8ff;
    }
    
    QPushButton:pressed {
        background-color: #004d7a;
    }
    
    QPushButton:disabled {
        background-color: #555555;
        color: #999999;
    }
    
    QSpinBox, QDoubleSpinBox {
        background-color: #444444;
        color: #ffffff;
        border: 1px solid #555555;
        padding: 2px;
        border-radius: 2px;
    }
    
    QSpinBox::up-button, QDoubleSpinBox::up-button {
        background-color: #0082c9;
        border: none;
    }
    
    QSpinBox::down-button, QDoubleSpinBox::down-button {
        background-color: #0082c9;
        border: none;
    }
    
    QComboBox {
        background-color: #444444;
        color: #ffffff;
        border: 1px solid #555555;
        padding: 2px 4px;
        border-radius: 2px;
    }
    
    QComboBox::drop-down {
        background-color: #0082c9;
        border: none;
    }
    
    QComboBox QAbstractItemView {
        background-color: #444444;
        color: #ffffff;
        selection-background-color: #0082c9;
    }
    
    QCheckBox {
        color: #ffffff;
        spacing: 5px;
    }
    
    QCheckBox::indicator {
        width: 16px;
        height: 16px;
        border: 1px solid #555555;
        border-radius: 2px;
        background-color: #444444;
    }
    
    QCheckBox::indicator:checked {
        background-color: #0082c9;
        border: 1px solid #0066a1;
    }
    
    QGroupBox {
        color: #ffffff;
        border: 1px solid #555555;
        border-radius: 4px;
        margin-top: 8px;
        padding-top: 8px;
        font-weight: bold;
    }
    
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 3px 0 3px;
    }
    
    QScrollBar:vertical {
        background: #2b2b2b;
        width: 12px;
        border: none;
    }
    
    QScrollBar::handle:vertical {
        background: #0082c9;
        border-radius: 6px;
        min-height: 20px;
    }
    
    QScrollBar::handle:vertical:hover {
        background: #00a8ff;
    }
    
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        border: none;
        background: none;
    }
    
    QScrollBar:horizontal {
        background: #2b2b2b;
        height: 12px;
        border: none;
    }
    
    QScrollBar::handle:horizontal {
        background: #0082c9;
        border-radius: 6px;
        min-width: 20px;
    }
    
    QScrollBar::handle:horizontal:hover {
        background: #00a8ff;
    }
    
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
        border: none;
        background: none;
    }
    
    QProgressBar {
        background-color: #444444;
        border: 1px solid #555555;
        border-radius: 3px;
        text-align: center;
        color: #ffffff;
        height: 20px;
    }
    
    QProgressBar::chunk {
        background-color: #0082c9;
        border-radius: 2px;
    }
    
    QTabBar::tab {
        background-color: #444444;
        color: #ffffff;
        padding: 4px 16px;
        border: 1px solid #555555;
    }
    
    QTabBar::tab:selected {
        background-color: #0082c9;
        border: 1px solid #0066a1;
    }
    
    QTabBar::tab:hover {
        background-color: #555555;
    }
    
    QTabWidget::pane {
        border: 1px solid #555555;
    }
    
    QMenuBar {
        background-color: #2b2b2b;
        color: #ffffff;
        border-bottom: 1px solid #555555;
    }
    
    QMenuBar::item:selected {
        background-color: #0082c9;
    }
    
    QMenu {
        background-color: #2b2b2b;
        color: #ffffff;
        border: 1px solid #555555;
    }
    
    QMenu::item:selected {
        background-color: #0082c9;
    }
    
    QStatusBar {
        background-color: #2b2b2b;
        color: #ffffff;
        border-top: 1px solid #555555;
    }
    
    QToolTip {
        background-color: #444444;
        color: #ffffff;
        border: 1px solid #0082c9;
        padding: 2px;
    }
    
    QMessageBox QLabel {
        color: #ffffff;
    }
    
    QMessageBox QPushButton {
        min-width: 60px;
    }
'''

# Backward compatibility aliases
STYLESHEET = LIGHTROOM_QSS  # For PyQt5-based code
DEFAULT_FILTERS = FILTER_DEFAULTS  # For older code
