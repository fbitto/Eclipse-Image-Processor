"""Observed-only filtering adapter for images with an explicit validity mask.

Finite images keep the original backend. Spatial averages divide weighted signal
by observed support; invalid numerical buffers are never used as observations.
WOW on masked inputs uses an explicitly recorded normalized-starlet variant,
not an assertion of byte equivalence to watroo's unmasked implementation.
"""
import numpy as np
from scipy.ndimage import gaussian_filter, convolve1d
from .filters import adaptive_circular_highpass, blend_filter_result


class MaskedWorker:
    def __init__(self, worker, valid):
        self.worker = worker
        self.valid = valid

    def span(self, a):
        """Observed intensity range; transport-buffer zeros do not set limits."""
        return float(np.ptp(a[self.valid]))

    def norm(self, a):
        span = self.span(a)
        result = np.zeros_like(a, dtype=float)
        if span > 0:
            result[self.valid] = (a[self.valid] - a[self.valid].min()) / span
        return result

    def mix(self, a, filtered, strength):
        """Map observed filter output to input units before the Strength blend."""
        original = np.where(self.valid, a, np.nan)
        output = blend_filter_result(original, np.where(self.valid, filtered, np.nan), strength)
        return np.where(self.valid, output, 0).astype(np.float32)

    def blur(self, a, sigma, truncate=4, mode='reflect'):
        """Normalize Gaussian sums by observed support, without filling holes.

        This excludes missing samples but does not remove the radial-slope bias
        of a one-sided kernel near the lunar boundary.
        """
        weights = gaussian_filter(self.valid.astype(float), sigma, truncate=truncate, mode=mode)
        signal = gaussian_filter(np.where(self.valid, a, 0), sigma, truncate=truncate, mode=mode)
        return np.divide(signal, weights, out=np.zeros_like(signal), where=weights > 0)

    def run_pre_asinh(self, a, factor):
        if factor <= 0:
            return a.copy()
        return np.where(self.valid, np.arcsinh(self.norm(a)*factor)/np.arcsinh(factor)
                        * self.span(a) + a[self.valid].min(), 0).astype(np.float32)

    def run_pre_log(self, a, exponent):
        if exponent < 0:
            return a.copy()
        k = 10. ** exponent
        return np.where(self.valid, np.log1p(k*self.norm(a))/np.log1p(k)
                        * self.span(a) + a[self.valid].min(), 0).astype(np.float32)

    def run_fnrgf_native(self, a, *args, **kwargs):
        return np.where(self.valid, self.worker.run_fnrgf_native(a, *args, valid=self.valid, **kwargs), 0)

    def run_rhef_native(self, a, *args, **kwargs):
        return np.where(self.valid, self.worker.run_rhef_native(a, *args, valid=self.valid, **kwargs), 0)

    def run_mgn_native(self, a, strength, gamma, k, h, truncate, sigmas):
        if strength == 0 or self.span(a) == 0:
            return a.copy()
        data = np.where(self.valid, np.maximum(a, 1e-15), 0).astype(float)
        result = np.zeros_like(a, dtype=float)
        for sigma in sigmas:
            residual = data - self.blur(data, sigma, truncate=truncate, mode='nearest')
            deviation = np.sqrt(np.maximum(self.blur(residual**2, sigma, truncate=truncate, mode='nearest'), 0))
            result += np.arctan(np.divide(residual, deviation, out=np.zeros_like(residual), where=deviation > 0) * k / 100.)
        lower, upper = data[self.valid].min(), data[self.valid].max()
        global_image = (data-lower)/(upper-lower) if upper > lower else np.zeros_like(data)
        global_image = np.maximum(global_image, 0) ** (10. / gamma)
        result = (1-h/100.) * result / len(sigmas) + h/100. * global_image
        return self.mix(a, result, strength)

    def run_usm(self, a, strength, radius, amount):
        if strength == 0:
            return a.copy()
        blurred = self.blur(a, max(.5, radius/10))
        sharpened = np.clip(a + (a-blurred)*max(.1, amount), a[self.valid].min(), a[self.valid].max())
        return np.where(self.valid, (1-strength/100.)*a+strength/100.*sharpened, 0).astype(np.float32)

    def run_bilateral_denoise(self, a, strength, diameter, sigma_color, sigma_space):
        if strength == 0 or self.span(a) == 0:
            return a.copy()
        norm = self.norm(a)
        gradients = []
        # Use only observed pairs: a missing neighbour does not create an edge.
        for axis in (0, 1):
            gradient = np.zeros_like(a, dtype=float)
            left = [slice(None), slice(None)]; right = left.copy()
            left[axis], right[axis] = slice(None, -1), slice(1, None)
            l, r = tuple(left), tuple(right)
            pair = self.valid[l] & self.valid[r]
            diff = np.where(pair, norm[r]-norm[l], 0)
            gradient[l] += diff / 2
            gradient[r] += diff / 2
            gradients.append(gradient)
        edge = np.clip(1-self.norm(np.hypot(*gradients))*sigma_space/100., .1, 1)
        smooth = self.blur(norm, max(.5, diameter/10))
        result = (norm*(1-edge)+smooth*edge)*self.span(a)+a[self.valid].min()
        return np.where(self.valid, (1-strength/100.)*a+strength/100.*result, 0).astype(np.float32)

    def run_radial_noise_gate(self, a, strength, threshold, sx, sy, sr, spatial_scale=1):
        if strength == 0 or threshold == 0:
            return a.copy()
        magnitude = np.max(np.abs(a[self.valid]))
        if magnitude == 0:
            return a.copy()
        unit = a/magnitude
        mean = self.blur(unit, 3*spatial_scale)
        std = np.sqrt(np.maximum(self.blur((unit-mean)**2, 3*spatial_scale), 0))
        snr = np.divide(np.abs(mean), std, out=np.full_like(mean, np.inf), where=std > 0)
        yy, xx = np.ogrid[:a.shape[0], :a.shape[1]]
        limit = threshold/100. * (1+2*np.hypot(xx-sx, yy-sy)/sr)
        gate = np.clip((snr-limit)/limit, 0, 1)
        return np.where(self.valid, a*(1-strength/100.+strength/100.*self.blur(gate, 2*spatial_scale)), 0).astype(np.float32)

    def run_achf(self, a, strength, kernel, boost, sx, sy, sr, intensity_threshold=10, background=10, spatial_scale=1.0):
        if strength == 0:
            return a.copy()
        yy, xx = np.ogrid[:a.shape[0], :a.shape[1]]
        regions = ((xx-sx)**2+(yy-sy)**2 <= sr**2).astype(np.uint8)
        regions[~self.valid] = 2
        filtered = adaptive_circular_highpass(a, kernel/10., intensity_threshold/100.*self.span(a),
                                             gain=boost/10., background=background/100., regions=regions,
                                             spatial_scale=spatial_scale)
        return np.where(self.valid, (1-strength/100.)*a+strength/100.*filtered, 0).astype(np.float32)

    def starlet_blur(self, a, step, bilateral):
        coefficients = np.array([1, 4, 6, 4, 1], dtype=float)/16
        if bilateral is None:
            kernel = np.zeros(4*step+1)
            kernel[::step] = coefficients
            signal = np.where(self.valid, a, 0)
            support = self.valid.astype(float)
            for axis in (0, 1):
                signal = convolve1d(signal, kernel, axis=axis, mode='reflect')
                support = convolve1d(support, kernel, axis=axis, mode='reflect')
            return np.divide(signal, support, out=np.zeros_like(signal), where=support > 0)
        # Observed-only bilateral taps; no reflected values across missing data.
        height, width = a.shape
        numerator = np.zeros_like(a, dtype=float)
        denominator = np.zeros_like(a, dtype=float)
        sigma = max(float(np.std(a[self.valid]))*float(bilateral), np.finfo(float).tiny)
        for iy, cy in enumerate(coefficients):
            for ix, cx in enumerate(coefficients):
                dy, dx = (iy-2)*step, (ix-2)*step
                y0, y1 = max(0, -dy), min(height, height-dy)
                x0, x1 = max(0, -dx), min(width, width-dx)
                if y1 <= y0 or x1 <= x0:
                    continue
                target = np.s_[y0:y1, x0:x1]
                tap = np.s_[y0+dy:y1+dy, x0+dx:x1+dx]
                weight = cy*cx * self.valid[tap] * np.exp(-.5*((a[tap]-a[target])/sigma)**2)
                numerator[target] += weight*a[tap]
                denominator[target] += weight
        return np.divide(numerator, denominator, out=np.zeros_like(numerator), where=denominator > 0)

    def run_wow_native(self, a, strength=100, n_scales=None, denoise_coefficients=None, bilateral=None):
        if strength == 0 or self.span(a) == 0:
            return a.copy()
        maximum = int(np.round(np.log2(min(a.shape))-np.log2(5)))
        scales = maximum if not n_scales else min(int(n_scales), maximum)
        if scales < 1:
            raise ValueError('Image too small or invalid WOW scale count')
        levels = list(denoise_coefficients or [])
        from watroo import B3spline
        # Reference noise factors are approximate for masked or resampled HDR
        # data; they are not a measured per-pixel detector-noise calibration.
        factors = B3spline(2).sigma_e(bilateral=bilateral)
        result, coarse = np.zeros_like(a, dtype=float), a.copy()
        noise = None
        for j in range(scales):
            smooth = self.starlet_blur(coarse, 2**j, bilateral)
            detail = coarse-smooth
            if noise is None:
                observed = detail[self.valid]
                noise = 1.4826*np.median(np.abs(observed-np.median(observed)))/factors[0]
            power = np.sqrt(np.maximum(self.starlet_blur(detail**2, 2**j, None), 0))
            threshold = (levels[j] if j < len(levels) else 0)*noise*factors[j]
            denoised = np.sign(detail)*np.maximum(np.abs(detail)-threshold, 0)
            result += np.divide(denoised, power, out=np.zeros_like(detail), where=power > 0)
            coarse = np.where(self.valid, smooth, 0)
        spread = np.std(coarse[self.valid])
        if spread > 0:
            result += coarse/spread
        return self.mix(a, result, strength)
