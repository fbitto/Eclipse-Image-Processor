"""NAFE copied/adapted from AEL 1.4.2, Copyright (c) 2026 Pere Guerra Serra.

MIT; see docs/third-party/AEL-MIT.txt. Druckmüller (2013), ApJS 207, 25,
equations 11–14. Input is linear float32 mono; sigma uses the same intensity
units. E is float32 in [0,1], undefined outside observed operator support.
Local additions: validation, stable units, cancellation and memory-bounded parallel levels.
"""
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from contextvars import copy_context

import numpy as np
from scipy import fft as sfft
from scipy.special import ndtr

from .ael_achf import normalized_gaussian, radial_log_residual
from types import SimpleNamespace
from .cancellation import check_cancelled
from .parallelism import filter_budget, filter_cpu_budget, memory_bounded_workers
from .progress import report


@contextmanager
def _level_results(level, positions, workers):
    """Ordered results with at most two submitted levels and inherited cancellation."""
    if workers == 1:
        yield map(level, positions)
        return

    def calculate(position):
        inherited = copy_context()
        # Keep the parent's callable CPU budget live as other layers finish.
        with filter_budget(lambda: max(1, inherited.run(filter_cpu_budget)//workers)):
            return level(position)

    positions = iter(positions)
    pending = deque()
    executor = ThreadPoolExecutor(max_workers=workers, thread_name_prefix='nafe-level')

    def submit():
        check_cancelled()
        position = next(positions, None)
        if position is not None:
            pending.append(executor.submit(copy_context().run, calculate, position))

    def results():
        while pending:
            check_cancelled()
            future = pending.popleft()
            value = future.result()
            del future
            yield value
            submit()

    try:
        for _ in range(workers):
            submit()
        yield results()
    finally:
        for future in pending:
            future.cancel()
        executor.shutdown(wait=True, cancel_futures=True)


def nafe_neighbourhood(n=129, *, scale=1.):
    """Odd support; twelve native sigmas 2**(m/2) scaled to target pixels; centre=1."""
    if isinstance(n, (bool, np.bool_)) or not isinstance(n, (int, np.integer)) or n < 1 or n % 2 != 1:
        raise ValueError('NAFE window must be a positive odd integer')
    if not np.isfinite(scale) or not np.sqrt(np.finfo(float).tiny) <= scale <= 1:
        raise ValueError('NAFE kernel scale must be resolvable, finite and in (0,1]')
    k = np.arange(n) - n // 2
    r2 = (k[:, None]**2 + k[None, :]**2).astype(np.float64)
    sig = 2.**(np.arange(1, 13)/2)*scale
    g = sum(np.exp(-.5*r2/s**2)/(2*np.pi*np.sqrt(s)) for s in sig)
    return g*(2*np.pi/np.sum(sig**-.5))


def nafe(image, valid, sigma, *, n=129, level_step=.005, target_valid=None, kernel_scale=1.):
    """AEL fuzzy CDF with a Gaussian intensity gate; no image tone curve or fill.

    Signed radiance is supported. Subtracting a common pedestal and rescaling
    image/sigma together avoids unit overflow without changing the fuzzy CDF.
    Cancellation is checked between levels and FFTs; partial results never return.
    valid selects kernel samples; optional target_valid selects finite observed
    queries, which do not enter the kernel population. Unsupported queries stay NaN.
    """
    if not np.isfinite(sigma) or sigma <= 0:
        raise ValueError('NAFE sigma must be finite and positive in input units')
    if not np.isfinite(level_step) or not 0 < level_step <= 1:
        raise ValueError('NAFE level step must be finite and in (0,1]')
    kernel = nafe_neighbourhood(n,scale=kernel_scale)
    a = np.asarray(image, np.float32)
    if a.ndim != 2 or not a.size:
        raise ValueError('NAFE requires a nonempty 2D image')
    if valid is not None and np.shape(valid) != a.shape:
        raise ValueError('NAFE validity must match image')
    if target_valid is not None and np.shape(target_valid) != a.shape:
        raise ValueError('NAFE target validity must match image')
    m = np.isfinite(a) if valid is None else np.asarray(valid, bool) & np.isfinite(a)
    targets = m if target_valid is None else np.asarray(target_valid,bool) & np.isfinite(a)
    info = dict(n=int(n), c_m=1, sigma=float(sigma), level_step=float(level_step),
                internal_sigmas_target_px=(2.**(np.arange(1,13)/2)*kernel_scale).tolist(),
                kernel_scale=float(kernel_scale),
                centre_normalization=1, levels=0, convolutions=0, level_workers=0)
    if not m.any() or not targets.any():
        return np.full(a.shape, np.nan, np.float32), dict(info, undefined=True)
    check_cancelled()
    v = a[m].astype(np.float64)
    lo, hi = float(v.min()), float(v.max())
    unit = max(hi-lo, float(sigma))
    gate = float(sigma)/unit
    if gate == 0:
        raise ValueError('NAFE sigma is too small relative to the input range')
    a0 = np.zeros(a.shape, np.float32)
    present = m | targets
    a0[present] = ((a[present].astype(np.float64)-lo)/unit).astype(np.float32)
    if not np.isfinite(a0[present]).all():
        raise ValueError('NAFE target range exceeds working-coordinate precision')
    v = a0[targets].astype(np.float64)
    h, w = a.shape
    half = n//2
    ph, pw = sfft.next_fast_len(h+n-1, real=True), sfft.next_fast_len(w+n-1, real=True)
    kf = sfft.rfft2(kernel.astype(np.float32), s=(ph,pw), workers=filter_cpu_budget())
    mf = m.astype(np.float32)

    def conv(x):
        check_cancelled()
        spectrum = sfft.rfft2(x, s=(ph,pw), workers=filter_cpu_budget())
        check_cancelled()
        y = sfft.irfft2(spectrum*kf, s=(ph,pw), workers=filter_cpu_budget())
        return y[half:half+h, half:half+w]

    norm = np.maximum(conv(mf), 1e-12)
    # Query-only targets need real neighborhood support, not FFT roundoff in an empty kernel.
    supported = m | (norm >= .01*kernel.sum())
    targets = targets & supported
    if not targets.any():
        return np.full(a.shape,np.nan,np.float32),dict(info,undefined=True)
    v = a0[targets].astype(np.float64)
    t = [-gate]
    high = max((hi-lo)/unit, float(v.max()))
    while t[-1] < high or len(t) < 2:
        check_cancelled()
        next_level = t[-1]+max(gate/2, level_step*t[-1])
        if next_level <= t[-1]:
            raise ValueError('NAFE sigma cannot resolve intensity levels')
        t.append(next_level)
    # Extend below the sample grid without shifting its existing interpolation nodes.
    lower = []
    node = t[0]
    low_target = float(v.min())
    while node > low_target:
        check_cancelled()
        previous_level = node-max(gate/2,level_step*max(0.,-node-gate))
        if previous_level >= node:
            raise ValueError('NAFE sigma cannot resolve target intensity levels')
        lower.append(previous_level)
        node = previous_level
    t = lower[::-1]+t
    t = np.asarray(t)
    idx = np.flatnonzero(targets.ravel())
    k = np.clip(np.searchsorted(t,v,side='right')-1, 0, len(t)-2)
    order = np.argsort(k,kind='stable')
    idx, v, k = idx[order], v[order], k[order]
    cuts = np.searchsorted(k,np.arange(len(t)))
    out = np.full(h*w,np.nan,np.float32)

    def level(tj):
        dtype = np.float64 if gate < np.finfo(np.float32).tiny else np.float32
        d = np.subtract(tj,a0,dtype=dtype)
        d /= gate
        ndtr(d,out=d)
        return (conv(mf*d.astype(np.float32,copy=False))/norm).ravel()

    plan = []
    previous = False
    for j in range(1,len(t)):
        check_cancelled()
        lo_j, hi_j = cuts[j-1], cuts[j]
        nxt = cuts[j+1] if j+1 < len(t) else hi_j
        if hi_j == lo_j and nxt == hi_j:
            previous = False
            continue
        if not previous:
            plan.append(t[j-1])
        plan.append(t[j])
        previous = True
    # shortcut: 64 bytes per padded pixel estimates per-level memory, revise if larger masters exceed the budget.
    workers = min(2, memory_bounded_workers(64*ph*pw))
    used = 0
    prev = None
    with _level_results(level, plan, workers) as results:
        for j in range(1,len(t)):
            check_cancelled()
            lo_j, hi_j = cuts[j-1], cuts[j]
            nxt = cuts[j+1] if j+1 < len(t) else hi_j
            if hi_j == lo_j and nxt == hi_j:
                prev = None
                continue
            report(j,len(t)-1,'NAFE intensity levels')
            if prev is None:
                prev = next(results); used += 1
            cur = next(results); used += 1
            if hi_j > lo_j:
                p = idx[lo_j:hi_j]
                f = (v[lo_j:hi_j]-t[j-1])/(t[j]-t[j-1])
                out[p] = prev[p]+f*(cur[p]-prev[p])
            prev = cur
    check_cancelled()
    out = np.clip(out.reshape(h,w),0,1)
    out[~targets] = np.nan
    return out, dict(info, levels=len(t), convolutions=used, level_workers=workers)


def nafe_noise_sigma(image, valid, cx, cy, radius, *, multiple=12., region_rsun=4., smooth_px=4.):
    """AEL residual-MAD estimate in a declared outer region; not photon uncertainty."""
    if not np.isfinite([cx,cy,radius,multiple,region_rsun,smooth_px]).all() or min(radius,multiple,region_rsun,smooth_px) <= 0:
        raise ValueError('NAFE noise geometry, multiplier, region and smoothing must be finite and positive')
    a = np.asarray(image,np.float32)
    if a.ndim != 2 or not a.size or np.shape(valid) != a.shape:
        raise ValueError('NAFE noise estimate needs a nonempty 2D image and matching validity')
    m = np.asarray(valid,bool) & np.isfinite(a)
    if not m.any():
        raise ValueError('NAFE noise estimate needs observed samples')
    y,x = np.ogrid[:a.shape[0],:a.shape[1]]
    rs = np.hypot(x-cx,y-cy)/radius
    reg = m & (rs>=region_rsun)
    where = f'r >= {region_rsun:g} R_sun'
    region_fallback = bool(reg.sum()<20000)
    if region_fallback:
        reg = m & (rs>=np.quantile(rs[m],.8))
        where = 'outermost fifth of observed radii'
    check_cancelled()
    # Shared linear scaling keeps the float32 Gaussian usable in arbitrary input units.
    unit = float(np.max(np.abs(a[m]))) or 1.
    normalized = np.where(m,a/unit,np.nan).astype(np.float32)
    sm = normalized_gaussian(normalized,m,smooth_px,min_support=.5)
    d = (normalized-sm)[reg & np.isfinite(sm)]
    sigma_a = 1.4826*float(np.median(np.abs(d-np.median(d))))*unit if d.size else 0.
    fallback = d.size<64 or not sigma_a>0
    sigma = max(1e-6*unit,np.finfo(np.float32).tiny) if fallback else multiple*sigma_a
    check_cancelled()
    return sigma,dict(sigma_A=sigma_a,noise_multiple=multiple,noise_region=where,
        noise_region_fallback=region_fallback,noise_pixels=int(d.size),noise_min_samples=64,
        noise_fallback='input-relative numerical floor' if fallback else None,
        noise_estimate=f'1.4826 MAD of residual from a {smooth_px:g} target-pixel normalized Gaussian')


def _radial_reference(image, samples, targets, sigma, cx, cy, radius):
    """Smooth diagnostic continuum on observed support; never replace source pixels."""
    check_cancelled()
    y,x = np.ogrid[:image.shape[0], :image.shape[1]]
    radii = np.hypot(x-cx,y-cy).astype(np.float32)
    low = float(np.min(image[samples]))
    unit = max(float(np.ptp(image[samples])),float(sigma))
    shifted = np.where(samples,(image.astype(float)-low+sigma)/unit,np.nan).astype(np.float32)
    residual,fit = radial_log_residual(shifted,samples,
        SimpleNamespace(sun_radius_px=radius,radius_map=lambda:radii))
    supported = samples & np.isfinite(residual)
    if not supported.any():
        raise ValueError('Limb-aware NAFE needs supported radial statistics; use AEL original')
    model = np.full(image.shape,np.nan,np.float32)
    model[supported] = (np.exp(np.log(shifted[supported]).astype(float)-residual[supported])*unit+low-sigma).astype(np.float32)
    query = targets & ~supported
    if query.any():
        check_cancelled()
        order = np.argsort(radii[supported])
        # Extend the model only to observed queries, not into missing image data.
        model[query] = np.interp(radii[query],radii[supported][order],model[supported][order]).astype(np.float32)
    check_cancelled()
    return model,fit


def nafe_layer(image, params, valid=None, targets=None):
    """Independent Overlay E; preview window and internal sigmas share native scale."""
    a = np.asarray(image,np.float32)
    if a.ndim != 2 or not a.size or (valid is not None and np.shape(valid) != a.shape):
        raise ValueError('NAFE requires a nonempty 2D image and matching validity')
    m = np.isfinite(a) if valid is None else np.asarray(valid,bool) & np.isfinite(a)
    method = params.get('nafe_method','ael')
    if method not in ('ael','limb_aware'):
        raise ValueError('Unknown NAFE method')
    if method == 'limb_aware':
        geometry = [params.get(key,np.nan) for key in ('sx','sy','sr')]
        if not np.isfinite(geometry).all() or geometry[2] <= 0:
            raise ValueError('Limb-aware NAFE needs finite geometry and a positive radius')
    scale = float(params.get('nafe_scale',1.))
    if not np.isfinite(scale) or not 0 < scale <= 1:
        raise ValueError('NAFE resolution scale must be in (0,1]')
    window = params.get('nafe_window',129)
    if isinstance(window,(bool,np.bool_)) or not isinstance(window,(int,np.integer)) or window<1 or window%2!=1:
        raise ValueError('NAFE native window must be a positive odd integer')
    n = 2*int(round((window//2)*scale))+1
    info = dict(input='linear luminance',sigma_units='working linear input units',upstream_version='1.4.2',
        operator='Druckmüller (2013), ApJS 207, 25, equations 11–14; AEL NAFE E',
        display='E itself; Overlay, no display stretch',native_window=int(window),target_scale=scale,
        resolution='native' if scale==1 else 'approximate preview; window and internal Gaussians scaled from native pixels',
        support='observed statistical/operator samples; separate observed output targets')
    if not m.any():
        return np.full(a.shape,np.nan,np.float32),dict(info,undefined=True)
    sigma = params.get('nafe_sigma')
    if sigma is None:
        sigma,noise = nafe_noise_sigma(a,m,params['sx'],params['sy'],params['sr'],
            multiple=params.get('nafe_noise_multiple',12.),region_rsun=params.get('nafe_noise_region',4.),
            smooth_px=params.get('nafe_noise_smooth',4.)*scale)
        info.update(sigma_from='automatic residual MAD',**noise)
    else:
        info['sigma_from'] = 'manual'
    q,operator = nafe(a,m,sigma,n=n,target_valid=targets,kernel_scale=scale)
    info.update(operator,method=method)
    if method == 'limb_aware' and np.isfinite(q).any():
        observed = np.isfinite(a) if targets is None else np.asarray(targets,bool) & np.isfinite(a)
        model,fit = _radial_reference(a,m,observed,sigma,params['sx'],params['sy'],params['sr'])
        expected,reference_operator = nafe(model,m,sigma,n=n,target_valid=observed,kernel_scale=scale)
        if np.any(np.isfinite(q) & ~np.isfinite(expected)):
            raise ValueError('Limb-aware reference has insufficient support; use AEL original')
        # Unit slope at neutral retains faint contrast without hard clipping strong differences.
        q = .5+.5*np.tanh(2*(q-expected))
        info.update(operator_revision='eip-nafe-radial-reference-1',radial_reference=fit,
            reference_operator=reference_operator,experimental=True,
            display='0.5 + 0.5 tanh(2(E - E_reference)); Overlay',
            operator='EIP radial-reference response using AEL NAFE and radial spline')
    return q,info
