"""Native parity and expanded synthetic qualification for optional revised normalization."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ.setdefault(key,'1')
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import argparse,copy,json,sys,traceback,shutil,subprocess
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import numpy as np,tifffile
from PIL import Image,ImageDraw
from inspect_filter_defaults import modes,parameters,calculate,save_case,write,digest,EXPECTED
from gui.background_tasks import load_source
from gui.app import EclipseProcessorApp
from core.presentation import psb_presentation_settings,psb_base


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--study',type=Path,required=True);parser.add_argument('--phase',choices=['synthetic','native','weak'],required=True);args=parser.parse_args();study=args.study;root=study/'08-Normalization-Fixes-and-Extensive-Validation'
    raw=json.load(open(study/'00-Test-Manifest-and-Current-Defaults/current-unprepared-numerical-defaults.json'));meta=json.load(open(study/'00-Test-Manifest-and-Current-Defaults/input-and-environment.json'))
    assert digest(meta['source'])==EXPECTED
    rows=[];errors=[];tested=[]
    archive=root/'Code-and-Frozen-Validation-Criteria';archive.mkdir(exist_ok=True)
    write(archive/'criteria.json',dict(compatibility_pixel_equality=True,missing_source_alpha=0,radial_null_sector_band_max=.03,injected_negative_fraction_max=.001,injected_zero_fraction_max=.02,minimum_injection_correlation=.95,note='Legacy/reference-compatible FNRGF unchanged; revised contrast differs and is offered as a separate choice'))
    for path in ('core/ael_achf.py','core/nrgf.py','core/continuous_fnrgf.py','core/layer_engine.py','core/filters.py','core/pipeline.py','gui/filter_controls.py','gui/project_settings.py','tests/test_revised_normalization.py','scripts/research/qualify_normalization_fixes.py'):
        shutil.copy2(path,archive/path.replace('/','--'))
    (archive/'current-tracked-diff.patch').write_bytes(subprocess.check_output(['git','diff']))
    if args.phase=='weak':
        qualify_weak(study,root,raw)
        assert digest(meta['source'])==EXPECTED
        return
    if args.phase=='native':
        loaded=load_source(meta['source'],None,EclipseProcessorApp.detect_lunar_limb);full=loaded['full'];full.setflags(write=False);preview=loaded['preview'];display=psb_presentation_settings(full,params=raw)
        for index,mode in enumerate(modes(),1):
            if mode[1] not in ('fnrgf','achf','tangential'):continue
            for resolution,a in [('preview',preview),('native',full)]:
                folder=root/'04-Full-Canvas-Native-and-Preview-Comparisons'/f'{index:02d}-{mode[0]}'/resolution
                try:
                    before=parameters(raw,mode,a.shape,full.shape,preview.shape,dict(normalization_mode='compatible'))
                    old_layer,_,_,_=calculate(a,before,mode)
                    old_folder=study/'01-Default-Filter-Baselines'/f'{index:02d}-{mode[0]}'/resolution
                    np.testing.assert_array_equal(old_layer['image'],tifffile.imread(old_folder/'encoded-layer-uint16.tif'))
                    np.testing.assert_array_equal(old_layer['alpha'],tifffile.imread(old_folder/'observed-layer-alpha-uint16.tif'))
                    p=parameters(raw,mode,a.shape,full.shape,preview.shape,dict(normalization_mode='revised'));base,_=psb_base(a,p,display)
                    layer,operator,seconds,notes=calculate(a,p,mode)
                    np.testing.assert_array_equal(layer['alpha'],old_layer['alpha'])
                    info,_,_,_=save_case(folder,a,p,mode,layer,operator,np.nan_to_num(base),seconds,notes,p['nrgf_scale'],arrays=True)
                    before_image=Image.open(old_folder/'full-canvas-100-percent-opacity.png').convert('RGB');after_image=Image.open(folder/'full-canvas-100-percent-opacity.png').convert('RGB')
                    before_image.thumbnail((1000,650));after_image.thumbnail((1000,650));sheet=Image.new('RGB',(2000,700),'#202020');sheet.paste(before_image,(0,35));sheet.paste(after_image,(1000,35));ImageDraw.Draw(sheet).text((10,10),'Compatible: '+mode[0],fill='white');ImageDraw.Draw(sheet).text((1010,10),'Revised; same source, geometry, exposure and opacity',fill='white');sheet.save(folder/'compatible-versus-revised-full-canvas.jpg');before_image.close();after_image.close()
                    row=dict(mode=mode[0],resolution=resolution,compatibility_exact=True,alpha_exact=True,missing_alpha=info['encoded']['missing_pixels_with_alpha'],seconds=seconds,clipped_fraction=info['encoded']['clipped_fraction'],warnings=notes)
                    rows.append(row);write(root/'native-and-preview-validation.json',rows);print('NATIVE/PREVIEW',row,flush=True)
                except Exception as exc:
                    folder.mkdir(parents=True,exist_ok=True);(folder/'FAILED-traceback.txt').write_text(traceback.format_exc());errors.append([mode[0],resolution,str(exc)]);print('FAILED',errors[-1],flush=True)
    else:
        y,x=np.indices((256,256));r=np.hypot(x-128,y-128);theta=np.arctan2(y-128,x-128)
        radial=(.05+np.maximum(r/30,1.)**-3).astype(np.float32);valid=(np.hypot(x-135,y-124)>30)&(x<238)&(y>12)
        inputs={p.stem.removeprefix('input-'):tifffile.imread(p) for p in (study/'02-Synthetic-Known-Truth-Controls').glob('input-*.tif')}
        extras=dict(centered_radial_null=np.where(r>30,radial,np.nan),constant_null=np.where(valid,1.,np.nan).astype(np.float32),sky_gradient=np.where(valid,radial+.0001*(x-128),np.nan).astype(np.float32),star_and_spike=np.where(valid,radial+.5*np.exp(-((x-180)**2+(y-80)**2)/8),np.nan).astype(np.float32))
        extras['star_and_spike'][100,200]+=10;inputs.update(extras)
        input_folder=root/'03-Expanded-Synthetic-Controls/Inputs';input_folder.mkdir(parents=True,exist_ok=True)
        for name,a in inputs.items():tifffile.imwrite(input_folder/(name+'.tif'),a)
        synthetic=copy.deepcopy(raw);synthetic.update(sx=128.,sy=128.,sr=30.,fnrgf_rmax=50)
        signal=.012*np.cos(12*theta)*np.exp(-((r-65)/12)**2)
        for index,mode in enumerate(modes(),1):
            if mode[1] not in ('fnrgf','achf','tangential'):continue
            outputs={}
            for scene,a in inputs.items():
                folder=root/'03-Expanded-Synthetic-Controls'/f'{index:02d}-{mode[0]}'/scene
                try:
                    p=parameters(synthetic,mode,a.shape,a.shape,a.shape,dict(normalization_mode='revised'))
                    p['layer_display']=dict(normalization_range=[float(np.nanmin(a)),float(np.nanmax(a))])
                    layer,operator,seconds,notes=calculate(a,p,mode)
                    info,q,alpha,_=save_case(folder,a,p,mode,layer,operator,np.nan_to_num(a/np.nanmax(a)),seconds,notes,1.,arrays=True)
                    assert info['encoded']['missing_pixels_with_alpha']==0
                    outputs[scene]=(q,alpha,info)
                    tested.append(dict(mode=mode[0],scene=scene,seconds=seconds,warnings=notes))
                except Exception as exc:
                    folder.mkdir(parents=True,exist_ok=True);(folder/'FAILED-traceback.txt').write_text(traceback.format_exc());errors.append([mode[0],scene,str(exc)])
            if all(key in outputs for key in ('radial_null','noisy_base','injected_faint_detail')):
                b,ba,_=outputs['noisy_base'];a,aa,_=outputs['injected_faint_detail'];common=(ba>.99)&(aa>.99)&(r>48)&(r<82)&(abs(signal)>.006);delta=(a-b)[common];truth=signal[common]
                null=outputs['radial_null'][2]['encoded']['worst_sector_band_RMS']
                score=dict(mode=mode[0],radial_null_band=null,centered_null_band=outputs['centered_radial_null'][2]['encoded']['worst_sector_band_RMS'],negative_fraction=float(np.mean(delta*truth<0)),zero_fraction=float(np.mean(delta==0)),correlation=float(np.corrcoef(delta,truth)[0,1]) if np.std(delta)>0 else 0.)
                score['screen_pass']=bool(null is not None and null<.03 and score['negative_fraction']<=.001 and score['zero_fraction']<.02 and score['correlation']>.95)
                if mode[0]=='FNRGF-reference-compatible':score['screen_pass']=None;score['note']='Intentionally unchanged reference path; original known ring remains'
                rows.append(score);print('SYNTHETIC',score,flush=True)
                write(root/'expanded-synthetic-quality.json',rows)
        write(root/'expanded-synthetic-executions.json',tested)
    assert digest(meta['source'])==EXPECTED
    write(root/(args.phase+'-qualification-completion.json'),dict(completed=True,source_hash_unchanged=True,errors=errors,cases=len(rows) if args.phase=='native' else len(tested)))
    print('COMPLETED',args.phase,'ERRORS',len(errors),flush=True)

def qualify_weak(study,root,raw):
    a=tifffile.imread(study/'02-Synthetic-Known-Truth-Controls/input-noisy_base.tif')
    y,x=np.indices(a.shape);r=np.hypot(x-128,y-128)
    signal=(.003*np.cos(12*np.arctan2(y-128,x-128))*np.exp(-((r-65)/12)**2)).astype(np.float32)
    raw=copy.deepcopy(raw);raw.update(sx=128.,sy=128.,sr=30.,fnrgf_rmax=50);rows=[]
    for index,mode in enumerate(modes(),1):
        if mode[1] not in ('fnrgf','achf','tangential'):continue
        p=parameters(raw,mode,a.shape,a.shape,a.shape,dict(normalization_mode='revised'))
        p['layer_display']=dict(normalization_range=[float(np.nanmin(a)),float(np.nanmax(a))])
        layer,operator,seconds,notes=calculate(a+signal,p,mode)
        folder=root/'03a-Weaker-Injection-Held-Out-Control'/f'{index:02d}-{mode[0]}'
        _,q,alpha,_=save_case(folder,a+signal,p,mode,layer,operator,np.nan_to_num(a/np.nanmax(a)),seconds,notes,1.,arrays=True)
        before_folder=root/'03-Expanded-Synthetic-Controls'/f'{index:02d}-{mode[0]}'/'noisy_base'
        before=tifffile.imread(before_folder/'encoded-layer-uint16.tif').astype(float)/65535
        before_raw=tifffile.imread(before_folder/'operator-float32.tif');ba=tifffile.imread(before_folder/'observed-layer-alpha-uint16.tif')/65535
        m=(alpha>.99)&(ba>.99)&np.isfinite(before_raw)&np.isfinite(operator)&(r>48)&(r<82)&(abs(signal)>.0015)
        delta=(q-before)[m];truth=signal[m];raw_delta=(operator-before_raw)[m]
        row=dict(mode=mode[0],input_amplitude=.003,input_noise_sigma=.001,negative_fraction=float(np.mean(delta*truth<0)),zero_fraction=float(np.mean(delta==0)),raw_negative_fraction=float(np.mean(raw_delta*truth<0)),correlation=float(np.corrcoef(delta,truth)[0,1]))
        rows.append(row);print('WEAK INJECTION',row,flush=True)
    write(root/'weaker-injection-quality.json',rows)


if __name__=='__main__':main()
