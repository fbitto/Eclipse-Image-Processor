"""Read-only NAFE limb controls; new output directory, no production changes.

Run with the project interpreter: diagnose_nafe_limb.py SOURCE.fits NEW_DIRECTORY
All comparison controls use measured samples; synthetic continuation is labelled.
"""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ.setdefault(key,'1')
import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys
import time
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import numpy as np
from PIL import Image,ImageDraw
from scipy.ndimage import distance_transform_edt
from scipy.special import ndtr
from gui.background_tasks import load_source
from core.ael_nafe import nafe,nafe_noise_sigma,nafe_neighbourhood
from core.statistics_support import statistics_support
from core.pipeline import prepare_parameters
from core.presentation import psb_presentation_settings,psb_base
from core.layer_engine import blend
from core.parallelism import filter_budget


def digest(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def display(path,values):
    Image.fromarray(np.rint(np.nan_to_num(np.clip(values,0,1))*255).astype(np.uint8)).save(path)


def scaled_kernel(n,scale):
    k=np.arange(n)-n//2;r2=k[:,None]**2+k[None,:]**2
    sig=2.**(np.arange(1,13)/2)*scale
    g=sum(np.exp(-.5*r2/s**2)/(2*np.pi*np.sqrt(s)) for s in sig)
    return g/g[n//2,n//2]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    output=args.output;before=digest(args.source)
    if before != '33ff81c882a0e5e98771b8c00f627af5860b56464798e16dc38e75122b45a005':
        raise ValueError('This case-specific diagnostic requires the approved e1c3c474 master')
    from gui.app import EclipseProcessorApp
    loaded=load_source(str(args.source),None,EclipseProcessorApp.detect_lunar_limb)
    user=tuple(float(v) for v in loaded['circle']);observed_reference=user
    full=loaded['full'];a=loaded['preview'];valid=np.isfinite(a)
    scale=np.sqrt(np.prod(np.array(a.shape)/full.shape))
    params=dict(zip(('sx','sy','sr'),user));params.update(statistics_exclude_lunar=True)
    p=prepare_parameters(params,full.shape,a.shape,a.shape)
    yy,xx=np.indices(a.shape);native_x=(xx+.5)/(a.shape[1]/full.shape[1])-.5
    native_y=(yy+.5)/(a.shape[0]/full.shape[0])-.5
    near=valid&(np.hypot(native_x-observed_reference[0],native_y-observed_reference[1])<observed_reference[2]+200)
    distance=distance_transform_edt(valid)/scale
    theta=np.arctan2(native_y-observed_reference[1],native_x-observed_reference[0])
    samples=statistics_support(a,p,valid)
    sigma,noise=nafe_noise_sigma(a,samples,p['sx'],p['sy'],p['sr'],smooth_px=4*scale)
    n=2*round(64*scale)+1
    settings=psb_presentation_settings(full,params=params)
    base,_=psb_base(a,p,settings);base=np.nan_to_num(base)
    display(output/'00-base-full.png',base)
    display(output/'00-observed-full.png',valid.astype(float))
    display(output/'00-operator-support-full.png',samples.astype(float))
    crop=(slice(max(0,round((1660-600)*a.shape[0]/full.shape[0])),round((1660+600)*a.shape[0]/full.shape[0])),
          slice(max(0,round((2975-600)*a.shape[1]/full.shape[1])),round((2975+600)*a.shape[1]/full.shape[1])))
    report=dict(source=str(args.source),resolved_source=str(args.source.resolve()),sha256_before=before,
        native_shape=list(full.shape),preview_shape=list(a.shape),target_scale=float(scale),
        user_geometry=user,observed_reference_geometry=observed_reference,
        reference_note='Observed-reference geometry from prior auto-detection; not an independent solar fit or a change to user geometry',
        native_window=129,preview_window=n,automatic_preview_sigma=sigma,noise=noise,cases=[])
    profiles=[];panels=[]
    def record(name,q,info,distance_map=distance,region=near,theta_map=theta,base_image=base, native=False):
        finite=np.isfinite(q);image=np.where(finite,q,.5)
        composite=blend(base_image,image,finite.astype(float),'Overlay',1.)
        start=0
        rows=[]
        for lo,hi in ((0,5),(5,15),(15,30),(30,60),(60,120),(120,180)):
            mask=region&(distance_map>lo)&(distance_map<=hi)
            good=mask&finite
            row=dict(case=name,band=f'{lo}-{hi}',observed=int(mask.sum()),supported=int(good.sum()),
                E_median=float(np.median(q[good])) if good.any() else None,
                E_p10=float(np.percentile(q[good],10)) if good.any() else None,
                E_p90=float(np.percentile(q[good],90)) if good.any() else None,
                blend_delta_median=float(np.median((composite-base_image)[good])) if good.any() else None)
            rows.append(row);profiles.append(row)
        sectors=[]
        for sector in range(12):
            mask=region&(distance_map>0)&(distance_map<=30)&(theta_map>=-np.pi+sector*np.pi/6)&(theta_map<-np.pi+(sector+1)*np.pi/6)
            good=mask&finite
            sectors.append(dict(sector=sector,observed=int(mask.sum()),unsupported=int((mask&~finite).sum()),
                E_median=float(np.median(q[good])) if good.any() else None))
        report['cases'].append(dict(name=name,native=native,info=info,bands=rows,sectors=sectors,
            observed_near_limb=int(region.sum()),unsupported_near_limb=int((region&~finite).sum())))
        np.savez_compressed(output/(name+'.npz'),E=q,supported=finite)
        display(output/(name+'-E.png'),q)
        display(output/(name+'-blend100.png'),composite)
        display(output/(name+'-alpha.png'),finite.astype(float))
        if not native:
            display(output/(name+'-blend40.png'),blend(base_image,image,finite.astype(float),'Overlay',.4))
            im=Image.open(output/(name+'-blend100.png')).crop((crop[1].start,crop[0].start,crop[1].stop,crop[0].stop)).resize((480,480))
            panels.append((name,im))
        print(name,'supported',int(finite[region].sum()),'/',int(region.sum()),'E bands',[(r['band'],r['E_median']) for r in rows],flush=True)
        (output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    cases=[('preview-default',samples,n,sigma,False),
           ('preview-observed-samples',valid,n,sigma,False),
           ('preview-sigma-times3',samples,n,3*sigma,False),
           ('preview-window65',samples,2*round(32*scale)+1,sigma,False),
           ('preview-scaled-internal-kernel',samples,n,sigma,True)]
    with filter_budget(8):
        for name,support,window,gate,physical in cases:
            start=time.monotonic()
            if physical:
                with patch('core.ael_nafe.nafe_neighbourhood',side_effect=lambda nn,**_:scaled_kernel(nn,scale)):
                    q,info=nafe(a,support,gate,n=window,target_valid=valid)
            else:q,info=nafe(a,support,gate,n=window,target_valid=valid)
            info.update(seconds=time.monotonic()-start,sigma_frozen=True,operator_pixels=int(support.sum()))
            record(name,q,info)
        # Native crop has a 600px radius: its inner 450px is clear of the 64px kernel/crop boundary.
        left,top=round(2975-600),round(1660-600)
        roi=full[top:top+1201,left:left+1201];v=np.isfinite(roi)
        pn=dict(params,sx=user[0]-left,sy=user[1]-top)
        m=statistics_support(roi,pn,v)
        native_sigma,native_noise=nafe_noise_sigma(full,np.isfinite(full)&statistics_support(full,params),*user)
        report.update(automatic_native_sigma=native_sigma,native_noise=native_noise,
            native_crop_origin=[left,top],native_crop_shape=list(roi.shape),
            native_crop_limit='Local operator test, not a full native export; level-grid origin can differ from full-canvas interpolation')
        yr,xr=np.indices(roi.shape);rr=np.hypot(xr-600,yr-600)
        dr=distance_transform_edt(v);tr=np.arctan2(yr-600,xr-600);region=v&(rr<450)
        bp,_=psb_base(roi,pn,settings);bp=np.nan_to_num(bp)
        display(output/'native-ROI-base.png',bp)
        for name,support in (('native-default',m),('native-observed-samples',v)):
            start=time.monotonic();q,info=nafe(roi,support,native_sigma,n=129,target_valid=v)
            info.update(seconds=time.monotonic()-start,sigma_frozen=True,operator_pixels=int(support.sum()))
            record(name,q,info,dr,region,tr,bp,True)
    # Flat null with a real missing disk; should not create a ring in E.
    y,x=np.indices((192,192));r=np.hypot(x-96,y-96);mask=r>35
    flat=np.ones(r.shape,np.float32);flat[~mask]=np.nan
    q,info=nafe(flat,mask,.03,n=33)
    np.testing.assert_allclose(q[mask],.5,atol=2e-6)
    report['flat_masked_null_max_error']=float(np.max(abs(q[mask]-.5)))
    # Independent monotone radial truth: no input ring. Removing inner observations is a synthetic control only.
    truth=(.1+np.maximum(r/35,1.e-3)**-3).astype(np.float32)
    # Keep the central continuation finite and bounded without adding anything to the real source.
    truth[r<35]=truth[r>=35].max()
    gate=.03
    for name,support in (('synthetic-masked',mask),('synthetic-complete',np.ones(mask.shape,bool))):
        q,info=nafe(truth,support,gate,n=33,target_valid=mask)
        dr=np.maximum(r-35,0);region=mask&(r<85);tr=np.arctan2(y-96,x-96)
        record(name,q,info,dr,region,tr,np.zeros_like(truth),True)
    # Exact direct CDF witnesses independently check the production FFT/interpolation near the real native limb.
    m=statistics_support(roi,pn,v);kernel=nafe_neighbourhood(129)
    exact=[]
    for angle in np.linspace(-np.pi,np.pi,12,endpoint=False):
        for offset in (5,20,50,100):
            x0=round(600+(272+offset)*np.cos(angle));y0=round(600+(272+offset)*np.sin(angle))
            if not v[y0,x0]:continue
            patch_image=roi[y0-64:y0+65,x0-64:x0+65];support=m[y0-64:y0+65,x0-64:x0+65]
            weights=kernel*support
            if weights.sum()<.01*kernel.sum():continue
            cdf=np.sum(weights*ndtr(np.where(support,(float(roi[y0,x0])-patch_image)/native_sigma,0)))/weights.sum()
            exact.append(dict(x=x0+left,y=y0+top,offset=offset,E_exact=float(cdf)))
    with np.load(output/'native-default.npz') as f:result=f['E']
    for row in exact:row['E_operator']=float(result[row['y']-top,row['x']-left]);row['abs_error']=abs(row['E_exact']-row['E_operator'])
    report['direct_cdf_witnesses']=exact
    assert max(row['abs_error'] for row in exact)<.01
    with (output/'band-profiles.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(profiles[0]));writer.writeheader();writer.writerows(profiles)
    sheet=Image.new('RGB',(1440,1040),'#252525');draw=ImageDraw.Draw(sheet)
    for i,(name,im) in enumerate(panels):
        x=(i%3)*480;y=(i//3)*520;draw.text((x+10,y+10),name,fill='white');sheet.paste(im,(x,y+35))
    sheet.save(output/'limb-controls.png')
    after=digest(args.source);assert before==after
    report['sha256_after']=after;report['source_unchanged']=True
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('DONE',output,'source unchanged',before,flush=True)


if __name__=='__main__':main()
