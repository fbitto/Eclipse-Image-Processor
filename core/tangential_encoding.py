"""EIP source-relative Tangential display; source and signed operator detail are immutable."""
import numpy as np
from scipy.ndimage import gaussian_filter1d
from .cancellation import check_cancelled


def source_relative_detail(detail, source, samples, targets, cx, cy, radius, *, gain=1.):
    """Encode (H,W) linear detail using allowed source radiance and empirical noise.

    Scale=max(5% of a smoothed annular mean |source|, 3*noise_sigma), in
    working linear intensity units. Only the reference gain is smoothed;
    missing radiance is never filled. Far-field noise is an adjacent MAD,
    not propagated detector uncertainty. Output is float32 in [0,1]/NaN.
    """
    a=np.asarray(source,np.float32);d=np.asarray(detail)
    if a.ndim!=2 or not a.size or d.shape!=a.shape or np.shape(samples)!=a.shape or np.shape(targets)!=a.shape:
        raise ValueError('Source-relative detail needs matching nonempty 2D data and masks')
    if not np.isfinite([cx,cy,radius,gain]).all() or radius<=0 or not 0<=gain<=5:
        raise ValueError('Source-relative detail needs finite geometry, positive radius and gain in [0,5]')
    m=np.asarray(samples,bool)&np.isfinite(a)
    good=np.asarray(targets,bool)&np.isfinite(a)&np.isfinite(d)
    info=dict(display='source-relative signed algebraic contrast',operator_revision='EIP Tangential source-relative 2026-11-08',
        scale_units='working linear intensity',source_fraction=.05,noise_multiple=3.,gain=float(gain),
        formula='0.5 + 0.5*z/hypot(1,z); z=gain*detail/(2.5*scale)',
        source_reference='allowed observed source, not filtered-layer statistics',noise_region_radii=8.,
        preview='approximate; continuum and empirical noise estimated at target resolution')
    out=np.full(a.shape,np.nan,np.float32)
    if gain==0:
        out[good]=.5
        return out,dict(info,bypass='zero gain')
    if m.sum()<64:raise ValueError('Source-relative contrast needs at least 64 allowed source samples; use existing normalization')
    check_cancelled()
    y,x=np.ogrid[:a.shape[0],:a.shape[1]]
    radii=np.hypot(x-cx,y-cy)
    first=float(np.floor(np.min(radii[m])));last=float(np.floor(np.max(radii[m])))
    sigma=min(max(1.,.1*radius),max(1.,last-first+1))
    # Compact keys retain four smoothing sigmas of constant leading extension,
    # without allocating bins from zero for an off-frame reference center.
    origin=max(0.,first-np.ceil(4*sigma))
    keys=(np.floor(radii[m])-origin).astype(np.int32)
    counts=np.bincount(keys);sums=np.bincount(keys,weights=np.abs(a[m].astype(float)))
    populated=np.flatnonzero(counts>=12)
    if len(populated)<8:raise ValueError('Source-relative contrast needs eight populated annuli; use existing normalization')
    grid=np.arange(len(counts))
    profile=np.interp(grid,populated,sums[populated]/counts[populated])
    check_cancelled()
    log_profile=gaussian_filter1d(np.log(np.maximum(profile,np.finfo(float).tiny)),sigma)
    pairs=m[:,1:]&m[:,:-1]&(radii[:,1:]>8*radius)&(radii[:,:-1]>8*radius)
    fallback=int(pairs.sum())<64
    if fallback:pairs=m[:,1:]&m[:,:-1]
    if pairs.sum()<64:raise ValueError('Source-relative contrast needs 64 observed adjacent pairs for noise; use existing normalization')
    check_cancelled()
    differences=a[:,1:][pairs].astype(float)-a[:,:-1][pairs].astype(float)
    noise=float(1.4826*np.median(abs(differences-np.median(differences)))/np.sqrt(2))
    info.update(source_noise_sigma=noise,noise_fallback=fallback,
        noise_region='all allowed observed pairs' if fallback else 'beyond eight reference radii',
        noise_pairs=int(differences.size),noise_estimator='1.4826 MAD of adjacent differences / sqrt(2); empirical',
        profile_annuli=int(len(populated)),profile_sigma_target_px=float(sigma),profile_min_count=12)
    del differences,pairs
    for first_row in range(0,a.shape[0],128):
        check_cancelled();last_row=min(first_row+128,a.shape[0]);mask=good[first_row:last_row]
        model=np.exp(np.interp(radii[first_row:last_row]-origin,grid,log_profile)).astype(np.float32)
        scale=np.maximum(.05*model,max(3*noise,np.finfo(np.float32).tiny))
        numerator=gain*np.where(mask,d[first_row:last_row],0).astype(float)
        out[first_row:last_row]=np.where(mask,.5+.5*numerator/np.hypot(2.5*scale,numerator),np.nan)
    check_cancelled()
    return out,info
