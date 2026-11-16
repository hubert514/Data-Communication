"""Unit checks for deterministic mixed-traffic analysis helpers."""

import importlib.util
from pathlib import Path
import unittest


SPEC = importlib.util.spec_from_file_location(
    "mixed_traffic_checkpoint",
    Path(__file__).resolve().parents[1] / "scripts/mixed_traffic_checkpoint.py",
)
checkpoint = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checkpoint)


class MixedTrafficAnalysis(unittest.TestCase):
    def test_nearest_rank_percentile(self):
        self.assertIsNone(checkpoint.percentile_nearest_rank([], 0.95))
        self.assertEqual(1, checkpoint.percentile_nearest_rank([1], 0.95))
        self.assertEqual(5, checkpoint.percentile_nearest_rank([1, 2, 3, 4, 5], 0.95))
        self.assertEqual(2, checkpoint.percentile_nearest_rank([4, 1, 3, 2], 0.50))

    def test_jain_fairness(self):
        self.assertIsNone(checkpoint.jain([]))
        self.assertIsNone(checkpoint.jain([0, 0]))
        self.assertAlmostEqual(1.0, checkpoint.jain([4, 4, 4, 4]))
        self.assertAlmostEqual(0.5, checkpoint.jain([1, 0]))

    def test_allocation_batches_are_order_independent_within_ppdu(self):
        rows = [
            {"decision_id": "1", "aid": "2", "ru_type": "52-tones", "ru_index": "2", "mcs": "5", "nss": "1"},
            {"decision_id": "1", "aid": "1", "ru_type": "52-tones", "ru_index": "1", "mcs": "5", "nss": "1"},
            {"decision_id": "2", "aid": "3", "ru_type": "242-tones", "ru_index": "1", "mcs": "5", "nss": "1"},
        ]
        batches = checkpoint.allocation_batches(rows, "decision_id")
        self.assertEqual("1", batches[0][0][0])
        self.assertEqual("2", batches[0][1][0])
        self.assertEqual(1, len(batches[1]))


if __name__ == "__main__":
    unittest.main()
