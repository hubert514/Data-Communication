"""Unit checks for paired experimental validation helpers."""

import importlib.util
from pathlib import Path
import sys
import unittest


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location(
    "experimental_validation", SCRIPTS / "experimental_validation.py"
)
validation = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validation)


class ExperimentalValidationHelpers(unittest.TestCase):
    def test_parse_int_list(self):
        self.assertEqual([1, 2, 3], validation.parse_int_list("1,2, 3"))

    def test_numeric_summary_uses_runs_as_units(self):
        summary = validation.numeric_summary([1.0, 2.0, 3.0])
        self.assertEqual(3, summary["n"])
        self.assertEqual(2.0, summary["mean"])
        self.assertEqual(1.0, summary["sd"])
        self.assertAlmostEqual(-0.4843382083, summary["ci95_lower"])
        self.assertAlmostEqual(4.4843382083, summary["ci95_upper"])
        self.assertEqual("varied", summary["variation_status"])

    def test_identical_runs_are_flagged(self):
        summary = validation.numeric_summary([4.0, 4.0, 4.0])
        self.assertEqual("identical", summary["variation_status"])
        self.assertEqual(0.0, summary["sd"])

    def test_merged_intervals(self):
        self.assertEqual([[1, 4], [8, 10]], validation.merged_intervals([(2, 4), (1, 3), (8, 10)]))


if __name__ == "__main__":
    unittest.main()
