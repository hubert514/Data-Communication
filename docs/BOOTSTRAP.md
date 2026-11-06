# Bootstrap handoff — 2026-11-07 (Asia/Taipei)

The provided GitHub repository already existed and was empty. Its first commit
contains the authoritative README; the `docs/bootstrap` review branch adds the
requested structure, TODO docs/config, issue/PR templates and feasibility tools.
The README's Git blob matches the supplied file (`67601e8592fe92fdca99c7d1e3fe801de0b9c5fd`).

## Executed bootstrap validation

| Command/check | Actual outcome |
|---|---|
| Official `git ls-remote` for ns-3.49 | Tag exists; peeled SHA `418210e8914e9f6bcb5cddbcc94a2cecb7853b68` |
| `python scripts/ns3_tools.py setup` | Candidate cloned and exact SHA verified |
| Repeat via `bash scripts/setup_ns3.sh` | Completed without altering checkout |
| `python -m unittest discover -s tests -v` | Six bootstrap safety tests passed |
| Python compile and `bash -n` on wrappers | Passed |
| `python scripts/ns3_tools.py setup --unsupported` | Rejected with nonzero exit |
| `bash scripts/run.sh --scheduler latency` | Explicit TODO / NOT IMPLEMENTED; exit 2 |
| `python scripts/analyze.py --input results/not-a-run` | Explicit TODO / NOT IMPLEMENTED; exit 2 |
| `python scripts/ns3_tools.py build` | Failed preflight: CMake not on PATH; no compilation |
| `python scripts/ns3_tools.py smoke` | Failed preflight: CMake not on PATH; no example execution |

Tests cover clean setup idempotency, managed patch idempotency, newly added
patched files, preservation/rejection of unknown tracked edits and untracked
files, changed patch inputs, and wrong-commit rejection. They test bootstrap
tooling only. CI repeats syntax and safety checks; it does not build ns-3 or
certify scheduler behavior.

Initial machine-local evidence directories (gitignored, not shared experiment
artifacts; timestamps are UTC):

- `.local/evidence/20261106T161243Z-setup-284d9bd2/`
- `.local/evidence/20261106T161329Z-setup-5e5798e9/`
- `.local/evidence/20261106T161323Z-build-b39f9829/`
- `.local/evidence/20261106T161324Z-smoke-85660620/`

Each directory has truthful `run_metadata.json`; executed external commands have
logs and checksums. Preflight failures have an error rather than fabricated
command output. A must preserve/share successful future evidence for PM review.

## Outstanding milestone and decisions

**TODO / NOT IMPLEMENTED:** accepted environment, successful ns-3 build,
official-example DL MU proof, mixed LL/BE B1, packet/flow metrics, P1/P2,
analysis, plots and checkpoint deck. No empirical data or improvement claim was
created. The candidate remains **UNVERIFIED** for build/runtime acceptance.

Start with [Engineer A feasibility](https://github.com/hubert514/Data-Communication/issues/1)
and [Engineer B API inspection](https://github.com/hubert514/Data-Communication/issues/2),
then [PM version/extension/interface review](https://github.com/hubert514/Data-Communication/issues/3).
The [issue register](ISSUES.md) contains all 12 checkpoint tasks and four
milestones. Handles, project license, accepted toolchain, timing/load details,
branch protection and scientific decisions remain with the Technical PM.

Every subsequent change goes through a PR. This bootstrap PR also awaits PM
review before merge; bootstrap completion does not mean checkpoint acceptance.
