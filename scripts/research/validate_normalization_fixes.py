"""Qualification of normalization repairs against the retained study controls."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ.setdefault(key,'1')
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import argparse,copy,json,sys,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import numpy as np,tifffile
from inspect_filter_defaults import modes,parameters,calculate,save_case,write


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--study',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();study=args.study;root=args.output;root.mkdir(exist_ok=True)
    raw=json.load(open(study/'00-Test-Manifest-and-Current-Defaults/current-unprepared-numerical-defaults.json'));raw.update(sx=128.,sy=128.,sr=30.,fnrgf_rmax=50)
    scenes={p.stem.removeprefix('input-'):tifffile.imread(p) for p in (study/'02-Synthetic-Known-Truth-Controls').glob('input-*.tif')}
    y,x=np.indices((256,256));r=np.hypot(x-128,y-128);signal=.012*np.cos(12*np.arctan2(y-128,x-128))*np.exp(-((r-65)/12)**2)
    rows=[];errors=[]
    for index,mode in enumerate(modes(),1):
        if not (mode[1] in ('fnrgf','tangential','achf')):continue
        outputs={}
        for scene,a in scenes.items():
            folder=root/f'{index:02d}-{mode[0]}'/scene
            try:
                p=parameters(raw,mode,a.shape,a.shape,a.shape,dict(normalization_mode='revised'))
                p['layer_display']=dict(normalization_range=[float(np.nanmin(a)),float(np.nanmax(a))])
                layer,operator,seconds,notes=calculate(a,p,mode)
                info,q,alpha,_=save_case(folder,a,p,mode,layer,operator,np.nan_to_num(a/np.nanmax(a)),seconds,notes,1.,arrays=True)
                outputs[scene]=(q,alpha,info)
            except Exception as exc:
                folder.mkdir(parents=True,exist_ok=True);(folder/'FAILED-traceback.txt').write_text(traceback.format_exc());errors.append([mode[0],scene,str(exc)])
        if all(key in outputs for key in ('radial_null','noisy_base','injected_faint_detail')):
            before,ba,_=outputs['noisy_base'];after,aa,_=outputs['injected_faint_detail'];mask=(ba>.99)&(aa>.99)&(r>48)&(r<82)&(abs(signal)>.006)
            delta=(after-before)[mask];truth=signal[mask]
            rows.append(dict(mode=mode[0],null_band=outputs['radial_null'][2]['encoded']['worst_sector_band_RMS'],negative_fraction=float(np.mean(delta*truth<0)),zero_fraction=float(np.mean(delta==0)),correlation=float(np.corrcoef(delta,truth)[0,1]) if np.std(delta)>0 else 0.,response_RMS=float(np.sqrt(np.mean(delta**2)))))
            write(root/'revised-quality-measurements.json',rows);print(rows[-1],flush=True)
    write(root/'execution-errors.json',errors);print('ERRORS',errors,flush=True)

if __name__=='__main__':main()
