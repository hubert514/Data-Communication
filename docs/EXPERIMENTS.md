# Experiment plan

**TODO / NOT IMPLEMENTED:** run harness, traffic calibration, measurements,
aggregation, statistics, and plots. No experimental data exists in this scaffold.

Use README Sections 5–6. Proposed checkpoint config is in
`configs/checkpoint.json`; it is a planning artifact, not an executable scenario.

| Phase | Principal factor | Planned values | Gate |
|---|---|---|---|
| E0 | Baseline sanity | B1, 8 STAs | Real DL MU evidence and valid metrics |
| E1 | Scheduler | B1/P1/P2 | Implemented and accepted variants only |
| E2 | Offered load | Calibrated low/medium/high | Record actual contention |
| E3 | STA count | 4/8/16/32 | Fix other controls |
| E4 | LL fraction | 25/50/75% | Comparable BE demands |
| E5 | Policy thresholds | TODO PM-approved sweep | No post-hoc optimized claim |

Pair seeds across schemes (at least 3 preliminary; target at least 10 final).
Vary one main factor at a time. Fix channel, MCS, coordinates, AC, RU policy,
ACK policy, MU cap, traffic/load, measurement window and drain across variants.
LL starts at 200 B/10 ms; validate contention before interpreting null effects.

TODO decide and document measurement layer, exact per-packet P95 convention,
deadline-miss denominator and lost-packet treatment, warm-up and drain, BE load,
and Jain index population before collection. FlowMonitor alone does not provide
exact packet-level P95 or scheduling decisions.

Every future figure must reference raw data, run IDs, config, project/upstream
SHAs, paired seeds, analysis invocation and file checksums. Preliminary single
runs must be labeled preliminary. D consolidates evidence; PM signs off claims.
