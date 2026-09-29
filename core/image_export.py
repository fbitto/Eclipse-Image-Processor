"""Export processed images to disk."""

from typing import Optional
import numpy as np
import tifffile
from config import CPU_CORES


def export_image_as_tiff(
    image: np.ndarray,
    file_path: str,
    metadata: Optional[dict] = None,
    compression: str = "zlib",
) -> bool:
    """
    Export image as 16-bit TIFF with optional metadata.
    
    Args:
        image: Image array (will be normalized to 0-65535 range)
        file_path: Output file path
        metadata: Optional metadata dictionary
        compression: Compression method ('zlib', 'lzw', etc.)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Ensure float32
        img_clean = np.nan_to_num(image, nan=0.0).astype(np.float32)
        i_min, i_max = float(np.min(img_clean)), float(np.max(img_clean))

        # Normalize to 0-1 range
        if i_max - i_min > 1e-6:
            img_norm = (img_clean - i_min) / (i_max - i_min)
        else:
            img_norm = np.zeros_like(img_clean)

        # Convert to 16-bit unsigned integer
        img_16bit = np.clip(img_norm * 65535.0, 0, 65535).astype(np.uint16)

        # Write TIFF
        tifffile.imwrite(
            file_path,
            img_16bit,
            compression=compression,
            maxworkers=CPU_CORES,
            metadata=metadata,
        )
        return True

    except Exception as e:
        print(f"Error exporting image: {e}")
        return False
