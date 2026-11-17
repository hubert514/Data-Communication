# B scheduler-mechanism evidence manifest

This directory contains observation-only scheduler diagnostics for BE loads 8
and 12 Mbps, RR and Queue-Age, and matched RngRun 1–3 (12 runs / 6 policy pairs).
Raw traces remain under `.local/mechanism-diagnosis/` and
`.local/instrumentation-nonregression/`.

```bash
python3 scripts/mechanism_diagnosis.py run-matrix --loads 8,12 --rng-runs 1,2,3
python3 scripts/mechanism_diagnosis.py compare-nonregression
python3 scripts/mechanism_diagnosis.py aggregate
(cd docs/evidence/b-mechanism-diagnosis-01 && sha256sum -c checksums.sha256)
```

`instrumentation-nonregression.csv` compares eight existing artifacts for each
policy against the pre-instrumentation run. All 16 comparisons are exact on all
common fields; only `run_id` and the newly introduced PHY `mpdu_count` field are
excluded. This covers scheduler rows, exact PHY timestamps/RUs/PSDU bytes,
packet events, and application summaries.

`mechanism-per-run-summary.csv` reports const queue counters sampled only for
already accepted candidates, post-update credit summaries, and actual PHY
aggregation. These candidate samples are decision-weighted; run-level summaries
are the inference units. `cross-policy-sequence.csv` records index-aligned PPDU
sequence comparisons. `hypothesis-assessment.csv` states the evidence and
alternative interpretation for H1–H5.

Patch `003-scheduler-mechanism-observation.patch` is observation-only: it adds
credit/order and const queue counters plus final PHY MPDU counts without adding
queue peeks, RNG calls, events, credit changes, eligibility changes, or RU logic.
