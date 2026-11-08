"""Independent support-aware Fourier radial normalization.

Fits sector statistics in input units. Adjacent populated radial models are
smoothed/interpolated; absent sectors never become zero-valued observations.
This optional variant differs from the reference-compatible FNRGF core.
"""
from .cancellation import check_cancelled
import numpy as np
from .nrgf import _local_quadratic
from .parallelism import map_in_threads


def stable_key_order(keys):
    """``np.argsort(keys, kind='stable')``; keys below 2**16 are sorted as uint16.

    A stable sort has one result for given key values, and NumPy sorts 16-bit
    integers with a radix sort, much faster than the merge sort of 64-bit keys.
    """
    keys = np.asarray(keys)
    if keys.size and keys.min() >= 0 and keys.max() < 1 << 16:
        return np.argsort(keys.astype(np.uint16), kind='stable')
    return np.argsort(keys, kind='stable')


def continuous_fnrgf(image, radii, angles, edges, order=6, segments=64,
                     cutoff=0, width_function='std', valid=None, smooth_px=8.,
                     ridge=.01, width_floor=.05, robust_iterations=2,
                     min_pixels=1, mean_tail=0., width_tail=0., target_valid=None, revised=False):
    a = np.asarray(image, dtype=float)
    r, theta, edges = np.asarray(radii), np.asarray(angles), np.asarray(edges)
    if a.ndim != 2 or r.shape != a.shape or theta.shape != a.shape:
        raise ValueError('FNRGF image and geometry must be matching 2D arrays')
    if edges.ndim != 1 or len(edges) < 2 or not np.isfinite(edges).all() or np.any(np.diff(edges) <= 0):
        raise ValueError('FNRGF radial edges must increase')
    if order < 1 or segments < 2*order+1 or not 0 <= cutoff <= order+1:
        raise ValueError('FNRGF needs segments >= 2*order+1 and a valid cutoff')
    if width_function not in ('std', 'mad') or min_pixels < 1:
        raise ValueError('Invalid FNRGF sector statistics')
    if not np.isfinite([smooth_px, ridge, width_floor, mean_tail, width_tail]).all() or smooth_px < 0 or ridge < 0 or not 0 <= width_floor <= 1:
        raise ValueError('Invalid FNRGF smoothing, regularization or width floor')
    if not 0 <= mean_tail <= 1 or not 0 <= width_tail <= 1 or not 0 <= robust_iterations <= 5:
        raise ValueError('Invalid FNRGF attenuation or iteration count')
    observed = np.isfinite(a) & np.isfinite(r) & np.isfinite(theta)
    target_mask = observed.copy()
    if target_valid is not None:
        if np.shape(target_valid) != a.shape:
            raise ValueError('FNRGF target validity must match image')
        target_mask &= np.asarray(target_valid, bool)
    if valid is not None:
        if np.shape(valid) != a.shape:
            raise ValueError('FNRGF statistics mask must match image')
        observed &= valid
    bins = np.searchsorted(edges, r, side='right')-1
    observed &= (bins >= 0) & (bins < len(edges)-1)
    target_mask = observed if target_valid is None else target_mask & (bins >= 0) & (bins < len(edges)-1)
    ids = np.flatnonzero(observed)
    output = np.full(a.shape, np.nan)
    if not ids.size:
        return output
    if np.ptp(a.ravel()[ids]) == 0:
        output[observed] = 0.
        return output
    # Scale internally to avoid unit-dependent ridge and width safety floors.
    magnitude = float(np.max(np.abs(a.ravel()[ids])))
    unit = a / (magnitude if magnitude else 1.)
    sector = np.floor((theta.ravel()[ids] % (2*np.pi))*segments/(2*np.pi)).astype(int) % segments
    keys = bins.ravel()[ids]*segments+sector
    sorting = stable_key_order(keys)
    ids = ids[sorting]
    counts = np.bincount(keys, minlength=(len(edges)-1)*segments)
    cuts = np.r_[0, np.cumsum(counts)]
    phi = (np.arange(segments)+.5)*2*np.pi/segments
    design = np.column_stack([np.ones(segments)] + [f(k*phi) for k in range(1, order+1) for f in (np.cos, np.sin)])
    # Preserve smooth sky trends; regularize only harmonics above k=2.
    harmonics = np.arange(1, order+1, dtype=float)
    penalty = np.r_[0., np.repeat(np.where(harmonics > 2, harmonics**2, 0.), 2)]
    models = np.full((2, len(edges)-1, design.shape[1]), np.nan)
    floors = np.full(len(edges)-1, np.nan)
    centers = (edges[:-1]+edges[1:])/2

    def fit(values, populations):
        good = populations > 0
        columns = 2*min(order, (np.count_nonzero(good)-1)//2)+1
        X, y = design[good, :columns], values[good]
        base = populations[good]/populations[good].sum()
        weights = base.copy()
        coverage = good.mean()
        regularizer = np.diag(np.sqrt(ridge/max(coverage, 1/segments)**4*penalty[:columns]))
        for iteration in range(int(robust_iterations)+1):
            check_cancelled()
            coef = np.linalg.lstsq(np.vstack([X*np.sqrt(weights[:, None]), regularizer]),
                                   np.r_[y*np.sqrt(weights), np.zeros(columns)], rcond=None)[0]
            residual = y-X@coef
            scatter = 1.4826*np.median(np.abs(residual-np.median(residual)))
            if iteration == robust_iterations or scatter <= np.finfo(float).eps*max(1., np.max(np.abs(y))):
                break
            weights = base/np.maximum(np.abs(residual)/(2*scatter), 1.)
        return np.pad(coef, (0, design.shape[1]-columns))

    for b in range(len(edges)-1):
        check_cancelled()
        means, widths, population = np.zeros(segments), np.zeros(segments), np.zeros(segments)
        for j in range(segments):
            check_cancelled()
            key = b*segments+j
            selected_ids=ids[cuts[key]:cuts[key+1]]
            values = unit.ravel()[selected_ids]
            if values.size < min_pixels:
                continue
            population[j] = values.size
            means[j] = values.mean()
            if revised and values.size>=6:
                # A cell average is not its center value on a steep or partially observed radial law.
                offset=(r.ravel()[selected_ids]-centers[b])/(edges[b+1]-edges[b])
                if np.ptp(offset)>.25:
                    coefficients,_,rank,_=np.linalg.lstsq(np.vander(offset,3,increasing=True),values,rcond=None)
                    if rank==3:means[j]=coefficients[0]
            widths[j] = values.std() if width_function == 'std' else 1.4826*np.median(np.abs(values-np.median(values)))
        if np.count_nonzero(population) < 3:
            continue
        # A single sample constrains a mean, but not a measured spread. Never
        # turn its undefined width into an almost-zero log-width observation.
        width_population = np.where(population >= 2, population, 0)
        if np.count_nonzero(width_population) < 3:
            continue
        positive = widths[(width_population > 0) & (widths > 0)]
        typical = float(np.median(positive)) if positive.size else 0.
        floors[b] = max(width_floor*typical, np.finfo(float).eps)
        models[0, b] = fit(means, population)
        # Model log-width, guaranteeing a positive interpolated divisor.
        models[1, b] = fit(np.log(np.maximum(widths, floors[b])), width_population)
    present = np.flatnonzero(np.isfinite(floors))
    for run in np.split(present, np.flatnonzero(np.diff(present) > 1)+1):
        check_cancelled()
        if not run.size:
            continue
        local = models[:, run].copy()
        if smooth_px and len(run) > 1:
            # Fit at physical nodes; replicated endpoints bend steep radial profiles.
            spacing = float(np.median(np.diff(centers[run])))
            for family in (0, 1):
                for k in range(local.shape[-1]):
                    check_cancelled()
                    local[family, :, k] = _local_quadratic(
                        local[family, :, k], smooth_px/spacing, centers[run]/spacing,degree=4 if revised else 2)
        spline=None
        if revised and len(run)>1:
            from scipy.interpolate import CubicSpline
            spline=CubicSpline(centers[run],local,axis=1)
        target = target_mask & (bins >= run[0]) & (bins <= run[-1])
        targets = np.flatnonzero(target)
        attenuation = np.array([np.linspace(1., mean_tail, order+1),
                                np.linspace(1., width_tail, order+1)])
        if cutoff:
            attenuation[:, -cutoff:] = 0
        # Chunks of targets are independent (each writes its own pixels): they run on
        # helper threads, with the same operations per pixel as one at a time.
        def evaluate(first):
            check_cancelled()
            selected = targets[first:first+32768]
            rr, tt = r.ravel()[selected], theta.ravel()[selected]
            # Share radial interpolation and angular bases across both families.
            nodes = centers[run]
            if len(run) == 1:
                coefficients = np.broadcast_to(local[:, :1, :], (2, rr.size, local.shape[-1]))
            elif spline is not None:
                coefficients=spline(rr)
            else:
                position = np.clip(rr, nodes[0], nodes[-1])
                left = np.clip(np.searchsorted(nodes, position, side='right')-1, 0, len(nodes)-2)
                slopes = (local[:, left+1, :]-local[:, left, :]) / (nodes[left+1]-nodes[left])[None, :, None]
                coefficients = local[:, left, :]+slopes*(position-nodes[left])[None, :, None]
            mean, log_width = np.zeros(rr.size), np.zeros(rr.size)
            for k in range(local.shape[-1]):
                check_cancelled()
                harmonic = (k+1)//2
                basis = 1. if k == 0 else (np.cos(harmonic*tt) if k % 2 else np.sin(harmonic*tt))
                mean += coefficients[0, :, k]*basis*attenuation[0, harmonic]
                # The log-width DC term sets units and is never attenuated.
                factor = 1. if k == 0 else attenuation[1, harmonic]
                log_width += coefficients[1, :, k]*basis*factor
            floor = np.interp(rr, nodes, floors[run])
            width = np.maximum(np.exp(np.clip(log_width, -700, 700)), floor)
            output.ravel()[selected] = (unit.ravel()[selected]-mean)/width
        map_in_threads(evaluate, range(0, targets.size, 32768))
    return output
