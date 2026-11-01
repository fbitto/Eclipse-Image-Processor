"""The threaded AEL edge-aware WOW is bit-identical to the single-thread code it replaced."""
import unittest
from unittest.mock import patch

import numpy as np

import core.ael_wow as wow
from core.parallelism import filter_budget


def _old_b3_normalized(a, m, step):
    """The previous whole-frame implementation, kept verbatim as the reference."""
    def conv(z):
        tmp = np.zeros_like(z)
        for kk, kv in zip(range(-2, 3), wow._B3K): tmp += kv * wow._shifted(z, kk * step, 0)
        out = np.zeros_like(z)
        for kk, kv in zip(range(-2, 3), wow._B3K): out += kv * wow._shifted(tmp, kk * step, 1)
        return out
    return conv(np.where(m, a, 0).astype(np.float32)) / np.maximum(conv(m.astype(np.float32)), 1e-20)


def _old_paired_b3_step(c, m, step, bilateral=False, guide=None, rows=128):
    """The previous single-thread loop over row blocks, kept verbatim as the reference."""
    _B3K, _TAPS, _rows_shifted = wow._B3K, wow._TAPS, wow._rows_shifted
    h, w = c.shape; out = np.zeros_like(c); compl = np.zeros_like(c); pair = np.zeros_like(c)
    for y0 in range(0, h, rows):
        y1 = min(h, y0 + rows); ctr = c[y0:y1]; mc = m[y0:y1]; ctg = ctr if guide is None else guide[y0:y1]
        V, VG, VAL = {}, {}, {}
        for dy, dx in _TAPS:
            V[dy, dx] = _rows_shifted(c, y0, y1, dy * step, dx * step, 0)
            VG[dy, dx] = V[dy, dx] if guide is None else _rows_shifted(guide, y0, y1, dy * step, dx * step, 0)
            VAL[dy, dx] = _rows_shifted(m, y0, y1, dy * step, dx * step, False)
        G = {}
        for t in _TAPS:
            u = (-t[0], -t[1])
            G[t] = mc.astype(np.float32) if t == (0, 0) else G[u] if u in G else (VAL[t] & VAL[u] & mc).astype(np.float32)
        if bilateral:
            mo = np.zeros_like(ctr); mo2 = np.zeros_like(ctr); ma = np.zeros_like(ctr)
            for dy, dx in _TAPS:
                k = float(_B3K[dy + 2] * _B3K[dx + 2]); g = G[dy, dx]; dl = np.where(g > 0, VG[dy, dx] - ctg, 0)
                mo += k * g * dl; mo2 += k * g * dl * dl; ma += k * g
            mean = mo / np.maximum(ma, 1e-20); vv = np.maximum(mo2 / np.maximum(ma, 1e-20) - mean * mean, 1e-20).astype(np.float64)
        num = np.zeros_like(ctr); den = np.zeros_like(ctr); ks = np.zeros_like(ctr); kn = np.zeros_like(ctr)
        for dy, dx in _TAPS:
            k = float(_B3K[dy + 2] * _B3K[dx + 2]); g = G[dy, dx]; v = np.where(g > 0, V[dy, dx], 0)
            if (dy, dx) != (0, 0): kn += k * g
            if bilateral:
                vg = v if guide is None else np.where(g > 0, VG[dy, dx], 0)
                wt = k * g.astype(np.float64) * np.exp(-.5 * (ctg.astype(np.float64) - vg) ** 2 / vv)
            else:
                wt = k * g
            num += wt * (v - ctr); den += wt; ks += k * g
        out[y0:y1] = ctr + num / np.maximum(den, 1e-20); compl[y0:y1] = ks; pair[y0:y1] = kn > 0
    return out, compl, pair


class ThreadedWowTests(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(11)
        yy, xx = np.mgrid[:300, :257]
        r = np.hypot(xx - 131.4, yy - 147.8)
        self.image = ((1 + 40*np.exp(-r/25) + .3*np.sin(xx/3)*np.exp(-r/60))
                      * np.exp(.05*rng.standard_normal(r.shape))).astype(np.float32)
        self.image[r < 20] = 0                                  # an unobserved lunar disk
        self.image[:, 250:] = np.nan                            # a straight data edge
        self.image[10:14, 30:200] = np.nan
        self.valid = np.isfinite(self.image) & (self.image > 0)

    def test_any_thread_count_matches_the_previous_code_bit_for_bit(self):
        with patch.object(wow, '_paired_b3_step', _old_paired_b3_step), \
             patch.object(wow, '_b3_normalized', _old_b3_normalized):
            expected = wow.wow_edge_aware(self.image, self.valid, n_scales=8)
        for workers in (1, 3, 8):
            with self.subTest(workers=workers), filter_budget(workers):
                np.testing.assert_array_equal(wow.wow_edge_aware(self.image, self.valid, n_scales=8), expected)

    def test_parts_match_the_previous_code_at_steps_wider_than_a_block(self):
        c = np.where(self.valid, self.image, 0).astype(np.float32)
        for step in (1, 16, 128, 256):
            with self.subTest(step=step), filter_budget(8):
                np.testing.assert_array_equal(wow._b3_normalized(c*c, self.valid, step),
                                              _old_b3_normalized(c*c, self.valid, step))
                guide = _old_paired_b3_step(c, self.valid, step)[0]
                for new, old in zip(wow._paired_b3_step(c, self.valid, step, True, guide),
                                    _old_paired_b3_step(c, self.valid, step, True, guide)):
                    np.testing.assert_array_equal(new, old)


if __name__ == '__main__':
    unittest.main()
