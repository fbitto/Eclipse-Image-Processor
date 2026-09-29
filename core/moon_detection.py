"""Lunar disk detection using Hough Circle Transform."""

from typing import Tuple
import numpy as np
import cv2


def detect_lunar_limb(raw_img: np.ndarray) -> Tuple[int, int, int]:
    """
    Auto-detect lunar disk center and radius using Hough Circle Transform.
    
    Args:
        raw_img: Input image (can be 2D or 3D)
        
    Returns:
        Tuple of (center_x, center_y, radius)
    """
    if raw_img is None:
        return 0, 0, 100

    # Convert to grayscale if needed
    if raw_img.ndim == 3:
        if raw_img.shape[2] in (3, 4):
            img_gray = 0.299 * raw_img[:, :, 0] + 0.587 * raw_img[:, :, 1] + 0.114 * raw_img[:, :, 2]
        elif raw_img.shape[0] in (3, 4):
            img_gray = 0.299 * raw_img[0, :, :] + 0.587 * raw_img[1, :, :] + 0.114 * raw_img[2, :, :]
        else:
            img_gray = raw_img[:, :, 0]
    else:
        img_gray = raw_img

    h, w = img_gray.shape
    clean_img = np.nan_to_num(img_gray, nan=0.0)
    norm = cv2.normalize(clean_img, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)

    # Downscale for faster processing
    scale = 800.0 / max(h, w)
    sw, sh = int(w * scale), int(h * scale)
    small = cv2.resize(norm, (sw, sh), interpolation=cv2.INTER_AREA)
    filtered = cv2.bilateralFilter(small, 9, 75, 75)

    # Hough Circle Transform
    circles = cv2.HoughCircles(
        filtered,
        cv2.HOUGH_GRADIENT,
        dp=1.2,
        minDist=min(sw, sh) // 4,
        param1=100,
        param2=30,
        minRadius=int(min(sw, sh) * 0.04),
        maxRadius=int(min(sw, sh) * 0.48),
    )

    best_candidate = None
    if circles is not None:
        circles = np.round(circles[0, :]).astype(int)
        best_contrast = -1.0
        for cx, cy, r in circles:
            if cx - r < 0 or cx + r >= sw or cy - r < 0 or cy + r >= sh:
                continue
            mask_in = np.zeros((sh, sw), dtype=np.uint8)
            mask_out = np.zeros((sh, sw), dtype=np.uint8)
            cv2.circle(mask_in, (cx, cy), int(r * 0.8), 255, -1)
            cv2.circle(mask_out, (cx, cy), int(r * 1.25), 255, -1)
            cv2.circle(mask_out, (cx, cy), int(r * 1.05), 0, -1)

            contrast = cv2.mean(small, mask=mask_out)[0] - cv2.mean(small, mask=mask_in)[0]
            if contrast > best_contrast and contrast > 5:
                best_contrast = contrast
                best_candidate = (int(cx / scale), int(cy / scale), int(r / scale))

    if best_candidate is None:
        return w // 2, h // 2, min(w, h) // 4

    # Refine detection using edge detection
    init_cx, init_cy, init_r = best_candidate
    r_search = int(init_r * 0.15)
    radii = np.arange(max(10, init_r - r_search), min(min(w, h) // 2, init_r + r_search))
    angles = np.linspace(0, 2 * np.pi, 72, endpoint=False)

    edge_pts = []
    for ang in angles:
        xs = np.clip((init_cx + radii * np.cos(ang)).astype(int), 0, w - 1)
        ys = np.clip((init_cy + radii * np.sin(ang)).astype(int), 0, h - 1)
        profile = norm[ys, xs].astype(float)
        grad = np.diff(profile)
        if len(grad) > 0 and grad.max() > 5:
            best_r = radii[np.argmax(grad)]
            edge_pts.append((init_cx + best_r * np.cos(ang), init_cy + best_r * np.sin(ang)))

    if len(edge_pts) >= 12:
        pts = np.array(edge_pts)
        x_pts, y_pts = pts[:, 0], pts[:, 1]
        A = np.column_stack([x_pts, y_pts, np.ones_like(x_pts)])
        B = -(x_pts**2 + y_pts**2)
        try:
            sol, _, _, _ = np.linalg.lstsq(A, B, rcond=None)
            final_cx, final_cy = -sol[0] / 2.0, -sol[1] / 2.0
            final_r = np.sqrt(max(1.0, final_cx**2 + final_cy**2 - sol[2]))
            if abs(final_cx - init_cx) < init_r * 0.2 and abs(final_cy - init_cy) < init_r * 0.2:
                return int(round(final_cx)), int(round(final_cy)), int(round(final_r))
        except Exception:
            pass

    return init_cx, init_cy, init_r
