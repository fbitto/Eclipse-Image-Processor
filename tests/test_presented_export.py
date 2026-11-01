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
