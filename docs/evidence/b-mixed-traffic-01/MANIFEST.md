# B-MIXED-TRAFFIC-01 evidence manifest

This manifest indexes the first project-specific 4 LL / 4 BE checkpoint pair.
The large packet, scheduler, and PHY traces remain under `.local/`; the small
reviewable summaries in this directory are committed.

## Configuration and provenance

- Project base before this work: `ffabf1eb7406bfd6e81c5e813acef8063154446d`
- Upstream ns-3.49 SHA: `418210e8914e9f6bcb5cddbcc94a2cecb7853b68`
- Topology: one AP and eight static STAs, 5 m from the AP
- PHY/MAC: 802.11ax, 5 GHz, 20 MHz, HE MCS 5, 800 ns GI
- Scheduler: official `RrMultiUserScheduler`, at most four MU STAs, UL OFDMA disabled
- Traffic: four LL flows (200 B, 160 kbit/s = nominal 10 ms interval) and four BE
  flows (1200 B, 8 Mbit/s); UDP downlink; all flows TID 0 / AC_BE
- Window: applications 1.0--6.0 s (5 s); 200 ms receive drain
- Randomness: seed 1, run 1
- E1: original RR, `UseQueueAgePriority=false`
- E2: class-agnostic queue-head age prototype, `UseQueueAgePriority=true`

Exact AID/MAC/IP/port mapping is in `mapping.csv`. Both runs used the same map.

## Local raw evidence

| Path | Meaning |
|---|---|
| `.local/mixed-traffic-checkpoint/E1-RR-seed1/` | E1 raw events, scheduler, PHY, summaries, validation and metadata |
| `.local/mixed-traffic-checkpoint/E2-QueueAge-seed1/` | E2 equivalent evidence |
| `.local/mixed-traffic-checkpoint/E1-vs-E2.csv` | descriptive paired comparison |

Raw SHA-256 values:

| Run | File | SHA-256 |
|---|---|---|
| E1 | `packet-events.csv` | `cce14f6e5a2335c4cb5802d2e8a981fc41471cf4edf5e8edd3638287e4c15e1d` |
| E1 | `scheduler.csv` | `bfd9b1860fe24c8dd8bf58a5d631513675678c8e88c1ed9bc572d229102dde37` |
| E1 | `phy.csv` | `bc2606af811695f92e87dd30e44a8034bce7e0048c5dbb3ecbc5b19e3bb91780` |
| E1 | `run-metadata.json` | `90fe3bf3cdd2d30e85ad162c5ed139733235b3d36c44c2b5120afb34937c686e` |
| E2 | `packet-events.csv` | `7f86188acabcef617e20f318f06a2843f56ec838ffdcd0a280d514626cdad4ff` |
| E2 | `scheduler.csv` | `7ee68b87f9777286268046ceb64be9ab6662fce50562f6c16c1e83edb53d32c6` |
| E2 | `phy.csv` | `1e76f911c49321ebca237a9ac28eec40c262f5171d8517fdf020780883b86f81` |
| E2 | `run-metadata.json` | `12db8d582cec9d1784d380fa303b78f26ea1c346e7b41cccc4c9b3d1079177d0` |

## Validation result

Both runs are **PASSED**. Each contains 3,619 actual AP PHY DL HE-MU
transmissions and 14,476 user/RU allocations. For each run, the ordered final
scheduler allocation batches exactly equal the ordered PHY batches. Mapping,
TID/AC, RU legality, at-most-four users, packet pairing, non-negative queue
ages, and per-flow count reconciliation all passed.

This is one deterministic paired seed. The comparison is descriptive only and
does not establish statistical improvement.

## Reproduction

```bash
python3 scripts/mixed_traffic_checkpoint.py run \
  --scheduler rr --run-id E1-RR-seed1 \
  --output .local/mixed-traffic-checkpoint/E1-RR-seed1 \
  --duration 5s --be-rate 8Mbps --seed 1 --rng-run 1

python3 scripts/mixed_traffic_checkpoint.py run \
  --scheduler queue-age --run-id E2-QueueAge-seed1 \
  --output .local/mixed-traffic-checkpoint/E2-QueueAge-seed1 \
  --duration 5s --be-rate 8Mbps --seed 1 --rng-run 1
```
