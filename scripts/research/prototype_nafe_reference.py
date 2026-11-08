"""Experimental NAFE reference-response subtraction; not a production filter.

A smooth radial model is evaluated only on observed support, passed through the
same fuzzy CDF, then its response is subtracted before Overlay encoding. The
original source and its missing pixels are never replaced by the model.
"""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ.setdefault(key,'1')
import argparse
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import numpy as np
from PIL import Image,ImageDraw,ImageOps
from scipy.ndimage import distance_transform_edt
from core.ael_achf import radial_log_residual
from core.ael_nafe import nafe
from core.statistics_support import statistics_support
from core.pipeline import prepare_parameters
from core.presentation import psb_presentation_settings,psb_base
from core.layer_engine import blend
from core.parallelism import filter_budget
from gui.background_tasks import load_source
from gui.app import EclipseProcessorApp


def reference_response(a,samples,targets,sigma,cx,cy,radius,n,scale=1.):
    y,x=np.ogrid[:a.shape[0],:a.shape[1]];r=np.hypot(x-cx,y-cy).astype(np.float32)
    low=float(np.min(a[samples]));unit=max(float(np.ptp(a[samples])),float(sigma))
    shifted=np.where(samples,(a.astype(float)-low+sigma)/unit,np.nan).astype(np.float32)
    residual,fit=radial_log_residual(shifted,samples,SimpleNamespace(sun_radius_px=radius,radius_map=lambda:r))
    supported=samples&np.isfinite(residual)
    model=np.full(a.shape,np.nan,np.float32)
    model[supported]=(np.exp(np.log(shifted[supported]).astype(float)-residual[supported])*unit+low-sigma).astype(np.float32)
    query=targets&~supported
    if query.any():
        order=np.argsort(r[supported]);rr=r[supported][order];values=model[supported][order]
        # Extrapolate the diagnostic model, never observed input, to existing query targets only.
        model[query]=np.interp(r[query],rr,values).astype(np.float32)
    expected,info=nafe(model,samples,sigma,n=n,target_valid=targets,kernel_scale=scale)
    return expected,dict(profile=fit,operator=info)


def corrected(a,samples,targets,sigma,cx,cy,radius,n,scale=1.,actual=None,soft=False):
    if actual is None:actual,_=nafe(a,samples,sigma,n=n,target_valid=targets,kernel_scale=scale)
    response,info=reference_response(a,samples,targets,sigma,cx,cy,radius,n,scale)
    signed=.5+actual-response
    good=np.isfinite(actual)&np.isfinite(response)
    info['raw_difference_outside_unit_fraction']=float(np.mean(((signed<0)|(signed>1))[good]))
    info['clipped_fraction']=0. if soft else info['raw_difference_outside_unit_fraction']
    info['encoding']='unit-slope tanh of signed CDF difference' if soft else 'clipped signed CDF difference'
    result=.5+.5*np.tanh(2*(actual-response)) if soft else np.clip(signed,0,1)
    return result,actual,response,info


def save(path,a):
    Image.fromarray((np.nan_to_num(np.clip(a,0,1))*255).astype(np.uint8)).save(path)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('source',type=Path);parser.add_argument('output',type=Path)
    parser.add_argument('--soft-encoding',action='store_true',help='Bound signed contrast smoothly, preserving its slope at zero')
    args=parser.parse_args()
    with args.source.open('rb') as f:before=hashlib.file_digest(f,'sha256').hexdigest()
    if before!='33ff81c882a0e5e98771b8c00f627af5860b56464798e16dc38e75122b45a005':raise ValueError('Use only approved e1c3c474 source')
    args.output.mkdir(parents=True,exist_ok=False);out=args.output
    results={}
    with filter_budget(8):
        y,x=np.indices((256,256));r=np.hypot(x-128,y-128);valid=r>55
        truth=(.05+np.maximum(r/55,1)**-3).astype(np.float32);truth[~valid]=np.nan
        q,old,ref,info=corrected(truth,valid,valid,.025,128,128,55,33,soft=args.soft_encoding)
        near=valid&(r<65)
        error=float(abs(np.median(q[near])-.5));assert error<.02,error
        assert np.array_equal(np.isfinite(q),valid)
        results['smooth_masked_null']=dict(median_error=error,original_median=float(np.median(old[near])),**info)
        injected=truth.copy();theta=np.arctan2(y-128,x-128)
        signal=(.02*np.cos(8*theta)*np.exp(-((r-65)/8)**2)).astype(np.float32);injected[valid]+=signal[valid]
        changed,old_changed,_,info=corrected(injected,valid,valid,.025,128,128,55,33,soft=args.soft_encoding)
        region=valid&(r>57)&(r<80)&(abs(signal)>.01)
        before_response=(old_changed-old)[region];after_response=(changed-q)[region]
        ratio=float(np.dot(before_response,after_response)/np.dot(before_response,before_response))
        agreement=float(np.mean(before_response*after_response>=0))
        assert .9<=ratio<=1.1,ratio
        assert agreement>.98,agreement
        results['angular_injection']=dict(response_ratio=ratio,sign_agreement=agreement,**info)
        flat=np.ones(truth.shape,np.float32);flat[~valid]=np.nan
        constant,_,_,_=corrected(flat,valid,valid,.025,128,128,55,33,soft=args.soft_encoding)
        np.testing.assert_allclose(constant[valid],.5,atol=2e-6)
        outputs=[]
        for seed in (713,914):
            noisy=truth.copy();noisy[valid]+=np.random.default_rng(seed).normal(0,.004,valid.sum())
            output,_,_,_=corrected(noisy,valid,valid,.025,128,128,55,33,soft=args.soft_encoding)
            outputs.append((output-q)[valid])
        correlation=float(np.corrcoef(outputs)[0,1]);assert abs(correlation)<.1,correlation
        results['independent_noise']=dict(correlation=correlation,limit=.1)
        units,_,_,_=corrected(truth*7+2,valid,valid,.025*7,128,128,55,33,soft=args.soft_encoding)
        unit_error=float(np.nanmax(abs(units-q)));assert unit_error<.001,unit_error
        results['units_and_pedestal']=dict(max_error=unit_error,limit=.001)
        population=valid&(r>60)
        base,_,_,_=corrected(truth,population,valid,.025,128,128,55,33,soft=args.soft_encoding)
        changed_input=truth.copy();changed_input[valid&~population]*=3
        changed,_,_,_=corrected(changed_input,population,valid,.025,128,128,55,33,soft=args.soft_encoding)
        excluded_error=float(np.max(abs(base[population]-changed[population])))
        assert excluded_error<3e-6,excluded_error
        results['excluded_sample_independence']=dict(max_error=excluded_error,limit=3e-6)
        partial=valid&(x<220)&(y>25)
        partial_result,_,_,_=corrected(truth,partial,partial,.025,128,128,55,33,soft=args.soft_encoding)
        partial_error=float(np.nanpercentile(abs(partial_result[partial]-.5),95))
        assert partial_error<.03,partial_error
        assert np.array_equal(np.isfinite(partial_result),partial)
        results['partial_coverage_null']=dict(p95_error=partial_error,limit=.03)
        loaded=load_source(str(args.source),None,EclipseProcessorApp.detect_lunar_limb)
        params=dict(zip(('sx','sy','sr'),loaded['circle']));params['statistics_exclude_lunar']=True
        full=loaded['full'];a=loaded['preview'];p=prepare_parameters(params,full.shape,a.shape,a.shape)
        baseline=Path('build/diagnostics/nafe-limb-auto-20261107');old_report=json.loads((baseline/'report.json').read_text())
        with np.load(baseline/'preview-scaled-internal-kernel.npz') as f:actual=f['E']
        valid=np.isfinite(a);samples=statistics_support(a,p,valid);sigma=old_report['automatic_preview_sigma'];scale=p['nafe_scale'];n=2*round(64*scale)+1
        result,_,reference,info=corrected(a,samples,valid,sigma,p['sx'],p['sy'],p['sr'],n,scale,actual,soft=args.soft_encoding)
        assert np.array_equal(np.isfinite(result),np.isfinite(actual))
        dist=distance_transform_edt(valid)/scale;yy,xx=np.indices(a.shape)
        near=valid&(dist>0)&(dist<60)&(np.hypot(xx-p['sx'],yy-p['sy'])<p['sr']+60*scale)
        info['near_limb_median']=float(np.median(result[near]));info['original_near_limb_median']=float(np.median(actual[near]));results['preview']=info
        display=psb_presentation_settings(full,params=params);base,_=psb_base(a,p,display);base=np.nan_to_num(base)
        for name,E in (('original',actual),('reference-response',reference),('experimental',result)):
            save(out/(name+'-E.png'),E)
            save(out/(name+'-blend100.png'),blend(base,np.where(np.isfinite(E),E,.5),np.isfinite(E).astype(float),'Overlay',1.))
        np.savez_compressed(out/'preview.npz',original=actual,reference=reference,experimental=result)
        # Native-scale crop test, preserving the independently measured global sigma.
        left,top=old_report['native_crop_origin'];a=full[top:top+1201,left:left+1201];v=np.isfinite(a)
        pn=dict(params,sx=params['sx']-left,sy=params['sy']-top);m=statistics_support(a,pn,v)
        with np.load(baseline/'native-default.npz') as f:actual=f['E']
        result,_,reference,info=corrected(a,m,v,old_report['automatic_native_sigma'],pn['sx'],pn['sy'],pn['sr'],129,actual=actual,soft=args.soft_encoding)
        assert np.array_equal(np.isfinite(result),np.isfinite(actual))
        dist=distance_transform_edt(v);y,x=np.indices(v.shape);near=v&(dist>0)&(dist<=60)&(np.hypot(x-600,y-600)<450)
        info['near_limb_median']=float(np.median(result[near]));info['original_near_limb_median']=float(np.median(actual[near]));results['native_crop']=info
        base,_=psb_base(a,pn,display);base=np.nan_to_num(base)
        for name,E in (('native-original',actual),('native-experimental',result)):
            save(out/(name+'-blend100.png'),blend(base,np.where(np.isfinite(E),E,.5),np.isfinite(E).astype(float),'Overlay',1.))
        np.savez_compressed(out/'native.npz',original=actual,reference=reference,experimental=result)
    with args.source.open('rb') as f:after=hashlib.file_digest(f,'sha256').hexdigest()
    assert before==after
    results.update(source_sha256=after,source_unchanged=True,production_implementation=False)
    (out/'report.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(results,indent=2),flush=True)


if __name__=='__main__':main()
