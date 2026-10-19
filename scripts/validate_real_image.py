"""Reproducible, opt-in validation on a user-supplied TIFF; never writes to it.

Run with QT_QPA_PLATFORM=offscreen and the project's Python environment.
Artifacts go to a new output directory. Numerical discrepancies across resolutions
are measurements, not pass/fail criteria for scientific correctness.
"""
import argparse
from copy import deepcopy
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import sys
import time
import warnings
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cv2
import numpy as np
from PIL import Image, ImageDraw
from PySide6.QtWidgets import QApplication
import tifffile

from core.filters import FilterWorker
from core.image_data import recipe_parameters
from core.pipeline import execute_pipeline
from core.presentation import render_presentation
from core.colour import colour_layer, set_luminosity
from gui.app import EclipseProcessorApp

STAGES = ("pre_stretch", "noise_gate", "bilateral", "fnrgf", "mgn", "wow", "rhef", "tangential", "achf")


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    before = digest(args.source)
    app = QApplication.instance() or QApplication([])
    window = EclipseProcessorApp()
    window.auto_calculate = False
    window.btn_auto_calc.setChecked(False)
    try:
        with patch("gui.app.QFileDialog.getOpenFileName", return_value=(str(args.source), "")):
            window.load_image_action()
        assert window.full_raw_image is not None, window.status_label.text()
        full, preview = window.full_raw_image, window.preview_image
        full_before, preview_before = full.copy(), preview.copy()
        source_rgb = tifffile.imread(args.source)
        report = dict(source=str(args.source), sha256=before,
                      shape=list(source_rgb.shape), dtype=str(source_rgb.dtype),
                      preview_shape=list(preview.shape), geometry=dict(
                          x=int(window.txt_x.text()), y=int(window.txt_y.text()), r=int(window.txt_r.text())),
                      saturated_samples=int(np.count_nonzero(source_rgb == np.iinfo(source_rgb.dtype).max))
                          if np.issubdtype(source_rgb.dtype, np.integer) else None,
                      zero_samples=int(np.count_nonzero(source_rgb == 0)),
                      versions={p: importlib.metadata.version(p) for p in
                                ("numpy", "scipy", "opencv-python", "PySide6", "tifffile", "watroo")},
                      python=sys.version, cases=[])
        params_preview = window.collect_filter_parameters(preview.shape)
        params_full = window.collect_filter_parameters(full.shape)
        display = dict(mode="asinh", strength=100, blend=1.)
        tiles = []

        def tile(values, title):
            # Fixed source min/max and identical asinh curve for every panel.
            low, high = float(full.min()), float(full.max())
            norm = np.clip((values-low)/(high-low), 0, 1)
            view = np.arcsinh(100*norm)/np.arcsinh(100)
            image = Image.fromarray((view*255).astype(np.uint8)).convert("RGB")
            image.thumbnail((550, 420))
            panel = Image.new("RGB", (550, 450), "#171717")
            panel.paste(image, (0, 28))
            ImageDraw.Draw(panel).text((8, 8), title, fill="white")
            tiles.append(panel)

        tile(full, "Original: fixed source range, asinh 100")
        cases = [(s, s, {"wow_bilateral": None, "statistics_exclude_lunar": False} if s == "wow" else {}) for s in STAGES]
        cases += [("fnrgf_legacy", "fnrgf", dict(fnrgf_mode="legacy")),
                  ("wow_masked", "wow", dict(wow_bilateral=None)),
                  ("pre_log", "pre_stretch", dict(pre_stretch_mode="log", pre_stretch_val=1.)),
                  ("rhef_continuous", "rhef", dict(rhef_mode="continuous")),
                  ("wow_bilateral", "wow", dict(wow_bilateral=1, wow_denoise=[1, 2, 3])),
                  ("combined", None, {})]
        worker = FilterWorker()
        for name, stage, extra in cases:
            row = dict(name=name, resolutions={})
            results = {}
            for resolution, image, baseline in (("preview", preview, params_preview), ("full", full, params_full)):
                p = deepcopy(baseline)
                for key in STAGES:
                    p[key+"_enabled"] = stage is None or key == stage
                    if key != "pre_stretch":
                        p[key+"_str"] = 10 if stage is None else 100
                p.update(extra)
                started = time.perf_counter()
                with warnings.catch_warnings(record=True) as caught:
                    warnings.simplefilter("always", RuntimeWarning)
                    out = execute_pipeline(worker, image, p)
                assert out.shape == image.shape and np.isfinite(out).all(), (name, resolution)
                assert not [w for w in caught if issubclass(w.category, RuntimeWarning)], (name, resolution, caught)
                results[resolution] = out
                row["resolutions"][resolution] = dict(
                    seconds=time.perf_counter()-started, min=float(out.min()), max=float(out.max()),
                    negative_pixels=int(np.count_nonzero(out < 0)),
                    percentiles=np.percentile(out, [0, 1, 50, 99, 100]).tolist(),
                    warnings=[str(w.message) for w in caught],
                    parameters=recipe_parameters(p),
                )
                if stage not in (None, "pre_stretch"):
                    bypass = deepcopy(p)
                    bypass[stage+"_str"] = 0
                    np.testing.assert_array_equal(execute_pipeline(worker, image, bypass), image)
                    if resolution == "preview":
                        mixed = deepcopy(p)
                        mixed[stage+"_str"] = 37
                        actual = execute_pipeline(worker, image, mixed)
                        np.testing.assert_allclose(actual, .63*image+.37*out, rtol=2e-6, atol=.02)
                        repeated = execute_pipeline(worker, image, p)
                        np.testing.assert_array_equal(repeated, out)
                if stage in ("fnrgf", "rhef"):
                    yy, xx = np.indices(image.shape)
                    radius = np.hypot(xx-p["sx"], yy-p["sy"])
                    inside = radius < p[stage+"_rad"]/10*p["sr"]
                    np.testing.assert_array_equal(out[inside], image[inside])
            reduced = cv2.resize(results["full"], (preview.shape[1], preview.shape[0]), interpolation=cv2.INTER_AREA)
            delta = reduced.astype(float)-results["preview"]
            row["preview_full_comparison"] = dict(
                rmse=float(np.sqrt(np.mean(delta**2))),
                normalized_rmse=float(np.sqrt(np.mean(delta**2))/np.ptp(full)),
                absolute_error_p99=float(np.percentile(np.abs(delta), 99)),
                note="Not a correctness threshold: ranking, normalization and wavelets are resolution dependent.")
            tile(results["full"], name+" (100% isolated; combined 10%)")
            # Numeric output retains signed values, before display clipping.
            tifffile.imwrite(args.output / (name+"_numeric.tiff"), results["full"].astype(np.float32))
            tifffile.imwrite(args.output / (name+"_preview_numeric.tiff"), results["preview"].astype(np.float32))
            report["cases"].append(row)
            (args.output/"measurements.json").write_text(json.dumps(report, indent=2))
            print("AUDIT CASE COMPLETE:", name, flush=True)

        # Exercise actual RGB TIFF/JPEG export with several stages and compare pixels.
        window.chk_export_layers.setChecked(False)
        window.chk_export_linear.setChecked(False)
        for key in ("mgn", "tangential"):
            getattr(window, "sec_"+key).chk_active.setChecked(True)
        # Exercise the actual background native-resolution verification job.
        window.recalculation_timer.stop()
        window.dispatch_pipeline_request()
        deadline = time.monotonic()+300
        while window.is_processing and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(.01)
        assert not window.is_processing and window._full_cache is not None, window.status_label.text()
        window.render_matrix_to_screen()
        verified_preview = window.last_preview_presentation.copy()
        destination = args.output/"actual_gui_export.tiff"
        with patch("gui.app.QFileDialog.getSaveFileName", return_value=(str(destination), "")):
            window.export_image_action()
        exported = tifffile.imread(destination)
        assert exported.dtype == np.uint16 and exported.shape == source_rgb.shape
        p = window.collect_filter_parameters(full.shape)
        actual_display = window.collect_display_parameters()
        processed = execute_pipeline(worker, full, p)
        expected = render_presentation(processed, full, actual_display)
        expected = set_luminosity(colour_layer(window.full_source_rgb, full, actual_display), expected)
        np.testing.assert_array_equal(exported, np.clip(expected*65535, 0, 65535).astype(np.uint16))
        jpeg = cv2.imread(str(destination.with_name(destination.stem+"_preview.jpg")))
        assert jpeg is not None and jpeg.shape == source_rgb.shape
        rgb8 = (np.clip(expected, 0, 1)*255).astype(np.uint8)
        reduced = cv2.resize(expected, (preview.shape[1], preview.shape[0]), interpolation=cv2.INTER_AREA)
        np.testing.assert_allclose(verified_preview, reduced, atol=1e-7)
        report['verification_preview_max_error'] = float(np.max(np.abs(verified_preview-reduced)))
        report["export"] = dict(shape=list(exported.shape), dtype=str(exported.dtype),
                                 exact_pixel_match=True, jpeg_mean_absolute_error=float(
                                     np.mean(np.abs(jpeg[..., ::-1].astype(float)-rgb8))),
                                 parameters=recipe_parameters(p), display=actual_display)
        np.testing.assert_array_equal(full, full_before)
        np.testing.assert_array_equal(preview, preview_before)
        report["source_unchanged"] = digest(args.source) == before
        assert report["source_unchanged"]
        cols = 3
        montage = Image.new("RGB", (550*cols, 450*((len(tiles)+cols-1)//cols)), "#171717")
        for index, image in enumerate(tiles):
            montage.paste(image, ((index % cols)*550, (index//cols)*450))
        montage.save(args.output/"comparison.png")
        # Geometry witness on full canvas, using the same fixed stretch as montage.
        low, high = float(full.min()), float(full.max())
        witness = Image.fromarray((np.arcsinh(100*(full-low)/(high-low))/np.arcsinh(100)*255).astype(np.uint8)).convert("RGB")
        g = report["geometry"]
        ImageDraw.Draw(witness).ellipse((g["x"]-g["r"], g["y"]-g["r"], g["x"]+g["r"], g["y"]+g["r"]), outline="red", width=2)
        witness.save(args.output/"geometry.png")
        report["completed"] = True
        (args.output/"measurements.json").write_text(json.dumps(report, indent=2))
    finally:
        window.close()
        app.processEvents()


if __name__ == "__main__":
    main()
