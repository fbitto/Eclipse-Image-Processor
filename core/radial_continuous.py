"""Global continuous radial ranks, using measured positive samples only.

Quantile distributions are interpolated, not image pixels. Inspired by AEL's
continuous radial statistics (Pere Guerra Serra, MIT); the reference-precision
path adapts ael/radial.py through AEL 1.4.1 (17029c9), with attribution in
docs/third-party/AEL-MIT.txt. The numerical API keeps its float64 default.
Output units are ranks [0, 1]; undefined pixels are NaN.
"""
from .cancellation import check_cancelled
import numpy as np


def rhef_continuous_normalize(image, radii, bin_px=2., application_radius=0.,
                              valid=None, min_count=12, quantile_count=257, target_valid=None,
                              reference_precision=False, position_angles=None):
    """Ranks on observed positive samples; reference_precision selects AEL float32 arithmetic."""
    dtype = np.float32 if reference_precision else np.float64
    a = np.asarray(image, dtype=dtype)
    r = np.asarray(radii, dtype=dtype)
    if a.ndim != 2 or a.shape != r.shape or not a.size:
        raise ValueError("Image and radii must be matching nonempty 2D arrays")
    if target_valid is not None and np.shape(target_valid) != a.shape:
        raise ValueError("RHEF target validity must match image")
    if not np.isfinite([bin_px, application_radius]).all() or bin_px <= 0 or application_radius < 0:
        raise ValueError("Invalid radial bounds")
    if not isinstance(min_count, (int, np.integer)) or min_count < 2:
        raise ValueError("Minimum population must be an integer >= 2")
    if not isinstance(quantile_count, (int, np.integer)) or quantile_count < 3:
        raise ValueError("At least three quantiles are required")
    mask = np.isfinite(a) & (a > 0) & np.isfinite(r) & (r >= application_radius)
    if valid is not None:
        if np.shape(valid) != a.shape:
            raise ValueError("Valid mask must match image")
        mask &= np.asarray(valid, dtype=bool)
    if position_angles is not None and np.shape(position_angles) != a.shape:
        raise ValueError("RHEF position angles must match image")
    out = np.full(a.shape, np.nan, dtype=dtype)
    ids = np.flatnonzero(mask)
    if not ids.size:
        return out
    rr = r.ravel()[ids]
    first = np.floor(rr / bin_px).astype(np.int64).min() if reference_precision else int(np.floor(rr.min() / bin_px))
    bins = np.floor(rr / bin_px).astype(np.int64) - first
    counts = np.bincount(bins)
    table = np.full((len(counts), quantile_count), np.nan, dtype=dtype)
    order = np.argsort(bins, kind="stable")
    cuts = np.r_[0, np.cumsum(counts)]
    values = np.log(a.ravel()[ids])
    probabilities = np.linspace(0, 1, quantile_count)
    for k in np.flatnonzero(counts >= min_count):
        check_cancelled()
        table[k] = np.quantile(values[order[cuts[k]:cuts[k + 1]]], probabilities)
    if target_valid is not None:
        targets = np.asarray(target_valid, bool) & np.isfinite(a) & (a > 0) & np.isfinite(r) & (r >= application_radius)
        target_bins = np.floor(np.where(np.isfinite(r),r,0)/bin_px).astype(np.int64)-first
        targets &= (target_bins >= 0) & (target_bins < len(counts))
        ids = np.flatnonzero(targets)
        rr = r.ravel()[ids]
        bins = target_bins.ravel()[ids]
        values = np.log(a.ravel()[ids])
    # Interpolate immediate neighbours only. An empty/sparse ring stays undefined;
    # a neighbour never validates it and no interpolation bridges a gap.
    eligible = counts[bins] >= min_count
    for start in range(0, ids.size, 16384):
        check_cancelled()
        use = np.arange(start, min(start + 16384, ids.size))
        use = use[eligible[use]]
        if not use.size:
            continue
        position = np.clip(rr[use] / bin_px - .5 - first, 0, len(counts) - 1)
        left = np.floor(position).astype(int)
        right = np.minimum(left + 1, len(counts) - 1)
        weight = position - left
        wl = (1 - weight) * np.isfinite(table[left, 0])
        wr = weight * np.isfinite(table[right, 0])
        mass = wl + wr
        # At exact node positions the current cell is always populated.
        good = mass > 0
        use, left, right, wl, wr, mass = (v[good] for v in (use, left, right, wl, wr, mass))
        if reference_precision:
            # Preserve AEL's four angular terms even globally: float32 accumulation changes rounding.
            wa = (np.zeros(len(use), dtype=np.float32) if position_angles is None else
                  (np.asarray(position_angles,np.float32).ravel()[ids[use]] % 360)/360)
            weights = ((1-weight[good])*(1-wa), (1-weight[good])*wa,
                       weight[good]*(1-wa), weight[good]*wa)
            nodes = (left, left, right, right)
            mass = np.zeros(len(use),np.float32)
            weights = tuple(w*np.isfinite(table[node,0]) for node,w in zip(nodes,weights))
            for w in weights:
                mass += w
        def threshold(index):
            if reference_precision:
                value = np.zeros(len(use),np.float32)
                for node,w in zip(nodes,weights):
                    value += np.nan_to_num(table[node,index])*w
                return value/np.maximum(mass,1e-12)
            return (np.nan_to_num(table[left, index]) * wl +
                    np.nan_to_num(table[right, index]) * wr) / mass

        if reference_precision:
            def inverse(right):
                lo = np.zeros(len(use), dtype=int)
                hi = np.full(len(use), quantile_count-1, dtype=int)
                for _ in range((quantile_count-2).bit_length()):
                    check_cancelled()
                    mid = (lo+hi)//2
                    above = values[use] >= threshold(mid) if right else values[use] > threshold(mid)
                    lo = np.where(above, mid, lo)
                    hi = np.where(above, hi, mid)
                vl, vh = threshold(lo), threshold(hi)
                fraction = np.clip((values[use]-vl)/np.maximum(vh-vl, 1e-12), 0, 1)
                rank = (lo+fraction*(hi-lo))/(quantile_count-1)
                return np.where(vh == vl, (hi if right else lo)/(quantile_count-1), rank)
            ranks = (inverse(False)+inverse(True))/2
            flat = threshold(np.full(len(use),quantile_count-1))-threshold(np.zeros(len(use),dtype=int))
            out.ravel()[ids[use]] = np.where(flat == 0,.5,ranks)
            continue

        def insertion(side):
            lo = np.zeros(len(use), dtype=int)
            hi = np.full(len(use), quantile_count, dtype=int)
            for _ in range(int(quantile_count).bit_length()):
                check_cancelled()
                mid = (lo + hi) // 2
                value = threshold(np.minimum(mid, quantile_count - 1))
                active = lo < hi
                advance = value <= values[use] if side == "right" else value < values[use]
                lo = np.where(active & advance, mid + 1, lo)
                hi = np.where(active & ~advance, mid, hi)
            return lo

        lower, upper = insertion("left"), insertion("right")
        k = np.clip(lower - 1, 0, quantile_count - 2)
        lo, hi = threshold(k), threshold(k + 1)
        fraction = np.divide(values[use] - lo, hi - lo,
                             out=np.zeros(len(use)), where=hi > lo)
        ranks = (k + np.clip(fraction, 0, 1)) / (quantile_count - 1)
        # Exact ties take the midpoint of their quantile interval. In particular
        # a constant distribution maps to .5, independently of its population.
        ties = upper > lower
        ranks[ties] = (lower[ties] + upper[ties] - 1) / (2 * (quantile_count - 1))
        out.ravel()[ids[use]] = ranks
    return out
