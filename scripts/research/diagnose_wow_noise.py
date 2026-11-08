"""Reproduce opt-in WOW suppression controls on the approved master, without editing it."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ.setdefault(key,'1')
import argparse,hashlib,json,time,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import numpy as np
from PIL import Image,ImageDraw
from scipy.ndimage import gaussian_filter
from core import ael_wow
from core.ael_wow import ael_wow_layer
from core.pipeline import prepare_parameters
from core.parallelism import filter_budget
from core.statistics_support import statistics_support
from core.presentation import psb_presentation_settings,psb_base
from core.layer_engine import blend
from gui.background_tasks import load_source
from gui.app import EclipseProcessorApp


def synthetic():
    # Research-only ablation: identical operator with a soft-threshold gate instead.
    source=Path(ael_wow.__file__).read_text()
    original='gain = -np.expm1(-.5*ratio*ratio)'
    assert source.count(original)==1
    namespace=dict(__name__='core.wow_soft_threshold_trial',__package__='core')
    exec(compile(source.replace(original,'gain = np.maximum(1-1/np.maximum(np.abs(ratio),1e-30),0)'),str(ael_wow.__file__),'exec'),namespace)
    y,x=np.indices((256,256));r=np.hypot(x-128,y-128);m=r>30
    base=(1+.3*np.exp(-r/55)).astype(np.float32)
    signal=(.15*np.exp(-((x-120)/3)**2)*np.exp(-((y-75)/40)**2)).astype(np.float32)
    sky=m&(r>110)&(x>160);stream=m&(abs(x-120)<2)&(y>45)&(y<90)
    p=dict(sx=128,sy=128,sr=30,wow_scales=4)
    results={}
    for kind in ('white','correlated'):
        noise=np.random.default_rng(94).normal(0,.006,base.shape)
        if kind=='correlated':noise=gaussian_filter(noise,1)*3
        a=(base+signal+noise).astype(np.float32);a[~m]=np.nan
        original,_=ael_wow_layer(a,p,m)
        for name,operator in (('smooth',ael_wow_layer),('soft',namespace['ael_wow_layer'])):
            b,_=operator(a,dict(p,wow_noise_reduction=2),m)
            results[kind+'_'+name]=dict(sky_std_ratio=float(np.std(b[sky])/np.std(original[sky])),
                streamer_contrast_ratio=float(np.median(b[stream]-.5)/np.median(original[stream]-.5)))
    noise=np.random.default_rng(94).normal(0,.006,base.shape)
    profile=np.exp(-((x-120)/3)**2)*np.exp(-((y-75)/40)**2)
    faint={}
    for strength in (0,1,2,3):
        outputs=[]
        for amplitude in (0,.01):
            a=(base+noise+amplitude*profile).astype(np.float32);a[~m]=np.nan
            outputs.append(ael_wow_layer(a,dict(p,wow_noise_reduction=strength),m)[0])
        faint[str(strength)]=float(np.median((outputs[1]-outputs[0])[stream]))
    results['faint_injection_response_ratio']={key:value/faint['0'] for key,value in faint.items()}
    return results


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path);parser.add_argument('output',type=Path)
    parser.add_argument('--native',action='store_true',help='Also run the full native frame; substantial memory and time')
    args=parser.parse_args()
    with args.source.open('rb') as f:before=hashlib.file_digest(f,'sha256').hexdigest()
    if before!='33ff81c882a0e5e98771b8c00f627af5860b56464798e16dc38e75122b45a005':
        raise ValueError('Use only the approved e1c3c474 master')
    args.output.mkdir(parents=True,exist_ok=False)
    report=dict(source=str(args.source.resolve()),sha256=before,synthetic=synthetic(),resolutions={})
    loaded=load_source(str(args.source),None,EclipseProcessorApp.detect_lunar_limb)
    full=loaded['full'];params=dict(zip(('sx','sy','sr'),loaded['circle']))
    params.update(wow_scales=8,wow_native_scales=True,statistics_exclude_lunar=True)
    display=psb_presentation_settings(full,params=params)
    for label,a in [('preview',loaded['preview'])]+([('native',full)] if args.native else []):
        p=prepare_parameters(params,full.shape,loaded['preview'].shape,a.shape)
        observed=np.isfinite(a);samples=statistics_support(a,p,observed)
        y,x=np.ogrid[:a.shape[0],:a.shape[1]];r=np.hypot(x-p['sx'],y-p['sy'])
        sky=observed&(r>4*p['sr']);inner=observed&(r>p['sr'])&(r<2*p['sr'])
        base,_=psb_base(a,p,display);base=np.nan_to_num(base)
        rows={};panels=[]
        for strength in (0.,1.,2.,3.):
            start=time.monotonic()
            with filter_budget(8):q,info=ael_wow_layer(a,dict(p,wow_noise_reduction=strength),samples)
            if strength==0:support=np.isfinite(q)
            np.testing.assert_array_equal(np.isfinite(q),support)
            rows[str(strength)]=dict(seconds=time.monotonic()-start,
                sky_texture_std=float(np.std(q[sky&support])),
                inner_contrast_std=float(np.std(q[inner&support])),receipt=info)
            rgb=blend(base,np.where(support,q,.5),support.astype(np.float32),'Overlay',1.)
            im=Image.fromarray((np.nan_to_num(np.clip(rgb,0,1))*255).astype(np.uint8))
            im.save(args.output/f'{label}-{strength:g}.png')
            if label=='native':
                cx,cy=int(p['sx']),int(p['sy']);crop=im.crop((cx-600,cy-600,cx+601,cy+601))
                crop.save(args.output/f'native-limb-{strength:g}.png')
            im.thumbnail((900,600));panel=Image.new('RGB',(900,630),'#202020');panel.paste(im,(0,30));ImageDraw.Draw(panel).text((8,8),f'{label}: noise reduction {strength:g}; WOW opacity 100%',fill='white');panels.append(panel)
            print(label,strength,rows[str(strength)]['seconds'],rows[str(strength)]['sky_texture_std'],flush=True)
        sheet=Image.new('RGB',(1800,1260),'#202020')
        for index,panel in enumerate(panels):sheet.paste(panel,((index%2)*900,(index//2)*630))
        sheet.save(args.output/f'{label}-comparison.jpg')
        report['resolutions'][label]=dict(shape=a.shape,scales=p['wow_scales'],measurements=rows)
        (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    with args.source.open('rb') as f:after=hashlib.file_digest(f,'sha256').hexdigest()
    assert before==after
    report['source_unchanged']=True
    (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
