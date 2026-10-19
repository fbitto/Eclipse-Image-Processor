"""Independent quadrature oracle for the published GHS derivative and tails."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import unittest
import numpy as np
from scipy.integrate import quad
from core.ghs import generalized_hyperbolic_stretch as ghs
from core.presentation import apply_ghs, stretch_image


def integral_oracle(x, stretch, sp, b, lp, hp):
    """Integrate the contrast function; do not use the production primitive."""
    d = np.expm1(stretch)
    def density(v):
        t = abs(min(max(v, lp), hp)-sp)
        if b < 0:
            return (1-b*d*t)**(1/b)
        if b == 0:
            return np.exp(-d*t)
        return (1+b*d*t)**(-(1+b)/b)
    def integrate(a, z):
        points = [a]+[v for v in (lp, sp, hp) if a < v < z]+[z]
        return sum(quad(density, lo, hi, epsabs=1e-13, epsrel=1e-12)[0]
                   for lo, hi in zip(points[:-1], points[1:]))
    return integrate(0, x)/integrate(0, 1)


class GHSTests(unittest.TestCase):
    def test_all_branches_match_independent_integrated_derivative(self):
        x = np.array([0., .001, .07, .13, .25, .37, .61, .83, 1.])
        for b in (-5, -2, -1, -.3, 0, .3, 1, 2, 15):
            for stretch in (.001, .7, 3, 5):
                for lp, sp, hp in ((0, 0, 1), (0, .25, 1), (.07, .25, .61), (.25, .25, .25)):
                    with self.subTest(b=b, stretch=stretch, lp=lp, sp=sp, hp=hp):
                        expected = [integral_oracle(v, stretch, sp, b, lp, hp) for v in x]
                        np.testing.assert_allclose(ghs(x, stretch, sp, b, lp, hp), expected, atol=3e-12, rtol=3e-11)

    def test_closed_form_unprotected_special_cases(self):
        x = np.linspace(0, 1, 301); stretch = 2.; d = np.expm1(stretch)
        np.testing.assert_allclose(ghs(x, stretch, 0, -1), np.log1p(d*x)/np.log1p(d), atol=1e-14)
        np.testing.assert_allclose(ghs(x, stretch, 0, 0), -np.expm1(-d*x)/-np.expm1(-d), atol=1e-14)
        np.testing.assert_allclose(ghs(x, stretch, 0, 1), x*(1+d)/(1+d*x), atol=1e-14)

    def test_identity_endpoints_full_parameter_domain_and_nonfinite_mask(self):
        x = np.r_[np.linspace(0, 1, 2001), np.nan]
        for b in (-5, -1.0000000001, -1, -.9999999999, -1e-10, 0, 1e-10, 1, 15):
            for sp in (0, .05, .5, 1):
                np.testing.assert_array_equal(ghs(x, 0, sp, b), x)
                for stretch in (1e-12, .001, 5, 20):
                    for lp, hp in ((0, 1), (sp, sp)):
                        y = ghs(x, stretch, sp, b, lp, hp)
                        self.assertEqual(y[0], 0); self.assertEqual(y[-2], 1)
                        self.assertTrue(np.isnan(y[-1]))
                        self.assertTrue(np.isfinite(y[:-1]).all())
                        self.assertTrue(np.all(np.diff(y[:-1]) >= -2e-15))
        self.assertEqual(ghs(x.astype(np.float32), 2, .1, 2).dtype, np.float64)

    def test_derivatives_are_continuous_and_protection_tails_are_linear(self):
        for b in (-2, -1, 0, 1, 5):
            h = 1e-7; sp, lp, hp = .3, .1, .7
            for join in (lp, sp, hp):
                y = ghs(np.array([join-h, join, join+h]), 2, sp, b, lp, hp)
                self.assertAlmostEqual((y[1]-y[0])/h, (y[2]-y[1])/h, delta=1e-5)
            for interval in ((0, lp), (hp, 1)):
                y = ghs(np.linspace(*interval, 51), 2, sp, b, lp, hp)
                np.testing.assert_allclose(np.diff(y, 2), 0, atol=1e-15)

    def test_limits_in_b_and_small_stretch(self):
        x = np.linspace(0, 1, 501)
        for center in (-1., 0.):
            reference = ghs(x, 2, .2, center, .1, .8)
            for delta in (-1e-9, 1e-9):
                np.testing.assert_allclose(ghs(x, 2, .2, center+delta, .1, .8), reference, atol=2e-9)
        np.testing.assert_allclose(ghs(x, 1e-12, .2, 2), x, atol=1e-12)

    def test_invalid_parameters_and_input_are_rejected_without_clamping(self):
        for kwargs in ({'stretch': -1}, {'stretch': 21}, {'b': -6}, {'b': 16},
                       {'sp': -.1}, {'sp': 1.1}, {'sp': .3, 'lp': .4},
                       {'sp': .3, 'hp': .2}, {'lp': -.1}, {'hp': 1.1}, {'b': np.nan}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                ghs(np.array([0., 1.]), **kwargs)
        for x in ([np.inf], [-.01], [1.01]):
            with self.assertRaises(ValueError): ghs(x)

    def test_presentation_uses_reference_curve_and_separate_linear_adjustment(self):
        a = np.linspace(0, 100, 1001).reshape(1, -1)
        settings = dict(mode='ghs', strength=3., sp=.12, b=-.5, lp=.02, hp=.7)
        expected = ghs(a/100, 3., .12, -.5, .02, .7)
        np.testing.assert_allclose(stretch_image(a, settings), expected, atol=1e-14)
        np.testing.assert_allclose(apply_ghs(a/100, 3., .12, -.5, .1, .02, .7, .9),
                                   np.clip((expected-.1)/.8, 0, 1), atol=1e-14)
        with self.assertRaises(ValueError): apply_ghs(a/100, 2., .1, 0, 1, WP=1)
