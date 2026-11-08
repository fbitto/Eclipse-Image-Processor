"""Targeted follow-up of measured dominant controls; no application changes."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ.setdefault(key,'1')
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import argparse,copy,json,sys,time,shutil
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import numpy as np,tifffile
from inspect_filter_defaults import modes,parameters,calculate,save_case,write,digest,EXPECTED,metrics
from gui.background_tasks import load_source
from gui.app import EclipseProcessorApp
from core.presentation import psb_presentation_settings,psb_base
from core.parallelism import filter_budget


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--phase',choices=['candidates','wow-retest','native-finalists','operator-evidence'],required=True);args=parser.parse_args()
    root=args.output;manifest=root/'00-Test-Manifest-and-Current-Defaults'
    raw=json.load(open(manifest/'current-unprepared-numerical-defaults.json'))
    meta=json.load(open(manifest/'input-and-environment.json'));source=meta['source']
    assert digest(source)==EXPECTED
    loaded=load_source(source,None,EclipseProcessorApp.detect_lunar_limb);full=loaded['full'];preview=loaded['preview'];display=psb_presentation_settings(full,params=raw)
    all_modes=modes();by_name={m[0]:m for m in all_modes};errors=[];results=[]
    if args.phase in ('candidates','wow-retest'):
        parent=root/'04-Dominant-Control-Follow-Up'
        if args.phase=='wow-retest':parent=parent/'WOW-Supported-Scale-Held-Out-Retest'
        parent.mkdir(exist_ok=True)
        write(parent/'candidate-screening-criteria-before-testing.json',dict(weak_response_retention_min=.8,sign_agreement_drop_max=.02,noise_increment_ratio_max=.9,new_ring_alert=.03,new_ring_relative_increase=1.25,role='conservative candidate screening, not independent scientific certification',held_out_seed=908))
        candidates=[('WOW-AEL-guided-edge-aware','noise-reduction-0.5',dict(wow_noise_reduction=.5)),('WOW-AEL-guided-edge-aware','noise-reduction-1',dict(wow_noise_reduction=1.)),('WOW-AEL-guided-edge-aware','noise-reduction-2',dict(wow_noise_reduction=2.)),('MGN-multiscale','global-mixture-90',dict(mgn_h=90)),('FNRGF-continuous-STD','radial-bin-1-native-pixel',dict(fnrgf_bin_px=1)),('FNRGF-continuous-STD','radial-bin-2-native-pixels',dict(fnrgf_bin_px=2)),('FNRGF-continuous-STD','harmonic-order-1',dict(fnrgf_ord=1)),('RHEF-continuous-global','linked-Upsilon-70',dict(rhef_upsilon=70,rhef_upsilon_high=70)),('Tangential-angular-detail','noise-threshold-1',dict(tangential_denoise=1)),('ACHF-adaptive-circular','kernel-9-preview-pixels',dict(achf_kernel=9)),('ACHF-adaptive-circular','kernel-39-preview-pixels',dict(achf_kernel=39))]
        if args.phase=='wow-retest':candidates=[v for v in candidates if v[0]=='WOW-AEL-guided-edge-aware']
        write(parent/'frozen-candidate-list.json',[dict(mode=name,label=label,changes=changes) for name,label,changes in candidates])
        size=512 if args.phase=='wow-retest' else 256;center=size//2
        y,x=np.indices((size,size));r=np.hypot(x-center,y-center);theta=np.arctan2(y-center,x-center)
        radial=(.05+np.maximum(r/30,1.)**-3).astype(np.float32);clean=radial*(1+.08*np.cos(5*theta));noise=np.random.default_rng(908).normal(0,.001,r.shape).astype(np.float32)
        weak=(.003*np.cos(12*theta)*np.exp(-((r-65)/12)**2)).astype(np.float32);strong=weak*4
        valid=(np.hypot(x-(center+7),y-(center-4))>30)&(x<size-18)&(y>12)
        inputs=dict(radial_null=radial,clean_angular=clean,noisy_base=clean+noise,weak_injection=clean+noise+weak,strong_injection=clean+noise+strong)
        synthetic=copy.deepcopy(raw);synthetic.update(sx=float(center),sy=float(center),sr=30.,fnrgf_rmax=50)
        if args.phase=='wow-retest':synthetic['wow_scales']=5
        inputs_dir=parent/'Held-Out-Test-Inputs';inputs_dir.mkdir(exist_ok=True)
        for key,a in inputs.items():
            a=a.copy();a[~valid]=np.nan;inputs[key]=a;tifffile.imwrite(inputs_dir/(key+'.tif'),a)
        comparison_cache={}
        for name,label,changes in candidates:
            mode=by_name[name];folder=parent/name/label
            try:
                for tag,overrides in [('baseline',{}),('candidate',changes)]:
                    if tag=='baseline' and name in comparison_cache:continue
                    outputs={}
                    for scene,a in inputs.items():
                        p=parameters(synthetic,mode,a.shape,a.shape,a.shape,overrides)
                        layer,operator,seconds,notes=calculate(a,p,mode)
                        info,q,alpha,_=save_case(folder/tag/scene,a,p,mode,layer,operator,np.nan_to_num(radial),seconds,notes,1.,arrays=True)
                        outputs[scene]=(q,alpha,info)
                    if tag=='baseline':comparison_cache[name]=outputs
                base_outputs=comparison_cache[name];candidate_outputs=outputs
                summaries={}
                for tag,outs in [('baseline',base_outputs),('candidate',candidate_outputs)]:
                    q,alpha,_=outs['noisy_base'];clean_q,ca,_=outs['clean_angular']
                    sky=valid&(r>120)&(alpha>.99)&(ca>.99)
                    entry=dict(noise_increment_std=float(np.std((q-clean_q)[sky])),null_worst_sector=outs['radial_null'][2]['encoded']['worst_sector_band_RMS'])
                    for scene,signal in [('weak_injection',weak),('strong_injection',strong)]:
                        a,aa,_=outs[scene];region=valid&(alpha>.99)&(aa>.99)&(r>48)&(r<82)&(abs(signal)>.5*np.max(abs(signal)))
                        delta=(a-q)[region];truth=signal[region]
                        entry[scene]=dict(response_RMS=float(np.sqrt(np.mean(delta**2))),sign_agreement=float(np.mean(delta*truth>0)),correlation=float(np.corrcoef(delta,truth)[0,1]) if np.std(delta)>0 else 0.)
                    summaries[tag]=entry
                b=summaries['baseline'];c=summaries['candidate']
                retention=c['weak_injection']['response_RMS']/max(b['weak_injection']['response_RMS'],1e-12)
                noise_ratio=c['noise_increment_std']/max(b['noise_increment_std'],1e-12)
                ring_bad=c['null_worst_sector'] is not None and c['null_worst_sector']>.03 and c['null_worst_sector']>1.25*(b['null_worst_sector'] or 0)
                row=dict(mode=name,label=label,changes=changes,measurements=summaries,weak_response_retention=retention,noise_increment_ratio=noise_ratio,new_ring_alert=ring_bad,
                    conservative_screen_pass=bool(retention>=.8 and noise_ratio<=.9 and not ring_bad and c['weak_injection']['sign_agreement']>=b['weak_injection']['sign_agreement']-.02))
                results.append(row);write(parent/'candidate-screening-results.json',results)
                # Real preview comparison uses the complete field for every candidate.
                p=parameters(raw,mode,preview.shape,full.shape,preview.shape,changes);base,_=psb_base(preview,p,display)
                layer,operator,seconds,notes=calculate(preview,p,mode)
                save_case(folder/'real-master-preview',preview,p,mode,layer,operator,np.nan_to_num(base),seconds,notes,p['nrgf_scale'])
                print('CANDIDATE',name,label,'retention',round(retention,3),'noise ratio',round(noise_ratio,3),'screen',row['conservative_screen_pass'],flush=True)
            except Exception as exc:
                folder.mkdir(parents=True,exist_ok=True);import traceback;(folder/'FAILED-traceback.txt').write_text(traceback.format_exc());errors.append([name,label,str(exc)]);print('FAILED',errors[-1],flush=True)
        # Retest only the invalid low segment requests at a valid higher count; retain initial failures.
        rows=json.load(open(root/'03-Parameter-Influence-Screening/influence-measurements.json'))
        for mode in (all_modes if args.phase=='candidates' else []):
            if mode[1]!='fnrgf':continue
            p=parameters(raw,mode,preview.shape,full.shape,preview.shape);baseline,_,_,_=calculate(preview,p,mode)
            pp=parameters(raw,mode,preview.shape,full.shape,preview.shape,dict(fnrgf_seg=64));layer,operator,seconds,notes=calculate(preview,pp,mode);base,_=psb_base(preview,pp,display)
            folder=root/'03-Parameter-Influence-Screening'/f'{all_modes.index(mode)+1:02d}-{mode[0]}'/'fnrgf_seg-valid-64-retest'
            _,q,alpha,_=save_case(folder,preview,pp,mode,layer,operator,np.nan_to_num(base),seconds,notes,pp['nrgf_scale'])
            common=(alpha>.99)&(baseline['alpha']>64879)&np.isfinite(preview);delta=q[common]-baseline['image'][common]/65535
            rows.append(dict(mode=mode[0],control='fnrgf_seg',test='valid-64-retest',value=64,encoded_MAE=float(np.mean(abs(delta))),encoded_p95_absolute_change=float(np.percentile(abs(delta),95)),common_support_fraction=float(common.sum()/np.isfinite(preview).sum()),measurement_file=str((folder/'measurements-and-exact-parameters.json').relative_to(root))))
        if args.phase=='candidates':write(root/'03-Parameter-Influence-Screening/influence-measurements.json',rows)
        else:
            path=root/'04-Dominant-Control-Follow-Up/candidate-screening-results.json'
            previous=json.load(open(path))
            for row in results:row['synthetic_scene']='512-pixel field; five supported bands, matching approximate native physical footprint'
            write(path,previous+results)
    elif args.phase=='native-finalists':
        rows=json.load(open(root/'04-Dominant-Control-Follow-Up/candidate-screening-results.json'))
        # Qualify each repair hypothesis on the complete native field, including retained negatives.
        chosen=[row for row in rows if row['conservative_screen_pass'] or row['label'] in ('radial-bin-1-native-pixel','radial-bin-2-native-pixels','kernel-9-preview-pixels')]
        for row in chosen:
            mode=by_name[row['mode']];p=parameters(raw,mode,full.shape,full.shape,preview.shape,row['changes']);base,_=psb_base(full,p,display)
            folder=root/'05-Full-Native-Finalist-Comparisons'/row['mode']/row['label']
            try:
                if (folder/'measurements-and-exact-parameters.json').exists():continue
                layer,operator,seconds,notes=calculate(full,p,mode)
                info,_,_,_=save_case(folder,full,p,mode,layer,operator,np.nan_to_num(base),seconds,notes,1.,arrays=True)
                results.append(dict(mode=row['mode'],label=row['label'],changes=row['changes'],synthetic_screen_pass=row['conservative_screen_pass'],seconds=seconds))
                print('NATIVE FINALIST',row['mode'],row['label'],seconds,flush=True)
            except Exception as exc:
                import traceback;folder.mkdir(parents=True,exist_ok=True);(folder/'FAILED-traceback.txt').write_text(traceback.format_exc());errors.append([row['mode'],row['label'],str(exc)])
        path=root/'05-Full-Native-Finalist-Comparisons/native-finalist-index.json'
        write(path,(json.load(open(path)) if path.exists() else [])+results)
    else:
        for index,mode in enumerate(all_modes,1):
            if not (mode[1]=='wow' and mode[3].get('wow_mode')=='ael_bilateral' or mode[1]=='achf' and mode[2]!='adaptive'):continue
            for label,a in [('preview',preview),('native',full)]:
                folder=root/'01-Default-Filter-Baselines'/f'{index:02d}-{mode[0]}'/label
                p=parameters(raw,mode,a.shape,full.shape,preview.shape);layer,operator,seconds,notes=calculate(a,p,mode)
                np.testing.assert_array_equal(layer['image'],tifffile.imread(folder/'encoded-layer-uint16.tif'))
                original=folder/'operator-float32.tif';retained=folder/'initial-wrapper-return-encoded-float32.tif'
                if not retained.exists():shutil.copy2(original,retained)
                tifffile.imwrite(original,operator.astype(np.float32),compression='zlib')
                info=json.load(open(folder/'measurements-and-exact-parameters.json'));info['operator']=dict(stage='detail before layer display encoding',finite_fraction=float(np.isfinite(operator[np.isfinite(a)]).mean()),percentiles=np.percentile(operator[np.isfinite(operator)],[0,1,50,99,100]).tolist());write(folder/'measurements-and-exact-parameters.json',info)
                print('RAW DETAIL VERIFIED',mode[0],label,flush=True)
            # Synthetic detail capture is cheap; keep initial wrapper arrays under explicit names.
            scenes=root/'02-Synthetic-Known-Truth-Controls';synthetic=copy.deepcopy(raw);synthetic.update(sx=128.,sy=128.,sr=30.,fnrgf_rmax=50)
            for source_file in scenes.glob('input-*.tif'):
                scene=source_file.stem.removeprefix('input-');a=tifffile.imread(source_file);p=parameters(synthetic,mode,a.shape,a.shape,a.shape)
                layer,operator,_,_=calculate(a,p,mode);folder=scenes/f'{index:02d}-{mode[0]}'/scene
                np.testing.assert_array_equal(layer['image'],tifffile.imread(folder/'encoded-layer-uint16.tif'))
                path=folder/'operator-float32.tif';retained=folder/'initial-wrapper-return-encoded-float32.tif'
                if not retained.exists():shutil.copy2(path,retained)
                tifffile.imwrite(path,operator.astype(np.float32),compression='zlib')
                info=json.load(open(folder/'measurements-and-exact-parameters.json'));info['operator']=dict(stage='detail before layer display encoding',finite_fraction=float(np.isfinite(operator[np.isfinite(a)]).mean()),percentiles=np.percentile(operator[np.isfinite(operator)],[0,1,50,99,100]).tolist());write(folder/'measurements-and-exact-parameters.json',info)
    assert digest(source)==EXPECTED
    write(root/(args.phase+'-completion.json'),dict(completed=True,source_hash_unchanged=True,errors=errors))
    print('FOLLOW-UP COMPLETED',args.phase,'errors',len(errors),flush=True)

if __name__=='__main__':main()
