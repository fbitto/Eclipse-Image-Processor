"""The faster PSB route writes the same document as layer-by-layer add_layer and the TIFF folder route."""
import io
import json
from pathlib import Path
import re
import tempfile
import unittest
from xml.sax.saxutils import unescape
import zlib

import numpy as np
from psd_tools import PSDImage
from psd_tools.compression import compress
from psd_tools.constants import Compression

from core.filters import FilterWorker
from core.layer_export import export_layer_package
from core.layer_package import build_layer_package
from core.parallelism import filter_budget
from core.presentation import psb_presentation_settings
from core.prominences import prominence_settings, prominence_layer
from core.psb_export import (_append_layer, _compress_plane, _zip_prediction_matches, add_layer, encode_layers,
                             export_psb_layers, export_psb_package, new_document, verify_psb_package)


def _document_bytes(doc):
    stream = io.BytesIO()
    doc._record.write(stream)
    return stream.getvalue()


def _recipe(doc):
    from psd_tools.constants import Resource
    xmp = doc._record.image_resources[Resource.XMP_METADATA].data.decode('utf-8')
    return json.loads(unescape(re.search('<eip:recipe>(.*)</eip:recipe>', xmp, re.S).group(1)))


class PlaneCompressionTests(unittest.TestCase):
    def test_compressed_plane_is_psd_tools_zip_with_prediction(self):
        rng = np.random.default_rng(7)
        planes = [rng.integers(0, 65536, size, dtype=np.uint16) for size in ((1, 1), (1, 9), (9, 1), (37, 53))]
        planes += [np.zeros((5, 6), np.uint16), np.full((5, 6), 65535, np.uint16),
                   np.tile(np.array([0, 65535], np.uint16), (4, 5))]
        planes.append(rng.integers(0, 65536, (64, 40), dtype=np.uint16)[:, ::2])   # a strided view
        for plane in planes:
            h, w = plane.shape
            expected = compress(np.ascontiguousarray(plane).astype('>u2').tobytes(),
                                Compression.ZIP_WITH_PREDICTION, w, h, 16, 2)
            with self.subTest(shape=plane.shape):
                self.assertEqual(_compress_plane(plane), expected)
                self.assertTrue(_zip_prediction_matches(expected, plane))

    def test_short_long_corrupt_or_different_streams_do_not_match(self):
        plane = np.arange(48*31, dtype=np.uint16).reshape(48, 31)*37
        data = _compress_plane(plane)
        changed = plane.copy()
        changed[30, 7] += 1
        self.assertFalse(_zip_prediction_matches(data, changed))
        self.assertFalse(_zip_prediction_matches(data[:-6], plane))
        self.assertFalse(_zip_prediction_matches(data+b'extra', plane))
        self.assertFalse(_zip_prediction_matches(data[:10]+b'\x00'*8+data[18:], plane))
        longer = zlib.compress(np.zeros((49, 31), '>u2'))
        self.assertFalse(_zip_prediction_matches(longer, np.zeros((48, 31), np.uint16)))


class ParallelEncodingTests(unittest.TestCase):
    def _specs(self):
        rng = np.random.default_rng(3)
        shape = (40, 56)
        grey = rng.integers(0, 65536, shape, dtype=np.uint16)
        alpha = rng.integers(0, 65536, shape, dtype=np.uint16)
        rgb = rng.integers(0, 65536, (*shape, 3), dtype=np.uint16)
        zeros = np.zeros(shape, np.uint16)
        return shape, [
            dict(name='00_BACKGROUND_Black', rgb=(zeros,)*3, alpha=None, mode='normal', opacity=1., visible=True),
            dict(name='grey', rgb=(grey,)*3, alpha=alpha, mode='overlay', opacity=.5, visible=True),
            dict(name='same grey, copied', rgb=(grey.copy(),)*3, alpha=alpha.copy(), mode='multiply',
                 opacity=0., visible=False),
            dict(name='colour', rgb=tuple(rgb[..., c] for c in range(3)), alpha=None, mode='color',
                 opacity=1., visible=True),
            dict(name='edge', rgb=(zeros,)*3, alpha=alpha, mode='normal', opacity=1., visible=True)]

    def test_document_is_identical_to_adding_layers_one_by_one_with_any_thread_count(self):
        shape, specs = self._specs()
        reference = new_document(shape[1], shape[0])
        for spec in specs:
            add_layer(reference, spec['name'], np.dstack(spec['rgb']), spec['alpha'], mode=spec['mode'],
                      opacity=spec['opacity'], visible=spec['visible'])
        expected = _document_bytes(reference)
        for workers in (1, 8):
            doc = new_document(shape[1], shape[0])
            with filter_budget(workers):
                encoded, counts = encode_layers(doc, specs)
            for spec, channels in zip(specs, encoded):
                _append_layer(doc, spec['name'], spec['mode'], spec['opacity'], spec['visible'], channels)
            with self.subTest(workers=workers):
                self.assertEqual(_document_bytes(doc), expected)
                # Background zeros, one opaque alpha, the grey plane and its alpha, three RGB planes.
                self.assertEqual(counts['compressed'], 7)


class MemoryRouteTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        yy, xx = np.mgrid[:64, :80]
        corona = np.exp(-np.hypot(xx-40, yy-32)/10)
        self.source = (1 + corona + .001*np.sin(xx)).astype(np.float32)
        self.source[30:35, 38:43] = np.nan
        self.rgb = np.stack([self.source*1.1, self.source, self.source*.8], axis=-1).astype(np.float32)
        self.params = dict(sx=40., sy=32., sr=8., tangential_enabled=True, tangential_str=25,
                           tangential_arc=10, tangential_gain=2., mgn_enabled=True, mgn_str=10, mgn_gam=32,
                           valid_mask=np.isfinite(self.source))
        self.display = psb_presentation_settings(self.source, self.params['valid_mask'], rgb=self.rgb,
                                                 params=self.params)

    def tearDown(self):
        self.tmp.cleanup()

    def _both(self, name, prominences=None, color_correction=False):
        folder = self.root/f'{name}_layers'
        export_layer_package(FilterWorker(), self.source, self.params, self.display, 'eclipse.tif', folder,
                             rgb=self.rgb, colour_report=dict(method='none'), prominences=prominences)
        old = self.root/f'{name}_folder.psb'
        export_psb_package(folder, old, color_correction=color_correction)
        package = build_layer_package(FilterWorker(), self.source, self.params, self.display, 'eclipse.tif',
                                      rgb=self.rgb, colour_report=dict(method='none'), prominences=prominences)
        new = self.root/f'{name}_memory.psb'
        report = export_psb_layers(package, new, color_correction=color_correction)
        return folder, old, new, package, report

    def _assert_same_psb(self, old, new):
        a, b = PSDImage.open(old), PSDImage.open(new)
        self.assertEqual(len(a), len(b))
        self.assertEqual(a._record.image_data.data, b._record.image_data.data)
        layers_a = [layer for layer in a.descendants()]
        layers_b = [layer for layer in b.descendants()]
        self.assertEqual(len(layers_a), len(layers_b))
        for x, y in zip(layers_a, layers_b):
            self.assertEqual((x.name, x.blend_mode, x.opacity, x.visible), (y.name, y.blend_mode, y.opacity, y.visible))
            self.assertEqual([int(i.id) for i in x._record.channel_info], [int(i.id) for i in y._record.channel_info])
            self.assertEqual([c.data for c in x._channels], [c.data for c in y._channels], x.name)
        ra, rb = _recipe(a), _recipe(b)
        for recipe in (ra['recipe'], rb['recipe']):
            recipe.pop('layer_sha256', None)
            for row in recipe['layers']:
                row.pop('sha256')
        self.assertEqual(ra, rb)

    def test_memory_route_writes_the_folder_route_psb_without_layer_files(self):
        folder, old, new, package, report = self._both('plain')
        self._assert_same_psb(old, new)
        self.assertEqual(len(report['layers']), len(package.layers))
        self.assertEqual(sorted(p.name for p in self.root.iterdir()),
                         sorted(['plain_layers', 'plain_folder.psb', 'plain_memory.psb']))
        recipe = _recipe(PSDImage.open(new))['recipe']
        self.assertIn('computed in memory', recipe['layer_sha256'])
        self.assertTrue(all(re.fullmatch('[0-9a-f]{64}', row['sha256']) for row in recipe['layers']))
        for row, layer in zip(json.loads((folder/'recipe.json').read_text())['layers'], package.layers):
            self.assertEqual(row['file'], layer.record['file'])

    def test_prominence_mask_and_color_correction_match_the_folder_route(self):
        p = dict(self.params)
        settings = prominence_settings(self.rgb, p, -2.)
        image, mask = prominence_layer(self.rgb, p, settings)
        _, old, new, package, report = self._both('corrected', (image, mask, settings), color_correction=True)
        self._assert_same_psb(old, new)
        self.assertIsNotNone(report['color_correction'])
        self.assertIsNotNone(package.layers[-1].mask)

    def test_verification_rejects_a_changed_channel(self):
        _, _, new, package, _ = self._both('checked')
        doc = PSDImage.open(new)
        layer = doc[2]
        changed = package.layers[1].rgb[0].copy()
        changed[5, 5] ^= 1
        layer._channels[1].data = _compress_plane(changed)
        layer._record.channel_info[1].length = len(layer._channels[1].data)+2
        damaged = self.root/'damaged.psb'
        with damaged.open('wb') as stream:
            doc._record.write(stream)
        with self.assertRaisesRegex(ValueError, 'PSB pixel mismatch'):
            verify_psb_package(damaged, package)


if __name__ == '__main__':
    unittest.main()
