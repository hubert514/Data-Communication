# B-EXPERIMENTAL-VALIDATION-01 evidence manifest

本目錄保存 4／8／12 Mbit/s BE load sweep、RngRun 1--3、RR／Queue-Age
共 18 次模擬的輕量可審核證據。大型 raw CSV/log 位於
`.local/experimental-validation/`，不納入 Git。

## Provenance

- Project starting commit: `cbf724b1a9831550119bb464a6ff1bc1929cedb7`
- ns-3.49 commit: `418210e8914e9f6bcb5cddbcc94a2cecb7853b68`
- Patches: `001-rr-queue-age-observation.patch`,
  `002-mixed-traffic-checkpoint.patch`
- Topology/configuration: 1 AP／8 STA、4 LL／4 BE、802.11ax 5 GHz 20 MHz、
  HE MCS 5、800 ns GI、最多四個 DL MU users、TID 0／AC_BE
- Window: 5 s application traffic + 200 ms drain
- RNG seed: 1; matched RngRun: 1, 2, 3

## Artifacts

| File | Meaning |
|---|---|
| `experiment-matrix.csv` | 18 runs、raw 路徑、exact reproduction command、HE-MU counts |
| `per-run-summary.csv` | 每個 run 的 throughput、delay、PDR、Jain、queue age、service behavior |
| `paired-comparison.csv` | 每個 load／RngRun 的 `Queue-Age - RR` metrics |
| `load-sweep-summary.csv` | 每個 load／policy 的 mean 與 SD |
| `statistical-summary.csv` | scheduler 與 paired differences 的 n、mean、SD、95% t interval |
| `statistical-summary.json` | 同上及 matrix completeness／checksum／reproduction audit |
| `scheduler-behavior-summary.csv` | class allocation、service gap 與 LL tail-window metrics |
| `selected-sta-distribution.csv` | 每個 run／AID 的 final allocation count 與 share |
| `hypothesis-assessment.csv` | H1--H6 的 observable、狀態與限制 |
| `verification.csv` | 每個 run 的完整 validation、checksum 與 command audit |
| `checksums.sha256` | 本目錄輕量 artifacts 的 SHA-256 |

`statistical-summary.json` 記錄：18 completed runs、9 matched pairs、沒有
incomplete pair、所有 validation 通過、所有 stored raw checksum 相符、所有
run 都有重現命令。

## Reproduction

```bash
python3 scripts/experimental_validation.py run-matrix \
  --raw-root .local/experimental-validation \
  --loads 4,8,12 --rng-runs 1,2,3 \
  --seed 1 --duration 5s --drain-time 200ms

python3 scripts/experimental_validation.py aggregate \
  --raw-root .local/experimental-validation \
  --output docs/evidence/b-experimental-validation-01
```

Runner 遇到已通過且 configuration 相符的非空 output 會重用，否則既有單次
runner 會拒絕覆寫，因此不會覆蓋原本的 seed-1 evidence。
