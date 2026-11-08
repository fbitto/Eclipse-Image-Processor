"""Synthetic-only frozen-statistics control for the shared ring display encoder."""
import argparse,inspect,json,sys
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import numpy as np,tifffile
from core import ael_achf
from inspect_filter_defaults import write


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();root=args.output
    source=inspect.getsource(ael_achf.display_detail_rings)
    assert source.count("return out,dict(display='level and spread per ring'")==1
    source=source.replace('def display_detail_rings(', 'def capture_ring_maps(').replace("return out,dict(display='level and spread per ring'", "return out,level,spread,dict(display='level and spread per ring'")
    ns=dict(ael_achf.__dict__);exec(compile(source,'research-ring-map-capture','exec'),ns)
    y,x=np.indices((256,256));r=np.hypot(x-128,y-128);r32=r.astype(np.float32)
    truth=.012*np.cos(12*np.arctan2(y-128,x-128))*np.exp(-((r-65)/12)**2);rows=[]
    for name in ('15-Tangential-angular-detail','18-ACHF-adaptive-circular','20-ACHF-AEL-ISO-04','21-ACHF-AEL-angular'):
        folder=root/'02-Synthetic-Known-Truth-Controls'/name
        before=tifffile.imread(folder/'noisy_base/operator-float32.tif');after=tifffile.imread(folder/'injected_faint_detail/operator-float32.tif')
        alpha=tifffile.imread(folder/'noisy_base/observed-layer-alpha-uint16.tif')/65535;alpha_after=tifffile.imread(folder/'injected_faint_detail/observed-layer-alpha-uint16.tif')/65535
        b=tifffile.imread(folder/'noisy_base/encoded-layer-uint16.tif').astype(float)/65535;a=tifffile.imread(folder/'injected_faint_detail/encoded-layer-uint16.tif').astype(float)/65535
        info=json.load(open(folder/'noisy_base/measurements-and-exact-parameters.json'));mapping=info['mapping'];sparse=not name.startswith(('20-','21-'));valid=(alpha>0)&np.isfinite(before)
        floor=max(float(np.max(abs(before[valid])))*np.finfo(np.float32).eps,np.finfo(np.float32).tiny) if sparse else 1e-5
        result=ns['capture_ring_maps'](before,valid,SimpleNamespace(radius_map=lambda:r32),width_px=mapping['ring_width_px'],noise_floor=floor,sparse_spread=sparse)
        assert len(result)==4
        out,level,spread,_=result
        gain=mapping.get('gain',1.)
        encode=lambda z:np.round(np.clip(.5+gain*(.5*np.tanh((z-level)/(np.float32(2.5)*spread))),0,1)*65535)/65535
        fixed_before=encode(before);fixed_after=encode(after)
        region=(alpha>.99)&(alpha_after>.99)&np.isfinite(before)&np.isfinite(after)&(r>48)&(r<82)&(abs(truth)>.006)
        baseline_difference=float(np.max(abs(fixed_before[region]-b[region])))
        assert baseline_difference<5e-5,(name,baseline_difference)
        signed=(a-b)[region]*truth[region];frozen=(fixed_after-fixed_before)[region]*truth[region]
        row=dict(mode=name,baseline_replay_max_difference=baseline_difference,current_negative_fraction=float(np.mean(signed<0)),current_zero_fraction=float(np.mean(signed==0)),frozen_negative_fraction=float(np.mean(frozen<0)),frozen_zero_fraction=float(np.mean(frozen==0)),scope='synthetic causal control; baseline display maps frozen, not an implemented algorithm')
        rows.append(row);print(row,flush=True)
    destination=root/'07-Causal-Probes-Synthetic-Only/Ring-Encoding-Frozen-Statistics';destination.mkdir(exist_ok=True)
    write(destination/'encoding-causal-probe.json',rows)

if __name__=='__main__':main()
