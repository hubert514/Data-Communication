# B expanded-validation evidence manifest

This directory contains derived evidence for BE offered loads 4, 8, and 12 Mbps
per flow, RR and Queue-Age, and matched RngRun 1–10: 60 validated simulations and
30 matched policy pairs. The statistical unit is one matched RngRun, never an
individual packet.

Large raw traces remain under `.local/experimental-validation/`. The runner
reuses completed runs only when configuration and prior validation match, so it
can be interrupted and resumed without replacing validated evidence.

```bash
python3 scripts/experimental_validation.py run-matrix --loads 4,8,12 --rng-runs 1,2,3,4,5,6,7,8,9,10
python3 scripts/experimental_validation.py aggregate --output docs/evidence/b-expanded-validation-01
(cd docs/evidence/b-expanded-validation-01 && sha256sum -c checksums.sha256)
```

`paired-comparison.csv` contains RR, Queue-Age, paired difference, ratio, and
percent change. `statistical-summary.csv` uses the ten independent paired runs
to report mean, sample SD, and a two-sided descriptive 95% Student-t interval.
`verification.csv` records validation, raw checksums, and reproduction-command
availability for all runs. Deterministic zero-variance metrics are reported as
such and are not presented as additional independent evidence.
