"""Versioned JSON processing settings; source pixels remain in the original file."""
import json
import os
from pathlib import Path
import tempfile

FORMAT='eclipse-image-processor-settings'
VERSION=4


class MissingSourceImage(FileNotFoundError):
    """Valid settings envelope whose original image needs to be located."""
    def __init__(self, source, settings):
        super().__init__(f'Original image not found: {source}')
        self.source = source
        self.settings = settings


def write_settings(output_path, source_path, settings, parameters, display):
    from .image_data import recipe_parameters
    destination=Path(output_path).with_suffix('.json')
    from .export_paths import protect_source
    protect_source([destination], source_path)
    source=Path(source_path).resolve()
    try:
        relative=Path(os.path.relpath(source,destination.parent.resolve())).as_posix()
    except ValueError:
        relative=None
    document=dict(format=FORMAT,version=VERSION,source=str(source),
        source_relative=relative,
        settings=settings,parameters=recipe_parameters(parameters),display=display)
    temporary=None
    try:
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=destination.parent,
                prefix='.'+destination.stem+'-',suffix='.json.tmp',delete=False) as stream:
            temporary=Path(stream.name)
            json.dump(document,stream,indent=2,ensure_ascii=False,allow_nan=False)
            stream.write('\n')
            stream.flush();os.fsync(stream.fileno())
        os.replace(temporary,destination)
    finally:
        if temporary is not None:temporary.unlink(missing_ok=True)
    return destination


def read_settings(path, *, source_override=None):
    path=Path(path)
    if path.stat().st_size>2*1024**2:
        raise ValueError('Settings JSON is too large')
    data=json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data,dict) or data.get('format')!=FORMAT:
        raise ValueError('Not a supported Eclipse Image Processor settings file')
    if type(data.get('version')) is not int or data['version']!=VERSION:
        raise ValueError(f'Unsupported settings version; expected version {VERSION}')
    if not isinstance(data.get('settings'),dict) or not isinstance(data.get('source'),str):
        raise ValueError('Settings JSON has no controls or source image')
    candidates=[]
    relative=data.get('source_relative')
    if source_override is not None:
        candidates.append(Path(source_override))
    else:
        if isinstance(relative,str):
            candidates.append(path.parent/relative)
            # Older Windows recipes used backslashes; retain literal POSIX names first.
            candidates.append(path.parent/relative.replace('\\','/'))
        candidates.append(Path(data['source']))
    source=next((p.resolve() for p in candidates if p.is_file()),None)
    if source is None:
        raise MissingSourceImage(str(source_override) if source_override is not None else data['source'],data['settings'])
    if source.suffix.lower()=='.json':
        raise ValueError('Settings source must be an image, not another JSON file')
    return source,data['settings']
