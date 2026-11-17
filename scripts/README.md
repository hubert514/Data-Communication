# Bootstrap tooling

Implemented preparation: `setup_ns3.sh`, `build.sh`, `smoke_ofdma.sh` delegate
to Python, reject unknown options and preserve evidence. See ENVIRONMENT.md for
prerequisites, candidate status, exact semantics and pending acceptance.

`scheduler_checkpoint.py` implements the Engineer B official-example workflow:
fixed-parameter execution, run metadata/checksums, PHY HE_MU parsing,
R0/R1/R2 comparison, CSV validation, and focused prototype comparison.

`mixed_traffic_checkpoint.py` runs and validates one project-specific 4 LL / 4
BE experiment. `experimental_validation.py` resumes a matched RR/Queue-Age load
sweep and produces per-run, paired, statistical, scheduler-behavior, and
verification artifacts. Large raw traces stay under `.local/`.

`drain_sensitivity.py` keeps the five-second offered interval fixed while varying
the receive drain, reports delivery and goodput with explicit denominators, and
checks the underlying packet/scheduler/PHY traces against the 200 ms reference.
`mechanism_diagnosis.py` aggregates the observation-only credit-order, queue
occupancy, aggregation, and cross-policy sequence traces and performs an exact
legacy-versus-instrumented non-regression comparison.

```bash
python3 scripts/experimental_validation.py run-matrix --loads 4,8,12 --rng-runs 1,2,3,4,5,6,7,8,9,10
python3 scripts/experimental_validation.py aggregate
python3 scripts/drain_sensitivity.py aggregate
python3 scripts/mechanism_diagnosis.py compare-nonregression
python3 scripts/mechanism_diagnosis.py aggregate
```

The legacy `run.sh` and `analyze.py` scaffolds still deliberately exit 2; use
the Python checkpoint tools above for the implemented scenario.
