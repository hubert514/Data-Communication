#!/usr/bin/env python3
"""Run and aggregate paired RR/queue-age mixed-traffic experiments."""

import argparse
from collections import defaultdict
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys

import mixed_traffic_checkpoint as checkpoint


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RAW_ROOT = ROOT / ".local" / "experimental-validation"
DEFAULT_EVIDENCE = ROOT / "docs" / "evidence" / "b-experimental-validation-01"
SCHEDULERS = ("rr", "queue-age")
CLASSES = ("LL", "BE", "ALL")
T_CRITICAL_95 = {
    1: 12.706,
    2: 4.303,
    3: 3.182,
    4: 2.776,
    5: 2.571,
    6: 2.447,
    7: 2.365,
    8: 2.306,
    9: 2.262,
    10: 2.228,
    11: 2.201,
    12: 2.179,
    13: 2.160,
    14: 2.145,
    15: 2.131,
    16: 2.120,
    17: 2.110,
    18: 2.101,
    19: 2.093,
    20: 2.086,
    21: 2.080,
    22: 2.074,
    23: 2.069,
    24: 2.064,
    25: 2.060,
    26: 2.056,
    27: 2.052,
    28: 2.048,
    29: 2.045,
    30: 2.042,
}


def parse_int_list(value):
    values = []
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        values.append(int(part))
    if not values or any(item <= 0 for item in values):
        raise argparse.ArgumentTypeError("expected a comma-separated list of positive integers")
    return values


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


def relative(path):
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path.resolve())


def run_name(load, scheduler, rng_run):
    label = "RR" if scheduler == "rr" else "QueueAge"
    return f"EV-BE{load}-{label}-run{rng_run}"


def output_path(raw_root, load, scheduler, rng_run):
    return raw_root / f"be{load}mbps" / f"{scheduler}-run{rng_run}"


def valid_completed_run(path, load, scheduler, rng_run, seed, duration, drain_time):
    metadata_path = path / "run-metadata.json"
    if not metadata_path.is_file():
        return False
    metadata = checkpoint.read_json(metadata_path)
    config = metadata.get("configuration", {})
    return (
        metadata.get("status") == "PASSED"
        and metadata.get("scheduler") == scheduler
        and config.get("be_rate") == f"{load}Mbps"
        and config.get("seed") == seed
        and config.get("rng_run") == rng_run
        and config.get("duration") == duration
        and config.get("drain_time") == drain_time
        and (path / "validation.json").is_file()
        and checkpoint.read_json(path / "validation.json").get("status") == "PASSED"
    )


def reproduction_command(path, load, scheduler, rng_run, seed, duration, drain_time):
    return (
        "python3 scripts/mixed_traffic_checkpoint.py run "
        f"--scheduler {scheduler} --run-id {run_name(load, scheduler, rng_run)} "
        f"--output {relative(path)} --be-rate {load}Mbps --duration {duration} "
        f"--drain-time {drain_time} --seed {seed} --rng-run {rng_run}"
    )


def run_matrix(args):
    raw_root = args.raw_root.resolve()
    raw_root.mkdir(parents=True, exist_ok=True)
    matrix_rows = []
    for load in args.loads:
        for rng_run in args.rng_runs:
            for scheduler in SCHEDULERS:
                path = output_path(raw_root, load, scheduler, rng_run)
                reused = valid_completed_run(
                    path,
                    load,
                    scheduler,
                    rng_run,
                    args.seed,
                    args.duration,
                    args.drain_time,
                )
                command = reproduction_command(
                    path, load, scheduler, rng_run, args.seed, args.duration, args.drain_time
                )
                if not reused:
                    namespace = argparse.Namespace(
                        scheduler=scheduler,
                        run_id=run_name(load, scheduler, rng_run),
                        output=path,
                        duration=args.duration,
                        drain_time=args.drain_time,
                        be_rate=f"{load}Mbps",
                        seed=args.seed,
                        rng_run=rng_run,
                    )
                    print(f"RUN {load} Mbps / RNG {rng_run} / {scheduler}", flush=True)
                    checkpoint.run_experiment(namespace)
                metadata = checkpoint.read_json(path / "run-metadata.json")
                validation = checkpoint.read_json(path / "validation.json")
                matrix_rows.append(
                    {
                        "be_load_mbps_per_flow": load,
                        "rng_seed": args.seed,
                        "rng_run": rng_run,
                        "scheduler": scheduler,
                        "run_id": metadata["run_id"],
                        "status": metadata["status"],
                        "source_finished_at": metadata["finished_at"],
                        "raw_path": relative(path),
                        "dl_he_mu_transmissions": validation["counts"]["dl_he_mu_transmissions"],
                        "dl_he_mu_user_allocations": validation["counts"]["dl_he_mu_user_allocations"],
                        "reproduction_command": command,
                    }
                )
    write_csv(raw_root / "experiment-matrix.csv", list(matrix_rows[0]), matrix_rows)
    manifest = {
        "schema": "experimental-validation-matrix-v1",
        "generated_at": max(row["source_finished_at"] for row in matrix_rows),
        "raw_root": relative(raw_root),
        "loads_mbps_per_be_flow": args.loads,
        "rng_seed": args.seed,
        "rng_runs": args.rng_runs,
        "schedulers": list(SCHEDULERS),
        "duration": args.duration,
        "drain_time": args.drain_time,
        "run_count": len(matrix_rows),
        "all_passed": all(row["status"] == "PASSED" for row in matrix_rows),
        "runs": matrix_rows,
    }
    (raw_root / "experiment-matrix.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"run_count": len(matrix_rows), "all_passed": manifest["all_passed"]}, indent=2))


def numeric_summary(values):
    n = len(values)
    mean = statistics.fmean(values) if values else None
    sd = statistics.stdev(values) if n >= 2 else None
    lower = upper = None
    if n >= 3:
        critical = T_CRITICAL_95.get(n - 1, 1.96)
        half_width = critical * sd / math.sqrt(n)
        lower, upper = mean - half_width, mean + half_width
    return {
        "n": n,
        "mean": mean,
        "sd": sd,
        "ci95_lower": lower,
        "ci95_upper": upper,
        "variation_status": "identical" if n > 1 and len(set(values)) == 1 else "varied",
    }


def merged_intervals(intervals):
    result = []
    for start, stop in sorted(intervals):
        if not result or start > result[-1][1]:
            result.append([start, stop])
        else:
            result[-1][1] = max(result[-1][1], stop)
    return result


def in_intervals(value, intervals):
    # The intervals are few (the P95 LL packet tail), so a linear scan is clearer
    # and fast enough for this checkpoint data set.
    for start, stop in intervals:
        if value < start:
            return False
        if value <= stop:
            return True
    return False


def scheduler_behavior(report):
    final_rows = [row for row in report["scheduler"] if row["phase"] == "final"]
    accepted = [
        row
        for row in report["scheduler"]
        if row["phase"] == "candidate"
        and row["eligibility_status"] == "candidate_accepted"
        and row["mpdu_age_ns"]
    ]
    total_final = len(final_rows)
    behavior = {}
    station_rows = []
    for traffic_class in ("LL", "BE"):
        selected = [row for row in final_rows if row["traffic_class"] == traffic_class]
        times = sorted({int(row["time_ns"]) for row in selected})
        gaps = [(right - left) / 1e6 for left, right in zip(times, times[1:])]
        ages = [
            int(row["mpdu_age_ns"]) / 1e6
            for row in accepted
            if row["traffic_class"] == traffic_class
        ]
        behavior[f"selected_{traffic_class.lower()}_allocations"] = len(selected)
        behavior[f"selected_{traffic_class.lower()}_share"] = (
            len(selected) / total_final if total_final else None
        )
        behavior[f"{traffic_class.lower()}_service_opportunities"] = len(times)
        behavior[f"{traffic_class.lower()}_mean_service_gap_ms"] = (
            statistics.fmean(gaps) if gaps else None
        )
        behavior[f"{traffic_class.lower()}_p95_service_gap_ms"] = (
            checkpoint.percentile_nearest_rank(gaps, 0.95) if gaps else None
        )
        behavior[f"{traffic_class.lower()}_max_service_gap_ms"] = max(gaps) if gaps else None
        behavior[f"{traffic_class.lower()}_candidate_mean_age_ms"] = (
            statistics.fmean(ages) if ages else None
        )
        behavior[f"{traffic_class.lower()}_candidate_p95_age_ms"] = (
            checkpoint.percentile_nearest_rank(ages, 0.95) if ages else None
        )
    station_groups = defaultdict(list)
    for row in final_rows:
        station_groups[(row["aid"], row["traffic_class"])].append(row)
    for (aid, traffic_class), rows in sorted(
        station_groups.items(), key=lambda item: int(item[0][0])
    ):
        station_rows.append(
            {
                "aid": aid,
                "traffic_class": traffic_class,
                "selected_allocations": len(rows),
                "selected_share": len(rows) / total_final if total_final else None,
            }
        )

    ll_packets = [
        row for row in report["packets"] if row["traffic_class"] == "LL" and row["delay_ms"]
    ]
    delays = [float(row["delay_ms"]) for row in ll_packets]
    threshold = checkpoint.percentile_nearest_rank(delays, 0.95)
    tail_packets = [row for row in ll_packets if float(row["delay_ms"]) >= threshold]
    intervals = merged_intervals(
        [(int(row["tx_time_ns"]), int(row["rx_time_ns"])) for row in tail_packets]
    )
    tail_final = [row for row in final_rows if in_intervals(int(row["time_ns"]), intervals)]
    tail_accepted = [row for row in accepted if in_intervals(int(row["time_ns"]), intervals)]
    tail_be = sum(row["traffic_class"] == "BE" for row in tail_final)
    behavior.update(
        {
            "ll_p95_delay_threshold_ms": threshold,
            "ll_tail_packet_count": len(tail_packets),
            "ll_tail_merged_wait_intervals": len(intervals),
            "tail_window_final_allocations": len(tail_final),
            "tail_window_be_selected_share": tail_be / len(tail_final) if tail_final else None,
            "tail_window_ll_candidate_mean_age_ms": statistics.fmean(
                int(row["mpdu_age_ns"]) / 1e6
                for row in tail_accepted
                if row["traffic_class"] == "LL"
            )
            if any(row["traffic_class"] == "LL" for row in tail_accepted)
            else None,
            "tail_window_be_candidate_mean_age_ms": statistics.fmean(
                int(row["mpdu_age_ns"]) / 1e6
                for row in tail_accepted
                if row["traffic_class"] == "BE"
            )
            if any(row["traffic_class"] == "BE" for row in tail_accepted)
            else None,
        }
    )
    return behavior, station_rows


def discover_runs(raw_root):
    records = []
    for metadata_path in sorted(raw_root.glob("**/run-metadata.json")):
        path = metadata_path.parent
        metadata = checkpoint.read_json(metadata_path)
        if metadata.get("status") != "PASSED":
            continue
        config = metadata.get("configuration", {})
        rate = config.get("be_rate", "")
        if not rate.endswith("Mbps"):
            continue
        records.append(
            {
                "path": path,
                "metadata": metadata,
                "load": int(rate[:-4]),
                "rng_run": int(config["rng_run"]),
                "scheduler": metadata["scheduler"],
            }
        )
    return records


def stored_checksums_match(path, metadata):
    checksums = metadata.get("checksums", {})
    return bool(checksums) and all(
        (path / name).is_file() and sha256(path / name) == expected
        for name, expected in checksums.items()
    )


METRICS = (
    "ll_throughput_mbps",
    "be_throughput_mbps",
    "all_throughput_mbps",
    "ll_mean_delay_ms",
    "ll_p95_delay_ms",
    "be_mean_delay_ms",
    "be_p95_delay_ms",
    "ll_pdr",
    "be_pdr",
    "ll_jain_throughput",
    "be_jain_throughput",
    "ll_candidate_mean_age_ms",
    "be_candidate_mean_age_ms",
    "selected_ll_share",
    "selected_be_share",
    "ll_mean_service_gap_ms",
    "be_mean_service_gap_ms",
    "ll_p95_service_gap_ms",
    "be_p95_service_gap_ms",
)


def aggregate(args):
    raw_root = args.raw_root.resolve()
    output = args.output.resolve()
    records = discover_runs(raw_root)
    if not records:
        raise RuntimeError(f"no completed experiments found under {raw_root}")
    per_run = []
    station_rows = []
    behavior_rows = []
    verification_rows = []
    for record in records:
        report = checkpoint.analyze(record["path"], write_outputs=False)
        classes = {row["traffic_class"]: row for row in report["classes"]}
        queue = {row["traffic_class"]: row for row in report["queue_age"]}
        behavior, stations = scheduler_behavior(report)
        base = {
            "be_load_mbps_per_flow": record["load"],
            "rng_run": record["rng_run"],
            "scheduler": record["scheduler"],
            "run_id": record["metadata"]["run_id"],
            "raw_path": relative(record["path"]),
        }
        row = dict(base)
        for traffic_class in CLASSES:
            prefix = traffic_class.lower()
            row[f"{prefix}_throughput_mbps"] = float(classes[traffic_class]["throughput_mbps"])
            row[f"{prefix}_mean_delay_ms"] = float(classes[traffic_class]["mean_delay_ms"])
            row[f"{prefix}_p95_delay_ms"] = float(classes[traffic_class]["p95_delay_ms"])
            row[f"{prefix}_pdr"] = float(classes[traffic_class]["pdr"])
            row[f"{prefix}_jain_throughput"] = float(classes[traffic_class]["jain_throughput"])
            row[f"{prefix}_candidate_mean_age_ms"] = float(queue[traffic_class]["mean_age_ms"])
            row[f"{prefix}_candidate_p95_age_ms"] = float(queue[traffic_class]["p95_age_ms"])
        row.update(behavior)
        row["dl_he_mu_transmissions"] = report["validation"]["counts"]["dl_he_mu_transmissions"]
        row["dl_he_mu_user_allocations"] = report["validation"]["counts"]["dl_he_mu_user_allocations"]
        per_run.append(row)
        behavior_rows.append({**base, **behavior})
        station_rows.extend({**base, **station} for station in stations)
        verification_rows.append(
            {
                **base,
                "validation_status": report["validation"]["status"],
                "stored_checksums_match": str(
                    stored_checksums_match(record["path"], record["metadata"])
                ).lower(),
                "exact_reproduction_command_recorded": str(
                    bool(record["metadata"].get("command_display"))
                ).lower(),
                **{name: str(value).lower() for name, value in report["validation"]["checks"].items()},
            }
        )

    per_run.sort(
        key=lambda row: (
            row["be_load_mbps_per_flow"],
            row["rng_run"],
            SCHEDULERS.index(row["scheduler"]),
        )
    )
    behavior_rows.sort(
        key=lambda row: (
            row["be_load_mbps_per_flow"],
            row["rng_run"],
            SCHEDULERS.index(row["scheduler"]),
        )
    )
    station_rows.sort(
        key=lambda row: (
            row["be_load_mbps_per_flow"],
            row["rng_run"],
            SCHEDULERS.index(row["scheduler"]),
            int(row["aid"]),
        )
    )
    verification_rows.sort(
        key=lambda row: (
            row["be_load_mbps_per_flow"],
            row["rng_run"],
            SCHEDULERS.index(row["scheduler"]),
        )
    )

    keys = {(row["be_load_mbps_per_flow"], row["rng_run"]) for row in per_run}
    metadata_by_key = {
        (record["load"], record["rng_run"], record["scheduler"]): record["metadata"]
        for record in records
    }
    paired_rows = []
    incomplete = []
    for load, rng_run in sorted(keys):
        pair = {
            row["scheduler"]: row
            for row in per_run
            if row["be_load_mbps_per_flow"] == load and row["rng_run"] == rng_run
        }
        if set(pair) != set(SCHEDULERS):
            incomplete.append({"load": load, "rng_run": rng_run, "found": sorted(pair)})
            continue
        if (
            metadata_by_key[(load, rng_run, "rr")]["configuration"]
            != metadata_by_key[(load, rng_run, "queue-age")]["configuration"]
        ):
            raise RuntimeError(
                f"uncontrolled pair at BE load {load} Mbps, RngRun {rng_run}"
            )
        for metric in METRICS:
            rr = pair["rr"][metric]
            qa = pair["queue-age"][metric]
            paired_rows.append(
                {
                    "be_load_mbps_per_flow": load,
                    "rng_run": rng_run,
                    "metric": metric,
                    "rr": rr,
                    "queue_age": qa,
                    "queue_age_minus_rr": qa - rr,
                    "queue_age_over_rr": qa / rr if rr != 0 else "",
                    "percent_change": (qa - rr) / rr * 100 if rr != 0 else "",
                }
            )

    stats_rows = []
    for load in sorted({row["be_load_mbps_per_flow"] for row in per_run}):
        for scheduler in SCHEDULERS:
            selected = [
                row
                for row in per_run
                if row["be_load_mbps_per_flow"] == load and row["scheduler"] == scheduler
            ]
            for metric in METRICS:
                summary = numeric_summary([row[metric] for row in selected])
                stats_rows.append(
                    {
                        "summary_type": "scheduler",
                        "be_load_mbps_per_flow": load,
                        "scheduler": scheduler,
                        "metric": metric,
                        **summary,
                    }
                )
        for metric in METRICS:
            values = [
                row["queue_age_minus_rr"]
                for row in paired_rows
                if row["be_load_mbps_per_flow"] == load and row["metric"] == metric
            ]
            stats_rows.append(
                {
                    "summary_type": "paired_difference",
                    "be_load_mbps_per_flow": load,
                    "scheduler": "queue-age-minus-rr",
                    "metric": metric,
                    **numeric_summary(values),
                }
            )
            ratios = [
                row["queue_age_over_rr"]
                for row in paired_rows
                if row["be_load_mbps_per_flow"] == load
                and row["metric"] == metric
                and row["queue_age_over_rr"] != ""
            ]
            stats_rows.append(
                {
                    "summary_type": "paired_ratio",
                    "be_load_mbps_per_flow": load,
                    "scheduler": "queue-age-over-rr",
                    "metric": metric,
                    **numeric_summary(ratios),
                }
            )

    load_rows = []
    core_metrics = (
        "ll_throughput_mbps",
        "be_throughput_mbps",
        "all_throughput_mbps",
        "ll_mean_delay_ms",
        "ll_p95_delay_ms",
        "be_mean_delay_ms",
        "be_p95_delay_ms",
        "ll_pdr",
        "be_pdr",
    )
    for load in sorted({row["be_load_mbps_per_flow"] for row in per_run}):
        for scheduler in SCHEDULERS:
            row = {"be_load_mbps_per_flow": load, "scheduler": scheduler}
            for metric in core_metrics:
                stat = next(
                    item
                    for item in stats_rows
                    if item["summary_type"] == "scheduler"
                    and item["be_load_mbps_per_flow"] == load
                    and item["scheduler"] == scheduler
                    and item["metric"] == metric
                )
                row[f"{metric}_mean"] = stat["mean"]
                row[f"{metric}_sd"] = stat["sd"]
            load_rows.append(row)

    def paired_mean(load, metric):
        values = [
            row["queue_age_minus_rr"]
            for row in paired_rows
            if row["be_load_mbps_per_flow"] == load and row["metric"] == metric
        ]
        return statistics.fmean(values) if values else None

    def paired_stat(load, metric):
        return numeric_summary(
            [
                row["queue_age_minus_rr"]
                for row in paired_rows
                if row["be_load_mbps_per_flow"] == load and row["metric"] == metric
            ]
        )

    hypothesis_rows = []
    for load in sorted({row["be_load_mbps_per_flow"] for row in per_run}):
        queue_gap = {
            scheduler: statistics.fmean(
                row["be_candidate_mean_age_ms"] - row["ll_candidate_mean_age_ms"]
                for row in per_run
                if row["be_load_mbps_per_flow"] == load and row["scheduler"] == scheduler
            )
            for scheduler in SCHEDULERS
        }
        be_share = paired_stat(load, "selected_be_share")
        ll_gap = paired_stat(load, "ll_mean_service_gap_ms")
        be_share_delta = be_share["mean"]
        ll_gap_delta = ll_gap["mean"]
        ll_delay_delta = paired_mean(load, "ll_mean_delay_ms")
        throughput_delta = paired_mean(load, "all_throughput_mbps")
        hypothesis_rows.extend(
            [
                {
                    "be_load_mbps_per_flow": load,
                    "hypothesis": "H1_BE_queue_heads_are_older",
                    "status": "SUPPORTED" if queue_gap["queue-age"] > 0 else "UNSUPPORTED",
                    "observable": "mean eligible BE queue-head age minus LL age",
                    "rr_value": queue_gap["rr"],
                    "queue_age_value": queue_gap["queue-age"],
                    "paired_delta": queue_gap["queue-age"] - queue_gap["rr"],
                    "limitation": "candidate queue-head samples, not full queue residence distributions",
                },
                {
                    "be_load_mbps_per_flow": load,
                    "hypothesis": "H2_service_shifts_toward_BE",
                    "status": "SUPPORTED"
                    if be_share["ci95_lower"] is not None and be_share["ci95_lower"] > 0
                    else ("UNSUPPORTED" if be_share["variation_status"] == "identical" else "INCONCLUSIVE"),
                    "observable": "paired change in BE share of final user allocations",
                    "rr_value": "",
                    "queue_age_value": "",
                    "paired_delta": be_share_delta,
                    "limitation": "allocation share does not reveal bytes aggregated per allocation",
                },
                {
                    "be_load_mbps_per_flow": load,
                    "hypothesis": "H3_LL_becomes_less_competitive",
                    "status": "SUPPORTED"
                    if ll_gap["ci95_lower"] is not None and ll_gap["ci95_lower"] > 0
                    else ("UNSUPPORTED" if ll_gap["variation_status"] == "identical" else "INCONCLUSIVE"),
                    "observable": "paired change in mean LL service-opportunity gap",
                    "rr_value": "",
                    "queue_age_value": "",
                    "paired_delta": ll_gap_delta,
                    "limitation": "class-level gap; low rate also controls queue availability",
                },
                {
                    "be_load_mbps_per_flow": load,
                    "hypothesis": "H4_airtime_credit_interaction",
                    "status": "INCONCLUSIVE",
                    "observable": "airtime-credit values at candidate sorting and final selection",
                    "rr_value": "",
                    "queue_age_value": "",
                    "paired_delta": "",
                    "limitation": "current observation trace does not record credits",
                },
                {
                    "be_load_mbps_per_flow": load,
                    "hypothesis": "H5_waiting_changes_without_throughput_change",
                    "status": "SUPPORTED"
                    if ll_delay_delta > 0 and abs(throughput_delta) < 1e-6
                    else "UNSUPPORTED",
                    "observable": "paired LL mean-delay and aggregate-throughput changes",
                    "rr_value": "",
                    "queue_age_value": "",
                    "paired_delta": f"delay={ll_delay_delta:.9f}; throughput={throughput_delta:.9f}",
                    "limitation": "association under the tested configuration, not causal isolation",
                },
                {
                    "be_load_mbps_per_flow": load,
                    "hypothesis": "H6_backlog_or_aggregation_controls_decisions",
                    "status": "INCONCLUSIVE",
                    "observable": "queue depth and A-MPDU membership at each final decision",
                    "rr_value": "",
                    "queue_age_value": "",
                    "paired_delta": "",
                    "limitation": "neither queue depth nor aggregate membership is recorded",
                },
            ]
        )

    output.mkdir(parents=True, exist_ok=True)
    write_csv(output / "per-run-summary.csv", list(per_run[0]), per_run)
    write_csv(output / "paired-comparison.csv", list(paired_rows[0]), paired_rows)
    write_csv(output / "statistical-summary.csv", list(stats_rows[0]), stats_rows)
    write_csv(output / "load-sweep-summary.csv", list(load_rows[0]), load_rows)
    write_csv(output / "scheduler-behavior-summary.csv", list(behavior_rows[0]), behavior_rows)
    write_csv(output / "selected-sta-distribution.csv", list(station_rows[0]), station_rows)
    write_csv(output / "hypothesis-assessment.csv", list(hypothesis_rows[0]), hypothesis_rows)
    write_csv(output / "verification.csv", list(verification_rows[0]), verification_rows)

    source_matrix = raw_root / "experiment-matrix.csv"
    if source_matrix.is_file():
        (output / "experiment-matrix.csv").write_text(
            source_matrix.read_text(encoding="utf-8"), encoding="utf-8"
        )
    summary = {
        "schema": "experimental-validation-statistics-v1",
        "generated_at": max(record["metadata"]["finished_at"] for record in records),
        "raw_root": relative(raw_root),
        "completed_runs": len(per_run),
        "paired_runs": len({(row["be_load_mbps_per_flow"], row["rng_run"]) for row in paired_rows}),
        "loads_mbps_per_be_flow": sorted({row["be_load_mbps_per_flow"] for row in per_run}),
        "rng_runs": sorted({row["rng_run"] for row in per_run}),
        "incomplete_pairs": incomplete,
        "statistical_unit": "one matched RNG run",
        "ci_method": "two-sided 95% Student t interval for n>=3; no interval for n<3",
        "interpretation_warning": "n=10 paired-run intervals are descriptive under the stated Student-t assumptions; no automatic significance or generality claim is made",
        "all_validations_passed": all(row["validation_status"] == "PASSED" for row in verification_rows),
        "all_stored_checksums_match": all(
            row["stored_checksums_match"] == "true" for row in verification_rows
        ),
        "all_reproduction_commands_recorded": all(
            row["exact_reproduction_command_recorded"] == "true"
            for row in verification_rows
        ),
        "statistics": stats_rows,
    }
    (output / "statistical-summary.json").write_text(
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
                "completed_runs": len(per_run),
                "matched_pairs": summary["paired_runs"],
                "all_validations_passed": summary["all_validations_passed"],
                "output": relative(output),
            },
            indent=2,
        )
    )


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    matrix = subparsers.add_parser("run-matrix", help="Run or resume a paired experiment matrix")
    matrix.add_argument("--raw-root", type=Path, default=DEFAULT_RAW_ROOT)
    matrix.add_argument("--loads", type=parse_int_list, default=[4, 8, 12])
    matrix.add_argument("--rng-runs", type=parse_int_list, default=[1, 2, 3])
    matrix.add_argument("--seed", type=int, default=1)
    matrix.add_argument("--duration", default="5s")
    matrix.add_argument("--drain-time", default="200ms")
    matrix.set_defaults(func=run_matrix)

    aggregate_parser = subparsers.add_parser(
        "aggregate", help="Aggregate completed paired experiments"
    )
    aggregate_parser.add_argument("--raw-root", type=Path, default=DEFAULT_RAW_ROOT)
    aggregate_parser.add_argument("--output", type=Path, default=DEFAULT_EVIDENCE)
    aggregate_parser.set_defaults(func=aggregate)
    return parser.parse_args()


def main():
    args = parse_args()
    try:
        args.func(args)
    except (OSError, RuntimeError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
