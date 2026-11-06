# Environment and first feasibility gate

**TODO / NOT IMPLEMENTED:** accepted simulator environment, successful build,
official-example runtime proof, and project simulation. This document records
the candidate and commands; it does not certify a working experiment.

| Item | Bootstrap state |
|---|---|
| Upstream | https://gitlab.com/nsnam/ns-3-dev.git |
| Candidate tag | `ns-3.49` |
| Candidate peeled commit | `418210e8914e9f6bcb5cddbcc94a2cecb7853b68` |
| Tag identity | Verified with `git ls-remote` on 2026-11-07 |
| Local build / DL MU behavior | **UNVERIFIED** until executed evidence and PM review |
| Accepted tag/SHA and toolchain | TODO — Engineer A evidence; Technical PM acceptance |

The scripts pin this candidate SHA to prevent moving dependencies. This is a
candidate identity pin, not acceptance of the release for the study. Do not
switch tags, use master, or change the scientific comparison without PM review.

## Supported setup path

Use a non-root Linux environment (Ubuntu/WSL2 is a proposed starting point),
Python 3.10+, Git, CMake 3.25+, GCC 11+ or Clang 17+, and Make or Ninja.
The CMake/compiler minima were inspected in the pinned `CMakeLists.txt`;
check the release's full installation requirements for your chosen platform.
Windows Git Bash can invoke the wrappers, but native Windows build support is
**not verified**. Scripts do not install system packages or configure WSL.

```bash
./scripts/setup_ns3.sh
./scripts/build.sh
./scripts/smoke_ofdma.sh
```

Equivalent entry points: `python3 scripts/ns3_tools.py setup`, `build`, `smoke`.
`--help` is supported; other arguments are rejected. Paths derive from the
script location, so commands can be invoked outside the repository directory.

Setup fetches only the proposed release into gitignored `.local/ns-3`, verifies
the exact commit, and applies the ordered tracked `patches/series`. It records
patch checksums and a worktree fingerprint. Applied patches are staged in the
local upstream index to account for newly added files; no upstream commit is made.
A repeat run accepts only the same
managed patch state. Unknown changes, untracked upstream files, changed patch
inputs, a wrong commit, or a partial checkout fail clearly; nothing is reset or
deleted. No simulator overlays exist yet; TODO define their installation when
A/B agree on the integration contract.

Build enables examples/tests and builds the official `wifi-he-network` target.
Smoke runs that official example with DL UDP, RR enabled by explicit
`dlAckType=MU-BAR`, eight STAs, `maxMuStas=4`, 20 MHz/5 GHz, MCS 5,
GI 800 ns, UL OFDMA disabled, seed/run 1, and a short 2 s trial.
This is **an upstream feasibility probe**, not the project LL/BE baseline.

Each operation writes `.local/evidence/<id>/run_metadata.json` plus command
logs, including success/failure, command arguments, exact upstream/project SHA,
project dirty state, OS/compiler, candidate/config, timestamps, and checksums.
Unknown or inapplicable values remain null and are never invented.

## Acceptance still required

1. A: preserve configure/build and example command logs, compiler/OS, exact SHA.
2. A/B: inspect scheduler/frame-exchange debug logs and add a focused TX trace
   if logs are insufficient. Identify actual **DL MU transmissions**, served
   STA IDs, and RU allocation. A nonzero throughput table alone is insufficient.
3. B: inspect the pinned scheduler decision point and queue timestamp, receiver,
   TID/AC, and occupancy visibility; propose a source-backed extension strategy.
4. PM: review evidence and select the accepted version/strategy. Update this
   document and candidate lock through PR with evidence links.

The smoke script records `dl_mu_gate=TODO_REVIEW`; an exit-zero example is
never automatically promoted to proof of OFDMA or checkpoint acceptance.

Official references: [installation](https://www.nsnam.org/docs/installation/html/quick-start.html),
[candidate tag](https://gitlab.com/nsnam/ns-3-dev/-/tags/ns-3.49),
[pinned example](https://gitlab.com/nsnam/ns-3-dev/-/blob/418210e8914e9f6bcb5cddbcc94a2cecb7853b68/examples/wireless/wifi-he-network.cc).
