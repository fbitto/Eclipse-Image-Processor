"""Optional unstretched source products for PixInsight; never infer linearity."""
import json
from pathlib import Path
import shutil
import tempfile

import numpy as np
import tifffile

from .image_data import observed_image


def split_source_channels(image):
    """Keep source RGB and derive the application's intensity plane in input units.

    Accept HWC/CHW RGB(A), mono and mono+alpha. Invalid RGB samples or zero alpha
    exclude the entire pixel. Coefficients preserve the existing mono pipeline;
    camera RGB is not claimed to be calibrated photometric luminance.
    """
    a = np.asarray(image)
    if a.ndim > 3:
        a = np.squeeze(a)
    rgb = None
    alpha = None
    if a.ndim == 3:
        if a.shape[-1] not in (2, 3, 4) and a.shape[0] in (2, 3, 4):
            a = np.moveaxis(a, 0, -1)
        if a.shape[-1] in (3, 4):
            rgb = np.asarray(a[..., :3], dtype=np.float32)
            valid = np.isfinite(rgb).all(axis=-1)
            mono = .299*rgb[..., 0] + .587*rgb[..., 1] + .114*rgb[..., 2]
            if a.shape[-1] == 4:
                alpha = a[..., 3]
        elif a.shape[-1] == 2:
            mono, alpha = a[..., 0], a[..., 1]
            valid = np.isfinite(mono)
        else:
            raise ValueError('Expected mono or RGB image channels')
    elif a.ndim == 2:
        mono = a
        valid = np.isfinite(mono)
    else:
        raise ValueError('Expected a 2D mono or 3D RGB image')
    if alpha is not None:
        valid &= np.isfinite(alpha) & (alpha > 0)
    mono, valid = observed_image(mono, valid)
    if rgb is not None:
        rgb = np.where(valid[..., None], rgb, np.nan).astype(np.float32)
    return mono.astype(np.float32), rgb


def export_linear_sources(mono, rgb, original_path, destination, input_state='unknown'):
    """Export original working units, no normalization/filter/stretch or inversion.

    LINEAR is used only for an explicitly declared linear input. An unknown or
    already stretched input is exported as INPUT, never relabelled as linear.
    """
    if input_state not in ('unknown', 'linear', 'nonlinear'):
        raise ValueError('Unknown input transfer state')
    mono, valid = observed_image(mono)
    destination = Path(destination)
    if destination.exists():
        raise FileExistsError(f'Source folder already exists: {destination}')
    destination.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.linear-', dir=destination.parent))
    stem = Path(original_path).stem
    stem = ''.join('_' if c in '<>:"/\\|?*' or ord(c) < 32 else c for c in stem).rstrip('. ') or 'image'
    label = 'LINEAR' if input_state == 'linear' else 'INPUT'
    files = []
    metadata = dict(source=str(original_path), input_state=input_state, normalization='none',
                    filters='none', stretch='none', units='Original loaded pixel units',
                    colour='Source RGB retained without colour calibration or ICC assignment')
    try:
        name = f'{stem}_{label}_L_float32.tif'
        tifffile.imwrite(stage/name, mono.astype(np.float32), photometric='minisblack',
                         compression='zlib', metadata=metadata)
        files.append(name)
        if rgb is not None:
            rgb = np.asarray(rgb, dtype=np.float32)
            if rgb.shape != (*mono.shape, 3) or not np.isfinite(rgb[valid]).all():
                raise ValueError('RGB must match source luminance and validity')
            name = f'{stem}_{label}_RGB_float32.tif'
            tifffile.imwrite(stage/name, np.where(valid[..., None], rgb, np.nan),
                             photometric='rgb', compression='zlib', metadata=metadata)
            files.append(name)
        name = f'{stem}_VALID.tif'
        tifffile.imwrite(stage/name, valid.astype(np.uint8)*255, compression='zlib', metadata=None)
        files.append(name)
        (stage/'sources.json').write_text(json.dumps(dict(metadata, files=files,
            luminance='0.299 R + 0.587 G + 0.114 B in source units; no photometric calibration',
            missing_pixels=int((~valid).sum())), indent=2), encoding='utf-8')
        note = ('La entrada se ha declarado lineal.' if input_state == 'linear' else
                'La entrada no está declarada lineal: los archivos INPUT conservan su transferencia original.')
        (stage/'LEEME.txt').write_text(note + '\nRGB y L sin filtros, estirado ni normalización. '
            'No se ha invertido ninguna curva de entrada. Los valores y NaN se conservan en float32.\n'
            'VALID indica datos observados (255) y ausentes (0).\n'
            'La luminancia es una combinación de canales, no una calibración de brillo físico.\n', encoding='utf-8')
        stage.rename(destination)
        return destination
    except Exception:
        shutil.rmtree(stage)
        raise
