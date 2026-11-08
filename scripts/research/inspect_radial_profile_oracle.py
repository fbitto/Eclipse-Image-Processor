"""Synthetic-only causal oracle for ACHF radial-profile bands; never processes real data."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ.setdefault(key,'1')
import argparse,copy,json,sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import numpy as np,tifffile
from inspect_filter_defaults import modes,parameters,calculate,save_case,write


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();root=args.output
    raw=json.load(open(root/'00-Test-Manifest-and-Current-Defaults/current-unprepared-numerical-defaults.json'));raw.update(sx=128.,sy=128.,sr=30.,fnrgf_rmax=50)
    y,x=np.indices((256,256));r=np.hypot(x-128,y-128);truth=(.05+np.maximum(r/30,1.)**-3).astype(np.float32)
    def oracle(a,valid,geometry,statistics=None):
        assert a.shape==(256,256) and geometry.sun_radius_px==30,'Oracle restricted to the declared synthetic scene'
        m=valid&np.isfinite(a)&(a>0);residual=np.full(a.shape,np.nan,np.float32)
        residual[m]=np.log(a[m])-np.log(truth[m])
        return residual,dict(method='known synthetic analytic radial law; diagnostic oracle, unavailable on real master')
    rows=[]
    for index,mode in enumerate(modes(),1):
        if mode[2] not in ('ael_iso_01','ael_iso_04'):continue
        for scene in ('radial_null','angular_structure_null','noisy_base','injected_faint_detail'):
            a=tifffile.imread(root/'02-Synthetic-Known-Truth-Controls'/('input-'+scene+'.tif'));p=parameters(raw,mode,a.shape,a.shape,a.shape)
            with patch('core.ael_achf.radial_log_residual',side_effect=oracle):layer,operator,seconds,notes=calculate(a,p,mode)
            folder=root/'07-Causal-Probes-Synthetic-Only'/mode[0]/scene
            info,_,_,_=save_case(folder,a,p,mode,layer,operator,np.nan_to_num(truth),seconds,notes,1.,arrays=True)
            before=json.load(open(root/'02-Synthetic-Known-Truth-Controls'/f'{index:02d}-{mode[0]}'/scene/'measurements-and-exact-parameters.json'))
            rows.append(dict(mode=mode[0],scene=scene,baseline_band_score=before['encoded']['worst_sector_band_RMS'],oracle_band_score=info['encoded']['worst_sector_band_RMS']))
            print('CAUSAL ORACLE',rows[-1],flush=True)
    write(root/'07-Causal-Probes-Synthetic-Only/radial-profile-oracle-results.json',rows)

if __name__=='__main__':main()
