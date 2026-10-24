"""Exercise the real export action without a visible Qt window or file dialog."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import cv2
import numpy as np
import tifffile

from core.filters import FilterWorker
from core.pipeline import prepare_parameters
from core.export import export_images
from gui.app import EclipseProcessorApp


class FilterExportTests(unittest.TestCase):
    def test_final_images_are_written_only_after_layers_succeed(self):
        image=np.ones((8,10),np.float32)
        with tempfile.TemporaryDirectory() as tmp:
            destination=Path(tmp)/'final.tif'
            jpeg=Path(tmp)/'final_preview.jpg'
            def layers(*args, **kwargs):
                self.assertFalse(destination.exists())
                self.assertFalse(jpeg.exists())
                return Path(tmp)/'layers'
            updates=[]
            with patch('core.export.export_layer_package',side_effect=layers) as package:
                export_images(image,{}, {},str(destination),'source.fits',
                              export_layers=True,processed=image,progress=lambda value,label:updates.append((value,label)))
            self.assertEqual([label for _,label in updates],[
                'Preparing export','Calculating filters','Writing layer package',
                'Composing final image','Writing TIFF','Writing JPEG','Export complete'])
            self.assertEqual(updates[0][0],0)
            self.assertEqual(updates[-1][0],100)
            self.assertEqual([value for value,_ in updates],sorted(value for value,_ in updates))
            package.assert_called_once()
            self.assertTrue(destination.exists())
            self.assertTrue(jpeg.exists())
            failed=Path(tmp)/'failed.tif'
            with patch('core.export.export_layer_package',side_effect=ValueError('layer failure')):
                with self.assertRaisesRegex(ValueError,'layer failure'):
                    export_images(image,{}, {},str(failed),'source.fits',
                                  export_layers=True,processed=image)
            self.assertFalse(failed.exists())
            self.assertFalse((Path(tmp)/'failed_preview.jpg').exists())

    def test_scaled_kernels_bins_and_real_16bit_tiff_and_jpeg(self):
        image = np.random.default_rng(81).uniform(100, 5000, (128, 160)).astype(np.float32)
        enabled = {"noise_gate", "fnrgf", "mgn"}
        window = SimpleNamespace(
            raw_image=image[::2, ::2], preview_image=image[::2, ::2],
            full_raw_image=image, status_label=Mock(), source_path="original.tif",
            collect_display_parameters=lambda: dict(mode="asinh", strength=12, blend=.65),
            colour_data=lambda: (None, None, None),
            chk_export_layers=Mock(isChecked=lambda: True),
            combo_input_state=Mock(currentData=lambda: "unknown"), full_source_rgb=None,
            txt_x=Mock(text=lambda: "80"), txt_y=Mock(text=lambda: "64"), txt_r=Mock(text=lambda: "16"),
        )
        for name in ("pre_stretch", "noise_gate", "bilateral", "fnrgf", "mgn", "wow", "rhef", "tangential", "achf"):
            setattr(window, f"sec_{name}", Mock(is_filter_active=lambda n=name: n in enabled))
        values = dict(noise_gate_str=10, noise_gate_thr=10,
                      fnrgf_str=32, fnrgf_ord=6, fnrgf_seg=4, fnrgf_cut=0,
                      fnrgf_rad=10, fnrgf_rmax=61, fnrgf_nbins=20, fnrgf_mask=0,
                      mgn_str=10, mgn_gam=32, mgn_k=70, mgn_h=70, mgn_trunc=3)
        for name, value in values.items():
            setattr(window, f"sl_{name}", Mock(value=lambda v=value: v))
        window.combo_fnrgf_width = Mock(currentIndex=lambda: 0)
        window.combo_fnrgf_binning = Mock(currentIndex=lambda: 0)
        recipe = dict(
            noise_gate_enabled=True, noise_gate_str=10, noise_gate_thr=10,
            fnrgf_enabled=True, fnrgf_str=32, fnrgf_ord=6, fnrgf_seg=16,
            fnrgf_cut=0, fnrgf_rad=10, fnrgf_rmax=61, fnrgf_nbins=20,
            mgn_enabled=True, mgn_str=10, mgn_gam=32, mgn_k=70, mgn_h=70, mgn_trunc=3,
            rhef_enabled=True, rhef_str=20, rhef_rad=10, rhef_upsilon=35,
            rhef_mode="continuous", rhef_bin_px=1, sx=80., sy=64., sr=16.,
        )
        window.collect_filter_parameters = lambda shape: prepare_parameters(
            recipe, image.shape, window.preview_image.shape, shape)
        originals = {name: getattr(FilterWorker, name) for name in
                     ("run_radial_noise_gate", "run_mgn_native", "run_fnrgf_native")}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "export.tiff"
            with patch("gui.app.QFileDialog.getSaveFileName", return_value=(str(path), "")), \
                 patch("gui.app.QApplication.processEvents"), \
                 patch.object(FilterWorker, "run_radial_noise_gate", autospec=True,
                              side_effect=originals["run_radial_noise_gate"]) as gate, \
                 patch.object(FilterWorker, "run_mgn_native", autospec=True,
                              side_effect=originals["run_mgn_native"]) as mgn, \
                 patch.object(FilterWorker, "run_fnrgf_native", autospec=True,
                              side_effect=originals["run_fnrgf_native"]) as fnrgf:
                export_images(image.copy(), window.collect_filter_parameters(image.shape),
                              window.collect_display_parameters(), str(path), 'original.tif',
                              scale_factor=2., export_layers=True)
            self.assertTrue(path.is_file(), window.status_label.setText.call_args)
            gate.assert_not_called()
            self.assertEqual(mgn.call_args.kwargs["sigmas"], (1.25, 2.5, 5, 10, 20, 40))
            self.assertEqual(fnrgf.call_args.args[8], 40)
            exported = tifffile.imread(path)
            self.assertEqual(exported.dtype, np.uint16)
            self.assertEqual(exported.shape, image.shape)
            jpeg = cv2.imread(str(path.with_name("export_preview.jpg")), cv2.IMREAD_GRAYSCALE)
            self.assertIsNotNone(jpeg)
            self.assertEqual(jpeg.shape, image.shape)
            import json
            from core.presentation import render_presentation
            from core.pipeline import execute_pipeline
            parameters = window.collect_filter_parameters(image.shape)
            expected = render_presentation(execute_pipeline(FilterWorker(), image, parameters),
                                           image, window.collect_display_parameters())
            np.testing.assert_array_equal(exported, (expected * 65535).astype(np.uint16))
            package = path.with_name("export_PS_layers")
            manifest = json.loads((package / "recipe.json").read_text())
            self.assertEqual([r["filter"] for r in manifest["layers"]], ["base", "fnrgf", "rhef", "mgn"])
            self.assertEqual([r["file"] for r in manifest["layers"]],
                             ["01_BASE_Normal.tif", "02_FNRGF_Overlay.tif", "03_RHEF_Overlay.tif", "04_MGN_Overlay.tif"])
            self.assertTrue((package / "Load_layers_Photoshop.jsx").is_file())
            instructions = (package / "Layers.md").read_text()
            self.assertIn('File > Scripts > Browse > Load_layers_Photoshop.jsx', instructions)
            self.assertIn('| Order | File | Blend mode | Effective opacity |', instructions)
