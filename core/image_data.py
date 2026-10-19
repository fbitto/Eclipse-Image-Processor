"""Observed-data masks, separate from numerical/display storage."""
import cv2
import numpy as np


def observed_image(image, valid=None):
    a = np.asarray(image, dtype=np.float64)
    if a.ndim != 2 or not a.size:
        raise ValueError('Image must be a nonempty 2D array')
    mask = np.isfinite(a) if valid is None else np.asarray(valid, dtype=bool)
    if mask.shape != a.shape or not mask.any() or not np.isfinite(a[mask]).all():
        raise ValueError('Image needs finite observed pixels and a matching validity mask')
    return np.where(mask, a, np.nan), mask


def normalize_observed(image):
    a, valid = observed_image(image)
    values = a[valid]
    span = np.ptp(values)
    out = np.zeros(a.shape, dtype=np.float64)
    if span > 0:
        out[valid] = (values - values.min()) / span
    return out


def resize_observed(image, size):
    """Area-average observed samples only; conservatively keep full support.

    Partially missing preview pixels remain missing rather than mixing the lunar
    boundary with a zero fill. No reconstructed pixels are added to the source.
    """
    a, valid = observed_image(image)
    weights = cv2.resize(valid.astype(np.float32), size, interpolation=cv2.INTER_AREA)
    values = cv2.resize(np.where(valid, a, 0).astype(np.float32), size, interpolation=cv2.INTER_AREA)
    mask = weights >= 1 - 1e-6
    result = np.full(weights.shape, np.nan, dtype=np.float32)
    np.divide(values, weights, out=result, where=mask)
    return result


def recipe_parameters(params):
    """Masks are image data, stored separately, never embedded in JSON metadata."""
    return {k: v for k, v in params.items() if k not in ('valid_mask', 'statistics_mask')}
