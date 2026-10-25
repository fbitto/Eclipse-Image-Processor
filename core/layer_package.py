"""Write the same cached layers and composition used by the GUI."""
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
from .layer_engine import engine_for, requests, opacity, LABELS, colour_display, display_base


def export_layered_package(worker, source, params, display, original_path, destination,
                           rgb=None, colour_report=None):
    from .layer_export import to_u16, photoshop_loader, write_edge_layer
    destination=Path(destination)
    if destination.exists():
        raise FileExistsError(destination)
    destination.parent.mkdir(parents=True,exist_ok=True)
    stage=Path(tempfile.mkdtemp(prefix='.layers-',dir=destination.parent))
    engine=engine_for(worker)
    valid=np.isfinite(source) & params.get('valid_mask',True)
    records=[]
    started=time.perf_counter()
    def write(label,image,alpha,mode,amount,**metadata):
        check_cancelled()
        timer=time.perf_counter()
        order=len(records)+1
        filename=f'{order:02d}_{label}_{mode.replace(" ","")}.tif'
        rgba=np.dstack([image,image,image,alpha])
        tifffile.imwrite(stage/filename,rgba,photometric='rgb',extrasamples=['unassalpha'],
                         compression='zlib',metadata=None)
        records.append(dict(order=order,file=filename,mode=mode,opacity=amount,
                            opacity_255=round(amount*255),visible=amount>0,**metadata))
        print(f'[LAYER {label}: TIFF WRITE] Done in {time.perf_counter()-timer:.3f}s')
    try:
        write('BASE',display_base(source,params,display),valid.astype(np.uint16)*65535,
              'Normal',1.,filter='base')
        engine.prepare(worker,source,params,include_all=False)
        for name,variant,p,enabled in requests(params,include_all=False):
            layer=engine.layer(worker,source,p,name,variant)
            amount=round(opacity(name,p,enabled)*float(display.get('blend',1))*255)/255
            write(LABELS.get(variant,name.upper()),layer['image'],layer['alpha'],layer['mode'],amount,
                  filter=name,variant=variant,normalization=layer['mapping'],
                  operator_strength=p.get(name+'_str',100))
        timer=time.perf_counter()
        combined=engine.render(worker,source,params,display)
        if rgb is not None:
            color=colour_display(rgb,source,display)
            order=len(records)+1
            filename=f'{order:02d}_RGB_Color.tif'
            tifffile.imwrite(stage/filename,np.dstack([to_u16(color),valid.astype(np.uint16)*65535]),
                             photometric='rgb',extrasamples=['unassalpha'],compression='zlib',metadata=None)
            records.append(dict(order=order,file=filename,filter='colour',mode='Color',
                                opacity=1.,opacity_255=255,visible=True))
            combined=set_luminosity(color,combined)
        from .presentation_edges import finish_presentation
        edge=engine.edge_alpha(source,params)
        write_edge_layer(stage,records,edge)
        combined=finish_presentation(combined,edge)
        if combined.ndim==2:
            combined=np.repeat(combined[...,None],3,axis=-1)
        combined_file='REFERENCE_COMBINED.tif'
        tifffile.imwrite(stage/combined_file,to_u16(combined),photometric='rgb',compression='zlib',metadata=None)
        tifffile.imwrite(stage/'SOURCE_float32.tif',zero_missing(source,valid).astype(np.float32),compression='zlib')
        tifffile.imwrite(stage/'VALID.tif',valid.astype(np.uint8)*255,compression='zlib')
        from .statistics_support import statistics_support
        tifffile.imwrite(stage/'STATISTICS_SUPPORT.tif',statistics_support(source,params,valid).astype(np.uint8)*255,compression='zlib')
        print(f'[LAYERS: COMPOSITE/SOURCE WRITE] Done in {time.perf_counter()-timer:.3f}s')
        for row in records:
            with (stage/row['file']).open('rb') as stream:
                row['sha256']=hashlib.file_digest(stream,'sha256').hexdigest()
        recipe=dict(shape=list(source.shape),layers=records,combined=combined_file,
                    parameters=recipe_parameters(params),display=display,source=original_path,
                    colour_calibration=colour_report,role='Independent linear-input layers; display composition',
                    alpha='Original validity retained separately; editable Edge Antialias adds display-only black fade',
                    missing_samples='Numerical files store zero; VALID marks unobserved samples')
        (stage/'recipe.json').write_text(json.dumps(recipe,indent=2),encoding='utf-8')
        background_file='00_BACKGROUND_Normal.tif'
        tifffile.imwrite(stage/background_file,np.zeros((*source.shape,3),np.uint16),
                         photometric='rgb',compression='zlib',metadata=None)
        loader_records=[dict(file=background_file,mode='Normal',opacity_255=255,visible=True),*records]
        (stage/'Load_layers_Photoshop.jsx').write_text(photoshop_loader(loader_records),encoding='utf-8')
        (stage/'Layers.md').write_text('# Independent filter layers\n\nLoad with File > Scripts > Browse > Load_layers_Photoshop.jsx.\n'
            'All filters start from the original linear input. Strength changes layer contrast; opacity controls blending.\n'
            'The base is stretched once. No second stretch is applied to the composition.\n'
            'Edge Antialias is an editable display-only black overlay at lunar/missing boundaries.\n'
            'Numerical source files store missing samples as zero; VALID preserves their identity.\n',encoding='utf-8')
        check_cancelled()
        stage.rename(destination)
        print(f'[LAYERS PACKAGE: TOTAL] Done in {time.perf_counter()-started:.3f}s; {len(records)} layers')
        return destination
    except Exception:
        shutil.rmtree(stage)
        raise
