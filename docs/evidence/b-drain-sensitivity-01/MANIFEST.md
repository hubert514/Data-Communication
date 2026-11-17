# B drain-sensitivity evidence manifest

This directory contains lightweight derived evidence for the fixed 12 Mbps per
BE-flow experiment. Application traffic always runs for five seconds; only the
receive drain changes among 200, 500, and 1000 ms. RngRun 1–3 and RR/Queue-Age
form 9 matched pairs (18 validated runs).

Large raw traces are intentionally excluded from Git:

- 200 ms: `.local/experimental-validation/be12mbps/`
- 500/1000 ms: `.local/drain-sensitivity/be12mbps/`

Reproduce or resume and aggregate with:

```bash
python3 scripts/drain_sensitivity.py run-matrix --load 12 --drains-ms 200,500,1000 --rng-runs 1,2,3
python3 scripts/drain_sensitivity.py aggregate
(cd docs/evidence/b-drain-sensitivity-01 && sha256sum -c checksums.sha256)
```

`drain-per-run-summary.csv` keeps application-stop delivery, drain delivery,
simulation-end delivery, and undelivered packets separate. Five-second final
delivery and full receive-window goodput have different explicit denominators.
`drain-trace-equivalence.csv` compares mapping, packet-event, scheduler, and PHY
rows against 200 ms after excluding `run_id`; all 48 comparisons are exact.
`drain-verification.csv` records raw checksum and invariant checks per run.

The application-undelivered field is a sink-level proxy. It is not a direct MAC
queue depth or proof that the remaining packets were all queued at simulation
stop.
