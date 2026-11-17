#!/usr/bin/env python3
"""Run and aggregate matched receive-drain sensitivity experiments."""

import argparse
import csv
import hashlib
import json
from pathlib import Path
import statistics
import sys

import experimental_validation as validation
import mixed_traffic_checkpoint as checkpoint


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RAW_ROOT = ROOT / ".local" / "drain-sensitivity"
DEFAULT_EXISTING_ROOT = ROOT / ".local" / "experimental-validation"
DEFAULT_EVIDENCE = ROOT / "docs" / "evidence" / "b-drain-sensitivity-01"
SCHEDULERS = ("rr", "queue-age")
CLASSES = ("LL", "BE", "ALL")


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_csv(path, fieldnames, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def parse_drain_list(value):
    drains = validation.parse_int_list(value)
    if len(set(drains)) != len(drains):
        raise argparse.ArgumentTypeError("drain durations must be unique")
    return drains


def run_id(load, drain_ms, scheduler, rng_run):
    label = "RR" if scheduler == "rr" else "QueueAge"
    return f"DRAIN-BE{load}-D{drain_ms}-{label}-run{rng_run}"


def new_output_path(raw_root, load, drain_ms, scheduler, rng_run):
    return raw_root / f"be{load}mbps" / f"drain{drain_ms}ms" / f"{scheduler}-run{rng_run}"


def run_matrix(args):
    raw_root = args.raw_root.resolve()
    existing_root = args.existing_root.resolve()
    raw_root.mkdir(parents=True, exist_ok=True)
    rows = []
    for drain_ms in args.drains_ms:
        drain_time = f"{drain_ms}ms"
        for rng_run in args.rng_runs:
            for scheduler in SCHEDULERS:
                existing_path = validation.output_path(
                    existing_root, args.load, scheduler, rng_run
                )
                if drain_ms == 200 and validation.valid_completed_run(
                    existing_path,
                    args.load,
                    scheduler,
                    rng_run,
                    args.seed,
                    args.duration,
                    drain_time,
                ):
                    path = existing_path
                    source = "reused_existing_200ms"
                else:
                    path = new_output_path(
                        raw_root, args.load, drain_ms, scheduler, rng_run
                    )
                    source = "drain_sensitivity_run"
                    if not validation.valid_completed_run(
                        path,
                        args.load,
                        scheduler,
                        rng_run,
                        args.seed,
                        args.duration,
                        drain_time,
                    ):
                        namespace = argparse.Namespace(
                            scheduler=scheduler,
                            run_id=run_id(args.load, drain_ms, scheduler, rng_run),
                            output=path,
                            duration=args.duration,
                            drain_time=drain_time,
                            be_rate=f"{args.load}Mbps",
                            seed=args.seed,
                            rng_run=rng_run,
                        )
                        print(
                            f"RUN drain={drain_ms} ms / RNG {rng_run} / {scheduler}",
                            flush=True,
                        )
                        checkpoint.run_experiment(namespace)
                metadata = checkpoint.read_json(path / "run-metadata.json")
                result = checkpoint.analyze(path, write_outputs=False)
                rows.append(
                    {
                        "be_load_mbps_per_flow": args.load,
                        "drain_ms": drain_ms,
                        "rng_seed": args.seed,
                        "rng_run": rng_run,
                        "scheduler": scheduler,
                        "run_id": metadata["run_id"],
                        "status": result["validation"]["status"],
                        "source_finished_at": metadata["finished_at"],
                        "source": source,
                        "raw_path": validation.relative(path),
                        "dl_he_mu_transmissions": result["validation"]["counts"][
                            "dl_he_mu_transmissions"
                        ],
                        "reproduction_command": validation.reproduction_command(
                            path,
                            args.load,
                            scheduler,
                            rng_run,
                            args.seed,
                            args.duration,
                            drain_time,
                        ),
                    }
                )
    matrix = {
        "schema": "drain-sensitivity-matrix-v1",
        "generated_at": max(row["source_finished_at"] for row in rows),
        "raw_root": validation.relative(raw_root),
        "load_mbps_per_be_flow": args.load,
        "drains_ms": args.drains_ms,
        "rng_seed": args.seed,
        "rng_runs": args.rng_runs,
        "duration": args.duration,
        "run_count": len(rows),
        "all_passed": all(row["status"] == "PASSED" for row in rows),
        "runs": rows,
    }
    write_csv(raw_root / "drain-experiment-matrix.csv", list(rows[0]), rows)
    (raw_root / "drain-experiment-matrix.json").write_text(
        json.dumps(matrix, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"run_count": len(rows), "all_passed": matrix["all_passed"]}, indent=2))


def summarize_class(report, traffic_class, drain_ms):
    mapping = report["mapping"]
    selected_flows = {
        row["flow_id"]
        for row in mapping
        if traffic_class == "ALL" or row["traffic_class"] == traffic_class
    }
    rows = [row for row in report["packets"] if row["flow_id"] in selected_flows]
    app_start_ns = min(int(row["app_start_ns"]) for row in mapping)
    app_stop_ns = max(int(row["app_stop_ns"]) for row in mapping)
    offered_duration_s = (app_stop_ns - app_start_ns) / 1e9
    receive_window_s = offered_duration_s + drain_ms / 1000
    received = [row for row in rows if row["status"] == "delivered"]
    received_by_stop = [row for row in received if int(row["rx_time_ns"]) <= app_stop_ns]
    received_during_drain = [row for row in received if int(row["rx_time_ns"]) > app_stop_ns]
    undelivered = [row for row in rows if row["status"] != "delivered"]
    delays = [float(row["delay_ms"]) for row in received]
    tx_bytes = sum(int(row["bytes"]) for row in rows)
    received_bytes = sum(int(row["bytes"]) for row in received)
    received_by_stop_bytes = sum(int(row["bytes"]) for row in received_by_stop)
    drain_bytes = sum(int(row["bytes"]) for row in received_during_drain)
    undelivered_bytes = sum(int(row["bytes"]) for row in undelivered)
    return {
        "traffic_class": traffic_class,
        "tx_packets": len(rows),
        "tx_bytes": tx_bytes,
        "rx_by_app_stop_packets": len(received_by_stop),
        "rx_by_app_stop_bytes": received_by_stop_bytes,
        "rx_during_drain_packets": len(received_during_drain),
        "rx_during_drain_bytes": drain_bytes,
        "rx_by_sim_end_packets": len(received),
        "rx_by_sim_end_bytes": received_bytes,
        "undelivered_at_sim_end_packets": len(undelivered),
        "undelivered_at_sim_end_bytes": undelivered_bytes,
        "pdr_at_app_stop": len(received_by_stop) / len(rows) if rows else None,
        "pdr_at_sim_end": len(received) / len(rows) if rows else None,
        "app_stop_delivery_mbps": received_by_stop_bytes * 8 / offered_duration_s / 1e6,
        "final_delivery_offered_interval_mbps": received_bytes
        * 8
        / offered_duration_s
        / 1e6,
        "receive_window_goodput_mbps": received_bytes * 8 / receive_window_s / 1e6,
        "mean_delay_ms": statistics.fmean(delays) if delays else None,
        "p95_delay_ms": checkpoint.percentile_nearest_rank(delays, 0.95),
        "max_delay_ms": max(delays) if delays else None,
        "application_undelivered_backlog_packets": len(undelivered),
        "application_undelivered_backlog_bytes": undelivered_bytes,
    }


def normalized_trace(path, excluded=("run_id",)):
    rows = checkpoint.read_csv(path)
    fields = [field for field in rows[0] if field not in excluded] if rows else []
    return fields, [tuple(row[field] for field in fields) for row in rows]


def compare_drain_traces(matrix, reference_drain_ms=200):
    by_key = {
        (int(item["drain_ms"]), int(item["rng_run"]), item["scheduler"]): item
        for item in matrix["runs"]
    }
    rows = []
    for rng_run in matrix["rng_runs"]:
        for scheduler in SCHEDULERS:
            reference_item = by_key[(reference_drain_ms, rng_run, scheduler)]
            reference_path = ROOT / reference_item["raw_path"]
            if not reference_path.is_dir():
                reference_path = Path(reference_item["raw_path"])
            for drain_ms in matrix["drains_ms"]:
                if drain_ms == reference_drain_ms:
                    continue
                comparison_item = by_key[(drain_ms, rng_run, scheduler)]
                comparison_path = ROOT / comparison_item["raw_path"]
                if not comparison_path.is_dir():
                    comparison_path = Path(comparison_item["raw_path"])
                for filename in (
                    "mapping.csv",
                    "packet-events.csv",
                    "scheduler.csv",
                    "phy.csv",
                ):
                    reference_fields, reference_rows = normalized_trace(
                        reference_path / filename
                    )
                    comparison_fields, comparison_rows = normalized_trace(
                        comparison_path / filename
                    )
                    rows.append(
                        {
                            "rng_run": rng_run,
                            "scheduler": scheduler,
                            "reference_drain_ms": reference_drain_ms,
                            "comparison_drain_ms": drain_ms,
                            "artifact": filename,
                            "reference_rows": len(reference_rows),
                            "comparison_rows": len(comparison_rows),
                            "fields_equal": str(
                                reference_fields == comparison_fields
                            ).lower(),
                            "exact_rows_equal_without_run_id": str(
                                reference_fields == comparison_fields
                                and reference_rows == comparison_rows
                            ).lower(),
                        }
                    )
    return rows


METRICS = (
    "pdr_at_app_stop",
    "pdr_at_sim_end",
    "app_stop_delivery_mbps",
    "final_delivery_offered_interval_mbps",
    "receive_window_goodput_mbps",
    "mean_delay_ms",
    "p95_delay_ms",
    "rx_during_drain_packets",
    "undelivered_at_sim_end_packets",
)


def aggregate(args):
    matrix_path = args.matrix.resolve()
    matrix = checkpoint.read_json(matrix_path)
    output = args.output.resolve()
    per_run = []
    verification = []
    metadata_by_key = {}
    for item in matrix["runs"]:
        path = ROOT / item["raw_path"]
        if not path.is_dir():
            path = Path(item["raw_path"])
        metadata = checkpoint.read_json(path / "run-metadata.json")
        report = checkpoint.analyze(path, write_outputs=False)
        key = (int(item["drain_ms"]), int(item["rng_run"]), item["scheduler"])
        metadata_by_key[key] = metadata
        base = {
            "be_load_mbps_per_flow": int(item["be_load_mbps_per_flow"]),
            "drain_ms": int(item["drain_ms"]),
            "rng_run": int(item["rng_run"]),
            "scheduler": item["scheduler"],
            "run_id": item["run_id"],
            "raw_path": item["raw_path"],
        }
        for traffic_class in CLASSES:
            per_run.append(
                {**base, **summarize_class(report, traffic_class, int(item["drain_ms"]))}
            )
        verification.append(
            {
                **base,
                "validation_status": report["validation"]["status"],
                "stored_checksums_match": str(
                    validation.stored_checksums_match(path, metadata)
                ).lower(),
                "all_packet_delays_nonnegative": str(
                    report["validation"]["checks"]["all_packet_delays_nonnegative"]
                ).lower(),
                "scheduler_final_equals_phy_sequence": str(
                    report["validation"]["checks"]["scheduler_final_equals_phy_sequence"]
                ).lower(),
                "legal_20mhz_ru_types": str(
                    report["validation"]["checks"]["legal_20mhz_ru_types"]
                ).lower(),
            }
        )
    per_run.sort(
        key=lambda row: (
            row["drain_ms"],
            row["rng_run"],
            SCHEDULERS.index(row["scheduler"]),
            CLASSES.index(row["traffic_class"]),
        )
    )
    paired = []
    stats = []
    drains = sorted({row["drain_ms"] for row in per_run})
    rng_runs = sorted({row["rng_run"] for row in per_run})
    for drain_ms in drains:
        for rng_run in rng_runs:
            configurations = [
                metadata_by_key[(drain_ms, rng_run, scheduler)]["configuration"]
                for scheduler in SCHEDULERS
            ]
            if configurations[0] != configurations[1]:
                raise RuntimeError(
                    f"uncontrolled pair at drain {drain_ms} ms, RngRun {rng_run}"
                )
            for traffic_class in CLASSES:
                pair = {
                    row["scheduler"]: row
                    for row in per_run
                    if row["drain_ms"] == drain_ms
                    and row["rng_run"] == rng_run
                    and row["traffic_class"] == traffic_class
                }
                for metric in METRICS:
                    rr = pair["rr"][metric]
                    qa = pair["queue-age"][metric]
                    paired.append(
                        {
                            "drain_ms": drain_ms,
                            "rng_run": rng_run,
                            "traffic_class": traffic_class,
                            "metric": metric,
                            "rr": rr,
                            "queue_age": qa,
                            "queue_age_minus_rr": qa - rr,
                        }
                    )
        for traffic_class in CLASSES:
            for scheduler in SCHEDULERS:
                selected = [
                    row
                    for row in per_run
                    if row["drain_ms"] == drain_ms
                    and row["traffic_class"] == traffic_class
                    and row["scheduler"] == scheduler
                ]
                for metric in METRICS:
                    stats.append(
                        {
                            "summary_type": "scheduler",
                            "drain_ms": drain_ms,
                            "traffic_class": traffic_class,
                            "scheduler": scheduler,
                            "metric": metric,
                            **validation.numeric_summary([row[metric] for row in selected]),
                        }
                    )
            for metric in METRICS:
                differences = [
                    row["queue_age_minus_rr"]
                    for row in paired
                    if row["drain_ms"] == drain_ms
                    and row["traffic_class"] == traffic_class
                    and row["metric"] == metric
                ]
                stats.append(
                    {
                        "summary_type": "paired_difference",
                        "drain_ms": drain_ms,
                        "traffic_class": traffic_class,
                        "scheduler": "queue-age-minus-rr",
                        "metric": metric,
                        **validation.numeric_summary(differences),
                    }
                )
    output.mkdir(parents=True, exist_ok=True)
    write_csv(output / "drain-per-run-summary.csv", list(per_run[0]), per_run)
    write_csv(output / "drain-paired-comparison.csv", list(paired[0]), paired)
    write_csv(output / "drain-statistical-summary.csv", list(stats[0]), stats)
    write_csv(output / "drain-verification.csv", list(verification[0]), verification)
    trace_equivalence = compare_drain_traces(matrix)
    write_csv(
        output / "drain-trace-equivalence.csv",
        list(trace_equivalence[0]),
        trace_equivalence,
    )
    source_csv = matrix_path.with_suffix(".csv")
    if source_csv.is_file():
        (output / "drain-experiment-matrix.csv").write_text(
            source_csv.read_text(encoding="utf-8"), encoding="utf-8"
        )
    summary = {
        "schema": "drain-sensitivity-statistics-v1",
        "generated_at": matrix["generated_at"],
        "measurement_semantics": {
            "pdr_at_app_stop": "packets received no later than application stop divided by generated packets",
            "pdr_at_sim_end": "packets received by app stop plus drain divided by generated packets",
            "app_stop_delivery_mbps": "bytes received by app stop normalized to the 5-second offered interval",
            "final_delivery_offered_interval_mbps": "all bytes received by simulation end normalized to the 5-second offered interval",
            "receive_window_goodput_mbps": "all bytes received by simulation end normalized to 5 seconds plus drain",
            "application_undelivered_backlog": "generated application packets not observed at the sink by simulation end; not a direct MAC queue measurement",
        },
        "run_count": len(verification),
        "paired_runs": len(drains) * len(rng_runs),
        "drains_ms": drains,
        "rng_runs": rng_runs,
        "all_validations_passed": all(
            row["validation_status"] == "PASSED" for row in verification
        ),
        "all_stored_checksums_match": all(
            row["stored_checksums_match"] == "true" for row in verification
        ),
        "all_longer_drain_traces_equal_200ms": all(
            row["exact_rows_equal_without_run_id"] == "true"
            for row in trace_equivalence
        ),
        "trace_equivalence_scope": "mapping, packet events, scheduler decisions, and PHY records; run_id excluded",
        "statistics": stats,
    }
    (output / "drain-statistical-summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    checksum_rows = []
    for path in sorted(output.iterdir()):
        if path.is_file() and path.name != "checksums.sha256":
            checksum_rows.append(f"{sha256(path)}  {path.name}")
    (output / "checksums.sha256").write_text("\n".join(checksum_rows) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "run_count": len(verification),
                "paired_runs": summary["paired_runs"],
                "all_validations_passed": summary["all_validations_passed"],
                "output": validation.relative(output),
            },
            indent=2,
        )
    )


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    matrix = subparsers.add_parser("run-matrix")
    matrix.add_argument("--raw-root", type=Path, default=DEFAULT_RAW_ROOT)
    matrix.add_argument("--existing-root", type=Path, default=DEFAULT_EXISTING_ROOT)
    matrix.add_argument("--load", type=int, default=12)
    matrix.add_argument("--drains-ms", type=parse_drain_list, default=[200, 500, 1000])
    matrix.add_argument("--rng-runs", type=validation.parse_int_list, default=[1, 2, 3])
    matrix.add_argument("--seed", type=int, default=1)
    matrix.add_argument("--duration", default="5s")
    matrix.set_defaults(func=run_matrix)
    aggregate_parser = subparsers.add_parser("aggregate")
    aggregate_parser.add_argument(
        "--matrix", type=Path, default=DEFAULT_RAW_ROOT / "drain-experiment-matrix.json"
    )
    aggregate_parser.add_argument("--output", type=Path, default=DEFAULT_EVIDENCE)
    aggregate_parser.set_defaults(func=aggregate)
    return parser.parse_args()


def main():
    args = parse_args()
    try:
        args.func(args)
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
