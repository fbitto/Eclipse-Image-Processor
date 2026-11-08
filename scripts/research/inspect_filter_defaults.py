"""Read-only filter baseline/sensitivity study; all generated evidence lives in --output."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ.setdefault(key,'1')
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import argparse,copy,csv,hashlib,json,platform,shutil,subprocess,sys,time,traceback,warnings
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import numpy as np
import tifffile
from PIL import Image,ImageDraw
from scipy.ndimage import distance_transform_edt,gaussian_filter1d
from PySide6.QtWidgets import QApplication
from core.filters import FilterWorker
from core.layer_engine import LayerEngine,requests,ORDER,blend
from core.pipeline import prepare_parameters
from core.parallelism import filter_budget
from core.image_data import resize_observed,recipe_parameters
from core.presentation import psb_base,psb_presentation_settings
from gui.app import EclipseProcessorApp
from gui.project_settings import capture_settings

EXPECTED='33ff81c882a0e5e98771b8c00f627af5860b56464798e16dc38e75122b45a005'

def digest(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def write(path,value):
    Path(path).write_text(json.dumps(value,indent=2,allow_nan=False,default=lambda v:v.tolist() if isinstance(v,np.ndarray) else float(v))+'\n',encoding='utf-8')

def modes():
    return [
        ('NRGF-median-MAD-legacy-chain','nrgf',None,dict(nrgf_robust=True,nrgf_partial_annuli='chain')),
        ('NRGF-median-MAD-anchored-chain','nrgf',None,dict(nrgf_robust=True,nrgf_partial_annuli='chain_anchored')),
        ('NRGF-mean-STD-legacy-chain','nrgf',None,dict(nrgf_robust=False,nrgf_partial_annuli='chain')),
        ('NAFE-AEL-original','nafe',None,dict(nafe_method='ael')),
        ('NAFE-limb-aware-experimental','nafe',None,dict(nafe_method='limb_aware')),
        ('FNRGF-continuous-STD','fnrgf',None,dict(fnrgf_mode='continuous',fnrgf_width_func='std')),
        ('FNRGF-continuous-MAD','fnrgf',None,dict(fnrgf_mode='continuous',fnrgf_width_func='mad')),
        ('FNRGF-reference-compatible','fnrgf',None,dict(fnrgf_mode='legacy')),
        ('RHEF-continuous-global','rhef',None,dict(rhef_mode='continuous')),
        ('RHEF-reference-compatible','rhef',None,dict(rhef_mode='legacy')),
        ('MGN-multiscale','mgn',None,{}),
        ('WOW-standard-observed-support','wow',None,dict(wow_mode='native',wow_bilateral=None)),
        ('WOW-watroo-bilateral-observed-support','wow',None,dict(wow_mode='native',wow_bilateral=1.)),
        ('WOW-AEL-guided-edge-aware','wow',None,dict(wow_mode='ael_bilateral')),
        ('Tangential-angular-detail','tangential',None,{}),
        ('Larson-Sekanina-linear','larson_sekanina',None,dict(larson_sekanina_mode='linear')),
        ('Larson-Sekanina-log-HDR','larson_sekanina',None,dict(larson_sekanina_mode='log')),
        ('ACHF-adaptive-circular','achf','adaptive',{}),
        ('ACHF-AEL-ISO-01','achf','ael_iso_01',{}),
        ('ACHF-AEL-ISO-04','achf','ael_iso_04',{}),
        ('ACHF-AEL-angular','achf','ael_angular_4',{})]

def parameters(raw,mode,shape,full_shape,preview_shape,overrides=None):
    p=copy.deepcopy(raw)
    p.update(mode[3]);p.update(overrides or {})
    for name in (*ORDER,'achf'):p[name+'_enabled']=name==mode[1]
    if mode[1]=='achf':
        for name,entry in p['achf_variants'].items():entry['enabled']=name==mode[2]
    p=prepare_parameters(p,full_shape,preview_shape,shape)
    return requests(p)[0][2]

def calculate(a,p,mode):
    captured={};name=mode[1];variant=mode[2]
    target=('core.nrgf.nrgf_layer' if name=='nrgf' else 'core.ael_nafe.nafe_layer' if name=='nafe' else
            'core.ael_wow.wow_edge_aware' if name=='wow' and p.get('wow_mode')=='ael_bilateral' else
            ('core.ael_achf.signed_detail_layer' if p.get('normalization_mode')=='revised' or p.get('achf_ael_parameters',{}).get('encoding')=='bounded' else 'core.ael_achf.display_detail_rings') if name=='achf' and variant!='adaptive' else
            'core.filters.larson_sekanina_residual' if name=='larson_sekanina' else 'core.pipeline.apply_filter')
    import importlib
    module,attribute=target.rsplit('.',1);original=getattr(importlib.import_module(module),attribute)
    def capture(*args,**kwargs):
        result=original(*args,**kwargs)
        captured['operator']=args[0] if target in ('core.ael_achf.display_detail_rings','core.ael_achf.signed_detail_layer') else result[0] if isinstance(result,tuple) else result
        return result
    start=time.monotonic()
    with warnings.catch_warnings(record=True) as caught,filter_budget(8),patch(target,side_effect=capture):
        warnings.simplefilter('always',RuntimeWarning)
        layer=LayerEngine().layer(FilterWorker(),a,p,name,variant)
    raw=captured['operator']
    if name=='tangential':raw=raw-a
    return layer,raw,time.monotonic()-start,[str(v.message) for v in caught if issubclass(v.category,RuntimeWarning)]

def radial_score(z,mask,radii,sr):
    bins=np.floor(radii).astype(np.int32)
    selected=mask&(radii>sr)&(radii<4*sr)
    if selected.sum()<64:return None
    count=np.bincount(bins[selected]);total=np.bincount(bins[selected],weights=z[selected])
    indices=np.flatnonzero(count>=8)
    if len(indices)<12:return None
    # Interpolation is for this 1D diagnostic only, never for output image radiance.
    grid=np.arange(indices[0],indices[-1]+1);profile=np.interp(grid,indices,total[indices]/count[indices])
    residual=gaussian_filter1d(profile,2)-gaussian_filter1d(profile,16)
    return float(np.sqrt(np.mean(residual**2)))

def metrics(z,alpha,a,p,native_scale=1.):
    observed=np.isfinite(a);valid=observed&(alpha>.99)&np.isfinite(z)
    y,x=np.ogrid[:a.shape[0],:a.shape[1]];r=np.hypot(x-p['sx'],y-p['sy'])/native_scale
    theta=np.arctan2(y-p['sy'],x-p['sx']);sr=p['sr']/native_scale
    sky=valid&(r>4*sr);corona=valid&(r>1.1*sr)&(r<3*sr)
    pair=sky[:,1:]&sky[:,:-1]
    diff=np.diff(z,axis=1)[pair]
    d=distance_transform_edt(observed)/native_scale
    band=[]
    for lo,hi in ((0,5),(5,15),(15,30),(30,60),(60,120)):
        q=valid&(d>lo)&(d<=hi)&(r<sr+120)
        band.append(dict(native_distance_px=[lo,hi],pixels=int(q.sum()),median=float(np.median(z[q])) if q.any() else None,
                         supported_fraction=float(np.mean((alpha>.99)[observed&(d>lo)&(d<=hi)&(r<sr+120)])) if (observed&(d>lo)&(d<=hi)&(r<sr+120)).any() else None))
    sectors=[]
    for index in range(8):
        m=valid&(theta>=-np.pi+index*np.pi/4)&(theta< -np.pi+(index+1)*np.pi/4)
        sectors.append(radial_score(z,m,r,sr))
    return dict(supported_fraction=float(valid.sum()/observed.sum()),support_pixels=int(valid.sum()),
        missing_pixels_with_alpha=int(np.count_nonzero((alpha>0)&~observed)),
        sky_texture_std=float(np.std(z[sky])) if sky.any() else None,
        sky_adjacent_MAD=float(1.4826*np.median(abs(diff-np.median(diff)))/np.sqrt(2)) if diff.size else None,
        corona_std=float(np.std(z[corona])) if corona.any() else None,
        clipped_fraction=float(np.mean((z[valid]<=0)|(z[valid]>=1))) if valid.any() else None,
        radial_profile_band_RMS=radial_score(z,valid,r,sr),sector_band_RMS=sectors,
        worst_sector_band_RMS=max((v for v in sectors if v is not None),default=None),limb_bands=band)

def save_image(path,z):
    Image.fromarray(np.uint8(np.nan_to_num(np.clip(z,0,1))*255)).save(path)

def save_case(folder,a,p,mode,layer,raw,base,seconds,notes,scale,arrays=False):
    folder.mkdir(parents=True,exist_ok=True)
    q=layer['image'].astype(np.float32)/65535;alpha=layer['alpha'].astype(np.float32)/65535
    diagnostic=blend(base,q,alpha,layer['mode'],1.)
    working_opacity=p.get(mode[1]+'_opacity',10)/100
    working=blend(base,q,alpha,layer['mode'],working_opacity)
    info=dict(mode=mode[0],family=mode[1],variant=mode[2],seconds=seconds,warnings=notes,
        parameters=recipe_parameters(p),mapping=layer['mapping'],blend_mode=layer['mode'],working_opacity=working_opacity,
        encoded=metrics(q,alpha,a,p,scale),diagnostic_100_percent=metrics(diagnostic,alpha,a,p,scale),
        working_opacity_composite=metrics(working,alpha,a,p,scale),
        operator=dict(finite_fraction=float(np.isfinite(raw[np.isfinite(a)]).mean()),percentiles=np.percentile(raw[np.isfinite(raw)],[0,1,50,99,100]).tolist() if np.isfinite(raw).any() else None))
    write(folder/'measurements-and-exact-parameters.json',info)
    save_image(folder/'full-canvas-100-percent-opacity.png',diagnostic)
    save_image(folder/'full-canvas-current-working-opacity.png',working)
    save_image(folder/'encoded-independent-layer.png',q)
    cx,cy=round(p['sx']),round(p['sy']);half=max(80,round(p['sr']*2.2))
    im=Image.open(folder/'full-canvas-100-percent-opacity.png')
    im.crop((max(0,cx-half),max(0,cy-half),min(a.shape[1],cx+half+1),min(a.shape[0],cy+half+1))).save(folder/'limb-and-inner-corona-crop.png');im.close()
    if arrays:
        tifffile.imwrite(folder/'operator-float32.tif',raw.astype(np.float32),compression='zlib')
        tifffile.imwrite(folder/'encoded-layer-uint16.tif',layer['image'],compression='zlib')
        tifffile.imwrite(folder/'observed-layer-alpha-uint16.tif',layer['alpha'],compression='zlib')
    return info,q,alpha,diagnostic

def sensitivity_candidates(mode,raw):
    family=mode[1]
    if family=='nrgf':return [('nrgf_bin_px',[max(.5,raw['nrgf_bin_px']/2),raw['nrgf_bin_px']*2]),('nrgf_smooth_bins',[2.,6.])]
    if family=='nafe':return [('nafe_window',[65,257]),('nafe_noise_multiple',[6.,24.])]
    if family=='fnrgf':return [('fnrgf_ord',[1,5]),('fnrgf_seg',[16,128])]
    if family=='rhef':return [('rhef_upsilon',[15,70]),('rhef_bin_px',[max(.5,raw['rhef_bin_px']/2),raw['rhef_bin_px']*2])]
    if family=='mgn':return [('mgn_k',[30,100]),('mgn_h',[30,90])]
    if family=='wow':return [('wow_scales',[6,10]),('wow_noise_reduction',[1.,2.])] if mode[3].get('wow_mode')=='ael_bilateral' else [('wow_scales',[6,10]),('wow_denoise',[[1.]*10,[3.]*10])]
    if family=='tangential':return [('tangential_arc',[1.,6.]),('tangential_denoise',[1.,3.])]
    if family=='larson_sekanina':return [('larson_sekanina_angular',[1.,6.]),('larson_sekanina_nearby_delta',[.2,.5])]
    if mode[2]=='adaptive':return [('achf_threshold',[10,60]),('achf_kernel',[max(3,raw['achf_kernel']//2|1),raw['achf_kernel']*2+1])]
    # Per-variant sigma lists stay coupled, avoiding a sweep of every band.
    settings=copy.deepcopy(raw['achf_variants'][mode[2]])
    candidates=[]
    for factor in (.5,2.):
        value=copy.deepcopy(settings)
        if 'sigmas' in value:value['sigmas']=[v*factor for v in value['sigmas']]
        else:value['angular_sigma']=value.get('angular_sigma',1)*factor
        candidates.append(value)
    variants=[]
    for value in candidates:
        all_settings=copy.deepcopy(raw['achf_variants']);all_settings[mode[2]]=value;variants.append(all_settings)
    return [('achf_variants',variants)]

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--phase',choices=['baseline','synthetic','sensitivity'],required=True)
    args=parser.parse_args();root=args.output;root.mkdir(exist_ok=True)
    if digest(args.source)!=EXPECTED:raise ValueError('Wrong source: approved-master hash mismatch')
    app=QApplication.instance() or QApplication([]);w=EclipseProcessorApp();w.auto_calculate=False;w.btn_auto_calc.setChecked(False)
    w.open_file(str(args.source));deadline=time.monotonic()+180
    while w.full_raw_image is None or any(getattr(w,n) is not None for n in ('_load_thread','_geometry_thread','_presentation_thread')) or w.is_processing:
        app.processEvents();time.sleep(.01)
        if time.monotonic()>deadline:raise TimeoutError(w.status_label.text())
    w.ui_level.setCurrentIndex(1);app.processEvents()
    full=w.full_raw_image;preview=w.preview_image
    with patch('gui.app.prepare_parameters',side_effect=lambda p,*_:p):raw=w.collect_filter_parameters(full.shape,include_mask=False)
    snapshot=capture_settings(w);w.close();app.processEvents()
    display=psb_presentation_settings(full,params=raw)
    archive=root/'00-Test-Manifest-and-Current-Defaults';archive.mkdir(exist_ok=True)
    if not (archive/'current-GUI-settings-snapshot.json').exists():
        write(archive/'current-GUI-settings-snapshot.json',snapshot);write(archive/'current-unprepared-numerical-defaults.json',recipe_parameters(raw))
        write(archive/'input-and-environment.json',dict(source=str(args.source.resolve()),sha256=EXPECTED,shape=full.shape,preview_shape=preview.shape,geometry={key:raw[key] for key in ('sx','sy','sr')},python=sys.version,platform=platform.platform(),modes=[m[0] for m in modes()],default_enabled=[name for name in (*ORDER,'achf') if raw.get(name+'_enabled')]))
        write(archive/'frozen-screening-criteria.json',dict(role='screening alerts, not scientific acceptance',parameter_influence_MAE=.005,local_display_band_alert=.03,missing_data_alpha_required=0,held_out_seeds=[361,908],no_aggregate_overrides_local_failure=True))
        for command,filename in [(['git','diff'],'uncommitted-code-snapshot.patch'),(['git','rev-parse','HEAD'],'git-HEAD.txt'),(['git','status','--short'],'git-working-tree.txt')]:
            (archive/filename).write_text(subprocess.check_output(command,text=True),encoding='utf-8')
        shutil.copy2(__file__,archive/'inspection-runner-source.py')
    errors=[];rows=[]
    if args.phase=='baseline':
        for index,mode in enumerate(modes(),1):
            for label,a in [('preview',preview),('native',full)]:
                folder=root/'01-Default-Filter-Baselines'/f'{index:02d}-{mode[0]}'/label
                if (folder/'measurements-and-exact-parameters.json').exists():continue
                try:
                    p=parameters(raw,mode,a.shape,full.shape,preview.shape);base,_=psb_base(a,p,display)
                    layer,operator,seconds,notes=calculate(a,p,mode)
                    info,_,_,_=save_case(folder,a,p,mode,layer,operator,np.nan_to_num(base),seconds,notes,p['nrgf_scale'],arrays=True)
                    print('BASELINE',mode[0],label,round(seconds,2),flush=True)
                except Exception as exc:
                    folder.mkdir(parents=True,exist_ok=True);(folder/'FAILED-traceback.txt').write_text(traceback.format_exc());errors.append([mode[0],label,str(exc)]);print('FAILED',errors[-1],flush=True)
                finally:
                    for key in ('layer','operator','base'):
                        if key in locals():del locals()[key]
    elif args.phase=='sensitivity':
        a=preview
        for index,mode in enumerate(modes(),1):
            p=parameters(raw,mode,a.shape,full.shape,preview.shape);base,_=psb_base(a,p,display)
            try:baseline,_,_,_=calculate(a,p,mode)
            except Exception as exc:errors.append([mode[0],'baseline',str(exc)]);continue
            original=baseline['image'].astype(float)/65535;original_alpha=baseline['alpha'].astype(float)/65535
            for control,values in sensitivity_candidates(mode,raw):
                for number,value in enumerate(values,1):
                    folder=root/'03-Parameter-Influence-Screening'/f'{index:02d}-{mode[0]}'/f'{control}-test-{number}'
                    try:
                        changes={control:value}
                        if control=='rhef_upsilon':changes['rhef_upsilon_high']=value
                        pp=parameters(raw,mode,a.shape,full.shape,preview.shape,changes)
                        layer,operator,seconds,notes=calculate(a,pp,mode)
                        info,q,alpha,_=save_case(folder,a,pp,mode,layer,operator,np.nan_to_num(base),seconds,notes,pp['nrgf_scale'])
                        common=(alpha>.99)&(original_alpha>.99)&np.isfinite(a)
                        difference=q[common]-original[common]
                        row=dict(mode=mode[0],control=control,test=number,value=recipe_parameters({control:value})[control],encoded_MAE=float(np.mean(abs(difference))),encoded_p95_absolute_change=float(np.percentile(abs(difference),95)),common_support_fraction=float(common.sum()/np.isfinite(a).sum()),measurement_file=str((folder/'measurements-and-exact-parameters.json').relative_to(root)))
                        rows.append(row);write(root/'03-Parameter-Influence-Screening'/'influence-measurements.json',rows)
                        print('SENSITIVITY',mode[0],control,number,row['encoded_MAE'],flush=True)
                    except Exception as exc:
                        folder.mkdir(parents=True,exist_ok=True);(folder/'FAILED-traceback.txt').write_text(traceback.format_exc());errors.append([mode[0],control,str(exc)]);print('FAILED',errors[-1],flush=True)
    else:
        y,x=np.indices((256,256));rr=np.hypot(x-128,y-128);theta=np.arctan2(y-128,x-128)
        mono=(.05+np.maximum(rr/30,1.)**-3).astype(np.float32)
        signal=(.012*np.cos(12*theta)*np.exp(-((rr-65)/12)**2)).astype(np.float32)
        clean=mono*(1+.08*np.cos(5*theta))
        valid=(np.hypot(x-135,y-124)>30)&(x<238)&(y>12)
        noise=np.random.default_rng(361).normal(0,.001,mono.shape).astype(np.float32)
        from scipy.ndimage import gaussian_filter
        independent_noise=np.random.default_rng(908).normal(0,.001,mono.shape).astype(np.float32)
        correlated_noise=gaussian_filter(independent_noise,1.)*3
        scenes=dict(radial_null=mono,angular_structure_null=clean,noisy_base=clean+noise,injected_faint_detail=clean+noise+signal,held_out_independent_noise=clean+independent_noise,held_out_correlated_noise=clean+correlated_noise)
        scene_root=root/'02-Synthetic-Known-Truth-Controls';scene_root.mkdir(exist_ok=True)
        flat=np.full(mono.shape,.5,np.float32)
        rings=(flat+.2*np.sin(2*np.pi*rr/8)).astype(np.float32)
        null_score=radial_score(flat,valid,rr,30)
        bad_score=radial_score(rings,valid,rr,30)
        assert null_score < 1e-6 and bad_score > .03,(null_score,bad_score)
        write(scene_root/'ring-metric-negative-control.json',dict(flat_score=null_score,injected_8_pixel_ring_score=bad_score,screening_alert=.03))
        tifffile.imwrite(scene_root/'negative-control-injected-8-pixel-rings.tif',np.where(valid,rings,np.nan))
        for name,a in scenes.items():
            a=a.copy();a[~valid]=np.nan;scenes[name]=a;tifffile.imwrite(scene_root/f'input-{name}.tif',a)
        synthetic=copy.deepcopy(raw);synthetic.update(sx=128.,sy=128.,sr=30.,fnrgf_rmax=50)
        write(scene_root/'known-truth-scene-definition.json',dict(solar_center=[128,128],missing_disk_center=[135,124],radius=30,seed=361,signal_amplitude=.012,noise_sigma=.001,physical_case='deliberately offset lunar missing boundary and straight coverage edges'))
        for index,mode in enumerate(modes(),1):
            outputs={}
            for name,a in scenes.items():
                folder=scene_root/f'{index:02d}-{mode[0]}'/name
                try:
                    p=parameters(synthetic,mode,a.shape,a.shape,a.shape)
                    layer,operator,seconds,notes=calculate(a,p,mode)
                    base=np.nan_to_num(mono/np.nanmax(mono))
                    info,q,alpha,_=save_case(folder,a,p,mode,layer,operator,base,seconds,notes,1.,arrays=True)
                    outputs[name]=(q,alpha,info)
                    print('SYNTHETIC',mode[0],name,round(seconds,2),flush=True)
                except Exception as exc:
                    folder.mkdir(parents=True,exist_ok=True);(folder/'FAILED-traceback.txt').write_text(traceback.format_exc());errors.append([mode[0],name,str(exc)])
            if all(key in outputs for key in ('noisy_base','held_out_independent_noise','angular_structure_null')):
                b,ba,_=outputs['noisy_base'];h,ha,_=outputs['held_out_independent_noise'];clean_q,ca,_=outputs['angular_structure_null']
                common=valid&(ba>.99)&(ha>.99)&(ca>.99)&(rr>40)
                correlation=float(np.corrcoef((b-clean_q)[common],(h-clean_q)[common])[0,1]) if common.sum()>64 and np.std((b-clean_q)[common])>0 and np.std((h-clean_q)[common])>0 else None
                write(scene_root/f'{index:02d}-{mode[0]}'/'independent-noise-null.json',dict(output_noise_correlation=correlation,common_pixels=int(common.sum()),interpretation='shared clean source subtracted; nonlinear display statistics can still introduce coherent differences'))
            if 'noisy_base' in outputs and 'injected_faint_detail' in outputs:
                before,ba,_=outputs['noisy_base'];after,aa,_=outputs['injected_faint_detail']
                region=valid&(ba>.99)&(aa>.99)&(rr>48)&(rr<82)&(abs(signal)>.006)
                if region.sum()<64:
                    errors.append([mode[0],'injection','fewer than 64 common-support injection targets']);continue
                response=(after-before)[region];truth=signal[region]
                row=dict(mode=mode[0],pixels=int(region.sum()),injection_correlation=float(np.corrcoef(response,truth)[0,1]) if np.std(response)>0 else 0.,sign_agreement=float(np.mean(response*truth>0)),response_RMS=float(np.sqrt(np.mean(response**2))))
                rows.append(row);write(scene_root/'paired-injection-responses.json',rows)
    write(root/f'{args.phase}-errors.json',errors)
    assert digest(args.source)==EXPECTED
    write(root/f'{args.phase}-completion.json',dict(completed=True,source_hash_unchanged=True,errors=errors))
    print('PHASE COMPLETED',args.phase,'errors',len(errors),flush=True)

if __name__=='__main__':main()
