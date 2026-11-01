"""Shared export destinations and protection of the loaded source."""
from pathlib import Path


def export_paths(output_path, include_settings=True, *, layers_format=None, linear=False, prominences=False):
    output = Path(output_path)
    paths = [output, output.with_name(output.stem + '_preview.jpg')]
    if include_settings:
        paths.append(output.with_suffix('.json'))
    if layers_format is not None:
        paths.append(output.with_name(output.stem+'_PS_layers'+('.psb' if layers_format=='psb' else '')))
    if linear:
        paths.append(output.with_name(output.stem+'_sources'))
    if prominences:
        paths.append(output.with_name(output.stem+'_prominences'))
    return paths


def available_export_path(output_path, **products):
    """Choose one unused stem for every companion in a layered export."""
    output=Path(output_path)
    candidate=output
    suffix=2
    while any(path.exists() or path.is_symlink() for path in export_paths(candidate,**products)):
        candidate=output.with_name(output.stem+f'_{suffix}'+output.suffix)
        suffix+=1
    return candidate


def protect_source(destinations, source_path):
    if not source_path:
        return
    source = Path(source_path)
    for destination in map(Path, destinations):
        if (destination.resolve() == source.resolve()
                or (destination.exists() and source.exists() and destination.samefile(source))):
            raise ValueError(f'Export destination would overwrite the original image: {destination}')
