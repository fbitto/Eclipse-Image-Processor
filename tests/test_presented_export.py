"""Presented display exports and separate full-precision working sources."""
from pathlib import Path
import tempfile
import unittest
import numpy as np
import tifffile
from PIL import Image
from psd_tools import PSDImage
from psd_tools.constants import Resource
from core.export import export_images

class PresentedExportTests(unittest.TestCase):
    def test_warmth_preview_matches_rgb16_tiff_psb_and_jpeg(self):
        from core.colour import neutralize_tse, set_luminosity
        from core.filters import FilterWorker
        from core.layer_engine import engine_for
        from core.layer_export import to_u16
        from gui.background_tasks import render_snapshot
        y,x = np.indices((120,160))
        radius = np.hypot(x-80,y-60)
        signal = .5*np.maximum(1-radius/40,0)**2
        rgb = np.array([.04,.08,.1]) + signal[...,None]
        source = rgb @ np.array([.299,.587,.114])
        params = dict(sx=80,sy=60,sr=5)
        background = dict(geometry=(80,60,5),radius=6.,grid=16,points=None)
        worker = FilterWorker();engine = engine_for(worker)
        reference = None
        with tempfile.TemporaryDirectory() as tmp:
            for amount in (0.,.5,1.):
                with self.subTest(warmth=amount):
                    job = dict(source=source,source_identity=source,params=params,display={},
                               engine=engine,worker=worker,rgb=rgb,colour_cache=None,preview_cache=None,
                               calibrate=True,white=1.,neutralize=neutralize_tse,set_luminosity=set_luminosity,
                               warmth=amount,warmth_background=background,psb_preview=True,
                               psb_params=params,psb_exposure_ev=0.,native=False)
                    preview = render_snapshot(job)[0]
                    target = Path(tmp)/f'warm{amount}.tif'
                    export_images(source,params,{},str(target),'camera.tif',source_rgb=rgb,
                                  calibrate_colour=True,white=1.,warmth=amount,warmth_background=background,
                                  export_layers=True,layers_format='psb')
                    presented = tifffile.imread(target)
                    self.assertEqual(presented.shape,rgb.shape)
                    self.assertEqual(presented.dtype,np.uint16)
                    np.testing.assert_array_equal(presented,to_u16(preview))
                    doc = PSDImage.open(target.with_name(target.stem+'_PS_layers.psb'))
                    current = doc[1]._channels[1].get_data(160,120,16,2)
                    if reference is None:reference = current
                    self.assertEqual(reference,current)
                    warm_layers = [layer for layer in doc if layer.name == 'Warmth - enhanced corona']
                    self.assertEqual(len(warm_layers),int(amount>0))
                    if warm_layers:self.assertTrue(warm_layers[0].has_mask())
                    planes = doc._record.image_data.get_data(doc._record.header)
                    merged = np.stack([np.frombuffer(p,dtype='>u2').reshape(source.shape) for p in planes],axis=-1)
                    np.testing.assert_array_equal(presented,merged)
                    with Image.open(target.with_name(target.stem+'_preview.jpg')) as jpeg:
                        self.assertEqual(jpeg.size,(160,120))
                        self.assertLess(np.mean(abs(np.asarray(jpeg).astype(float)-preview*255)),3.)

    def test_hdr_tiff_matches_psb_pixels_has_profile_and_keeps_float_sources(self):
        y,x=np.indices((96,128));r=np.hypot(x-64,y-48)
        a=(1e6/(np.maximum(r,1)/12)**4).astype('f4')
        a[48,64]=1e12;a[0,0]=np.nan;a[8,8]=-7
        p=dict(sx=64,sy=48,sr=12)
        before=a.copy()
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)/'out.tif'
            export_images(a,p,{},str(target),'camera.fits',export_layers=True,layers_format='psb',input_state='linear')
            image=tifffile.imread(target)
            self.assertEqual(image.shape,(*a.shape,3));self.assertEqual(image.dtype,np.uint16)
            self.assertGreater(np.median(image[(r>14.4)&np.isfinite(a)])/65535,.02)
            with tifffile.TiffFile(target) as tif:
                self.assertEqual(tif.pages[0].tags[34675].value[16:20],b'RGB ')
            with Image.open(Path(tmp)/'out_preview.jpg') as jpeg:
                self.assertEqual(jpeg.info['icc_profile'][16:20],b'RGB ')
            doc=PSDImage.open(Path(tmp)/'out_PS_layers.psb')
            self.assertEqual(doc.image_resources.get_data(Resource.ICC_PROFILE)[16:20],b'RGB ')
            planes=doc._record.image_data.get_data(doc._record.header)
            merged=np.stack([np.frombuffer(plane,dtype='>u2').reshape(a.shape) for plane in planes],axis=-1)
            np.testing.assert_array_equal(image,merged)
            self.assertIn('16-bit',doc[1].name)
            sources=Path(tmp)/'out_sources'
            restored=tifffile.imread(sources/'camera_LINEAR_L_float32.tif')
            np.testing.assert_array_equal(restored,np.nan_to_num(a))
            self.assertEqual(restored.dtype,np.float32);self.assertEqual(restored[8,8],-7)
            mask=tifffile.imread(sources/'camera_VALID.tif')
            self.assertEqual(mask[0,0],0);self.assertEqual(mask[8,8],255)
            with tifffile.TiffFile(sources/'camera_LINEAR_L_float32.tif') as tif:
                self.assertNotIn(34675,tif.pages[0].tags)
        np.testing.assert_array_equal(a,before)

if __name__=='__main__':unittest.main()
