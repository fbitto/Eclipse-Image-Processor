"""Verified PSB16 export of existing independent layer packages.

Low-level new_document/add_layer/_to_lr16 and imports adapted from AEL 1.3.3,
Copyright (c) 2026 Pere Guerra Serra, MIT (docs/third-party/AEL-MIT.txt).
Local additions: required blend modes, merged RGBA, recipe metadata, no-replace
publication and exact channel verification. No upstream AEL install is needed.

Speed: every distinct channel plane is compressed once, on helper threads
(zlib releases the GIL), with the same psd-tools prediction and zlib call as
add_layer, so the file is identical byte for byte to adding the layers one
by one. The export passes its layers in memory (export_psb_layers); a TIFF
layer folder can still be converted (export_psb_package). Verification
decompresses each distinct stored channel once, on threads bounded by memory.

GUI response: the helper threads never build a full-size bytes object. Such a
copy holds the GIL (bytes allocation, tobytes, zlib's final join of a whole
plane), and with a dozen threads queued behind one another the GUI thread
can wait up to a second. Encoding writes the big-endian deltas into one array
that zlib reads in place; verification inflates and compares by blocks of
rows. Same bytes, same exact comparison.
"""
from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context
from pathlib import Path
import gc
import hashlib
import importlib.metadata
import json
import os
import errno
import shutil
import tempfile
import time
import zlib
from xml.sax.saxutils import escape

import numpy as np
import tifffile
from .cancellation import check_cancelled
from .progress import report

MODES = ('normal','overlay','multiply','color','linear_light')
BLEND_KEYS = {'Multiply':'multiply','Normal':'normal','Overlay':'overlay','Color':'color','Linear Light':'linear_light'}
# Scratch memory for compression or verification: about four plane copies per thread.
PLANE_TEMPORARIES = 4
# Verification steps: decompressed and compressed bytes handled at a time. Copies
# this small hold the GIL for about a millisecond; much smaller steps make a
# dozen threads queue for the GIL between steps (4 MB was 3.5 times slower).
VERIFY_BLOCK_BYTES = 16*1024**2
VERIFY_INPUT_BYTES = 4*1024**2

def _psd():
    try:
        from psd_tools import PSDImage
    except ImportError as e:  # pragma: no cover
        raise ImportError('PSB export requires psd-tools==1.26.0; install the project requirements') from e
    from psd_tools.api.layers import PixelLayer
    from psd_tools.constants import BlendMode, ChannelID, Compression, Resource, Tag
    from psd_tools.psd.image_resources import ImageResource
    from psd_tools.psd.layer_and_mask import ChannelData, ChannelDataList, ChannelInfo, LayerInfo, LayerRecord
    from psd_tools.psd.tagged_blocks import TaggedBlocks
    return dict(PSDImage=PSDImage, PixelLayer=PixelLayer, BlendMode=BlendMode, ChannelID=ChannelID,
                Compression=Compression, Resource=Resource, Tag=Tag, ImageResource=ImageResource,
                ChannelData=ChannelData, ChannelDataList=ChannelDataList, ChannelInfo=ChannelInfo,
                LayerInfo=LayerInfo, LayerRecord=LayerRecord, TaggedBlocks=TaggedBlocks)


def new_document(width: int, height: int):
    """An empty 16-bit RGB document in PSB large document format."""
    P = _psd()
    doc = P["PSDImage"].new("RGB", (int(width), int(height)), depth=16)
    doc._record.header.version = 2
    doc._next_layer_id = 1
    return doc


def _append_layer(doc, name, mode, opacity, visible, channels):
    """One layer record exactly as add_layer builds it; ``channels`` is [(ChannelID, ChannelData)]."""
    P = _psd()
    h, w = doc.height, doc.width
    rec = P["LayerRecord"](top=0, left=0, bottom=h, right=w, channel_info=[])
    rec.name = name.encode("mac_roman", "replace").decode("mac_roman")[:31]
    rec.tagged_blocks.set_data(P["Tag"].UNICODE_LAYER_NAME, name)
    rec.tagged_blocks.set_data(P["Tag"].LAYER_ID, doc._next_layer_id)
    doc._next_layer_id += 1
    rec.blend_mode = getattr(P["BlendMode"], mode.upper())
    rec.opacity = int(round(float(opacity) * 255))
    rec.flags.visible = bool(visible)
    cdl = P["ChannelDataList"]()
    for cid, cd in channels:
        rec.channel_info.append(P["ChannelInfo"](cid, len(cd.data) + 2))
        cdl.append(cd)
    layer = P["PixelLayer"](doc, rec, cdl)
    doc.append(layer)
    return layer


def add_layer(doc, name: str, rgb16: np.ndarray, alpha16: np.ndarray | None = None, *, mode: str = "normal",
              opacity: float = 1.0, visible: bool = True, rle: bool = False):
    """Append a full-canvas layer on top.  ``rgb16``: (H, W, 3) or (H, W) grey, uint16; ``alpha16``: (H, W)
    uint16 or None (opaque).  ``opacity`` 0–1."""
    P = _psd()
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}")
    rgb16 = np.asarray(rgb16)
    if rgb16.ndim == 2:
        rgb16 = np.repeat(rgb16[..., None], 3, axis=2)
    if rgb16.dtype != np.uint16 or rgb16.shape[2] != 3:
        raise ValueError("rgb16 must be uint16, (H, W, 3) or (H, W)")
    h, w = rgb16.shape[:2]
    if (h, w) != (doc.height, doc.width):
        raise ValueError(f"layer is {w}×{h}, document is {doc.width}×{doc.height}: layers are full canvas")
    if alpha16 is None:
        alpha16 = np.full((h, w), 65535, np.uint16)
    elif alpha16.dtype != np.uint16 or alpha16.shape != (h, w):
        raise ValueError("alpha16 must be uint16 (H, W)")
    comp = P["Compression"].RLE if rle else P["Compression"].ZIP_WITH_PREDICTION
    ver = doc._record.header.version
    planes = ((P["ChannelID"].TRANSPARENCY_MASK, alpha16), (P["ChannelID"](0), rgb16[..., 0]),
              (P["ChannelID"](1), rgb16[..., 1]), (P["ChannelID"](2), rgb16[..., 2]))
    channels = []
    for cid, plane in planes:
        cd = P["ChannelData"](comp)
        cd.set_data(np.ascontiguousarray(plane).astype(">u2").tobytes(), w, h, 16, ver)
        channels.append((cid, cd))
    return _append_layer(doc, name, mode, opacity, visible, channels)


def _workers(plane_bytes):
    """Threads for plane work: the filter CPU budget, bounded by an eighth of physical memory (1 GiB if unknown)."""
    from .parallelism import filter_cpu_budget, physical_memory_bytes
    installed = physical_memory_bytes()
    memory = 1024**3 if installed is None else installed//8
    return max(1, min(filter_cpu_budget(), memory//max(1, PLANE_TEMPORARIES*plane_bytes)))


def _compress_plane(plane):
    """ZIP-with-prediction bytes of a (H, W) uint16 plane, as psd_tools.compression.compress makes them.

    The same row deltas (modulo 2**16), stored big-endian, and the same
    zlib.compress call; zlib reads the array in place instead of a bytes copy.
    """
    plane = np.asarray(plane)
    encoded = np.empty(plane.shape, '>u2')
    encoded[:, :1] = plane[:, :1]
    np.subtract(plane[:, 1:], plane[:, :-1], out=encoded[:, 1:])
    return zlib.compress(encoded)


class _Inflater:
    """A zlib stream read in bounded pieces: input in slices of VERIFY_INPUT_BYTES, output as asked.

    Handing zlib the whole remaining stream on each call would copy it into
    ``unconsumed_tail`` every time; a slice keeps every copy small.
    """

    def __init__(self, data):
        self._zlib = zlib.decompressobj()
        self._data = memoryview(data)
        self._position = 0
        self._tail = b''

    def read(self, size):
        """The next ``size`` decompressed bytes; fewer only where the stream has no more."""
        parts, have = [], 0
        while have < size and not self._zlib.eof:
            if self._tail:
                piece = self._tail
            elif self._position < len(self._data):
                piece = self._data[self._position:self._position+VERIFY_INPUT_BYTES]
                self._position += len(piece)
            else:
                piece = b''                 # input used up: only what zlib still holds
            chunk = self._zlib.decompress(piece, size-have)
            self._tail = self._zlib.unconsumed_tail
            if chunk:
                parts.append(chunk)
                have += len(chunk)
            elif not piece or len(self._tail) == len(piece):
                break                       # no output and no input taken: nothing more will come
        return b''.join(parts)

    def finished(self):
        """No output left, the end of the stream read, and nothing after it.

        After the end, CPython keeps leftover input in ``unconsumed_tail`` as well
        as in ``unused_data``; input never handed to zlib is left over too.
        """
        return (not self.read(1) and self._zlib.eof and not self._zlib.unused_data
                and not self._tail and self._position >= len(self._data))


def _zip_prediction_matches(data, expected):
    """Whether a ZIP-with-prediction 16-bit channel decodes exactly to ``expected`` (H, W).

    The decoding of psd_tools.compression.decompress (inflate, then the running
    sum of each row modulo 2**16), done by blocks of rows: no full-size bytes
    object is made. A stream that is short, long, unterminated or corrupt does
    not match (psd-tools would put a black channel in place of a corrupt one).
    """
    h, w = expected.shape
    rows = max(1, VERIFY_BLOCK_BYTES//(2*w))
    stream = _Inflater(data)
    try:
        for first in range(0, h, rows):
            check_cancelled()
            count = min(rows, h-first)
            block = stream.read(2*w*count)
            if len(block) != 2*w*count:
                return False
            deltas = np.frombuffer(block, '>u2').reshape(count, w).astype(np.uint16)
            if not np.array_equal(np.cumsum(deltas, axis=1, dtype=np.uint16), expected[first:first+count]):
                return False
        return stream.finished()
    except zlib.error:
        return False


def _map(function, items, workers, detail=None, span=(0., 1.)):
    """Ordered results on helper threads that inherit cancellation (copy_context).

    With ``detail``, core.progress.report announces each finished item as a
    share (per mille) of the writer's work: ``span`` is this step's part of it.
    """
    items = list(items)
    workers = max(1, min(len(items), workers))
    results = []
    def announce():
        if detail:
            report(round(1000*(span[0]+(span[1]-span[0])*len(results)/len(items))), 1000, detail)
    if workers == 1:
        for item in items:
            results.append(function(item))
            announce()
        return results
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix='psb-plane') as executor:
        futures = [executor.submit(copy_context().run, function, item) for item in items]
        try:
            for future in futures:
                results.append(future.result())
                announce()
            return results
        except BaseException:
            for future in futures:
                future.cancel()
            raise


def _plane_digest(plane):
    """Content key of a uint16 plane (BLAKE2b-256 of its big-endian bytes), by row blocks."""
    digest = hashlib.blake2b(digest_size=32)
    digest.update(repr(plane.shape).encode())
    for first in range(0, plane.shape[0], 256):
        digest.update(np.ascontiguousarray(plane[first:first+256], dtype='>u2'))
    return digest.digest()


def encode_layers(doc, specs):
    """Compressed channels of each layer, as add_layer would make them; distinct planes once, in parallel.

    ``specs``: dicts with name, rgb (three (H, W) uint16 planes, possibly the
    same object), alpha ((H, W) uint16 or None = opaque), mode, opacity and
    visible. Planes equal in content (R = G = B of grey layers, shared alphas,
    zero planes) are compressed once; zlib is deterministic, so the bytes match
    add_layer's. Returns one [(ChannelID, ChannelData)] list per spec and the
    counts; the caller appends them in order with _append_layer.
    """
    P = _psd()
    h, w = doc.height, doc.width
    comp = P["Compression"].ZIP_WITH_PREDICTION
    planned = []
    distinct = {}
    opaque = None
    for spec in specs:
        rgb = tuple(np.asarray(plane) for plane in spec['rgb'])
        alpha = spec.get('alpha')
        if alpha is None:
            if opaque is None:
                opaque = np.full((h, w), 65535, np.uint16)
            alpha = opaque
        if len(rgb) != 3 or any(plane.dtype != np.uint16 or plane.shape != (h, w) for plane in (*rgb, alpha)):
            raise ValueError('PSB layer planes must be full-canvas uint16 (H, W)')
        if spec.get('mode', 'normal') not in MODES:
            raise ValueError(f"mode must be one of {MODES}")
        for plane in (alpha, *rgb):
            distinct.setdefault(id(plane), plane)
        planned.append((alpha, *rgb))
    workers = _workers(2*h*w)
    keys = dict(zip(distinct, _map(_plane_digest, distinct.values(), workers)))
    unique = {}
    for identity, plane in distinct.items():
        unique.setdefault(keys[identity], plane)
    def encode(item):
        check_cancelled()
        key, plane = item
        return key, _compress_plane(plane)
    compressed = dict(_map(encode, unique.items(), workers, 'compressing PSB planes', (0., .6)))
    ids = (P["ChannelID"].TRANSPARENCY_MASK, P["ChannelID"](0), P["ChannelID"](1), P["ChannelID"](2))
    layers = []
    for layer_planes in planned:
        channels = []
        for cid, plane in zip(ids, layer_planes):
            cd = P["ChannelData"](comp)
            cd.data = compressed[keys[id(plane)]]
            channels.append((cid, cd))
        layers.append(channels)
    return layers, dict(planes=4*len(planned), distinct=len(distinct), compressed=len(unique), threads=workers)


def _to_lr16(doc) -> None:
    P = _psd()
    lmi = doc._record.layer_and_mask_information
    li = lmi.layer_info
    if li is None or not li.layer_records:
        return
    if lmi.tagged_blocks is None:
        lmi.tagged_blocks = P["TaggedBlocks"]()
    lmi.tagged_blocks.set_data(P["Tag"].LAYER_16, layer_count=li.layer_count, layer_records=li.layer_records,
                               channel_image_data=li.channel_image_data)
    lmi.layer_info = P["LayerInfo"]()


def _check_recipe(recipe, shape):
    if len(shape) != 2 or not all(isinstance(v,int) and 0 < v <= 300000 for v in shape):
        raise ValueError('PSB needs two positive image dimensions, at most 300000 pixels')
    if not recipe.get('layers') or len(recipe['layers']) > 32766:
        raise ValueError('PSB needs 1 to 32766 image layers plus background')
    for row in recipe['layers']:
        if row.get('mode') not in BLEND_KEYS or not 0 <= row.get('opacity_255',-1) <= 255:
            raise ValueError('Unsupported layer mode or opacity')


def _package(package):
    package = Path(package).resolve()
    recipe = json.loads((package/'recipe.json').read_text())
    shape = tuple(recipe['shape'])
    _check_recipe(recipe, shape)
    for row in recipe['layers']:
        _package_path(package,row['file'])
        if row.get('mask_file'):
            _package_path(package,row['mask_file'])
    return package,recipe,shape


def _package_path(package,name):
    path = (package/name).resolve()
    if not path.is_relative_to(package) or not path.is_file():
        raise ValueError('Layer package paths must reference files inside the package')
    return path


def _pixels(path,shape):
    a = tifffile.imread(path)
    if a.dtype != np.uint16 or a.shape not in ((*shape,3),(*shape,4)):
        raise ValueError(f'PSB layer must be full-canvas uint16 RGB/RGBA: {path.name}')
    return a


def _name(row):
    return row.get('name') or Path(row['file']).stem


def _black_composite(composite):
    """Composite straight uint16 RGBA onto black; preserve RGB input exactly."""
    if composite.shape[-1] == 3:
        return composite
    return np.rint(composite[...,:3].astype(np.float64) *
                   (composite[...,3:4].astype(np.float64)/65535)).astype(np.uint16)


def _layer_mask(package,row,shape):
    if not row.get('mask_file'):
        return None
    mask=tifffile.imread(_package_path(package,row['mask_file']))
    if mask.dtype != np.uint16 or mask.shape != shape:
        raise ValueError('PSB editable mask must be full-canvas uint16')
    return mask


def _folder_package(package, *, check_hashes=True):
    """A TIFF layer folder as an in-memory package, checking each file against its recipe hash."""
    from .layer_package import LayerPackage, PackageLayer
    package,recipe,shape = _package(package)
    layers = []
    for row in recipe['layers']:
        check_cancelled()
        path = _package_path(package,row['file'])
        if check_hashes and row.get('sha256'):
            with path.open('rb') as stream:
                if hashlib.file_digest(stream,'sha256').hexdigest() != row['sha256']:
                    raise ValueError(f'Layer file changed since package creation: {path.name}')
        a = _pixels(path,shape)
        alpha = a[...,3] if a.shape[-1] == 4 else None
        layers.append(PackageLayer(row,(a[...,0],a[...,1],a[...,2]),alpha,_layer_mask(package,row,shape)))
    combined = _black_composite(_pixels(_package_path(package,recipe['combined']),shape))
    corona = None
    if recipe.get('corona_combined'):
        corona = _black_composite(_pixels(_package_path(package,recipe['corona_combined']),shape))
    valid = None
    mask_file = recipe.get('validity_file','VALID.tif')
    if (package/mask_file).is_file():
        valid = tifffile.imread(_package_path(package,mask_file))
        if valid.shape != shape:
            raise ValueError('Color Correction validity must match PSB canvas')
        valid = valid > 0
    return LayerPackage(shape,layers,combined,recipe,corona_combined=corona,valid=valid)


def _correction_input(package):
    if package.valid is None:
        raise ValueError('Color Correction needs the validity mask of the layer package')
    composite = package.corona_combined if package.corona_combined is not None else package.combined
    return composite,package.valid,package.recipe.get('parameters',{})


def _layer_specs(package):
    zeros = np.zeros(package.shape,np.uint16)
    specs = [dict(name='00_BACKGROUND_Black',rgb=(zeros,)*3,alpha=None,mode='normal',opacity=1.,visible=True)]
    for layer in package.layers:
        row = layer.record
        specs.append(dict(name=_name(row),rgb=layer.rgb,alpha=layer.alpha,mode=BLEND_KEYS[row['mode']],
                          opacity=row['opacity_255']/255.,visible=row.get('visible',True)))
    return specs


def _same(actual, expected, shape):
    return np.array_equal(np.frombuffer(actual,dtype='>u2').reshape(shape),expected)


def _channel_matches(channel, expected):
    """Whether a stored layer channel decodes exactly to the (H, W) uint16 plane ``expected``."""
    from psd_tools.constants import Compression
    if channel.compression == Compression.ZIP_WITH_PREDICTION:
        return _zip_prediction_matches(channel.data, expected)
    h, w = expected.shape
    return _same(channel.get_data(w,h,16,2),expected,expected.shape)


def _merged_planes(doc, shape):
    """The three stored merged planes as big-endian views, without copying the image data."""
    from psd_tools.constants import Compression
    image = doc._record.image_data
    size = 2*shape[0]*shape[1]
    if image.compression == Compression.RAW and len(image.data) == 3*size:
        return [np.frombuffer(image.data,'>u2',count=size//2,offset=k*size).reshape(shape) for k in range(3)]
    return [np.frombuffer(plane,'>u2').reshape(shape) for plane in image.get_data(doc._record.header)]


def verify_psb_document(path, package, *, color_correction=False):
    """Reopen the PSB; check structure, every channel, the black background and the merged RGB exactly.

    The same checks as before, with every stored channel compared on helper
    threads; a channel whose compressed bytes and expected plane both repeat an
    already verified pair is the same check and is not decompressed again.
    """
    from psd_tools import PSDImage
    from psd_tools.constants import BlendMode,Resource
    shape = package.shape
    recipe = package.recipe
    doc = PSDImage.open(path)
    if (doc._record.header.version,doc.depth,doc.height,doc.width) != (2,16,*shape):
        raise ValueError('PSB header does not match the package')
    if len(doc) != len(recipe['layers']) + 1 + bool(color_correction):
        raise ValueError('PSB layer count does not match the package')
    profile=doc.image_resources.get_data(Resource.ICC_PROFILE)
    if not profile or profile[16:20]!=b"RGB " or profile[36:40]!=b"acsp":
        raise ValueError("PSB RGB colour profile is missing or invalid")
    background=doc[0]
    if (background.name,background.blend_mode,background.opacity,bool(background.visible)) != (
            '00_BACKGROUND_Black',BlendMode.NORMAL,255,True):
        raise ValueError('PSB black background metadata mismatch')
    if {int(info.id) for info in background._record.channel_info} != {-1,0,1,2}:
        raise ValueError('PSB black background channels mismatch')
    zeros = np.zeros(shape,np.uint16)
    opaque = np.full(shape,65535,np.uint16)
    checks = []
    for info,channel in zip(background._record.channel_info,background._channels):
        checks.append(('PSB black background pixel mismatch',channel,opaque if int(info.id) == -1 else zeros))
    report_rows=[]
    image_layers=[layer for layer in list(doc)[1:] if not layer.is_group()]
    if len(image_layers) != len(recipe['layers']):
        raise ValueError('PSB image-layer count does not match the package')
    for layer,package_layer in zip(image_layers,package.layers):
        row = package_layer.record
        if (layer.name,layer.blend_mode,layer.opacity,bool(layer.visible)) != (
                _name(row),getattr(BlendMode,BLEND_KEYS[row['mode']].upper()),
                row['opacity_255'],row.get('visible',True)):
            raise ValueError(f'PSB layer metadata mismatch: {_name(row)}')
        mask = package_layer.mask
        channels={int(info.id) for info in layer._record.channel_info}
        if channels != ({-2,-1,0,1,2} if mask is not None else {-1,0,1,2}):
            raise ValueError('PSB layer channels do not match RGB, transparency and optional mask')
        alpha = package_layer.alpha if package_layer.alpha is not None else opaque
        for info,channel in zip(layer._record.channel_info,layer._channels):
            cid = int(info.id)
            expected = mask if cid == -2 else alpha if cid == -1 else package_layer.rgb[cid]
            checks.append((f'PSB pixel mismatch: {_name(row)}, channel {cid}',channel,expected))
        if mask is not None:
            data=layer._record.mask_data
            if (data.top,data.left,data.bottom,data.right,data.background_color)!=(0,0,*shape,0) or data.flags.mask_disabled or data.flags.invert_mask:
                raise ValueError('PSB layer mask bounds or flags mismatch')
        report_rows.append(dict(name=layer.name,mode=row['mode'],opacity_255=layer.opacity,
                                visible=bool(layer.visible),exact_rgb=True,exact_alpha=True))
    unique = {}
    planes = {id(expected):expected for _,_,expected in checks}
    workers = _workers(2*shape[0]*shape[1])
    digests = dict(zip(planes,_map(_plane_digest,planes.values(),workers)))
    for message,channel,expected in checks:
        pair = (hashlib.blake2b(channel.data,digest_size=32).digest(),digests[id(expected)])
        unique.setdefault(pair,(message,channel,expected))
    def check(item):
        check_cancelled()
        message,channel,expected = item
        if not _channel_matches(channel,expected):
            raise ValueError(message)
        return True
    started = time.perf_counter()
    _map(check,unique.values(),workers,'verifying PSB channels',(.6,1.))
    print(f'[PSB VERIFY: CHANNELS] {len(checks)} channels, {len(unique)} distinct, {workers} threads; '
          f'done in {time.perf_counter()-started:.3f}s')
    if doc._record.header.channels != 3:
        raise ValueError('PSB black-backed merged image must be RGB')
    for k,plane in enumerate(_merged_planes(doc,shape)):
        if not np.array_equal(plane,package.combined[...,k]):
            raise ValueError(f'PSB merged channel mismatch: {k}')
    if Resource.XMP_METADATA not in doc._record.image_resources:
        raise ValueError('PSB recipe metadata is missing')
    correction_report=None
    if color_correction:
        from .color_correction import verify_color_correction
        correction_report=verify_color_correction(doc,*_correction_input(package))
    return dict(version=2,depth=16,shape=list(shape),layers=report_rows,
                exact_composite=not color_correction,exact_base_reference=True,
                color_correction=correction_report,merged_transparency=False,black_background=True,
                psd_tools=importlib.metadata.version('psd-tools'))


def verify_psb_package(path,package,*,color_correction=False):
    """Reopen PSB; check original channels, opaque black background and cached RGB exactly.

    ``package`` is a TIFF layer folder or an in-memory core.layer_package.LayerPackage.
    """
    if not hasattr(package,'layers'):
        package=_folder_package(package,check_hashes=False)
    return verify_psb_document(path,package,color_correction=color_correction)


def _write_psb(package, destination, *, color_correction=False):
    """Encode, write, verify and publish; the published file is always the verified one."""
    total_start = time.perf_counter()
    recipe = package.recipe
    shape = package.shape
    _check_recipe(recipe, shape)
    if color_correction and len(recipe['layers'])>32760:
        raise ValueError('Color Correction exceeds the PSB layer-record limit')
    destination = Path(destination)
    if destination.exists():
        raise FileExistsError(destination)
    if destination.suffix.lower() != '.psb':
        raise ValueError('The layered Photoshop destination must end in .psb')
    doc = new_document(shape[1],shape[0])
    encode_start = time.perf_counter()
    specs = _layer_specs(package)
    encoded, counts = encode_layers(doc,specs)
    print(f"[PSB: ENCODE] {len(specs)} layers, {counts['planes']} planes, {counts['compressed']} compressed "
          f"({counts['threads']} threads); done in {time.perf_counter()-encode_start:.3f}s")
    check_cancelled()
    correction=None
    for spec,channels,package_layer in zip(specs,encoded,(None,*package.layers)):
        if color_correction and package_layer is not None and package_layer.record.get('filter') == 'prominences':
            from .color_correction import add_color_correction
            correction=add_color_correction(doc,*_correction_input(package))
        layer=_append_layer(doc,spec['name'],spec['mode'],spec['opacity'],spec['visible'],channels)
        if package_layer is not None and package_layer.mask is not None:
            from .color_correction import _mask
            _mask(layer,package_layer.mask)
    composite_start = time.perf_counter()
    from psd_tools.constants import Compression,Resource
    from psd_tools.psd.image_resources import ImageResource
    rec=doc._record
    from .color_correction import srgb_profile
    if Resource.ICC_PROFILE not in rec.image_resources:
        rec.image_resources[Resource.ICC_PROFILE]=ImageResource(key=Resource.ICC_PROFILE,data=srgb_profile())
    composite = package.combined
    if color_correction and correction is None:
        from .color_correction import add_color_correction
        correction=add_color_correction(doc,*_correction_input(package))
    rec.header.channels=3
    rec.image_data.compression=Compression.RAW
    rec.image_data.set_data([np.ascontiguousarray(composite[...,k]).astype('>u2').tobytes()
                             for k in range(composite.shape[-1])],rec.header)
    _to_lr16(doc)
    provenance = dict(recipe=recipe,writer='AEL-derived PSB16 writer; Eclipse Image Processor',
                      psd_tools=importlib.metadata.version('psd-tools'),black_background=True)
    if correction is not None:
        provenance['color_correction']=correction
    xmp = ('<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
           '<rdf:Description rdf:about="" xmlns:eip="https://eclipse-image-processor/metadata/1/">'
           '<eip:recipe>'+escape(json.dumps(provenance,ensure_ascii=False))+'</eip:recipe>'
           '</rdf:Description></rdf:RDF></x:xmpmeta>')
    rec.image_resources[Resource.XMP_METADATA]=ImageResource(
        signature=b'8BIM',key=Resource.XMP_METADATA,name='',data=xmp.encode('utf-8'))
    print(f"[PSB: CACHED COMPOSITE/METADATA] Done in {time.perf_counter()-composite_start:.3f}s")
    temporary=None
    write_start = time.perf_counter()
    try:
        with tempfile.NamedTemporaryFile(prefix='.'+destination.stem+'-',suffix='.psb.tmp',
                                         dir=destination.parent,delete=False) as stream:
            temporary=Path(stream.name)
            rec.write(stream)
            stream.flush()
            os.fsync(stream.fileno())
        print(f"[PSB: DISK WRITE] Done in {time.perf_counter()-write_start:.3f}s")
        del doc,rec
        gc.collect()
        verify_start = time.perf_counter()
        result=verify_psb_package(temporary,package,color_correction=color_correction)
        print(f"[PSB: VERIFY] Done in {time.perf_counter()-verify_start:.3f}s")
        check_cancelled()
        try:
            # Prefer atomic no-replace publication on filesystems with hard links.
            os.link(temporary,destination)
        except (OSError,NotImplementedError) as error:
            if (isinstance(error,OSError) and error.errno not in (errno.EPERM,errno.ENOTSUP,errno.ENOSYS,errno.EXDEV)
                    and getattr(error,'winerror',None) not in (1,50)):
                raise
            created=False
            try:
                with destination.open('xb') as stream:
                    created=True
                    with temporary.open('rb') as source:
                        shutil.copyfileobj(source,stream,1024*1024)
                    stream.flush()
                    os.fsync(stream.fileno())
            except BaseException:
                if created:
                    destination.unlink(missing_ok=True)
                raise
        print(f"[PSB: TOTAL] Done in {time.perf_counter()-total_start:.3f}s")
        return result
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def export_psb_layers(package, destination, *, color_correction=False):
    """Write an in-memory layer package (core.layer_package) as a verified PSB, without TIFF files.

    Each recipe row gets the sha256 of its pixels (see LAYER_SHA256), because
    there is no layer file to hash.
    """
    from .layer_package import LAYER_SHA256
    from .parallelism import filter_cpu_budget
    hashes = _map(lambda layer: layer.sha256(), package.layers, filter_cpu_budget())
    for layer,digest in zip(package.layers,hashes):
        layer.record['sha256']=digest
    package.recipe['layer_sha256']=LAYER_SHA256
    return _write_psb(package,destination,color_correction=color_correction)


def export_psb_package(package,destination,*,color_correction=False):
    """Convert a TIFF layer folder; publish only after verified writing, never overwrite."""
    destination = Path(destination)
    if destination.exists():
        raise FileExistsError(destination)
    if destination.suffix.lower() != '.psb':
        raise ValueError('The layered Photoshop destination must end in .psb')
    return _write_psb(_folder_package(package),destination,color_correction=color_correction)
