"""Behaviour kept from before the speed changes: errors, their order, and bounded memory."""
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

import numpy as np
import tifffile

from core.parallelism import filter_budget, map_in_threads, memory_bounded_workers
from core.presentation_edges import finish_presentation
from core.psb_export import export_psb_package


class ThreadHelperTests(unittest.TestCase):
    def test_items_not_started_never_run_after_an_error(self):
        ran = []
        lock = threading.Lock()
        def work(item):
            with lock:
                ran.append(item)
            if item == 0:
                raise ValueError('first item fails')
            time.sleep(.02)
        with filter_budget(2), self.assertRaisesRegex(ValueError, 'first item fails'):
            map_in_threads(work, range(200))
        time.sleep(.1)
        self.assertLess(len(ran), 200)

    def test_memory_bound(self):
        with filter_budget(16), patch('core.parallelism.physical_memory_bytes', return_value=16*1024**3):
            self.assertEqual(memory_bounded_workers(1024**3), 4)
            self.assertEqual(memory_bounded_workers(1), 16)
            self.assertEqual(memory_bounded_workers(10*1024**3), 1)
        with filter_budget(16), patch('core.parallelism.physical_memory_bytes', return_value=None):
            self.assertEqual(memory_bounded_workers(256*1024**2), 4)


class ShapeTests(unittest.TestCase):
    def test_finish_rejects_an_edge_alpha_of_another_size(self):
        with self.assertRaises(ValueError):
            finish_presentation(np.zeros((600, 40), np.float32), np.zeros((700, 40), np.uint16))


class PsbPackageOrderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.package = self.root/'layers'
        self.package.mkdir()
        shape = (24, 32)
        rgb = np.full((*shape, 3), 1000, np.uint16)
        tifffile.imwrite(self.package/'base.tif', rgb, photometric='rgb')
        tifffile.imwrite(self.package/'merged.tif', rgb, photometric='rgb')
        (self.package/'recipe.json').write_text(json.dumps(dict(
            shape=list(shape), combined='merged.tif',
            layers=[dict(file='base.tif', name='BASE', mode='Normal', opacity_255=255, visible=True)])))

    def tearDown(self):
        self.tmp.cleanup()

    def test_validity_is_read_only_for_color_correction(self):
        tifffile.imwrite(self.package/'VALID.tif', np.ones((3, 3), np.uint8))
        export_psb_package(self.package, self.root/'plain.psb')
        self.assertTrue((self.root/'plain.psb').exists())

    def test_a_missing_package_is_reported_before_an_existing_destination(self):
        (self.package/'recipe.json').unlink()
        destination = self.root/'taken.psb'
        destination.write_bytes(b'keep')
        with self.assertRaises(FileNotFoundError):
            export_psb_package(self.package, destination)
        with self.assertRaises(FileNotFoundError):
            export_psb_package(self.package, self.root/'other.psd')
        self.assertEqual(destination.read_bytes(), b'keep')


if __name__ == '__main__':
    unittest.main()
