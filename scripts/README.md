# Bootstrap tooling

Implemented preparation: `setup_ns3.sh`, `build.sh`, `smoke_ofdma.sh` delegate
to Python, reject unknown options and preserve evidence. See ENVIRONMENT.md for
prerequisites, candidate status, exact semantics and pending acceptance.

TODO / NOT IMPLEMENTED: project run CLI, batch experiments, aggregation and
plots. `run.sh` and `analyze.py` deliberately exit 2 with that status; no
simulation entry point or empirical output is synthesized.
