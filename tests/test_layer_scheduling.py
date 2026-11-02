"""Layer batches start the longest layer first and share the cores among the layers still running."""
from threading import Event
import time
import unittest
from unittest.mock import patch

import numpy as np

from core.layer_engine import COSTS, LayerEngine
from core.parallelism import CPU_CORES, filter_budget, filter_cpu_budget


class SchedulingTests(unittest.TestCase):
    def test_a_callable_budget_is_asked_again_at_every_call(self):
        value = [3]
        with filter_budget(lambda: value[0]):
            self.assertEqual(filter_cpu_budget(), 3)
            value[0] = 11
            self.assertEqual(filter_cpu_budget(), 11)
            value[0] = 0
            self.assertEqual(filter_cpu_budget(), 1)
        with filter_budget(5):
            self.assertEqual(filter_cpu_budget(), 5)

    def _requests(self):
        params = {}
        return [(name, variant, params, True) for name, variant in
                (('fnrgf', None), ('mgn', None), ('wow', None), ('achf', 'ael_iso_04'), ('achf', 'ael_angular_4'))]

    def test_longest_layer_starts_first_and_later_takes_the_free_cores(self):
        started, budgets = [], {}
        other_started, wow_measured, others_done = Event(), Event(), Event()
        def layer(engine, worker, source, p, name, variant=None, calculate=True):
            if not calculate:
                return None
            key = variant or name
            started.append(key)
            if key == 'wow':
                other_started.wait(5)                 # both places of the batch are busy
                budgets['wow'] = [filter_cpu_budget()]
                wow_measured.set()
                others_done.wait(5)                   # every other layer has finished
                time.sleep(.05)
                budgets['wow'].append(filter_cpu_budget())
            else:
                other_started.set()
                wow_measured.wait(5)
                budgets[key] = filter_cpu_budget()
                if len(budgets) == 5:
                    others_done.set()
            return dict(image=None)
        source = np.ones((64, 64), np.float32)
        with patch('core.layer_engine.requests', return_value=self._requests()), \
             patch('core.layer_engine.layer_workers', return_value=2), \
             patch.object(LayerEngine, 'layer', layer):
            LayerEngine().prepare(None, source, {})
        expected = sorted(('fnrgf', 'mgn', 'wow', 'ael_iso_04', 'ael_angular_4'), key=lambda k: -COSTS[k])
        self.assertEqual(expected[0], 'wow')
        # The two places start together; after that the batch keeps the longest-first order.
        self.assertEqual(set(started[:2]), set(expected[:2]))
        self.assertEqual(started[2:], expected[2:])
        self.assertEqual(budgets['wow'], [max(1, CPU_CORES//2), CPU_CORES])

if __name__ == '__main__':
    unittest.main()
