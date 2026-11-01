"""Layer fusion and the presentation finish in threaded row strips are bit-identical to whole-frame code."""
import unittest
from unittest.mock import patch

import numpy as np

from core.layer_engine import LayerEngine, blend
from core.parallelism import filter_budget
from core.presentation_edges import finish_presentation


def _old_finish(image, alpha):
    result=np.nan_to_num(image,nan=0.,posinf=0.,neginf=0.)
    if alpha is not None:
        coverage=1-alpha.astype(float)/65535
        result=result*(coverage[...,None] if result.ndim==3 else coverage)
    return result


class ThreadedFusionTests(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(31)
        self.shape = (700, 333)
        self.base = rng.integers(0, 65536, self.shape).astype(float)/65535
        self.layers = [dict(image=rng.integers(0, 65536, self.shape, dtype=np.uint16),
                            alpha=rng.integers(0, 65536, self.shape, dtype=np.uint16), mode=mode, mapping={})
                       for mode in ('Overlay', 'Multiply', 'Linear Light', 'Overlay')]

    def test_render_matches_blending_the_whole_frame_in_order(self):
        names = [('mgn', None), ('wow', None), ('tangential', None), ('larson_sekanina', None)]
        params = dict(mgn_enabled=True, wow_enabled=True, tangential_enabled=True, larson_sekanina_enabled=True,
                      mgn_opacity=40, wow_opacity=70, tangential_opacity=100, larson_sekanina_opacity=25)
        requested = [(name, variant, params, True) for name, variant in names]
        engine = LayerEngine()
        lookup = {name: layer for (name, _), layer in zip(names, self.layers)}
        with patch('core.layer_engine.requests', return_value=requested), \
             patch('core.layer_engine.opacity', side_effect=lambda name, p, enabled=True: p[name+'_opacity']/100), \
             patch.object(LayerEngine, 'layer', side_effect=lambda w, s, p, name, variant, calculate=True: lookup[name]):
            expected = self.base.copy()
            for (name, _), layer in zip(names, self.layers):
                amount = round(params[name+'_opacity']/100*.9*255)/255
                expected = blend(expected, layer['image'].astype(float)/65535, layer['alpha'].astype(float)/65535,
                                 layer['mode'], amount)
            expected = expected.astype(np.float32)
            for workers in (1, 8):
                with self.subTest(workers=workers), filter_budget(workers):
                    actual = engine.render(None, np.ones(self.shape, np.float32), params, dict(blend=.9),
                                           calculate=False, base=self.base)
                    self.assertEqual(actual.dtype, np.float32)
                    np.testing.assert_array_equal(actual, expected)

    def test_finish_matches_the_whole_frame(self):
        rng = np.random.default_rng(8)
        alpha = rng.integers(0, 65536, self.shape, dtype=np.uint16)
        for image in (rng.random(self.shape).astype(np.float32), rng.random((*self.shape, 3))):
            image[3:9, 4:20] = np.nan
            for edge in (None, alpha):
                with self.subTest(ndim=image.ndim, edge=edge is not None), filter_budget(8):
                    expected = _old_finish(image, edge)
                    actual = finish_presentation(image, edge)
                    self.assertEqual(actual.dtype, expected.dtype)
                    np.testing.assert_array_equal(actual, expected)


if __name__ == '__main__':
    unittest.main()
