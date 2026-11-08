"""Frozen-scene and native qualification for optional per-variant AEL ACHF contrast."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ.setdefault(key,'1')
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import argparse,copy,json,sys,subprocess,shutil,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import numpy as np,tifffile
from PIL import Image,ImageDraw
from inspect_filter_defaults import modes,parameters,calculate,save_case,write,digest,EXPECTED,save_image
from core.ael_achf import BOUNDED_CONTRAST_LIMITS,signed_detail_layer
from core.presentation import psb_base,psb_presentation_settings
from core.image_data import resize_observed
from core.layer_engine import blend,engine_for,ORDER
from core.filters import FilterWorker
from core.parallelism import filter_budget
from core.psb_export import export_psb_layers
from core.export import export_images
from core.project_settings import read_settings
from gui.app import EclipseProcessorApp
from gui.background_tasks import load_source
from gui.project_settings import restore_settings,capture_settings
from PySide6.QtWidgets import QApplication
from unittest.mock import patch


def params(raw,mode,shape,full_shape,preview_shape,encoding='bounded',contrast=None,policy='compatible'):
    variants=copy.deepcopy(raw['achf_variants']);entry=variants[mode[2]]
    entry.update(encoding=encoding,contrast=BOUNDED_CONTRAST_LIMITS[mode[2]] if contrast is None else contrast)
    return parameters(raw,mode,shape,full_shape,preview_shape,dict(achf_variants=variants,normalization_mode=policy))


def render(a,p,mode,folder,base,scale):
    layer,detail,seconds,notes=calculate(a,p,mode)
    info,q,alpha,_=save_case(folder,a,p,mode,layer,detail,base,seconds,notes,scale,arrays=True)
    if p['achf_ael_parameters']['encoding']=='bounded':
        gain=p['achf_ael_parameters']['contrast'];z=gain*detail.astype(float)/(2.5*.05)
        reference=np.round((.5+.5*z/np.hypot(1.,z))*65535)/65535
        mask=(alpha>.99)&np.isfinite(reference)
        difference=float(np.max(abs(q[mask]-reference[mask]))) if mask.any() else 0.
        assert difference<=2/65535,(mode[0],difference)
        info['prototype_max_difference']=difference
    assert info['encoded']['missing_pixels_with_alpha']==0
    return info,q,alpha,detail


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--study',type=Path,required=True);args=parser.parse_args();study=args.study;root=study/'11-AEL-ACHF-Bounded-Contrast-Implementation-and-Validation'
    meta=json.load(open(study/'00-Test-Manifest-and-Current-Defaults/input-and-environment.json'));raw=json.load(open(study/'00-Test-Manifest-and-Current-Defaults/current-unprepared-numerical-defaults.json'));assert digest(meta['source'])==EXPECTED
    archive=root/'Code-and-Frozen-Criteria';archive.mkdir()
    write(archive/'criteria.json',dict(maximum_contrast=BOUNDED_CONTRAST_LIMITS,minimum_injection_correlation=.95,negative_fraction_max=.001,zero_fraction_max=.02,radial_null_sector_max=.03,prototype_tolerance=2/65535,original_pixel_and_alpha_parity=True))
    for path in ('core/ael_achf.py','core/layer_engine.py','gui/filter_controls.py','gui/ui_levels.py','tests/test_achf_bounded_contrast.py','scripts/research/validate_achf_bounded_contrast.py'):
        shutil.copy2(path,archive/path.replace('/','--'))
    selected=[(i,m) for i,m in enumerate(modes(),1) if m[2] in BOUNDED_CONTRAST_LIMITS]
    inputs={p.stem:tifffile.imread(p) for p in (study/'09-Outer-Detail-Contrast-Investigation/Synthetic-Inputs').glob('*.tif')}
    for name in ('centered_radial_null','held_out_correlated_noise','sky_gradient','star_and_spike','constant_null'):
        inputs['small-'+name]=tifffile.imread(study/'08-Normalization-Fixes-and-Extensive-Validation/03-Expanded-Synthetic-Controls/Inputs'/(name+'.tif'))
    input_dir=root/'02-Synthetic-Inputs';input_dir.mkdir()
    for name,a in inputs.items():tifffile.imwrite(input_dir/(name+'.tif'),a)
    executions=[];responses=[]
    for index,mode in selected:
        maximum=BOUNDED_CONTRAST_LIMITS[mode[2]]
        for gain in (1.,maximum):
            outputs={}
            for scene,a in inputs.items():
                center=a.shape[0]//2;synthetic=copy.deepcopy(raw);synthetic.update(sx=float(center),sy=float(center),sr=30.)
                p=params(synthetic,mode,a.shape,a.shape,a.shape,contrast=gain)
                folder=root/'03-Synthetic-Qualification'/f'{index:02d}-{mode[0]}'/f'contrast-{gain:g}'/scene
                info,q,alpha,detail=render(a,p,mode,folder,np.nan_to_num(a/np.nanmax(a)),1.)
                executions.append(dict(mode=mode[0],contrast=gain,scene=scene,prototype_difference=info['prototype_max_difference'],null_band=info['encoded']['worst_sector_band_RMS'],clipped_fraction=info['encoded']['clipped_fraction']))
                outputs[scene]=(q,alpha,detail,info)
            y,x=np.indices(outputs['noisy'][0].shape);r=np.hypot(x-256,y-256);theta=np.arctan2(y-256,x-256)
            assert outputs['radial_null'][3]['encoded']['worst_sector_band_RMS']<.03
            for radius in (2,4,6):
                a,alpha,_,_=outputs[f'injected-{radius}R'];b,ba,_,_=outputs['noisy'];truth=.003*np.cos(12*theta)*np.exp(-((r-radius*30)/9)**2)
                mask=(alpha>.99)&(ba>.99)&(abs(truth)>.0015)
                delta=(a-b)[mask];signal=truth[mask]
                row=dict(mode=mode[0],contrast=gain,radius=radius,negative_fraction=float(np.mean(delta*signal<0)),zero_fraction=float(np.mean(delta==0)),correlation=float(np.corrcoef(delta,signal)[0,1]))
                responses.append(row);write(root/'synthetic-injection-results.json',responses);print('INJECTION',row,flush=True)
                assert row['negative_fraction']<=.001 and row['zero_fraction']<.02 and row['correlation']>=.95,row
    write(root/'synthetic-executions.json',executions)
    loaded=load_source(meta['source'],None,EclipseProcessorApp.detect_lunar_limb);full=loaded['full'];preview=loaded['preview'];full.setflags(write=False);display=psb_presentation_settings(full,params=raw);native_rows=[]
    for index,mode in selected:
        resolution_results={};panels=[]
        for resolution,a in [('preview',preview),('native',full)]:
            p=params(raw,mode,a.shape,full.shape,preview.shape);base=np.nan_to_num(psb_base(a,p,display)[0]);folder=root/'04-Full-Native-and-Preview'/f'{index:02d}-{mode[0]}'/resolution
            info,q,alpha,detail=render(a,p,mode,folder,base,p['nrgf_scale'])
            for policy,prior in [('compatible',study/'01-Default-Filter-Baselines'/f'{index:02d}-{mode[0]}'/resolution),('revised',study/'08-Normalization-Fixes-and-Extensive-Validation/04-Full-Canvas-Native-and-Preview-Comparisons'/f'{index:02d}-{mode[0]}'/resolution)]:
                old_p=params(raw,mode,a.shape,full.shape,preview.shape,encoding='normalization',policy=policy)
                original,old_detail,_,_=calculate(a,old_p,mode)
                np.testing.assert_array_equal(original['image'],tifffile.imread(prior/'encoded-layer-uint16.tif'))
                np.testing.assert_array_equal(original['alpha'],np.uint16(np.round(alpha*65535)))
                if policy=='revised':np.testing.assert_array_equal(detail,old_detail)
            tanh,_=signed_detail_layer(detail,alpha>0,.05,BOUNDED_CONTRAST_LIMITS[mode[2]])
            y,x=np.ogrid[:a.shape[0],:a.shape[1]];r=np.hypot(x-p['sx'],y-p['sy'])/p['sr'];inner=(alpha>.99)&(r>1)&(r<1.5)
            matched=dict(tanh_inner_saturation=float(np.mean((tanh[inner]<=0)|(tanh[inner]>=1))),algebraic_inner_saturation=float(np.mean((q[inner]<=0)|(q[inner]>=1))))
            row=dict(mode=mode[0],resolution=resolution,contrast=BOUNDED_CONTRAST_LIMITS[mode[2]],prototype_difference=info['prototype_max_difference'],original_paths_exact=True,raw_matches_revised=True,alpha_exact=True,matched_gain_saturation=matched)
            native_rows.append(row);write(root/'native-validation.json',native_rows);resolution_results[resolution]=(q,alpha)
            print('NATIVE VERIFIED',row,flush=True)
            if resolution=='native':
                for policy,label in [('compatible','Compatible ring normalization'),('revised','Revised fixed signed scale'),('bounded','Bounded signed contrast')]:
                    if policy=='bounded':path=folder/'full-canvas-current-working-opacity.png'
                    else:path=(study/'01-Default-Filter-Baselines'/f'{index:02d}-{mode[0]}'/'native' if policy=='compatible' else study/'08-Normalization-Fixes-and-Extensive-Validation/04-Full-Canvas-Native-and-Preview-Comparisons'/f'{index:02d}-{mode[0]}'/'native')/'full-canvas-current-working-opacity.png'
                    with Image.open(path) as im:
                        im=im.convert('RGB');im.thumbnail((1000,650));panel=Image.new('RGB',(1000,700),'#202020');panel.paste(im,(0,35));ImageDraw.Draw(panel).text((8,8),label+'; same working opacity',fill='white');panels.append(panel)
        reduced=resize_observed(np.where(resolution_results['native'][1]>.99,resolution_results['native'][0],np.nan),(preview.shape[1],preview.shape[0]));mask=np.isfinite(reduced)&(resolution_results['preview'][1]>.99)
        write(root/'04-Full-Native-and-Preview'/f'{index:02d}-{mode[0]}'/'preview-comparison.json',dict(encoded_RMSE=float(np.sqrt(np.mean((reduced[mask]-resolution_results['preview'][0][mask])**2)))))
        sheet=Image.new('RGB',(3000,700),'#202020')
        for n,panel in enumerate(panels):sheet.paste(panel,(n*1000,0))
        sheet.save(root/'04-Full-Native-and-Preview'/f'{index:02d}-{mode[0]}'/'Three-Contrast-Paths-Native-Comparison.jpg')
    # Restore actual per-card GUI settings, then exercise full colour export.
    app=QApplication.instance() or QApplication([]);snapshot=json.load(open(study/'00-Test-Manifest-and-Current-Defaults/current-GUI-settings-snapshot.json'));snapshot['ui_mode']='expert'
    for name in (*ORDER,'achf'):snapshot['sections']['sec_'+name]['active']=name=='achf'
    for key,row in snapshot['sections'].items():
        if key.startswith('sec_achf'):row['active']=key!='sec_achf_adaptive'
    snapshot['controls']['chk_achf_adaptive']['value']=False;snapshot['controls']['chk_prominences']['value']=True
    for variant,limit in BOUNDED_CONTRAST_LIMITS.items():
        snapshot['controls'][f'achf_ael_controls.{variant}.enabled']['value']=True
        snapshot['controls'][f'achf_ael_controls.{variant}.encoding']=dict(kind='combo',value=1,text='Contrast: Bounded signed (experimental)')
        snapshot['controls'][f'achf_ael_controls.{variant}.contrast']=dict(kind='slider',value=int(limit*10))
    w=EclipseProcessorApp();w.auto_calculate=False;w.full_raw_image=full;w.raw_image=w.preview_image=preview;w._display_reference_source=full;w._display_bounds=loaded['display_bounds'];restore_settings(w,snapshot);p=w.collect_filter_parameters(full.shape,include_mask=False);saved=capture_settings(w);w.close();app.processEvents()
    export=root/'05-Native-Colour-PSB-Recipe-and-Prominence-Checks';export.mkdir();destination=export/'Bounded-AEL-ACHF-Native-Colour.tif';captured={}
    def capture(package,*args,**kwargs):
        captured['merged']=hashlib.sha256(np.ascontiguousarray(package.combined,dtype='<u2').tobytes()).hexdigest()
        captured['prominences']=[row.sha256() for row in package.layers if row.record.get('filter')=='prominences']
        captured['mappings']=[row.record for row in package.layers if row.record.get('filter')=='achf']
        return export_psb_layers(package,*args,**kwargs)
    worker=FilterWorker();engine=engine_for(worker)
    with filter_budget(8),patch('core.psb_export.export_psb_layers',side_effect=capture):
        export_images(full,p,{},str(destination),meta['source'],source_rgb=loaded['rgb'],calibrate_colour=True,white=loaded['white'],export_layers=True,layers_format='psb',layer_cache=engine,project_settings=saved,input_state='linear',original_rgb=loaded['rgb'],export_prominences=True,prominence_exposure_ev=-2.,prominence_saturation=.65,prominence_contrast=1.,prominence_edge_softness=3.)
    image=tifffile.imread(destination);assert image.shape==(*full.shape,3) and image.dtype==np.uint16
    assert hashlib.sha256(np.ascontiguousarray(image,dtype='<u2').tobytes()).hexdigest()==captured['merged']
    source,saved=read_settings(destination.with_suffix('.json'));verify=EclipseProcessorApp();verify.auto_calculate=False;verify.full_raw_image=full;verify.raw_image=verify.preview_image=preview;restore_settings(verify,saved)
    for variant,limit in BOUNDED_CONTRAST_LIMITS.items():assert verify.achf_ael_controls[variant]['encoding'].currentData()=='bounded' and verify.achf_ael_controls[variant]['contrast'].value()==int(limit*10)
    verify.close();app.processEvents();prior=json.load(open(study/'08-Normalization-Fixes-and-Extensive-Validation/06-Native-Colour-PSB-Recipe-and-Prominence-Checks/native-export-and-recipe-checks.json'));assert captured['prominences']==prior[0]['prominence_layer_hashes']
    write(export/'layer-mapping-receipts.json',captured['mappings']);assert digest(meta['source'])==EXPECTED
    write(root/'completion.json',dict(completed=True,source_unchanged=True,synthetic_cases=len(executions),injection_measurements=len(responses),native_preview_cases=len(native_rows),prototype_matches=True,original_pixels_exact=True,alpha_unchanged=True,raw_matches_revised=True,TIFF_matches_verified_PSB=True,original_prominence_layer_identical=True,settings_roundtrip=True,default_mapping_unchanged=True,contrast_limits=BOUNDED_CONTRAST_LIMITS))
    print('BOUNDED ACHF QUALIFICATION COMPLETED',flush=True)

if __name__=='__main__':main()
