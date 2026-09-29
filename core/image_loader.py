"""Image loading from various formats (TIFF, FITS, XISF, PNG, etc.)."""

from typing import Optional, Tuple
import numpy as np
import cv2
import tifffile


def load_image(file_path: str) -> Optional[np.ndarray]:
    """
    Load image from file in various formats (TIFF, FITS, XISF, PNG, JPG, BMP).
    
    Args:
        file_path: Path to the image file
        
    Returns:
        Image as float32 numpy array, or None if loading failed
    """
    try:
        img = None
        lower_path = file_path.lower()

        # Try XISF format
        if lower_path.endswith(".xisf"):
            try:
                import xisf
                xisf_file = xisf.XISF(file_path)
                img = xisf_file.read_image(0)
            except Exception as e:
                print(f"XISF reader warning: {e}")

        # Try FITS format
        if img is None and lower_path.endswith((".fits", ".fit", ".fts")):
            try:
                from astropy.io import fits
                with fits.open(file_path) as hdul:
                    for hdu in hdul:
                        if hdu.data is not None and isinstance(hdu.data, np.ndarray) and hdu.data.ndim >= 2:
                            img = np.squeeze(hdu.data)
                            break
            except Exception as e:
                print(f"FITS reader warning: {e}")

        # Try TIFF format
        if img is None:
            try:
                with tifffile.TiffFile(file_path) as tif:
                    img = tif.pages[0].asarray()
            except Exception:
                pass

        # Try OpenCV (supports PNG, JPG, BMP, etc.)
        if img is None:
            img = cv2.imread(file_path, cv2.IMREAD_UNCHANGED)

        # Fallback to PIL
        if img is None:
            from PIL import Image
            with Image.open(file_path) as pil_img:
                img = np.array(pil_img)

        if img is None:
            raise ValueError("Could not decode image with any available decoder.")

        # Convert to float32 and ensure grayscale
        if img.ndim == 3:
            if img.dtype != np.float32:
                img = img.astype(np.float32)
            if img.shape[2] in (3, 4):
                img = 0.299 * img[:, :, 0] + 0.587 * img[:, :, 1] + 0.114 * img[:, :, 2]
            elif img.shape[0] in (3, 4):
                img = 0.299 * img[0, :, :] + 0.587 * img[1, :, :] + 0.114 * img[2, :, :]
        elif img.ndim > 3:
            img = np.squeeze(img)

        if img.dtype != np.float32:
            img = img.astype(np.float32)

        return np.ascontiguousarray(img)

    except Exception as e:
        print(f"Error loading image: {e}")
        return None


def create_preview_image(full_image: np.ndarray, max_dimension: int = 1500) -> Tuple[np.ndarray, float]:
    """
    Create a downscaled preview image for faster processing.
    
    Args:
        full_image: Full resolution image
        max_dimension: Maximum dimension for preview
        
    Returns:
        Tuple of (preview_image, scale_factor)
    """
    h_full, w_full = full_image.shape[:2]

    if max(h_full, w_full) > max_dimension:
        scale = max_dimension / float(max(h_full, w_full))
        new_w, new_h = int(w_full * scale), int(h_full * scale)
        preview = cv2.resize(full_image, (new_w, new_h), interpolation=cv2.INTER_AREA)
        return preview, scale
    else:
        return full_image.copy(), 1.0
