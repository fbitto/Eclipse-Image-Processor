# Eclipse Image Processor

A powerful desktop application for processing and analyzing solar eclipse images. FiltrosEclipse provides advanced image filtering, radial normalization, and harmonic analysis tools specifically designed for eclipse corona imaging.

## Features

- **16/32-bit Image Support**: Load TIFF, FITS, and XISF solar master frames
- **Radial Normalization**: Fourier-based radial enhancement filter (FNRGF) for corona analysis
- **Harmonic Analysis**: Configurable harmonic decomposition with Fourier order control
- **Real-time Preview**: Toggle between filtered and original images
- **Dyadic Angular Segmentation**: Power-of-2 angular subdivisions (16-256 segments)
- **Advanced Denoising**: Bilateral filtering and multi-scale processing
- **Automatic Lunar Disk Detection**: Hough Circle Transform for precise boundary detection
- **Interactive Controls**: Sliders for all parameters with live preview
- **Multiple Export Formats**: Save processed images in various formats

## System Requirements

- **Python**: 3.14 or higher
- **OS**: Windows, macOS, or Linux
- **RAM**: 4GB minimum (8GB recommended)
- **Disk Space**: 500MB for installation

## Installation

### Windows

1. **Install Python 3.14+**
   - Download from [python.org](https://www.python.org/downloads/)
   - During installation, check "Add Python to PATH"

2. **Clone the Repository**
   ```bash
   git clone https://github.com/yourusername/Eclipse-Image-Processor.git
   cd Eclipse-Image-Processor
   ```

3. **Create Virtual Environment (Recommended)**
   ```bash
   python -m venv venv
   venv\Scriptsctivate
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
   git clone https://github.com/yourusername/Eclipse-Image-Processor.git
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
   git clone https://github.com/yourusername/Eclipse-Image-Processor.git
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

## Quick Start Guide

### 1. Load an Image

- Click **📁 Open Image** button
- Select a 16-bit or 32-bit TIFF, FITS, or XISF file
- The image will load and display in the preview area

### 2. Detect Lunar Disk

- Click **🏌️ Auto-detect Lunar Disk** to automatically find the lunar boundary
- Or manually enter center coordinates (X, Y) and radius (R)
- The detected circle appears as an overlay on the image

### 3. Configure FNRGF Filter

The Fourier-based Radial Enhancement Filter (FNRGF) is the core processing tool:

- **Strength** (0-100): Filter intensity. 0 = no filtering
- **Fourier Order** (0-50): Number of harmonic coefficients. Higher = more detail
- **Angular Segments** (2^n: 16-256): Azimuthal resolution. Must be power of 2
  - Minimum segments = 2 × Fourier Order (Nyquist sampling)
  - Default: 64 (2^6) recommended for Order ≤ 8
- **Harmonic Cutoff** (0-20): Frequency cutoff to reduce oscillations
- **App Radius** (0.5-2.5 R☉): Filter envelope application radius
- **Outer Radius R_max** (1.5-6.0 R☉): Outer boundary for analysis

### 4. Apply Additional Filters

**Bilateral Denoising**
- Smooths image while preserving edges
- **Strength**: Filter intensity (0-100)

**Pre-Stretch** (Optional)
- Normalize intensity before processing
- Useful for low-contrast images

**Multi-Scale Processing** (Optional)
- Applies filters at multiple scales
- Enhances fine details

**Sharpening** (Optional)
- Unsharp mask for edge enhancement

### 5. Compare Results

- Click **👁️ View Original** to toggle between filtered and original images
- Use **Auto Calculate** to enable real-time updates as you adjust sliders

### 6. Save Results

- Use **File > Export** to save the processed image
- Supports PNG, JPEG, TIFF, and other formats
- Choose output resolution and quality

## Parameter Guidelines

### For Coronal Streamers
- Fourier Order: 8-12
- Angular Segments: 32-64 (2^5 to 2^6)
- FNRGF Strength: 50-80
- App Radius: 1.0-1.5 R☉

### For Fine Structure
- Fourier Order: 15-25
- Angular Segments: 64-128 (2^6 to 2^7)
- FNRGF Strength: 60-90
- App Radius: 1.5-2.0 R☉

### For Large-Scale Features
- Fourier Order: 4-8
- Angular Segments: 16-32 (2^4 to 2^5)
- FNRGF Strength: 30-60
- App Radius: 0.8-1.2 R☉

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+O` | Open image |
| `Ctrl+E` | Export image |
| `Ctrl+Q` | Quit application |
| `Space` | Toggle original/filtered view |

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

## File Formats

### Supported Input Formats
- **TIFF** (.tif, .tiff): 16-bit or 32-bit
- **FITS** (.fits, .fit): Standard astronomical format
- **XISF** (.xisf): eXtensible Image Serialization Format

### Supported Output Formats
- PNG, JPEG, TIFF (16-bit), FITS

## Performance Tips

1. **Use appropriate image resolution** (2048×2048 to 4096×4096 recommended)
2. **Limit Fourier Order** to 20-30 for real-time processing
3. **Enable Auto Calculate** only when needed (toggle off while adjusting)
4. **Use 64 angular segments** as default for balanced results
5. **Close unnecessary applications** to maximize available RAM

## Citation

If you use this application in scientific research, please cite:
```
FiltrosEclipse: Advanced Solar Eclipse Image Processing
[Your Institution/Author Name]
```

## License

[Your License Here - e.g., MIT, GPL-3.0]

## Support & Issues

- Report bugs on [GitHub Issues](https://github.com/yourusername/Eclipse-Image-Processor/issues)
- For questions, use [GitHub Discussions](https://github.com/yourusername/Eclipse-Image-Processor/discussions)

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Changelog

### v1.4.0
- Implemented dyadic angular segmentation (powers of 2)
- Added intelligent slider with Nyquist validation
- Improved FNRGF performance
- Enhanced UI with golden button styling

### v1.3.1
- Performance optimizations
- Bug fixes in radial normalization

### v1.0.0
- Initial release

---

**Last Updated**: 2026-10-01  
**Maintainer**: [Your Name/Team]
