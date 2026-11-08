"""Read-only real-image check of today's corona warmth, not future controls.

Usage: python tests/proposed/check_sky_colour_baseline.py INPUT.fits REPORT.json
Writes only the explicitly supplied report; no image, settings or app changes.
"""
import os
for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ.setdefault(name,'1')
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import numpy as np
from gui.background_tasks import load_source
from core.colour import set_luminosity
from core.image_data import resize_observed
from core.pipeline import prepare_parameters
from core.presentation import psb_presentation_settings, psb_base
from core.warmth import warmth_layer, blend_warmth


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    source=Path(sys.argv[1]);report_path=Path(sys.argv[2])
    if report_path.exists():raise FileExistsError(report_path)
    before=digest(source)
    # Previously auto-detected reference geometry; this is not independent astrometry.
    geometry=(2975,1660,272)
    loaded=load_source(str(source),geometry,None)
    assert loaded['rgb'] is not None,'RGB fixture required'
    full=loaded['full'];preview=loaded['preview'];rgb=loaded['rgb']
    params=dict(zip(('sx','sy','sr'),geometry))
    display=psb_presentation_settings(full,np.isfinite(full),rgb=rgb,params=params)
    reduced=np.stack([resize_observed(rgb[...,c],(preview.shape[1],preview.shape[0])) for c in range(3)],axis=-1)
    p=prepare_parameters(params,full.shape,preview.shape,preview.shape)
    base,colour=psb_base(preview,p,display,reduced)
    presented=set_luminosity(colour,base)
    original=presented.copy()
    bg=dict(geometry=geometry,radius=6.,grid=16,points=None)
    valid=np.isfinite(preview)
    layer=warmth_layer(presented,1.,bg,native_shape=full.shape,valid=valid)
    assert warmth_layer(presented,0.,bg,native_shape=full.shape,valid=valid) is None
    assert blend_warmth(presented,None) is presented
    output=blend_warmth(presented,layer)
    np.testing.assert_array_equal(presented,original)
    np.testing.assert_array_equal(np.isfinite(output),np.isfinite(original))
    assert np.isfinite(output[valid]).all()
    alpha=np.zeros(preview.shape) if layer is None else layer[1]/65535.
    assert (alpha[~valid]==0).all()
    luminance_error=float(np.max(abs((output @ [.30,.59,.11]-original @ [.30,.59,.11])[valid])))
    assert luminance_error<=3/65535,luminance_error
    after=digest(source)
    assert before==after,'Source bytes changed'
    report=dict(scope='Current corona-warmth baseline only; new controls not implemented',
        source=str(source),sha256_before=before,sha256_after=after,
        native_shape=list(full.shape),preview_shape=list(preview.shape),
        reference_geometry=list(geometry),sky_sampling=bg,
        filters='None; PSB presentation base with source colour, no calibration',
        supported_warmth_layer=layer is not None,
        coverage_fraction_above_half=float(np.mean(alpha[valid]>.5)),
        exact_unmodified_fraction=float(np.mean(alpha[valid]==0)),
        max_luminance_error=luminance_error,
        green_excess_sample_mean=float(np.mean((presented[...,1]-(presented[...,0]+presented[...,2])/2)[valid])),
        checks=['zero bypass','input immutability','finite/missing support','luminance tolerance','source SHA-256 unchanged'])
    report_path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
