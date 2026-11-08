"""AEL 1.4.1 guided edge-aware WOW. Copyright (c) 2026 Pere Guerra Serra.

Adapted from AEL filterbank.py, verified through 1.4.1 (17029c9) (MIT; docs/third-party/AEL-MIT.txt).
Linear luminance, symmetric observed pairs; no reflected or invented samples.

Threads: the 128-row blocks of every paired step and of the local-power
convolution run on core.parallelism.map_in_threads, within the layer's CPU
budget. Each block writes its own rows and each pixel goes through the same
operations in the same order, so the result is bit-identical for any number of
threads. The level Gaussians (cv2.GaussianBlur, one call on the whole frame)
stay on one thread: OpenCV spreads one call over the cores itself.
"""
import numpy as np
from .ael_achf import display_detail
from .cancellation import check_cancelled
from .parallelism import map_in_threads, memory_bounded_workers
from .progress import report

_B3K = np.array([1, 4, 6, 4, 1], np.float32) / 16
# Scratch memory of one block of a paired step, per pixel of the block (measured: about 330 bytes).
PAIRED_BYTES_PER_PIXEL = 330
_TAPS = [(dy, dx) for dy in range(-2, 3) for dx in range(-2, 3)]


def _rows_shifted(z, y0, y1, dy, dx, fill):
    """Rows y0:y1 of ``z`` read at (y + dy, x + dx); ``fill`` where that falls outside the frame (no reflected border)."""
    h, w = z.shape; out = np.full((y1 - y0, w), fill, z.dtype)
    a, b = max(y0 + dy, 0), min(y1 + dy, h); c, d = max(dx, 0), min(w + dx, w)
    if a < b and c < d: out[a - y0 - dy:b - y0 - dy, c - dx:d - dx] = z[a:b, c:d]
    return out


def _shifted(z, d, axis):
    """``z`` read at index + d along ``axis``; zero outside the frame."""
    out = np.zeros_like(z); n = z.shape[axis]
    if abs(d) >= n: return out
    src = [slice(None)] * 2; dst = [slice(None)] * 2
    src[axis] = slice(max(d, 0), n + min(d, 0)); dst[axis] = slice(max(-d, 0), n - max(d, 0))
    out[tuple(dst)] = z[tuple(src)]
    return out


def _run_blocks(job, h, rows, workers=None):
    """``job(y0, y1)`` on fixed blocks of ``rows`` rows, on up to ``workers`` threads (default: this filter's CPU
    budget). Blocks write disjoint rows, so neither the order nor the number of threads changes a bit. A cancelled job
    stops at the next block."""
    def run(block):
        check_cancelled()
        job(*block)
    map_in_threads(run, [(y0, min(h, y0 + rows)) for y0 in range(0, h, rows)], workers)


def _b3_normalized(a, m, step, rows=128, workers=None):
    """Normalised B3 convolution at ``step`` over the observed pixels: the local power used to whiten a scale (a variance
    needs no symmetric taps). By row blocks; each pixel is summed in AEL's order (rows first, then columns)."""
    z = np.where(m, a, 0).astype(np.float32); mf = m.astype(np.float32)
    out = np.empty_like(z)
    def job(y0, y1):
        def conv(src):
            tmp = np.zeros((y1 - y0, src.shape[1]), np.float32)
            for kk, kv in zip(range(-2, 3), _B3K): tmp += kv * _rows_shifted(src, y0, y1, kk * step, 0, 0)
            res = np.zeros_like(tmp)
            for kk, kv in zip(range(-2, 3), _B3K): res += kv * _shifted(tmp, kk * step, 1)
            return res
        out[y0:y1] = conv(z) / np.maximum(conv(mf), 1e-20)
    _run_blocks(job, z.shape[0], rows, workers)
    return out


def _weighted_gaussian(x, w, sigma):
    """Gaussian mean of ``x`` with weights ``w``, zero outside the frame."""
    import cv2
    num = cv2.GaussianBlur((x * w).astype(np.float32), (0, 0), sigma, borderType=cv2.BORDER_CONSTANT)
    den = cv2.GaussianBlur(w.astype(np.float32), (0, 0), sigma, borderType=cv2.BORDER_CONSTANT)
    return num / np.maximum(den, 1e-6)


def _paired_b3_step(c, m, step, bilateral=False, guide=None, rows=128, workers=None):
    """One à-trous B3 step over symmetric observed pairs: a tap counts only if its mirror tap is observed too, so the
    local mean never leans to one side of an edge of the data. With ``bilateral``, each tap is also weighted by
    exp(-(v - c)² / 2σ²), σ² the local variance of the tap differences; with ``guide``, those range weights come from the
    guide and the mean from ``c``. Returns (smoothed, observed share of the kernel, 1 where some pair is observed).
    The blocks of ``rows`` rows run on threads (_run_blocks); each block is AEL's loop body, unchanged."""
    out = np.zeros_like(c); compl = np.zeros_like(c); pair = np.zeros_like(c)
    # Shifted reads are views of one zero-padded copy per array instead of a new copy per
    # tap and block (same values: outside the frame a tap reads zero / unobserved).
    h, w = c.shape; P = 2 * step
    def padded(z, fill):
        out_ = np.full((h + 2 * P, w + 2 * P), fill, z.dtype); out_[P:P + h, P:P + w] = z
        return out_
    cp = padded(c, 0); mp = padded(m, False); gp = cp if guide is None else padded(guide, 0)
    def shifted(zp, y0, y1, dy, dx):
        return zp[P + y0 + dy * step:P + y1 + dy * step, P + dx * step:P + dx * step + w]
    def block(y0, y1):
        ctr = c[y0:y1]; mc = m[y0:y1]; ctg = ctr if guide is None else guide[y0:y1]
        V, VG, VAL = {}, {}, {}
        for dy, dx in _TAPS:
            V[dy, dx] = shifted(cp, y0, y1, dy, dx)
            VG[dy, dx] = V[dy, dx] if guide is None else shifted(gp, y0, y1, dy, dx)
            VAL[dy, dx] = shifted(mp, y0, y1, dy, dx)
        G = {}
        for t in _TAPS:
            u = (-t[0], -t[1])
            G[t] = mc.astype(np.float32) if t == (0, 0) else G[u] if u in G else (VAL[t] & VAL[u] & mc).astype(np.float32)
        # k * g, its mask and ctg in double precision are the same for every use below.
        KG, POS = {}, {}
        for dy, dx in _TAPS:
            KG[dy, dx] = float(_B3K[dy + 2] * _B3K[dx + 2]) * G[dy, dx]; POS[dy, dx] = G[dy, dx] > 0
        if bilateral:
            mo = np.zeros_like(ctr); mo2 = np.zeros_like(ctr); ma = np.zeros_like(ctr)
            for dy, dx in _TAPS:
                kg = KG[dy, dx]; dl = np.where(POS[dy, dx], VG[dy, dx] - ctg, 0)
                kgdl = kg * dl
                mo += kgdl; mo2 += kgdl * dl; ma += kg
            mean = mo / np.maximum(ma, 1e-20); vv = np.maximum(mo2 / np.maximum(ma, 1e-20) - mean * mean, 1e-20).astype(np.float64)
            ctg64 = ctg.astype(np.float64)
        num = np.zeros_like(ctr); den = np.zeros_like(ctr); ks = np.zeros_like(ctr); kn = np.zeros_like(ctr)
        for dy, dx in _TAPS:
            k = float(_B3K[dy + 2] * _B3K[dx + 2]); g = G[dy, dx]; kg = KG[dy, dx]; v = np.where(POS[dy, dx], V[dy, dx], 0)
            if (dy, dx) != (0, 0): kn += kg
            if bilateral:                                       # in double precision, as the author's chain computed it
                vg = v if guide is None else np.where(POS[dy, dx], VG[dy, dx], 0)
                # k * g * exp(-.5 * (ctg - vg)**2 / vv), each operation in place, in the same order.
                x = np.subtract(ctg64, vg); np.square(x, out=x); np.multiply(x, -.5, out=x)
                np.divide(x, vv, out=x); np.exp(x, out=x)
                wt = g.astype(np.float64); np.multiply(wt, k, out=wt); np.multiply(wt, x, out=wt)
                np.multiply(wt, v - ctr, out=x); num += x; den += wt
            else:
                num += kg * (v - ctr); den += kg
            ks += kg
        out[y0:y1] = ctr + num / np.maximum(den, 1e-20); compl[y0:y1] = ks; pair[y0:y1] = kn > 0
    if workers is None:
        workers = memory_bounded_workers(PAIRED_BYTES_PER_PIXEL * rows * w)
    _run_blocks(block, c.shape[0], rows, workers)
    return out, compl, pair


def wow_edge_aware(img, valid, *, n_scales=8, guided=True, completeness=(.6, .995),
                   noise_reduction=0., noise_valid=None, return_reference=False):
    """Edge-aware WOW, the default WOW layer since 1.3.5 (called WOW bilateral up to 1.3.4): the operator of the edge-aware
    WOW layer of the author's 2026 image, with the cure of issue #4. Edge-aware is the name Auchère et al. (2023) give to the
    variant of WOW whose smoothing uses range weights, a bilateral filter, to avoid halos at spikes and edges.

    Each B3 à-trous scale is smoothed over symmetric observed pairs with range weights (bilateral: taps across a strong
    edge count less), whitened by its local power, centred on its mean where its kernel is whole, and its local level is
    removed with a weighted Gaussian of min(150, max(32, 4·2^j)) px. From scale 3 up a scale enters with the observed
    share of its kernel, smoothstep from ``completeness[0]`` to ``completeness[1]``. Outside-frame taps are absent; no
    reflected border and no copied missing pixels.

    Issue #4 (Edu): range weights computed from the data being decomposed can turn faint fine detail next to stronger
    structure into its opposite. With ``guided`` (the default), the range weights of each scale come from a guide that
    does not contain the detail of that scale (the same step without range weights) and the mean still comes from the
    data. Measured: docs/VALIDATION_1.3.4.md and docs/VALIDATION_1.3.5.md. ``guided=False`` is the author's operator as it
    ran in 2026."""
    # EIP extension: optional smooth significance gate; zero retains upstream arithmetic.
    # return_reference supplies the original detail and per-band estimates for display/export receipts.
    import cv2
    if not np.isfinite(noise_reduction) or not 0 <= noise_reduction <= 5:
        raise ValueError('WOW noise reduction must be in [0,5]')
    a = np.asarray(img, np.float32); m = valid & np.isfinite(a)
    if noise_valid is not None and np.shape(noise_valid) != a.shape:
        raise ValueError('WOW noise statistics must match image')
    noise_samples = m if noise_valid is None else m & np.asarray(noise_valid,bool)
    estimates = []
    reference = np.zeros_like(a) if noise_reduction else None
    c = np.where(m, a, 0).astype(np.float32); out = np.zeros_like(c); lo, hi = completeness
    h = c.shape[0]
    total = 3 * n_scales
    # The per-pixel steps between the threaded B3 steps run in the same row blocks on threads
    # (each block computes exactly the expressions the whole-frame code computed); only the
    # mean over the whole kernels stays one serial reduction, so its value is unchanged.
    for s in range(n_scales):
        check_cancelled()
        step = 2 ** s
        report(3 * s, total, f'WOW scale {s + 1}/{n_scales}: guide')
        guide = None
        if guided:
            smooth = _paired_b3_step(c, m, step)[0]
            guide = np.empty_like(c)
            def observed_guide(y0, y1):
                guide[y0:y1] = np.where(m[y0:y1], smooth[y0:y1], 0)
            _run_blocks(observed_guide, h, 128)
            del smooth
        report(3 * s + 1, total, f'WOW scale {s + 1}/{n_scales}: range weights')
        smooth, compl, pair = _paired_b3_step(c, m, step, True, guide)
        del guide
        nxt = np.empty_like(c); wave = np.empty_like(c); square = np.empty_like(c)
        def wavelet(y0, y1):
            ms, cs = m[y0:y1], c[y0:y1]
            n = np.where(ms, smooth[y0:y1], 0).astype(np.float32)
            wv = np.where(ms, cs - n, 0).astype(np.float32)
            wv[np.abs(wv) <= 8 * np.finfo(np.float32).eps * np.maximum(np.abs(cs), np.abs(n))] = 0
            nxt[y0:y1] = n; wave[y0:y1] = wv; square[y0:y1] = wv * wv
        _run_blocks(wavelet, h, 128)
        del smooth
        report(3 * s + 2, total, f'WOW scale {s + 1}/{n_scales}: whitening')
        power = _b3_normalized(square, m, step)
        del square
        noise_sigma = 0.
        if noise_reduction:
            check_cancelled()
            population = noise_samples & (compl >= .999) & (pair > 0)
            fallback = int(population.sum()) < 64
            if fallback:
                population = m & (compl >= .999) & (pair > 0)
            values = wave[population]
            if values.size < 64:
                raise ValueError('WOW noise reduction needs at least 64 fully supported samples per scale; reduce scales or set noise reduction to zero')
            noise_sigma = float(1.4826*np.median(np.abs(values-np.median(values))))
            estimates.append(dict(scale=s+1,sigma=noise_sigma,samples=int(values.size),
                                  region='all fully supported observed samples' if fallback else 'outer observed statistics',
                                  fallback=fallback))
            del values,population
        g = np.empty_like(c); w = np.empty_like(c); wp = np.empty_like(c); whole = np.empty(c.shape, bool)
        def whiten(y0, y1):
            ms, cm = m[y0:y1], compl[y0:y1]
            g[y0:y1] = np.where(ms & (cm > 0), wave[y0:y1] / np.sqrt(np.maximum(power[y0:y1], 1e-20)), 0)
            if s >= 3:
                q = np.clip((cm - lo) / (hi - lo), 0, 1); w[y0:y1] = (q * q * (3 - 2 * q) * ms).astype(np.float32)
            else:
                w[y0:y1] = (ms & (cm > 0)).astype(np.float32)
            wp[y0:y1] = w[y0:y1] * pair[y0:y1]
            whole[y0:y1] = ms & (cm >= .999)
        _run_blocks(whiten, h, 128)
        del power
        if not noise_reduction:
            del wave
        mean = float(np.mean(g[whole], dtype=np.float64)) if whole.any() else 0.
        del whole
        weighted = np.empty_like(c)
        def centre(y0, y1):
            g[y0:y1] = g[y0:y1] - mean
            weighted[y0:y1] = (g[y0:y1] * wp[y0:y1]).astype(np.float32)
        _run_blocks(centre, h, 128)
        check_cancelled()
        sigma = min(150., max(32., 4. * step))
        num = cv2.GaussianBlur(weighted, (0, 0), sigma, borderType=cv2.BORDER_CONSTANT)
        del weighted
        check_cancelled()
        den = cv2.GaussianBlur(wp, (0, 0), sigma, borderType=cv2.BORDER_CONSTANT)
        del wp
        def accumulate(y0, y1):
            level = num[y0:y1] / np.maximum(den[y0:y1], 1e-6)
            residual = w[y0:y1] * (g[y0:y1] - pair[y0:y1] * level)
            if noise_reduction:
                reference[y0:y1] += residual
                if noise_sigma > 0:
                    ratio = wave[y0:y1].astype(np.float64)/(noise_reduction*noise_sigma)
                    gain = -np.expm1(-.5*ratio*ratio)
                    residual = residual*gain
            out[y0:y1] += residual
        _run_blocks(accumulate, h, 128)
        del num, den, g, w, pair, compl
        if noise_reduction:
            del wave
        c = nxt
    report(total, total, 'WOW done')
    result = np.empty_like(out)
    def finish(y0, y1):
        result[y0:y1] = np.where(m[y0:y1], out[y0:y1], np.nan)
    _run_blocks(finish, h, 128)
    if return_reference:
        baseline = result if reference is None else np.where(m,reference,np.nan).astype(np.float32)
        return result,baseline,estimates
    return result


wow_bilateral = wow_edge_aware                           # the name up to 1.3.4



def ael_wow_layer(image, params, valid=None, statistics=None):
    """Encoded Overlay layer. wow_scales is adapted to target resolution upstream."""
    a = np.asarray(image,dtype=np.float32)
    if a.ndim != 2 or not a.size:
        raise ValueError('AEL WOW requires a nonempty 2D image')
    cx,cy,radius = params['sx'],params['sy'],params['sr']
    if not np.isfinite([cx,cy,radius]).all() or radius <= 0:
        raise ValueError('AEL WOW requires finite geometry and positive radius')
    count=params.get('wow_scales',8) or 8
    if isinstance(count,bool) or not isinstance(count,(int,np.integer)) or not 1 <= count <= 10:
        raise ValueError('AEL WOW requires 1 to 10 scales')
    mask=np.isfinite(a) & (a>0)
    if valid is not None:
        if np.shape(valid) != a.shape:
            raise ValueError('AEL WOW validity must match image')
        mask &= np.asarray(valid,bool)
    if statistics is not None and np.shape(statistics)!=a.shape:
        raise ValueError("AEL WOW statistics mask must match image")
    y,x=np.ogrid[:a.shape[0],:a.shape[1]]
    r=np.hypot(x-cx,y-cy).astype(np.float32)
    check_cancelled()
    samples=mask if statistics is None else mask & np.asarray(statistics,bool)
    outer=samples & (r>=4*radius)
    reduction=params.get('wow_noise_reduction',0.)
    detail,reference,estimates=wow_edge_aware(a,mask,n_scales=count,noise_reduction=reduction,
        noise_valid=outer,return_reference=True)
    region=samples & (r>=1.1*radius) & (r<2*radius)
    encoded,mapping=display_detail(reference,mask,scale_region=region,statistics=statistics)
    if reduction:
        # Anchor contrast to the original layer so display scaling cannot undo suppression.
        encoded=np.where(mask,.5+.5*np.tanh(detail/(2.5*mapping['scale'])),np.nan).astype(np.float32)
        mapping.update(noise_reduction=float(reduction),noise_estimates=estimates,
            noise_method='EIP smooth coefficient significance; gain=1-exp(-0.5*(wave/(strength*sigma))^2)',
            noise_scale_anchor='unsuppressed WOW detail',noise_estimator='per-band 1.4826 MAD; empirical, not calibrated uncertainty')
    mapping['scale_region']='1.1–2 reference-disk radii' if region.sum()>=1000 else 'all observed pixels'
    return encoded,dict(mapping,operator='AEL edge-aware WOW',input='linear luminance',
                        support_mode='experimental statistics separation' if statistics is not None else 'compatibility',
                        n_scales=count,range_weights='guided (issue #4)',completeness=[.6,.995],
                        level_sigma_px='min(150, max(32, 4*2^j))',upstream_version='1.4.1', upstream_commit='17029c9284748c087adcd0d40241f7e3faf8d778')
