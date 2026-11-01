"""Source identity, failed writes and unsupported TIFF encodings."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import tifffile

from core.export import export_images
from core.export_paths import export_paths, protect_source, available_export_path
from core.project_settings import write_settings
from gui.background_tasks import load_source


class ExportSafetyTests(unittest.TestCase):
    def test_layered_exports_use_one_new_stem_for_every_product(self):
        image=np.arange(80,dtype=np.float32).reshape(8,10)/80
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);target=root/'final.tif'
            target.write_bytes(b'old tiff')
            (root/'final_PS_layers.psb').write_bytes(b'old psb')
            # A companion-only collision also reserves the entire next stem.
            (root/'final_2_preview.jpg').write_bytes(b'old jpeg')
            with patch('core.psb_export.export_psb_package') as psb:
                def publish(package,path,**kwargs):Path(path).write_bytes(b'new psb')
                psb.side_effect=publish
                message=export_images(image,{}, {},str(target),'source.fits',processed=image,
                    export_layers=True,layers_format='psb',project_settings={})
            self.assertIn('final_3.tif',message)
            for name in ('final_3.tif','final_3_preview.jpg','final_3.json','final_3_PS_layers.psb'):
                self.assertTrue((root/name).is_file(),name)
            self.assertEqual(target.read_bytes(),b'old tiff')
            self.assertEqual((root/'final_PS_layers.psb').read_bytes(),b'old psb')
            self.assertEqual((root/'final_2_preview.jpg').read_bytes(),b'old jpeg')
            package=root/'another_PS_layers';package.mkdir()
            self.assertEqual(available_export_path(root/'another.tif',layers_format='tiff'),root/'another_2.tif')

    def test_layer_destination_alias_of_source_is_protected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'input.fits';source.write_bytes(b'original')
            (root/'output_PS_layers.psb').symlink_to(source)
            with self.assertRaisesRegex(ValueError,'original image'):
                export_images(np.ones((8,10)),{}, {},str(root/'output.tif'),str(source),
                    export_layers=True,layers_format='psb')
            self.assertEqual(source.read_bytes(),b'original')

    def test_multi_page_volume_and_too_small_tiffs_fail_before_detection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            cases=[('pages',np.zeros((6,8,2),np.float32),{},'Multi-page'),
                   ('volume',np.zeros((2,8,10),np.float32),dict(volumetric=True,photometric='minisblack'),'layout'),
                   ('small',np.zeros((8,2),np.float32),{},'at least')]
            for name,image,options,message in cases:
                path=root/(name+'.tif');tifffile.imwrite(path,image,**options)
                with self.subTest(name=name),patch('gui.background_tasks.cv2.imread') as fallback,patch('gui.app.EclipseProcessorApp.detect_lunar_limb') as detect:
                    with self.assertRaisesRegex(ValueError,message):load_source(str(path),None,detect)
                    detect.assert_not_called();fallback.assert_not_called()

    def test_single_page_mono_alpha_and_planar_rgb_are_supported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            mono_alpha=np.stack([np.ones((8,10)),np.ones((8,10))],-1).astype(np.float32)
            mono_alpha[0,0,1]=0
            path=root/'alpha.tif'
            tifffile.imwrite(path,mono_alpha,photometric='minisblack',extrasamples=['unassalpha'])
            loaded=load_source(str(path),(5,4,1),None)
            self.assertTrue(np.isnan(loaded['full'][0,0]))
            for width in (4,10):
                path=root/f'planar_{width}.tif'
                tifffile.imwrite(path,np.ones((3,8,width),np.float32),photometric='rgb',planarconfig='separate')
                self.assertEqual(load_source(str(path),(2,4,1),None)['rgb'].shape,(8,width,3))

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
                     ('core.export.Image.Image.save', dict(side_effect=partial)),
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
