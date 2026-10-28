"""Source identity, failed writes and unsupported TIFF encodings."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import tifffile

from core.export import export_images
from core.export_paths import export_paths, protect_source
from core.project_settings import write_settings
from gui.background_tasks import load_source


class ExportSafetyTests(unittest.TestCase):
    def test_source_aliases_and_companions_are_protected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root/'source.tif'
            source.write_bytes(b'original')
            symbolic = root/'symbolic.tif'
            symbolic.symlink_to(source)
            hard = root/'hard.tif'
            os.link(source, hard)
            for target in (source, root/'..'/root.name/'source.tif', symbolic, hard):
                with self.subTest(target=target), self.assertRaisesRegex(ValueError, 'original image'):
                    export_images(np.ones((4, 4)), {}, {}, str(target), str(source))
            companion = root/'final_preview.jpg'
            companion.symlink_to(source)
            with self.assertRaises(ValueError):
                protect_source(export_paths(root/'final.tif'), source)
            settings = root/'recipe.json'
            settings.symlink_to(source)
            with self.assertRaises(ValueError):
                write_settings(settings, source, {}, {}, {})
            self.assertEqual(source.read_bytes(), b'original')

    def test_failed_writes_preserve_existing_files_and_clean_temporaries(self):
        image = np.ones((8, 10), np.float32)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root/'final.tif'
            jpeg = root/'final_preview.jpg'
            def partial(path, *args, **kwargs):
                Path(path).write_bytes(b'partial')
                raise OSError('disk full')
            cases = [('core.export.tifffile.imwrite', dict(side_effect=partial)),
                     ('core.export.cv2.imwrite', dict(side_effect=partial)),
                     ('core.export.cv2.imwrite', dict(return_value=False)),
                     ('core.export.os.replace', dict(side_effect=OSError('replace failed')))]
            for name, behavior in cases:
                target.write_bytes(b'previous tiff')
                jpeg.write_bytes(b'previous jpeg')
                with self.subTest(name=name, behavior=behavior), patch(name, **behavior):
                    with self.assertRaises(OSError):
                        export_images(image, {}, {}, str(target), 'source.fits', processed=image)
                self.assertEqual(target.read_bytes(), b'previous tiff')
                self.assertEqual(jpeg.read_bytes(), b'previous jpeg')
                self.assertEqual(set(root.iterdir()), {target, jpeg})

    def test_unsupported_tiff_photometric_does_not_fall_back(self):
        with tempfile.TemporaryDirectory() as tmp:
            for photometric in ('miniswhite', 'palette'):
                path = Path(tmp)/(photometric+'.tif')
                options = dict(colormap=np.zeros((3, 256), np.uint16)) if photometric == 'palette' else {}
                tifffile.imwrite(path, np.arange(16, dtype=np.uint8).reshape(4, 4),
                                 photometric=photometric, **options)
                with patch('gui.background_tasks.cv2.imread') as fallback:
                    with self.assertRaisesRegex(ValueError, 'Unsupported TIFF photometric'):
                        load_source(str(path), (2, 2, 1), None)
                    fallback.assert_not_called()

    def test_supported_tiffs_preserve_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            for photometric, shape in [('minisblack', (4, 5)), ('rgb', (4, 5, 3))]:
                image = np.ones(shape, np.float32)
                image[0, 0] = np.nan
                path = Path(tmp)/(photometric+'.tif')
                tifffile.imwrite(path, image, photometric=photometric)
                result = load_source(str(path), (2, 2, 1), None)
                self.assertTrue(np.isnan(result['full'][0, 0]))
                np.testing.assert_allclose(result['full'][1:], 1)
