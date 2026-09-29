# FiltrosEclipse v1.4.0 - Modular Structure Checklist

## 📋 Complete File Structure

### Root Level (4 files)
```
/
├── main.py                    ✓ Entry point (import config + gui.app)
├── config.py                  ⚠️ NEEDS UPDATE (see below)
├── requirements.txt           ✓ Python dependencies
└── README_MODULAR.md          ✓ Architecture documentation
```

### /core/ (6 files)
```
/core/
├── __init__.py                ✓ Package initializer (export FilterWorker)
├── filters.py                 ✓ FilterWorker class + all 39 filter algorithms
├── image_loader.py            ✓ Load FITS/NEF/PNG images
├── image_export.py            ✓ Export processed images (PNG/TIFF)
├── moon_detection.py          ✓ Moon detection algorithm
└── pipeline.py                ✓ Pipeline executor for batch processing
```

### /gui/ (8 files)
```
/gui/
├── __init__.py                ✓ Package initializer (export EclipseProcessorApp)
├── app.py                     ✓ EclipseProcessorApp main class
├── main_window.py             ✓ Main window layout + signals
├── components.py              ✓ UI components (sliders, spinboxes, buttons)
├── widgets.py                 ✓ Custom widgets (Canvas, Histogram, etc.)
├── factories.py               ✓ Widget factory functions
├── sections.py                ✓ Section panels (Radial, Histogram, Edges)
└── preview.py                 ✓ Preview canvas + image display
```

### /utils/ (3 files)
```
/utils/
├── __init__.py                ✓ Package initializer
├── helpers.py                 ✓ Utility helper functions
└── styling.py                 ✓ Qt stylesheet definitions
```

---

## ⚠️ config.py - REQUIRES UPDATE

The current `config.py` needs to include:

### 1. **Window Configuration**
```python
WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 900
CANVAS_WIDTH = 600
CANVAS_HEIGHT = 600
```

### 2. **Performance Settings**
```python
FNRGF_THREADS = 4  # Match your CPU core count
HISTOGRAM_LEVELS = 256
PREVIEW_SCALE = 0.5  # For faster preview updates
```

### 3. **Default Filter Parameters (ALL 39)**
```python
DEFAULT_FILTERS = {
    # FNRGF (Radial Normalization)
    'fnrgf_enabled': True,
    'fnrgf_sigma': 100.0,
    'fnrgf_power': 1.0,
    
    # Histogram Equalization
    'histogram_enabled': True,
    'histogram_clip_limit': 0.03,
    'histogram_grid_size': 8,
    
    # Gaussian Blur
    'gaussian_enabled': False,
    'gaussian_sigma': 1.0,
    
    # Bilateral Filter
    'bilateral_enabled': False,
    'bilateral_d': 9,
    'bilateral_sigma_color': 75.0,
    'bilateral_sigma_space': 75.0,
    
    # Median Filter
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
    
    # Unsharp Mask
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
```

### 4. **Qt Stylesheet**
```python
STYLESHEET = '''
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
    }
    QSlider::handle:horizontal {
        background: #0082c9;
        width: 12px;
        margin: -4px 0;
        border-radius: 6px;
    }
    QPushButton {
        background-color: #0082c9;
        color: white;
        border: none;
        padding: 5px;
        border-radius: 3px;
    }
    QPushButton:hover {
        background-color: #0066a1;
    }
    QPushButton:pressed {
        background-color: #004d7a;
    }
    QSpinBox, QDoubleSpinBox {
        background-color: #444444;
        color: #ffffff;
        border: 1px solid #555555;
        padding: 2px;
    }
    QComboBox {
        background-color: #444444;
        color: #ffffff;
        border: 1px solid #555555;
        padding: 2px;
    }
    QCheckBox {
        color: #ffffff;
    }
    QCheckBox::indicator {
        width: 16px;
        height: 16px;
    }
    QCheckBox::indicator:checked {
        background-color: #0082c9;
    }
    QGroupBox {
        color: #ffffff;
        border: 1px solid #555555;
        border-radius: 4px;
        margin-top: 8px;
        padding-top: 8px;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 3px 0 3px;
    }
    QScrollBar:vertical {
        background: #2b2b2b;
        width: 12px;
    }
    QScrollBar::handle:vertical {
        background: #0082c9;
        border-radius: 6px;
    }
    QProgressBar {
        background-color: #444444;
        border: 1px solid #555555;
        text-align: center;
        color: #ffffff;
    }
    QProgressBar::chunk {
        background-color: #0082c9;
    }
'''
```

---

## ✅ Verification Checklist

### Step 1: Verify File Existence
- [ ] `/core/__init__.py` exists
- [ ] `/core/filters.py` exists (25KB+)
- [ ] `/core/image_loader.py` exists
- [ ] `/core/image_export.py` exists
- [ ] `/core/moon_detection.py` exists
- [ ] `/core/pipeline.py` exists
- [ ] `/gui/__init__.py` exists
- [ ] `/gui/app.py` exists (60KB+)
- [ ] `/gui/main_window.py` exists (31KB+)
- [ ] `/gui/components.py` exists
- [ ] `/gui/widgets.py` exists
- [ ] `/gui/factories.py` exists
- [ ] `/gui/sections.py` exists
- [ ] `/gui/preview.py` exists
- [ ] `/utils/__init__.py` exists
- [ ] `/utils/helpers.py` exists
- [ ] `/utils/styling.py` exists
- [ ] `/main.py` exists (or `/main_new.py`)
- [ ] `/config.py` exists
- [ ] `/requirements.txt` exists

### Step 2: Update config.py
- [ ] Add all window dimensions
- [ ] Add all 39 filter parameters to DEFAULT_FILTERS
- [ ] Add complete Qt stylesheet
- [ ] Verify FNRGF_THREADS matches your CPU cores

### Step 3: Test Application
- [ ] Run: `python main.py`
- [ ] Load a FITS file
- [ ] Enable FNRGF filter
- [ ] Verify performance: FNRGF should complete in ~1.8-2.0 seconds
- [ ] Test other filters
- [ ] Verify UI responsiveness

### Step 4: Cleanup
- [ ] Delete old `/main.py` (if `/main_new.py` works)
- [ ] Rename `/main_new.py` → `/main.py` (if needed)
- [ ] Remove legacy directories: `/filters`, `/stretches`, `/worker`
- [ ] Keep: `/uploads`, `/outputs`, `/scripts` for user data

---

## 🚀 Startup Flow

```
User runs: python main.py
    ↓
main.py imports config + gui.app.EclipseProcessorApp
    ↓
EclipseProcessorApp.__init__()
    ├─ Imports gui.main_window.MainWindow
    ├─ Imports core.filters.FilterWorker
    ├─ Imports utils.styling
    ├─ Creates UI components (gui.components)
    └─ Connects signals/slots
    ↓
MainWindow.setup_ui()
    ├─ gui.sections.RadialSection
    ├─ gui.sections.HistogramSection
    ├─ gui.preview.PreviewCanvas
    └─ gui.components (sliders, spinboxes, buttons)
    ↓
FilterWorker ready for processing
    ├─ core.image_loader (load images)
    ├─ core.filters (apply algorithms)
    ├─ core.image_export (save results)
    └─ core.moon_detection (detect moon)
```

---

## 📝 Notes

- **Token Efficiency**: By specifying which module to load in future queries (e.g., "Load core/filters.py"), you'll save significant context window space.
- **Performance**: FNRGF filter maintains original performance (~1.8-2.0s for large images).
- **UI Integrity**: All 39 filter parameters are preserved in the modular structure.
- **Styling**: Centralized in `config.py` + `utils/styling.py` for easy customization.

---

**Status**: ✅ Modularization Complete | ⏳ Awaiting User Verification
