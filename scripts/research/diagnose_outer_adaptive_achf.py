"""Research-only pair-threshold control for weak adaptive ACHF response at 6 radii."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ.setdefault(key,'1')
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import argparse,json,sys,copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import numpy as np,tifffile
from inspect_filter_defaults import modes,parameters,calculate,write


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--study',type=Path,required=True);parser.add_argument('--linear-reference',action='store_true');args=parser.parse_args();study=args.study;root=study/'09-Outer-Detail-Contrast-Investigation/Adaptive-ACHF-Expected-Linear-Response-Control' if args.linear_reference else study/'09-Outer-Detail-Contrast-Investigation/Adaptive-ACHF-Pair-Rejection-Causal-Control';root.mkdir(exist_ok=False)
    raw=json.load(open(study/'00-Test-Manifest-and-Current-Defaults/current-unprepared-numerical-defaults.json'));raw.update(sx=256.,sy=256.,sr=30.)
    source=study/'09-Outer-Detail-Contrast-Investigation/Synthetic-Inputs'
    before=tifffile.imread(source/'noisy.tif');after=tifffile.imread(source/'injected-6R.tif')
    y,x=np.indices(before.shape);r=np.hypot(x-256,y-256);truth=.003*np.cos(12*np.arctan2(y-256,x-256))*np.exp(-((r-180)/9)**2)
    mode=next(m for m in modes() if m[0]=='ACHF-adaptive-circular');rows=[]
    from core.filters import adaptive_circular_highpass
    valid=np.isfinite(before)&(r>30)
    labels=(r<=30).astype(np.uint8)
    expected=adaptive_circular_highpass(np.where(np.isfinite(before),truth,0),raw['achf_kernel']/10,2.,gain=1.,background=0.,regions=labels,threshold_mode='relative',sample_valid=valid)
    tifffile.imwrite(root/'known-linear-kernel-response.tif',expected)
    for threshold in (10,20,200):
        outputs=[]
        for label,a in [('before',before),('after',after)]:
            p=parameters(raw,mode,a.shape,a.shape,a.shape,dict(normalization_mode='revised',achf_threshold=threshold));p['layer_display']=dict(normalization_range=[float(np.nanmin(a)),float(np.nanmax(a))])
            layer,operator,_,notes=calculate(a,p,mode);outputs.append((operator,layer))
            tifffile.imwrite(root/f'threshold-{threshold}-{label}-raw-detail.tif',operator.astype(np.float32),compression='zlib')
        b,bl=outputs[0];a,al=outputs[1];mask=(bl['alpha']>64879)&(al['alpha']>64879)&(abs(truth)>.0015)&np.isfinite(b)&np.isfinite(a)
        raw_delta=(a-b)[mask];encoded_delta=(al['image'].astype(float)-bl['image'])[mask];signal=truth[mask]
        rows.append(dict(relative_pair_threshold_percent=threshold,raw_negative_fraction=float(np.mean(raw_delta*signal<0)),raw_zero_fraction=float(np.mean(raw_delta==0)),encoded_negative_fraction=float(np.mean(encoded_delta*signal<0)),encoded_zero_fraction=float(np.mean(encoded_delta==0)),raw_correlation=float(np.corrcoef(raw_delta,signal)[0,1]),encoded_correlation=float(np.corrcoef(encoded_delta,signal)[0,1])))
        if args.linear_reference:
            e=expected[mask];stable=abs(e)>1e-3*np.max(abs(e))
            rows[-1].update(raw_correlation_with_expected_kernel=float(np.corrcoef(raw_delta,e)[0,1]),raw_wrong_sign_against_expected_kernel=float(np.mean(raw_delta[stable]*e[stable]<0)),expected_kernel_negative_fraction_against_input=float(np.mean(e*signal<0)))
        write(root/'pair-threshold-causal-results.json',rows);print(rows[-1],flush=True)

if __name__=='__main__':main()
