# Bootstrap tooling

Implemented preparation: `setup_ns3.sh`, `build.sh`, `smoke_ofdma.sh` delegate
to Python, reject unknown options and preserve evidence. See ENVIRONMENT.md for
prerequisites, candidate status, exact semantics and pending acceptance.

`scheduler_checkpoint.py` implements the Engineer B official-example workflow:
fixed-parameter execution, run metadata/checksums, PHY HE_MU parsing,
R0/R1/R2 comparison, CSV validation, and focused prototype comparison.

TODO / NOT IMPLEMENTED: the full project 4 LL / 4 BE run CLI, batch performance
experiments, aggregation and plots. `run.sh` and `analyze.py` deliberately exit
2 with that status; no project performance output is synthesized.
