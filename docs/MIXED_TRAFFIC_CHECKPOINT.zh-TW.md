# Wi-Fi 6 RR OFDMA 4 LL / 4 BE Check-Point

日期：2026-11-17（Asia/Taipei）
ns-3：49，固定 SHA `418210e8914e9f6bcb5cddbcc94a2cecb7853b68`

## A. 完成狀態

| 交付項目 | 狀態 | 證據 |
|---|---|---|
| 1 AP / 8 STA、4 LL / 4 BE 專案場景 | **IMPLEMENTED / TESTED / PASSED** | `002-mixed-traffic-checkpoint.patch` |
| 真實應用層 Tx/Rx、delay、loss、PDR、throughput | **IMPLEMENTED / TESTED / PASSED** | `flow-summary.csv`、`class-summary.csv` |
| AID/MAC/IP/port/flow 明確對照 | **IMPLEMENTED / TESTED / PASSED** | `mapping.csv` |
| RR candidate age、eligibility、final RU | **IMPLEMENTED / TESTED / PASSED** | `scheduler.csv` |
| scheduler final 與 AP PHY HE-MU 對帳 | **TESTED / PASSED** | E1/E2 均 3,619 batches，ordered equality |
| E1 原始 RR / E2 class-agnostic queue age | **TESTED / PASSED** | seed 1 paired run |
| 吞吐量與 P95 delay 圖 | **IMPLEMENTED / TESTED / PASSED** | `figures/*-by-class.svg` |
| 多 seed 統計推論 | **NOT IMPLEMENTED** | 本 check-point 受限於不跑長模擬，只做 deterministic seed 1 |
| LL-aware custom policy | **NOT IMPLEMENTED** | 本階段刻意不實作 |
| 改善宣稱 | **NOT IMPLEMENTED** | 單一 seed 結果不支持改善 |

## B. 場景與 RR 架構摘要

場景使用 Spectrum PHY（OFDMA 必要）、802.11ax、5 GHz、20 MHz、HE MCS 5、800 ns GI。
AP 使用官方 `RrMultiUserScheduler`，`NStations=4`、UL OFDMA/BSRP/central 26-tone RU
關閉。八個 STA 靜態關聯並預先建立 TID 0 Block Ack；量測從 1 s 開始，因此所有 STA
在第一個應用封包前已完成 association。

LL 是應用層標籤，不是 MAC access category：STA 0--3 使用 200-byte UDP、160 kbit/s，
等價於 nominal 10 ms packet interval；STA 4--7 使用 1200-byte UDP、每 flow 8 Mbit/s。
所有 flow 都是 IPv4 ToS 0、TID 0、AC_BE，避免用 EDCA 優先權混入 scheduler 比較。

RR 的既有路徑為：airtime-credit 排序的 `m_staListDl` → BA/TID 檢查 →
`PeekNextMpdu(linkId, tid, address)` → `TryAddMpdu()` → private `m_candidates` →
`FinalizeTxVector()` 配合法 RU → PSDU/PHY。queue-age prototype 只在原有 eligibility loop
前，以每 STA 最舊 eligible queue-head timestamp 做穩定排序；其餘 eligibility、RU 與
airtime credit 更新保留官方行為。

## C. Queue-age 可觀測性

候選 MPDU 是指定 AID/MAC/TID 之 `PeekNextMpdu()` 回傳的下一個 eligible queue-head。
觀測值為：

```cpp
Simulator::Now() - mpdu->GetTimestamp()
```

AID/MAC 來自 scheduler `MasterInfo`，TID 來自原有 TID loop，AC 由
`QosUtilsMapTidToAc()` 取得。`WifiMpdu` retry counter 不會重設 timestamp；alias 仍回讀
original MPDU timestamp。此值不是 application latency：它只代表候選 head MPDU，不能
代表 A-MPDU 中其他 MPDU；A-MSDU 也只看到 wrapper MPDU 建立時間。

E1 的 TraceSource 只使用原有 loop 已取得的 `mpdu`，不新增 queue lookup、RNG 或事件；
先前官方 example R0/R1/R2 已證明 sink 接與不接時，selected STA、RU 與 PHY sequence
完全相同。

## D. Metric 定義

| Metric | 觀測點與公式 |
|---|---|
| sent packet | `OnOffApplication::TxWithAddresses`；只有 UDP socket 成功送出才計數 |
| received packet | STA `PacketSink::RxWithSeqTsSize` |
| application delay | sink simulation time 減 `SeqTsSizeHeader::GetTs()` |
| lost | 成功 sent 但在 app stop 後 200 ms drain 結束前未收到 |
| PDR | received packets / sent packets |
| throughput | received application bytes × 8 / 固定 5 s window |
| mean delay | 已收到 packets 的 arithmetic mean，packet-weighted |
| P95 delay | 已收到 packets 的 nearest-rank 95th percentile |
| Jain fairness | per-flow throughput 的 `(sum x)^2 / (n sum x^2)` |
| queue age summary | `candidate_accepted` 的 eligible queue-head ages；不是所有 queued MPDU |

`packet-events.csv` 是原始 app event；分析器以 `(flow_id, seq)` 配對，產生一列一 packet
的 `packet-summary.csv`。class aggregation 是 packet-weighted delay；throughput 是各 flow
加總。所有空值維持空值，不以 0 假造。

## E. E1 / E2 結果（seed 1）

共同驗證：8 個 flow 全部 PDR 1.0；E1/E2 各有 3,619 次實際 AP PHY DL HE-MU 與
14,476 個 user/RU allocations；每次最多 4 STA，使用合法 20 MHz RU；ordered scheduler
final batches 與 ordered PHY batches 完全相同。

| Class | Policy | Throughput (Mbit/s) | Mean delay (ms) | P95 delay (ms) | Lost |
|---|---|---:|---:|---:|---:|
| LL | E1 RR | 0.63872 | 0.913537 | 1.542850 | 0 |
| LL | E2 queue age | 0.63872 | 2.047962 | 3.043950 | 0 |
| BE | E1 RR | 31.99488 | 1.911540 | 2.509783 | 0 |
| BE | E2 queue age | 31.99488 | 1.905572 | 2.480433 | 0 |
| ALL | E1 RR | 32.63360 | 1.804786 | 2.484183 | 0 |
| ALL | E2 queue age | 32.63360 | 1.920803 | 2.540458 | 0 |

本 paired run 的 throughput 差異為 0；E2 的 LL mean 增加 1.134425 ms、P95 增加
1.501100 ms。這只是單一 deterministic seed 的描述性結果，不能作顯著性推論；且它
不支持「queue-age 改善 LL delay」的宣稱。原因解讀需留待多 seed 與 load sweep，不能從
一筆結果臆測因果。

## F. Queue-age summary

| Run / class | Samples | Mean (ms) | P50 (ms) | P95 (ms) | Max (ms) |
|---|---:|---:|---:|---:|---:|
| E1 LL | 1,996 | 0.702337 | 0.717200 | 1.331650 | 2.028000 |
| E1 BE | 12,480 | 1.170615 | 1.112425 | 1.790950 | 2.051075 |
| E2 LL | 1,996 | 1.836762 | 1.803300 | 2.832750 | 3.282700 |
| E2 BE | 12,480 | 1.167958 | 1.115800 | 1.769000 | 2.024900 |

## G. 重現與驗證

```bash
python3 scripts/ns3_tools.py setup
cd .local/ns-3 && ./ns3 build scratch/wifi-ofdma-mixed-traffic && cd ../..

python3 scripts/mixed_traffic_checkpoint.py run \
  --scheduler rr --run-id E1-RR-seed1 \
  --output .local/mixed-traffic-checkpoint/E1-RR-seed1 \
  --duration 5s --be-rate 8Mbps --seed 1 --rng-run 1

python3 scripts/mixed_traffic_checkpoint.py run \
  --scheduler queue-age --run-id E2-QueueAge-seed1 \
  --output .local/mixed-traffic-checkpoint/E2-QueueAge-seed1 \
  --duration 5s --be-rate 8Mbps --seed 1 --rng-run 1
```

分析器的 acceptance checks 包括 mapping 唯一性、4/4 class、TID/AC、event pairing、
flow counts、queue age 非負、HE-MU 存在、RU legality、每 PPDU 最多四人，以及 scheduler
final/PHY ordered equality。任何一項失敗，run command 都回傳非零。

## H. Blockers、解法與下一步

1. **多 seed 尚未完成**：限制是不跑長模擬。解法是以同一 harness 跑 RNG run 2--10，
   匯總 mean/CI；完成前禁止改善宣稱。
2. **class-agnostic age 不是 LL-aware policy**：目前 class 只用於觀測與分析。下一個 policy
   必須先定義 deadline/urgency、fairness safeguard 與 overload behavior，再在新 attribute
   後實作，不應偷偷改 RR default。
3. **raw traces 太大，不適合 git**：保留在 `.local`，manifest 保存 SHA-256；commit 小型
   summaries、圖與 reproduction commands。
4. **Engineer A raw archive 仍不可得**：官方 364 已獨立重現，但不能宣稱核對其外部 archive
   每一列。若取得 archive，再依 manifest checksum 驗證。

推薦下一步：先跑 seed/run 2--10 的 E1/E2 paired matrix 與 4/8/12 Mbit/s BE load sweep，
確認現有 class-agnostic age 的穩定行為；之後才提出 LL-aware policy acceptance criteria。

## I. 兩張英文簡報摘要

### Slide 1 — Check-point implementation and verification

- Built a reproducible ns-3.49 Wi-Fi 6 DL OFDMA scenario: 1 AP, 8 STAs, 4 LL + 4 BE UDP flows.
- Both application classes use TID 0 / AC_BE; class labels do not alter EDCA priority.
- Added packet-level delay/loss metrics, AID/MAC/flow mapping, queue-head age traces, final RU traces, and AP PHY HE-MU traces.
- E1 and E2 each produced 3,619 DL HE-MU transmissions and 14,476 RU allocations.
- Ordered scheduler allocations exactly matched ordered PHY transmissions in both runs.

### Slide 2 — Seed-1 result and next decision

- E1 RR vs. E2 class-agnostic queue age had identical throughput: 32.6336 Mbit/s aggregate, zero observed loss.
- LL P95 delay changed from 1.543 ms to 3.044 ms; this run does not support an improvement claim.
- Result scope: one deterministic paired seed; descriptive, not statistically conclusive.
- Next: run paired multi-seed and BE-load sweeps, then define LL deadline and fairness acceptance criteria before implementing an LL-aware policy.
