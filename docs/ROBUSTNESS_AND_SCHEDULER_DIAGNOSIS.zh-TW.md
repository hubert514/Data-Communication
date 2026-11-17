# Wi-Fi 6 OFDMA 實驗穩健性與排程機制診斷

## 執行摘要

本次工作在既有 `feature/rr-queue-age-scheduler` 與 `0134dd4a` 之上完成，沒有
重跑專案、合併分支或實作新的 LL-aware policy。已完成三項獨立驗證：12 Mbps
的 200/500/1000 ms drain 敏感度（18 runs）、4/8/12 Mbps 的 RngRun 1–10
擴充（60 runs），以及 8/12 Mbps 的 observation-only 排程機制 trace（12 runs）。

主要結論如下：

- 12 Mbps 下 Queue-Age 的 BE delivery 優勢不是 200 ms receive cutoff 的假象。
  延長到 500 與 1000 ms 後，封包、scheduler 與 PHY trace 均與 200 ms 逐列完全
  相同；Queue-Age 相對 RR 的 BE simulation-end PDR 仍高 `0.040513`，五秒 offered
  interval 正規化的 final delivery 仍高 `1.94432 Mbps`。
- 十組配對 run 顯示，Queue-Age 的 LL mean delay 在 8 Mbps 由 `0.896337` 增為
  `2.022914 ms`（`2.257×`），而 aggregate delivery 與 BE PDR 完全不變；在
  12 Mbps 則由 `3.080321` 增為 `37.221717 ms`（`12.093×`），同時 aggregate
  final delivery 增加 `1.939392 Mbps`、BE PDR 增加 `0.040410`。
- 8 Mbps 的機制證據排除「平均 backlog 或平均 aggregation 變大」作為主要解釋：
  RR 與 Queue-Age 的 class-level queue、MPDU count、aggregation share 與 PSDU
  byte mean 完全相同。兩 policy 在每個比較 PPDU 前的 credit order 100% 相同，
  但 final STA set 僅有 `76.6–77.1%` 相同、PHY timestamp 僅有 `71.0–72.4%`
  相同。因此最符合證據的解釋是 queue-age priority 改變「哪一批 STA 在何時被
  服務」，而 aggregate allocation/throughput 掩蓋了 LL waiting-time 變化。
- 新 instrumentation 對 RR 與 Queue-Age 各八份既有輸出進行 16 組逐列比較，
  scheduler、RU、PHY timestamp、PSDU bytes、封包結果與應用層 summary 全部完全
  相同。可觀察結果支持 instrumentation 為 observation-only。

所有信賴區間都以獨立 RngRun 為單位。十組或三組配對資料只作描述性推論，不因
區間狹窄而自動宣稱統計顯著或可外推至其他拓樸。

## 1. 範圍與可重現狀態

固定實驗仍是 ns-3.49 commit `418210e8914e9f6bcb5cddbcc94a2cecb7853b68`、
1 AP / 8 STA、4 LL / 4 BE、20 MHz DL HE-MU OFDMA、五秒 application traffic。
RR 與 class-agnostic Queue-Age 使用相同拓樸、PHY/MAC、流量、seed 與配對 RngRun。

本次新增：

1. 可中斷、可續跑且不覆寫已驗證 raw run 的 drain runner。
2. RngRun 1–10 的配對差、ratio、sample SD 與 95% Student-t interval。
3. `MechanismObservation` trace：pre-selection credit order、credit value、已接受
   candidate 的 const queue packets/bytes，以及 post-credit-update order/selected。
4. 實際 PHY PSDU 的 `mpdu_count` 與既有 `psdu_bytes`、RU、AID 對應。
5. exact instrumentation non-regression 與三套 reproducibility manifest。

原始 trace 均保留在 `.local/`，Git 僅收錄 runner、patch、derived CSV/JSON、checksum
與文件。證據入口為 [drain manifest](evidence/b-drain-sensitivity-01/MANIFEST.md)、
[expanded manifest](evidence/b-expanded-validation-01/MANIFEST.md) 與
[mechanism manifest](evidence/b-mechanism-diagnosis-01/MANIFEST.md)。

## 2. Drain-time 敏感度

### 2.1 測量定義

各指標刻意分開，避免把 receive cutoff 與穩態 throughput 混為一談：

| 指標 | 分子 | 分母／時間窗 |
|---|---|---|
| `pdr_at_app_stop` | app stop 前收到的 packets | 五秒內產生的 packets |
| `pdr_at_sim_end` | app stop 前與 drain 中收到的 packets | 五秒內產生的 packets |
| `app_stop_delivery_mbps` | app stop 前收到的 bytes | 固定五秒 offered interval |
| `final_delivery_offered_interval_mbps` | simulation end 前收到的全部 bytes | 固定五秒 offered interval |
| `receive_window_goodput_mbps` | simulation end 前收到的全部 bytes | `5 s + drain` |
| `application_undelivered_backlog` | sink 未觀察到的 application packets | simulation end 截止；只是 proxy |

`final_delivery_offered_interval_mbps` 是最終交付量用五秒 offered interval 正規化，
不是另一次穩態鏈路 throughput 測量。`receive_window_goodput_mbps` 的分母會隨 drain
增長，即使沒有新增封包抵達也會下降。

### 2.2 實際結果

下表是三個 RngRun 的 BE class mean：

| Drain | Policy | PDR@app stop | PDR@sim end | Drain RX packets | End undelivered | Final delivery / 5 s (Mbps) | Receive-window goodput (Mbps) |
|---:|---|---:|---:|---:|---:|---:|---:|
| 200 ms | RR | 0.934123 | 0.956073 | 548.667 | 1098.000 | 45.88416 | 44.11938 |
| 200 ms | Queue-Age | 0.971142 | 0.996586 | 636.000 | 85.333 | 47.82848 | 45.98892 |
| 500 ms | RR | 0.934123 | 0.956073 | 548.667 | 1098.000 | 45.88416 | 41.71287 |
| 500 ms | Queue-Age | 0.971142 | 0.996586 | 636.000 | 85.333 | 47.82848 | 43.48044 |
| 1000 ms | RR | 0.934123 | 0.956073 | 548.667 | 1098.000 | 45.88416 | 38.23680 |
| 1000 ms | Queue-Age | 0.971142 | 0.996586 | 636.000 | 85.333 | 47.82848 | 39.85707 |

三種 drain 的 application-stop PDR、simulation-end PDR、drain RX、undelivered、delay
與五秒正規化 final delivery 全部相同。48 組逐列 trace 比較（3 runs × 2 policies ×
2 longer drains × 4 artifacts）也全部相同；排除的只有 `run_id`。這表示所有可抵達
sink 的封包在 200 ms 內已抵達，延長 simulation stop 沒有額外 scheduler/PHY 動作。

Queue-Age − RR 的 BE simulation-end PDR 為 `+0.040513`，描述性 95% CI
`[0.038922, 0.042104]`；五秒正規化 final delivery 為 `+1.94432 Mbps`，CI
`[1.86795, 2.02069]`，在三個 drain 都完全相同。Receive-window goodput 差值因分母
機械性增大而由 `1.86954` 降至 `1.62027 Mbps`，不能解讀成多傳或少傳了封包。

資料見 [drain per-run summary](evidence/b-drain-sensitivity-01/drain-per-run-summary.csv)、
[paired comparison](evidence/b-drain-sensitivity-01/drain-paired-comparison.csv) 與
[trace equivalence](evidence/b-drain-sensitivity-01/drain-trace-equivalence.csv)。

## 3. RngRun 1–10 擴充結果

共 60 runs / 30 matched pairs，全部 validation 與 stored raw checksum 通過。每個
配對差先在同一 RngRun 內計算，再以十個 RngRun 計算 sample SD 與雙尾 95%
Student-t interval。

| BE load / flow | RR LL mean (ms) | Queue-Age LL mean (ms) | Paired Δ mean (95% CI) | Mean ratio | Aggregate delivery Δ | BE PDR Δ |
|---:|---:|---:|---:|---:|---:|---:|
| 4 Mbps | 0.584170 | 0.601784 | +0.017613 `[0.017484, 0.017743]` | 1.030× | 0 | 0 |
| 8 Mbps | 0.896337 | 2.022914 | +1.126577 `[1.113311, 1.139844]` | 2.257× | 0 | 0 |
| 12 Mbps | 3.080321 | 37.221717 | +34.141397 `[33.998575, 34.284218]` | 12.093× | +1.939392 Mbps | +0.040410 |

12 Mbps aggregate delivery 差的描述性 CI 為 `[1.912546, 1.966238] Mbps`；BE PDR
差的 CI 為 `[0.039851, 0.040970]`。LL P95 在 12 Mbps 增加 `82.418771 ms`
（ratio `15.774×`）。8 Mbps 的 aggregate delivery、BE PDR、class Jain throughput
與 BE allocation share 均為零差且零變異，但 LL delay 與 HE-MU 時序有實際 run 間
變異；因此不能用 aggregate throughput 相同推論 latency path 相同。

完整數值見 [statistical summary](evidence/b-expanded-validation-01/statistical-summary.csv)、
[paired rows](evidence/b-expanded-validation-01/paired-comparison.csv) 與
[verification](evidence/b-expanded-validation-01/verification.csv)。

## 4. Observation-only instrumentation 與 non-regression

Patch `003-scheduler-mechanism-observation.patch` 在既有 RR code path 中增加：

- 排序前 `m_staListDl[primaryAc]` 的 AID、credit、順序；
- 既有 candidate 已接受時，以 `WifiMacQueue::GetNPackets(queueId)` 與
  `GetNBytes(queueId)` 讀取 const counters；沒有額外 `PeekNextMpdu()`；
- final allocation 更新 credit 後的順序、credit 與 selected flag；
- 已建構 PHY PSDU 的 MPDU count 與 PSDU bytes。

它不新增 RNG call、Simulator event、queue mutation、eligibility branch、credit formula、
RU allocation 或 retry 行為。`GetNPackets/GetNBytes` 是觀察既有 queue state，candidate
head age 仍由既有 eligibility peek 取得的 MPDU 計算。

Non-regression 以 pre-instrumentation 與 instrumented 的 8 Mbps / RngRun 1 比較：

| Policy | Artifact comparisons | Packet-event rows | Scheduler rows | PHY rows | Result |
|---|---:|---:|---:|---:|---|
| RR | 8 | 37,320 | 103,832 | 14,476 | all exact |
| Queue-Age | 8 | 37,320 | 47,084 | 14,476 | all exact |

所有 common fields 逐列完全相同，包括 exact PHY timestamp、AID、RU、PSDU bytes、
packet outcome 與 application metrics。只排除不同的 `run_id` 與 legacy PHY 不存在的
新 `mpdu_count` 欄位。證據見
[non-regression CSV](evidence/b-mechanism-diagnosis-01/instrumentation-nonregression.csv)。

## 5. 為何 class-agnostic Queue-Age 增加 LL delay

### H1：BE backlog 主導 scheduler opportunities

**8 Mbps：不支持為主要解釋。** 已接受 candidate 的 decision-weighted queue mean 為
LL `1.000`、BE `1.335979` packets，且兩 policy 的 per-run means 完全相同。BE 有短暫
burst 的可能，但沒有龐大 backlog 或 policy 間平均 queue 差。

**12 Mbps：支持。** RR 的 BE queue mean 為 `105.438774`，Queue-Age 為
`80.268833` packets；Queue-Age 的 LL mean 為 `5.443888`。BE backlog 明顯主導，且
Queue-Age 配合較高 BE service share（RR `0.632636`、Queue-Age `0.907408`）降低 BE
undelivered proxy。限制是 queue samples 只在 candidate accepted 時取得，並非固定週期
queue snapshot。

### H2：Queue-Age priority 擾動原 airtime-credit 優先順序

**支持，但需精確描述。** 8 Mbps 的每個 index-aligned PPDU 前，兩 policy 的
pre-selection credit order 100% 相同；Queue-Age 仍使 final selected AID set 只有
`76.6–77.1%` 與 RR 相同。換言之，policy 從相同 credit state 選出不同集合，而非
instrumentation 改寫 credit。聚合後 selected pre-credit rank mean 恰巧同為
`4.948210`，顯示單一平均值會掩蓋 per-decision membership displacement。

12 Mbps 下，Queue-Age 相對 RR 的 selected pre-credit rank mean 增加 `1.080260`
（三-run 描述性 CI `[1.068660, 1.091861]`）；先前 policy decision 又回饋至後續 credit
state，因此兩條序列的 pre-credit order 不再全同。後段 credit divergence 是 policy
feedback，不能反向當作最初原因。

### H3：Queue-Age 改變 LL service timing，而不只 aggregate allocation share

**8 Mbps 強力支持。** RR 與 Queue-Age 都有相同的 PPDU 數、aggregate throughput、
class allocation share、queue/aggregation mean；但 exact final batch 只相同
`76.6–77.1%`，含 aggregation 的 exact PHY batch 只相同 `66.1–67.4%`，exact PHY
timestamp 只相同 `71.0–72.4%`。這與 LL mean delay `2.257×` 同時出現，支持
service timing/sequence 是 aggregate metric 看不到的主要機制。

### H4：BE aggregation 或 PSDU size 造成較長 LL waiting

**不支持「平均大小是主要原因」。** 8 Mbps 的 RR/Queue-Age BE MPDU count mean
都為 `1.335979`、aggregated allocation share 都為 `0.335979`、PSDU mean 都為
`1697.364694 bytes`；LL 均為單 MPDU、`270 bytes`。12 Mbps 的 BE aggregation
也近乎相同：MPDU count 配對差 `0.001946`、PSDU bytes 差 `2.475508`，三-run
描述性 intervals 都跨過零。

這不排除個別 aggregate 在不同時間出現而中介 timing；它只排除平均 BE aggregate
變大作為充分解釋。12 Mbps 的 Queue-Age LL aggregation 上升更合理地視為 LL 已累積
backlog 的結果，不能顛倒因果。

### H5：Overload 下 Queue-Age 改善 BE draining、代價是 LL service

**12 Mbps 支持受控 policy association。** 十組配對中 Queue-Age 的 aggregate final
delivery 增加 `1.939392 Mbps`、BE PDR 增加 `0.040410`，同時 LL mean delay 增加
`34.141397 ms`、LL mean service gap 約由 `10.0013` 增至 `49.7832 ms`。Drain
敏感度顯示差異延長至 1000 ms 仍存在。8 Mbps 則不支持此 delivery trade-off：LL
delay 上升但 delivery、PDR 與 allocation aggregate 不變。

這些是相同輸入下的 policy contrast；它支持機制鏈的一致性，但仍不等同於已隔離
每一個內部變數的單一因果實驗。完整分類見
[hypothesis assessment](evidence/b-mechanism-diagnosis-01/hypothesis-assessment.csv)。

## 6. 測試與 patch 可重建性

已實際完成：

- Project Python unit tests：`17/17` passed。
- ns-3 `wifi-mac-ofdma`：`1/1` passed。
- ns-3 `wifi-ru-allocation`、`wifi-mac-queue`、`wifi-queue-scheduler`、
  `wifi-traced-callback-typedef`：各 `1/1` passed。
- `scratch/wifi-ofdma-mixed-traffic`：build passed。
- Patch 001 → 002 → 003 在 pinned SHA 上 forward apply，三個 patched source 與
  工作 checkout byte-for-byte 相同；003 → 002 → 001 reverse 後 clean。
- Instrumentation non-regression：`16/16` artifact comparisons exact。
- Drain validation：`18/18` runs passed；expanded validation：`60/60` passed；
  mechanism runs：`12/12` passed。

## 7. 限制

1. 十個 RngRun 仍只涵蓋單一 topology、channel model、PHY/MAC 設定與 seed；95% CI
   依賴 run-level independence、近似常態 paired differences 與正確配對假設。
2. Mechanism diagnosis 僅三個 matched RngRun；其中 candidate/PPDU rows 是 run 內
   samples，不能當成獨立 replications。
3. `application_undelivered_backlog` 只代表 simulation end 前 sink 未收到；沒有直接
   區分 MAC queue 殘留、admission/expiry/drop 或其他未交付原因。
4. Queue occupancy 是 accepted-candidate conditional sample，不是全 STA 固定時間採樣。
5. 12 Mbps 因 RR 與 Queue-Age PPDU 數不同，cross-policy sequence 只比較共同 prefix；
   不能把後段不存在的 PPDU 當成 mismatch row。
6. 本階段沒有實作 LL-aware/fairness scheduler，亦未測試其他 STA 數、LL rate、RU
   policy、channel loss 或 No-OFDMA。

## 8. Final Demo 建議研究方向

下一個 policy 應從本次失敗機制直接修正，而不是繼續使用 class-agnostic oldest-first：

1. 僅對 LL candidate 計算 `queue_age / LL_deadline` urgency；不讓大量 BE backlog 的
   oldest packet 無條件壓過低速 LL。
2. 只有超過門檻的 urgent LL 做 stable priority；其餘 slot 依原 RR credit order
   填入，以保留 airtime fairness 結構與 deterministic tie-break。
3. 加入明確 BE service-gap guard，但只在 BE pending 且超過門檻時保留有限 slot，
   避免 LL priority 反向造成 BE starvation。
4. 保留本次 `MechanismObservation` 與 exact non-regression harness，先驗證 policy 關閉
   時與 RR 完全相同，再做 RngRun 1–10 的 RR / class-agnostic Queue-Age / LL-aware /
   LL-aware+fairness 四方配對比較。
5. Primary outcomes 應預先固定為 LL mean/P95/deadline miss、BE final delivery/PDR、
   class fairness 與 service gap；同時保留 explicit receive-window denominators。

驗收目標不應只寫「降低 LL delay」，而應要求：8 與 12 Mbps 下 LL latency 改善、BE
delivery 不低於預先設定 guardrail、無 starvation、合法 RU、policy-off exact
non-regression，以及多個 topology/load 的 run-level robustness。
