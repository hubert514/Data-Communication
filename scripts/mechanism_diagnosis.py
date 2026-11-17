#!/usr/bin/env python3
"""Run, validate, and aggregate observation-only scheduler mechanism traces."""

import argparse
from collections import defaultdict
import csv
import hashlib
import json
from pathlib import Path
import statistics
import sys

import experimental_validation as validation
import mixed_traffic_checkpoint as checkpoint


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RAW_ROOT = ROOT / ".local" / "mechanism-diagnosis"
DEFAULT_NONREG_ROOT = ROOT / ".local" / "instrumentation-nonregression"
DEFAULT_BASELINE_ROOT = ROOT / ".local" / "experimental-validation"
DEFAULT_EVIDENCE = ROOT / "docs" / "evidence" / "b-mechanism-diagnosis-01"
SCHEDULERS = ("rr", "queue-age")
CLASSES = ("LL", "BE")


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def write_csv(path, fieldnames, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def instrumented_path(raw_root, load, scheduler, rng_run):
    return raw_root / f"be{load}mbps" / f"{scheduler}-run{rng_run}"


def run_matrix(args):
    raw_root = args.raw_root.resolve()
    nonreg_root = args.nonreg_root.resolve()
    rows = []
    for load in args.loads:
        for rng_run in args.rng_runs:
            for scheduler in SCHEDULERS:
                nonreg_path = nonreg_root / (
                    "rr-be8-run1" if scheduler == "rr" else "queue-age-be8-run1"
                )
                if load == 8 and rng_run == 1 and (nonreg_path / "mechanism.csv").is_file():
                    path = nonreg_path
                    source = "reused_nonregression_run"
                else:
                    path = instrumented_path(raw_root, load, scheduler, rng_run)
                    source = "mechanism_diagnosis_run"
                    if not validation.valid_completed_run(
                        path,
                        load,
                        scheduler,
                        rng_run,
                        args.seed,
                        args.duration,
                        args.drain_time,
                    ) or not (path / "mechanism.csv").is_file():
                        namespace = argparse.Namespace(
                            scheduler=scheduler,
                            run_id=f"MECH-BE{load}-{scheduler}-run{rng_run}",
                            output=path,
                            duration=args.duration,
                            drain_time=args.drain_time,
                            be_rate=f"{load}Mbps",
                            seed=args.seed,
                            rng_run=rng_run,
                        )
                        print(f"RUN mechanism BE={load} / RNG {rng_run} / {scheduler}", flush=True)
                        checkpoint.run_experiment(namespace)
                metadata = checkpoint.read_json(path / "run-metadata.json")
                report = checkpoint.analyze(path, write_outputs=False)
                if not (path / "mechanism.csv").is_file():
                    raise RuntimeError(f"missing mechanism trace: {path}")
                rows.append(
                    {
                        "be_load_mbps_per_flow": load,
                        "rng_seed": args.seed,
                        "rng_run": rng_run,
                        "scheduler": scheduler,
                        "run_id": metadata["run_id"],
                        "status": report["validation"]["status"],
                        "source_finished_at": metadata["finished_at"],
                        "source": source,
                        "raw_path": validation.relative(path),
                        "mechanism_rows": len(read_csv(path / "mechanism.csv")),
                        "reproduction_command": validation.reproduction_command(
                            path,
                            load,
                            scheduler,
                            rng_run,
                            args.seed,
                            args.duration,
                            args.drain_time,
                        ),
                    }
                )
    raw_root.mkdir(parents=True, exist_ok=True)
    write_csv(raw_root / "mechanism-experiment-matrix.csv", list(rows[0]), rows)
    matrix = {
        "schema": "mechanism-diagnosis-matrix-v1",
        "generated_at": max(row["source_finished_at"] for row in rows),
        "loads_mbps_per_be_flow": args.loads,
        "rng_runs": args.rng_runs,
        "run_count": len(rows),
        "all_passed": all(row["status"] == "PASSED" for row in rows),
        "runs": rows,
    }
    (raw_root / "mechanism-experiment-matrix.json").write_text(
        json.dumps(matrix, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"run_count": len(rows), "all_passed": matrix["all_passed"]}, indent=2))


def normalized_rows(path, excluded):
    rows = read_csv(path)
    fields = [name for name in rows[0] if name not in excluded] if rows else []
    return fields, [tuple(row[name] for name in fields) for row in rows]


def compare_nonregression(args):
    baseline_root = args.baseline_root.resolve()
    instrumented_root = args.instrumented_root.resolve()
    rows = []
    for scheduler in SCHEDULERS:
        baseline = validation.output_path(baseline_root, 8, scheduler, 1)
        instrumented = instrumented_root / (
            "rr-be8-run1" if scheduler == "rr" else "queue-age-be8-run1"
        )
        for filename in (
            "mapping.csv",
            "packet-events.csv",
            "scheduler.csv",
            "phy.csv",
            "packet-summary.csv",
            "flow-summary.csv",
            "class-summary.csv",
            "queue-age-summary.csv",
        ):
            left_fields, left = normalized_rows(baseline / filename, {"run_id", "mpdu_count"})
            right_fields, right = normalized_rows(
                instrumented / filename, {"run_id", "mpdu_count"}
            )
            common = [field for field in left_fields if field in right_fields]
            left_common = [
                tuple(row[left_fields.index(field)] for field in common) for row in left
            ]
            right_common = [
                tuple(row[right_fields.index(field)] for field in common) for row in right
            ]
            rows.append(
                {
                    "scheduler": scheduler,
                    "artifact": filename,
                    "baseline_rows": len(left),
                    "instrumented_rows": len(right),
                    "common_fields": "|".join(common),
                    "exact_common_rows_equal": str(left_common == right_common).lower(),
                }
            )
    output = args.output.resolve()
    write_csv(output, list(rows[0]), rows)
    result = {
        "schema": "instrumentation-nonregression-v1",
        "all_exact": all(row["exact_common_rows_equal"] == "true" for row in rows),
        "comparisons": rows,
        "excluded_fields": ["run_id", "new mpdu_count field absent from legacy PHY trace"],
    }
    output.with_suffix(".json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"comparisons": len(rows), "all_exact": result["all_exact"]}, indent=2))
    if not result["all_exact"]:
        raise RuntimeError("instrumentation changed an existing observable")


def mean(values):
    return statistics.fmean(values) if values else None


def p95(values):
    return checkpoint.percentile_nearest_rank(values, 0.95) if values else None


def analyze_run(item):
    path = ROOT / item["raw_path"]
    if not path.is_dir():
        path = Path(item["raw_path"])
    report = checkpoint.analyze(path, write_outputs=False)
    mechanism = read_csv(path / "mechanism.csv")
    phy = report["phy"]
    if not phy or "mpdu_count" not in phy[0]:
        raise RuntimeError(f"instrumented PHY trace lacks mpdu_count: {path}")

    pre_by_decision = defaultdict(dict)
    accepted_by_decision = defaultdict(list)
    post_by_decision = defaultdict(list)
    for row in mechanism:
        decision = row["decision_id"]
        if row["phase"] == "credit_order_before_selection":
            pre_by_decision[decision][row["aid"]] = int(row["order"])
        elif row["phase"] == "candidate_candidate_accepted":
            accepted_by_decision[decision].append(row)
        elif row["phase"] == "credit_order_after_update":
            post_by_decision[decision].append(row)

    final_by_decision = defaultdict(list)
    for row in report["scheduler"]:
        if row["phase"] == "final":
            final_by_decision[row["decision_id"]].append(row)

    reordered = []
    selected_ranks = []
    for decision, final_rows in final_by_decision.items():
        ranks = pre_by_decision[decision]
        accepted = sorted(
            accepted_by_decision[decision], key=lambda row: int(row["order"])
        )
        accepted_aids = [row["aid"] for row in accepted]
        credit_ordered = sorted(accepted_aids, key=lambda aid: ranks[aid])
        reordered.append(accepted_aids != credit_ordered)
        selected_ranks.extend(ranks[row["aid"]] for row in final_rows)

    base = {
        "be_load_mbps_per_flow": int(item["be_load_mbps_per_flow"]),
        "rng_run": int(item["rng_run"]),
        "scheduler": item["scheduler"],
        "run_id": item["run_id"],
        "raw_path": item["raw_path"],
        "decision_count": len(final_by_decision),
        "reordered_decisions": sum(reordered),
        "reordered_decision_share": mean([float(value) for value in reordered]),
        "selected_pre_credit_rank_mean": mean(selected_ranks),
        "selected_pre_credit_rank_p95": p95(selected_ranks),
    }
    rows = []
    for traffic_class in CLASSES:
        accepted = [
            row
            for rows_for_decision in accepted_by_decision.values()
            for row in rows_for_decision
            if row["traffic_class"] == traffic_class
        ]
        phy_rows = [row for row in phy if row["traffic_class"] == traffic_class]
        post_rows = [
            row
            for rows_for_decision in post_by_decision.values()
            for row in rows_for_decision
            if row["traffic_class"] == traffic_class
        ]
        queue_packets = [int(row["queue_packets"]) for row in accepted]
        queue_bytes = [int(row["queue_bytes"]) for row in accepted]
        mpdu_counts = [int(row["mpdu_count"]) for row in phy_rows]
        psdu_bytes = [int(row["psdu_bytes"]) for row in phy_rows]
        selected_credits = [float(row["credit_us"]) for row in post_rows if row["selected"] == "1"]
        unselected_credits = [
            float(row["credit_us"]) for row in post_rows if row["selected"] == "0"
        ]
        rows.append(
            {
                **base,
                "traffic_class": traffic_class,
                "accepted_samples": len(accepted),
                "queue_packets_mean": mean(queue_packets),
                "queue_packets_p95": p95(queue_packets),
                "queue_bytes_mean": mean(queue_bytes),
                "queue_bytes_p95": p95(queue_bytes),
                "phy_allocations": len(phy_rows),
                "mpdu_count_mean": mean(mpdu_counts),
                "mpdu_count_p95": p95(mpdu_counts),
                "aggregated_allocation_share": mean(
                    [float(value > 1) for value in mpdu_counts]
                ),
                "psdu_bytes_mean": mean(psdu_bytes),
                "psdu_bytes_p95": p95(psdu_bytes),
                "post_credit_selected_mean_us": mean(selected_credits),
                "post_credit_unselected_mean_us": mean(unselected_credits),
            }
        )
    return rows


def sequence_batches(path):
    scheduler = read_csv(path / "scheduler.csv")
    phy = read_csv(path / "phy.csv")
    mechanism = read_csv(path / "mechanism.csv")
    final = defaultdict(list)
    for row in scheduler:
        if row["phase"] == "final":
            final[row["decision_id"]].append(
                (row["aid"], row["ru_type"], row["ru_index"], row["mcs"], row["nss"])
            )
    phy_batches = defaultdict(list)
    phy_times = {}
    for row in phy:
        phy_times[row["phy_sequence"]] = row["time_ns"]
        phy_batches[row["phy_sequence"]].append(
            (
                row["aid"],
                row["ru_type"],
                row["ru_index"],
                row["mcs"],
                row["nss"],
                row["mpdu_count"],
                row["psdu_bytes"],
            )
        )
    credit_order = defaultdict(list)
    for row in mechanism:
        if row["phase"] == "credit_order_before_selection":
            credit_order[row["decision_id"]].append((int(row["order"]), row["aid"]))
    credit_batches = [
        tuple(aid for _, aid in sorted(rows)) for rows in credit_order.values()
    ]
    return (
        list(final.values()),
        list(phy_batches.values()),
        list(phy_times.values()),
        credit_batches,
    )


def compare_policy_sequences(matrix):
    by_key = {
        (int(item["be_load_mbps_per_flow"]), int(item["rng_run"]), item["scheduler"]): item
        for item in matrix["runs"]
    }
    rows = []
    for load in matrix["loads_mbps_per_be_flow"]:
        for rng_run in matrix["rng_runs"]:
            data = {}
            for scheduler in SCHEDULERS:
                item = by_key[(load, rng_run, scheduler)]
                path = ROOT / item["raw_path"]
                if not path.is_dir():
                    path = Path(item["raw_path"])
                data[scheduler] = sequence_batches(path)
            rr_final, rr_phy, rr_times, rr_credit = data["rr"]
            qa_final, qa_phy, qa_times, qa_credit = data["queue-age"]
            compared = min(len(rr_final), len(qa_final))
            exact_final = sum(rr_final[i] == qa_final[i] for i in range(compared))
            same_aid_set = sum(
                {row[0] for row in rr_final[i]} == {row[0] for row in qa_final[i]}
                for i in range(compared)
            )
            exact_phy = sum(rr_phy[i] == qa_phy[i] for i in range(compared))
            same_time = sum(rr_times[i] == qa_times[i] for i in range(compared))
            same_credit_order = sum(
                rr_credit[i] == qa_credit[i] for i in range(compared)
            )
            rows.append(
                {
                    "be_load_mbps_per_flow": load,
                    "rng_run": rng_run,
                    "rr_ppdus": len(rr_final),
                    "queue_age_ppdus": len(qa_final),
                    "compared_prefix_ppdus": compared,
                    "exact_final_batch_share": exact_final / compared if compared else None,
                    "same_selected_aid_set_share": same_aid_set / compared if compared else None,
                    "exact_phy_batch_with_aggregation_share": exact_phy / compared if compared else None,
                    "exact_phy_timestamp_share": same_time / compared if compared else None,
                    "same_pre_selection_credit_order_share": same_credit_order / compared
                    if compared
                    else None,
                    "comparison_scope": "index-aligned full sequence"
                    if len(rr_final) == len(qa_final)
                    else "index-aligned common prefix; PPDU counts differ",
                }
            )
    return rows


MECHANISM_METRICS = (
    "reordered_decision_share",
    "selected_pre_credit_rank_mean",
    "queue_packets_mean",
    "queue_bytes_mean",
    "mpdu_count_mean",
    "aggregated_allocation_share",
    "psdu_bytes_mean",
    "post_credit_selected_mean_us",
    "post_credit_unselected_mean_us",
)


def aggregate(args):
    matrix = checkpoint.read_json(args.matrix.resolve())
    per_run = []
    for item in matrix["runs"]:
        per_run.extend(analyze_run(item))
    per_run.sort(
        key=lambda row: (
            row["be_load_mbps_per_flow"],
            row["rng_run"],
            SCHEDULERS.index(row["scheduler"]),
            CLASSES.index(row["traffic_class"]),
        )
    )
    paired = []
    stats = []
    for load in sorted({row["be_load_mbps_per_flow"] for row in per_run}):
        for traffic_class in CLASSES:
            for rng_run in sorted({row["rng_run"] for row in per_run}):
                pair = {
                    row["scheduler"]: row
                    for row in per_run
                    if row["be_load_mbps_per_flow"] == load
                    and row["traffic_class"] == traffic_class
                    and row["rng_run"] == rng_run
                }
                for metric in MECHANISM_METRICS:
                    rr = pair["rr"][metric]
                    qa = pair["queue-age"][metric]
                    paired.append(
                        {
                            "be_load_mbps_per_flow": load,
                            "rng_run": rng_run,
                            "traffic_class": traffic_class,
                            "metric": metric,
                            "rr": rr,
                            "queue_age": qa,
                            "queue_age_minus_rr": qa - rr,
                        }
                    )
            for scheduler in SCHEDULERS:
                selected = [
                    row
                    for row in per_run
                    if row["be_load_mbps_per_flow"] == load
                    and row["traffic_class"] == traffic_class
                    and row["scheduler"] == scheduler
                ]
                for metric in MECHANISM_METRICS:
                    stats.append(
                        {
                            "summary_type": "scheduler",
                            "be_load_mbps_per_flow": load,
                            "traffic_class": traffic_class,
                            "scheduler": scheduler,
                            "metric": metric,
                            **validation.numeric_summary([row[metric] for row in selected]),
                        }
                    )
            for metric in MECHANISM_METRICS:
                values = [
                    row["queue_age_minus_rr"]
                    for row in paired
                    if row["be_load_mbps_per_flow"] == load
                    and row["traffic_class"] == traffic_class
                    and row["metric"] == metric
                ]
                stats.append(
                    {
                        "summary_type": "paired_difference",
                        "be_load_mbps_per_flow": load,
                        "traffic_class": traffic_class,
                        "scheduler": "queue-age-minus-rr",
                        "metric": metric,
                        **validation.numeric_summary(values),
                    }
                )
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    sequence_rows = compare_policy_sequences(matrix)
    write_csv(output / "mechanism-per-run-summary.csv", list(per_run[0]), per_run)
    write_csv(output / "mechanism-paired-comparison.csv", list(paired[0]), paired)
    write_csv(output / "mechanism-statistical-summary.csv", list(stats[0]), stats)
    write_csv(output / "cross-policy-sequence.csv", list(sequence_rows[0]), sequence_rows)
    source_matrix = args.matrix.resolve().with_suffix(".csv")
    if source_matrix.is_file():
        (output / "mechanism-experiment-matrix.csv").write_text(
            source_matrix.read_text(encoding="utf-8"), encoding="utf-8"
        )
    summary = {
        "schema": "mechanism-diagnosis-statistics-v1",
        "generated_at": matrix["generated_at"],
        "run_count": len(matrix["runs"]),
        "matched_pairs": len(matrix["runs"]) // 2,
        "loads_mbps_per_be_flow": matrix["loads_mbps_per_be_flow"],
        "rng_runs": matrix["rng_runs"],
        "all_runs_passed": matrix["all_passed"],
        "statistical_unit": "one matched RNG run; candidate and allocation samples are summarized within each run first",
        "ci_method": "two-sided 95% Student t interval across three matched runs",
        "interpretation_warning": "n=3 intervals and sequence shares are descriptive; no automatic significance or generality claim is made",
        "queue_occupancy_semantics": "const per-STA/TID MAC queue counters sampled only when the existing candidate loop accepted a queue-head MPDU; samples are decision-weighted, not independent replications",
        "aggregation_semantics": "MPDU count and PSDU bytes from the already-constructed PHY PSDU map for actual DL HE-MU user allocations",
        "credit_reorder_semantics": "accepted candidate AID order differs from those same accepted AIDs sorted by the scheduler credit order recorded before queue-age sorting",
        "cross_policy_sequence": sequence_rows,
        "statistics": stats,
    }
    (output / "mechanism-statistical-summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    checksums = []
    for path in sorted(output.iterdir()):
        if path.is_file() and path.name != "checksums.sha256":
            checksums.append(f"{sha256(path)}  {path.name}")
    (output / "checksums.sha256").write_text("\n".join(checksums) + "\n", encoding="utf-8")
    print(json.dumps({"runs": len(matrix["runs"]), "output": validation.relative(output)}, indent=2))


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    matrix = subparsers.add_parser("run-matrix")
    matrix.add_argument("--raw-root", type=Path, default=DEFAULT_RAW_ROOT)
    matrix.add_argument("--nonreg-root", type=Path, default=DEFAULT_NONREG_ROOT)
    matrix.add_argument("--loads", type=validation.parse_int_list, default=[8, 12])
    matrix.add_argument("--rng-runs", type=validation.parse_int_list, default=[1, 2, 3])
    matrix.add_argument("--seed", type=int, default=1)
    matrix.add_argument("--duration", default="5s")
    matrix.add_argument("--drain-time", default="200ms")
    matrix.set_defaults(func=run_matrix)
    nonreg = subparsers.add_parser("compare-nonregression")
    nonreg.add_argument("--baseline-root", type=Path, default=DEFAULT_BASELINE_ROOT)
    nonreg.add_argument("--instrumented-root", type=Path, default=DEFAULT_NONREG_ROOT)
    nonreg.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_EVIDENCE / "instrumentation-nonregression.csv",
    )
    nonreg.set_defaults(func=compare_nonregression)
    aggregate_parser = subparsers.add_parser("aggregate")
    aggregate_parser.add_argument(
        "--matrix", type=Path, default=DEFAULT_RAW_ROOT / "mechanism-experiment-matrix.json"
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
