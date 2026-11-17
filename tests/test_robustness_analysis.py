"""Unit checks for robustness and scheduler-diagnosis helpers."""

import argparse
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))


def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


drain = load("drain_sensitivity")
mechanism = load("mechanism_diagnosis")


class RobustnessAnalysisHelpers(unittest.TestCase):
    def test_duplicate_drain_durations_are_rejected(self):
        with self.assertRaises(argparse.ArgumentTypeError):
            drain.parse_drain_list("200,500,200")

    def test_drain_metrics_keep_windows_separate(self):
        report = {
            "mapping": [
                {
                    "flow_id": "1",
                    "traffic_class": "BE",
                    "app_start_ns": "1000000000",
                    "app_stop_ns": "6000000000",
                }
            ],
            "packets": [
                {
                    "flow_id": "1",
                    "status": "delivered",
                    "rx_time_ns": "5900000000",
                    "bytes": "1000",
                    "delay_ms": "1.0",
                },
                {
                    "flow_id": "1",
                    "status": "delivered",
                    "rx_time_ns": "6100000000",
                    "bytes": "1000",
                    "delay_ms": "101.0",
                },
                {
                    "flow_id": "1",
                    "status": "lost_by_sim_stop",
                    "rx_time_ns": "",
                    "bytes": "1000",
                    "delay_ms": "",
                },
            ],
        }
        result = drain.summarize_class(report, "BE", 200)
        self.assertEqual(1, result["rx_by_app_stop_packets"])
        self.assertEqual(1, result["rx_during_drain_packets"])
        self.assertEqual(1, result["undelivered_at_sim_end_packets"])
        self.assertAlmostEqual(1 / 3, result["pdr_at_app_stop"])
        self.assertAlmostEqual(2 / 3, result["pdr_at_sim_end"])
        self.assertAlmostEqual(0.0032, result["final_delivery_offered_interval_mbps"])
        self.assertAlmostEqual(0.016 / 5.2, result["receive_window_goodput_mbps"])

    def test_trace_normalization_excludes_run_id(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "trace.csv"
            drain.write_csv(
                path,
                ["run_id", "time_ns", "aid"],
                [{"run_id": "A", "time_ns": "1", "aid": "7"}],
            )
            fields, rows = drain.normalized_trace(path)
        self.assertEqual(["time_ns", "aid"], fields)
        self.assertEqual([("1", "7")], rows)

    def test_mechanism_normalization_can_ignore_new_columns(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "phy.csv"
            mechanism.write_csv(
                path,
                ["run_id", "aid", "mpdu_count"],
                [{"run_id": "new", "aid": "3", "mpdu_count": "2"}],
            )
            fields, rows = mechanism.normalized_rows(
                path, {"run_id", "mpdu_count"}
            )
        self.assertEqual(["aid"], fields)
        self.assertEqual([("3",)], rows)


if __name__ == "__main__":
    unittest.main()
