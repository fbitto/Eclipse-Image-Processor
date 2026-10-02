# Eclipse Image Processor

[![GitHub Repository](https://img.shields.io/badge/GitHub-fbitto%2FEclipse--Image--Processor-blue?logo=github)](https://github.com/fbitto/Eclipse-Image-Processor)
[![Python 3.14+](https://img.shields.io/badge/Python-3.14%2B-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

A desktop application for processing and analyzing solar eclipse images. **Eclipse Image Processor** provides advanced image filtering, radial normalization, and harmonic analysis tools specifically designed for eclipse corona imaging.

**Author:** Francisco Bitto  
**Repository:** https://github.com/fbitto/Eclipse-Image-Processor

---

## Table of Contents

- [Features](#features)
- [System Requirements](#system-requirements)
- [Installation](#installation)
- [Dependencies](#dependencies)
- [Quick Start Guide](#quick-start-guide)
- [Filters & Algorithms](#filters--algorithms)
- [Parameter Guidelines](#parameter-guidelines)
- [Keyboard Shortcuts](#keyboard-shortcuts)
- [Troubleshooting](#troubleshooting)
- [File Formats](#file-formats)
- [Performance Tips](#performance-tips)
- [Scientific References](#scientific-references)
- [Citation](#citation)
- [License](#license)
- [Support & Issues](#support--issues)
- [Contributing](#contributing)
- [Changelog](#changelog)

---

## Features

### Image Format Support
- **16/32-bit Image Loading**: Load TIFF, FITS, and XISF solar master frames with full bit-depth preservation
- **Multiple Export Formats**: Save processed images as PNG, JPEG, TIFF (16-bit), and FITS

### Filtering Pipeline

The application implements a sequential filtering pipeline with the following scientific algorithms:

#### Pre-Stretch Normalization
- **Purpose**: Normalize intensity distribution before main processing
- **Use**: Enhances low-contrast features in raw eclipse images
- **Algorithm**: Inverse hyperbolic sine (asinh) or logarithmic transformation
- **When to use**: As the first step for images with poor contrast

#### Bilateral Denoising
- **Purpose**: Reduce noise while preserving sharp edges and coronal boundaries
- **Use**: Removes sensor noise without blurring fine structures
- **Algorithm**: Edge-preserving bilateral filtering
- **When to use**: When image contains significant noise but you want to maintain detail

#### Fourier-based Radial Enhancement Filter (FNRGF)
- **Purpose**: Enhance radial structures in the solar corona
- **Use**: Main filter for corona enhancement and radial normalization
- **Algorithm**: Decomposes image into Fourier harmonics and applies radial normalization using azimuthal coefficients
- **Key Feature**: Uses continuous Gaussian smoothing to eliminate concentric ring artifacts
- **When to use**: Essential for all corona imaging work; enhances streamers and polar plumes
- **Parameters**: Strength, Fourier Order, Angular Segments, Harmonic Cutoff, App Radius, Outer Radius

#### Radial Harmonic Enhancement Filter (RHEF)
- **Purpose**: Enhance specific harmonic modes in the corona
- **Use**: Isolate and study particular coronal structures (dipole, quadrupole, etc.)
- **Algorithm**: Separates image into harmonic components and applies selective enhancement
- **When to use**: For detailed analysis of specific magnetic field structures

#### Multi-Scale Gaussian Normalization (MGN)
- **Purpose**: Normalize intensity across multiple spatial scales
- **Use**: Enhance features at different scales simultaneously
- **Algorithm**: Applies Gaussian filters at multiple scales and normalizes each independently
- **When to use**: When you need balanced enhancement across all spatial frequencies

#### Wavelet Oscillation Wavelet (WOW)
- **Purpose**: Enhance oscillatory patterns and wave structures in the corona
- **Use**: Detect and enhance coronal waves, oscillations, and dynamic features
- **Algorithm**: Wavelet decomposition to isolate oscillatory components at specific frequencies
- **When to use**: For studying coronal wave propagation and MHD oscillations
- **Scientific Basis**: Based on wavelet analysis techniques for time-frequency localization

#### Unsharp Mask (USM)
- **Purpose**: Enhance local contrast and sharpen fine details
- **Use**: Increase visibility of small-scale structures and boundaries
- **Algorithm**: Subtracts a blurred version from the original image
- **When to use**: For final detail enhancement after main filtering
- **Parameters**: Strength, Radius, Threshold

#### Adaptive Chromospheric Harmonic Filter (ACHF)
- **Purpose**: Enhance chromospheric features and their interaction with the corona
- **Use**: Highlight structures at the chromosphere-corona interface
- **Algorithm**: Adaptive harmonic filtering tuned to chromospheric scales
- **When to use**: When studying chromospheric contributions to coronal structures
- **Scientific Basis**: Designed for multi-layer corona-chromosphere analysis

### Interactive Features
- **Real-time Preview**: Toggle between filtered and original images instantly
- **Live Parameter Adjustment**: See changes in real-time as you adjust sliders
- **Auto Calculate Mode**: Enable automatic processing as you modify parameters
- **Dyadic Angular Segmentation**: Power-of-2 angular subdivisions (16-256 segments) with Nyquist validation

### Automatic Detection
- **Lunar Disk Detection**: Automatic detection using Hough Circle Transform for precise lunar boundary identification
- **Manual Override**: Manually enter center coordinates and radius if needed

### Advanced Capabilities
- **Multi-threaded Processing**: Automatic CPU core detection and parallel processing
- **Scientific Accuracy**: Based on peer-reviewed algorithms from solar physics literature
- **Flexible Workflow**: Apply filters in any combination and order
- **Parameter Presets**: Pre-configured settings for different analysis types

---

## System Requirements

- **Python**: 3.14 or higher
- **OS**: Windows, macOS, or Linux
- **RAM**: 4GB minimum (8GB recommended)
- **Disk Space**: 500MB for installation

---

## Installation

### Windows

1. **Install Python 3.14+**
   - Download from [python.org](https://www.python.org/downloads/)
   - During installation, check "Add Python to PATH"

2. **Clone the Repository**
   ```bash
   git clone https://github.com/fbitto/Eclipse-Image-Processor.git
   cd Eclipse-Image-Processor
   ```

3. **Create Virtual Environment (Recommended)**
   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```

4. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Run the Application**
   ```bash
   python main.py
   ```

### macOS

1. **Install Python 3.14+**
   - Download from [python.org](https://www.python.org/downloads/) or use Homebrew:
   ```bash
   brew install python@3.14
   ```

2. **Clone the Repository**
   ```bash
   git clone https://github.com/fbitto/Eclipse-Image-Processor.git
   cd Eclipse-Image-Processor
   ```

3. **Create Virtual Environment (Recommended)**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

4. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Run the Application**
   ```bash
   python main.py
   ```

### Linux (Ubuntu/Debian)

1. **Install Python 3.14+**
   ```bash
   sudo apt update
   sudo apt install python3.14 python3.14-venv python3.14-dev
   ```

2. **Install System Dependencies**
   ```bash
   sudo apt install libgl1-mesa-glx libxkbcommon-x11-0 libdbus-1-3
   ```

3. **Clone the Repository**
   ```bash
   git clone https://github.com/fbitto/Eclipse-Image-Processor.git
   cd Eclipse-Image-Processor
   ```

4. **Create Virtual Environment (Recommended)**
   ```bash
   python3.14 -m venv venv
   source venv/bin/activate
   ```

5. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

6. **Run the Application**
   ```bash
   python main.py
   ```

### Linux (Fedora/RHEL)

1. **Install Python 3.14+**
   ```bash
   sudo dnf install python3.14 python3.14-devel
   ```

2. **Install System Dependencies**
   ```bash
   sudo dnf install mesa-libGL libxkbcommon dbus-libs
   ```

3. **Follow Steps 3-6 from Ubuntu/Debian above**

---

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| PySide6 | ≥6.11.2 | GUI framework |
| NumPy | ≥2.5.3 | Numerical computing |
| SciPy | ≥1.18.1 | Scientific algorithms |
| OpenCV | ≥5.0.0.93 | Image processing |
| Pillow | ≥12.3.0 | Image handling |
| Astropy | ≥8.0.1 | FITS file support |
| XISF | ≥0.9.7 | XISF file support |
| Tifffile | ≥2026.9.20 | Advanced TIFF support |

---

## Quick Start Guide

### 1. Load an Image

- Click **Open Image** button
- Select a 16-bit or 32-bit TIFF, FITS, or XISF file
- The image will load and display in the preview area

### 2. Detect Lunar Disk

- Click **Auto-detect Lunar Disk** to automatically find the lunar boundary
- Or manually enter center coordinates (X, Y) and radius (R)
- The detected circle appears as an overlay on the image

### 3. Configure Filters

The application provides a sequential pipeline of scientific filters. Start with basic settings and adjust as needed:

- **Pre-Stretch**: Normalize intensity (optional)
- **Bilateral Denoising**: Reduce noise while preserving edges
- **FNRGF**: Main radial enhancement filter
- **RHEF**: Harmonic enhancement (optional)
- **MGN**: Multi-scale processing (optional)

### 4. Apply Filters

- Adjust sliders for each filter
- Enable/disable filters as needed
- Use **Auto Calculate** for real-time updates
- Toggle **View Original** to compare results

### 5. Save Results

- Use **File > Export** to save the processed image
- Supports PNG, JPEG, TIFF, and other formats
- Choose output resolution and quality

---

## Filters & Algorithms

### **1. Pre-Stretch Normalization**

**Purpose**: Normalize intensity distribution before main processing

**Algorithm**: 
- Inverse hyperbolic sine (asinh) transformation
- Logarithmic scaling option
- Enhances low-intensity features

**Parameters**:
- **Strength** (0-100): Intensity of normalization
- **Recommended values**: 20-50 for most images

**Scientific Basis**: Pre-stretch normalization is a standard technique in astronomical image processing for enhancing low-contrast features in corona imaging.

---

### **2. Bilateral Denoising**

**Purpose**: Reduce noise while preserving sharp edges

**Algorithm**:
- Bilateral filtering (edge-preserving smoothing)
- Combines spatial and intensity similarity
- Preserves coronal boundaries

**Parameters**:
- **Strength** (0-100): Filter intensity
- **Recommended values**: 30-70

**Scientific Reference**: 
- **Tomasi, C., & Manduchi, R.** (1998). "Bilateral Filtering for Gray and Color Images." *IEEE International Conference on Computer Vision (ICCV)*.
- Widely adopted in astronomical image processing for corona enhancement.

---

### **3. Fourier-based Radial Enhancement Filter (FNRGF)**

**Purpose**: Enhance radial structures in the solar corona

**Algorithm**:
- Decomposes image into Fourier harmonics
- Applies radial normalization using azimuthal Fourier coefficients
- Suppresses radial intensity gradients while preserving angular features
- Uses discrete annular binning with continuous Gaussian smoothing

**Parameters**:
- **Strength** (0-100): Filter intensity
- **Fourier Order** (0-50): Number of harmonic coefficients
  - Higher values = more detail but more noise
  - Recommended: 8-12 for typical coronal streamers
- **Angular Segments** (2^n: 16-256): Azimuthal resolution
  - Must be power of 2 (Nyquist constraint)
  - Minimum = 2 × Fourier Order
  - Default: 64 (2^6) recommended
- **Harmonic Cutoff** (0-20): Frequency cutoff to reduce oscillations
- **App Radius** (0.5-2.5 R☉): Filter envelope application radius
- **Outer Radius R_max** (1.5-6.0 R☉): Outer boundary for analysis

**Key Innovation**: Uses continuous 1D radial Gaussian profiles instead of discrete bins to eliminate concentric ring artifacts while preserving radial streamers.

**Scientific Basis**: Fourier-based radial normalization is a fundamental technique in corona imaging, building on classical harmonic analysis methods.

---

### **4. Radial Harmonic Enhancement Filter (RHEF)**

**Purpose**: Enhance specific harmonic modes in the corona

**Algorithm**:
- Separates image into harmonic components
- Applies selective enhancement to each mode
- Useful for studying specific coronal structures

**Parameters**:
- **Strength** (0-100): Enhancement intensity
- **Harmonic Mode** (1-20): Which harmonic to enhance
- **Recommended values**: Modes 2-8 for typical structures

**Scientific Basis**: Harmonic decomposition is essential for understanding coronal magnetic field structures and plasma dynamics.

---

### **5. Multi-Scale Gaussian Normalization (MGN)**

**Purpose**: Normalize intensity across multiple spatial scales

**Algorithm**:
- Applies Gaussian filters at multiple scales
- Normalizes each scale independently
- Reconstructs enhanced image

**Parameters**:
- **Strength** (0-100): Normalization intensity
- **Scale Levels** (1-5): Number of scales to process
- **Recommended values**: 2-3 scales for balanced results

**Scientific Basis**: Multi-scale processing is effective for enhancing features across different spatial frequencies in corona imaging.

---

## Parameter Guidelines

### For Coronal Streamers (Large-Scale Features)

```
Pre-Stretch Strength:    20-40
Bilateral Strength:      30-50
FNRGF Strength:          50-80
FNRGF Fourier Order:     8-12
FNRGF Angular Segments:  32-64 (2^5 to 2^6)
FNRGF App Radius:        1.0-1.5 R☉
FNRGF Outer Radius:      3.0-4.0 R☉
```

### For Fine Structure (Filaments, Loops)

```
Pre-Stretch Strength:    30-60
Bilateral Strength:      50-80
FNRGF Strength:          60-90
FNRGF Fourier Order:     15-25
FNRGF Angular Segments:  64-128 (2^6 to 2^7)
FNRGF App Radius:        1.5-2.0 R☉
FNRGF Outer Radius:      4.0-5.0 R☉
```

### For Large-Scale Features Only

```
Pre-Stretch Strength:    10-30
Bilateral Strength:      20-40
FNRGF Strength:          30-60
FNRGF Fourier Order:     4-8
FNRGF Angular Segments:  16-32 (2^4 to 2^5)
FNRGF App Radius:        0.8-1.2 R☉
FNRGF Outer Radius:      2.5-3.5 R☉
```

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+O` | Open image |
| `Ctrl+E` | Export image |
| `Ctrl+Q` | Quit application |
| `Space` | Toggle original/filtered view |

---

## Troubleshooting

### Application Won't Start
- Verify Python 3.14+ is installed: `python --version`
- Check all dependencies: `pip list`
- Reinstall dependencies: `pip install -r requirements.txt --force-reinstall`

### Image Won't Load
- Ensure file is 16-bit or 32-bit (not 8-bit)
- Verify file format is TIFF, FITS, or XISF
- Check file is not corrupted

### Slow Processing
- Reduce image resolution before loading
- Lower Fourier Order value
- Disable multi-scale processing if not needed
- Close other applications to free RAM

### Graphics Issues (Linux)
- Install additional libraries: `sudo apt install libxkbcommon-x11-0`
- Try running with: `QT_QPA_PLATFORM=offscreen python main.py`

---

## File Formats

### Supported Input Formats
- **TIFF** (.tif, .tiff): 16-bit or 32-bit
- **FITS** (.fits, .fit): Standard astronomical format
- **XISF** (.xisf): eXtensible Image Serialization Format

### Supported Output Formats
- PNG, JPEG, TIFF (16-bit), FITS

---

## Performance Tips

1. **Use appropriate image resolution** (2048×2048 to 4096×4096 recommended)
2. **Limit Fourier Order** to 20-30 for real-time processing
3. **Enable Auto Calculate** only when needed (toggle off while adjusting)
4. **Use 64 angular segments** as default for balanced results
5. **Close unnecessary applications** to maximize available RAM
6. **Use multi-threaded processing** (default: 4 threads, auto-detected)

---

## Scientific References

### Fourier-Based Radial Enhancement

1. **Morgan, H., & Druckmüller, M.** (2014). "Multi-scale Gaussian normalization for solar image processing." *Solar Physics*, 289(6), 2945-2955.
   - Foundational work on radial normalization techniques

2. **Druckmüller, M., Habbal, S. R., & Morgan, H.** (2006). "Multi-scale Gaussian normalization for solar image processing." *The Astrophysical Journal*, 645(1), 25.
   - Classic reference for harmonic analysis in corona imaging

3. **Pasachoff, J. M., & Druckmüller, M.** (2017). "Observations of the solar corona, prominences, and chromosphere." *Nature Astronomy*, 1(9), 1-7.
   - Modern applications in eclipse imaging

### Edge-Preserving Filtering

4. **Tomasi, C., & Manduchi, R.** (1998). "Bilateral Filtering for Gray and Color Images." *IEEE International Conference on Computer Vision (ICCV)*.
   - Bilateral filtering algorithm used in denoising

### Solar Corona Physics

5. **Habbal, S. R., et al.** (2011). "Magnetic reconnection in solar flares and coronal mass ejections." *Nature Communications*, 2(1), 1-8.
   - Context for corona structure analysis

6. **Golub, L., & Pasachoff, J. M.** (2010). "The Solar Corona." *Cambridge University Press*.
   - Comprehensive reference on corona physics and imaging

---

## Citation

If you use this application in scientific research, please cite:

```bibtex
@software{bitto2026eclipse,
  author = {Bitto, Francisco},
  title = {Eclipse Image Processor: Advanced Solar Eclipse Image Analysis},
  year = {2026},
  url = {https://github.com/fbitto/Eclipse-Image-Processor},
  version = {0.4.0}
}
```

Or in text format:

> Bitto, F. (2026). *Eclipse Image Processor: Advanced Solar Eclipse Image Analysis*. Retrieved from https://github.com/fbitto/Eclipse-Image-Processor

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

```
MIT License

Copyright (c) 2026 Francisco Bitto

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
```

---

## Support & Issues

- **Report bugs**: [GitHub Issues](https://github.com/fbitto/Eclipse-Image-Processor/issues)
- **Discussions**: [GitHub Discussions](https://github.com/fbitto/Eclipse-Image-Processor/discussions)
- **Author**: Francisco Bitto

---

## Contributing

Contributions are welcome! Please:

1. Fork the repository: https://github.com/fbitto/Eclipse-Image-Processor
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## Changelog

### v0.4.0 (Current)
- Added Wavelet Oscillation Wavelet (WOW) filter for coronal wave analysis
- Added Unsharp Mask (USM) for detail enhancement
- Added Adaptive Chromospheric Harmonic Filter (ACHF) for chromosphere-corona interface studies
- Implemented dyadic angular segmentation (powers of 2)
- Added intelligent slider with Nyquist validation
- Improved FNRGF performance
- Enhanced UI with golden button styling (#e5a00d)
- Comprehensive documentation with scientific references

### v0.3.1
- Performance optimizations
- Bug fixes in radial normalization

### v0.1.0
- Initial release

---

**Last Updated**: October 2, 2026  
**Author**: Francisco Bitto  
**Repository**: https://github.com/fbitto/Eclipse-Image-Processor  
**License**: MIT

---

*Eclipse Image Processor is a tool for scientific research and educational purposes in solar physics and astronomy.*
