"""Shared export destinations and protection of the loaded source."""
from pathlib import Path


def export_paths(output_path, include_settings=True):
    output = Path(output_path)
    paths = [output, output.with_name(output.stem + '_preview.jpg')]
    if include_settings:
        paths.append(output.with_suffix('.json'))
    return paths


def protect_source(destinations, source_path):
    if not source_path:
        return
    source = Path(source_path)
    for destination in map(Path, destinations):
        if (destination.resolve() == source.resolve()
                or (destination.exists() and source.exists() and destination.samefile(source))):
            raise ValueError(f'Export destination would overwrite the original image: {destination}')
