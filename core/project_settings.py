"""Versioned JSON processing settings; source pixels remain in the original file."""
import json
import os
from pathlib import Path
import tempfile

FORMAT='eclipse-image-processor-settings'
VERSION=2


def write_settings(output_path, source_path, settings, parameters, display):
    from .image_data import recipe_parameters
    destination=Path(output_path).with_suffix('.json')
    source=Path(source_path).resolve()
    document=dict(format=FORMAT,version=VERSION,source=str(source),
        source_relative=os.path.relpath(source,destination.parent.resolve()),
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


def read_settings(path):
    path=Path(path)
    if path.stat().st_size>2*1024**2:
        raise ValueError('Settings JSON is too large')
    data=json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data,dict) or data.get('format')!=FORMAT or data.get('version') not in (1,VERSION):
        raise ValueError('Not a supported Eclipse Image Processor settings file')
    if not isinstance(data.get('settings'),dict) or not isinstance(data.get('source'),str):
        raise ValueError('Settings JSON has no controls or source image')
    candidates=[]
    relative=data.get('source_relative')
    if isinstance(relative,str):candidates.append(path.parent/relative)
    candidates.append(Path(data['source']))
    source=next((p.resolve() for p in candidates if p.is_file()),None)
    if source is None:
        raise FileNotFoundError(f"Original image not found: {data['source']}")
    if source.suffix.lower()=='.json':
        raise ValueError('Settings source must be an image, not another JSON file')
    if data['version']==1:
        # Version 1 sliders used preview pixels; parameters record export pixels.
        parameters=data.get('parameters',{})
        values=data['settings'].get('controls',{})
        sigmas=parameters.get('mgn_sigmas')
        for index in range(6):
            record=values.get(f'sl_mgn_sigmas.{index}')
            if isinstance(record,dict) and type(record.get('value')) is int:
                native=(sigmas[index] if isinstance(sigmas,list) and len(sigmas)==6
                        else record['value']/100*parameters.get('spatial_scale',1))
                record['value']=round(native*100)
    return source,data['settings']
