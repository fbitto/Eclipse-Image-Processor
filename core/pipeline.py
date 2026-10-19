"""Single synchronous filter pipeline, shared by Qt preview and export."""
import time
from .cancellation import check_cancelled
from copy import deepcopy
import numpy as np


def prepare_parameters(parameters, full_shape, preview_shape, target_shape):
    """Geometry is supplied in full-res pixels; spatial controls in preview pixels.

    Scale X/Y independently using OpenCV's pixel-centre convention. Circular
    radii and kernels use the geometric mean scale for rounded aspect ratios.
    FNRGF ring widths are target-image pixels, independent of preview resizing.
    """
    shapes = (full_shape, preview_shape, target_shape)
    if any(len(shape) != 2 or not np.isfinite(shape).all() or min(shape) <= 0 for shape in shapes):
        raise ValueError("Resolution shapes must contain two positive finite dimensions")
    p = deepcopy(parameters)
    sy, sx = target_shape[0] / full_shape[0], target_shape[1] / full_shape[1]
    p["sx"] = (p["sx"] + .5) * sx - .5
    p["sy"] = (p["sy"] + .5) * sy - .5
    p["sr"] *= float(np.sqrt(sx * sy))
    scale = float(np.sqrt(target_shape[0] / preview_shape[0] * target_shape[1] / preview_shape[1]))
    p["spatial_scale"] = scale
    for key in ("bilateral_d", "usm_radius", "achf_kernel", "rhef_bin_px",
                "fnrgf_smooth", "fnrgf_fade", "tangential_fade", "statistics_guard_px"):
        if key in p:
            # Apply pixel floors before resizing, preserving the preview footprint.
            value = max(5.0, p[key]) if key in ("bilateral_d", "usm_radius") else p[key]
            p[key] = value * scale
    if "fnrgf_bin_px" in p:
        from utils.helpers import recommended_radial_bins
        p["fnrgf_nbins"] = recommended_radial_bins(
            p.get("fnrgf_rad", 10) / 10.0 * p["sr"],
            p.get("fnrgf_rmax", 30) / 10.0 * p["sr"],
            logarithmic=p.get("fnrgf_radial_binning", "linear") == "log",
            width_px=p["fnrgf_bin_px"],
        )
    elif "fnrgf_nbins" in p:
        # Compatibility with callers supplying the former preview-count control.
        p["fnrgf_nbins"] = max(1, int(round(p["fnrgf_nbins"] * scale)))
    if "wow_scales" in p or p.get("wow_enabled", False):
        # Starlet supports are dyadic: choose the nearest available footprint.
        reference_shape = full_shape if p.get('wow_native_scales', False) else preview_shape
        preview_max = max(1, int(np.round(np.log2(min(reference_shape) / 5.0))))
        target_max = max(1, int(np.round(np.log2(min(target_shape) / 5.0))))
        requested = p.get("wow_scales")
        count = preview_max if requested in (None, 0) else min(int(requested), preview_max)
        wavelet_scale = float(np.sqrt(target_shape[0]/reference_shape[0]*target_shape[1]/reference_shape[1]))
        offset = int(np.floor(np.log2(wavelet_scale) + 0.5))
        p["wow_scales"] = int(np.clip(count + offset, 1, target_max))
        levels = list(p.get("wow_denoise", []))
        if levels:
            # Keep thresholds attached to the same physical bands. Newly added
            # fine bands inherit the finest threshold instead of disabling noise control.
            levels = [levels[0]] * offset + levels if offset >= 0 else levels[-offset:]
            p["wow_denoise"] = levels[:p["wow_scales"]]
    p["mgn_sigmas"] = tuple(s * scale for s in p.get("mgn_sigmas", (1.25, 2.5, 5, 10, 20, 40)))
    return p


def execute_pipeline(worker, raw_image, params):
    from .filters import finite_image, CPU_CORES
    check_cancelled()
    if raw_image is None:
        raise ValueError("No image supplied")

    pipeline_start = time.time()
    print(f"\n{'='*80}\n[PIPELINE] Execution start (Native Engine - {CPU_CORES} CPUs) - Shape: {raw_image.shape}\n{'='*80}")

    p = params
    valid = p.get("valid_mask")
    if valid is not None:
        from .image_data import observed_image
        observed, valid = observed_image(raw_image, valid)
        # Zero is only a finite transport buffer. MaskedWorker excludes these
        # positions from statistics/support; restore NaN before returning data.
        img = np.where(valid, observed, 0).astype(np.float32)
        if not valid.all():
            from .masked_filters import MaskedWorker
            worker = MaskedWorker(worker, valid)
    else:
        img = finite_image(raw_image).astype(np.float32)

    if p.get('statistics_exclude_lunar', False) or p.get('statistics_exclude_bright', False) or p.get('statistics_mask') is not None:
        from .statistics_support import statistics_support, StatisticsWorker
        support = statistics_support(raw_image, p, valid) if p.get('statistics_mask') is None else np.asarray(p['statistics_mask'], dtype=bool) & np.isfinite(raw_image) & (valid if valid is not None else True)
        if support.shape != raw_image.shape or not support.any():
            raise ValueError('Statistics mask must match image and contain observations')
        from .masked_filters import MaskedWorker
        base_worker = worker.worker if isinstance(worker, MaskedWorker) else worker
        worker = StatisticsWorker(base_worker, support)

    check_cancelled()
    # STEP 0: PRE-STRETCH (ASINH / LOGARITHMIC)
    if p.get("pre_stretch_enabled", False):
        mode = p.get("pre_stretch_mode", "asinh")
        val = p.get("pre_stretch_val", 10.0)
        step_start = time.time()
        if mode == "log":
            img = worker.run_pre_log(img, val)
            print(f"[PRE-STRETCH: LOG] Done in {time.time() - step_start:.3f}s (K=10^{val:.1f})")
        else:
            img = worker.run_pre_asinh(img, val)
            print(f"[PRE-STRETCH: ASINH] Done in {time.time() - step_start:.3f}s (Factor={val})")

    check_cancelled()
    # STEP 0B: RADIAL NOISE GATE
    if p.get("noise_gate_enabled", False):
        step_start = time.time()
        img = worker.run_radial_noise_gate(
            img, p["noise_gate_str"], p["noise_gate_thr"], p["sx"], p["sy"], p["sr"], spatial_scale=p.get("spatial_scale", 1.0),
            local_sigma=p.get('noise_gate_sigma', 3.), gate_sigma=p.get('noise_gate_smooth', 2.)
        )
        print(f"[NOISE GATE] Done in {time.time() - step_start:.3f}s")

    check_cancelled()
    # STEP 0C: BILATERAL DENOISE
    if p.get("bilateral_enabled", False):
        step_start = time.time()
        img = worker.run_bilateral_denoise(
            img, p["bilateral_str"], p["bilateral_d"], p["bilateral_sc"], p["bilateral_ss"]
        )
        print(f"[BILATERAL] Done in {time.time() - step_start:.3f}s")

    check_cancelled()
    # STEP 1A: NATIVE FNRGF ENGINE (MULTI-THREADED)
    if p.get("fnrgf_enabled", False):
        step_start = time.time()
        img = worker.run_fnrgf_native(
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
            mode=p.get('fnrgf_mode', 'legacy'), radial_smooth=p.get('fnrgf_smooth', 8.), boundary_fade=p.get('fnrgf_fade', 0.),
            ridge=p.get('fnrgf_ridge', .01), width_floor=p.get('fnrgf_floor', .05),
            robust_iterations=p.get('fnrgf_robust', 2), min_pixels_per_sector=p.get('fnrgf_min_pixels', 1),
            mean_attenuation_range=(1., p.get('fnrgf_mean_tail', 0.)),
            std_attenuation_range=(1., p.get('fnrgf_width_tail', 0.)),
        )
        print(f"[FNRGF NATIVE] Done in {time.time() - step_start:.3f}s")

    check_cancelled()
    # STEP 2A: NATIVE MGN ENGINE (MULTI-SCALE GAUSSIAN NORMALIZATION)
    if p.get("mgn_enabled", False):
        step_start = time.time()
        img = worker.run_mgn_native(
            img,
            p["mgn_str"],
            p["mgn_gam"],
            p.get("mgn_k", 70),
            p.get("mgn_h", 70),
            p.get("mgn_trunc", 3),
            sigmas=p.get("mgn_sigmas", (1.25, 2.5, 5, 10, 20, 40)),
            weights=p.get('mgn_weights'),
        )
        print(f"[MGN NATIVE] Done in {time.time() - step_start:.3f}s")

    check_cancelled()
    # STEP 2B: NATIVE WOW ENGINE (A TROUS WAVELETS WHITENING)
    if p.get("wow_enabled", False):
        step_start = time.time()
        img = worker.run_wow_native(
            img, p["wow_str"], p.get("wow_scales"),
            denoise_coefficients=p.get("wow_denoise", []),
            bilateral=p.get("wow_bilateral"),
        )
        print(f"[WOW NATIVE] Done in {time.time() - step_start:.3f}s")

    check_cancelled()
    # STEP 2C: NATIVE RHEF ENGINE
    if p.get("rhef_enabled", False):
        step_start = time.time()
        img = worker.run_rhef_native(
            img, p["rhef_str"], p["rhef_rad"], p["rhef_upsilon"], p["sx"], p["sy"], p["sr"],
            bin_px=p.get("rhef_bin_px", 1.0),
            mode=p.get("rhef_mode", "legacy"), upsilon_h_val=p.get('rhef_upsilon_high'),
            min_count=p.get('rhef_min_count', 12), quantile_count=p.get('rhef_quantiles', 257),
            noise_confidence=p.get('rhef_noise_confidence', 0.),
        )
        print(f"[RHEF NATIVE] Done in {time.time() - step_start:.3f}s")

    check_cancelled()
    # STEP 3: UNSHARP MASK
    # Compatibility for older API recipes; the UI exposes tangential detail.
    if p.get("usm_enabled", False):
        step_start = time.time()
        img = worker.run_usm(img, p["usm_str"], p["usm_radius"], p["usm_sigma"])
        print(f"[USM] Done in {time.time() - step_start:.3f}s")

    check_cancelled()
    if p.get('tangential_enabled', False):
        img = worker.run_tangential(
            img, p['tangential_str'], p['sx'], p['sy'], p['sr'],
            arc_sigma=p.get('tangential_arc', 3.), gain=p.get('tangential_gain', 1.),
            denoise=p.get('tangential_denoise', 0.), inner_radius=p.get('tangential_inner', 1.),
            outer_radius=p.get('tangential_outer', 0.), fade_px=p.get('tangential_fade', 8.))

    check_cancelled()
    # STEP 4: ACHF (SYMMETRIC VARIABLE KERNEL)
    if p.get("achf_enabled", False):
        step_start = time.time()
        img = worker.run_achf(
            img, p["achf_str"], p["achf_kernel"], p["achf_boost"], p["sx"], p["sy"], p["sr"],
            intensity_threshold=p.get("achf_threshold", 10),
            background=p.get("achf_background", 10),
            spatial_scale=p.get("spatial_scale", 1.0),
        )
        print(f"[ACHF] Done in {time.time() - step_start:.3f}s")

    check_cancelled()
    finite_image(img)
    print(f"[PIPELINE] Complete. Total time: {time.time() - pipeline_start:.3f}s\n{'='*80}\n")
    if valid is not None and not valid.all():
        img = np.where(valid, img, np.nan).astype(np.float32)
    return img

