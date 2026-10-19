"""Generalised Hyperbolic Stretch on normalized intensities, in float64.

Independent implementation of Payne/Cranfield's published GHS equations:
https://www.ghsastro.co.uk/doc/tools/GeneralizedHyperbolicStretch/GeneralizedHyperbolicStretch.html
Sections 3.7–3.11 and 5.2. Inputs are in [0, 1]; NaN remains undefined.
The UI stretch factor is ln(D+1), not D. No per-image normalization occurs here.
"""
import numpy as np


def generalized_hyperbolic_stretch(image, stretch=0., sp=0., b=0., lp=0., hp=1.):
    """Evaluate the five-parameter GHS curve with tangent shadow/highlight tails.

    All base branches have been divided by their slope at zero. This shared
    scale cancels in the final endpoint normalization and improves conditioning.
    LP <= SP <= HP; stretch=0 is exactly identity, including LP=SP=HP.
    """
    stretch, sp, b, lp, hp = map(float, (stretch, sp, b, lp, hp))
    if not np.isfinite([stretch, sp, b, lp, hp]).all():
        raise ValueError('GHS parameters must be finite')
    if not 0 <= stretch <= 20 or not -5 <= b <= 15:
        raise ValueError('GHS requires stretch in [0,20] and b in [-5,15]')
    if not 0 <= lp <= sp <= hp <= 1:
        raise ValueError('GHS requires 0 <= LP <= SP <= HP <= 1')
    x = np.asarray(image, dtype=np.float64)
    if np.isinf(x).any() or np.any((x < 0) | (x > 1)):
        raise ValueError('GHS intensities must be in [0,1] or NaN')
    if stretch == 0:
        return x.copy()
    d = np.expm1(stretch)

    def base(t):
        t = np.asarray(t, dtype=np.float64)
        if b == -1:
            return np.log1p(d*t)/d
        if b < 0:
            # Integral branch, evaluated with expm1 near its logarithmic limit.
            log_term = np.log1p(-b*d*t)
            z = ((b+1)/b)*log_term
            exprel = np.divide(np.expm1(z), z, out=np.ones_like(z), where=z != 0)
            return log_term/(-b*d)*exprel
        if b == 0:
            return -np.expm1(-d*t)/d
        return -np.expm1(-np.log1p(b*d*t)/b)/d

    def slope(t):
        if b < 0:
            return np.exp(np.log1p(-b*d*t)/b)
        if b == 0:
            return np.exp(-d*t)
        return np.exp(-(1+b)/b*np.log1p(b*d*t))

    lower, upper = base(sp-lp), base(hp-sp)
    lower_slope, upper_slope = slope(sp-lp), slope(hp-sp)
    zero = -lower-lp*lower_slope
    one = upper+(1-hp)*upper_slope
    # Evaluate only each active region: unused power/exponential branches must
    # not overflow or manufacture invalid values at other intensities.
    y = np.full_like(x, np.nan)
    for mask, values in (
        (x < lp, lambda v: -lower+(v-lp)*lower_slope),
        ((x >= lp) & (x < sp), lambda v: -base(sp-v)),
        ((x >= sp) & (x < hp), lambda v: base(v-sp)),
        (x >= hp, lambda v: upper+(v-hp)*upper_slope),
    ):
        y[mask] = (values(x[mask])-zero)/(one-zero)
    # Restore exact endpoint constraints despite final floating-point rounding.
    y = np.clip(y, 0., 1.)
    return np.where(x == 0, 0., np.where(x == 1, 1., y))
