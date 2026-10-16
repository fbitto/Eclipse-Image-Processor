"""
FilterWorker: Native NumPy/SciPy coronal enhancement engine.

Contains all 10 scientific filters:
  - PRE-STRETCH: Asinh & Logarithmic
  - DENOISING: Radial Noise Gate, Bilateral
  - RADIAL: FNRGF, RHEF
  - MULTI-SCALE: MGN, WOW
  - SHARPENING: USM, ACHF
"""

import os
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Tuple

import cv2
import numpy as np
from PySide6.QtCore import QObject, Signal, Slot
from scipy.ndimage import gaussian_filter, gaussian_filter1d
import numpy as np
from scipy.stats import rankdata

CPU_CORES = os.cpu_count() or 4


def blend_filter_result(image, filtered, strength):
    """Presentation blend in common input units; scientific cores stay untouched.

    Affinely map the full filtered range to the input range before mixing.
    No clipping or percentile loss. Constant filtered output maps to input mean.
    """
    original = np.asarray(image, dtype=np.float64)
    if strength == 0:
        return np.array(image, copy=True)
    result = np.asarray(filtered, dtype=np.float64)
    mask = np.isfinite(original) & np.isfinite(result)
    output = original.copy()
    if not np.any(mask):
        return output.astype(np.float32)
    source = original[mask]
    values = result[mask]
    span = np.ptp(values)
    mapped = (source.min() + (values-values.min())/span*np.ptp(source)
              if span > 0 else np.full(values.shape, source.mean()))
    alpha = float(strength)/100.0
    output[mask] = (1-alpha)*source + alpha*mapped
    return output.astype(np.float32)


def mgn_normalize(image, sigma=None, k=0.7, gamma=3.2, h=0.7,
                  weights=None, truncate=3, clip=True,
                  gamma_min=None, gamma_max=None):
    """Array MGN matching sunkit-image 0.7.0's numerical operations.

    Reference: https://docs.sunpy.org/projects/sunkit-image/en/stable/
    _modules/sunkit_image/enhance.html#mgn
    Morgan & Druckmuller (2014), doi:10.1007/s11207-014-0523-9.
    Unlike the reference, never mutate the caller's input or global error state.
    NaNs propagate; this is not a mask-aware implementation.
    """
    scales = (1.25, 2.5, 5, 10, 20, 40) if sigma is None else tuple(sigma)
    scale_weights = np.ones(len(scales)) if weights is None else tuple(weights)
    if not scales or len(scale_weights) != len(scales):
        raise ValueError("MGN needs equally sized, nonempty sigma and weights")
    if not np.isfinite(scales).all() or np.any(np.asarray(scales) <= 0):
        raise ValueError("MGN sigmas must be positive and finite")
    if not np.isfinite([k, gamma, h, truncate]).all() or gamma <= 0 or truncate <= 0:
        raise ValueError("Invalid MGN parameters")
    data = np.array(image, copy=True)
    if data.ndim != 2:
        raise ValueError("MGN requires a 2D image")
    if clip:
        data[data <= 0] = 1e-15
    data = data.astype(np.float32)
    result = np.zeros_like(data)
    with np.errstate(all="ignore"):
        for scale, weight in zip(scales, scale_weights):
            residual = data-gaussian_filter(data, scale, truncate=truncate, mode="nearest")
            deviation = np.sqrt(gaussian_filter(residual**2, scale,
                                               truncate=truncate, mode="nearest"))
            deviation = np.where(deviation == 0, 1.0, deviation)
            residual /= deviation
            residual *= k
            np.arctan(residual, out=residual)
            residual *= weight
            result += residual
        result /= len(scales)
        lower = data.min() if gamma_min is None else gamma_min
        upper = data.max() if gamma_max is None else gamma_max
        global_image = data-lower
        if upper-lower != 0:
            global_image /= upper-lower
        global_image **= 1/gamma
        global_image *= h
        result *= 1-h
        result += global_image
    return result


def rhef_normalize(image, radii, bin_edges, application_radius=0.0,
                   upsilon=0.35, valid=None, vignette=None):
    """Array RHEF following sunkit-image's scipy ranking and upsilon convention.

    Radii, bin edges and radial limits must share units. Ties get average ranks.
    Upsilon branches are selected using the mean rank in each annulus, as in
    sunkit_image.utils.apply_upsilon (not a fixed 0.5 split). Returns NaN outside
    the domain; no presentation rescaling or original-image blending.
    Reference: sunkit-image RHEF; Gilly (2022), thesis, as cited by that package.
    """
    a = np.asarray(image, dtype=np.float64)
    r = np.asarray(radii, dtype=np.float64)
    edges = np.asarray(bin_edges, dtype=float)
    if a.ndim != 2 or r.shape != a.shape:
        raise ValueError("Image and radii must be matching 2D arrays")
    if edges.ndim != 1 or edges.size < 2 or not np.isfinite(edges).all() or np.any(np.diff(edges) <= 0):
        raise ValueError("Bin edges must be finite and strictly increasing")
    if not np.isfinite(application_radius) or application_radius < 0:
        raise ValueError("Invalid application radius")
    if vignette is not None and (not np.isfinite(vignette) or vignette < application_radius):
        raise ValueError("Vignette must be at or above application radius")
    if upsilon is not None:
        exponents = np.asarray(upsilon if np.ndim(upsilon) else (upsilon, upsilon), dtype=float)
        if exponents.shape != (2,) or not np.isfinite(exponents).all() or np.any(exponents <= 0):
            raise ValueError("Upsilon needs one or two positive finite exponents")
    mask = np.isfinite(a) & np.isfinite(r) & (r >= application_radius)
    if valid is not None:
        if np.shape(valid) != a.shape:
            raise ValueError("Valid mask must match image")
        mask &= np.asarray(valid, dtype=bool)
    bins = np.searchsorted(edges, r, side="right")-1
    mask &= (bins >= 0) & (bins < edges.size-1)
    indices = np.flatnonzero(mask)
    indices = indices[np.argsort(bins.ravel()[indices], kind="stable")]
    bin_ids = bins.ravel()[indices]
    boundaries = np.r_[0, np.flatnonzero(np.diff(bin_ids))+1, indices.size]
    out = np.full(a.size, np.nan)
    for start, stop in zip(boundaries[:-1], boundaries[1:]):
        target = indices[start:stop]
        if not target.size:
            continue
        ranks = rankdata(a.ravel()[target], method="average")/target.size
        if upsilon is not None:
            low = ranks < ranks.mean()
            transformed = np.empty_like(ranks)
            transformed[low] = .5*(2*ranks[low])**exponents[0]
            transformed[~low] = 1-.5*(2-2*ranks[~low])**exponents[1]
            ranks = transformed
        out[target] = ranks
    out = out.reshape(a.shape)
    # Reference applies vignette after ranking; do not change ring populations.
    if vignette is not None:
        out[r > vignette] = np.nan
    return out


def fnrgf_normalize(image, radii, angles, bin_edges, order=3, segments=130,
                    cutoff=0, application_radius=1.0, width_function="std",
                    mean_attenuation_range=(1.0, 0.0),
                    std_attenuation_range=(1.0, 0.0), min_pixels=1):
    """Array FNRGF core following sunkit-image's Fourier coefficient convention.

    Includes its attenuation[1] convention for the constant terms. Empty
    sectors contribute zero, as in the reference. Nonfinite samples are ignored;
    nonpositive reconstructed widths use 1 (reference only guards exact zero).
    MAD changes width only, never the mean. Unprocessed pixels are NaN.
    No display scaling, smoothing, original-image mix or limb mask is applied.
    """
    a = np.asarray(image, dtype=np.float64)
    r, theta = np.asarray(radii), np.asarray(angles) % (2*np.pi)
    edges = np.asarray(bin_edges, dtype=float)
    order, segments, cutoff = int(order), int(segments), int(cutoff)
    if a.ndim != 2 or r.shape != a.shape or theta.shape != a.shape:
        raise ValueError("Image, radii and angles must be matching 2D arrays")
    if order < 1 or segments < 2*order+1 or not 0 <= cutoff <= order+1:
        raise ValueError("Need order >= 1, segments >= 2*order+1 and cutoff <= order+1")
    if edges.ndim != 1 or edges.size < 2 or not np.all(np.isfinite(edges)) or np.any(np.diff(edges) <= 0):
        raise ValueError("Radial edges must be finite and strictly increasing")
    if width_function not in ("std", "mad") or min_pixels < 1:
        raise ValueError("Invalid width function or minimum sector population")
    attenuation = np.array([np.linspace(*mean_attenuation_range, order+1),
                            np.linspace(*std_attenuation_range, order+1)])
    if cutoff:
        attenuation[:, -cutoff:] = 0
    phi = (np.arange(segments)+.5)*2*np.pi/segments
    harmonics = np.arange(1, order+1)
    cos = np.cos(np.outer(phi, harmonics))
    sin = np.sin(np.outer(phi, harmonics))
    flat, rf, tf = a.ravel(), r.ravel(), theta.ravel()
    bins = np.searchsorted(edges, rf, side="right")-1
    valid = ((bins >= 0) & (bins < len(edges)-1) & (rf > application_radius)
             & np.isfinite(flat) & np.isfinite(tf))
    pix = np.flatnonzero(valid)
    sector = np.minimum((tf[pix]*segments/(2*np.pi)).astype(int), segments-1)
    keys = bins[pix]*segments+sector
    sorting = np.argsort(keys, kind="stable")
    pix = pix[sorting]
    counts = np.bincount(keys, minlength=(len(edges)-1)*segments)
    offsets = np.r_[0, np.cumsum(counts)]
    out = np.full(flat.shape, np.nan)

    def process_bin(b):
        means, widths = np.zeros(segments), np.zeros(segments)
        for j in range(segments):
            key = b*segments+j
            values = flat[pix[offsets[key]:offsets[key+1]]]
            if values.size < min_pixels:
                continue
            means[j] = values.mean()
            widths[j] = (values.std() if width_function == "std" else
                         1.4826*np.median(np.abs(values-np.median(values))))
        target = pix[offsets[b*segments]:offsets[(b+1)*segments]]
        if not target.size:
            return
        ct = np.cos(np.outer(tf[target], harmonics))
        st = np.sin(np.outer(tf[target], harmonics))
        profiles = []
        for values, atten in zip((means, widths), attenuation):
            profiles.append(values.mean()*atten[1] +
                            ct @ ((2/segments)*(values @ cos)*atten[1:]) +
                            st @ ((2/segments)*(values @ sin)*atten[1:]))
        mean, width = profiles
        width = np.where(width > 0, width, 1.0)
        out[target] = (flat[target]-mean)/width

    with ThreadPoolExecutor(max_workers=CPU_CORES) as executor:
        list(executor.map(process_bin, range(len(edges)-1)))
    return out.reshape(a.shape)


def adaptive_circular_highpass(image, radius, intensity_threshold, gain=2.0,
                               background=0.1, regions=None):
    """Own variable-kernel implementation of Druckmuller et al. (2006), §4.2.

    Threshold is absolute in input intensity units. Opposite neighbors are
    accepted together, preserving an even, real-spectrum local kernel.
    C_p = background*delta + gain*(delta - W_p), with normalized W_p.
    The paper specifies constraints, not the exact Corona 3.0 algorithm.
    Complexity: O(pixels * radius**2); working memory: O(pixels).
    """
    a = np.asarray(image, dtype=np.float64)
    if a.ndim != 2 or not np.isfinite(a).all():
        raise ValueError("ACHF requires a finite 2D image")
    if not np.isfinite([radius, intensity_threshold, gain, background]).all():
        raise ValueError("ACHF parameters must be finite")
    if radius <= 0 or intensity_threshold < 0 or gain < 0 or not 0 <= background < 1:
        raise ValueError("Invalid ACHF radius, threshold, gain or background")
    labels = np.zeros(a.shape, dtype=np.uint8) if regions is None else np.asarray(regions)
    if labels.shape != a.shape:
        raise ValueError("Region labels must match image dimensions")
    h, w = a.shape
    sigma = max(radius / 3.0, 0.25)
    numerator = np.zeros_like(a)
    denominator = np.ones_like(a)  # central Gaussian weight
    # Enumerate one half of the circular support; never wrap image borders.
    for dy in range(0, min(int(np.ceil(radius)), (h - 1) // 2) + 1):
        for dx in range(-min(int(np.ceil(radius)), (w - 1) // 2),
                        min(int(np.ceil(radius)), (w - 1) // 2) + 1):
            if (dy == 0 and dx <= 0) or dx*dx + dy*dy > radius*radius:
                continue
            y0, y1, x0, x1 = dy, h-dy, abs(dx), w-abs(dx)
            center = a[y0:y1, x0:x1]
            plus = a[y0+dy:y1+dy, x0+dx:x1+dx]
            minus = a[y0-dy:y1-dy, x0-dx:x1-dx]
            region = labels[y0:y1, x0:x1]
            accepted = ((np.abs(plus-center) <= intensity_threshold)
                        & (np.abs(minus-center) <= intensity_threshold)
                        & (labels[y0+dy:y1+dy, x0+dx:x1+dx] == region)
                        & (labels[y0-dy:y1-dy, x0-dx:x1-dx] == region))
            weight = accepted * np.exp(-(dx*dx+dy*dy)/(2*sigma*sigma))
            numerator[y0:y1, x0:x1] += weight * ((center-plus)+(center-minus))
            denominator[y0:y1, x0:x1] += 2*weight
    # Signed output is intentional. No clipping or min/max normalization here.
    return (background*a + gain*numerator/denominator).astype(np.float32)


class FilterWorker(QObject):
    """Executes coronal enhancement filters with multi-threaded native C/NumPy engines."""

    finished = Signal(np.ndarray)
    failed = Signal(str)

    @Slot(np.ndarray, dict)
    def process_pipeline(self, raw_image: np.ndarray, params: dict):
        """Always report completion or failure so the GUI can accept new work."""
        try:
            if raw_image is None:
                raise ValueError("No image supplied")
            self._process_pipeline(raw_image, params)
        except Exception as error:
            import traceback
            traceback.print_exc()
            self.failed.emit(str(error))

    def _process_pipeline(self, raw_image: np.ndarray, params: dict):
        """Sequentially applies enabled scientific filters."""
        if raw_image is None:
            return

        pipeline_start = time.time()
        print(f"\n{'='*80}\n[PIPELINE] Execution start (Native Engine - {CPU_CORES} CPUs) - Shape: {raw_image.shape}\n{'='*80}")

        img = raw_image.copy()
        p = params

        # STEP 0: PRE-STRETCH (ASINH / LOGARITHMIC)
        if p.get("pre_stretch_enabled", False):
            mode = p.get("pre_stretch_mode", "asinh")
            val = p.get("pre_stretch_val", 10.0)
            step_start = time.time()
            if mode == "log":
                img = self.run_pre_log(img, val)
                print(f"[PRE-STRETCH: LOG] Done in {time.time() - step_start:.3f}s (K=10^{val:.1f})")
            else:
                img = self.run_pre_asinh(img, val)
                print(f"[PRE-STRETCH: ASINH] Done in {time.time() - step_start:.3f}s (Factor={val})")

        # STEP 0B: RADIAL NOISE GATE
        if p.get("noise_gate_enabled", False):
            step_start = time.time()
            img = self.run_radial_noise_gate(
                img, p["noise_gate_str"], p["noise_gate_thr"], p["sx"], p["sy"], p["sr"]
            )
            print(f"[NOISE GATE] Done in {time.time() - step_start:.3f}s")

        # STEP 0C: BILATERAL DENOISE
        if p.get("bilateral_enabled", False):
            step_start = time.time()
            img = self.run_bilateral_denoise(
                img, p["bilateral_str"], p["bilateral_d"], p["bilateral_sc"], p["bilateral_ss"]
            )
            print(f"[BILATERAL] Done in {time.time() - step_start:.3f}s")

        # STEP 1A: NATIVE FNRGF ENGINE (MULTI-THREADED)
        if p.get("fnrgf_enabled", False):
            step_start = time.time()
            img = self.run_fnrgf_native(
                img,
                p["fnrgf_str"],
                p["fnrgf_ord"],
                p["fnrgf_seg"],
                p["fnrgf_cut"],
                p["fnrgf_rad"],
                p.get("fnrgf_rmax", 30),
                p.get("fnrgf_nbins", 100),
                p["sx"],
                p["sy"],
                p["sr"],
                width_function=p.get("fnrgf_width_func", "std"),
                radial_binning=p.get("fnrgf_radial_binning", "linear"),
                apply_mask=p.get("fnrgf_apply_mask", 0),
            )
            print(f"[FNRGF NATIVE] Done in {time.time() - step_start:.3f}s")

        # STEP 2A: NATIVE MGN ENGINE (MULTI-SCALE GAUSSIAN NORMALIZATION)
        if p.get("mgn_enabled", False):
            step_start = time.time()
            img = self.run_mgn_native(
                img,
                p["mgn_str"],
                p["mgn_gam"],
                p.get("mgn_k", 70),
                p.get("mgn_h", 70),
                p.get("mgn_trunc", 3),
            )
            print(f"[MGN NATIVE] Done in {time.time() - step_start:.3f}s")

        # STEP 2B: NATIVE WOW ENGINE (A TROUS WAVELETS WHITENING)
        if p.get("wow_enabled", False):
            step_start = time.time()
            img = self.run_wow_native(
                img, p["wow_str"], p.get("wow_scales"),
                denoise_coefficients=p.get("wow_denoise", []),
                bilateral=p.get("wow_bilateral"),
            )
            print(f"[WOW NATIVE] Done in {time.time() - step_start:.3f}s")

        # STEP 2C: NATIVE RHEF ENGINE
        if p.get("rhef_enabled", False):
            step_start = time.time()
            img = self.run_rhef_native(
                img, p["rhef_str"], p["rhef_rad"], p["rhef_upsilon"], p["sx"], p["sy"], p["sr"],
                bin_px=p.get("rhef_bin_px", 1.0),
            )
            print(f"[RHEF NATIVE] Done in {time.time() - step_start:.3f}s")

        # STEP 3: UNSHARP MASK
        if p.get("usm_enabled", False):
            step_start = time.time()
            img = self.run_usm(img, p["usm_str"], p["usm_radius"], p["usm_sigma"])
            print(f"[USM] Done in {time.time() - step_start:.3f}s")

        # STEP 4: ACHF (SYMMETRIC VARIABLE KERNEL)
        if p.get("achf_enabled", False):
            step_start = time.time()
            img = self.run_achf(
                img, p["achf_str"], p["achf_kernel"], p["achf_boost"], p["sx"], p["sy"], p["sr"],
                intensity_threshold=p.get("achf_threshold", 10),
                background=p.get("achf_background", 10),
            )
            print(f"[ACHF] Done in {time.time() - step_start:.3f}s")

        print(f"[PIPELINE] Complete. Total time: {time.time() - pipeline_start:.3f}s\n{'='*80}\n")
        self.finished.emit(img)

    def run_pre_asinh(self, img: np.ndarray, factor: float) -> np.ndarray:
        if factor <= 0:
            return img.copy()
        try:
            cleaned = np.nan_to_num(img, nan=0.0)
            i_min, i_max = float(np.min(cleaned)), float(np.max(cleaned))
            if i_max - i_min <= 1e-6:
                return img.copy()
            norm = (cleaned - i_min) / (i_max - i_min + 1e-5)
            beta = float(factor)
            stretched = np.arcsinh(norm * beta) / np.arcsinh(beta)
            return (stretched * (i_max - i_min) + i_min).astype(np.float32)
        except Exception as e:
            print(f"Error in Pre-Asinh Stretch: {e}")
            return img.copy()

    def run_pre_log(self, img: np.ndarray, log_exp: float) -> np.ndarray:
        if log_exp <= 0:
            return img.copy()
        try:
            cleaned = np.nan_to_num(img, nan=0.0)
            i_min, i_max = float(np.min(cleaned)), float(np.max(cleaned))
            if i_max - i_min <= 1e-6:
                return img.copy()
            norm = (cleaned - i_min) / (i_max - i_min + 1e-5)
            k = 10.0 ** float(log_exp)
            stretched = np.log1p(k * norm) / np.log1p(k)
            return (stretched * (i_max - i_min) + i_min).astype(np.float32)
        except Exception as e:
            print(f"Error in Pre-Log Stretch: {e}")
            return img.copy()

    def run_radial_noise_gate(
        self, img: np.ndarray, strength: float, threshold_param: float, sun_x: float, sun_y: float, sun_r: float
    ) -> np.ndarray:
        if strength == 0:
            return img.copy()
        try:
            h, w = img.shape[:2]
            cx, cy = float(sun_x), float(sun_y)
            r0 = float(sun_r if sun_r > 5 else 100.0)

            y_indices, x_indices = np.indices((h, w), dtype=np.float32)
            r_map = np.hypot(x_indices - cx, y_indices - cy) / (r0 + 1e-5)

            local_mean = gaussian_filter(img, sigma=3.0)
            local_var = gaussian_filter((img - local_mean) ** 2, sigma=3.0)
            local_std = np.sqrt(local_var + 1e-8)

            snr = np.abs(local_mean) / (local_std + 1e-8)
            threshold_base = float(threshold_param / 100.0)
            threshold_map = threshold_base * (1.0 + r_map * 2.0)

            gate = np.clip((snr - threshold_map) / (threshold_map + 1e-8), 0.0, 1.0)
            gate_smooth = gaussian_filter(gate, sigma=2.0)
            denoised = img * gate_smooth

            alpha = strength / 100.0
            return cv2.addWeighted(denoised.astype(np.float32), alpha, img, 1.0 - alpha, 0)
        except Exception as e:
            print(f"Error in Radial Noise Gate: {e}")
            return img.copy()

    def run_bilateral_denoise(
        self, img: np.ndarray, strength: float, diameter_param: float, sigma_color_param: float, sigma_space_param: float
    ) -> np.ndarray:
        if strength == 0:
            return img.copy()
        try:
            img_clean = np.nan_to_num(img, nan=0.0)
            img_min, img_max = float(np.min(img_clean)), float(np.max(img_clean))
            if img_max - img_min < 1e-6:
                return img.copy()

            img_norm = (img_clean - img_min) / (img_max - img_min + 1e-8)
            blur_radius = max(0.5, float(diameter_param / 10.0))

            gy, gx = np.gradient(img_norm)
            gradient_mag = np.sqrt(gx**2 + gy**2)
            grad_min, grad_max = float(np.min(gradient_mag)), float(np.max(gradient_mag))

            if grad_max - grad_min > 1e-6:
                gradient_norm = (gradient_mag - grad_min) / (grad_max - grad_min)
            else:
                gradient_norm = np.zeros_like(gradient_mag)

            edge_sensitivity = float(sigma_space_param / 100.0)
            edge_weight = np.clip(1.0 - gradient_norm * edge_sensitivity, 0.1, 1.0)
            smoothed = gaussian_filter(img_norm, sigma=blur_radius)

            denoised_norm = img_norm * (1.0 - edge_weight) + smoothed * edge_weight
            denoised = denoised_norm * (img_max - img_min) + img_min

            alpha = strength / 100.0
            return cv2.addWeighted(denoised.astype(np.float32), alpha, img, 1.0 - alpha, 0)
        except Exception as e:
            print(f"Error in Edge-Preserving Denoise: {e}")
            return img.copy()


    def run_fnrgf_native(
        self, img, strength, order_fourier, angular_segments, cutoff_val,
        app_radius_val, rmax_val, nbins_val, sun_x, sun_y, sun_r,
        width_function="std", radial_binning="linear", apply_mask=0,
        min_pixels_per_sector=1, clip_pct=0.0,
        mean_attenuation_range=(1.0, 0.0), std_attenuation_range=(1.0, 0.0),
    ) -> np.ndarray:
        """Fourier Normalizing Radial Gradient Filter plus optional display mix.

        Core output is dimensionless. Outside the application domain the input
        is preserved. clip_pct > 0 explicitly enables percentile display scaling.
        """
        if strength == 0:
            return img.copy()
        a = np.asarray(img, dtype=np.float32)
        if sun_r <= 0 or not np.isfinite(sun_r):
            raise ValueError("FNRGF requires a positive disk radius")
        app_r, outer = float(app_radius_val)/10, float(rmax_val)/10
        if not 0 < app_r < outer or int(nbins_val) < 1:
            raise ValueError("FNRGF needs 0 < application radius < outer radius")
        yy, xx = np.indices(a.shape, dtype=float)
        r = np.hypot(xx-sun_x, yy-sun_y)/sun_r
        theta = np.arctan2(yy-sun_y, xx-sun_x)
        if radial_binning == "log":
            edges = np.geomspace(app_r, outer, int(nbins_val)+1)
        elif radial_binning == "linear":
            edges = np.linspace(app_r, outer, int(nbins_val)+1)
        else:
            raise ValueError("Unknown radial binning")
        filtered = fnrgf_normalize(
            a, r, theta, edges, order=int(order_fourier),
            segments=int(angular_segments), cutoff=int(cutoff_val),
            application_radius=app_r, width_function=width_function,
            mean_attenuation_range=mean_attenuation_range,
            std_attenuation_range=std_attenuation_range,
            min_pixels=min_pixels_per_sector,
        )
        valid = np.isfinite(filtered)
        if clip_pct > 0 and np.any(valid):
            if not 0 < clip_pct < 50:
                raise ValueError("clip_pct must be between 0 and 50")
            lo, hi = np.percentile(filtered[valid], [clip_pct, 100-clip_pct])
            if hi > lo:
                source = a[valid]
                filtered[valid] = (np.clip((filtered[valid]-lo)/(hi-lo), 0, 1)
                                   * np.ptp(source)+source.min())
        # Compact protection band: zero contribution outside 0.95..1.05 R_sun.
        protection = np.clip(1-np.abs(r-1.0)/.05, 0, 1)
        alpha = float(strength)/100 * (1-float(apply_mask)/100*protection)
        result = a.copy()
        result[valid] = ((1-alpha[valid])*a[valid]+alpha[valid]*filtered[valid])
        return result

    def run_rhef_native(
        self, img, strength, app_radius_val, upsilon_val, sun_x, sun_y, sun_r,
        valid=None, upsilon_h_val=None, vignette_rsun=None, bin_px=1.0,
    ) -> np.ndarray:
        """RHEF core plus external Strength blend; no percentile rescaling.

        UI radius is in tenths of disk radius and upsilon in hundredths.
        bin_px is the ring width in pixels of the supplied image.
        Outside application radius preserve input; vignette explicitly returns NaN.
        """
        if strength == 0:
            return img.copy()
        if not np.isfinite([sun_r, bin_px]).all() or sun_r <= 0 or bin_px <= 0:
            raise ValueError("RHEF needs positive disk radius and bin width")
        a = np.asarray(img, dtype=np.float32)
        yy, xx = np.indices(a.shape, dtype=float)
        r = np.hypot(xx-sun_x, yy-sun_y)
        edges = np.arange(int(np.floor(r.max()/bin_px))+2, dtype=float)*bin_px
        upsilon = None if upsilon_val is None else (
            float(upsilon_val)/100,
            float(upsilon_val if upsilon_h_val is None else upsilon_h_val)/100)
        filtered = rhef_normalize(
            a, r, edges, application_radius=float(app_radius_val)/10*sun_r,
            upsilon=upsilon, valid=valid,
            vignette=None if vignette_rsun is None else float(vignette_rsun)*sun_r,
        )
        selected = np.isfinite(filtered)
        result = a.copy()
        alpha = float(strength)/100
        result[selected] = (1-alpha)*a[selected]+alpha*filtered[selected]
        if vignette_rsun is not None:
            result[r > float(vignette_rsun)*sun_r] = np.nan
        return result

    def run_mgn_native(
        self, img, strength, gamma_val, k_val, h_val, trunc_val,
        sigmas=(1.25, 2.5, 5.0, 10.0, 20.0, 40.0), weights=None,
    ) -> np.ndarray:
        """Official MGN core, with UI units and an external Strength blend.

        The core is unchanged; its result is affinely mapped to input units for Strength.
        Gaussian widths remain in input pixels, as in sunkit-image.
        """
        if strength == 0:
            return img.copy()
        filtered = mgn_normalize(
            img, sigma=sigmas, gamma=float(gamma_val)/10,
            k=float(k_val)/100, h=float(h_val)/100,
            truncate=float(trunc_val), weights=weights,
        )
        return blend_filter_result(img, filtered, strength)

    def run_wow_native(self, image, strength=100, n_scales=None,
                       denoise_coefficients=None, noise=None, bilateral=None):
        """WOW via watroo, the backend used by sunkit-image.

        No fixed detector calibration or output z-scaling. Optional noise map
        must be calibrated in units of THIS input, after any preceding filters.
        Empty denoising coefficients disable denoising; missing noise is estimated
        by watroo when denoising is requested. Strength is an external blend.
        """
        if strength == 0:
            return image.copy()
        from watroo import B3spline, utils
        a = np.array(image, dtype=np.float64, copy=True)
        if a.ndim != 2 or not np.isfinite(a).all():
            raise ValueError("WOW requires a finite 2D image")
        maximum = int(np.round(np.log2(min(a.shape))-np.log2(5)))
        if maximum < 1:
            raise ValueError("Image too small for WOW")
        scales = maximum if n_scales in (None, 0) else min(int(n_scales), maximum)
        if scales < 1:
            raise ValueError("WOW scale count must be positive or automatic")
        levels = [] if denoise_coefficients is None else list(denoise_coefficients)
        if not np.isfinite(levels).all() or any(x < 0 for x in levels):
            raise ValueError("Noise significance levels must be nonnegative")
        levels = levels[:scales]
        if noise is not None:
            noise = np.asarray(noise, dtype=float)
            if noise.shape != a.shape or not np.isfinite(noise).all() or (noise < 0).any():
                raise ValueError("WOW noise map must match image and be finite and nonnegative")
        # A constant image has no detail to whiten; avoid a huge coarse DC term.
        if np.ptp(a) == 0:
            filtered = np.zeros_like(a)
        else:
            filtered, _ = utils.wow(
                a, scaling_function=B3spline, n_scales=scales, weights=[],
                whitening=True, denoise_coefficients=levels, noise=noise,
                bilateral=bilateral, bilateral_scaling=False,
                soft_threshold=True, preserve_variance=False, h=0,
            )
        if not np.isfinite(filtered).all():
            raise ValueError("WOW produced nonfinite output")
        return blend_filter_result(image, filtered, strength)

    def run_usm(
        self, img: np.ndarray, strength: float, radius_param: float, sigma_param: float
    ) -> np.ndarray:
        if strength == 0:
            return img.copy()
        try:
            radius = max(0.5, float(radius_param / 10.0))
            sigma = max(0.1, float(sigma_param))

            blurred = gaussian_filter(img, sigma=radius)
            high_pass = img - blurred
            sharpened = np.clip(img + high_pass * sigma, np.min(img), np.max(img))

            alpha = strength / 100.0
            return cv2.addWeighted(sharpened.astype(np.float32), alpha, img, 1.0 - alpha, 0)
        except Exception as e:
            print(f"Error in USM: {e}")
            return img.copy()

    def run_achf(
        self, img, strength, base_kernel_param, boost_param,
        sun_x, sun_y, sun_r, intensity_threshold=10.0, background=10.0,
    ) -> np.ndarray:
        """Adaptive symmetric circular filter; UI threshold/background are percent.

        Radius is in tenths of pixels; gain is in tenths. Strength is an
        external blend and is not part of the paper's variable-kernel operator.
        """
        if strength == 0:
            return img.copy()
        a = np.asarray(img, dtype=np.float32)
        yy, xx = np.ogrid[:a.shape[0], :a.shape[1]]
        regions = ((xx-float(sun_x))**2 + (yy-float(sun_y))**2 <= float(sun_r)**2)
        threshold = float(intensity_threshold)/100.0 * float(np.ptp(a))
        filtered = adaptive_circular_highpass(
            a, float(base_kernel_param)/10.0, threshold,
            gain=float(boost_param)/10.0, background=float(background)/100.0,
            regions=regions,
        )
        alpha = float(strength)/100.0
        return ((1-alpha)*a + alpha*filtered).astype(np.float32)
