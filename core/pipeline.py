"""
Filter execution pipeline for Eclipse Processor.

Applies filters in sequence based on parameters.
Optimized for performance.
"""

import numpy as np
from typing import Dict, Any

# Import all filters - DO NOT instantiate here
from filters.pre_stretch import AsinhPreStretch
from filters.noise_gate import RadialNoiseGate
from filters.bilateral import EdgePreservingDenoise
from filters.fnrgf import FNRGF
from filters.rhef import RHEF
from filters.mgn import MGN
from filters.wow import WOW
from filters.usm import UnsharpMask
from filters.achf import ACHF


def execute_pipeline(image: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
    """
    Execute filter pipeline in sequence.
    
    Args:
        image: Input image (numpy array)
        params: Filter parameters dictionary
        
    Returns:
        Processed image
    """
    result = image.astype(np.float32)
    
    # 1. PRE-STRETCH
    if params.get("pre_stretch_enabled", False):
        factor = params.get("pre_stretch_factor", 10)
        filter_obj = AsinhPreStretch()
        result = filter_obj.apply(result, factor=factor)
    
    # 2. NOISE GATE
    if params.get("noise_gate_enabled", False):
        strength = params.get("noise_gate_strength", 0)
        threshold = params.get("noise_gate_threshold", 50)
        radius = params.get("noise_gate_radius", 10)
        filter_obj = RadialNoiseGate()
        result = filter_obj.apply(result, strength=strength, threshold=threshold, radius=radius)
    
    # 3. BILATERAL
    if params.get("bilateral_enabled", False):
        strength = params.get("bilateral_strength", 0)
        d = params.get("bilateral_d", 15)
        sigma_spatial = params.get("bilateral_sigma_spatial", 30)
        sigma_range = params.get("bilateral_sigma_range", 0.1)
        filter_obj = EdgePreservingDenoise()
        result = filter_obj.apply(result, strength=strength, d=d, 
                                sigma_spatial=sigma_spatial, sigma_range=sigma_range)
    
    # 4. FNRGF
    if params.get("fnrgf_enabled", False):
        strength = params.get("fnrgf_strength", 0)
        order = params.get("fnrgf_order", 6)
        segments = params.get("fnrgf_segments", 50)
        cutoff = params.get("fnrgf_cutoff", 0)
        radius = params.get("fnrgf_radius", 10)
        rmax = params.get("fnrgf_rmax", 30)
        nbins = params.get("fnrgf_nbins", 80)
        apply_mask = params.get("fnrgf_apply_mask", 0)
        width_function = params.get("fnrgf_width_function", "std")
        radial_binning = params.get("fnrgf_radial_binning", "linear")
        sun_x = params.get("fnrgf_sun_x", 0)
        sun_y = params.get("fnrgf_sun_y", 0)
        sun_r = params.get("fnrgf_sun_r", 100)
        
        filter_obj = FNRGF()
        result = filter_obj.apply(
            result,
            strength=strength,
            order=order,
            segments=segments,
            cutoff=cutoff,
            radius=radius,
            rmax=rmax,
            nbins=nbins,
            sun_x=sun_x,
            sun_y=sun_y,
            sun_r=sun_r,
            width_function=width_function,
            radial_binning=radial_binning,
            apply_mask=apply_mask
        )
    
    # 5. RHEF
    if params.get("rhef_enabled", False):
        strength = params.get("rhef_strength", 0)
        radius = params.get("rhef_radius", 10)
        upsilon = params.get("rhef_upsilon", 1.0)
        sun_x = params.get("rhef_sun_x", 0)
        sun_y = params.get("rhef_sun_y", 0)
        sun_r = params.get("rhef_sun_r", 100)
        
        filter_obj = RHEF()
        result = filter_obj.apply(
            result,
            strength=strength,
            radius=radius,
            upsilon=upsilon,
            sun_x=sun_x,
            sun_y=sun_y,
            sun_r=sun_r
        )
    
    # 6. MGN
    if params.get("mgn_enabled", False):
        strength = params.get("mgn_strength", 0)
        gamma = params.get("mgn_gamma", 32)
        k = params.get("mgn_k", 70)
        h = params.get("mgn_h", 70)
        trunc = params.get("mgn_trunc", 3)
        
        filter_obj = MGN()
        result = filter_obj.apply(result, strength=strength, gamma=gamma, k=k, h=h, trunc=trunc)
    
    # 7. WOW
    if params.get("wow_enabled", False):
        strength = params.get("wow_strength", 0)
        n_scales = params.get("wow_n_scales", 6)
        gamma = params.get("wow_gamma", 32)
        h = params.get("wow_h", 20)
        
        filter_obj = WOW()
        result = filter_obj.apply(result, strength=strength, n_scales=n_scales, gamma=gamma, h=h)
    
    # 8. USM
    if params.get("usm_enabled", False):
        strength = params.get("usm_strength", 0)
        radius = params.get("usm_radius", 10)
        sigma = params.get("usm_sigma", 2.0)
        
        filter_obj = UnsharpMask()
        result = filter_obj.apply(result, strength=strength, radius=radius, sigma=sigma)
    
    # 9. ACHF
    if params.get("achf_enabled", False):
        strength = params.get("achf_strength", 0)
        kernel = params.get("achf_kernel", 20)
        boost = params.get("achf_boost", 20)
        
        filter_obj = ACHF()
        result = filter_obj.apply(result, strength=strength, kernel=kernel, boost=boost)
    
    return result
