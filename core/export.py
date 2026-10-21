"""Native TIFF/JPEG and optional packages from an immutable GUI snapshot."""
import os
import time
from pathlib import Path
import cv2
import numpy as np
import tifffile
from .filters import FilterWorker, CPU_CORES
from .pipeline import execute_pipeline
from .presentation import render_presentation
from .colour import neutralize_tse, colour_layer, set_luminosity
from .image_data import recipe_parameters
from .layer_export import export_layer_package
from .linear_export import export_linear_sources


def export_images(source, parameters, display, file_path, original_path,
                  scale_factor=1., source_rgb=None, calibrate_colour=False, white=1.,
                  export_layers=False, export_linear=False, input_state='unknown', processed=None):
    """Compute/write in the caller's worker; source and cached output stay untouched."""
    export_start = time.time()
    worker = FilterWorker()
    colour_rgb, colour_report = source_rgb, dict(method='none') if source_rgb is not None else None
    if source_rgb is not None and calibrate_colour:
        colour_rgb, colour_report = neutralize_tse(source_rgb, white)
    print(f"[EXPORT] Full-resolution calculation; {CPU_CORES} CPUs available")
    img = execute_pipeline(worker, source, parameters) if processed is None else processed
    img_norm = render_presentation(img, source, display)
    if colour_rgb is not None:
        img_norm = set_luminosity(colour_layer(colour_rgb, source, display), img_norm)
    img_16bit = np.clip(img_norm*65535., 0, 65535).astype(np.uint16)
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

    return (f"Status: Exported {os.path.basename(file_path)} + preview"
            + (f" + {layers_path.name}" if layers_path else "")
            + (f" + {linear_path.name}" if linear_path else ""))
