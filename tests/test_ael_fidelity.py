"""Known-signal controls for AEL 1.3.5 ports; no upstream runtime required."""
import unittest
from types import SimpleNamespace
import numpy as np
from core.ael_wow import ael_wow_layer
from core.ael_achf import display_detail, display_detail_rings


class FidelityTests(unittest.TestCase):
    def test_guided_wow_keeps_faint_pattern_sign(self):
        y,x=np.mgrid[:640,:768]
        r=np.hypot(x-310.3,y-370.7)
        th=(-np.arctan2(x-310.3,-(y-370.7))) % (2*np.pi)
        valid=r>63
        pattern=.005*np.sin(37*th+np.random.default_rng(20261005).uniform(-np.pi,np.pi))*np.exp(-((r-160)/65)**4)
        corona=(1+.3*np.cos(3*th)+.1*np.sin(7*th)).astype(np.float32)
        p=dict(sx=310.3,sy=370.7,sr=60,wow_scales=8)
        base,_=ael_wow_layer(corona,p,valid)
        injected,_=ael_wow_layer((corona*np.exp(pattern)).astype(np.float32),p,valid)
        sel=valid&(r>90)&(r<260)
        self.assertGreater(np.corrcoef((injected-base)[sel],pattern[sel])[0,1],.2)

    def test_ring_display_preserves_inner_contrast_and_missing_values(self):
        y,x=np.mgrid[:320,:320];r=np.hypot(x-159.5,y-159.5)
        th=np.arctan2(y-159.5,x-159.5)
        valid=r>30
        detail=(np.sin(37*th)*np.exp(-(r-30)/15)).astype(np.float32)
        geometry=SimpleNamespace(radius_map=lambda:r)
        global_layer,_=display_detail(detail,valid)
        layer,info=display_detail_rings(detail,valid,geometry)
        inner=valid&(r<60)
        self.assertGreater(np.mean(global_layer[inner]>=.99),.1)
        self.assertLess(np.mean(layer[inner]>=.99),.01)
        self.assertTrue(np.isnan(layer[~valid]).all())
        poisoned=detail.copy();poisoned[~valid]=1e20
        np.testing.assert_array_equal(layer,display_detail_rings(poisoned,valid,geometry)[0])
        wedge=valid&(abs(th)<.01)
        fallback,info=display_detail_rings(detail,wedge,geometry)
        np.testing.assert_array_equal(fallback,display_detail(detail,wedge)[0])
        self.assertIn('fewer than three',info['display'])
