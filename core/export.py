"""Native TIFF/JPEG and optional packages from an immutable GUI snapshot."""
import os
import time
import tempfile
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
                  export_layers=False, export_linear=False, input_state='unknown', processed=None,
                  layers_format='tiff', layer_cache=None, project_settings=None, progress=None,
                  color_correction=False):
    """Compute/write in the caller's worker; source and cached output stay untouched."""
    if layers_format not in ('psb','tiff'):
        raise ValueError('Photoshop layers format must be psb or tiff')
    layers_requested=export_layers or parameters.get("export_achf_variants",False) or parameters.get("export_achf_ael_variants",False)
    if color_correction and (not layers_requested or layers_format!='psb'):
        raise ValueError('Color Correction requires Photoshop PSB layer export')
    stages=['Preparing export','Calculating filters']
    if layers_requested:
        stages.append('Writing layer package')
        if layers_format=='psb':stages.append('Writing and verifying PSB')
    if export_linear:stages.append('Writing source images')
    stages.extend(['Composing final image','Writing TIFF','Writing JPEG'])
    if project_settings is not None:stages.append('Writing settings JSON')
    def stage(label):
        if progress is not None:progress(round(100*stages.index(label)/len(stages)),label)
    stage('Preparing export')
    export_start = time.time()
    worker = FilterWorker()
    if layer_cache is not None:
        from .layer_engine import LayerEngine
        if not isinstance(layer_cache,LayerEngine):
            raise ValueError("Invalid layer cache")
        worker.layer_engine=layer_cache
    colour_rgb, colour_report = source_rgb, dict(method='none') if source_rgb is not None else None
    if source_rgb is not None and calibrate_colour:
        colour_rgb, colour_report = neutralize_tse(source_rgb, white)
    stage('Calculating filters')
    if parameters.get('layered_model',False):
        from .layer_engine import engine_for
        engine_for(worker).prepare(worker,source,parameters)
    layers_path = None
    if layers_requested:
        stage('Writing layer package')
        stem = Path(file_path).with_suffix("").with_name(Path(file_path).stem + "_PS_layers")
        candidate = stem.with_name(stem.name + '.psb') if layers_format == 'psb' else stem
        suffix = 2
        while candidate.exists():
            candidate = stem.with_name(stem.name + f"_{suffix}" + ('.psb' if layers_format == 'psb' else ''))
            suffix += 1
        if layers_format == 'psb':
            from .psb_export import export_psb_package
            with tempfile.TemporaryDirectory(prefix='eip-psb-layers-') as temporary:
                package = export_layer_package(worker, source, parameters, display,
                    original_path, Path(temporary)/'layers', rgb=colour_rgb, colour_report=colour_report)
                stage('Writing and verifying PSB')
                export_psb_package(package,candidate,color_correction=color_correction)
            layers_path = candidate
        else:
            layers_path = export_layer_package(worker, source, parameters, display,
                original_path, candidate, rgb=colour_rgb, colour_report=colour_report)

    linear_path = None
    if export_linear:
        stage('Writing source images')
        candidate = Path(file_path).with_suffix("").with_name(Path(file_path).stem + "_sources")
        suffix = 2
        while candidate.exists():
            candidate = Path(file_path).with_suffix("").with_name(Path(file_path).stem + f"_sources_{suffix}")
            suffix += 1
        linear_path = export_linear_sources(source, source_rgb, original_path, candidate, input_state)

    stage('Composing final image')
    action="layer composition" if parameters.get("layered_model",False) else "calculation"
    print(f"[EXPORT] Full-resolution {action}; {CPU_CORES} CPUs available")
    if parameters.get("layered_model",False):
        from .layer_engine import engine_for
        img = engine_for(worker).render(worker,source,parameters,display) if processed is None else processed
    else:
        img = execute_pipeline(worker, source, parameters, process_label="EXPORT FINAL") if processed is None else processed
    if processed is not None:
        print("[EXPORT FINAL] Reusing cached native filters; no recalculation")
    presentation_start = time.perf_counter()
    img_norm = img if parameters.get("layered_model",False) else render_presentation(img, source, display)
    print(f"[EXPORT FINAL: PRESENTATION] Done in {time.perf_counter()-presentation_start:.3f}s")
    if colour_rgb is not None:
        if parameters.get("layered_model",False):
            from .layer_engine import colour_display
            colour=colour_display(colour_rgb,source,display)
        else:
            colour=colour_layer(colour_rgb,source,display)
        img_norm = set_luminosity(colour,img_norm)
    from .layer_engine import engine_for
    from .presentation_edges import finish_presentation
    img_norm=finish_presentation(img_norm,engine_for(worker).edge_alpha(source,parameters))
    if parameters.get("layered_model",False):
        from .layer_export import to_u16
        img_16bit=to_u16(img_norm)
    else:
        img_16bit = np.clip(img_norm*65535., 0, 65535).astype(np.uint16)
    t0 = time.time()
    stage('Writing TIFF')
    tifffile.imwrite(file_path, img_16bit, photometric="rgb" if colour_rgb is not None else "minisblack",
                     compression="zlib", maxworkers=CPU_CORES,
                     metadata={"scale_factor": scale_factor, "source": original_path,
                               "parameters": recipe_parameters(parameters), "display": display,
                               "colour_calibration": colour_report, "missing_samples": "opaque zero; 2-native-pixel observed-side edge antialias",
                               "role": "Independent layer composition; not a linear master" if parameters.get("layered_model",False) else "Sequential pipeline presentation; not a linear master"})
    print(f"[EXPORT: DISK WRITE] Done in {time.time() - t0:.3f}s")
    
    stage('Writing JPEG')
    # Presentation is already stretched: JPEG uses the same display values.
    t0 = time.time()
    jpeg_path = file_path.rsplit('.', 1)[0] + "_preview.jpg"
    
    img_gamma = img_norm
    img_gamma = np.clip(img_gamma * 255.0, 0, 255).astype(np.uint8)
    
    # Save as JPEG with high quality
    if not cv2.imwrite(jpeg_path, cv2.cvtColor(img_gamma, cv2.COLOR_RGB2BGR) if img_gamma.ndim == 3 else img_gamma, [cv2.IMWRITE_JPEG_QUALITY, 95]):
        raise OSError("Could not write JPEG preview")
    print(f"[EXPORT: JPEG PREVIEW] Done in {time.time() - t0:.3f}s")
    
    settings_path=None
    if project_settings is not None:
        stage('Writing settings JSON')
        from .project_settings import write_settings
        settings_path=write_settings(file_path,original_path,project_settings,parameters,display)

    print(f"[EXPORT] Finished successfully in {time.time() - export_start:.3f}s\n{'='*80}\n")

    if progress is not None:progress(100,'Export complete')
    return (f"Status: Exported {os.path.basename(file_path)} + preview"
            + (f" + {settings_path.name}" if settings_path else "")
            + (f" + {layers_path.name}" if layers_path else "")
            + (f" + {linear_path.name}" if linear_path else ""))
