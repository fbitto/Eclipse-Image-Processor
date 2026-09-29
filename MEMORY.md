# MEMORY.md - Long-Term Memory

## Key Decisions

- solar_eclipse_processor.py will NOT use sunpy/sunkit-image (e.g. for FNRGF radial filtering) - decided to keep the script's dependency footprint minimal (numpy/scipy/Pillow required; rawpy/exifread/tifffile optional). The custom radial_flatten (Adaptive Circular Filter) stays as the sole radial-normalization approach.
- FiltrosEclipse v1.3.1 - Performance restored to original spec (FNRGF: 1.8-2.0s). Code kept monolithic in main.py with config.py for stylesheet. No modularization attempted — original fast implementation preserved exactly.

## Lessons Learned

- In solar corona radial normalization (RHEF), discrete annular binning creates concentric ring/onion-layer banding artifacts due to independent [0, 1] ranking per bin. Replacing discrete bins with continuous 1D radial Gaussian profiles (gaussian_filter1d on radial mean/std profiles) eliminates banding completely while preserving radial streamers.

## Ongoing Projects

- Main client: Mecalux, S.A.
- FiltrosEclipse v1.4.0 - MODULAR ARCHITECTURE COMPLETE. Refactored into /core, /gui, /utils with 20 Python files. config.py updated with all 39 filters + dark theme stylesheet. FNRGF performance preserved (1.8-2.0s). Ready for user testing. See MODULAR_CHECKLIST.md and SETUP_SUMMARY.md for details.

## Opinions & Preferences

- Prefers inline script metadata (PEP 723 standard) in standalone Python files for direct execution with tools like `uv run`. When generating complete standalone Python scripts, include the `/// script` metadata block specifying `requires-python` and `dependencies`.

