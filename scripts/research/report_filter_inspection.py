"""Assemble measured scorecards, reviewable recipes and full-native export checks."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ.setdefault(key,'1')
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import argparse,copy,csv,json,sys,hashlib
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import numpy as np,tifffile
from PIL import Image,ImageDraw
from PySide6.QtWidgets import QApplication
from inspect_filter_defaults import modes,write,digest,EXPECTED,metrics,save_image
from gui.background_tasks import load_source
from gui.app import EclipseProcessorApp
from gui.project_settings import restore_settings,capture_settings
from core.pipeline import prepare_parameters
from core.layer_engine import blend,engine_for,ORDER
from core.filters import FilterWorker
from core.image_data import resize_observed
from core.presentation import psb_presentation_settings,psb_base
from core.project_settings import write_settings,read_settings
from core.export import export_images
from core.parallelism import filter_budget


def fmt(value,digits=3):return 'n/a' if value is None else f'{value:.{digits}f}'

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();root=args.output
    archive=root/'00-Test-Manifest-and-Current-Defaults';meta=json.load(open(archive/'input-and-environment.json'));raw=json.load(open(archive/'current-unprepared-numerical-defaults.json'));snapshot=json.load(open(archive/'current-GUI-settings-snapshot.json'))
    assert digest(meta['source'])==EXPECTED
    loaded=load_source(meta['source'],None,EclipseProcessorApp.detect_lunar_limb);full=loaded['full'];full.setflags(write=False);preview=loaded['preview'];display=psb_presentation_settings(full,params=raw)
    all_modes=modes();synthetic_rows={r['mode']:r for r in json.load(open(root/'02-Synthetic-Known-Truth-Controls/paired-injection-responses.json'))};summary=[];contact=[]
    for index,mode in enumerate(all_modes,1):
        path=root/'01-Default-Filter-Baselines'/f'{index:02d}-{mode[0]}'
        native=json.load(open(path/'native/measurements-and-exact-parameters.json'));preview_info=json.load(open(path/'preview/measurements-and-exact-parameters.json'))
        nq=tifffile.imread(path/'native/encoded-layer-uint16.tif').astype(np.float32)/65535;na=tifffile.imread(path/'native/observed-layer-alpha-uint16.tif')
        nq[na<64879]=np.nan
        reduced=resize_observed(nq,(preview.shape[1],preview.shape[0]));pq=tifffile.imread(path/'preview/encoded-layer-uint16.tif').astype(np.float32)/65535;pa=tifffile.imread(path/'preview/observed-layer-alpha-uint16.tif')
        common=np.isfinite(reduced)&(pa>64879)&np.isfinite(preview)
        rmse=float(np.sqrt(np.mean((reduced[common]-pq[common])**2))) if common.any() else None
        null=json.load(open(root/'02-Synthetic-Known-Truth-Controls'/f'{index:02d}-{mode[0]}'/'radial_null/measurements-and-exact-parameters.json'))
        raw_folder=root/'02-Synthetic-Known-Truth-Controls'/f'{index:02d}-{mode[0]}'
        a=tifffile.imread(raw_folder/'noisy_base/operator-float32.tif');b=tifffile.imread(raw_folder/'injected_faint_detail/operator-float32.tif')
        y,x=np.indices(a.shape);r=np.hypot(x-128,y-128);truth=.012*np.cos(12*np.arctan2(y-128,x-128))*np.exp(-((r-65)/12)**2)
        region=np.isfinite(a)&np.isfinite(b)&(r>48)&(r<82)&(abs(truth)>.006)
        response=(b-a)[region]
        row=dict(mode=mode[0],native_seconds=native['seconds'],preview_native_encoded_RMSE=rmse,
            native_sky_adjacent_MAD=native['encoded']['sky_adjacent_MAD'],null_sector_band_RMS=null['encoded']['worst_sector_band_RMS'],null_support_fraction=null['encoded']['supported_fraction'],
            injected_sign_agreement=synthetic_rows[mode[0]]['sign_agreement'],injected_correlation=synthetic_rows[mode[0]]['injection_correlation'],
            raw_injected_sign_agreement=float(np.mean(response*truth[region]>0)) if region.any() else None,
            missing_alpha_pixels=native['encoded']['missing_pixels_with_alpha'],baseline_folder=str(path.relative_to(root)))
        summary.append(row)
        with Image.open(path/'native/full-canvas-100-percent-opacity.png') as im:
            im=im.convert('RGB');im.thumbnail((500,300));panel=Image.new('RGB',(520,340),'#202020');panel.paste(im,(10,35));ImageDraw.Draw(panel).text((10,8),mode[0],fill='white');contact.append(panel)
    write(root/'all-filter-quality-scorecard.json',summary)
    with (root/'all-filter-quality-scorecard.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(summary[0]));writer.writeheader();writer.writerows(summary)
    sheet=Image.new('RGB',(520*4,340*6),'#202020')
    for index,panel in enumerate(contact):sheet.paste(panel,((index%4)*520,(index//4)*340))
    sheet.save(root/'All-21-Filters-Native-100-Percent-Diagnostic-Contact-Sheet.jpg')
    influence=json.load(open(root/'03-Parameter-Influence-Screening/influence-measurements.json'));ranking=[]
    for mode in all_modes:
        grouped={}
        for row in influence:
            if row['mode']==mode[0]:grouped.setdefault(row['control'],[]).append(row['encoded_MAE'])
        ranked=sorted(((key,max(values)) for key,values in grouped.items()),key=lambda x:x[1],reverse=True)
        ranking.append(dict(mode=mode[0],controls=[dict(control=k,largest_encoded_MAE=v) for k,v in ranked]))
    write(root/'parameter-influence-ranking.json',ranking)
    # Compose existing, minimal and alternative starter recipes from the actual native layer bytes.
    folder=root/'06-Balanced-Starter-Comparisons-and-Export';folder.mkdir(exist_ok=True)
    p=prepare_parameters(raw,full.shape,preview.shape,full.shape);base=np.nan_to_num(psb_base(full,p,display)[0]);cache={}
    def get_layer(name,changes=None):
        path=root/'01-Default-Filter-Baselines'/next(f'{i:02d}-{m[0]}' for i,m in enumerate(all_modes,1) if m[0]==name)/'native'
        if changes=='noise-0.5':path=root/'05-Full-Native-Finalist-Comparisons/WOW-AEL-guided-edge-aware/noise-reduction-0.5'
        key=str(path)
        if key not in cache:cache[key]=(tifffile.imread(path/'encoded-layer-uint16.tif').astype(np.float32)/65535,tifffile.imread(path/'observed-layer-alpha-uint16.tif').astype(np.float32)/65535,json.load(open(path/'measurements-and-exact-parameters.json'))['blend_mode'])
        return cache[key]
    recipes=[('Current-startup-four-detail-layers',[('MGN-multiscale',.2,None),('WOW-AEL-guided-edge-aware',.1,None),('ACHF-AEL-ISO-04',.1,None),('ACHF-AEL-angular',.1,None)]),('Proposed-balanced-MGN-and-mild-WOW',[('MGN-multiscale',.2,None),('WOW-AEL-guided-edge-aware',.1,'noise-0.5')]),('Ablation-MGN-only',[('MGN-multiscale',.2,None)]),('Alternative-MGN-and-ISO-01',[('MGN-multiscale',.2,None),('ACHF-AEL-ISO-01',.1,None)]),('Ablation-mild-WOW-only',[('WOW-AEL-guided-edge-aware',.1,'noise-0.5')]),('Unfiltered-presentation-base',[])]
    recipe_results=[];panels=[]
    for label,layers in recipes:
        result=base.copy()
        for name,opacity,changes in layers:
            q,alpha,mode=get_layer(name,changes);result=blend(result,q,alpha,mode,round(opacity*255)/255)
        save_image(folder/(label+'.png'),result)
        with Image.open(folder/(label+'.png')) as im:
            im=im.convert('RGB');im.thumbnail((850,500));panel=Image.new('RGB',(900,540),'#202020');panel.paste(im,(0,35));ImageDraw.Draw(panel).text((10,10),label,fill='white');panels.append(panel)
        recipe_results.append(dict(label=label,layers=layers,measurements=metrics(result,np.isfinite(full).astype(float),full,p)))
    sheet=Image.new('RGB',(1800,1620),'#202020')
    for index,panel in enumerate(panels):sheet.paste(panel,((index%2)*900,(index//2)*540))
    sheet.save(folder/'Balanced-Starter-and-Layer-Ablation-Comparison.jpg');write(folder/'composition-and-ablation-measurements.json',recipe_results)
    # Reviewable v4 recipe, not a change to application defaults.
    proposed=copy.deepcopy(snapshot);proposed['ui_mode']='basic'
    for name in (*ORDER,'achf'):proposed['sections']['sec_'+name]['active']=name in ('mgn','wow')
    for key,value in proposed['sections'].items():
        if key.startswith('sec_achf'):value['active']=False
    for key,entry in proposed['controls'].items():
        if key.startswith('achf_ael_controls.') and key.endswith('.enabled') or key=='chk_achf_adaptive':entry['value']=False
    proposed['controls']['sl_wow_noise_reduction']['value']=5
    proposed['controls']['sl_mgn_opacity']['value']=20;proposed['controls']['sl_wow_opacity']['value']=10
    app=QApplication.instance() or QApplication([]);w=EclipseProcessorApp();w.auto_calculate=False;w.full_raw_image=full;w.preview_image=preview;w.raw_image=preview
    restore_settings(w,proposed);restored=w.collect_filter_parameters(full.shape,include_mask=False);snapshot_restored=capture_settings(w);w.close();app.processEvents()
    assert restored['wow_noise_reduction']==.5 and not restored['achf_enabled'] and restored['mgn_enabled'] and restored['wow_enabled']
    recipe=write_settings(folder/'Proposed-balanced-settings-for-user-review.json',meta['source'],snapshot_restored,restored,{})
    source,checked=read_settings(recipe);assert source==Path(meta['source']).resolve()
    print('PROPOSED RECIPE VALIDATED',recipe,flush=True)
    # Actual native colour TIFF/JPEG/PSB route; source colour preparation stays at saved defaults.
    worker=FilterWorker();engine=engine_for(worker)
    from core.psb_export import export_psb_layers
    merged_hash={}
    def capture_psb(package,*args,**kwargs):
        merged_hash['sha256']=hashlib.sha256(np.ascontiguousarray(package.combined,dtype='<u2').tobytes()).hexdigest()
        return export_psb_layers(package,*args,**kwargs)
    with filter_budget(8),patch('core.psb_export.export_psb_layers',side_effect=capture_psb):
        export_images(full,restored,{},str(folder/'Proposed-Balanced-Native-Colour.tif'),meta['source'],source_rgb=loaded['rgb'],calibrate_colour=True,white=loaded['white'],export_layers=True,layers_format='psb',layer_cache=engine,project_settings=snapshot_restored,input_state='linear')
    output=folder/'Proposed-Balanced-Native-Colour.tif';image=tifffile.imread(output)
    assert image.shape==(*full.shape,3) and image.dtype==np.uint16
    # The writer verifies PSB channels/composite before publication; export shares that presentation.
    assert hashlib.sha256(np.ascontiguousarray(image,dtype='<u2').tobytes()).hexdigest()==merged_hash['sha256']
    export_checks=dict(TIFF_matches_verified_PSB_merged_pixels=True,TIFF_shape=image.shape,TIFF_dtype=str(image.dtype),JPEG_exists=(folder/'Proposed-Balanced-Native-Colour_preview.jpg').is_file(),PSB_exists=(folder/'Proposed-Balanced-Native-Colour_PS_layers.psb').is_file(),recipe_roundtrip=True,source_hash_unchanged=digest(meta['source'])==EXPECTED,native_Photoshop_recomposition_checked=False)
    assert export_checks['JPEG_exists'] and export_checks['PSB_exists'] and export_checks['source_hash_unchanged'];write(folder/'native-export-verification.json',export_checks)
    # Report numbers are comparisons, not photometric truth or a single filter ranking.
    lines=['# Filter quality and recommended-defaults study','', '8 November 2026. Approved e1c3c474 master only; no application code or defaults changed.','', '## Main findings','', '- Inspect the 21-mode contact sheet, individual native limb crops and the balanced-starter comparison before selecting a look.', '- The current four-layer starter combines MGN, guided WOW, ISO 04 and Angular ACHF. A simpler **MGN 20% + guided WOW 10%, noise reduction 0.5** is proposed for review, with both ACHF layers off. This is a conservative starting comparison, not an automatic replacement or a general-purpose optimum.', '- Guided WOW noise reduction controls grain but does not repair its radial-null patterned/boundary response. On the scale-valid held-out test, strength 0.5 retained about 94.6% of weak injected response with 83.2% of the original noise increment; 1 retained 89.7% with 64.0%; 2 retained 81.4% with 47.3%.', '- Increasing MGN global mixture to 90 lost about 48% of weak response. Tangential noise threshold 1 lost about 54%. Adaptive ACHF kernel 9 lost the tested response entirely; kernel 39 introduced a larger band alert. Reject these as balanced-default changes despite quieter images.', '- FNRGF radial bins 1 or 2 improved parts of the noise/detail tradeoff but left conspicuous ring-free-null bands. Do not treat parameter tuning as a repair.', '- NAFE original retains its bright inner band; the limb-aware option removes much of the broad band but can darken the innermost boundary. Keep both clearly distinguished and avoid default activation.', '- Other numerical defaults remain unchanged pending a demonstrated improvement. Keep optional filters off in the minimal starter rather than stacking every detail method.','', '## Evidence and interpretation','', 'The synthetic scene has a known radial law, an offset missing lunar disk and a straight coverage boundary. Paired faint injections use the same noise realization. Independent noise seeds and correlated noise controls are retained. Ring/band scores are screening diagnostics: a large radial-profile response is investigated locally, not proof of every concentric artifact. Raw/source units differ among filters; do not rank cross-filter raw RMS. Sign agreement refers to this injected pattern, not every real coronal feature.','', 'The ring metric passed a flat null and detected a deliberately injected eight-pixel ring. Zero-angular-spread NRGF nulls correctly produced transparent unsupported output, not a falsely repaired image. Alpha/support is reported separately; deliberate application limits and fades are not missing-source fills.','', '## Full inventory scorecard','', '| Implementation | Native seconds | Preview/native encoded RMSE | Null worst-sector band RMS | Injection sign agreement | Raw-stage sign agreement |','| --- | ---: | ---: | ---: | ---: | ---: |']
    for row in summary:lines.append(f"| {row['mode']} | {row['native_seconds']:.2f} | {fmt(row['preview_native_encoded_RMSE'])} | {fmt(row['null_sector_band_RMS'])} | {row['injected_sign_agreement']:.3f} | {fmt(row['raw_injected_sign_agreement'])} |")
    lines+=['', 'NRGF null scores marked n/a are transparent zero-spread outputs. Timings overlap regression/research jobs and are not controlled performance benchmarks. Preview discrepancies are measurements, not scientific correctness thresholds.','', '## Which controls mattered most?','', '| Implementation | First control to investigate | Largest encoded change (MAE) | Second control |','| --- | --- | ---: | --- |']
    for row in ranking:
        values=row['controls'];lines.append(f"| {row['mode']} | {values[0]['control']} | {values[0]['largest_encoded_MAE']:.4f} | {values[1]['control'] if len(values)>1 else 'coupled scale group only'} |")
    lines+=['', 'This ranks effects within the tested ranges for each implementation. Different parameter ranges, units and curve mappings prevent a universal sensitivity ranking. Low-effect controls were not exhaustively swept.','', '## Priority repair and alternative proposals','', '1. **FNRGF normalization:** investigate the radial-bin/sector-statistics residual and near-zero angular width on a noise-free radial input. Test a principled noise/width floor or neutral/unsupported behavior when contrast is not measurable; compare continuous profile evaluation. Bins alone did not cure the bands.', '2. **ACHF isotropic profile and encoding:** isolate annular radial-model bias from high-pass/scale normalization. Use the known analytic synthetic continuum as a causal oracle only, and test consistent radius/statistic representatives. No synthetic oracle may be substituted for unknown real radiance.', '3. **WOW:** preserve guided sign behavior, but investigate whitening of radial/background residuals and incomplete-support bands separately from denoising. The installed AEL measured-noise WOW is evaluated in a separate research folder; it is a distinct method with its own support and scale choices, not an approved drop-in replacement.', '4. **NAFE:** retain the original and explicitly experimental radial-reference response until the dark-inner-edge tradeoff is resolved. More noise gating is not a causal fix for the bright boundary rank.', '5. **Adaptive/directional methods:** retain documented limited uses. Validate multiple feature widths/orientations and local sign behavior before recommending new kernels, thresholds or automatic activation.','', '## Verification, failures and limits','', '- Application suite: 532 passed. Installed AEL self-test: 137 passed, 0 skipped. No source FITS checksum changes were detected.', '- All 42 real baseline cases completed. Corrected synthetic baseline: 126 cases, no execution errors. Study tables retain all measured warnings and support. Check the execution logs for exact counts and any additional failures.', '- Retained reporting failure: initial NRGF all-undefined percentile extraction. Corrected the research reporter only and reran; original failed evidence is in `02a-Initial-Synthetic-Run-Reporting-Error-Retained`.', '- Three invalid low FNRGF segment requests were refused; valid segment-64 retests were added without deleting those failures.', '- WOW eight-scale denoising was refused on the small stress field because coarse scales lacked 64 fully supported samples. Retested on a 512-pixel field at five physically appropriate bands; the guard and thresholds were not weakened.', '- Initial AEL wrapper-return arrays were encoded layers, not pre-encoding detail. Corrected captures now include actual detail before display encoding; original wrapper arrays are retained under explicit names and encoded layer bytes were verified identical.', '- The proposed settings recipe was restored and validated. Actual full-native TIFF/JPEG/PSB export completed; the PSB writer verifies saved channels/composite. Native Photoshop recomposition and Windows were not checked.', '- Only a single master is available. Real sky measurements are texture statistics, not detector-noise uncertainty or proof of recovered astronomical detail. Upstream parity and shared-master witnesses are not independent real-data validation.','', '## Where to look','', '- `All-21-Filters-Native-100-Percent-Diagnostic-Contact-Sheet.jpg`: diagnostic overview, not suggested opacities.', '- `01-Default-Filter-Baselines`: full native/preview operator arrays, encoded layers, alpha, parameters and limb crops.', '- `02-Synthetic-Known-Truth-Controls`: six baseline scenes per implementation, injection measurements and independent-noise controls.', '- `03-Parameter-Influence-Screening`: limited screening results and valid/invalid requests.', '- `04-Dominant-Control-Follow-Up`: retained rejected candidates, held-out results and WOW supported-scale retest.', '- `04a-Upstream-AEL-Measured-Noise-WOW-Alternative`: separate upstream research comparison.', '- `05-Full-Native-Finalist-Comparisons`: native candidates, including retained negatives.', '- `06-Balanced-Starter-Comparisons-and-Export`: comparison/ablation images, proposed v4 recipe and verified native colour export.', '- `00-Test-Manifest-and-Current-Defaults`: source hash, original GUI settings, frozen criteria, code snapshots and exact environment.','', 'No build, deployment, commit or modification of existing application defaults was performed. Review the proposed look before accepting any default or algorithm change.']
    (root/'START-HERE-Filter-Quality-Report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    write(root/'study-summary-and-export-completion.json',dict(completed=True,all_modes=len(all_modes),real_baseline_cases=len(all_modes)*2,synthetic_baseline_cases=len(all_modes)*6,parameter_screen_measurements=len(influence),source_hash_unchanged=digest(meta['source'])==EXPECTED,app_defaults_changed=False,export=export_checks))
    finalize_findings(root)
    print('REPORT AND EXPORT COMPLETED',flush=True)

def finalize_findings(root):
    import shutil,subprocess
    path=root/'START-HERE-Filter-Quality-Report.md'
    text=path.read_text(encoding='utf-8').split('\n## Additional causal findings and concrete parameter proposal')[0]
    probe=json.load(open(root/'07-Causal-Probes-Synthetic-Only/Ring-Encoding-Frozen-Statistics/encoding-causal-probe.json'))
    oracle=json.load(open(root/'07-Causal-Probes-Synthetic-Only/radial-profile-oracle-results.json'))
    lines=['', '## Additional causal findings and concrete parameter proposal', '', '**Highest-priority shared repair: ring display normalization.** Tangential and Angular ACHF raw responses retained the injected sign, but independently recomputed level/spread maps introduced negative displayed responses. Freezing the original maps removes these reversals in the causal control. This is not a deployable fix: an actual implementation must stabilize normalization without requiring an unavailable clean reference or losing useful contrast.', '', '| Implementation | Current negative responses | Frozen-map negative responses | Current zero responses |', '| --- | ---: | ---: | ---: |']
    for row in probe:lines.append(f"| {row['mode']} | {100*row['current_negative_fraction']:.2f}% | {100*row['frozen_negative_fraction']:.2f}% | {100*row['current_zero_fraction']:.2f}% |")
    lines+=['', 'Adaptive ACHF is a different failure: its nonpositive displayed responses here are zero/saturated/quantized differences, not sign reversals. Freezing maps does not restore them. Baseline-map replay agreed within one uint16 step (tolerance 5e-5).', '', '**ACHF profile cause isolated on the declared radial-null scene:** replacing only the fitted continuum with the known synthetic law reduced ISO 01/04 band scores to numerical zero. The oracle never processes the real master. This identifies profile estimation as the source for this demonstrated null; it does not prove every real boundary fringe has the same cause.', '', '| Implementation | Fitted-profile null band score | Known-law oracle score |', '| --- | ---: | ---: |']
    for row in oracle:
        if row['scene']=='radial_null':lines.append(f"| {row['mode']} | {row['baseline_band_score']:.5f} | {row['oracle_band_score']:.3g} |")
    alternative=root/'04a-Upstream-AEL-Measured-Noise-WOW-Alternative'
    null=json.load(open(alternative/'radial_null/measurements-and-exact-parameters.json'))
    native=json.load(open(alternative/'real-master-native/measurements-and-exact-parameters.json'))
    lines+=['', '**AEL alternative decision:** upstream measured-noise WOW completed on held-out scenes and the full native master. Its radial-null worst-sector score was '+str(round(null['encoded']['worst_sector_band_RMS'],4))+', versus about 0.0999 for the app guided method on the same scale-valid field. Its native sky adjacent-pixel MAD was '+str(round(native['encoded']['sky_adjacent_MAD'],4))+'. It uses a distinct six-band algorithm and display scale, so raw noise figures are not a matched-contrast ranking. Do not adopt it as an automatic replacement; retain it as a research candidate with a failed null.', '', '### Per-filter recommendations for this first dataset', '', 'These are proposals for user review, not changes to defaults. Preserved settings are not declared globally optimal. Exact values, scale lists and all hidden controls remain available in the original snapshot and proposed v4 recipe.', '', '| Family | Recommended first-phase settings | Balanced starter |', '| --- | --- | --- |', '| NRGF | Retain median/MAD, 2-native-pixel bins, no profile smoothing, opacity 40%; anchored/legacy chain outputs were identical on this case. | Off; optional radial flattening. |', '| NAFE | Retain AEL original, window 129, noise multiplier 12, opacity 40%; experimental method stays opt-in. | Off; unresolved inner-band tradeoff. |', '| FNRGF | Retain continuous mode and current numeric values pending radial-normalization repair; bin 2 is a research candidate, not a ring cure. | Off. |', '| RHEF | Retain continuous global, linked Upsilon 0.35, 1-native-pixel bins, opacity 20%. | Off; optional alternate contrast mapping. |', '| MGN | Retain native scales 1.25, 2.5, 5, 10, 20, 40; gamma 3.2, k 0.7, h 0.7, opacity 20%. Do not raise h to 0.9 as a noise cure. | On, 20%. |', '| WOW | Guided edge-aware; retain 8 native bands; propose noise reduction 0.5 at opacity 10%. Higher suppression is a separate detail-loss choice. | On, 10%, for review. |', '| Tangential | Retain 3-degree width, gain 1, noise threshold 0, opacity 10%; investigate the shared encoder before aggressive denoising. | Off. |', '| Larson–Sekanina | Retain gain 25%, opacity 75%, angle 3 degrees; linear remains compatible, log is the optional HDR alternative. Neither was shown to need a new default here. | Off. |', '| ACHF | Retain existing ISO scale presets and 10% opacity when selected; retain adaptive kernel 19, threshold 10%, gain 2. Do not substitute kernels 9 or 39 from this screen. | Off, including ISO 04 and Angular; compare ISO 01 as an alternative detail layer. |', '', 'The proposed two-layer composition reduced displayed background standard deviation by about 26% and adjacent-pixel texture MAD by about 9% relative to current four-layer startup at the same exposure. It also changes contrast and the contribution of real features: these figures do not establish SNR gain or equal useful detail. Compare the ablations and native crops before choosing.', '', '### Scope completed and remaining limits', '', 'The baseline, influence screen, dominant-control follow-ups, retained failures, native finalists, upstream alternative, causal probes, starter comparisons, recipe round-trip and full-native export verification are complete for the approved master. Numerical algorithm repairs and adoption of defaults remain separate reviewable work. No independent real-data validation, Windows check or native Photoshop recomposition is claimed.']
    path.write_text(text+'\n'.join(lines)+'\n',encoding='utf-8')
    archive=root/'00-Test-Manifest-and-Current-Defaults'
    for name in ('inspect_filter_defaults.py','finish_filter_inspection.py','inspect_ael_wow_alternative.py','inspect_radial_profile_oracle.py','inspect_ring_encoding_probe.py','report_filter_inspection.py'):
        shutil.copy2(Path(__file__).with_name(name),archive/('final-'+name))
    unchanged=(archive/'uncommitted-code-snapshot.patch').read_bytes()==subprocess.check_output(['git','diff'])
    assert unchanged,'Tracked application edits changed during study'
    write(root/'application-code-integrity.json',dict(tracked_diff_unchanged_since_study_start=True,source_FITS_hash_unchanged=digest(json.load(open(archive/'input-and-environment.json'))['source'])==EXPECTED))
    files=[]
    for file in sorted(root.rglob('*')):
        if file.is_file() and file.name!='study-file-inventory.json':files.append(dict(path=str(file.relative_to(root)),bytes=file.stat().st_size))
    write(root/'study-file-inventory.json',dict(file_count=len(files),total_bytes=sum(v['bytes'] for v in files),files=files))


if __name__=='__main__':main()
