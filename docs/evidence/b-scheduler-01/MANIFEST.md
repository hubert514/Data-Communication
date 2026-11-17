# B-SCHEDULER-01 evidence manifest

This directory indexes Engineer B's local ns-3.49 scheduler checkpoint work.
The large raw logs and CSV files remain uncommitted under `.local/` as required.

## Provenance

- Project base SHA: `9a91cc10e1d515aae1db006c4929ddc5a154f669`
- Upstream ns-3 SHA: `418210e8914e9f6bcb5cddbcc94a2cecb7853b68`
- Host: macOS Darwin 25.6.0, arm64
- Compiler: Apple clang 21.0.0
- CMake: 4.5.0
- Python: 3.13.7
- Ninja: 1.13.0

## Local evidence

| Path | Meaning |
|---|---|
| `.local/evidence/20261116T181829Z-setup-5fa5ca82/` | Successful pinned ns-3 setup log and metadata |
| `.local/evidence/20261116T183223Z-build-dc05f095/` | Configure/build logs and metadata |
| `.local/scheduler-checkpoint/R0/` | Pristine RR baseline log and metadata |
| `.local/scheduler-checkpoint/R1_FINAL/` | Final source state; traces disconnected |
| `.local/scheduler-checkpoint/R2_FINAL/` | Final source state; CSV trace sink connected |
| `.local/scheduler-checkpoint/comparison-final.json` | Automated ordered R0/R1/R2 comparison |
| `.local/scheduler-checkpoint/FIX_RR/` | Controlled staggered-flow fixture with RR |
| `.local/scheduler-checkpoint/FIX_QA/` | Same fixture with queue-age policy enabled |
| `.local/scheduler-checkpoint/fixture-prototype-comparison.json` | Automated prototype validation |

Each run directory contains `run.log` and `run_metadata.json`. Runs with a
trace sink also contain `scheduler_observations.csv`. Metadata records the full
command, source status, parameters, exit code, counts, and SHA-256 checksums.

## Tracked reconstruction artifacts

- `patches/001-rr-queue-age-observation.patch`
- `scripts/scheduler_checkpoint.py`
- `docs/SCHEDULER_CHECKPOINT.zh-TW.md`
- `docs/evidence/b-scheduler-01/results-summary.json`

The raw Engineer A archive named in
`origin/feature/simulation-environment:docs/evidence/a-env-01/MANIFEST.txt` was
not locally available. Its committed excerpts and recomputation output were
read without changing that branch. R0 is an independent local reproduction,
not a substitute raw copy of Engineer A's archive.
