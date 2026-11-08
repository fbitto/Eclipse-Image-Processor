"""Full-native colour/PSB/recipe and original-prominence checks for both normalization paths."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ.setdefault(key,'1')
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import argparse,copy,hashlib,json,sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import numpy as np,tifffile
from PIL import Image,ImageDraw
from PySide6.QtWidgets import QApplication
from inspect_filter_defaults import write,digest,EXPECTED
from gui.background_tasks import load_source
from gui.app import EclipseProcessorApp
from gui.project_settings import restore_settings,capture_settings
from core.project_settings import write_settings,read_settings
from core.filters import FilterWorker
from core.layer_engine import engine_for,ORDER
from core.parallelism import filter_budget
from core.export import export_images
from core.psb_export import export_psb_layers


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--study',type=Path,required=True);args=parser.parse_args();study=args.study;root=study/'08-Normalization-Fixes-and-Extensive-Validation/06-Native-Colour-PSB-Recipe-and-Prominence-Checks';root.mkdir(exist_ok=True)
    meta=json.load(open(study/'00-Test-Manifest-and-Current-Defaults/input-and-environment.json'));settings=json.load(open(study/'00-Test-Manifest-and-Current-Defaults/current-GUI-settings-snapshot.json'))
    assert digest(meta['source'])==EXPECTED
    loaded=load_source(meta['source'],None,EclipseProcessorApp.detect_lunar_limb);full=loaded['full'];rgb=loaded['rgb'];full.setflags(write=False)
    source_hash=hashlib.sha256(full.tobytes()).hexdigest();rgb_hash=hashlib.sha256(rgb.tobytes()).hexdigest()
    app=QApplication.instance() or QApplication([]);records=[];panels=[]
    for policy in ('compatible','revised'):
        folder=root/('Original-Compatible' if policy=='compatible' else 'Revised-Normalization');folder.mkdir(exist_ok=True)
        snapshot=copy.deepcopy(settings);snapshot['ui_mode']='expert'
        snapshot['controls']['combo_normalization_mode']=dict(kind='combo',value=0 if policy=='compatible' else 1,text='Filter normalization: Compatible' if policy=='compatible' else 'Filter normalization: Revised (experimental)')
        for name in (*ORDER,'achf'):snapshot['sections']['sec_'+name]['active']=name in ('fnrgf','tangential','achf')
        for key,entry in snapshot['sections'].items():
            if key.startswith('sec_achf'):entry['active']=True
        for key,entry in snapshot['controls'].items():
            if key.startswith('achf_ael_controls.') and key.endswith('.enabled') or key=='chk_achf_adaptive':entry['value']=True
        for name in ('fnrgf','tangential','achf'):snapshot['controls']['sl_'+name+'_opacity']['value']=10
        snapshot['controls']['sl_general_warmth']['value']=35;snapshot['controls']['sl_warmth']['value']=40;snapshot['controls']['chk_reduce_green_sky']['value']=True
        snapshot['controls']['chk_prominences']['value']=True
        w=EclipseProcessorApp();w.auto_calculate=False;w.full_raw_image=full;w.raw_image=w.preview_image=loaded['preview'];w._display_reference_source=full;w._display_bounds=loaded['display_bounds']
        restore_settings(w,snapshot);p=w.collect_filter_parameters(full.shape,include_mask=False);snapshot=capture_settings(w)
        assert p['normalization_mode']==policy
        w.close();app.processEvents()
        worker=FilterWorker();engine=engine_for(worker);captured={}
        def capture(package,*args,**kwargs):
            captured['merged']=hashlib.sha256(np.ascontiguousarray(package.combined,dtype='<u2').tobytes()).hexdigest()
            captured['prominences']=[row.sha256() for row in package.layers if row.record.get('filter')=='prominences']
            captured['normalizations']=[dict(filter=row.record['filter'],variant=row.record.get('variant'),mapping=row.record.get('normalization')) for row in package.layers if row.record.get('filter') in ('fnrgf','tangential','achf')]
            return export_psb_layers(package,*args,**kwargs)
        destination=folder/'All-Affected-Filters-Native-Colour.tif'
        with filter_budget(8),patch('core.psb_export.export_psb_layers',side_effect=capture):
            export_images(full,p,{},str(destination),meta['source'],source_rgb=rgb,calibrate_colour=True,white=loaded['white'],export_layers=True,layers_format='psb',layer_cache=engine,project_settings=snapshot,input_state='linear',original_rgb=rgb,export_prominences=True,prominence_exposure_ev=-2.,prominence_saturation=.65,prominence_contrast=1.,prominence_edge_softness=3.,warmth=.4,general_warmth=.35,reduce_green_sky=True,green_reduction=.75)
        output=tifffile.imread(destination)
        assert output.shape==(*full.shape,3) and output.dtype==np.uint16
        assert hashlib.sha256(np.ascontiguousarray(output,dtype='<u2').tobytes()).hexdigest()==captured['merged']
        path=folder/'Reviewable-Settings.json';write_settings(path,meta['source'],snapshot,p,{})
        source,saved=read_settings(path);assert source==Path(meta['source']).resolve()
        verify=EclipseProcessorApp();verify.auto_calculate=False;verify.full_raw_image=full;verify.raw_image=verify.preview_image=loaded['preview'];restore_settings(verify,saved)
        assert verify.combo_normalization_mode.currentData()==policy;verify.close();app.processEvents()
        row=dict(policy=policy,TIFF_matches_verified_PSB=True,TIFF_shape=output.shape,TIFF_dtype=str(output.dtype),prominence_layer_hashes=captured['prominences'],normalizations=captured['normalizations'],recipe_roundtrip=True,JPEG_exists=destination.with_name(destination.stem+'_preview.jpg').is_file())
        assert row['JPEG_exists'];records.append(row);write(root/'native-export-and-recipe-checks.json',records)
        with Image.open(destination.with_name(destination.stem+'_preview.jpg')) as im:
            im=im.convert('RGB');im.thumbnail((1000,650));panel=Image.new('RGB',(1000,700),'#202020');panel.paste(im,(0,35));ImageDraw.Draw(panel).text((10,10),policy+'; diagnostic combination, identical warmth and source prominences',fill='white');panels.append(panel)
        print('EXPORT VERIFIED',policy,flush=True)
    assert records[0]['prominence_layer_hashes']==records[1]['prominence_layer_hashes'] and records[0]['prominence_layer_hashes']
    assert hashlib.sha256(full.tobytes()).hexdigest()==source_hash and hashlib.sha256(rgb.tobytes()).hexdigest()==rgb_hash
    assert digest(meta['source'])==EXPECTED
    sheet=Image.new('RGB',(2000,700),'#202020');sheet.paste(panels[0],(0,0));sheet.paste(panels[1],(1000,0));sheet.save(root/'Compatible-versus-Revised-Native-Colour-Comparison.jpg')
    write(root/'completion.json',dict(completed=True,source_and_original_RGB_unchanged=True,original_prominence_layer_identical=True,TIFF_PSB_pixel_equality_both_paths=True,scope='All affected filters enabled for integration diagnostics; not a recommended starter recipe',native_Photoshop_checked=False))

if __name__=='__main__':main()
