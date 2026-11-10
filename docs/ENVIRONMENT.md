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

## Observed evidence (Engineer A, 2026-11-10) — NOT PM accepted

Everything in this section was observed on one machine and is pending Engineer B
interpretation and PM review. It is not an acceptance of the tag, toolchain or DL MU gate.
Evidence files: `docs/evidence/a-env-01/` (tentative location, see MANIFEST.txt there).

| Item | Observed |
|---|---|
| Project SHA / state | `9a91cc10e1d515aae1db006c4929ddc5a154f669`, clean, no patches |
| Upstream | `ns-3.49` / `418210e8914e9f6bcb5cddbcc94a2cecb7853b68` (`git rev-parse` matches the candidate lock) |
| OS | Ubuntu 24.04.2 LTS on WSL2, kernel 6.18.54.1, x86_64 |
| Toolchain | g++ 13.3.0, CMake 3.28.3, Python 3.12.3, Git 2.43.0, Ninja 1.11.1, GNU Make 4.3 |
| Build profile | debug, examples and tests enabled; only `wifi-he-network` was built |
| setup | `20261110T012214Z-setup-42f72e11`, completed, rc=0 |
| build | `20261110T012353Z-build-a43a93e5`, completed, configure rc=0 (~38 s), build rc=0 (~4 min 43 s) |
| smoke | `20261110T013905Z-smoke-24d0991e`, rc=0, `status=executed_pending_dl_mu_review`, `dl_mu_gate=TODO_REVIEW` |

Official example `wifi-he-network` (smoke configuration, seed/run 1, 2 s, 8 STAs, `maxMuStas=4`):

- Scheduler layer (smoke `01.log`, script-managed): 364 DL MU decisions.
- PHY layer (manual run, `WifiPhy=function` log, not script-generated): 364 `WifiPhy::Send`
  calls with preamble `HE_MU`; timestamps identical to the 364 scheduler decisions.
- Every `HE_MU` carries 4 users with one 52-tone RU each (RU 1-4), 1456 RUs in total,
  all sent by the AP PHY. STA-ID (AID) 1-4 and 5-8 alternate; AID n maps to MAC
  `00:00:00:00:00:0n`, AP is `...:09`. PSDUs are AP-to-STA QOSDATA.
- 364 `HE_MU` versus 363 trigger frames: the last `HE_MU` starts at 1.9957272 s with a
  5311.2 us PPDU, so its trigger would fall after the 2 s stop time.

Limits and open items:

- Trigger subtype (MU-BAR) is inferred from `dlAckType=MU-BAR`; the log does not show it.
- PHY evidence is the `WifiPhy::Send` function log, not the `PhyTxPsduBegin` trace.
- Official-example probe only: not the project B1 baseline, no packet-level measurement,
  single seed/run, single machine.
- Large logs are not committed; their sha256 are in MANIFEST.txt and their accessible
  location is TODO.
  
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
