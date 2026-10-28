"""Native TIFF/JPEG and optional packages from an immutable GUI snapshot."""
import os
import time
import tempfile
from contextlib import ExitStack
from pathlib import Path
import cv2
import numpy as np
import tifffile
from .filters import FilterWorker, CPU_CORES
from .presentation import composition_settings, psb_presentation_settings
from .colour import neutralize_tse, set_luminosity, warm_colour
from .image_data import recipe_parameters
from .layer_export import export_layer_package
from .export_paths import export_paths, protect_source
from .linear_export import export_linear_sources


def export_images(source, parameters, display, file_path, original_path,
                  scale_factor=1., source_rgb=None, calibrate_colour=False, white=1.,
                  export_layers=False, export_linear=False, input_state='unknown', processed=None,
                  layers_format='tiff', layer_cache=None, project_settings=None, progress=None,
                  color_correction=False, psb_exposure_ev=0., psb_preview_jpeg=False,
                  original_rgb=None, export_prominences=False, prominence_exposure_ev=-2.,
                  prominence_saturation=1., warmth=0.):
    """Compute/write in the caller's worker; source and cached output stay untouched."""
    destinations = export_paths(file_path, project_settings is not None)
    protect_source(destinations, original_path)
    if processed is not None and np.shape(processed) != np.shape(source):
        raise ValueError('Cached composition must match the source canvas')
    if layers_format not in ('psb','tiff'):
        raise ValueError('Photoshop layers format must be psb or tiff')
    layers_requested = export_layers
    if color_correction and (not layers_requested or layers_format!='psb'):
        raise ValueError('Color Correction requires Photoshop PSB layer export')
    prominences = None
    if export_prominences:
        from .prominences import prominence_settings, prominence_layer
        if original_rgb is None or np.shape(original_rgb) != (*source.shape, 3):
            raise ValueError('Prominences require the original loaded RGB on the same canvas')
        settings=prominence_settings(original_rgb,parameters,prominence_exposure_ev,prominence_saturation)
        image,mask=prominence_layer(original_rgb,parameters,settings)
        prominences=(image,mask,settings)
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
    if colour_rgb is not None:
        colour_rgb = warm_colour(colour_rgb, warmth)
        colour_report['warmth'] = warmth
    stage('Calculating filters')
    from .layer_engine import engine_for
    engine = engine_for(worker)
    engine.prepare(worker,source,parameters)
    layers_path = None
    if layers_requested or psb_preview_jpeg:
        package_display = psb_presentation_settings(source, parameters.get('valid_mask'),
            rgb=colour_rgb, params=parameters, exposure_ev=psb_exposure_ev)
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
                package = export_layer_package(worker, source, parameters, package_display,
                    original_path, Path(temporary)/'layers', rgb=colour_rgb, colour_report=colour_report,
                    prominences=prominences)
                stage('Writing and verifying PSB')
                export_psb_package(package,candidate,color_correction=color_correction)
            layers_path = candidate
        else:
            layers_path = export_layer_package(worker, source, parameters, package_display,
                original_path, candidate, rgb=colour_rgb, colour_report=colour_report,
                prominences=prominences)

    linear_path = None
    if export_linear:
        stage('Writing source images')
        candidate = Path(file_path).with_suffix("").with_name(Path(file_path).stem + "_sources")
        suffix = 2
        while candidate.exists():
            candidate = Path(file_path).with_suffix("").with_name(Path(file_path).stem + f"_sources_{suffix}")
            suffix += 1
        linear_path = export_linear_sources(source, source_rgb, original_path, candidate, input_state,
                                            preprocessing=parameters.get('background_extraction'))

    stage('Composing final image')
    print(f"[EXPORT] Full-resolution layer composition; {CPU_CORES} CPUs available")
    img = engine.render(worker,source,parameters,display) if processed is None else processed
    if processed is not None:
        print("[EXPORT FINAL] Reusing cached native filters; no recalculation")
    neutral_display = composition_settings(display)
    img_norm = img
    if colour_rgb is not None:
        from .layer_engine import colour_display
        colour=colour_display(colour_rgb,source,neutral_display)
        img_norm = set_luminosity(colour,img_norm)
    from .presentation_edges import finish_presentation
    edge = engine.edge_alpha(source,parameters)
    if psb_preview_jpeg:
        from .presentation import psb_base
        base, colour = psb_base(source, parameters, package_display, colour_rgb)
        jpeg_image = engine.render(worker,source,parameters,package_display,base=base)
        if colour is not None:
            jpeg_image = set_luminosity(colour,jpeg_image)
        jpeg_image = finish_presentation(jpeg_image,edge)
        if prominences is not None:
            from .prominences import composite_prominences
            jpeg_image=composite_prominences(jpeg_image,*prominences[:2])
    else:
        jpeg_image = finish_presentation(img_norm, edge)
    img_norm=finish_presentation(img_norm,edge)
    from .layer_export import to_u16
    img_16bit=to_u16(img_norm)
    with ExitStack() as cleanup:
        temporary_paths = []
        for destination in destinations[:2]:
            fd, name = tempfile.mkstemp(dir=destination.parent,
                prefix='.' + destination.stem + '-', suffix=destination.suffix)
            os.close(fd)
            temporary = Path(name)
            cleanup.callback(temporary.unlink, missing_ok=True)
            temporary_paths.append(name)
        tiff_temporary, jpeg_temporary = temporary_paths
        t0 = time.time()
        stage('Writing TIFF')
        tifffile.imwrite(tiff_temporary, img_16bit, photometric="rgb" if colour_rgb is not None else "minisblack",
                         compression="zlib", maxworkers=CPU_CORES,
                         metadata={"scale_factor": scale_factor, "source": original_path,
                                   "parameters": recipe_parameters({k:v for k,v in parameters.items() if k != "layer_display"}),
                                   "composition_normalization": neutral_display, "visual_stretch_applied": False,
                                   "colour_calibration": colour_report, "missing_samples": "opaque zero; 2-native-pixel observed-side edge antialias",
                                   "role": "Independent layer composition; not a linear master"})
        if prominences is not None:
            from .prominences import composite_prominences
            image,mask,settings=prominences
            # Publish both products together without replacing an earlier prominence export.
            folder=Path(file_path).with_suffix('').with_name(Path(file_path).stem+'_prominences')
            base_folder=folder
            suffix=2
            while folder.exists():
                folder=base_folder.with_name(base_folder.name+f'_{suffix}');suffix+=1
            with tempfile.TemporaryDirectory(prefix='.prominences-',dir=folder.parent) as temporary:
                target=Path(temporary)/'products';target.mkdir()
                tifffile.imwrite(target/'PROMINENCES.tif',to_u16(composite_prominences(np.zeros(source.shape),image,mask)),
                                 photometric='rgb',compression='zlib',metadata=settings)
                tifffile.imwrite(target/'PROMINENCES_MASK.tif',mask,compression='zlib',metadata=None)
                target.rename(folder)
        print(f"[EXPORT: DISK WRITE] Done in {time.time() - t0:.3f}s")

        stage('Writing JPEG')
        # JPEG follows the selected presentation; the main TIFF remains un-stretched.
        t0 = time.time()

        jpeg_pixels = np.clip(jpeg_image * 255.0, 0, 255).astype(np.uint8)

        # Save as JPEG with high quality
        if not cv2.imwrite(jpeg_temporary, cv2.cvtColor(jpeg_pixels, cv2.COLOR_RGB2BGR) if jpeg_pixels.ndim == 3 else jpeg_pixels, [cv2.IMWRITE_JPEG_QUALITY, 95]):
            raise OSError("Could not write JPEG preview")
        print(f"[EXPORT: JPEG PREVIEW] Done in {time.time() - t0:.3f}s")

        # shortcut: publication is atomic per file; use a transaction if bundles must commit together.
        for temporary, destination in zip(temporary_paths, destinations[:2]):
            protect_source([destination], original_path)
            os.replace(temporary, destination)

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
            + (f" + {folder.name}" if prominences is not None else "")
            + (f" + {linear_path.name}" if linear_path else ""))
