"""Write cached filter layers with an independent Photoshop presentation recipe.

The layers are produced once, in Photoshop order, and handed to a sink. The
TIFF route writes each one to the package folder as it comes, exactly as
before. The PSB route keeps them in memory (build_layer_package), so
core.psb_export encodes them without writing, re-reading and hashing a TIFF
file per layer. Pixels, order, names, modes and opacities are the same on
both routes.
"""
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import time
import numpy as np
import tifffile

from .cancellation import check_cancelled
from .colour import set_luminosity
from .image_data import recipe_parameters, zero_missing
from .layer_engine import engine_for, requests, opacity, LABELS

# The in-memory route has no layer file to hash: each recipe row gets this digest instead.
LAYER_SHA256 = ('sha256 of each layer as uint16 pixels in C order, little-endian, interleaved '
                'R, G, B and A (R, G, B for a layer without transparency), computed in memory: '
                'the PSB route writes no layer TIFF files')


class PackageLayer:
    """One recipe row and its uint16 (H, W) planes; a grey layer shares one plane for R, G and B."""

    def __init__(self, record, rgb, alpha=None, mask=None):
        self.record = record
        self.rgb = tuple(rgb)
        self.alpha = alpha
        self.mask = mask

    def sha256(self):
        """Digest of the pixels (see LAYER_SHA256), by blocks of rows."""
        planes = self.rgb if self.alpha is None else (*self.rgb, self.alpha)
        digest = hashlib.sha256()
        for first in range(0, planes[0].shape[0], 256):
            block = np.dstack([plane[first:first+256] for plane in planes])
            digest.update(np.ascontiguousarray(block, dtype='<u2'))
        return digest.hexdigest()


class LayerPackage:
    """Layers, merged RGB, colour-correction input and recipe of one export, in memory.

    ``combined`` is the merged uint16 RGB of the PSB. ``corona_combined`` (only
    with prominences) and ``valid`` feed the optional Color Correction, as the
    CORONA_COMBINED and VALID files of a TIFF package do.
    """

    def __init__(self, shape, layers, combined, recipe, *, corona_combined=None, valid=None):
        self.shape = tuple(shape)
        self.layers = layers
        self.combined = combined
        self.corona_combined = corona_combined
        self.valid = valid
        self.recipe = recipe


def _inputs(source, params, rgb):
    source = np.asarray(source)
    if source.ndim != 2 or not source.size:
        raise ValueError('Layer export requires a nonempty monochrome canvas')
    valid = np.isfinite(source)
    mask = params.get('valid_mask')
    if mask is not None:
        mask = np.asarray(mask, dtype=bool)
        if mask.shape != source.shape:
            raise ValueError('Layer validity must match the source canvas')
        valid &= mask
    if rgb is not None:
        rgb = np.asarray(rgb)
        if rgb.shape != (*source.shape, 3) or not np.isfinite(rgb[valid]).all():
            raise ValueError('RGB must match luminance and its observed-data mask')
    return source, valid, rgb


def _produce_layers(worker, source, valid, params, display, rgb, colour_report, prominences, emit,
                    base_colour=None):
    """Compute every layer in Photoshop order and pass it to ``emit``.

    ``source``, ``valid`` and ``rgb`` come from _inputs. ``emit(name,
    rgb_planes, alpha, record_fields, mask=None)`` stores one layer.
    ``base_colour`` may carry the (base, colour) pair of presentation.psb_base
    for the same source, parameters and display, so a caller that needs it too
    computes it once. Returns the final display settings and parameters, the
    merged float composite and, with prominences, the corona composite before
    them.
    """
    from .presentation import quantize_u16
    from .presentation import psb_presentation_settings, psb_base
    if display.get('mode') != 'ael_presentation':
        display = psb_presentation_settings(source, params.get('valid_mask'), rgb=rgb, params=params)
        base_colour = None
    params = {k:v for k,v in params.items() if k != 'layer_display'}
    engine=engine_for(worker)
    def write(label,image,alpha,mode,amount,**metadata):
        name=f'{label}_{mode.replace(" ","")}'
        emit(name,(image,image,image),alpha,dict(mode=mode,opacity=amount,
             opacity_255=round(amount*255),visible=amount>0,**metadata))
    reference = source if rgb is None else rgb
    finite = np.isfinite(reference) & (valid if reference.ndim == 2 else valid[..., None])
    reference_scale = float(np.max(reference, where=finite, initial=0.)) / .98 or 1.
    reference_u16 = quantize_u16(np.where(finite, reference / reference_scale, 0.))
    reference_planes = ((reference_u16,)*3 if reference_u16.ndim == 2
                        else tuple(reference_u16[..., c] for c in range(3)))
    emit('LINEAR_REFERENCE_Normal', reference_planes,
         (finite if finite.ndim == 2 else finite.all(axis=-1)).astype(np.uint16)*65535,
         dict(name='Scaled input preview (16-bit)',
              filter='linear_reference', mode='Normal', opacity=1., opacity_255=255,
              visible=False, reference_scale=reference_scale,
              role='Quantized viewing reference only; use separate working float32 sources for linear data',
              negative_values='clipped in 16-bit reference; float source retains signed values',
              colour_calibration=colour_report))
    base, color = base_colour if base_colour is not None else psb_base(source,params,display,rgb)
    observed_alpha = valid.astype(np.uint16)*65535
    write('BASE',quantize_u16(base),observed_alpha,
          'Normal',1.,filter='base',name='Display base')
    engine.prepare(worker,source,params)
    for name,variant,p,enabled in requests(params):
        layer=engine.layer(worker,source,p,name,variant)
        amount=round(opacity(name,p,enabled)*float(display.get('blend',1))*255)/255
        write(LABELS.get(variant,name.upper()),layer['image'],layer['alpha'],layer['mode'],amount,
              filter=name,variant=variant,normalization=layer['mapping'],
              operator_strength=p.get(name+'_str',100))
    timer=time.perf_counter()
    combined=engine.render(worker,source,params,display,base=base)
    if rgb is not None:
        color_u16=quantize_u16(color)
        emit('RGB_Color',tuple(color_u16[..., c] for c in range(3)),observed_alpha,
             dict(filter='colour',mode='Color',opacity=1.,opacity_255=255,visible=True))
        combined=set_luminosity(color,combined)
    from .presentation_edges import finish_presentation, EDGE_WIDTH_NATIVE_PX
    edge=engine.edge_alpha(source,params)
    if edge is not None:
        zeros=np.zeros(edge.shape,np.uint16)
        emit('EDGE_ANTIALIAS_Normal',(zeros,)*3,edge,
             dict(name='Edge Antialias',filter='edge_antialias',mode='Normal',opacity=1.,opacity_255=255,
                  visible=True,width_native_px=EDGE_WIDTH_NATIVE_PX,
                  role='Display-only lunar/missing boundary fade to opaque black'))
    combined=finish_presentation(combined,edge)
    if combined.ndim==2:
        combined=np.repeat(combined[...,None],3,axis=-1)
    corona=None
    if prominences is not None:
        from .prominences import composite_prominences
        image, mask, settings = prominences
        if image.shape != (*source.shape, 3) or mask.shape != source.shape:
            raise ValueError('Prominences must match the original canvas')
        corona=combined
        emit('PROMINENCES_Normal',tuple(image[..., c] for c in range(3)),None,
             dict(name='Prominences and chromosphere',filter='prominences',mode='Normal',opacity=1.,
                  opacity_255=255,visible=True,mask_file='PROMINENCES_MASK.tif',normalization=settings),
             mask=mask)
        combined=composite_prominences(combined,image,mask)
    print(f'[LAYERS: COMPOSITE] Done in {time.perf_counter()-timer:.3f}s')
    return display, params, combined, corona


def _recipe(source, records, params, display, original_path, colour_report, prominences):
    recipe=dict(shape=list(source.shape),layers=records,combined='REFERENCE_COMBINED.tif',
                parameters=recipe_parameters(params),display=display,source=original_path,
                colour_calibration=colour_report,role='Independent linear-input layers; display composition',
                alpha='Original validity retained separately; editable Edge Antialias adds display-only black fade',
                missing_samples='Numerical files store zero; VALID marks unobserved samples')
    if prominences is not None:
        recipe['corona_combined']='CORONA_COMBINED.tif'
    return recipe


def build_layer_package(worker, source, params, display, original_path, rgb=None, colour_report=None,
                        prominences=None, base_colour=None):
    """Every layer of the export in memory, in Photoshop order, with the recipe of the TIFF route.

    For core.psb_export.export_psb_layers. The rows name the files a TIFF
    package would have; their sha256 is added by the PSB writer (LAYER_SHA256).
    """
    from .presentation import quantize_u16
    started=time.perf_counter()
    source,valid,rgb=_inputs(source,params,rgb)
    layers=[]
    def keep(name,planes,alpha,fields,mask=None):
        check_cancelled()
        row=dict(order=len(layers)+1,file=f'{len(layers)+1:02d}_{name}.tif',**fields)
        layers.append(PackageLayer(row,planes,alpha,mask))
    display,params,combined,corona=_produce_layers(worker,source,valid,params,display,rgb,colour_report,
                                                   prominences,keep,base_colour)
    recipe=_recipe(source,[layer.record for layer in layers],params,display,original_path,
                   colour_report,prominences)
    package=LayerPackage(source.shape,layers,quantize_u16(combined),recipe,
                         corona_combined=None if corona is None else quantize_u16(corona),valid=valid)
    print(f'[LAYERS PACKAGE: IN MEMORY] Done in {time.perf_counter()-started:.3f}s; {len(layers)} layers')
    return package


def export_layered_package(worker, source, params, display, original_path, destination,
                           rgb=None, colour_report=None, prominences=None, base_colour=None):
    from .layer_export import to_u16, photoshop_loader
    from .color_correction import srgb_profile
    profile=srgb_profile()
    source,valid,rgb=_inputs(source,params,rgb)
    if display.get('mode') != 'ael_presentation':
        # Before the destination checks, as always: a failure here creates no folder.
        from .presentation import psb_presentation_settings
        display = psb_presentation_settings(source, params.get('valid_mask'), rgb=rgb, params=params)
        base_colour = None
    destination=Path(destination)
    if destination.exists():
        raise FileExistsError(destination)
    destination.parent.mkdir(parents=True,exist_ok=True)
    stage=Path(tempfile.mkdtemp(prefix='.layers-',dir=destination.parent))
    records=[]
    started=time.perf_counter()
    def write(name,planes,alpha,fields,mask=None):
        check_cancelled()
        timer=time.perf_counter()
        order=len(records)+1
        filename=f'{order:02d}_{name}.tif'
        # Every display layer carries the sRGB profile; the scaled input preview does not.
        icc=None if fields.get('filter')=='linear_reference' else profile
        if alpha is None:
            tifffile.imwrite(stage/filename,np.dstack(planes),photometric='rgb',compression='zlib',metadata=None,
                             iccprofile=icc)
        else:
            tifffile.imwrite(stage/filename,np.dstack([*planes,alpha]),photometric='rgb',extrasamples=['unassalpha'],
                             compression='zlib',metadata=None,iccprofile=icc)
        if mask is not None:
            tifffile.imwrite(stage/fields['mask_file'],mask,compression='zlib',metadata=None)
        records.append(dict(order=order,file=filename,**fields))
        print(f'[LAYER {name}: TIFF WRITE] Done in {time.perf_counter()-timer:.3f}s')
    try:
        display,params,combined,corona=_produce_layers(worker,source,valid,params,display,rgb,colour_report,
                                                       prominences,write,base_colour)
        timer=time.perf_counter()
        if corona is not None:
            tifffile.imwrite(stage/'CORONA_COMBINED.tif',to_u16(corona),photometric='rgb',compression='zlib',metadata=None,
                             iccprofile=profile)
        recipe=_recipe(source,records,params,display,original_path,colour_report,prominences)
        combined_file=recipe['combined']
        tifffile.imwrite(stage/combined_file,to_u16(combined),photometric='rgb',compression='zlib',metadata=None,
                         iccprofile=profile)
        tifffile.imwrite(stage/'SOURCE_float32.tif',zero_missing(source,valid).astype(np.float32),compression='zlib')
        tifffile.imwrite(stage/'VALID.tif',valid.astype(np.uint8)*255,compression='zlib')
        from .statistics_support import statistics_support
        tifffile.imwrite(stage/'STATISTICS_SUPPORT.tif',statistics_support(source,params,valid).astype(np.uint8)*255,compression='zlib')
        print(f'[LAYERS: COMPOSITE/SOURCE WRITE] Done in {time.perf_counter()-timer:.3f}s')
        for row in records:
            with (stage/row['file']).open('rb') as stream:
                row['sha256']=hashlib.file_digest(stream,'sha256').hexdigest()
        (stage/'recipe.json').write_text(json.dumps(recipe,indent=2),encoding='utf-8')
        background_file='00_BACKGROUND_Normal.tif'
        tifffile.imwrite(stage/background_file,np.zeros((*source.shape,3),np.uint16),
                         photometric='rgb',compression='zlib',metadata=None,iccprofile=profile)
        loader_records=[dict(file=background_file,mode='Normal',opacity_255=255,visible=True),*records]
        (stage/'Load_layers_Photoshop.jsx').write_text(photoshop_loader(loader_records),encoding='utf-8')
        (stage/'Layers.md').write_text('# Independent filter layers\n\nLoad with File > Scripts > Browse > Load_layers_Photoshop.jsx.\n'
            'All filters start from the shared linear working input (including optional background equalization; see recipe parameters). Larson–Sekanina exposes Gain (0–200%); adaptive ACHF and tangential detail have operator-specific gains. Other filters have no Strength control. Opacity controls blending.\n'
            'The base uses the PSB Asinh-10 presentation with automatic scale plus manual EV exposure, regardless of the preview toggle. Main TIFF/JPEG share this presented composition and carry sRGB profiles. The hidden scaled input preview is quantized, not a linear master; use the companion float32 working sources for numerical data.\n'
            'Edge Antialias is an editable display-only black overlay at lunar/missing boundaries.\n'
            'Numerical source files store missing samples as zero; VALID preserves their identity.\n',encoding='utf-8')
        check_cancelled()
        stage.rename(destination)
        print(f'[LAYERS PACKAGE: TOTAL] Done in {time.perf_counter()-started:.3f}s; {len(records)} layers')
        return destination
    except Exception:
        shutil.rmtree(stage)
        raise
