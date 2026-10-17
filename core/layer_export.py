"""Independent mono detail and optional RGB Color layer for Photoshop.

Every branch shares one prepared input, with no preceding enhancement branch.
Detail layers are uint16 equal-channel RGB; the optional top RGB layer uses Color.
Both support unassociated alpha. Numerical
input/preparation files retain float32 input units; they are not PS display layers.
"""
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

import numpy as np
import tifffile

from .colour import colour_layer, set_luminosity
from .pipeline import execute_pipeline
from .presentation import stretch_image
from .image_data import observed_image, recipe_parameters

FILTERS = ('fnrgf', 'mgn', 'wow', 'rhef', 'usm', 'achf')
PREPARATION = ('pre_stretch', 'noise_gate', 'bilateral')


def photoshop_loader(records):
    """Import into a new unsaved document; never close an owner's document."""
    return '''#target photoshop
(function () {
    var layers = RECORDS;
    var folder = File($.fileName).parent;
    var dialogs = app.displayDialogs;
    var result = null;
    function ownedCopy(file) {
        for (var i = 0; i < app.documents.length; i++) {
            try {
                if (app.documents[i].fullName.fsName === file.fsName) {
                    app.activeDocument = app.documents[i];
                    return app.activeDocument.duplicate();
                }
            } catch (ignored) {}
        }
        return app.open(file);
    }
    try {
        app.displayDialogs = DialogModes.NO;
        for (var j = 0; j < layers.length; j++) {
            var entry = layers[j];
            var input = ownedCopy(File(folder.fsName + '/' + entry.file));
            try {
                if (j === 0) {
                    result = input.duplicate('Independent corona layers');
                    app.activeDocument = result;
                    if (result.activeLayer.isBackgroundLayer) {
                        result.activeLayer.isBackgroundLayer = false;
                    }
                } else {
                    app.activeDocument = input;
                    input.activeLayer.duplicate(result, ElementPlacement.PLACEATBEGINNING);
                    app.activeDocument = result;
                    result.activeLayer = result.layers[0];
                }
                result.activeLayer.name = entry.file.replace(/\\.tif$/i, '');
                result.activeLayer.blendMode = entry.mode === 'Color' ? BlendMode.COLOR : (entry.mode === 'Normal' ? BlendMode.NORMAL : BlendMode.OVERLAY);
                result.activeLayer.opacity = entry.opacity_255 * 100 / 255;
                result.activeLayer.visible = entry.visible;
            } finally {
                app.activeDocument = input;
                input.close(SaveOptions.DONOTSAVECHANGES);
            }
        }
        app.activeDocument = result;
    } finally {
        app.displayDialogs = dialogs;
    }
})();
'''.replace('RECORDS', json.dumps(records, ensure_ascii=True))


def to_u16(a):
    return np.rint(np.clip(a, 0, 1) * 65535).astype(np.uint16)


def neutral_layer(values, valid):
    """Median-centred tanh display; S is 1.4826 MAD, in branch units.

    No absolute epsilon: near-constant residuals use a relative numerical floor.
    Excluded pixels have neutral grey and zero alpha, never invented structure.
    """
    a = np.asarray(values, dtype=np.float64)
    mask = np.asarray(valid, dtype=bool)
    if a.ndim != 2 or not a.size or mask.shape != a.shape:
        raise ValueError('Layer validity must match image')
    result = np.full(a.shape, .5, dtype=np.float64)
    if not mask.any():
        return result, dict(center=0., scale=0., constant=True)
    selected = a[mask]
    if not np.isfinite(selected).all():
        raise ValueError("Observed layer samples must be finite")
    center = float(np.median(selected))
    residual = selected - center
    mad = float(1.4826 * np.median(np.abs(residual)))
    floor = max(float(np.max(np.abs(selected))) * 1e-6, np.finfo(float).tiny)
    constant = bool(np.ptp(selected) <= floor)
    scale = max(mad, floor)
    if not constant:
        result[mask] = .5 + .5 * np.tanh(residual / (2.5 * scale))
    return result, dict(center=center, scale=scale, mad=mad,
                        relative_floor=floor, constant=constant,
                        formula='0.5 + 0.5*tanh((q-center)/(2.5*scale))')


def overlay(base, layer, alpha, opacity):
    """Photoshop Overlay in declared display numbers, with straight alpha."""
    mixed = np.where(base <= .5, 2 * base * layer,
                     1 - 2 * (1 - base) * (1 - layer))
    weight = alpha * opacity
    return base * (1 - weight) + mixed * weight


def branch_domain(shape, params, name):
    yy, xx = np.ogrid[:shape[0], :shape[1]]
    radius = np.hypot(xx - params['sx'], yy - params['sy'])
    sr = float(params['sr'])
    if not np.isfinite(sr) or sr <= 0:
        raise ValueError('Layer export needs a positive disk radius')
    domain = radius > sr
    if name in ('fnrgf', 'rhef'):
        domain &= radius >= float(params[name + '_rad']) / 10 * sr
    if name == 'fnrgf':
        domain &= radius < float(params.get('fnrgf_rmax', 30)) / 10 * sr
    return domain


def export_layer_package(worker, source, params, display, original_path, destination, rgb=None, colour_report=None):
    """Write a new package atomically; active nonzero branches only, bottom first.

    Source is the application's monochrome image, with optional missing-data mask. Its original
    transfer function/colour cannot be inferred. No RGB/ICC calibration is claimed.
    """
    source, valid = observed_image(source, params.get("valid_mask"))
    source = source.astype(np.float32)
    params = dict(params, valid_mask=valid)
    if rgb is not None:
        rgb = np.asarray(rgb)
        if rgb.shape != (*source.shape, 3) or not np.isfinite(rgb[valid]).all():
            raise ValueError('RGB must match luminance and its observed-data mask')
    destination = Path(destination)
    if destination.exists():
        raise FileExistsError(f'Layer folder already exists: {destination}')
    destination.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.layers-', dir=destination.parent))
    stem = Path(original_path).stem
    # Remove characters unsupported by common desktop filesystems.
    stem = ''.join('_' if c in '<>:"/\\|?*' or ord(c) < 32 else c for c in stem).rstrip('. ') or 'image'
    records = []
    try:
        preparation = dict(params)
        for name in FILTERS:
            preparation[name + '_enabled'] = False
        prepared = execute_pipeline(worker, source, preparation)
        tifffile.imwrite(stage / f'{stem}_SOURCE_float32.tif', source,
                         compression='zlib', metadata={'role': 'Loaded monochrome input; transfer function unspecified'})
        tifffile.imwrite(stage / f'{stem}_PREPARED_float32.tif', prepared.astype(np.float32),
                         compression='zlib', metadata={'role': 'Common preparation; may be nonlinear if pre-stretch enabled'})

        tifffile.imwrite(stage / f'{stem}_VALID.tif', valid.astype(np.uint8)*255,
                         compression='zlib', metadata={'role': 'Observed-data validity; 255 observed, 0 missing'})
        base16 = to_u16(stretch_image(prepared, display))
        base_file = f'{stem}_01_BASE_Normal.tif'
        base_rgb = np.repeat(base16[..., None], 3, axis=2)
        if not valid.all():
            base_rgb = np.concatenate([base_rgb, (valid.astype(np.uint16)*65535)[..., None]], axis=2)
        tifffile.imwrite(stage / base_file, base_rgb, photometric='rgb',
                         extrasamples=['unassalpha'] if not valid.all() else None,
                         compression='zlib', metadata=None)
        records.append(dict(order=1, file=base_file, filter='base', mode='Normal',
                            opacity=1., opacity_255=255, visible=True))
        composite = base16.astype(np.float64) / 65535
        for name in FILTERS:
            if not params.get(name + '_enabled', False) or params.get(name + '_str', 0) == 0:
                continue
            branch = dict(preparation)
            for key in PREPARATION:
                branch[key + '_enabled'] = False
            branch[name + '_enabled'] = True
            branch[name + '_str'] = 100
            # FNRGF limb protection belongs in layer alpha, not baked into RGB.
            branch['fnrgf_apply_mask'] = 0
            filtered = execute_pipeline(worker, prepared.copy(), branch)
            # USM carries its base; ACHF carries background * input.
            # Extract only their signed sharpening residuals.
            # Other operators provide mapped normalized structure; remove DC below.
            if name == 'usm':
                values = filtered - prepared
            elif name == 'achf':
                values = filtered - float(params.get('achf_background', 10)) / 100 * prepared
            else:
                values = filtered
            domain = branch_domain(source.shape, params, name) & valid
            if name == 'rhef' and params.get('rhef_mode') == 'continuous':
                domain &= prepared > 0
            layer, mapping = neutral_layer(values, domain)
            alpha = domain.astype(np.float64)
            if name == 'fnrgf' and params.get('fnrgf_apply_mask', 0):
                yy, xx = np.ogrid[:source.shape[0], :source.shape[1]]
                r = np.hypot(xx - params['sx'], yy - params['sy']) / params['sr']
                protection = np.clip(1 - np.abs(r - 1) / .05, 0, 1)
                alpha *= 1 - float(params['fnrgf_apply_mask']) / 100 * protection
            # Recommended contribution, not the old chain's Strength blend.
            opacity = min(.35, float(params[name + '_str']) / 100) * float(display.get('blend', 1))
            opacity_255 = round(opacity * 255)
            layer16, alpha16 = to_u16(layer), to_u16(alpha)
            order = len(records) + 1
            label = name.upper()
            if name == 'rhef':
                label += '_' + params.get('rhef_mode', 'legacy')
            filename = f'{stem}_{order:02d}_{label}_Overlay.tif'
            rgba = np.empty((*source.shape, 4), dtype=np.uint16)
            rgba[..., :3] = layer16[..., None]
            rgba[..., 3] = alpha16
            tifffile.imwrite(stage / filename, rgba, photometric='rgb',
                             extrasamples=['unassalpha'], compression='zlib', metadata=None)
            composite = overlay(composite, layer16.astype(float) / 65535,
                                alpha16.astype(float) / 65535, opacity_255 / 255)
            records.append(dict(order=order, file=filename, filter=name, mode='Overlay',
                                opacity=opacity, opacity_255=opacity_255, visible=opacity_255 > 0,
                                normalization=mapping, operator_strength=100,
                                signal=('signed sharpening residual' if name in ('usm', 'achf')
                                        else 'full-strength structure output in mapped input units'),
                                input='PREPARED_float32', domain='Outside lunar disc and filter application domain'))
        if rgb is not None:
            tifffile.imwrite(stage/f'{stem}_RGB_COLOUR_INPUT_float32.tif',
                             np.where(valid[..., None], rgb, np.nan).astype(np.float32),
                             photometric='rgb', compression='zlib',
                             metadata={'role': 'Colour working input; optional neutralization applied',
                                       'colour_calibration': colour_report})
            rgb_layer = to_u16(colour_layer(rgb, source, display))
            order = len(records)+1
            filename = f'{stem}_{order:02d}_RGB_Color.tif'
            rgba = np.concatenate([rgb_layer, (valid.astype(np.uint16)*65535)[..., None]], axis=2)
            tifffile.imwrite(stage/filename, rgba, photometric='rgb', extrasamples=['unassalpha'], compression='zlib', metadata=None)
            records.append(dict(order=order, file=filename, filter='colour', mode='Color', opacity=1., opacity_255=255, visible=True))
            composite_rgb = set_luminosity(rgb_layer.astype(float)/65535, composite)
        else:
            composite_rgb = np.repeat(composite[..., None], 3, axis=2)
        combined_file = f'{stem}_PS_COMBINED.tif'
        combined_rgb = to_u16(composite_rgb)
        if not valid.all():
            combined_rgb = np.concatenate([combined_rgb, (valid.astype(np.uint16)*65535)[..., None]], axis=2)
        tifffile.imwrite(stage / combined_file, combined_rgb, photometric='rgb',
                         extrasamples=['unassalpha'] if not valid.all() else None,
                         compression='zlib', metadata=None)
        for record in records:
            with (stage / record['file']).open('rb') as stream:
                record['sha256'] = hashlib.file_digest(stream, 'sha256').hexdigest()
        manifest = dict(schema=1, source=str(original_path), shape=list(source.shape),
                        working_image_sha256=hashlib.sha256(source.tobytes()).hexdigest(),
                        parameters=recipe_parameters(params), display=display, layers=records,
                        validity_file=f'{stem}_VALID.tif', missing_pixels=int((~valid).sum()),
                        masked_wow='Observed-only normalized starlet variant' if not valid.all() else None,
                        combined=combined_file, order='bottom_to_top',
                        colour='RGB Color layer over mono detail; no calibrated ICC' if rgb is not None else 'Monochrome equal-channel RGB; no calibrated ICC',
                        colour_calibration=colour_report,
                        blend_space='Display numeric values; no extra gamma conversion',
                        alpha='Unassociated; input lunar disc excluded from enhancement layers',
                        composite='Independent branches, distinct from sequential pipeline final',
                        stretch='Base only; no stretch or gamma after Overlay composition',
                        normalization='Median-centred tanh; not the AEL numerical algorithms',
                        opacity='min(Strength/100, 0.35) * Reveal; quantized to 1/255',
                        limitations=['Finite lunar observations are not automatically excluded from filter input.',
                                     'Masked WOW is a normalized-starlet variant, not byte-equivalent to watroo.',
                                     'Native Photoshop rendering not verified.'])
        (stage / 'recipe.json').write_text(json.dumps(manifest, indent=2, allow_nan=False), encoding='utf-8')
        (stage / 'Cargar_capas_Photoshop.jsx').write_text(photoshop_loader(records), encoding='utf-8')
        lines = ['# Capas para Photoshop', '',
                 'En Photoshop: Archivo > Secuencias de comandos > Examinar > Cargar_capas_Photoshop.jsx.',
                 'El script crea un documento nuevo sin guardar; configura nombres, orden, modos y opacidades.',
                 'Orden de abajo hacia arriba. SOURCE y PREPARED son archivos numéricos: no apilarlos.',
                 'La capa RGB superior en modo Color conserva el detalle de las capas inferiores. No cambiarla a Normal.',
                 'La base ya está estirada. No aplicar gamma ni estirado a las capas de gris medio ni al combinado.',
                 'El combinado PS usa ramas independientes y difiere del final de la cadena de la aplicación.',
                 'Importar conservando transparencia (alfa sin premultiplicar). No añadir de nuevo esa máscara.',
                 'Usar los valores numéricos RGB sin conversión adicional de gamma en la mezcla; no hay ICC calibrado.',
                 'Para comparar con PS_COMBINED, desactivar ajustes adicionales de mezcla gamma en Photoshop.',
                 'La opacidad recomendada es un inicio conservador; no reproduce Strength de la cadena.', '',
                 '| Orden | Archivo | Modo | Opacidad efectiva |', '|---|---|---|---|']
        lines += [f"| {r['order']} | {r['file']} | {r['mode']} | {100*r['opacity_255']/255:.4f}% |" for r in records]
        lines += ['', 'Los datos ausentes se excluyen del cálculo y se conservan como NaN/alfa cero.',
                  'En entradas con máscara, WOW usa una variante starlet normalizada por soporte, distinta del backend sin máscara.',
                  'Gris neutro teórico 0.5 se cuantiza a 32768/65535 en TIFF. No es radiancia.',
                  'El máximo error por cuantización y la gestión de color de Photoshop deben verificarse allí.']
        (stage / 'CAPAS.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
        stage.rename(destination)
        return destination
    except Exception:
        shutil.rmtree(stage)
        raise
