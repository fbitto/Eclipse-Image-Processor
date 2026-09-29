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

CPU_CORES = os.cpu_count() or 4


class FilterWorker(QObject):
    """Executes coronal enhancement filters with multi-threaded native C/NumPy engines."""

    finished = Signal(np.ndarray)

    @Slot(np.ndarray, dict)
    def process_pipeline(self, raw_image: np.ndarray, params: dict):
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

        # STEP 1B: NATIVE RHEF ENGINE
        if p.get("rhef_enabled", False):
            step_start = time.time()
            img = self.run_rhef_native(
                img, p["rhef_str"], p["rhef_rad"], p["rhef_upsilon"], p["sx"], p["sy"], p["sr"]
            )
            print(f"[RHEF NATIVE] Done in {time.time() - step_start:.3f}s")

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
                img, p["wow_str"], p["wow_scales"], p["wow_gam"], p["wow_h"]
            )
            print(f"[WOW NATIVE] Done in {time.time() - step_start:.3f}s")

        # STEP 3: UNSHARP MASK
        if p.get("usm_enabled", False):
            step_start = time.time()
            img = self.run_usm(img, p["usm_str"], p["usm_radius"], p["usm_sigma"])
            print(f"[USM] Done in {time.time() - step_start:.3f}s")

        # STEP 4: ACHF (PARALLELIZED MULTI-SCALE KERNELS)
        if p.get("achf_enabled", False):
            step_start = time.time()
            img = self.run_achf(
                img, p["achf_str"], p["achf_kernel"], p["achf_boost"], p["sx"], p["sy"], p["sr"]
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
        self,
        img: np.ndarray,
        strength: float,
        order_fourier: int,
        angular_segments: int,
        cutoff_val: float,
        app_radius_val: float,
        rmax_val: float,
        nbins_val: int,
        sun_x: float,
        sun_y: float,
        sun_r: float,
        width_function: str = "std",
        radial_binning: str = "linear",
        apply_mask: float = 0,
    ) -> np.ndarray:
        """Fast Normalizing Radial Gradient Filter (Native Parallel Implementation)."""
        if strength == 0:
            return img.copy()
        try:
            ord_val = max(1, int(order_fourier))
            seg_val = max(4, int(angular_segments))
            r_outer = max(1.1, float(rmax_val / 10.0))
            num_bins = max(10, int(nbins_val))

            h, w = img.shape[:2]
            cx, cy = float(sun_x), float(sun_y)
            r0 = float(sun_r if sun_r > 5 else 100.0)

            y_indices, x_indices = np.indices((h, w), dtype=np.float32)
            dx = x_indices - cx
            dy = y_indices - cy
            r_map = np.hypot(dx, dy) / (r0 + 1e-5)
            theta_map = (np.arctan2(dy, dx) + 2.0 * np.pi) % (2.0 * np.pi)

            if radial_binning == "log":
                bin_edges = np.logspace(np.log10(1.0), np.log10(r_outer), num_bins + 1)
            else:
                bin_edges = np.linspace(1.0, r_outer, num_bins + 1)

            app_r = float(app_radius_val / 10.0)
            sector_width = 2.0 * np.pi / seg_val
            sector_indices = np.clip((theta_map / sector_width).astype(np.int32), 0, seg_val - 1)

            sector_centers = (np.arange(seg_val) + 0.5) * sector_width
            cos_matrix = np.cos(np.outer(np.arange(1, ord_val + 1), sector_centers))
            sin_matrix = np.sin(np.outer(np.arange(1, ord_val + 1), sector_centers))

            damping = np.ones(ord_val, dtype=np.float32)
            if cutoff_val > 0:
                damping = np.exp(-0.5 * (np.arange(1, ord_val + 1) / float(cutoff_val)) ** 2)

            background_map = np.zeros((h, w), dtype=np.float32)
            width_map = np.ones((h, w), dtype=np.float32)

            def compute_radial_bin(b: int):
                r_low, r_high = bin_edges[b], bin_edges[b + 1]
                bin_mask = (r_map >= r_low) & (r_map < r_high)
                if not np.any(bin_mask):
                    return None

                sector_means = np.zeros(seg_val, dtype=np.float32)
                sector_widths = np.zeros(seg_val, dtype=np.float32)

                for s in range(seg_val):
                    cell_mask = bin_mask & (sector_indices == s)
                    cell_pixels = img[cell_mask]
                    if cell_pixels.size > 0:
                        if width_function == "mad":
                            med = float(np.nanmedian(cell_pixels))
                            mad = float(np.nanmedian(np.abs(cell_pixels - med))) * 1.4826
                            sector_means[s] = med
                            sector_widths[s] = mad if mad > 1e-6 else (float(np.nanstd(cell_pixels)) + 1e-5)
                        else:
                            sector_means[s] = float(np.nanmean(cell_pixels))
                            sector_widths[s] = float(np.nanstd(cell_pixels)) + 1e-5
                    else:
                        sector_widths[s] = 1.0

                a0 = float(np.mean(sector_means))
                w0 = float(np.mean(sector_widths))

                ak = (2.0 / seg_val) * np.dot(cos_matrix, sector_means) * damping
                bk = (2.0 / seg_val) * np.dot(sin_matrix, sector_means) * damping

                angles_in_bin = theta_map[bin_mask]
                harmonic_sum = np.zeros_like(angles_in_bin)
                for k in range(ord_val):
                    harmonic_sum += ak[k] * np.cos((k + 1) * angles_in_bin) + bk[k] * np.sin((k + 1) * angles_in_bin)

                return bin_mask, a0 + harmonic_sum, max(w0, 1e-5)

            with ThreadPoolExecutor(max_workers=CPU_CORES) as executor:
                results = list(executor.map(compute_radial_bin, range(num_bins)))

            for res in results:
                if res is not None:
                    b_mask, bg_vals, w_val = res
                    background_map[b_mask] = bg_vals
                    width_map[b_mask] = w_val

            background_smooth = gaussian_filter(background_map, sigma=1.5)
            width_smooth = gaussian_filter(width_map, sigma=1.5)

            normalized = (img - background_smooth) / (width_smooth + 1e-5)
            transition = np.clip((r_map - 1.0) / max(0.1, app_r - 1.0), 0.0, 1.0)
            envelope = 0.5 * (1.0 - np.cos(np.pi * transition))
            filtered_matrix = img * (1.0 - envelope) + normalized * envelope

            if apply_mask > 0:
                mask_strength = apply_mask / 100.0
                r_normalized = (r_map - 0.95) / 0.08
                limb_mask = 0.5 * (1.0 - np.cos(np.pi * np.clip(r_normalized, 0.0, 1.0)))
                filtered_matrix = (
                    filtered_matrix * (1.0 - mask_strength * limb_mask)
                    + filtered_matrix * mask_strength * limb_mask
                )

            min_orig, max_orig = float(np.min(img)), float(np.max(img))
            f_min, f_max = float(np.min(filtered_matrix)), float(np.max(filtered_matrix))
            if f_max - f_min > 1e-6:
                filtered_matrix = (
                    (filtered_matrix - f_min) / (f_max - f_min) * (max_orig - min_orig) + min_orig
                )

            alpha = strength / 100.0
            return cv2.addWeighted(filtered_matrix.astype(np.float32), alpha, img, 1.0 - alpha, 0)
        except Exception as e:
            print(f"Error in FNRGF: {e}")
            return img.copy()

    def run_rhef_native(
        self, img: np.ndarray, strength: float, app_radius_val: float, upsilon_val: float, sun_x: float, sun_y: float, sun_r: float
    ) -> np.ndarray:
        """Radial Histogram Equalization Filter (Native Implementation)."""
        if strength == 0:
            return img.copy()
        try:
            h, w = img.shape[:2]
            cx, cy = float(sun_x), float(sun_y)
            app_r = float(app_radius_val / 10.0) * float(sun_r if sun_r > 5 else 100.0)

            y_indices, x_indices = np.indices((h, w), dtype=np.float32)
            r_map = np.hypot(x_indices - cx, y_indices - cy)

            max_r = int(np.max(r_map)) + 1
            r_int = np.clip(np.round(r_map).astype(np.int32), 0, max_r - 1)

            r_counts = np.bincount(r_int.ravel(), minlength=max_r)
            r_sums = np.bincount(r_int.ravel(), weights=img.ravel(), minlength=max_r)

            valid = r_counts > 0
            mean_profile = np.zeros(max_r, dtype=np.float32)
            mean_profile[valid] = r_sums[valid] / r_counts[valid]

            smooth_sigma = max(2, max_r // 50)
            smooth_mean = gaussian_filter1d(mean_profile, sigma=smooth_sigma)
            mean_2d = smooth_mean[r_int]

            sq_diff = (img - mean_2d) ** 2
            sq_sums = np.bincount(r_int.ravel(), weights=sq_diff.ravel(), minlength=max_r)
            std_profile = np.zeros(max_r, dtype=np.float32)
            std_profile[valid] = np.sqrt(sq_sums[valid] / np.maximum(r_counts[valid] - 1, 1))

            smooth_std = gaussian_filter1d(std_profile, sigma=smooth_sigma) + 1e-5
            std_2d = smooth_std[r_int]

            upsilon = max(0.1, float(upsilon_val / 100.0))
            normalized = (img - mean_2d) / (std_2d**upsilon)

            transition_width = 15.0
            r_inner, r_outer = app_r, app_r + transition_width
            transition = np.clip((r_map - r_inner) / (r_outer - r_inner + 1e-5), 0.0, 1.0)
            mask = 0.5 * (1.0 - np.cos(np.pi * transition))

            masked_norm = normalized * mask + ((img - mean_2d) / std_2d) * (1.0 - mask)
            min_orig, max_orig = np.min(img), np.max(img)
            n_min, n_max = np.min(masked_norm), np.max(masked_norm)

            if n_max - n_min <= 1e-6:
                return img.copy()

            scaled_norm = (masked_norm - n_min) / (n_max - n_min + 1e-5) * (max_orig - min_orig) + min_orig
            alpha = strength / 100.0
            return cv2.addWeighted(scaled_norm.astype(np.float32), alpha, img, 1.0 - alpha, 0)
        except Exception as e:
            print(f"Error in RHEF: {e}")
            return img.copy()

    def run_mgn_native(
        self, img: np.ndarray, strength: float, gamma_val: float, k_val: float, h_val: float, trunc_val: float
    ) -> np.ndarray:
        """Multi-Scale Gaussian Normalization (Morgan & Druckmüller 2014 - Native Multi-Core)."""
        if strength == 0:
            return img.copy()
        try:
            gamma_param = 0.5 + (gamma_val / 100.0) * 9.5
            k_param = 0.1 + (k_val / 100.0) * 1.9
            h_param = 0.1 + (h_val / 100.0) * 0.9
            trunc_param = max(3, int(trunc_val))

            sigma_scales = [1.25 * (2.0 ** i) for i in range(6)]

            def compute_mgn_scale(sigma: float):
                mu = gaussian_filter(img, sigma=sigma, truncate=trunc_param)
                mu2 = gaussian_filter(img ** 2, sigma=sigma, truncate=trunc_param)
                variance = np.maximum(0.0, mu2 - mu ** 2)
                sigma_local = np.sqrt(variance + 1e-6)
                norm_diff = (img - mu) / sigma_local
                return np.arctan(k_param * norm_diff)

            with ThreadPoolExecutor(max_workers=min(6, CPU_CORES)) as executor:
                scale_results = list(executor.map(compute_mgn_scale, sigma_scales))

            c_prime = np.mean(scale_results, axis=0)

            c_prime_min, c_prime_max = float(np.min(c_prime)), float(np.max(c_prime))
            c_prime_norm = (c_prime - c_prime_min) / max(1e-6, c_prime_max - c_prime_min)
            c_gamma = c_prime_norm ** (1.0 / max(0.1, gamma_param))

            img_clean = np.nan_to_num(img, nan=0.0)
            i_min, i_max = float(np.min(img_clean)), float(np.max(img_clean))
            g_global = (img_clean - i_min) / max(1e-6, i_max - i_min)
            filtered_matrix = (1.0 - h_param) * c_gamma + h_param * g_global

            min_orig, max_orig = float(np.min(img)), float(np.max(img))
            f_min, f_max = float(np.min(filtered_matrix)), float(np.max(filtered_matrix))
            if f_max - f_min > 1e-6:
                filtered_matrix = (
                    (filtered_matrix - f_min) / (f_max - f_min) * (max_orig - min_orig) + min_orig
                )

            alpha = strength / 100.0
            return cv2.addWeighted(filtered_matrix.astype(np.float32), alpha, img, 1.0 - alpha, 0)
        except Exception as e:
            print(f"Error in MGN: {e}")
            return img.copy()

    def run_wow_native(
        self, img: np.ndarray, strength: float, n_scales_val: int, gamma_val: float, h_val: float
    ) -> np.ndarray:
        """Wavelets Optimized Whitening (WOW - Solar Coronal Multiscale Engine)."""
        if strength == 0:
            return img.copy()

        try:
            h, w = img.shape[:2]
            n_scales = int(np.clip(n_scales_val, 2, 8))
            gamma_param = max(0.5, float(gamma_val / 10.0))
            h_weight = float(h_val / 100.0)

            current = img.astype(np.float32)
            wavelet_details = []

            for s in range(n_scales):
                sigma_s = float(1.5 * (2.0 ** s))
                smoothed = gaussian_filter(current, sigma=sigma_s, mode="reflect")
                detail = current - smoothed
                wavelet_details.append(detail)
                current = smoothed

            enhanced_details = np.zeros_like(img, dtype=np.float32)

            for s, detail in enumerate(wavelet_details):
                scale_sigma = float(1.5 * (2.0 ** s))
                local_var = gaussian_filter(detail ** 2, sigma=scale_sigma * 2.0, mode="reflect")
                local_rms = np.sqrt(np.maximum(1e-8, local_var))
                whitened = detail / (local_rms + 1e-5)
                compressed = np.arctan(whitened * 1.5) * (local_rms ** (1.0 / gamma_param))
                enhanced_details += compressed

            detail_gain = (1.0 - 0.5 * h_weight) * 1.5
            reconstructed = img + enhanced_details * detail_gain

            p_low, p_high = float(np.percentile(reconstructed, 0.05)), float(np.percentile(reconstructed, 99.95))
            if p_high - p_low > 1e-6:
                norm_reconstructed = np.clip((reconstructed - p_low) / (p_high - p_low), 0.0, 1.0)
                min_orig, max_orig = float(np.min(img)), float(np.max(img))
                filtered_matrix = norm_reconstructed * (max_orig - min_orig) + min_orig
            else:
                filtered_matrix = img.copy()

            alpha = strength / 100.0
            return cv2.addWeighted(filtered_matrix.astype(np.float32), alpha, img, 1.0 - alpha, 0)

        except Exception as e:
            print(f"Error in WOW: {e}")
            return img.copy()

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
        self,
        img: np.ndarray,
        strength: float,
        base_kernel_param: float,
        boost_param: float,
        sun_x: float,
        sun_y: float,
        sun_r: float,
    ) -> np.ndarray:
        """ACHF with 3 multi-scale Gaussian filters executed in parallel across CPU threads."""
        if strength == 0:
            return img.copy()
        try:
            h, w = img.shape[:2]
            cx, cy = float(sun_x), float(sun_y)
            r0 = float(sun_r if sun_r > 5 else 100.0)

            y_indices, x_indices = np.indices((h, w), dtype=np.float32)
            r_map = np.hypot(x_indices - cx, y_indices - cy) / (r0 + 1e-5)

            base_sigma = max(0.5, float(base_kernel_param / 10.0))

            with ThreadPoolExecutor(max_workers=3) as executor:
                f_fine = executor.submit(gaussian_filter, img, base_sigma)
                f_med = executor.submit(gaussian_filter, img, base_sigma * 2.0)
                f_broad = executor.submit(gaussian_filter, img, base_sigma * 4.0)

                low_fine = f_fine.result()
                low_medium = f_med.result()
                low_broad = f_broad.result()

            w_fine = np.clip(1.8 - r_map, 0.0, 1.0)
            w_broad = np.clip((r_map - 1.5) / 1.5, 0.0, 1.0)
            w_medium = 1.0 - np.maximum(w_fine, w_broad)
            w_sum = w_fine + w_medium + w_broad + 1e-8

            low_adaptive = (
                low_fine * (w_fine / w_sum)
                + low_medium * (w_medium / w_sum)
                + low_broad * (w_broad / w_sum)
            )
            high_pass = img - low_adaptive
            boost = float(boost_param / 10.0)
            enhanced = img + high_pass * boost

            r_normalized = (r_map - 0.95) / 0.08
            lunar_mask = 0.5 * (1.0 - np.cos(np.pi * np.clip(r_normalized, 0.0, 1.0)))
            enhanced = img * (1.0 - lunar_mask) + enhanced * lunar_mask
            enhanced = np.clip(enhanced, np.min(img), np.max(img))

            alpha = strength / 100.0
            return cv2.addWeighted(enhanced.astype(np.float32), alpha, img, 1.0 - alpha, 0)
        except Exception as e:
            print(f"Error in ACHF: {e}")
            return img.copy()
