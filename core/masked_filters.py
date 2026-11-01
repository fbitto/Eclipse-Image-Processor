"""Observed-only filtering adapter for images with an explicit validity mask.

Application MGN/non-AEL WOW use this adapter even on complete data; direct
numerical APIs retain their reference backend unless requested. Spatial averages divide weighted signal
by observed support; invalid numerical buffers are never used as observations.
WOW on masked inputs uses an explicitly recorded normalized-starlet variant,
not an assertion of byte equivalence to watroo's unmasked implementation.
"""
from .cancellation import check_cancelled
import numpy as np
from scipy.ndimage import gaussian_filter, convolve1d
from scipy.special import erf
from .filters import adaptive_circular_highpass, blend_filter_result, ordered_scale_results


class MaskedWorker:
    def __init__(self, worker, valid, targets=None):
        self.worker = worker
        self.valid = valid
        self.targets=valid if targets is None else targets

    def span(self, a):
        """Observed intensity range; transport-buffer zeros do not set limits."""
        return float(np.ptp(a[self.valid]))

    def mix(self, a, filtered, strength):
        """Map observed filter output to input units before the Strength blend."""
        original = np.where(self.targets, a, np.nan)
        output = blend_filter_result(original, np.where(self.targets, filtered, np.nan), strength,statistics=self.valid)
        return np.where(self.targets,np.where(np.isfinite(filtered),output,np.nan),0).astype(np.float32)

    def run_nrgf_native(self, a, *args, **kwargs):
        return np.where(self.valid, self.worker.run_nrgf_native(a, *args, valid=self.valid, **kwargs), 0)

    def run_fnrgf_native(self, a, *args, **kwargs):
        return np.where(self.valid, self.worker.run_fnrgf_native(a, *args, valid=self.valid, **kwargs), 0)

    def run_rhef_native(self, a, *args, **kwargs):
        return np.where(self.valid, self.worker.run_rhef_native(a, *args, valid=self.valid, **kwargs), 0)

    def run_mgn_native(self, a, strength, gamma, k, h, truncate, sigmas, weights=None, observed_edges=False):
        if strength == 0 or self.span(a) == 0:
            return a.copy()
        data = np.where(self.targets, a, 0).astype(float)
        magnitude = np.max(np.abs(data[self.valid]))
        if magnitude > 0 and (magnitude < 1e-10 or magnitude > 1e10):
            data /= magnitude
        data = np.where(self.targets, np.maximum(data, 1e-15), 0)
        result = np.zeros_like(a, dtype=float)
        weights = np.ones(len(sigmas)) if weights is None else weights
        def scale_detail(item):
            sigma, weight = item
            check_cancelled()
            if weight == 0:return np.zeros_like(data)
            support = gaussian_filter(self.valid.astype(float), sigma, truncate=truncate, mode='constant',cval=0)
            def blur(values):
                check_cancelled()
                signal = gaussian_filter(np.where(self.valid, values, 0), sigma,
                                         truncate=truncate, mode='constant',cval=0)
                return np.divide(signal, support, out=np.full_like(signal,np.nan), where=support > 0)
            residual = data-blur(data)
            deviation = np.sqrt(np.maximum(blur(residual**2), 0))
            detail=weight*np.arctan(np.divide(residual, deviation,
                    out=np.zeros_like(residual), where=deviation > 0)*k/100.)
            return np.where(support>0,detail,np.nan)
        for detail in ordered_scale_results(scale_detail, zip(sigmas, weights), data):
            result += detail
        lower, upper = data[self.valid].min(), data[self.valid].max()
        global_image = (data-lower)/(upper-lower) if upper > lower else np.zeros_like(data)
        global_image = np.maximum(global_image, 0) ** (10. / gamma)
        result = (1-h/100.) * result / len(sigmas) + h/100. * global_image
        return self.mix(a, result, strength)


    def run_larson_sekanina(self, a, *args, **kwargs):
        return np.where(self.valid, self.worker.run_larson_sekanina(a, *args, valid=self.valid, **kwargs), 0)

    def run_tangential(self, a, *args, **kwargs):
        return np.where(self.targets, self.worker.run_tangential(a, *args, valid=self.valid,target_valid=self.targets, **kwargs), 0)

    def run_achf(self, a, strength, kernel, boost, sx, sy, sr, intensity_threshold=10, background=10, spatial_scale=1.0, threshold_mode="absolute"):
        if strength == 0:
            return a.copy()
        yy, xx = np.ogrid[:a.shape[0], :a.shape[1]]
        regions = ((xx-sx)**2+(yy-sy)**2 <= sr**2).astype(np.uint8)
        regions[~self.targets] = 2
        threshold=intensity_threshold/100.
        if threshold_mode == "absolute":threshold *= self.span(a)
        filtered = adaptive_circular_highpass(a, kernel/10., threshold,
                                             gain=boost/10., background=background/100., regions=regions,
                                             spatial_scale=spatial_scale,threshold_mode=threshold_mode,sample_valid=self.valid)
        return np.where(self.targets, (1-strength/100.)*a+strength/100.*filtered, 0).astype(np.float32)

    def starlet_blur(self, a, step, bilateral):
        coefficients = np.array([1, 4, 6, 4, 1], dtype=float)/16
        if bilateral is None:
            kernel = np.zeros(4*step+1)
            kernel[::step] = coefficients
            signal = np.where(self.valid, a, 0)
            support = self.valid.astype(float)
            for axis in (0, 1):
                check_cancelled()
                def convolve(values):
                    if step < 8:
                        return convolve1d(values, kernel, axis=axis, mode='constant',cval=0)
                    padding = [(0, 0)]*2
                    padding[axis] = (2*step, 2*step)
                    extended = np.pad(values, padding, mode='constant')
                    # Match SciPy: double accumulation, round once per axis.
                    result = np.zeros(values.shape, dtype=float)
                    for j, coefficient in enumerate(coefficients):
                        check_cancelled()
                        slices = [slice(None)]*2
                        slices[axis] = slice(j*step, j*step+values.shape[axis])
                        result += coefficient*extended[tuple(slices)]
                    return result.astype(values.dtype, copy=False)
                signal = convolve(signal)
                support = convolve(support)
            return np.divide(signal, support, out=np.full_like(signal,np.nan), where=support > 0)
        # Observed-only bilateral taps; no reflected values across missing data.
        height, width = a.shape
        numerator = np.zeros_like(a, dtype=float)
        denominator = np.zeros_like(a, dtype=float)
        if not np.isfinite(bilateral) or bilateral <= 0:
            raise ValueError('Bilateral scale must be positive and finite')
        mean=self.starlet_blur(a,step,None)
        data=np.where(self.valid,a,0)
        variance=np.maximum(self.starlet_blur(data*data,step,None)-mean*mean,0)
        sigma=np.maximum(np.sqrt(variance)*float(bilateral),np.finfo(float).tiny)
        for iy, cy in enumerate(coefficients):
            check_cancelled()
            for ix, cx in enumerate(coefficients):
                check_cancelled()
                dy, dx = (iy-2)*step, (ix-2)*step
                y0, y1 = max(0, -dy), min(height, height-dy)
                x0, x1 = max(0, -dx), min(width, width-dx)
                if y1 <= y0 or x1 <= x0:
                    continue
                target = np.s_[y0:y1, x0:x1]
                tap = np.s_[y0+dy:y1+dy, x0+dx:x1+dx]
                # Missing transport values are not bilateral observations. Bound
                # the difference before division: a constant observed image has
                # sigma=tiny, so even a finite missing-buffer value can overflow.
                # At 40 sigma the Gaussian weight is already zero in float64.
                pair = self.valid[tap] & self.targets[target]
                difference = np.subtract(a[tap], a[target],
                                         out=np.zeros(pair.shape, dtype=float), where=pair)
                local_sigma=sigma[target]
                distance = np.divide(np.clip(difference,-40*local_sigma,40*local_sigma),local_sigma,
                                     out=np.zeros_like(difference),where=pair)
                weight = cy*cx * pair * np.exp(-.5*distance**2)
                numerator[target] += np.multiply(weight, a[tap],
                                                 out=np.zeros(pair.shape, dtype=float), where=pair)
                denominator[target] += weight
        return np.divide(numerator, denominator, out=np.full_like(numerator,np.nan), where=denominator > 0)

    def run_wow_native(self, a, strength=100, n_scales=None, denoise_coefficients=None, bilateral=None, observed_edges=False, noise=None):
        if strength == 0 or self.span(a) == 0:
            return a.copy()
        maximum = int(np.round(np.log2(min(a.shape))-np.log2(5)))
        scales = maximum if not n_scales else min(int(n_scales), maximum)
        if scales < 1:
            raise ValueError('Image too small or invalid WOW scale count')
        levels = list(denoise_coefficients or [])
        if not np.isfinite(levels).all() or any(level < 0 for level in levels):
            raise ValueError("Noise significance levels must be nonnegative and finite")
        if noise is not None:
            noise=np.asarray(noise,dtype=float)
            if noise.shape != a.shape or not np.isfinite(noise).all() or (noise<0).any():
                raise ValueError("Noise map must match image and be finite and nonnegative")
        from watroo import B3spline
        # Reference noise factors are approximate for masked or resampled HDR
        # data; they are not a measured per-pixel detector-noise calibration.
        factors = B3spline(2).sigma_e(bilateral=bilateral)
        result, coarse = np.zeros_like(a, dtype=float), np.where(self.targets,a,0).astype(float)
        for j in range(scales):
            check_cancelled()
            smooth = self.starlet_blur(coarse, 2**j, bilateral)
            detail = coarse-smooth
            if noise is None:
                observed = detail[self.valid]
                noise = 1.4826*np.median(np.abs(observed-np.median(observed)))/factors[0]
            power = np.sqrt(np.maximum(self.starlet_blur(detail**2, 2**j, None), 0))
            threshold = (levels[j] if j < len(levels) else 0)*noise*factors[j]
            ratio=np.divide(np.abs(detail),threshold,out=np.full_like(detail,np.inf),where=np.asarray(threshold)>0)
            denoised=detail*erf(ratio)
            result += np.divide(denoised, power, out=np.zeros_like(detail), where=power > 0)
            coarse = np.where(self.targets, smooth, 0)
        spread = np.std(coarse[self.valid])
        if spread > 0:
            result += coarse/spread
        return self.mix(a, result, strength)
