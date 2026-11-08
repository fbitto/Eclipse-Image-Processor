"""Full-native follow-up to diagnose_nafe_limb.py; read-only source, new outputs.

Run with SOURCE.fits and the existing diagnostic output directory. Refuses to
replace an earlier full-native run. Verifies ROI agreement and source integrity.
"""
import os,sys,time,json,hashlib
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ.setdefault(key,'1')
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt
from gui.background_tasks import load_source
from gui.app import EclipseProcessorApp
from core.statistics_support import statistics_support
from core.ael_nafe import nafe_layer
from core.parallelism import filter_budget
from core.progress import progress_scope
from core.presentation import psb_presentation_settings,psb_base
from core.layer_engine import blend
import argparse
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('source',type=Path);parser.add_argument('output',type=Path)
args=parser.parse_args();source=args.source;out=args.output
if not (out/'report.json').is_file():raise FileNotFoundError('Run diagnose_nafe_limb.py first')
if (out/'full-native.npz').exists():raise FileExistsError(out/'full-native.npz')
with source.open('rb') as f:before=hashlib.file_digest(f,'sha256').hexdigest()
if before != '33ff81c882a0e5e98771b8c00f627af5860b56464798e16dc38e75122b45a005':
    raise ValueError('This case-specific diagnostic requires the approved e1c3c474 master')
loaded=load_source(str(source),None,EclipseProcessorApp.detect_lunar_limb)
a=loaded['full'];valid=np.isfinite(a);p=dict(zip(('sx','sy','sr'),loaded['circle']));p['statistics_exclude_lunar']=True
m=statistics_support(a,p,valid);start=time.monotonic();last=[-1]
def progress(done,total,detail):
 bucket=int(10*done/total)
 if bucket>last[0]:print(f'{100*done/total:.0f}% {detail}',flush=True);last[0]=bucket
with filter_budget(8),progress_scope(progress):q,info=nafe_layer(a,p,m,targets=valid)
seconds=time.monotonic()-start
np.savez_compressed(out/'full-native.npz',E=q,supported=np.isfinite(q))
for name,values in [('full-native-E',q)]:
 Image.fromarray((np.nan_to_num(np.clip(values,0,1))*255).astype(np.uint8)).save(out/(name+'.png'))
settings=psb_presentation_settings(a,params=p);base,_=psb_base(a,p,settings);base=np.nan_to_num(base)
finite=np.isfinite(q);layer=np.where(finite,q,.5)
for amount in (.4,1.):
 final=blend(base,layer,finite.astype(float),'Overlay',amount)
 Image.fromarray((np.clip(final,0,1)*255).astype(np.uint8)).save(out/f'full-native-blend{round(amount*100)}.png')
y,x=np.ogrid[:a.shape[0],:a.shape[1]];region=valid&(np.hypot(x-p['sx'],y-p['sy'])<p['sr']+200)
d=distance_transform_edt(valid)
bands=[]
for lo,hi in ((0,5),(5,15),(15,30),(30,60),(60,120),(120,180)):
 mask=region&(d>lo)&(d<=hi)&finite
 bands.append(dict(band=f'{lo}-{hi}',pixels=int(mask.sum()),E_median=float(np.median(q[mask]))))
report=json.loads((out/'report.json').read_text());left,top=report['native_crop_origin']
with np.load(out/'native-default.npz') as f:roi=f['E']
actual=q[top:top+roi.shape[0],left:left+roi.shape[1]];ry,rx=np.indices(roi.shape);central=np.hypot(rx-600,ry-600)<450
compare=central&np.isfinite(actual)&np.isfinite(roi)
maximum=float(np.max(abs(actual[compare]-roi[compare])))
assert maximum<.01,maximum
with source.open('rb') as f:after=hashlib.file_digest(f,'sha256').hexdigest()
assert after==before
result=dict(shape=list(a.shape),seconds=seconds,operator=info,bands=bands,unsupported_near_limb=int((region&~finite).sum()),
 native_roi_max_absolute_difference=maximum,source_sha256=after,source_unchanged=True,
 corner_E_medians=[float(np.nanmedian(q[s])) for s in ((slice(0,64),slice(0,64)),(slice(0,64),slice(-64,None)),(slice(-64,None),slice(0,64)),(slice(-64,None),slice(-64,None)))])
(out/'full-native-report.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True)
