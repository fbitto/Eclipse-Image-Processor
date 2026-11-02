"""Enhanced streamer coverage, sampled sky noise, editable masks and RGB protection."""
import unittest
import numpy as np

from core.colour import set_luminosity, warm_colour
from core.warmth import warmth_layer, blend_warmth


def scene():
    y,x = np.indices((240,360))
    sky = .08 + .015*x/360 + .01*y/240
    # Deliberately far beyond six disk radii: no artificial outer cutoff.
    streamer = .025*np.exp(-((y-120)/5)**2)*np.clip((x-190)/35,0,1)*np.clip((345-x)/25,0,1)
    lum = sky+streamer
    rgb = set_luminosity(np.broadcast_to([.04,.08,.1],(*lum.shape,3)),lum)
    background = dict(geometry=(180,120,12),radius=6.,grid=16,points=None)
    return rgb,background,streamer


class WarmthTests(unittest.TestCase):
    def test_warmth_reaches_observed_inner_limb_without_a_white_annulus(self):
        y,x = np.indices((240,360))
        radius = np.hypot(x-180,y-120)
        lum = .08 + .5*np.exp(-np.maximum(radius-30,0)/12)
        rgb = set_luminosity(np.broadcast_to([.04,.08,.1],(*lum.shape,3)),lum)
        valid = radius >= 30
        rgb[~valid] = np.nan
        bg = dict(geometry=(180,120,30),radius=3.,grid=16,points=None)
        layer = warmth_layer(rgb,1.,bg,valid=valid)
        inner = valid & (radius < 32)
        self.assertGreater(layer[1][inner].min()/65535.,.98)
        self.assertTrue((layer[1][~valid] == 0).all())
        output = blend_warmth(rgb,layer)
        self.assertTrue(np.isnan(output[~valid]).all())

    def test_enhanced_streamer_tips_receive_colour_and_sky_gradient_is_preserved(self):
        rgb,bg,streamer = scene()
        layer = warmth_layer(rgb,1.,bg)
        self.assertIsNotNone(layer)
        output = blend_warmth(rgb,layer)
        mask = layer[1]/65535.
        self.assertGreater(mask[120,320],.9)
        red_blue_change = (output[120,320,0]-output[120,320,2]) - (rgb[120,320,0]-rgb[120,320,2])
        self.assertGreater(red_blue_change,.015)
        np.testing.assert_array_equal(output[20:70],rgb[20:70])
        np.testing.assert_allclose(output @ [.30,.59,.11],rgb @ [.30,.59,.11],atol=2/65535)
        # The old rule loses a streamer whose linear RGB excess was barely detectable.
        linear = np.array([.04,.08,.1])+1.e-7
        old = warm_colour(linear,1.,sky_rgb=[.04,.08,.1])
        self.assertLess(np.max(abs(old-linear)),1.e-10)

    def test_sky_noise_is_rejected_and_strength_changes_colour_not_coverage_extent(self):
        rgb,bg,streamer = scene()
        rng = np.random.default_rng(31)
        noise = rng.normal(0,.002,rgb.shape[:2])
        rgb = set_luminosity(rgb, rgb @ [.30,.59,.11]+noise)
        full = warmth_layer(rgb,1.,bg)
        half = warmth_layer(rgb,.5,bg)
        self.assertLess(np.mean(full[1][20:70]/65535.),.002)
        self.assertLess(np.mean(full[1][20:70]/65535. > .05),.02)
        self.assertGreater(full[1][120,320]/65535,.75)
        np.testing.assert_allclose(half[1].astype(float),full[1]*.5,atol=1.)
        self.assertGreater(half[1][120,320]/65535.,.375)

    def test_bypass_missing_pixels_insufficient_or_rank_deficient_samples(self):
        rgb,bg,_ = scene()
        self.assertIsNone(warmth_layer(rgb,0.,bg))
        self.assertIs(blend_warmth(rgb,None),rgb)
        self.assertIsNone(warmth_layer(rgb,1.,None))
        self.assertIsNone(warmth_layer(rgb,1.,dict(bg,points=[])))
        self.assertIsNone(warmth_layer(rgb,1.,dict(bg,points=[(20,20)]*8)))
        before = rgb.copy();rgb[110:115,300:305] = np.nan
        valid = np.isfinite(rgb).all(axis=-1)
        layer = warmth_layer(rgb,1.,bg,valid=valid)
        self.assertTrue((layer[1][~valid] == 0).all())
        self.assertTrue(np.isnan(blend_warmth(rgb,layer)[~valid]).all())
        np.testing.assert_array_equal(rgb[valid],before[valid])
        for bad in (-1.,2.,np.nan):
            with self.assertRaises(ValueError):warmth_layer(rgb,bad,bg)

    def test_reduced_preview_maps_native_sky_samples_and_streamer_extent(self):
        from core.image_data import resize_observed
        rgb,bg,_ = scene()
        reduced = np.stack([resize_observed(rgb[...,c],(180,120)) for c in range(3)],axis=-1)
        native = warmth_layer(rgb,1.,bg)
        preview = warmth_layer(reduced,1.,bg,native_shape=rgb.shape[:2])
        self.assertGreater(preview[1][60,160]/65535,.9)
        expected = resize_observed(native[1].astype(float)/65535.,(180,120))
        self.assertLess(np.mean(abs(preview[1]/65535.-expected)),.015)

    def test_missing_and_bright_sky_patches_do_not_truncate_streamers(self):
        rgb,bg,_ = scene()
        points = [(20,20),(180,20),(330,20),(20,120),(330,120),
                  (20,220),(180,220),(330,220),(90,220),(260,20)]
        rgb[16:25,16:25] = 1.
        rgb[16:25,176:185] = np.nan
        layer = warmth_layer(rgb,1.,dict(bg,points=points))
        self.assertIsNotNone(layer)
        self.assertGreater(layer[1][120,320]/65535.,.9)
        self.assertEqual(layer[1][20,180],0)

    def test_mask_transition_is_soft_and_full_sky_has_no_layer(self):
        rgb,bg,_ = scene()
        alpha = warmth_layer(rgb,1.,bg)[1].astype(float)/65535.
        self.assertTrue(((alpha>0)&(alpha<1)).any())
        self.assertLess(np.max(abs(np.diff(alpha[120]))),.3)
        flat = np.broadcast_to([.04,.08,.1],rgb.shape).copy()
        self.assertIsNone(warmth_layer(flat,1.,bg))

    def test_faint_streamer_tint_does_not_replace_the_underlying_blue_sky(self):
        rgb,bg,_ = scene()
        output = blend_warmth(rgb,warmth_layer(rgb,1.,bg))
        # The faint streamer adds warm chroma; its brighter sky pedestal stays blue.
        self.assertGreater(output[120,320,2],output[120,320,0])
        self.assertLess(np.max(abs(output[120,320]-rgb[120,320])),.025)

    def test_calibrated_white_corona_is_preserved_exactly_at_zero_warmth(self):
        from core.colour import neutralize_tse
        rgb,bg,_ = scene()
        linear = (rgb @ [.299,.587,.114])[...,None]*np.array([.7,1.,.4])
        calibrated,_ = neutralize_tse(linear,white=None)
        np.testing.assert_allclose(calibrated[...,0],calibrated[...,1],atol=1.e-7)
        np.testing.assert_allclose(calibrated[...,1],calibrated[...,2],atol=1.e-7)
        calibrated *= .5  # Present below clipping; a luminance-1 white cannot take colour.
        self.assertIs(blend_warmth(calibrated,warmth_layer(calibrated,0.,bg)),calibrated)
        warmed = blend_warmth(calibrated,warmth_layer(calibrated,1.,bg))
        self.assertGreater(warmed[120,320,0],warmed[120,320,2])

    def test_whiter_streamer_is_supported_at_lower_contrast_than_blue_sky_noise(self):
        rgb,bg,_ = scene()
        sky = np.array([.04,.08,.1])
        rgb[:] = sky
        noise = np.random.default_rng(12).normal(0,.002,rgb.shape[:2])
        rgb += noise[...,None]
        # Equal brightness, different colour: the neutral feature has corona evidence.
        rgb[100:120,60:80] = (sky @ [.30,.59,.11]+.003)+noise[100:120,60:80,None]
        rgb[100:120,280:300] += .003
        mask = warmth_layer(rgb,1.,bg)[1].astype(float)/65535.
        self.assertGreater(mask[105:115,65:75].mean(),mask[105:115,285:295].mean()+.1)

    def test_editable_warmth_layer_sits_below_unchanged_original_prominences(self):
        from core.filters import FilterWorker
        from core.layer_package import build_layer_package
        rgb,bg,_ = scene()
        source = rgb @ [.299,.587,.114]
        params = dict(zip(('sx','sy','sr'),bg['geometry']))
        original = np.broadcast_to(np.array([65535,1200,0],np.uint16),rgb.shape).copy()
        mask = np.zeros(source.shape,np.uint16);mask[118:123,315:321] = 65535
        package = build_layer_package(FilterWorker(),source,params,{},'original.tif',rgb=rgb,
                    warmth=1.,warmth_background=bg,prominences=(original,mask,{}))
        filters = [layer.record['filter'] for layer in package.layers]
        self.assertLess(filters.index('warmth'),filters.index('prominences'))
        np.testing.assert_array_equal(package.combined[mask>0],original[mask>0])
        layer = package.layers[filters.index('prominences')]
        np.testing.assert_array_equal(layer.mask,mask)
        np.testing.assert_array_equal(np.dstack(layer.rgb),original)
