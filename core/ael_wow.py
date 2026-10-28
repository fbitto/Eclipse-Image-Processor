"""AEL 1.3.5 guided edge-aware WOW. Copyright (c) 2026 Pere Guerra Serra.

Adapted from AEL filterbank.py (MIT; docs/third-party/AEL-MIT.txt).
Linear luminance, symmetric observed pairs; no reflected or invented samples.
"""
import numpy as np
from .ael_achf import display_detail
from .cancellation import check_cancelled

_B3K = np.array([1, 4, 6, 4, 1], np.float32) / 16
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


def _b3_normalized(a, m, step):
    """Normalised B3 convolution at ``step`` over the observed pixels: the local power used to whiten a scale (a variance
    needs no symmetric taps)."""
    def conv(z):
        tmp = np.zeros_like(z)
        for kk, kv in zip(range(-2, 3), _B3K): tmp += kv * _shifted(z, kk * step, 0)
        out = np.zeros_like(z)
        for kk, kv in zip(range(-2, 3), _B3K): out += kv * _shifted(tmp, kk * step, 1)
        return out
    return conv(np.where(m, a, 0).astype(np.float32)) / np.maximum(conv(m.astype(np.float32)), 1e-20)


def _weighted_gaussian(x, w, sigma):
    """Gaussian mean of ``x`` with weights ``w``, zero outside the frame."""
    import cv2
    num = cv2.GaussianBlur((x * w).astype(np.float32), (0, 0), sigma, borderType=cv2.BORDER_CONSTANT)
    den = cv2.GaussianBlur(w.astype(np.float32), (0, 0), sigma, borderType=cv2.BORDER_CONSTANT)
    return num / np.maximum(den, 1e-6)


def _paired_b3_step(c, m, step, bilateral=False, guide=None, rows=128):
    """One à-trous B3 step over symmetric observed pairs: a tap counts only if its mirror tap is observed too, so the
    local mean never leans to one side of an edge of the data. With ``bilateral``, each tap is also weighted by
    exp(-(v - c)² / 2σ²), σ² the local variance of the tap differences; with ``guide``, those range weights come from the
    guide and the mean from ``c``. Returns (smoothed, observed share of the kernel, 1 where some pair is observed)."""
    h, w = c.shape; out = np.zeros_like(c); compl = np.zeros_like(c); pair = np.zeros_like(c)
    for y0 in range(0, h, rows):
        check_cancelled()
        y1 = min(h, y0 + rows); ctr = c[y0:y1]; mc = m[y0:y1]; ctg = ctr if guide is None else guide[y0:y1]
        V, VG, VAL = {}, {}, {}
        for dy, dx in _TAPS:
            V[dy, dx] = _rows_shifted(c, y0, y1, dy * step, dx * step, 0)
            VG[dy, dx] = V[dy, dx] if guide is None else _rows_shifted(guide, y0, y1, dy * step, dx * step, 0)
            VAL[dy, dx] = _rows_shifted(m, y0, y1, dy * step, dx * step, False)
        G = {}
        for t in _TAPS:
            u = (-t[0], -t[1])
            G[t] = mc.astype(np.float32) if t == (0, 0) else G[u] if u in G else (VAL[t] & VAL[u] & mc).astype(np.float32)
        if bilateral:
            mo = np.zeros_like(ctr); mo2 = np.zeros_like(ctr); ma = np.zeros_like(ctr)
            for dy, dx in _TAPS:
                k = float(_B3K[dy + 2] * _B3K[dx + 2]); g = G[dy, dx]; dl = np.where(g > 0, VG[dy, dx] - ctg, 0)
                mo += k * g * dl; mo2 += k * g * dl * dl; ma += k * g
            mean = mo / np.maximum(ma, 1e-20); vv = np.maximum(mo2 / np.maximum(ma, 1e-20) - mean * mean, 1e-20).astype(np.float64)
        num = np.zeros_like(ctr); den = np.zeros_like(ctr); ks = np.zeros_like(ctr); kn = np.zeros_like(ctr)
        for dy, dx in _TAPS:
            k = float(_B3K[dy + 2] * _B3K[dx + 2]); g = G[dy, dx]; v = np.where(g > 0, V[dy, dx], 0)
            if (dy, dx) != (0, 0): kn += k * g
            if bilateral:                                       # in double precision, as the author's chain computed it
                vg = v if guide is None else np.where(g > 0, VG[dy, dx], 0)
                wt = k * g.astype(np.float64) * np.exp(-.5 * (ctg.astype(np.float64) - vg) ** 2 / vv)
            else:
                wt = k * g
            num += wt * (v - ctr); den += wt; ks += k * g
        out[y0:y1] = ctr + num / np.maximum(den, 1e-20); compl[y0:y1] = ks; pair[y0:y1] = kn > 0
    return out, compl, pair


def wow_edge_aware(img, valid, *, n_scales=8, guided=True, completeness=(.6, .995)):
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
    a = np.asarray(img, np.float32); m = valid & np.isfinite(a)
    c = np.where(m, a, 0).astype(np.float32); out = np.zeros_like(c); lo, hi = completeness
    for s in range(n_scales):
        check_cancelled()
        step = 2 ** s
        guide = np.where(m, _paired_b3_step(c, m, step)[0], 0).astype(np.float32) if guided else None
        nxt, compl, pair = _paired_b3_step(c, m, step, True, guide); nxt = np.where(m, nxt, 0).astype(np.float32)
        wave = np.where(m, c - nxt, 0).astype(np.float32)
        wave[np.abs(wave) <= 8 * np.finfo(np.float32).eps * np.maximum(np.abs(c), np.abs(nxt))] = 0
        g = np.where(m & (compl > 0), wave / np.sqrt(np.maximum(_b3_normalized(wave * wave, m, step), 1e-20)), 0).astype(np.float32)
        if s >= 3:
            q = np.clip((compl - lo) / (hi - lo), 0, 1); w = (q * q * (3 - 2 * q) * m).astype(np.float32)
        else:
            w = (m & (compl > 0)).astype(np.float32)
        whole = m & (compl >= .999)
        g = g - (float(np.mean(g[whole], dtype=np.float64)) if whole.any() else 0.)
        g = g - pair * _weighted_gaussian(g, w * pair, min(150., max(32., 4. * step)))
        out += w * g; c = nxt
    return np.where(m, out, np.nan).astype(np.float32)


wow_bilateral = wow_edge_aware                           # the name up to 1.3.4



def ael_wow_layer(image, params, valid=None):
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
    y,x=np.ogrid[:a.shape[0],:a.shape[1]]
    r=np.hypot(x-cx,y-cy).astype(np.float32)
    check_cancelled()
    detail=wow_edge_aware(a,mask,n_scales=count)
    region=mask & (r>=1.1*radius) & (r<2*radius)
    encoded,mapping=display_detail(detail,mask,scale_region=region)
    mapping['scale_region']='1.1–2 reference-disk radii' if region.sum()>=1000 else 'all observed pixels'
    return encoded,dict(mapping,operator='AEL edge-aware WOW',input='linear luminance',
                        n_scales=count,range_weights='guided (issue #4)',completeness=[.6,.995],
                        level_sigma_px='min(150, max(32, 4*2^j))',upstream_version='1.3.5')
