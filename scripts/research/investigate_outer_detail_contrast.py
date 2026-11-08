"""Research only: recover display contrast without changing raw detail, source or defaults."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ.setdefault(key,'1')
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import argparse,copy,json,sys,subprocess,hashlib,shutil
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import numpy as np,tifffile
from scipy.ndimage import gaussian_filter1d
from PIL import Image,ImageDraw
from inspect_filter_defaults import modes,parameters,calculate,metrics,write,digest,EXPECTED,save_image
from gui.background_tasks import load_source
from gui.app import EclipseProcessorApp
from core.presentation import psb_base,psb_presentation_settings
from core.layer_engine import blend


def scales(a,valid,p,linear):
    if not linear:return dict(current=.05)
    values=np.abs(a[valid].astype(float));limits=p.get('layer_display',{}).get('normalization_range')
    span=float(limits[1]-limits[0]) if limits is not None else float(np.ptp(a[np.isfinite(a)].astype(float)))
    lo,hi=np.percentile(a[valid],[.5,99.5]);baseline=max(.01*span,np.finfo(np.float32).tiny)
    y,x=np.ogrid[:a.shape[0],:a.shape[1]];r=np.hypot(x-p['sx'],y-p['sy']);bins=np.floor(r).astype(int)
    count=np.bincount(bins[valid]);sums=np.bincount(bins[valid],weights=values);indices=np.flatnonzero(count>=12)
    if len(indices)<8:raise ValueError('Insufficient source-profile reference support')
    profile=np.interp(np.arange(len(count)),indices,sums[indices]/count[indices])
    log_profile=gaussian_filter1d(np.log(np.maximum(profile,np.finfo(float).tiny)),max(1.,.1*p['sr']))
    model=np.exp(np.interp(r,np.arange(len(count)),log_profile)).astype(np.float32)
    radial=np.maximum(.05*model,baseline/8)
    pairs=valid[:,1:]&valid[:,:-1]&(r[:,1:]>8*p['sr'])&(r[:,:-1]>8*p['sr'])
    fallback=int(pairs.sum())<64
    if fallback:pairs=valid[:,1:]&valid[:,:-1]
    differences=np.diff(a.astype(float),axis=1)[pairs]
    noise=float(1.4826*np.median(abs(differences-np.median(differences)))/np.sqrt(2)) if differences.size else 0.
    fractional=np.maximum(.05*model,max(3*noise,np.finfo(np.float32).tiny))
    return dict(fractional=fractional,source_noise=noise,noise_fallback=fallback,current=baseline,robust=max(.01*(hi-lo),np.finfo(np.float32).tiny),radial=radial)


def encode(detail,reference,gain,method):
    scale=reference['fractional'] if method=='fractional-source-contrast' else reference['robust'] if method=='robust-source-range' else reference['radial'] if method=='bounded-source-profile' else reference['current']
    factor=4. if method in ('uniform-gain-4','algebraic-gain-4') else 1.
    z=gain*factor*detail.astype(float)/(2.5*scale)
    signed=z/np.hypot(1.,z) if method in ('algebraic-gain-4','fractional-source-contrast') else np.tanh(z)
    return np.round(np.clip(.5+.5*signed,0,1)*65535)/65535


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--study',type=Path,required=True);parser.add_argument('--fractional-only',action='store_true');args=parser.parse_args();study=args.study
    root=study/'09-Outer-Detail-Contrast-Investigation'
    if args.fractional_only:root=root/'Source-Fractional-Contrast-Additional-Probe'
    root.mkdir(exist_ok=False)
    before=subprocess.check_output(['git','diff']);(root/'application-diff-at-start.patch').write_bytes(before);shutil.copy2(__file__,root/'investigation-source.py')
    meta=json.load(open(study/'00-Test-Manifest-and-Current-Defaults/input-and-environment.json'));raw=json.load(open(study/'00-Test-Manifest-and-Current-Defaults/current-unprepared-numerical-defaults.json'));assert digest(meta['source'])==EXPECTED
    selected=[(i,m) for i,m in enumerate(modes(),1) if m[0] in ('Tangential-angular-detail','ACHF-adaptive-circular','ACHF-AEL-ISO-04','ACHF-AEL-angular')]
    if args.fractional_only:selected=[v for v in selected if v[1][0] in ('Tangential-angular-detail','ACHF-adaptive-circular')]
    write(root/'additional-hypothesis.json',dict(enabled=args.fractional_only,reason='The max-range-derived cap bound the previous source profile almost everywhere on the native master',formula='zero-centered algebraic contrast; scale=max(0.05*source continuum,3*far-field adjacent-MAD sigma)',noise_region='beyond eight reference radii; explicit fallback',no_application_changes=True))
    write(root/'frozen-comparison-definition.json',dict(methods=['current','uniform-gain-4','algebraic-gain-4','robust-source-range','bounded-source-profile'],criteria=dict(negative_fraction_max=.001,zero_fraction_max=.02,radial_null_sector_alert=.03),synthetic_shape=[512,512],radius=30,noise_sigma=.001,seed=1429,injection_amplitude=.003,injection_radii=[2,4,6],scope='display contrast only, not improved SNR; no adoption'))
    y,x=np.indices((512,512));r=np.hypot(x-256,y-256);theta=np.arctan2(y-256,x-256)
    radial=(.05+np.maximum(r/30,1.)**-3).astype(np.float32);valid=(np.hypot(x-263,y-252)>30)&(x<494)&(y>12)
    clean=radial*(1+.08*np.cos(5*theta));noisy=(clean+np.random.default_rng(1429).normal(0,.001,r.shape)).astype(np.float32)
    scenes=dict(radial_null=radial,clean=clean,noisy=noisy)
    for radius in (2,4,6):scenes[f'injected-{radius}R']=noisy+(.003*np.cos(12*theta)*np.exp(-((r-radius*30)/9)**2)).astype(np.float32)
    for key,a in scenes.items():a=a.copy();a[~valid]=np.nan;scenes[key]=a
    source_inputs=root/'Synthetic-Inputs';source_inputs.mkdir()
    for key,a in scenes.items():tifffile.imwrite(source_inputs/(key+'.tif'),a)
    rows=[];synthetic=copy.deepcopy(raw);synthetic.update(sx=256.,sy=256.,sr=30.,fnrgf_rmax=80)
    for index,mode in selected:
        linear=mode[0] in ('Tangential-angular-detail','ACHF-adaptive-circular');methods=['current','uniform-gain-4','algebraic-gain-4']+(['robust-source-range','bounded-source-profile'] if linear else [])
        if args.fractional_only:methods=['current','fractional-source-contrast']
        results={};raws={};alphas={};settings={}
        for scene,a in scenes.items():
            p=parameters(synthetic,mode,a.shape,a.shape,a.shape,dict(normalization_mode='revised'));p['layer_display']=dict(normalization_range=[float(np.nanmin(a)),float(np.nanmax(a))])
            layer,detail,_,_=calculate(a,p,mode);alpha=layer['alpha']/65535;sample=valid&(alpha>0)
            reference=scales(a,sample,p,linear);gain=float(p['tangential_gain'] if mode[1]=='tangential' else p['achf_boost']/10 if mode[2]=='adaptive' else 1.)
            raws[scene]=detail;alphas[scene]=alpha
            for method in methods:
                q=encode(detail,reference,gain,method);results[scene,method]=q
                if method=='current':np.testing.assert_allclose(q[sample],layer['image'][sample]/65535,atol=2/65535)
                m=metrics(q,alpha,a,p)
                settings[scene,method]=m
        for method in methods:
            null=settings['radial_null',method]['worst_sector_band_RMS']
            for radius in (2,4,6):
                scene=f'injected-{radius}R';truth=.003*np.cos(12*theta)*np.exp(-((r-radius*30)/9)**2)
                common=valid&(alphas['noisy']>.99)&(alphas[scene]>.99)&(abs(truth)>.0015)
                delta=(results[scene,method]-results['noisy',method])[common];reference_delta=(results[scene,'current']-results['noisy','current'])[common]
                noise_mask=valid&(alphas['noisy']>.99)&(alphas['clean']>.99)&(r>(radius-.35)*30)&(r<(radius+.35)*30)
                increment=(results['noisy',method]-results['clean',method])[noise_mask]
                original_increment=(results['noisy','current']-results['clean','current'])[noise_mask]
                row=dict(mode=mode[0],method=method,radius_rsun=radius,null_band=null,negative_fraction=float(np.mean(delta*truth[common]<0)),zero_fraction=float(np.mean(delta==0)),response_RMS=float(np.sqrt(np.mean(delta**2))),response_gain=float(np.sqrt(np.mean(delta**2))/max(np.sqrt(np.mean(reference_delta**2)),1e-12)),noise_gain=float(np.std(increment)/max(np.std(original_increment),1e-12)),correlation=float(np.corrcoef(delta,truth[common])[0,1]) if np.std(delta)>0 else 0.)
                rows.append(row);write(root/'synthetic-response-noise-and-null-measurements.json',rows);print('SYNTHETIC',mode[0],method,radius,'detail gain',round(row['response_gain'],2),'noise gain',round(row['noise_gain'],2),'negative',row['negative_fraction'],flush=True)
        # A point spike tests sensitivity of source-reference statistics; raw detail is held fixed.
        a=scenes['noisy'];sample=valid&(alphas['noisy']>0);p=parameters(synthetic,mode,a.shape,a.shape,a.shape,dict(normalization_mode='revised'))
        p['layer_display']=dict(normalization_range=[float(np.nanmin(a)),float(np.nanmax(a))])
        reference=scales(a,sample,p,linear);spiked=a.copy();spiked[100,450]=np.nanmax(a)*100
        altered_p=copy.deepcopy(p);altered_p['layer_display']=dict(normalization_range=[float(np.nanmin(spiked)),float(np.nanmax(spiked))])
        altered=scales(spiked,sample,altered_p,linear)
        target=sample&(r>120)&(r<210)
        spike_rows=[]
        for method in methods:
            first=encode(raws['noisy'],reference,gain,method);second=encode(raws['noisy'],altered,gain,method)
            spike_rows.append(dict(method=method,outer_encoded_MAE_from_reference_change=float(np.mean(abs(second[target]-first[target])))))
        folder=root/f'{index:02d}-{mode[0]}';folder.mkdir();write(folder/'reference-sensitivity-to-one-spike.json',spike_rows)
    loaded=load_source(meta['source'],None,EclipseProcessorApp.detect_lunar_limb);full=loaded['full'];observed=np.isfinite(full);display=psb_presentation_settings(full,params=raw);native_rows=[]
    for index,mode in selected:
        linear=mode[0] in ('Tangential-angular-detail','ACHF-adaptive-circular');methods=['current','uniform-gain-4','algebraic-gain-4']+(['robust-source-range','bounded-source-profile'] if linear else [])
        if args.fractional_only:methods=['current','fractional-source-contrast']
        base_folder=study/'08-Normalization-Fixes-and-Extensive-Validation/04-Full-Canvas-Native-and-Preview-Comparisons'/f'{index:02d}-{mode[0]}'/'native'
        detail=tifffile.imread(base_folder/'operator-float32.tif');alpha=tifffile.imread(base_folder/'observed-layer-alpha-uint16.tif')/65535;p=json.load(open(base_folder/'measurements-and-exact-parameters.json'))['parameters'];current=tifffile.imread(base_folder/'encoded-layer-uint16.tif')/65535
        gain=float(p['tangential_gain'] if mode[1]=='tangential' else p['achf_boost']/10 if mode[2]=='adaptive' else 1.)
        reference=scales(full,observed&(alpha>0),p,linear);base=np.nan_to_num(psb_base(full,p,display)[0]);panels=[]
        native_y,native_x=np.ogrid[:full.shape[0],:full.shape[1]];rr=np.hypot(native_x-p['sx'],native_y-p['sy'])/p['sr']
        for method in methods:
            q=encode(detail,reference,gain,method);common=observed&(alpha>.99)
            if method=='current':np.testing.assert_allclose(q[common],current[common],atol=2/65535)
            folder=root/f'{index:02d}-{mode[0]}'/'Native-Full-Canvas'/method;folder.mkdir(parents=True)
            render=blend(base,np.nan_to_num(q,nan=.5),alpha,'Overlay',.1)
            save_image(folder/'full-canvas-opacity-10-percent.png',render);save_image(folder/'encoded-layer.png',q)
            measurements=metrics(q,alpha,full,p);band_rows=[]
            for lo,hi in ((1.,1.5),(1.5,3.),(3.,5.),(5.,8.)):
                mask=common&(rr>lo)&(rr<hi);band_rows.append(dict(radii=[lo,hi],encoded_std=float(np.std(q[mask])),saturated_fraction=float(np.mean((q[mask]<=0)|(q[mask]>=1)))))
            row=dict(mode=mode[0],method=method,measurements=measurements,bands=band_rows,scale_summary=dict(current=float(reference['current']),robust=float(reference.get('robust',reference['current'])),radial_percentiles=np.percentile(reference['radial'][common],[1,50,99]).tolist() if 'radial' in reference else None,source_noise=reference.get('source_noise'),noise_fallback=reference.get('noise_fallback'),fractional_percentiles=np.percentile(reference['fractional'][common],[1,50,99]).tolist() if 'fractional' in reference else None))
            native_rows.append(row);write(folder/'measurements.json',row)
            with Image.open(folder/'full-canvas-opacity-10-percent.png') as im:
                im=im.convert('RGB');im.thumbnail((750,450));panel=Image.new('RGB',(800,490),'#202020');panel.paste(im,(0,35));ImageDraw.Draw(panel).text((8,8),method+'; same raw detail, opacity 10%',fill='white');panels.append(panel)
        sheet=Image.new('RGB',(1600,490*((len(panels)+1)//2)),'#202020')
        for number,panel in enumerate(panels):sheet.paste(panel,((number%2)*800,(number//2)*490))
        sheet.save(root/f'{index:02d}-{mode[0]}'/'Native-Contrast-Candidate-Comparison.jpg');write(root/'native-contrast-and-clipping-measurements.json',native_rows);print('NATIVE DONE',mode[0],flush=True)
    assert digest(meta['source'])==EXPECTED and subprocess.check_output(['git','diff'])==before
    write(root/'completion.json',dict(completed=True,source_unchanged=True,application_code_unchanged=True,defaults_unchanged=True,synthetic_measurements=len(rows),native_methods=len(native_rows)))

if __name__=='__main__':main()
