# Latency-Aware and Fair OFDMA Scheduling in Wi-Fi 6 (ns-3)

> **Status:** Planning / pre-implementation (2026-11-06)  
> **Course:** Data Communication — semester project  
> **Team:** 4 members: 2 implementation engineers, 1 technical PM, 1 evaluation/report lead  
> **Next milestone:** Progress checkpoint during **2026-11-16 to 2026-11-22** (exact presentation date TBD)

## 1. Project overview

This project studies downlink (DL) Wi-Fi 6 / IEEE 802.11ax OFDMA scheduling in ns-3 when **latency-sensitive (LL)** and **best-effort (BE)** UDP traffic coexist. We will establish a built-in Round Robin OFDMA baseline, implement a simple latency-aware scheduler, then add a fairness-protection mechanism and evaluate the latency–throughput–fairness trade-off.

**Core research question:** Can a simple latency-aware OFDMA scheduler lower LL packet delay and deadline misses relative to Round Robin **without unacceptable BE throughput loss or starvation**?

### Research questions

- **RQ1 — Latency:** Does latency-aware STA selection reduce LL mean/P95 packet delay and deadline-miss ratio compared with Round Robin?
- **RQ2 — Cost:** How much BE throughput or fairness is lost when LL packets receive priority?
- **RQ3 — Fairness:** Can explicit protection of waiting BE stations improve the trade-off?
- **RQ4 — Robustness:** How do conclusions change with load, STA count, traffic composition, and scheduler parameters?

### Scope and non-goals

**In scope:** One AP; multiple associated STAs; **downlink** UDP; 20 MHz HE/802.11ax; built-in RR OFDMA; two custom STA-selection policies; measured packet-level latency, throughput, losses, and fairness; reproducible simulation runs.

**Not in initial scope:** Full reproduction of LOMAS, production Wi-Fi firmware, uplink scheduling, joint PHY/link adaptation optimization, novel 802.11 standard changes, or dynamic RU sizing. Adaptive RU allocation and mixed AC_VO/AC_BE experiments are possible **stretch goals** after the core comparisons work.

**Important:** This is a project plan, **not a claim that code is already written or experiments have been run**. Record all actual findings as they become available.

## 2. Why these baselines?

Three variants should run in the **same simulation topology and measurement pipeline**:

| ID | Scheme | Purpose | Required |
|---|---|---|---|
| **B1** | Built-in `ns3::RrMultiUserScheduler` | Reference OFDMA performance | Yes |
| **P1** | Queue-age / urgency-aware OFDMA | Reduce LL delay | Yes |
| **P2** | Urgency-aware OFDMA + BE fairness guard | Reduce starvation and BE harm | Semester target |
| B0 | Single-user Wi-Fi 6 | Non-OFDMA reference | Optional |

The built-in RR scheduler is **not necessarily strict cyclic station rotation**: ns-3 documentation describes **dynamic priority based on airtime fairness**. Preserve and document its actual behavior rather than replacing it with a home-made “RR” and calling that the official baseline.

**Controlled comparison:** Fix all factors that are not the tested scheduler (channel, MCS/rate control, STA placement, offered load, QoS/AC, maximum scheduled STAs, RU-allocation rules, ACK policy, run duration, and random-seed pairing).

## 3. Proposed scheduling policies (design specification)

### B1 — Round Robin

Use the official `RrMultiUserScheduler` as shipped with the chosen ns-3 release. Configure and log `NStations` and any other relevant attributes. **Confirm by trace/log that DL MU/OFDMA transmissions actually occur**; simply setting `WIFI_STANDARD_80211ax` does **not** enable OFDMA by itself.

### P1 — Latency-aware STA selection

At each eligible DL OFDMA scheduling opportunity, consider stations with packets eligible for transmission. For an LL station `i`, define:

```text
queue_age_i_ms = now_ms - enqueue_time_of_oldest_eligible_LL_packet_i_ms
urgency_i      = queue_age_i_ms / deadline_i_ms
```

Initial policy (to refine after feasibility testing):

1. Build the **eligible, nonempty** STA candidate list; never schedule an empty queue.
2. Identify urgent LL candidates with `urgency_i >= urgency_threshold` (initial trial: `0.5`, **not an optimized value**).
3. Rank urgent LL candidates by descending urgency; break ties deterministically.
4. Fill remaining MU slots using the original RR priority/order as closely as the API permits.
5. Preserve legal RU assignments and all PHY/MAC constraints; only STA-selection priority should differ from B1 in the first comparison.
6. If no eligible LL packet is urgent, behave like B1 as nearly as possible.

**Feasibility gate:** First confirm whether the scheduler can access an eligible packet's enqueue time, traffic class, and station ID. Do not silently substitute **time since the STA was last served** for **actual packet queue age**. If enqueue time cannot be accessed safely, document the limitation and explicitly rename any fallback as *service-age-aware*, not queue-age-aware.

### P2 — Latency-aware with BE fairness protection

Extend P1 with a configurable service-starvation guard:

```text
be_service_age_i_ms = now_ms - last_successfully_scheduled_service_i_ms
```

If a BE station has pending traffic and its service age exceeds `be_max_service_gap_ms`, reserve an eligible MU service opportunity for the most overdue BE candidate, subject to a valid allocation and actual pending frames; fill other positions through P1. Log each fairness intervention.

The fairness rule, handling of first-time service, multiple overdue STAs, and empty queues must be deterministic and documented. Never promise that this simple guard **guarantees a hard deadline**; evaluate achieved behavior empirically.

**Design limitation:** `last scheduled` does not equal `packet delivered`. Use separate TX/ACK/RX logs if needed to interpret fairness and losses.

### Minimal pseudocode

```text
on_downlink_mu_opportunity():
    candidates = all_eligible_stations_with_pending_data()
    if scheme == B1:
        return upstream_rr_selection(candidates)

    urgent = rank_urgent_LL_by_packet_queue_age(candidates)
    if scheme == P2:
        protected = oldest_starved_BE_if_any(candidates)
    else:
        protected = none

    selected = unique_valid_stations(protected, urgent)
    selected += upstream_rr_fill_for_remaining_slots(candidates, selected)
    return allocate_using_same_valid_RU_policy_as_B1(selected)
```

This is **behavioral pseudocode**, not a claim that these exact functions exist in ns-3.

## 4. Simulator and technical feasibility

### Proposed reference version

Use **ns-3.49 (`ns-3.49` upstream tag)** as the first candidate because an upstream release tag dated 2026-10-06 is available. **Do not commit to it until a local build and the required OFDMA example pass.** If it is incompatible with the team's environment, the PM may approve a different released tag. Once chosen, pin **the exact tag and commit SHA** in `docs/ENVIRONMENT.md` and the setup script; do not use an unpinned `master` branch for final comparisons.

### Official components to inspect

- `src/wifi/model/he/multi-user-scheduler.{h,cc}` — general MU scheduling interface (verify paths in the pinned tag).
- `src/wifi/model/he/rr-multi-user-scheduler.{h,cc}` — RR implementation and station/RU decisions (verify paths).
- `examples/wireless/wifi-he-network.cc` — official HE network example.
- `WifiMacHelper::SetMultiUserScheduler(...)` — AP's multi-user scheduling configuration.
- `FlowMonitor` — per-flow IP-layer accounting; **not** sufficient alone for exact per-packet P95 and scheduler decisions.
- Wi-Fi queue / MPDU metadata / tracing — determine whether enqueue timestamps and TID/AC can be read from the scheduling path.

**Do not confuse** `RrMultiUserScheduler` (DL/UL OFDMA multi-user scheduling) with `RrWifiQueueScheduler` (single-user MAC queue service order).

The implementation engineer must select and document **one** extension strategy:

1. A new `MultiUserScheduler` subclass, **if** supported hooks permit the required decisions; or
2. A maintained patch/derived implementation of `RrMultiUserScheduler`, if necessary due to private/internal APIs.

Do not copy upstream code without retaining the applicable license notices and documenting modified files.

### First feasibility probes

- [ ] Pin and build ns-3; save compiler, OS, and exact commit.
- [ ] Run the official `wifi-he-network` example with an explicit MU scheduler.
- [ ] Verify traces/logs show **DL MU** transmissions and the served STA IDs.
- [ ] Verify `NStations` and channel-width settings in the pinned version.
- [ ] Identify the precise callback or function where candidate STA priority is decided.
- [ ] Inspect whether enqueue time, receiver, TID/AC, and queue occupancy are accessible.
- [ ] Demonstrate a **minimal change in selected STA ordering** without breaking the run.
- [ ] Document limits and an alternative if packet queue age is not available.

**Never mark an item complete using documentation alone**; provide an executed command, log, trace, test, or source inspection with the pinned version.

## 5. Initial simulation plan

Start with a **simple DL testbed**. The table below is a proposed configuration, not measured or optimized values.

| Parameter | Initial value | Notes |
|---|---|---|
| Wi-Fi standard | 802.11ax / HE | Confirm version-specific API |
| Topology | 1 AP + 8 associated STAs | Initially 4 LL and 4 BE recipients |
| Direction | DL only | AP sends UDP to the STAs |
| Channel | 20 MHz, 5 GHz | Fixed for initial comparisons |
| MCS | Fixed MCS 5 | Record rate manager/PHY config |
| Placement | STAs about 5–10 m from AP | Fix exact coordinates or seed |
| OFDMA cap | Up to 4 selected STAs | `NStations` or equivalent verified attribute |
| LL traffic | UDP, 200 B every 10 ms | Also test 5 ms / 2 ms if needed |
| BE traffic | UDP, 1200 B packets | Sweep offered load; document rates |
| QoS phase 1 | Same AC for both classes | Isolate *scheduler* effects |
| QoS extension | AC_VO for LL; AC_BE for BE | Separate experiment due to EDCA confounding |
| Simulated duration | 20–30 s + drain interval | Add warm-up if needed |
| Randomness | Paired seeds | >=3 initial runs; target >=10 final |

**Traffic classification:** Initially distinguish LL versus BE by explicitly documented recipient/flow identity (e.g., separate STA sets and UDP ports). Using the same AC in phase 1 avoids attributing EDCA priority to the custom scheduler. Treat mixed AC as an additional independent variable later.

**Load warning:** The initial LL rate is only 0.16 Mb/s per LL STA (`200*8/0.010`); verify that the network actually experiences scheduling contention before interpreting a null result.

## 6. Metrics and statistical protocol

| Metric | Definition / requirement |
|---|---|
| **LL mean delay** | Mean application- or IP-layer packet latency, with layer clearly labeled. |
| **LL P95 delay** | Exact 95th percentile from packet-level TX/RX timestamps, or explicitly label an estimate from histogram bins. |
| **LL deadline miss ratio** | State the denominator and how lost packets are counted; use a prespecified application deadline (initial trial: 10 ms). |
| **BE goodput** | Delivered BE application payload bytes / measurement-window seconds; identify the layer. |
| **Packet loss** | Sent, delivered, and unresolved packets; distinguish drain-time artifacts. |
| **Fairness** | Jain's index over comparable BE STA goodputs plus per-STA service-gap statistics; do not equate equal throughput to fair treatment when demands differ. |
| **Scheduler decisions** | Per-decision time, eligible count, selected STA IDs, queue age/urgency (if available), fairness intervention, RU allocation. |

FlowMonitor measures IP-level flows and provides delay aggregates/histograms; it does **not** directly tell us the scheduler's decision or guarantee exact packet-level P95. Use dedicated application traces or packet IDs/timestamps where needed. Stop applications before `Simulator::Stop()` and allow a drain interval; document remaining queued packets.

**Experimental controls**:

- Compare B1/P1/P2 under identical environment configs and corresponding seeds.
- Use multiple independent replications and report spread (e.g., mean ± SD or confidence intervals).
- Clearly separate preliminary single-run plots from final statistical conclusions.
- Never fabricate or extrapolate empirical results.
- For each figure, link to the exact config, run IDs, commit SHA, seed set, analysis script, and raw CSV.

### Planned experiments

| ID | Variable | Initial values | Key output |
|---|---|---|---|
| E0 | Baseline sanity | B1, fixed 8 STAs | MU trace, throughput, delay, loss |
| E1 | Scheduler choice | B1 / P1 / P2 | LL P95 vs BE goodput |
| E2 | Offered load | Low / medium / high, calibrated | Saturation sensitivity |
| E3 | STA count | 4 / 8 / 16 / 32 | Scalability and fairness |
| E4 | Traffic mix | 25% / 50% / 75% LL STAs | Coexistence sensitivity |
| E5 | Thresholds | urgency threshold, BE service-gap limit | Parameter sensitivity |

Vary one principal factor at a time with other settings fixed; **do not** blindly run the Cartesian product of all values. Dynamic RU sizing is reserved for a stretch milestone.

## 7. Team responsibilities (decided by the PM)

**All project requirements, priorities, deadline changes, and acceptance criteria are owned by the Technical PM.** Engineers propose implementation details; the PM approves changes to the study design. The report lead consolidates evidence but does not independently change experiment definitions.

| Role | Primary ownership | Handoff |
|---|---|---|
| **Engineer A — Simulation & Baseline** | ns-3 setup; topology; UDP traffic; B1 configuration; metrics hooks; run automation | Reproducible baseline command, raw data, config, logs |
| **Engineer B — Scheduler** | Source/API investigation; P1/P2 policy; patches; scheduling traces; scheduler tests | Scheduler switch, code diff, decision logs, tests |
| **Technical PM (you)** | Spec and milestone control; interface contract; PR review; merge approval; integration QA; risk log; scope decisions | Accepted issues/PRs, integration smoke tests, checkpoint status |
| **Member D — Evaluation & Report** | Experiment tables; data audit; statistics/plots; checkpoint and final presentation/report | Reproducible figures with source paths, English slides/report |

**Coding ownership:** Only A and B normally modify simulator C++. The PM reviews and verifies integration; D uses documented results and scripts, not fragile manual data copying. A/B should review each other's critical changes when practical.

### Required engineer-to-engineer interface contract

Before parallel development, agree on:

1. Exact pinned ns-3 version, toolchain, patch installation method.
2. One simulation entry point and one canonical configuration schema.
3. Scheduler selector: `rr`, `latency`, `fairness` (not all implemented on day one).
4. Traffic/STA identifiers and definition of LL and BE.
5. Single definition of warm-up, active measurement window, application stop, and drain.
6. Output schemas (`flows.csv`, `packets.csv`, `scheduler_decisions.csv`, `run_metadata.json`).
7. Flags/fields that are **planned** versus already implemented.

## 8. Milestones and acceptance gates

### Checkpoint — week of 2026-11-16 (exact date TBD)

**Nov 7–10: Feasibility**
- A: pin/build ns-3 and run official HE/OFDMA example; record commands and logs.
- B: locate MU scheduling decision points; report queue-age visibility and extension strategy.
- PM: review feasibility notes, select approved extension path and interface contract.
- D: prepare research question, setup diagram, checkpoint slide outline.

**Nov 11–13: Baseline**
- A: implement 1 AP / 8 STA DL UDP B1 scenario; export real flow and packet measurements.
- B: produce a minimal candidate-selection prototype or focused instrumentation test.
- PM: check OFDMA traces, traffic classification, metrics definitions, and reproducibility.
- D: produce initial table/plot from **actual** data, labeled preliminary.

**Nov 14–15: Integration + checkpoint package**
- A/B: integrate under the same version/config; resolve build and CLI issues.
- PM: perform smoke test and record what is verified versus pending.
- D: finish 7–8 slide checkpoint deck; include evidence, blockers, and next steps.

**Minimum checkpoint acceptance:**

- [ ] Official HE OFDMA example executes; output proves DL MU scheduling.
- [ ] A project-specific mixed-traffic B1 run is reproducible from a recorded command.
- [ ] At least one authentic throughput/delay result is exported and plotted.
- [ ] P1 decision rule and precise code insertion/extension path are documented.
- [ ] PM reviews integration, remaining blockers, and fallback options.

**Stretch for checkpoint:** P1 builds, changes station selection in a controlled test, and produces an initial B1/P1 comparison. **P2 is not required by checkpoint.**

### After checkpoint — semester deliverables

- **M2:** Complete, test and integrate P1.
- **M3:** Complete P2 BE fairness guard and verify no empty or invalid allocations.
- **M4:** Execute E1–E4 under paired seeds; analyze latency/cost/fairness trade-offs.
- **M5:** Execute E5 sensitivity and reproduce all final figures from scripts.
- **M6:** Submit source, experiment manifest, plots, English presentation, and final report with limitations.

### Fallback decision

If **by Nov 14** the team cannot produce a reliable B1 baseline, freeze P1 feature work and fix baseline/measurement first. If packet enqueue timestamps are inaccessible, prepare a clearly labeled service-age fallback and request PM approval before changing the study's claim.

## 9. Repository layout (requested scaffold; not all modules exist yet)

```text
.
├── README.md
├── .gitignore
├── LICENSE                       # choose/confirm applicable license; never strip ns-3 licenses
├── docs/
│   ├── ENVIRONMENT.md            # exact ns-3 tag/SHA, toolchain, build commands
│   ├── DESIGN.md                 # P1/P2 rules, constraints, fallback decisions
│   ├── EXPERIMENTS.md            # controlled variables and planned run matrix
│   ├── PM_STATUS.md              # owner, ETA, state, blockers, evidence links
│   └── CHECKPOINT.md             # checkpoint results and presentation outline
├── sim/                          # A: project simulation source/config
├── scheduler/                    # B: custom policy source and/or patches
├── patches/                      # changes to pinned upstream ns-3, if needed
├── scripts/                      # setup, build, run, batch, aggregate, plot
├── configs/                      # committed, machine-readable scenario configs
├── tests/                        # smoke/behavior/regression checks
├── results/
│   └── README.md                 # schema and storage policy; no fabricated results
├── figures/                       # generated figures or scripts to reproduce
└── .github/
    ├── ISSUE_TEMPLATE/
    └── pull_request_template.md
```

**Dependency strategy:** Keep this project repo separate from the entire ns-3 upstream history. Use a setup script that fetches a **pinned upstream tag/SHA** to a **gitignored local directory** (for example `.local/ns-3`) and applies tracked local patches / installs project sources, then builds. Record any upstream modifications as versioned patches or tracked source overlays. The setup script must be **idempotent or fail clearly**; do not silently overwrite uncommitted modifications.

Do not commit large compiled binaries, full upstream trees, raw PCAP archives, or local build directories. Commit small sample data only if clearly labeled **synthetic fixture** or **real experiment** with provenance.

### Planned command-line contract

Once the implementation exists, aim for an interface conceptually like:

```bash
# Illustrative future commands — NOT yet tested/implemented
./scripts/setup_ns3.sh
./scripts/build.sh
./scripts/run.sh --scheduler rr --n-stas 8 --seed 1 --config configs/checkpoint.yaml
./scripts/run.sh --scheduler latency --n-stas 8 --seed 1 --config configs/checkpoint.yaml
./scripts/run.sh --scheduler fairness --n-stas 8 --seed 1 --config configs/checkpoint.yaml
python3 scripts/analyze.py --input results/<run-id>/
```

The scripts must reject unsupported arguments with clear errors and emit `run_metadata.json` containing: upstream SHA, project SHA, OS/compiler, config, scheduler, seed/run, exact invocation, timestamps, and outcome.

### Output schema (initial contract)

- `flows.csv`: `run_id,flow_id,traffic_class,src,dst,tx_packets,rx_packets,rx_payload_bytes,throughput_mbps,mean_delay_ms,loss_count`
- `packets.csv`: `run_id,flow_id,packet_id,traffic_class,tx_time_s,rx_time_s,delay_ms,status` (use explicit missing/expired status, not fake receive times)
- `scheduler_decisions.csv`: `run_id,time_s,scheduler,eligible_sta_ids,selected_sta_ids,ru_allocation,urgent_sta_ids,fairness_override` (+ optional observed queue ages)
- `run_metadata.json`: exact version, scenario, parameters, scheduler, seed, timing and file checksums

Schemas may be revised **only with a documented migration/PR approved by PM**. Clearly distinguish measured fields from inferred or unavailable fields; do not populate them with invented defaults.

## 10. Git and review policy

- `main` stays reproducibly buildable; use short-lived branches `feature/simulation-*`, `feature/scheduler-*`, and `docs/*`.
- Every change goes through a PR; PM approves design-affecting merges and verifies checkpoint evidence.
- PR description must include **what changed, how tested, command/output, relevant issue, and known limitations**.
- Never merge a claimed performance improvement based on a single uncontrolled run.
- Create issues with **owner, exact acceptance criteria, dependencies, target milestone, and evidence URL/path**.
- D owns presentation consistency; PM owns technical sign-off for all results shown to the professor.

### PM acceptance tests

1. **Build:** reproducible setup/build succeeds from a fresh environment.
2. **OFDMA:** actual DL MU transmissions are observed; stations and RUs are logged.
3. **Baseline:** RR remains runnable after scheduler changes.
4. **Behavior:** a crafted test with LL urgency demonstrably changes P1 selection (or documents why it does not).
5. **Fairness:** BE protection in P2 triggers under a crafted starvation scenario, without invalid/duplicate selections.
6. **Measurement:** LL/BE flow labeling, packet timestamps, losses, units, and denominator conventions are checked.
7. **Reproducibility:** every chart is regenerable from tracked scripts, configuration, and preserved raw result files.

## 11. Checkpoint presentation outline (7–8 slides)

1. **Goal & professor feedback** — why simple latency-aware scheduling and why RR baseline.
2. **Feasibility evidence** — pinned ns-3 version, supported classes, compiled example, observed DL MU behavior.
3. **Scenario** — AP/STAs, LL/BE traffic, controlled parameters.
4. **Baseline** — RR architecture, configuration, authentic run evidence.
5. **Proposed P1/P2** — queue-age urgency, fairness guard, implementation path.
6. **Preliminary results** — real data with axes/units, comparison if available.
7. **Technical issues & decisions** — inaccessible metadata, RU constraints, QoS confounding, fallbacks.
8. **Schedule & next steps** — completed/pending work, who owns each artifact, next milestones.

**Reporting rule:** Separate `Implemented`, `Tested`, `Planned`, and `Blocked`. Do not present expected curves as simulated results.

## 12. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Scheduler cannot observe packet enqueue time | Source inspection early; add instrumentation/metadata if practical; otherwise PM-approved, explicitly renamed service-age fallback. |
| Modifying MU selection requires private internal changes | Implement maintained upstream patch or derived scheduler with pinned version and regression tests. |
| No contention at initial LL rates | Calibrate offered load and track nonempty queue/selection opportunities before interpreting null improvements. |
| AC_VO priority masks scheduler effect | First compare same AC; make mixed-AC comparison a separate controlled experiment. |
| P1 starves BE | P2 service-gap guard, BE goodput/fairness diagnostics, log interventions. |
| P95/packet losses mismeasured | Packet-level timestamps and IDs; explicit measurement window, drain interval, and missing-packet rules. |
| Two engineers conflict in ns-3 code | Separate scenario and scheduler ownership; frozen interface contract; integration smoke test every merge. |
| Time slips before checkpoint | B1 + authentic results take precedence over P2 and optional features. |

## 13. Instructions for Codex / repository bootstrap

The Technical PM will use Codex to initialize the GitHub repository. **At bootstrap, do the following in order:**

1. Create a repository with this `README.md` at its root. Do not create a fork/full copy of the upstream ns-3 source unless PM changes that decision.
2. Scaffold the directory structure and minimal `.gitignore`, issue/PR templates, and documentation placeholders. All placeholder files must say `TODO / NOT IMPLEMENTED` rather than claiming results exist.
3. Record the proposed upstream ns-3.49 tag as **unverified** until `scripts/setup_ns3.sh` and an OFDMA smoke test execute successfully; then pin the exact SHA.
4. Implement the **version setup + official example smoke test** first. Do not generate unsupported scheduler APIs, fake test passes, dummy empirical CSVs, or simulated improvement plots.
5. Maintain separate, reviewable commits or PRs for baseline scaffolding, measurement, and scheduler changes. Do not combine all work into one unreviewable patch.
6. Open trackable tasks for Engineer A, Engineer B, Technical PM, and Report Lead based on Section 8, with deliverables and acceptance criteria.
7. Pause at technical decisions that change the scientific comparison (e.g., substitute service age for queue age, change AC policy, change RU allocation). Document choices and request PM review.

**Bootstrap definition of done:** repository skeleton exists, the README and templates are committed, setup instructions are accurate, and the next unimplemented issues are visible. **Do not claim the project or checkpoint is finished merely because a repository exists.**

## 14. Research and official references

- [ns-3 Wi-Fi design documentation](https://www.nsnam.org/docs/models/html/wifi-design.html) — MU scheduler responsibilities, OFDMA and RR behavior.
- [ns-3 Wi-Fi user documentation](https://www.nsnam.org/docs/models/html/wifi-user.html) — `SetMultiUserScheduler`, queue scheduler distinction, ToS/AC configuration.
- [ns-3 FlowMonitor documentation](https://www.nsnam.org/docs/models/html/flow-monitor.html) — metrics, scope, and queue-drain caveat.
- [ns-3 upstream release tags](https://gitlab.com/nsnam/ns-3-dev/-/tags) — verify and pin a stable version.
- [ns-3 HE network example (upstream)](https://github.com/nsnam/ns-3-dev-git/blob/master/examples/wireless/wifi-he-network.cc) — adapt only after checking the pinned version.
- Magrin et al., **Validation of the ns-3 802.11ax OFDMA Implementation** (2021), DOI: [10.1145/3460797.3460798](https://doi.org/10.1145/3460797.3460798).
- Magrin et al., **Performance Evaluation of 802.11ax OFDMA through Theoretical Analysis and Simulations** (2023), DOI: [10.1109/TWC.2022.3231447](https://doi.org/10.1109/TWC.2022.3231447).
- **LOMAS: Latency-driven OFDMA Scheduling Design in Wi-Fi 6 Networks** (2025), DOI: [10.1109/ICNP65844.2025.11192340](https://doi.org/10.1109/ICNP65844.2025.11192340).

---

**Ownership:** Technical PM is the final decision-maker for scope, acceptance gates, experiment definitions, integration, and claims presented in the course checkpoint/final report. Program contributors remain responsible for correctness of their respective implementations.
