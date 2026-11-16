#!/usr/bin/env python3
"""Run and compare local ns-3.49 RR scheduler checkpoint experiments."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = ROOT / ".local" / "ns-3"
DEFAULT_EVIDENCE = ROOT / ".local" / "scheduler-checkpoint"

BASE_OPTIONS = {
    "udp": 1,
    "downlink": 1,
    "nStations": 8,
    "maxMuStas": 4,
    "dlAckType": "MU-BAR",
    "enableUlOfdma": 0,
    "enableBsrp": 0,
    "frequency": 5,
    "channelWidth": 20,
    "mcs": 5,
    "guardInterval": 800,
    "simulationTime": "2s",
    "distance": 5,
    "RngSeed": 1,
    "RngRun": 1,
}

HE_MU_RE = re.compile(r"^\+(?P<time>[0-9.]+)s .*WifiPhy:Send\(.*preamble: HE_MU .*$")
USER_RE = re.compile(
    r"\{STA-ID: (?P<aid>[0-9]+), RU\{(?P<ru_type>[^/]+)/(?P<ru_index>[0-9]+)/"
    r"(?P<segment>[^}]+)\}, MCS: (?P<mcs>[0-9]+), Nss: (?P<nss>[0-9]+)\}"
)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def probe(*args: str) -> str | None:
    result = subprocess.run(args, cwd=UPSTREAM, capture_output=True, text=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else None


def parse_phy_log(path: Path) -> list[dict[str, object]]:
    transmissions: list[dict[str, object]] = []
    with path.open(encoding="utf-8", errors="replace") as stream:
        for line in stream:
            match = HE_MU_RE.match(line)
            if not match:
                continue
            users = []
            for user in USER_RE.finditer(line):
                users.append(
                    {
                        "aid": int(user.group("aid")),
                        "ru_type": user.group("ru_type"),
                        "ru_index": int(user.group("ru_index")),
                        "segment": user.group("segment"),
                        "mcs": int(user.group("mcs")),
                        "nss": int(user.group("nss")),
                    }
                )
            transmissions.append(
                {
                    "time_ns": int(Decimal(match.group("time")) * Decimal(1_000_000_000)),
                    "users": users,
                }
            )
    return transmissions


def canonical_phy(transmissions: list[dict[str, object]]) -> list[tuple[object, ...]]:
    rows: list[tuple[object, ...]] = []
    for tx_index, transmission in enumerate(transmissions):
        for user in transmission["users"]:
            rows.append(
                (
                    tx_index,
                    transmission["time_ns"],
                    user["aid"],
                    user["ru_type"],
                    user["ru_index"],
                    user["segment"],
                    user["mcs"],
                    user["nss"],
                )
            )
    return rows


def validate_trace_csv(path: Path, transmissions: list[dict[str, object]]) -> dict[str, object]:
    candidate_rows = []
    final_rows = []
    with path.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            if row["phase"] == "candidate":
                candidate_rows.append(row)
            elif row["phase"] == "final":
                final_rows.append(row)

    age_rows = [row for row in candidate_rows if row["mpdu_age_ns"]]
    nonnegative_ages = all(int(row["mpdu_age_ns"]) >= 0 for row in age_rows)
    timestamps_not_future = all(
        int(row["mpdu_timestamp_ns"]) <= int(row["time_ns"]) for row in age_rows
    )
    exact_age_arithmetic = all(
        int(row["mpdu_age_ns"])
        == int(row["time_ns"]) - int(row["mpdu_timestamp_ns"])
        for row in age_rows
    )

    trace_final = sorted(
        (
            int(row["time_ns"]),
            int(row["aid"]),
            row["ru_type"],
            int(row["ru_index"]),
            int(row["mcs"]),
            int(row["nss"]),
        )
        for row in final_rows
    )
    phy_final = sorted(
        (
            int(transmission["time_ns"]),
            int(user["aid"]),
            str(user["ru_type"]),
            int(user["ru_index"]),
            int(user["mcs"]),
            int(user["nss"]),
        )
        for transmission in transmissions
        for user in transmission["users"]
    )
    final_matches_phy = trace_final == phy_final
    all_final_selected = all(row["final_selected"] == "1" for row in final_rows)
    passed = all(
        (
            nonnegative_ages,
            timestamps_not_future,
            exact_age_arithmetic,
            final_matches_phy,
            all_final_selected,
        )
    )
    ages = [int(row["mpdu_age_ns"]) for row in age_rows]
    return {
        "candidate_rows": len(candidate_rows),
        "candidate_rows_with_age": len(age_rows),
        "final_rows": len(final_rows),
        "nonnegative_ages": nonnegative_ages,
        "timestamps_not_future": timestamps_not_future,
        "exact_age_arithmetic": exact_age_arithmetic,
        "all_final_selected": all_final_selected,
        "final_matches_phy": final_matches_phy,
        "min_age_ns": min(ages) if ages else None,
        "max_age_ns": max(ages) if ages else None,
        "passed": passed,
    }


def load_trace_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def command_run(args: argparse.Namespace) -> int:
    if not (UPSTREAM / ".git").is_dir():
        raise SystemExit("Missing .local/ns-3 checkout")

    output_dir = Path(args.output_dir).resolve() / args.label
    output_dir.mkdir(parents=True, exist_ok=False)
    log_path = output_dir / "run.log"
    trace_path = output_dir / "scheduler_observations.csv"

    options = dict(BASE_OPTIONS)
    options["RngRun"] = args.rng_run
    if args.queue_age_priority:
        options["useQueueAgePriority"] = 1
    if args.queue_age_fixture:
        options["queueAgeFixture"] = 1
    if args.trace_sink:
        options["rrTraceCsv"] = trace_path
        options["rrTraceRunId"] = args.label

    example = "wifi-he-network " + " ".join(f"--{key}={value}" for key, value in options.items())
    command = [sys.executable, "ns3", "run", example]
    env = os.environ.copy()
    env["NS_LOG"] = (
        "RrMultiUserScheduler=level_debug|prefix_time:"
        "MultiUserScheduler=level_debug|prefix_time:"
        "WifiPhy=function|prefix_time"
    )

    metadata = {
        "schema": "scheduler-checkpoint-run-v1",
        "label": args.label,
        "started_at": now(),
        "finished_at": None,
        "command": command,
        "command_shell": shlex.join(command),
        "cwd": str(UPSTREAM),
        "upstream_sha": probe("git", "rev-parse", "HEAD"),
        "upstream_status": probe("git", "status", "--porcelain"),
        "project_sha": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "options": {key: str(value) for key, value in options.items()},
        "rng_seed": 1,
        "rng_run": args.rng_run,
        "trace_sink": bool(args.trace_sink),
        "ns_log": env["NS_LOG"],
        "returncode": None,
    }
    (output_dir / "run_metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    with log_path.open("w", encoding="utf-8") as log:
        result = subprocess.run(
            command,
            cwd=UPSTREAM,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            check=False,
        )

    transmissions = parse_phy_log(log_path)
    metadata.update(
        finished_at=now(),
        returncode=result.returncode,
        dl_he_mu_count=len(transmissions),
        phy_user_rows=len(canonical_phy(transmissions)),
        checksums={"run.log": sha256(log_path)},
    )
    if trace_path.exists():
        metadata["checksums"][trace_path.name] = sha256(trace_path)
    (output_dir / "run_metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    print(json.dumps(metadata, indent=2, ensure_ascii=False))
    return result.returncode


def command_compare(args: argparse.Namespace) -> int:
    root = Path(args.output_dir).resolve()
    labels = args.labels
    parsed = {label: parse_phy_log(root / label / "run.log") for label in labels}
    canonical = {label: canonical_phy(value) for label, value in parsed.items()}
    reference = canonical[labels[0]]
    comparisons = {
        label: {
            "dl_he_mu_count": len(parsed[label]),
            "phy_user_rows": len(canonical[label]),
            "identical_to_reference": canonical[label] == reference,
        }
        for label in labels
    }
    trace_validations = {}
    for label in labels:
        trace_path = root / label / "scheduler_observations.csv"
        if trace_path.exists():
            trace_validations[label] = validate_trace_csv(trace_path, parsed[label])
    passed = all(item["identical_to_reference"] for item in comparisons.values()) and all(
        item["passed"] for item in trace_validations.values()
    )
    report = {
        "schema": "scheduler-checkpoint-comparison-v1",
        "reference": labels[0],
        "labels": labels,
        "comparisons": comparisons,
        "trace_validations": trace_validations,
        "passed": passed,
    }
    report_path = root / args.report
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if passed else 1


def command_prototype_compare(args: argparse.Namespace) -> int:
    root = Path(args.output_dir).resolve()
    baseline = parse_phy_log(root / args.baseline / "run.log")
    prototype = parse_phy_log(root / args.prototype / "run.log")
    trace_path = root / args.prototype / "scheduler_observations.csv"
    rows = load_trace_rows(trace_path)

    changed = []
    selected_set_changed = []
    for index, (base_tx, proto_tx) in enumerate(zip(baseline, prototype)):
        if base_tx != proto_tx:
            changed.append(index)
        if {user["aid"] for user in base_tx["users"]} != {
            user["aid"] for user in proto_tx["users"]
        }:
            selected_set_changed.append(index)
    changed.extend(range(min(len(baseline), len(prototype)), max(len(baseline), len(prototype))))

    legal_ru_allocations = all(
        0 < len(tx["users"]) <= 4
        and len(
            {
                (user["ru_type"], user["ru_index"], user["segment"])
                for user in tx["users"]
            }
        )
        == len(tx["users"])
        for tx in prototype
    )

    ranking_by_decision: dict[int, dict[int, tuple[int, int]]] = {}
    accepted_by_decision: dict[int, set[int]] = {}
    final_by_decision: dict[int, set[int]] = {}
    for row in rows:
        decision = int(row["decision_id"])
        aid = int(row["aid"])
        status = row["eligibility_status"]
        if status == "age_rank_observed":
            candidate = (int(row["mpdu_age_ns"]), int(row["scan_order"]))
            old = ranking_by_decision.setdefault(decision, {}).get(aid)
            if old is None or candidate[0] > old[0]:
                ranking_by_decision[decision][aid] = candidate
        elif status == "candidate_accepted":
            accepted_by_decision.setdefault(decision, set()).add(aid)
        elif status == "final_selected":
            final_by_decision.setdefault(decision, set()).add(aid)

    final_is_eligible = all(
        selected <= accepted_by_decision.get(decision, set())
        for decision, selected in final_by_decision.items()
    )
    selected_oldest_four = True
    for decision, ranked in ranking_by_decision.items():
        expected = {
            aid
            for aid, _ in sorted(ranked.items(), key=lambda item: (-item[1][0], item[1][1]))[:4]
        }
        if final_by_decision.get(decision, set()) != expected:
            selected_oldest_four = False
            break

    trace_validation = validate_trace_csv(trace_path, prototype)
    first_difference = None
    if selected_set_changed:
        index = selected_set_changed[0]
        decision = index + 1
        first_difference = {
            "transmission_index": index,
            "baseline": baseline[index],
            "prototype": prototype[index],
            "prototype_ranked_ages_ns": {
                str(aid): age_and_order[0]
                for aid, age_and_order in sorted(ranking_by_decision.get(decision, {}).items())
            },
        }

    passed = all(
        (
            bool(selected_set_changed),
            legal_ru_allocations,
            final_is_eligible,
            selected_oldest_four,
            trace_validation["passed"],
        )
    )
    report = {
        "schema": "scheduler-checkpoint-prototype-comparison-v1",
        "baseline": args.baseline,
        "prototype": args.prototype,
        "baseline_dl_he_mu_count": len(baseline),
        "prototype_dl_he_mu_count": len(prototype),
        "changed_transmission_count": len(changed),
        "changed_selected_sta_set_count": len(selected_set_changed),
        "first_difference": first_difference,
        "legal_ru_allocations": legal_ru_allocations,
        "final_is_eligible": final_is_eligible,
        "selected_oldest_four": selected_oldest_four,
        "trace_validation": trace_validation,
        "passed": passed,
    }
    report_path = root / args.report
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if passed else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="operation", required=True)

    run = subparsers.add_parser("run")
    run.add_argument("--label", required=True)
    run.add_argument("--output-dir", default=str(DEFAULT_EVIDENCE))
    run.add_argument("--rng-run", type=int, default=1)
    run.add_argument("--trace-sink", action="store_true")
    run.add_argument("--queue-age-priority", action="store_true")
    run.add_argument("--queue-age-fixture", action="store_true")
    run.set_defaults(func=command_run)

    compare = subparsers.add_parser("compare")
    compare.add_argument("--output-dir", default=str(DEFAULT_EVIDENCE))
    compare.add_argument("--labels", nargs="+", required=True)
    compare.add_argument("--report", default="comparison.json")
    compare.set_defaults(func=command_compare)

    prototype = subparsers.add_parser("prototype-compare")
    prototype.add_argument("--output-dir", default=str(DEFAULT_EVIDENCE))
    prototype.add_argument("--baseline", required=True)
    prototype.add_argument("--prototype", required=True)
    prototype.add_argument("--report", default="prototype-comparison.json")
    prototype.set_defaults(func=command_prototype_compare)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
