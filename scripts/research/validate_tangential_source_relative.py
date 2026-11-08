"""Qualification of the optional source-relative Tangential implementation."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ.setdefault(key,'1')
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import argparse,copy,json,sys,hashlib,subprocess,shutil
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import numpy as np,tifffile
from PIL import Image,ImageDraw
from scipy.ndimage import gaussian_filter
from inspect_filter_defaults import modes,parameters,calculate,save_case,write,digest,EXPECTED
from investigate_outer_detail_contrast import scales,encode
from core.statistics_support import statistics_support
from core.image_data import resize_observed
from core.parallelism import filter_budget
from core.layer_engine import LayerEngine,engine_for,ORDER
from core.filters import FilterWorker
from core.export import export_images
from core.psb_export import export_psb_layers
from core.project_settings import read_settings
from core.presentation import psb_base,psb_presentation_settings
from gui.background_tasks import load_source
from gui.app import EclipseProcessorApp
from gui.project_settings import restore_settings,capture_settings
from PySide6.QtWidgets import QApplication
from unittest.mock import patch


def render(a,p,mode,folder,base,scale):
    layer,detail,seconds,notes=calculate(a,p,mode)
    info,q,alpha,composition=save_case(folder,a,p,mode,layer,detail,base,seconds,notes,scale,arrays=True)
    if p.get('tangential_encoding')=='source_relative':
        samples=statistics_support(a,p,np.isfinite(a));reference=scales(a,samples,p,True)
        expected=encode(detail,reference,p['tangential_gain'],'fractional-source-contrast')
        valid=(alpha>.99)&np.isfinite(a)&np.isfinite(expected)
        difference=float(np.max(abs(expected[valid]-q[valid])))
        assert difference<=2/65535,(folder,difference)
        info['research_formula_max_difference']=difference
        assert info['encoded']['missing_pixels_with_alpha']==0
    return info,q,alpha,detail


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--study',type=Path,required=True);args=parser.parse_args();study=args.study;root=study/'10-Source-Relative-Tangential-Implementation-and-Validation'
    raw=json.load(open(study/'00-Test-Manifest-and-Current-Defaults/current-unprepared-numerical-defaults.json'));meta=json.load(open(study/'00-Test-Manifest-and-Current-Defaults/input-and-environment.json'));assert digest(meta['source'])==EXPECTED
    archive=root/'Source-and-Criteria';archive.mkdir()
    write(archive/'frozen-criteria.json',dict(prototype_pixel_tolerance=2/65535,null_sector_alert=.03,negative_fraction_max=.001,zero_fraction_max=.02,source_and_alpha_unchanged=True,preview='measure and report; no claim of resampling invariance'))
    for path in ('core/tangential_encoding.py','core/layer_engine.py','gui/filter_controls.py','tests/test_tangential_source_relative.py','scripts/research/validate_tangential_source_relative.py'):
        shutil.copy2(path,archive/path.replace('/','--'))
    (archive/'tracked-diff.patch').write_bytes(subprocess.check_output(['git','diff']))
    mode=next(m for m in modes() if m[0]=='Tangential-angular-detail');rows=[]
    inputs={p.stem:tifffile.imread(p) for p in (study/'09-Outer-Detail-Contrast-Investigation/Synthetic-Inputs').glob('*.tif')}
    y,x=np.indices((512,512));r=np.hypot(x-256,y-256);valid=np.isfinite(inputs['radial_null']);radial=inputs['radial_null']
    noise=gaussian_filter(np.random.default_rng(734).normal(size=r.shape),1.)
    noise=noise/np.std(noise)*.001
    correlated=(np.nan_to_num(radial)+noise).astype(np.float32);correlated[~valid]=np.nan
    gradient=(radial+.00005*(x-256)).astype(np.float32)
    spike=inputs['noisy'].copy();spike[100,450]=np.nanmax(spike)*100
    inputs.update(correlated_noise=correlated,sky_gradient=gradient,single_bright_spike=spike,flat=np.where(valid,1.,np.nan).astype(np.float32))
    folder=root/'02-Synthetic-Inputs';folder.mkdir()
    outputs={};synthetic=copy.deepcopy(raw);synthetic.update(sx=256.,sy=256.,sr=30.)
    for scene,a in inputs.items():
        tifffile.imwrite(folder/(scene+'.tif'),a)
        p=parameters(synthetic,mode,a.shape,a.shape,a.shape,dict(tangential_encoding='source_relative',normalization_mode='revised'))
        info,q,alpha,detail=render(a,p,mode,root/'03-Synthetic-Qualification'/scene,np.nan_to_num(a/np.nanmax(a)),1.)
        outputs[scene]=(q,alpha,detail,info)
        rows.append(dict(scene=scene,prototype_max_difference=info['research_formula_max_difference'],null_band=info['encoded']['worst_sector_band_RMS'],noise_sigma=info['mapping']['source_noise_sigma'],noise_fallback=info['mapping']['noise_fallback']))
        print('SYNTHETIC',rows[-1],flush=True)
    responses=[]
    for radius in (2,4,6):
        q,alpha,_,_=outputs[f'injected-{radius}R'];b,ba,_,_=outputs['noisy'];signal=.003*np.cos(12*np.arctan2(y-256,x-256))*np.exp(-((r-radius*30)/9)**2)
        mask=(alpha>.99)&(ba>.99)&(abs(signal)>.0015)
        delta=(q-b)[mask];truth=signal[mask]
        row=dict(radius=radius,negative_fraction=float(np.mean(delta*truth<0)),zero_fraction=float(np.mean(delta==0)),correlation=float(np.corrcoef(delta,truth)[0,1]))
        assert row['negative_fraction']<=.001 and row['zero_fraction']<.02
        responses.append(row)
    assert outputs['radial_null'][3]['encoded']['worst_sector_band_RMS']<.03
    write(root/'synthetic-qualification.json',dict(cases=rows,injections=responses))
    loaded=load_source(meta['source'],None,EclipseProcessorApp.detect_lunar_limb);full=loaded['full'];preview=loaded['preview'];full.setflags(write=False);display=psb_presentation_settings(full,params=raw);native={}
    for resolution,a in [('preview',preview),('native',full)]:
        p=parameters(raw,mode,a.shape,full.shape,preview.shape,dict(tangential_encoding='source_relative'));base=np.nan_to_num(psb_base(a,p,display)[0])
        info,q,alpha,detail=render(a,p,mode,root/'04-Approved-Master'/resolution,base,p['nrgf_scale'])
        for policy,prior_folder in [('compatible',study/'01-Default-Filter-Baselines/15-Tangential-angular-detail'/resolution),('revised',study/'08-Normalization-Fixes-and-Extensive-Validation/04-Full-Canvas-Native-and-Preview-Comparisons/15-Tangential-angular-detail'/resolution)]:
            old_p=parameters(raw,mode,a.shape,full.shape,preview.shape,dict(tangential_encoding='normalization',normalization_mode=policy))
            old,old_detail,_,_=calculate(a,old_p,mode)
            np.testing.assert_array_equal(old['image'],tifffile.imread(prior_folder/'encoded-layer-uint16.tif'))
            np.testing.assert_array_equal(old['alpha'],np.uint16(np.round(alpha*65535)))
            np.testing.assert_array_equal(detail,old_detail)
        native[resolution]=(q,alpha,info)
        print('NATIVE/PREVIEW VERIFIED',resolution,info['research_formula_max_difference'],flush=True)
    reduced=resize_observed(np.where(native['native'][1]>.99,native['native'][0],np.nan),(preview.shape[1],preview.shape[0]))
    common=np.isfinite(reduced)&(native['preview'][1]>.99)
    comparison=dict(encoded_RMSE=float(np.sqrt(np.mean((reduced[common]-native['preview'][0][common])**2))),preview_noise_sigma=native['preview'][2]['mapping']['source_noise_sigma'],native_noise_sigma=native['native'][2]['mapping']['source_noise_sigma'],common_pixels=int(common.sum()),note='Approximate: noise and continuum estimated at target resolution')
    write(root/'preview-native-comparison.json',comparison)
    # Actual GUI snapshot and full native colour export, with original prominences.
    app=QApplication.instance() or QApplication([]);snapshot=json.load(open(study/'00-Test-Manifest-and-Current-Defaults/current-GUI-settings-snapshot.json'));snapshot['ui_mode']='standard'
    snapshot['controls']['combo_tangential_encoding']=dict(kind='combo',value=1,text='Contrast: Source-relative (experimental)')
    for name in (*ORDER,'achf'):snapshot['sections']['sec_'+name]['active']=name=='tangential'
    for key,row in snapshot['sections'].items():
        if key.startswith('sec_achf'):row['active']=False
    snapshot['controls']['chk_prominences']['value']=True
    w=EclipseProcessorApp();w.auto_calculate=False;w.full_raw_image=full;w.raw_image=w.preview_image=preview;w._display_reference_source=full;w._display_bounds=loaded['display_bounds'];restore_settings(w,snapshot)
    p=w.collect_filter_parameters(full.shape,include_mask=False);saved=capture_settings(w);assert p['tangential_encoding']=='source_relative';w.close();app.processEvents()
    export_dir=root/'05-Native-Colour-TIFF-JPEG-PSB-and-Recipe';export_dir.mkdir()
    captured={}
    def capture(package,*args,**kwargs):
        captured['merged']=hashlib.sha256(np.ascontiguousarray(package.combined,dtype='<u2').tobytes()).hexdigest()
        captured['prominences']=[v.sha256() for v in package.layers if v.record.get('filter')=='prominences']
        captured['mapping']=next(v.record['normalization'] for v in package.layers if v.record.get('filter')=='tangential')
        return export_psb_layers(package,*args,**kwargs)
    destination=export_dir/'Source-Relative-Tangential-Native-Colour.tif';worker=FilterWorker();engine=engine_for(worker)
    with filter_budget(8),patch('core.psb_export.export_psb_layers',side_effect=capture):
        export_images(full,p,{},str(destination),meta['source'],source_rgb=loaded['rgb'],calibrate_colour=True,white=loaded['white'],export_layers=True,layers_format='psb',layer_cache=engine,project_settings=saved,input_state='linear',original_rgb=loaded['rgb'],export_prominences=True,prominence_exposure_ev=-2.,prominence_saturation=.65,prominence_contrast=1.,prominence_edge_softness=3.)
    image=tifffile.imread(destination);assert image.shape==(*full.shape,3) and image.dtype==np.uint16
    assert hashlib.sha256(np.ascontiguousarray(image,dtype='<u2').tobytes()).hexdigest()==captured['merged']
    recipe=destination.with_suffix('.json');source,settings=read_settings(recipe);verify=EclipseProcessorApp();verify.auto_calculate=False;verify.full_raw_image=full;verify.raw_image=verify.preview_image=preview;restore_settings(verify,settings);assert verify.combo_tangential_encoding.currentData()=='source_relative';verify.close();app.processEvents()
    prior=json.load(open(study/'08-Normalization-Fixes-and-Extensive-Validation/06-Native-Colour-PSB-Recipe-and-Prominence-Checks/native-export-and-recipe-checks.json'))
    assert captured['prominences']==prior[0]['prominence_layer_hashes']
    assert digest(meta['source'])==EXPECTED
    write(root/'completion.json',dict(completed=True,synthetic_cases=len(rows),injections=responses,prototype_parity=True,legacy_image_parity=True,raw_operator_unchanged=True,alpha_unchanged=True,preview=comparison,TIFF_matches_verified_PSB=True,original_prominence_layer_identical=True,settings_roundtrip=True,source_unchanged=True,mode_is_optional=True))
    write(export_dir/'export-mapping.json',captured['mapping']);print('QUALIFICATION COMPLETED',flush=True)

if __name__=='__main__':main()
