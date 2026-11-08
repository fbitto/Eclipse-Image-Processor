"""Research-only comparison of upstream measured-noise WOW; never changes the app."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ.setdefault(key,'1')
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import argparse,json,time,sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import numpy as np,tifffile
from inspect_filter_defaults import save_case,write,digest,EXPECTED
from gui.background_tasks import load_source
from gui.app import EclipseProcessorApp
from core.pipeline import prepare_parameters
from core.statistics_support import statistics_support
from core.presentation import psb_presentation_settings,psb_base


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();root=args.output
    plugin=Path('/Users/franciscobitto/.codex/plugins/cache/pere-guerra-eclipse/agentic-eclipse-library/1.1.6')
    sys.path.insert(0,str(plugin/'runtime'))
    import ael
    from ael import filterbank
    from ael.geometry import EclipseGeometry
    assert ael.__version__=='1.4.2' and Path(ael.__file__).is_relative_to(plugin/'runtime')
    meta=json.load(open(root/'00-Test-Manifest-and-Current-Defaults/input-and-environment.json'));raw=json.load(open(root/'00-Test-Manifest-and-Current-Defaults/current-unprepared-numerical-defaults.json'))
    assert digest(meta['source'])==EXPECTED
    loaded=load_source(meta['source'],None,EclipseProcessorApp.detect_lunar_limb);full=loaded['full'];preview=loaded['preview'];display=psb_presentation_settings(full,params=raw)
    parent=root/'04a-Upstream-AEL-Measured-Noise-WOW-Alternative';parent.mkdir(exist_ok=True)
    mode=('AEL-1.4.2-measured-noise-WOW-research-only','wow',None,{})
    inputs=root/'04-Dominant-Control-Follow-Up/WOW-Supported-Scale-Held-Out-Retest/Held-Out-Test-Inputs'
    rows=[]
    for label,a in [(p.stem,tifffile.imread(p)) for p in sorted(inputs.glob('*.tif'))]+[('real-master-preview',preview),('real-master-native',full)]:
        synthetic=not label.startswith('real-')
        p=dict(raw,sx=256.,sy=256.,sr=30.) if synthetic else prepare_parameters(raw,full.shape,preview.shape,a.shape)
        mask=statistics_support(a,p,np.isfinite(a));geometry=EclipseGeometry(a.shape,(p['sx'],p['sy']),p['sr'])
        captured={};original=filterbank.wow_measured
        def capture(*args,**kwargs):
            result=original(*args,**kwargs);captured['detail']=result[0];return result
        start=time.monotonic()
        with patch.object(filterbank,'wow_measured',side_effect=capture):q,blend_mode,mapping=filterbank.make_filter('wow',a,mask,geometry)
        elapsed=time.monotonic()-start
        alpha=mask&np.isfinite(q)
        layer=dict(image=np.uint16(np.clip(np.nan_to_num(q,nan=.5),0,1)*65535),alpha=np.uint16(alpha)*65535,mode='Overlay',mapping=dict(mapping,research_only=True,upstream_runtime='1.4.2',comparison_note='upstream measured-noise WOW default six scales, distinct from app guided edge-aware WOW'))
        base=np.nan_to_num(a/np.nanmax(a)) if synthetic else np.nan_to_num(psb_base(a,p,display)[0])
        info,_,_,_=save_case(parent/label,a,p,mode,layer,captured['detail'],base,elapsed,[],1. if synthetic else p['nrgf_scale'],arrays=True)
        rows.append(dict(scene=label,seconds=elapsed,measurements=str((parent/label/'measurements-and-exact-parameters.json').relative_to(root))))
        write(parent/'alternative-index.json',rows);print('UPSTREAM ALTERNATIVE',label,elapsed,flush=True)
    assert digest(meta['source'])==EXPECTED
    write(parent/'completion.json',dict(completed=True,source_hash_unchanged=True,scope='research alternative; not added to the app'))

if __name__=='__main__':main()
