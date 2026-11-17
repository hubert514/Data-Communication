#!/usr/bin/env python3
"""Run, summarize, validate, compare, and plot the mixed-traffic checkpoint."""

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import shlex
import statistics
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
NS3 = ROOT / ".local" / "ns-3"
TARGET = "scratch/wifi-ofdma-mixed-traffic"
RAW_FILES = ("mapping.csv", "packet-events.csv", "scheduler.csv", "phy.csv")


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_csv(path, fieldnames, rows):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def percentile_nearest_rank(values, percentile):
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(percentile * len(ordered)) - 1)]


def jain(values):
    if not values or sum(value * value for value in values) == 0:
        return None
    return sum(values) ** 2 / (len(values) * sum(value * value for value in values))


def format_float(value, digits=9):
    return "" if value is None else f"{value:.{digits}f}"


def git_output(*args, cwd=ROOT):
    result = subprocess.run(
        ["git", *args], cwd=cwd, check=False, capture_output=True, text=True
    )
    return result.stdout.strip() if result.returncode == 0 else None


def validate_required_files(output_dir):
    missing = [name for name in RAW_FILES if not (output_dir / name).is_file()]
    if missing:
        raise RuntimeError("Missing raw output: " + ", ".join(missing))


def allocation_batches(rows, key_name):
    batches = []
    current_key = None
    current = []
    for row in rows:
        key = row[key_name]
        if current_key is not None and key != current_key:
            batches.append(sorted(current))
            current = []
        current_key = key
        current.append(
            (
                row["aid"],
                row["ru_type"],
                row["ru_index"],
                row["mcs"],
                row["nss"],
            )
        )
    if current:
        batches.append(sorted(current))
    return batches


def analyze(output_dir, write_outputs=True):
    output_dir = output_dir.resolve()
    validate_required_files(output_dir)
    mapping = read_csv(output_dir / "mapping.csv")
    events = read_csv(output_dir / "packet-events.csv")
    scheduler = read_csv(output_dir / "scheduler.csv")
    phy = read_csv(output_dir / "phy.csv")

    checks = {}
    checks["mapping_has_8_stations"] = len(mapping) == 8
    checks["mapping_has_4_ll_4_be"] = (
        sum(row["traffic_class"] == "LL" for row in mapping) == 4
        and sum(row["traffic_class"] == "BE" for row in mapping) == 4
    )
    checks["all_flows_are_tid0_ac_be"] = all(
        row["tid"] == "0" and row["access_category"] == "AC_BE" for row in mapping
    )
    for field in ("flow_id", "sta_index", "aid", "mac", "ip", "port"):
        checks[f"mapping_unique_{field}"] = len({row[field] for row in mapping}) == 8

    by_flow = {row["flow_id"]: row for row in mapping}
    packets = {}
    duplicate_tx = False
    duplicate_rx = False
    rx_without_tx = False
    for event in events:
        key = (event["flow_id"], event["seq"])
        packet = packets.setdefault(key, {"tx": None, "rx": None})
        if event["event"] == "tx":
            duplicate_tx = duplicate_tx or packet["tx"] is not None
            packet["tx"] = event
        elif event["event"] == "rx":
            duplicate_rx = duplicate_rx or packet["rx"] is not None
            packet["rx"] = event
        else:
            raise RuntimeError(f"Unknown packet event {event['event']!r}")
    rx_without_tx = any(value["rx"] is not None and value["tx"] is None for value in packets.values())
    checks["no_duplicate_packet_events"] = not duplicate_tx and not duplicate_rx
    checks["every_rx_has_matching_tx"] = not rx_without_tx

    packet_rows = []
    flow_delays = {flow_id: [] for flow_id in by_flow}
    flow_counts = {
        flow_id: {"tx_packets": 0, "rx_packets": 0, "tx_bytes": 0, "rx_bytes": 0}
        for flow_id in by_flow
    }
    for (flow_id, seq), value in sorted(
        packets.items(), key=lambda item: (int(item[0][0]), int(item[0][1]))
    ):
        tx = value["tx"]
        rx = value["rx"]
        if tx is None:
            continue
        counts = flow_counts[flow_id]
        counts["tx_packets"] += 1
        counts["tx_bytes"] += int(tx["bytes"])
        if rx is not None:
            counts["rx_packets"] += 1
            counts["rx_bytes"] += int(rx["bytes"])
            delay_ms = int(rx["delay_ns"]) / 1e6
            flow_delays[flow_id].append(delay_ms)
        else:
            delay_ms = None
        packet_rows.append(
            {
                "run_id": tx["run_id"],
                "flow_id": flow_id,
                "traffic_class": tx["traffic_class"],
                "sta_index": tx["sta_index"],
                "aid": tx["aid"],
                "mac": tx["mac"],
                "seq": seq,
                "bytes": tx["bytes"],
                "tx_time_ns": tx["time_ns"],
                "rx_time_ns": "" if rx is None else rx["time_ns"],
                "delay_ms": format_float(delay_ms, 6),
                "status": "delivered" if rx is not None else "lost_by_sim_stop",
            }
        )

    flow_rows = []
    for flow_id, row in sorted(by_flow.items(), key=lambda item: int(item[0])):
        counts = flow_counts[flow_id]
        duration_s = (int(row["app_stop_ns"]) - int(row["app_start_ns"])) / 1e9
        delays = flow_delays[flow_id]
        tx_packets = counts["tx_packets"]
        rx_packets = counts["rx_packets"]
        flow_rows.append(
            {
                **row,
                "measurement_duration_s": format_float(duration_s, 6),
                **counts,
                "lost_packets": tx_packets - rx_packets,
                "pdr": format_float(rx_packets / tx_packets if tx_packets else None, 9),
                "throughput_mbps": format_float(counts["rx_bytes"] * 8 / duration_s / 1e6, 9),
                "mean_delay_ms": format_float(statistics.fmean(delays) if delays else None, 6),
                "p95_delay_ms": format_float(percentile_nearest_rank(delays, 0.95), 6),
            }
        )

    class_rows = []
    for traffic_class in ("LL", "BE", "ALL"):
        selected = (
            flow_rows if traffic_class == "ALL" else [r for r in flow_rows if r["traffic_class"] == traffic_class]
        )
        flow_ids = {r["flow_id"] for r in selected}
        delays = [delay for flow_id in flow_ids for delay in flow_delays[flow_id]]
        tx_packets = sum(int(r["tx_packets"]) for r in selected)
        rx_packets = sum(int(r["rx_packets"]) for r in selected)
        throughput = sum(float(r["throughput_mbps"]) for r in selected)
        class_rows.append(
            {
                "run_id": mapping[0]["run_id"] if mapping else "",
                "traffic_class": traffic_class,
                "flow_count": len(selected),
                "tx_packets": tx_packets,
                "rx_packets": rx_packets,
                "lost_packets": tx_packets - rx_packets,
                "pdr": format_float(rx_packets / tx_packets if tx_packets else None, 9),
                "throughput_mbps": format_float(throughput, 9),
                "mean_delay_ms": format_float(statistics.fmean(delays) if delays else None, 6),
                "p95_delay_ms": format_float(percentile_nearest_rank(delays, 0.95), 6),
                "jain_throughput": format_float(
                    jain([float(r["throughput_mbps"]) for r in selected]), 9
                ),
            }
        )

    candidate_rows = [
        row
        for row in scheduler
        if row["phase"] == "candidate"
        and row["eligibility_status"] == "candidate_accepted"
        and row["mpdu_age_ns"]
    ]
    queue_rows = []
    for traffic_class in ("LL", "BE", "ALL"):
        selected = (
            candidate_rows
            if traffic_class == "ALL"
            else [row for row in candidate_rows if row["traffic_class"] == traffic_class]
        )
        ages = [int(row["mpdu_age_ns"]) / 1e6 for row in selected]
        queue_rows.append(
            {
                "run_id": mapping[0]["run_id"] if mapping else "",
                "traffic_class": traffic_class,
                "sample_definition": "eligible_queue_head_candidate",
                "sample_count": len(ages),
                "mean_age_ms": format_float(statistics.fmean(ages) if ages else None, 6),
                "p50_age_ms": format_float(percentile_nearest_rank(ages, 0.50), 6),
                "p95_age_ms": format_float(percentile_nearest_rank(ages, 0.95), 6),
                "max_age_ms": format_float(max(ages) if ages else None, 6),
            }
        )

    final_rows = [row for row in scheduler if row["phase"] == "final"]
    scheduler_batches = allocation_batches(final_rows, "decision_id")
    phy_batches = allocation_batches(phy, "phy_sequence")
    checks["scheduler_has_final_allocations"] = bool(scheduler_batches)
    checks["phy_has_dl_he_mu_transmissions"] = bool(phy_batches)
    checks["max_four_phy_users"] = all(len(batch) <= 4 for batch in phy_batches)
    checks["legal_20mhz_ru_types"] = all(
        row["ru_type"] in {"26-tones", "52-tones", "106-tones", "242-tones"}
        for row in phy
    )
    checks["scheduler_final_equals_phy_sequence"] = scheduler_batches == phy_batches
    checks["scheduler_classes_resolved"] = all(
        row["traffic_class"] in {"LL", "BE"} for row in scheduler
    )
    checks["candidate_ages_nonnegative"] = all(
        int(row["mpdu_age_ns"]) >= 0 for row in candidate_rows
    )
    checks["flow_counts_reconcile"] = all(
        int(row["lost_packets"]) == int(row["tx_packets"]) - int(row["rx_packets"])
        for row in flow_rows
    )
    checks["all_packet_delays_nonnegative"] = all(
        not row["delay_ms"] or float(row["delay_ms"]) >= 0 for row in packet_rows
    )
    checks["at_least_one_packet_each_flow"] = all(int(row["tx_packets"]) > 0 for row in flow_rows)

    validation = {
        "schema": "mixed-traffic-validation-v1",
        "generated_at": utc_now(),
        "status": "PASSED" if all(checks.values()) else "FAILED",
        "checks": checks,
        "counts": {
            "dl_he_mu_transmissions": len(phy_batches),
            "dl_he_mu_user_allocations": len(phy),
            "scheduler_final_decisions": len(scheduler_batches),
            "scheduler_final_allocations": len(final_rows),
            "eligible_queue_head_samples": len(candidate_rows),
        },
    }

    if write_outputs:
        write_csv(
            output_dir / "packet-summary.csv",
            list(packet_rows[0]) if packet_rows else ["run_id"],
            packet_rows,
        )
        write_csv(output_dir / "flow-summary.csv", list(flow_rows[0]), flow_rows)
        write_csv(output_dir / "class-summary.csv", list(class_rows[0]), class_rows)
        write_csv(output_dir / "queue-age-summary.csv", list(queue_rows[0]), queue_rows)
        (output_dir / "validation.json").write_text(
            json.dumps(validation, indent=2) + "\n", encoding="utf-8"
        )
    return {
        "mapping": mapping,
        "packets": packet_rows,
        "flows": flow_rows,
        "classes": class_rows,
        "queue_age": queue_rows,
        "scheduler": scheduler,
        "phy": phy,
        "validation": validation,
    }


def run_experiment(args):
    if not NS3.is_dir():
        raise RuntimeError(f"ns-3 checkout not found: {NS3}")
    output_dir = args.output.resolve()
    if output_dir.exists() and any(output_dir.iterdir()):
        raise RuntimeError(f"Output directory is not empty: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    use_age = args.scheduler == "queue-age"
    target_args = [
        TARGET,
        f"--outputDir={output_dir}",
        f"--runId={args.run_id}",
        f"--beRate={args.be_rate}",
        f"--measurementDuration={args.duration}",
        f"--drainTime={args.drain_time}",
        f"--seed={args.seed}",
        f"--run={args.rng_run}",
        f"--useQueueAgePriority={str(use_age).lower()}",
    ]
    command = [str(NS3 / "ns3"), "run", " ".join(target_args)]
    started_at = utc_now()
    with (output_dir / "run.log").open("w", encoding="utf-8") as log:
        result = subprocess.run(command, cwd=NS3, stdout=log, stderr=subprocess.STDOUT, check=False)
    metadata = {
        "schema": "mixed-traffic-run-v1",
        "run_id": args.run_id,
        "scheduler": args.scheduler,
        "status": "SIMULATION_PASSED" if result.returncode == 0 else "SIMULATION_FAILED",
        "started_at": started_at,
        "finished_at": utc_now(),
        "command": command,
        "command_display": shlex.join(command),
        "returncode": result.returncode,
        "configuration": {
            "topology": "1 AP / 8 STA",
            "traffic_classes": "4 LL / 4 BE",
            "standard": "802.11ax",
            "channel_width_mhz": 20,
            "mcs": 5,
            "guard_interval_ns": 800,
            "max_mu_stas": 4,
            "ll_packet_bytes": 200,
            "ll_interval_ms": 10,
            "ll_rate": "160kbps",
            "be_packet_bytes": 1200,
            "be_rate": args.be_rate,
            "duration": args.duration,
            "drain_time": args.drain_time,
            "seed": args.seed,
            "rng_run": args.rng_run,
            "tid": 0,
            "access_category": "AC_BE",
        },
        "project_sha": git_output("rev-parse", "HEAD"),
        "project_dirty": git_output("status", "--porcelain"),
        "ns3_sha": git_output("rev-parse", "HEAD", cwd=NS3),
        "ns3_dirty": git_output("status", "--porcelain", cwd=NS3),
    }
    if result.returncode != 0:
        (output_dir / "run-metadata.json").write_text(
            json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
        )
        raise RuntimeError(f"Simulation failed; inspect {output_dir / 'run.log'}")
    report = analyze(output_dir)
    metadata["status"] = report["validation"]["status"]
    metadata["validation"] = report["validation"]
    metadata["checksums"] = {
        path.name: sha256(path)
        for path in sorted(output_dir.iterdir())
        if path.is_file() and path.name != "run-metadata.json"
    }
    (output_dir / "run-metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    if metadata["status"] != "PASSED":
        raise RuntimeError(f"Validation failed; inspect {output_dir / 'validation.json'}")
    print(json.dumps(report["validation"], indent=2))


def compare_runs(args):
    baseline = analyze(args.baseline, write_outputs=False)
    treatment = analyze(args.treatment, write_outputs=False)
    baseline_metadata = read_json(args.baseline / "run-metadata.json")
    treatment_metadata = read_json(args.treatment / "run-metadata.json")
    if baseline_metadata["configuration"] != treatment_metadata["configuration"]:
        raise RuntimeError("Run configurations differ; refusing an uncontrolled comparison")
    if baseline_metadata["scheduler"] == treatment_metadata["scheduler"]:
        raise RuntimeError("Comparison requires two distinct scheduler labels")
    baseline_map = {row["traffic_class"]: row for row in baseline["classes"]}
    treatment_map = {row["traffic_class"]: row for row in treatment["classes"]}
    rows = []
    for traffic_class in ("LL", "BE", "ALL"):
        left = baseline_map[traffic_class]
        right = treatment_map[traffic_class]
        rows.append(
            {
                "traffic_class": traffic_class,
                "baseline_run_id": left["run_id"],
                "treatment_run_id": right["run_id"],
                "baseline_throughput_mbps": left["throughput_mbps"],
                "treatment_throughput_mbps": right["throughput_mbps"],
                "throughput_delta_mbps": format_float(
                    float(right["throughput_mbps"]) - float(left["throughput_mbps"]), 9
                ),
                "baseline_mean_delay_ms": left["mean_delay_ms"],
                "treatment_mean_delay_ms": right["mean_delay_ms"],
                "mean_delay_delta_ms": format_float(
                    float(right["mean_delay_ms"]) - float(left["mean_delay_ms"]), 6
                ),
                "baseline_p95_delay_ms": left["p95_delay_ms"],
                "treatment_p95_delay_ms": right["p95_delay_ms"],
                "p95_delay_delta_ms": format_float(
                    float(right["p95_delay_ms"]) - float(left["p95_delay_ms"]), 6
                ),
            }
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_csv(args.output, list(rows[0]), rows)
    comparison = {
        "schema": "mixed-traffic-comparison-v1",
        "generated_at": utc_now(),
        "baseline": str(args.baseline.resolve()),
        "treatment": str(args.treatment.resolve()),
        "baseline_validation": baseline["validation"]["status"],
        "treatment_validation": treatment["validation"]["status"],
        "controlled_configuration_equal": True,
        "baseline_scheduler": baseline_metadata["scheduler"],
        "treatment_scheduler": treatment_metadata["scheduler"],
        "rows": rows,
        "interpretation": "Descriptive paired-run differences only; no improvement claim or statistical inference.",
    }
    json_path = args.output.with_suffix(".json")
    json_path.write_text(json.dumps(comparison, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(comparison, indent=2))


def svg_bar_chart(title, unit, categories, series, output):
    width, height = 760, 430
    left, right, top, bottom = 90, 30, 65, 80
    plot_w, plot_h = width - left - right, height - top - bottom
    maximum = max(value for _, values in series for value in values) * 1.15 or 1
    colors = ["#2563eb", "#f97316"]
    group_w = plot_w / len(categories)
    bar_w = min(54, group_w / (len(series) + 1))
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img">',
        f"<title>{title}</title>",
        f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        f'<text x="{left}" y="32" font-family="sans-serif" font-size="20" font-weight="600">{title}</text>',
        f'<text x="{left}" y="52" font-family="sans-serif" font-size="12" fill="#475569">Source: validated class-summary.csv; unit: {unit}</text>',
    ]
    for tick in range(6):
        value = maximum * tick / 5
        y = top + plot_h - plot_h * tick / 5
        parts.append(f'<line x1="{left}" y1="{y:.2f}" x2="{width-right}" y2="{y:.2f}" stroke="#e2e8f0"/>')
        parts.append(f'<text x="{left-10}" y="{y+4:.2f}" text-anchor="end" font-family="sans-serif" font-size="11" fill="#475569">{value:.2f}</text>')
    for category_index, category in enumerate(categories):
        center = left + group_w * (category_index + 0.5)
        parts.append(f'<text x="{center:.2f}" y="{top+plot_h+28}" text-anchor="middle" font-family="sans-serif" font-size="13">{category}</text>')
        total_width = bar_w * len(series)
        for series_index, (label, values) in enumerate(series):
            value = values[category_index]
            x = center - total_width / 2 + series_index * bar_w + 4
            height_value = plot_h * value / maximum
            y = top + plot_h - height_value
            parts.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{bar_w-8:.2f}" height="{height_value:.2f}" fill="{colors[series_index]}"/>')
            parts.append(f'<text x="{x+(bar_w-8)/2:.2f}" y="{max(top+12, y-6):.2f}" text-anchor="middle" font-family="sans-serif" font-size="11">{value:.3f}</text>')
    legend_x = left
    legend_y = height - 22
    for index, (label, _) in enumerate(series):
        x = legend_x + index * 155
        parts.append(f'<rect x="{x}" y="{legend_y-10}" width="12" height="12" fill="{colors[index]}"/>')
        parts.append(f'<text x="{x+18}" y="{legend_y}" font-family="sans-serif" font-size="12">{label}</text>')
    parts.append("</svg>")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(parts) + "\n", encoding="utf-8")


def plot_runs(args):
    baseline = analyze(args.baseline, write_outputs=False)
    treatment = analyze(args.treatment, write_outputs=False)
    categories = ["LL", "BE"]
    base = {row["traffic_class"]: row for row in baseline["classes"]}
    treat = {row["traffic_class"]: row for row in treatment["classes"]}
    labels = (baseline["mapping"][0]["run_id"], treatment["mapping"][0]["run_id"])
    svg_bar_chart(
        "Per-class throughput",
        "Mbit/s",
        categories,
        [
            (labels[0], [float(base[c]["throughput_mbps"]) for c in categories]),
            (labels[1], [float(treat[c]["throughput_mbps"]) for c in categories]),
        ],
        args.output_dir / "throughput-by-class.svg",
    )
    svg_bar_chart(
        "Per-class application delay (P95)",
        "ms",
        categories,
        [
            (labels[0], [float(base[c]["p95_delay_ms"]) for c in categories]),
            (labels[1], [float(treat[c]["p95_delay_ms"]) for c in categories]),
        ],
        args.output_dir / "p95-delay-by-class.svg",
    )
    print(args.output_dir.resolve())


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run and validate one experiment")
    run_parser.add_argument("--scheduler", choices=("rr", "queue-age"), required=True)
    run_parser.add_argument("--run-id", required=True)
    run_parser.add_argument("--output", type=Path, required=True)
    run_parser.add_argument("--duration", default="5s")
    run_parser.add_argument("--drain-time", default="200ms")
    run_parser.add_argument("--be-rate", default="8Mbps")
    run_parser.add_argument("--seed", type=int, default=1)
    run_parser.add_argument("--rng-run", type=int, default=1)
    run_parser.set_defaults(func=run_experiment)

    analyze_parser = subparsers.add_parser("analyze", help="Recompute and validate outputs")
    analyze_parser.add_argument("output", type=Path)
    analyze_parser.set_defaults(func=lambda args: print(json.dumps(analyze(args.output)["validation"], indent=2)))

    compare_parser = subparsers.add_parser("compare", help="Compare two validated runs")
    compare_parser.add_argument("--baseline", type=Path, required=True)
    compare_parser.add_argument("--treatment", type=Path, required=True)
    compare_parser.add_argument("--output", type=Path, required=True)
    compare_parser.set_defaults(func=compare_runs)

    plot_parser = subparsers.add_parser("plot", help="Create SVG figures from two runs")
    plot_parser.add_argument("--baseline", type=Path, required=True)
    plot_parser.add_argument("--treatment", type=Path, required=True)
    plot_parser.add_argument("--output-dir", type=Path, required=True)
    plot_parser.set_defaults(func=plot_runs)
    return parser.parse_args()


def main():
    args = parse_args()
    try:
        args.func(args)
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
