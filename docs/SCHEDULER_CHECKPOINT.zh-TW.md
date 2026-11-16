# ns-3.49 RR OFDMA Scheduler Check-Point 實作與驗證報告

實作日期：2026-11-17（Asia/Taipei）
專案基底：`9a91cc10e1d515aae1db006c4929ddc5a154f669`
ns-3 基底：`418210e8914e9f6bcb5cddbcc94a2cecb7853b68` (ns-3.49)

## 1. 結論與狀態

| 項目 | 狀態 | 實際結果 |
|---|---|---|
| 可重現的官方 RR DL OFDMA baseline | **TESTED / PASSED** | R0 成功，364 DL HE_MU，1456 user allocations |
| candidate queue-age TraceSource | **IMPLEMENTED / TESTED / PASSED** | 1456 筆有效 `candidate_head_mpdu_age` |
| final RU allocation TraceSource | **IMPLEMENTED / TESTED / PASSED** | 1456 筆 final rows 全部對上 PHY |
| R0/R1/R2 非回歸 | **TESTED / PASSED** | ordered time/AID/RU/MCS/NSS 完全相同 |
| class-agnostic queue-age prototype | **IMPLEMENTED / TESTED / PASSED** | fixture 中 selected-STA set 改變 2 次 |
| 官方 ns-3 相關 test suites | **TESTED / PASSED** | 5 suites PASS |
| Engineer A raw archive 獨立重算 | **BLOCKED** | 檔案需 repo login，本機不存在 raw archive |
| 專案 4 LL / 4 BE baseline 整合 | **NOT IMPLEMENTED** | Engineer A 專案情境尚未出現於本地 main |
| LL-aware policy / 效能改善宣稱 | **NOT IMPLEMENTED** | 本階段僅驗證 MAC scheduler 可觀測性與功能差異 |

## 2. 實作內容

### 2.1 可重建上游 patch

`patches/001-rr-queue-age-observation.patch` 對應下列 ns-3 檔案：

- `src/wifi/model/he/rr-multi-user-scheduler.h`：新增 TraceSource 狀態、decision ID，以及預設關閉的 queue-age policy attribute。
- `src/wifi/model/he/rr-multi-user-scheduler.cc`：在原有 candidate path 使用已取得的 MPDU 發出觀測，並在 `FinalizeTxVector()` 後發出 final allocation。
- `examples/wireless/wifi-he-network.cc`：實作可選 CSV sink、prototype CLI 開關與 deterministic traffic fixture。

專案側新增 `scripts/scheduler_checkpoint.py`，負責執行、保存 metadata/checksum、解析 PHY HE_MU、比對 R0/R1/R2 與驗證 prototype。

### 2.2 CSV schema

```text
run_id,decision_id,phase,time_ns,link_id,access_category,scan_order,
aid,mac,tid,mpdu_uid,mpdu_timestamp_ns,mpdu_age_ns,
eligibility_status,final_selected,ru_type,ru_index,mcs,nss
```

無 MPDU 或不適用的欄位留空，不以 0 偽裝。`time_ns` 為 simulation time。

## 3. RR scheduler architecture

1. `MultiUserScheduler::NotifyAccessGranted()` 設定 EDCA、available TXOP time、channel width 與 link ID，然後呼叫 `SelectTxFormat()`。
2. RR 選擇 DL MU 時進入 `TrySendingDlMuPpdu()`，取得 primary AC 與要檢查的 TID set。
3. `m_staListDl[primaryAc]` 是以 airtime credits 排序的 station list。每個 `MasterInfo` 提供 AID、MLD/link MAC 與 credits。
4. 原有 loop 先確認 BA agreement，再以
   `GetQosTxop(ac)->PeekNextMpdu(linkId, tid, address)` 查看該 STA/TID 的下一個 eligible queue-head MPDU。
5. `CreateAliasIfNeeded()` 處理 multi-link alias，`TryAddMpdu()` 以暫時 RU/TX vector 確認 size/time/TXOP constraints；通過才放入 private `m_candidates`。
6. `ComputeDlMuInfo()` 呼叫 `FinalizeTxVector()`，依實際 candidate 數量重新分配合法 RU，並刪掉無法服務的尾端 candidates。
7. 完成 PSDU map 後，`UpdateCredits()` 為全體 STA 增加 airtime credits、對已傳送 STA 扣除依 bandwidth share 計算的 credits，再以 credits 降冪重排下一輪順序。

## 4. Queue-age accessibility 與語意

觀測點是原有 candidate loop 已經呼叫 `PeekNextMpdu()` 之後。觀測式為：

```cpp
const Time age = Simulator::Now() - mpdu->GetTimestamp();
```

- **MPDU 是誰**：指定 link/AID MAC/TID 下，原有 queue scheduler 回傳的下一個 eligible queue-head `WifiMpdu`，不是任意 queue element。
- **eligibility**：先通過 BA agreement，且 `PeekNextMpdu()` 非 null；後續仍要通過 `TryAddMpdu()` 的 size/time/TXOP 限制才是 `candidate_accepted`。
- **AID/MAC/TID/AC**：AID 與 MAC 來自當前 `MasterInfo`；TID 來自原有 TID loop；AC 由 `QosUtilsMapTidToAc(tid)` 取得。
- **timestamp 與 retransmission**：`WifiMpdu` constructor 只寫入一次 `OriginalInfo::m_timestamp`。`IncrementRetryCount()` 不改 timestamp；alias 的 `GetTimestamp()` 回讀 original timestamp，因此 retry/alias 保留原 MPDU 建立時間。
- **aggregation 限制**：此值是 candidate head MPDU 年齡。A-MPDU 中後續聚合的 MPDU 不由這一筆代表；A-MSDU 則是 wrapper MPDU 的 construction time。不能將它解釋為 application end-to-end latency。
- **observation-only 性質**：R1/R2 沒有新增 `PeekNextMpdu()`、RNG 呼叫或 simulation event。TraceSource 只讀取原有 `mpdu` 與 scheduler state。

## 5. 環境、build 與執行指令

### 5.1 環境

```text
macOS Darwin 25.6.0 arm64
Apple clang 21.0.0
CMake 4.5.0
Python 3.13.7
Ninja 1.13.0
```

### 5.2 Setup/build

```bash
./scripts/setup_ns3.sh
brew install cmake
./scripts/build.sh
cd .local/ns-3
./ns3 build wifi-he-network
```

`setup_ns3.sh` 將 ns-3 固定在指定 SHA。成功 setup/build evidence 分別位於：

```text
.local/evidence/20261116T181829Z-setup-5fa5ca82/
.local/evidence/20261116T183223Z-build-dc05f095/
```

### 5.3 Baseline 與非回歸

```bash
python3 scripts/scheduler_checkpoint.py run --label R0 --rng-run 1
python3 scripts/scheduler_checkpoint.py run --label R1_FINAL --rng-run 1
python3 scripts/scheduler_checkpoint.py run --label R2_FINAL --rng-run 1 --trace-sink
python3 scripts/scheduler_checkpoint.py compare \
  --labels R0 R1_FINAL R2_FINAL --report comparison-final.json
```

Harness 實際傳給官方 example 的共同參數：

```text
wifi-he-network --udp=1 --downlink=1 --nStations=8 --maxMuStas=4
--dlAckType=MU-BAR --enableUlOfdma=0 --enableBsrp=0 --frequency=5
--channelWidth=20 --mcs=5 --guardInterval=800 --simulationTime=2s
--distance=5 --RngSeed=1 --RngRun=1
```

### 5.4 Prototype fixture

```bash
python3 scripts/scheduler_checkpoint.py run \
  --label FIX_RR --rng-run 1 --trace-sink --queue-age-fixture
python3 scripts/scheduler_checkpoint.py run \
  --label FIX_QA --rng-run 1 --trace-sink \
  --queue-age-fixture --queue-age-priority
python3 scripts/scheduler_checkpoint.py prototype-compare \
  --baseline FIX_RR --prototype FIX_QA \
  --report fixture-prototype-comparison.json
```

### 5.5 ns-3 test suites

```bash
cd .local/ns-3
./test.py -n -s wifi-mac-ofdma
./test.py -n -s wifi-ru-allocation
./test.py -n -s wifi-mac-queue
./test.py -n -s wifi-queue-scheduler
./test.py -n -s wifi-traced-callback-typedef
```

## 6. 實際測試結果

### 6.1 R0/R1/R2

| Run | Exit | DL HE_MU | PHY user rows | 與 R0 ordered tuples 一致 |
|---|---:|---:|---:|---|
| R0 pristine | 0 | 364 | 1456 | reference |
| R1_FINAL trace disconnected | 0 | 364 | 1456 | true |
| R2_FINAL CSV sink connected | 0 | 364 | 1456 | true |

Ordered tuple 包含 transmission index、simulation timestamp、AID、RU type/index/segment、MCS 與 NSS。比對結果不依賴 log 排版。

R2_FINAL CSV 驗證：

- candidate rows / rows with age：1456 / 1456
- final rows：1456
- age range：6,000 ns 至 61,631,000 ns
- age 非負：true
- MPDU timestamp 不晚於 observation time：true
- `age == time_ns - mpdu_timestamp_ns`：true
- final allocation 與 PHY HE_MU 逐筆相符：true

因此 Engineer A 報告的 364 在同一 ns-3 SHA 與參數下被本機 R0 **獨立重現**。但由於 Engineer A raw archive 未在本地，本工作不聲稱對該 archive 的 checksum 或每行 log 完成獨立驗證。

### 6.2 Queue-age prototype

`UseQueueAgePriority` 預設為 false。開啟時，prototype 只在原有 TID set 與 BA 條件下預掃 queue heads，以最早 timestamp 穩定排序 STA list，平手時保留原 RR order；後續 BA、eligible MPDU、TXOP/time 與 RU legality 均由原有路徑檢查。

Fixture 將前四個 UDP flows 延後 2 ms，使第 5–8 STA 在同時競爭時擁有較老 head MPDU。首次 selected-set 差異：

| time | Policy | Selected AIDs | head age | RU |
|---:|---|---|---:|---|
| 3,218,800 ns | RR | 1,2,3,4 | 218,800 ns each | 52-tone indices 1–4 |
| 3,218,800 ns | Queue age | 5,6,7,8 | 265,980 ns each | 52-tone indices 1–4 |

實際結果：FIX_RR 有 368 次 DL HE_MU，FIX_QA 有 367 次，selected-STA set 有 2 個 transmission index 不同。這是可重現的 **functional behavior difference**，不是效能改善結論。驗證器確認：

- final selected 全部屬於 accepted eligible candidates：true
- 每次選擇觀測到的 oldest four：true
- RU 無重疊且每次不超過 4 STA：true
- CSV final allocation 與 PHY HE_MU 相符：true

### 6.3 官方 tests

| Suite | 結果 |
|---|---|
| `wifi-mac-ofdma` | **PASS**, 116.242 s |
| `wifi-ru-allocation` | **PASS** |
| `wifi-mac-queue` | **PASS** |
| `wifi-queue-scheduler` | **PASS** |
| `wifi-traced-callback-typedef` | **PASS** |

專案側 `python3 -m unittest discover -s tests -v` 也已 **PASS (6/6)**。新增 patch 後曾暴露 macOS `/var`/`/private/var` 別名造成的 `Path.relative_to()` 錯誤；`scripts/ns3_tools.py` 現在會先 resolve root，再計算 patch 相對路徑。

過程中 `./test.py -s wifi` 因 `wifi` 不是 suite 精確名稱而 exit 2（**FAILED: command usage**）；改用實際 suite 名後全數通過。第一次平行執行也觸發 `test.py` 同秒輸出目錄衝突，改為序列執行後通過；這是 test harness 限制，不是 suite failure。

## 7. Acceptance criteria

| Criterion | 狀態 | 證據 |
|---|---|---|
| R0/R1/R2 全部正常結束 | **PASSED** | exit 0 |
| DL HE_MU 數量一致 | **PASSED** | 364 / 364 / 364 |
| ordered transmission timestamps 一致 | **PASSED** | canonical tuple equality |
| selected STA sequence 一致 | **PASSED** | canonical tuple equality |
| RU type/index 一致 | **PASSED** | canonical tuple equality |
| MCS/NSS 一致 | **PASSED** | canonical tuple equality |
| instrumentation final 對上 PHY | **PASSED** | 1456 / 1456 |
| ages 非負 | **PASSED** | 1456 rows |
| MPDU timestamp 不在未來 | **PASSED** | 1456 rows |
| observation 無額外 queue lookup | **PASSED** | 實作傳入原有 `mpdu` |
| observation 不影響 policy | **PASSED** | 無 selection branch 讀取 trace 值；R0/R1/R2 等價 |
| 無新增 RNG/events | **PASSED** | 實作無 RNG/Schedule；R0/R1/R2 等價 |
| queue age 改變 selected STA | **PASSED** | fixture selected-set changes = 2 |
| prototype final candidates eligible | **PASSED** | automated set containment |
| prototype RU legal | **PASSED** | automated uniqueness/capacity + PHY match |

## 8. 技術問題與解法

1. **Engineer A raw logs 不可得**：只能查閱 remote-tracking branch 的 manifest、excerpt、metadata 與 recomputation output。解法是保留 limitation，並用同 SHA/參數獨立建立 R0；後續取得 archive 時再依 manifest checksum 核對。
2. **private candidate/RU state**：不從外部穿透 private state，改在 scheduler 原有 candidate/finalization 點發出 TraceSources，CSV writer 留在 example 側。
3. **`PeekNextMpdu()` 可能影響 queue scheduler state**：observation-only path 不再呼叫，使用原 loop 已有 pointer。只有明確開啟的 prototype ranking 有額外 lookup，並且這是 policy 行為，非觀測行為。
4. **final scheduler decision 不等於任意情境下一定 PHY send**：CSV 使用 `phase=final` 而不命名為 PHY TX，並在本次控制情境以 PHY log 逐筆對照。
5. **LL/BE identity 尚未整合**：目前 policy 明確標示 class-agnostic，不將 queue age 當作 LL 標籤。

## 9. 證據位置與建議下一步

證據索引見 `docs/evidence/b-scheduler-01/MANIFEST.md`。大型 raw logs/CSV 位於 `.local/scheduler-checkpoint/`，不會汙染 Git。建議下一個 engineering task 是：

1. 將 Engineer A 的 4 LL / 4 BE 情境合併到本地後，以明確 AID/TID/AC/flow mapping 連接 LL/BE identity。
2. 先用本 TraceSource 在 RR 下量測 per-class `candidate_head_mpdu_age`，並另行取得 application send/receive delay；不混用兩種 metric。
3. 將 class-agnostic prototype 拆成獨立 scheduler variant 或 protected ranking hook，加入 LL-aware parameter，並以 seeds/runs 1–3 進行 RR vs policy 實驗。
4. 報告 throughput、end-to-end delay、tail delay 前，建立多 seed confidence interval 與等價 offered-load 檢查。

## 10. English Check-Point slide summary

### Slide 1 — Verified RR Baseline and Instrumentation

- Reproduced the ns-3.49 official 8-STA DL OFDMA baseline at the pinned upstream commit: 364 DL HE_MU transmissions and 1,456 PHY user allocations.
- Added observation-only TraceSources at the existing RR candidate loop and after RU finalization; the CSV sink runs outside the scheduler.
- `candidate_head_mpdu_age = Simulator::Now() - WifiMpdu::GetTimestamp()` is a MAC scheduling observation, not application end-to-end latency.
- R0/R1/R2 had identical ordered timestamps, selected AIDs, RU assignments, MCS, and NSS; all 1,456 final trace rows matched PHY transmissions.

### Slide 2 — Queue-Age Functional Prototype

- Added a disabled-by-default, class-agnostic prototype that ranks stations by the oldest eligible queue-head MPDU while reusing RR BA, TXOP, eligibility, and legal RU machinery.
- In a deterministic 8-STA/4-RU fixture, RR selected AIDs 1–4 while the age policy selected the older AIDs 5–8 at 3.2188 ms.
- Automated checks confirmed eligible final candidates, legal non-overlapping RUs, oldest-four selection, and trace-to-PHY agreement.
- This proves controllable scheduler behavior, not latency or throughput improvement; the next step is integration with the real 4 LL / 4 BE scenario and multi-seed evaluation.
