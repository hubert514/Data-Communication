# Engineer A 工作交接書：模擬環境、RR 基準、流量與量測

文件修訂：r1。更新日期：2026-11-07。時程使用 Asia/Taipei。

**負責人：Engineer A。實際姓名／GitHub 帳號：TODO，由 Technical PM 指定。**

本文將專案規格拆成可執行的工作包。需求與驗收依據仍是根目錄 [README](../README.md)；本文的實作建議不代表新的核准需求。若兩者衝突，以 README 及 PM 記錄的決策為準。

> 你的第一個目標：讓另一位組員能依照留下的環境與命令，重跑官方 OFDMA 範例，接著重跑專案的混合流量 B1，取得可追溯的真實封包與流量資料。

## 0. 開工與版本規範

先讀 [共用版本／協作規範](DEVELOPMENT_WORKFLOW.zh-TW.md)。這份 r1 是工作指示版本，不表示場景已實作、ns-3 已驗收或 project 已發布。

- 從最新 `origin/main` 建立 `feature/simulation-*`，在 PR 記錄完整 base commit；不要繼續把日常開發堆在 bootstrap 分支。
- `configs/ns3-candidate.json` 是候選 lock，ENVIRONMENT.md 記錄接受狀態；更換 tag/SHA 時必須同步並取得 PM 核准，不能只改本機 `.local`。
- 每次交接附 project/upstream SHA、patch 指紋、有效 config、schema 狀態、seed/run、命令、實際輸出與可共享 evidence。
- A 協調 setup/build/run 與 canonical config；B 協調 scheduler patch／series。修改共用接點先對齊 Issue，不複製另一套入口。
- schema／時間窗／deadline 分母／AC/RU/ACK 等改動先提出 migration／研究影響；producer、consumer 與文件同步後由 PM 接受。
- 透過 PR 合併，禁止 force-push `main`；本次文件上線不代表 #1/#5/#9 或 checkpoint 通過。

本文工作包使用 `A-ENV`、`A-BASE`、`A-INTEG` 等名稱；研究方案仍是 `B1`／`P1`／`P2`，兩者不是同一套編號。

### 工作包輸入／交付／驗收對照

| 工作包 | 目標窗口／相依 | 明確交付位置 | 完成所需證據與交接 |
|---|---|---|---|
| A-ENV-01：工具鏈與 build | 11/7–10；候選 lock＋bootstrap 工具 | `docs/ENVIRONMENT.md`、必要 `scripts/` 改動、#1 | 乾淨 setup/build 命令與 logs、完整版本；交 B/PM。缺工具的回報只算 Blocked |
| A-ENV-02：官方 DL MU | 11/7–10；A-ENV-01 可執行環境 | #1 evidence；ENVIRONMENT 的查證結果 | 實際 DL MU、served STA、RU；與 B 判讀、交 PM。exit 0 不足 |
| A-CONTRACT-01：共同契約 | 11/7–10；A/B source／環境發現 | `docs/DESIGN.md`、#3 | entry/config/ID/time/schema 全部有定義或明確阻礙，PM 決策後供平行實作 |
| A-BASE-01：共同場景與流量 | 11/11–13；PM 接受的版本／契約 | `sim/`、核准 `configs/`、#5 | 1 AP/8 STAs、4 LL/4 BE、同 AC、官方 RR，可重跑且有 DL MU；交 B |
| A-METRICS-01：真實資料 | 11/11–13；A-BASE-01＋核准 metric/window 定義 | flow/packet writer、raw files/manifest、#5 | 逐封包配對、單位、loss/drain、真實 aggregates 一致；交 PM/D |
| A-RUN-01：canonical run | 11/11–13；共同入口與量測 | `scripts/`、run metadata、#5 | 一個實際可跑的 RR 命令、拒絕不支援參數、失敗也保存證據；交 B/PM |
| A-INTEG-01：整合交付 | 11/14–15；A 的基準／量測與 B 已實作 probe | 整合 PR、#9、PM_STATUS | 乾淨安裝後 RR 回歸、共用 schema/CLI 正常、D 可取到真實資料；交 PM |

各包細節見下列章節。表中的產物尚未存在者皆為 TODO；以測試／證據與 PM 接受判定完成，不以「檔案已建立」判定。遇到相依未完成時，先做不依賴它的排錯／調查並回報 Blocked。

## 1. 接手時的真實狀態

| 項目 | 已知狀態 | 對你的影響 |
|---|---|---|
| README | 已提交到 `main` | 先讀第 4–10、13 節 |
| 專案骨架與工具 | [PR #13](https://github.com/hubert514/Data-Communication/pull/13) 已合併到 `main` | 從最新 `origin/main` 開工，記錄自己的 base SHA |
| ns-3 候選版本 | `ns-3.49`；commit `418210e8914e9f6bcb5cddbcc94a2cecb7853b68` | 版本身分已核對，建置與執行尚未驗收 |
| 候選原始碼下載 | bootstrap 主機成功，重複 setup 成功 | 每位組員仍須在自己的環境驗證 |
| 建置與官方範例 | bootstrap 主機在前置檢查找不到 CMake，尚未編譯或執行 | 這是你優先排除的阻礙 |
| 工具測試 | 六項 bootstrap 安全測試、語法與 GitHub CI 已通過 | 不代表 ns-3、OFDMA 或專案場景已通過 |
| `sim/` | TODO / NOT IMPLEMENTED | 專案 B1 尚未實作 |
| `configs/checkpoint.json` | 規劃用設定草案，尚無讀取器 | 不能把它當成已能執行的場景 |
| `scripts/run.sh`、`scripts/analyze.py` | 明確回報 TODO 並以非零狀態結束 | 現在不能用來產生實驗資料 |
| P1/P2、實驗資料與圖表 | TODO / NOT IMPLEMENTED | 不預設任何改善幅度或成功結果 |

詳細啟動紀錄見 [BOOTSTRAP.md](BOOTSTRAP.md)，環境說明見 [ENVIRONMENT.md](ENVIRONMENT.md)。以上是文件編寫時的已知狀態；接手時需核對實際分支與 Issue 更新。

## 2. 你的責任範圍與交接界線

| 工作 | 主要負責者 | 你需要做的事 |
|---|---|---|
| 作業系統、工具鏈、ns-3 setup/build | A | 固定版本、排除環境問題、留下可重現紀錄 |
| AP/STA、通道、固定速率與位置 | A | 建立共同場景，確保各方案使用相同控制條件 |
| DL UDP、LL/BE 流量與識別 | A | 產生流量，提供 B 可使用的身分對照 |
| 官方 RR B1 | A | 啟用真正的官方 MU scheduler，確認有 DL MU |
| 封包／flow 量測、run metadata | A | 提供可信原始資料與清楚定義 |
| P1/P2 候選排序、BE guard | B | 提供場景與量測支援；不要自行修改 B 的演算法 |
| scheduler 決策追蹤 | B 主責，A 配合 | 對齊 run ID、時間、STA/flow 對照及檔案位置 |
| 統計分析與圖表、英文報告 | Report Lead 主責 | 交付原始資料、定義、執行方式與限制；協助查錯 |
| 科學比較、版本與介面變更、合併驗收 | PM | 提案並附證據，由 PM 決定 |

你主要修改 `sim/`、場景設定、環境／執行工具及相關文件。A/B 通常負責模擬器 C++，重要變更應盡可能互相審查。共用的 `scripts/`、`configs/`、`patches/series` 若有修改，先協調避免覆寫 B 的工作。

## 3. 時程與工作包

| 時間 | 工作包 | 最低交付 | 對應 Issue |
|---|---|---|---|
| 11/7–11/10 | A-ENV：環境與官方範例可行性 | 工具鏈／版本、建置與範例命令、DL MU 證據或明確阻礙 | [#1](https://github.com/hubert514/Data-Communication/issues/1) |
| 11/7–11/10 | A/B/PM 介面對齊 | 單一入口、設定、身分、時間與資料格式契約 | [#3](https://github.com/hubert514/Data-Communication/issues/3) |
| 11/11–11/13 | A-BASE：混合流量 B1 與量測 | 一個可重現的專案 RR 執行、真實 CSV、metadata 與 logs | [#5](https://github.com/hubert514/Data-Communication/issues/5) |
| 11/14–11/15 | A-INTEG：與 B 整合 | 同一版本／設定／命令，B1 回歸與交接資料 | [#9](https://github.com/hubert514/Data-Communication/issues/9) |
| 11/16–11/22 | Checkpoint，確切報告日期待定 | 協助 PM 重跑，支援 Report Lead 查核真實資料 | [#12](https://github.com/hubert514/Data-Communication/issues/12) |
| Checkpoint 後 | M2–M6 支援工作 | P1/P2 共用場景、成對種子實驗、重現資料 | 日期與優先序由 PM 排定 |

以下逐日安排是建議拆分，讓 PM 可以追蹤；它沒有新增 README 之外的硬性期限。

| 日期 | 建議完成事項 |
|---|---|
| 11/7 | 確認 checkout、工具鏈與 CMake 問題；嘗試乾淨 setup/build |
| 11/8 | 執行官方範例；保存 logs；與 B 查 DL MU／STA／RU 證據 |
| 11/9 | 補足 trace，或提交阻礙、重現步驟與替代方案 |
| 11/10 | 向 PM 交可行性包；與 B 固定介面契約 |
| 11/11 | 實作共同拓樸、固定 PHY/MAC、DL UDP 與身分映射 |
| 11/12 | 接上封包與 flow 量測；檢查時間窗、drain 與資料一致性 |
| 11/13 | 重跑 B1、交資料給 Report Lead、提交 PR 與限制清單 |
| 11/14 | 與 B 整合；供 PM 判斷 B1 是否可靠及是否啟動 fallback |
| 11/15 | 修正整合問題，交付 checkpoint 可重現包 |

## 4. A-ENV：環境與官方 OFDMA 可行性，依順序執行

### A-ENV-1. 確認來源與工作分支

1. 閱讀 README、ENVIRONMENT、DESIGN、目前 Issue #1/#3。
2. 記錄專案 commit、分支、工作目錄是否有未提交修改。
3. 以 PM 指定的整合基點建立短期工作分支，例如 `feature/simulation-environment`。這是分支名稱建議。
4. 不把整份 ns-3 上游原始碼加入本專案；本地依賴維持於 gitignored `.local/ns-3`。
5. 核對最新 `main` 與自己的 base SHA，避免在舊版只含 README 的 checkout 另建重複工具。

可記錄的命令：

```bash
git status --short --branch
git rev-parse HEAD
git remote -v
```

### A-ENV-2. 準備工具鏈

目前建議路徑為非 root 的 Linux／WSL2；各平台是否可用必須以實測為準。不要把 Git Bash 能執行 shell script 當成 ns-3 已可在原生 Windows 完成建置。

工具需求依目前 pinned source 與工具腳本：Python 3.10+、Git、CMake 3.25+、GCC 11+ 或 Clang 17+，以及 Make 或 Ninja。仍需確認所選平台的完整依賴。

```bash
python3 --version
git --version
cmake --version
c++ --version
```

另外記錄所用 Make 或 Ninja 的版本，以及 OS、架構、編譯器路徑。若使用 `CXX`，記錄實際值。沒有的工具應記為缺少，不能填入預期版本。

當前阻礙的處理順序：

1. 確認 CMake 是未安裝，還是未加入當前環境的 PATH。
2. 使用團隊可重現的方式準備依賴，記錄安裝步驟；不要假設其他組員已有相同環境。
3. 若轉換 OS、工具鏈或候選 release，將理由與影響提交 PM；未經核准不自行更換研究使用的版本。
4. 若被系統權限／套件安裝限制阻擋，交明確錯誤、已嘗試方式及下一個可行方案。

### A-ENV-3. 執行既有 setup/build

以下命令已存在於 bootstrap 分支；它們仍可能因環境或上游問題失敗。

```bash
./scripts/setup_ns3.sh
./scripts/build.sh
```

也可使用等價的 Python 入口：

```bash
python3 scripts/ns3_tools.py setup
python3 scripts/ns3_tools.py build
git -C .local/ns-3 rev-parse HEAD
```

逐項確認：

- [ ] 上游 HEAD 等於候選固定 SHA。
- [ ] configure 與 build 都有實際完成，保存 return code 與日誌。
- [ ] 記錄 debug profile、examples/tests 是否啟用；目前 build helper 只明確建置官方 `wifi-he-network` 目標，不等於整套上游測試已執行。
- [ ] 保存 `.local/evidence/<operation-id>/run_metadata.json` 及命令 logs。
- [ ] 設定與 build 文件能讓 B 在另一份乾淨環境重現。

setup 遇到未知 upstream 修改會拒絕繼續。不要直接 `reset --hard`、刪掉同學檔案或覆寫整個目錄；先保存差異，確認是手動工作、已管理 patch 還是部分失敗狀態，再與 B/PM 協調。正式上游修改必須轉成追蹤的 patch／overlay。

### A-ENV-4. 執行官方範例並收集真正的 DL MU 證據

```bash
./scripts/smoke_ofdma.sh
```

目前 helper 使用官方 `wifi-he-network`，規劃的 probe 包含：DL UDP、8 STAs、RR MU、最多 4 STAs、20 MHz、5 GHz、MCS 5、GI 800 ns、停用 UL OFDMA、短時間試跑與固定 seed/run。確切參數以腳本及實際 metadata 為準。

這個官方 probe 並非專案「4 LL＋4 BE」的 B1；它也沒有替專案完成 packet-level 量測。

判讀時要分開四件事：

| 證據 | 能說明什麼 | 仍不能推論什麼 |
|---|---|---|
| `WIFI_STANDARD_80211ax` | 裝置使用 HE 標準設定 | 已經發生 OFDMA |
| `SetMultiUserScheduler` 設定 | AP 已配置 MU scheduler | runtime 一定選了多個 STAs |
| 範例 exit 0／吞吐量表 | 程式完成執行並輸出結果 | DL MU、STA、RU 均已查證 |
| 實際 TX trace／可判讀日誌 | 送出時的類型、收件 STA 與 RU | 演算法有性能改善，或全部負載下都能運作 |

與 B 一起確認並保存：

1. AP 實際送出 DL MU/OFDMA PPDU 的時間與 TX 資料。
2. 最終送出集合中的 STA AID／MAC，並能對回場景身分。
3. 最終 RU 指派，及設定的排程 STA 上限確實被遵守。
4. 所觀察的是 DL MU，而不是 UL trigger、SU 傳送或候選名單。
5. 若日誌只列「候選 STA」，補實際傳送 trace；候選加入可能在後續合法性檢查被排除。

現有 smoke metadata 會保留 `dl_mu_gate=TODO_REVIEW`。不得只因 exit 0 就自行改成已通過；必須提供證據給 PM 審查。

### A-ENV-5. 環境可行性交付包

提交到 Issue #1／PR，至少包含：

- OS／編譯器／CMake／建置工具版本與依賴安裝方式。
- upstream tag＋完整 SHA，project SHA、分支與 dirty 狀態。
- setup、build、smoke 的完整命令、實際結果與 logs 位置。
- 一段可查核的 DL MU、STA 與 RU 證據；不足時明確標示缺口。
- 已知限制、重現方式、需要 PM 做的版本或環境決策。
- 更新 ENVIRONMENT.md，區分「已觀察」與「待驗收」。

本機 `.local/` 是 gitignored；寫本機路徑不代表 PM／同學可存取。應透過 PR 文件、CI artifact 或團隊核准的儲存位置分享必要小型日誌／manifest；大型資料保留 checksum 與位置，不把整份上游或二進位檔推進 repo。

## 5. A/B 開發前必須凍結的共同契約

在平行實作之前與 B 逐項討論，將結果放入 DESIGN.md，由 PM 核准。尚未決定的項目維持 TODO。

| 契約 | 你需要提供的內容 | B 需要回覆的內容 |
|---|---|---|
| 版本與安裝 | 接受的 SHA、工具鏈、建置指令 | patch／overlay 如何安裝與重現 |
| 單一場景入口 | 建議入口、參數解析與設定讀取方式 | scheduler 註冊與切換接點 |
| 方案名稱 | `rr`／`latency`／`fairness` 的 CLI 契約 | 哪些已實作，未實作如何報錯 |
| 身分 | 邏輯 STA ID、Node ID、AID、MAC、IP、flow、port、LL/BE | 在 scheduler 中能取得哪些身分，以及映射需求 |
| LL/BE 分類 | 明確的收件人／flow 對照，phase 1 同 AC | 不靠不同 AC 偷代替流量分類 |
| 時間 | warm-up、發送、量測、app stop、drain、sim stop | queue-age 與 service-age 起算／更新事件 |
| 資料與 trace | flow／packet writer、run ID、metadata | scheduler decision writer 與事件語意 |
| 共用檔案 | 哪些檔案由 A 修改 | 哪些由 B 修改，整合時如何避免衝突 |

特別注意：設定草案中的邏輯 STA `0..7` 不等於 ns-3 Node ID 或 AID。不要依賴「剛好相同」的數字，必須留下可驗證對照。

時間戳記也要與 B 分清楚：候選版本 `WifiMpdu::GetTimestamp()` 的註解是 MPDU 建立時間；尚未證明它等於真正入佇列時間。由 B 查明 queue-age 來源，你負責定義 application／IP TX-RX 量測並配合事件對照，不能把這幾種時間互相替代。

## 6. A-BASE：建立專案 B1 場景

### A-BASE-1. 場景設定與實作順序

先完成一個小型、可重現的共同場景，再增加負載與站數。以下初始值來自 README；未決事項不能擅自填成已核准值。

| 項目 | 初始規劃／要求 | 待確認事項 |
|---|---|---|
| 拓樸 | 1 AP＋8 associated STAs | 實際 node/device 建立順序 |
| 收件組別 | 4 LL、4 BE | 邏輯 ID 與實體身分／ports 對照 |
| 方向／傳輸層 | AP → STAs，下行 UDP | sink/client 啟停時間與封包識別方式 |
| Wi-Fi／頻道 | HE/802.11ax，20 MHz，5 GHz | pinned API 設定及 runtime 核對 |
| 速率 | 固定 MCS 5 | rate manager、control rate 等完整設定 |
| 位置 | 距 AP 約 5–10 m | 固定座標或可重現的產生方法 |
| MU cap | 最多 4 STAs | 以 pinned 版本實際 attribute 與 trace 驗證 |
| LL | 200 B，每 10 ms | payload 定義與 application deadline |
| BE | 1200 B，offered load 待校準 | 每站負載與總負載、負載設定方式 |
| QoS phase 1 | LL 與 BE 同一 AC | 草案提出 AC_BE，採用前確認 TID/ToS 映射 |
| 時間 | 20–30 s 級試驗，加 drain | 精確 active window、warm-up、drain 待 PM 核准 |
| 重複 | 初期至少 3 組，最終目標至少 10 組 | seed/run 配對方式與獨立重複定義 |
| ACK、RU、其他 MAC | 跨方案固定 | 由 A/B 列出實際值並交 PM 核准 |

建議實作步驟：

1. 建立 nodes、固定位置、channel、PHY、MAC、IP 與 association。
2. 啟用官方 `RrMultiUserScheduler`，保留官方 airtime/credit 優先行為。
3. 先確認 AP 至各 STA 可傳送，再加入明確的 LL/BE flow 配置。
4. 加入 run/config 驗證、輸出目錄管理、身分對照與 metadata。
5. 加入封包 TX/RX 事件，然後補 flow aggregates；不要只留下最後一行 throughput。
6. 執行小規模資料一致性檢查與 DL MU trace 檢查。
7. 固定一組 canonical command，交給 B 與 PM 重跑。

不要自行把基準改成手寫 strict round-robin；也不要把 `RrWifiQueueScheduler` 當成 OFDMA MU scheduler。

### A-BASE-2. 流量識別與封包追蹤

建立可重現的對照資料，形式由契約決定，內容至少涵蓋：

- run ID、邏輯 STA ID、Node ID、device／MAC、association AID、IP。
- LL/BE 分類、flow ID、協定、來源／目的位址與 ports。
- packet ID 的產生位置、唯一性範圍、TX/RX 相配方式。
- 重傳、分片、聚合與重複接收時，應用封包與 MAC MPDU 如何避免混計。

不要把 MAC retransmission 次數直接算成 application sent packets；不要預設不同 flow 的 packet sequence number 全域唯一。若使用標籤／header，記錄其大小、是否計入 payload 與可能改變負載的影響。

### A-BASE-3. 時間窗與量測定義先寫清楚

在收集用於比較的資料前，與 PM／Report Lead 決定：

| 必答問題 | 需要的明確答案 |
|---|---|
| packet latency 測量層 | application TX→RX 或 IP 層；不能混用名稱 |
| active window | 開始、結束及邊界是否包含，依 TX cohort 還是 RX-in-window |
| warm-up | 是否排除 association／啟動過程，排除範圍 |
| application stop | 發送者停止時間；接收者應能涵蓋必要 drain |
| drain | 時長與理由；測試延長 drain 是否改變未解決封包數 |
| deadline | 初始 trial 10 ms，與 queue-age urgency 的 deadline 語意對齊 |
| deadline misses | 分母是哪批 TX 封包，逾時收到與未收到如何分類 |
| P95 | 對哪一批成功相配封包計算、percentile convention、未收到封包如何另報 |
| unresolved／loss | 已知 drop、超過 deadline、結束仍在 queue／未收到是否分開 |

有限 drain 後未收到的封包應保留「未解決」語意與已知 drop 證據。不要單靠缺少 RX 就假設知道它在哪一層遺失。P95 只對收到封包計算時，必須同時交代 loss／deadline miss，避免低延遲看起來來自大量封包未送達。

### A-BASE-4. 四種輸出與責任

遵循 README 初始 schema。若需新增或改欄位，透過有 migration 說明的 PR 請 PM 核准。

```text
flows.csv
run_id,flow_id,traffic_class,src,dst,tx_packets,rx_packets,rx_payload_bytes,throughput_mbps,mean_delay_ms,loss_count

packets.csv
run_id,flow_id,packet_id,traffic_class,tx_time_s,rx_time_s,delay_ms,status

scheduler_decisions.csv
run_id,time_s,scheduler,eligible_sta_ids,selected_sta_ids,ru_allocation,urgent_sta_ids,fairness_override
```

| 輸出 | 主責 | 必須查核 |
|---|---|---|
| `flows.csv` | A | LL/BE、bytes 層次、時間分母、delay 與 loss 定義 |
| `packets.csv` | A | TX/RX 唯一配對、時間單位、缺失欄位及 status |
| `scheduler_decisions.csv` | B；A 協助接入 | 同一 run／clock／STA 對照，區分候選與最後有效選擇 |
| `run_metadata.json` | A 主責整合，B 補政策資訊 | 精確版本、設定、seed/run、命令、時間、結果、checksums |

`flows.csv` 的 `throughput_mbps` 不可在未說明下混入 IP overhead 或直接稱為 application BE goodput。應將採用的 byte 定義記在契約；若需要同時保存兩種指標，先提 schema 變更。

`run_metadata.json` 至少保存：

- upstream tag/SHA、project SHA、dirty 狀態及 patch/overlay 指紋。
- OS、工具鏈、建置 profile 與相關 build 選項。
- 完整有效設定；不能只存 config 檔名，否則日後檔案變更會失去原值。
- scheduler、seed、run、精確命令與可影響結果的環境設定。
- 執行起訖、return code、成功／失敗與錯誤位置。
- 量測窗、warm-up、app stop、drain、分類／指標定義版本。
- 產出檔案、checksum、保存位置；缺少欄位明確標 unavailable／null。

目前 bootstrap 工具的 metadata 是 operation-specific，不能直接宣稱專案 run pipeline 已實作。

### A-BASE-5. 基本資料稽核

這些是需以真實輸出執行的檢查，現在均為 TODO：

- [ ] flow／packet 的 run ID 一致，沒有不同版本資料混入同一目錄。
- [ ] 封包 ID 配對規則明確，無意外重複或負值延遲。
- [ ] RX 計數、payload bytes 與逐封包統計在相同窗口／定義下相符。
- [ ] TX、RX、已知 drop、unresolved 的核對方式可說明差額，分類不重複。
- [ ] 收不到封包的 RX time／delay 留空或用核准缺失值，不填 0 或假時間。
- [ ] 無 RX 的 flow 不除以零，不產出具有誤導性的 0 ms 平均延遲。
- [ ] 秒與毫秒、bits 與 bytes、每站與總量的單位一致。
- [ ] FlowMonitor 的 IP 層 aggregate 與 application trace 差異可解釋。
- [ ] 精確 P95 來自真實 packet timestamps；histogram 估計另行標示。
- [ ] 零／極低負載、初始正常負載、較高負載時都能合理處理資料；具體測試值先記錄。

BE goodput 的核准量測窗若為長度 `T` 秒，且 `B` 是該定義下實際交付的 application payload bytes，則 `goodput_mbps = B × 8 / T / 1e6`。公式正確仍須先定義如何選取 bytes 與窗口。

## 7. A-BASE：負載校準與可重現執行

初始 LL 每站 `200 × 8 / 0.010 = 0.16 Mb/s`；4 站合計約 `0.64 Mb/s` application offered load。這是參數換算，不是模擬量測結果。

校準時：

1. 保留初始 LL 組態，逐步調整 BE offered load，記錄每站與總量。
2. 觀察 queue backlog、可排程候選、MU 機會、實際服務及量測品質。
3. 與 PM 決定低／中／高負載代表值，不以「看見改善」作為挑值的唯一理由。
4. 若需要把 LL interval 改為 5 ms／2 ms，作為不同負載情境記錄並取得研究設計核准。
5. 無競爭時 P1 沒有改善不代表錯誤；先證明排程確實有選擇衝突。

執行工具仍待你實作。README 裡的下列形式是**未實作的未來介面示意**，不是可執行命令：

```bash
# TODO / NOT IMPLEMENTED — 以 PM 核准的最終 CLI 為準
./scripts/run.sh --scheduler rr --n-stas 8 --seed 1 --config "TODO-approved-config"
```

完成 run 工具時，至少應做到：

- 驗證未知參數、未決必要設定、非法站數／時間／負載並清楚報錯。
- 未實作的 `latency`／`fairness` 必須拒絕，不可偷偷退回 `rr`。
- 明確處理 config 與 CLI 的優先序，記錄最後有效值。
- 使用獨立 run ID，避免覆寫既有資料；失敗也保存 metadata／日誌。
- 同一 seed/run 在各方案配對；記錄獨立重複的規則，不能把同一結果複製成多次。
- 大量 batch 在 B1／量測尚未通過前維持 TODO。

## 8. A-INTEG：11/14–11/15 整合與 checkpoint 交付

依順序執行：

1. 與 B 核對同一 upstream SHA、project 整合 commit、patch 順序、工具鏈。
2. 從已知乾淨的環境依 setup 安裝 project sources／patches；手動改 `.local` 卻未版本化的內容不得漏交。
3. 重跑 canonical B1，確認輸出與 schema 正確、真實 DL MU 仍存在。
4. 若 B 有 prototype，只對已實作功能執行 focused test，記錄明確結果；沒有 P1 仍可按最低 checkpoint gate 前進。
5. 把可讀的 run manifest、原始資料、命令與限制交給 PM／Report Lead。
6. Report Lead 產生圖表後，協助核對單位、flow 分類與資料來源；圖表與統計主責仍是 D。
7. 將問題、owner、影響範圍、下一步更新到 PM_STATUS／Issue。

**11/14 fallback：若還沒有可靠 B1，由 PM 啟動凍結 P1 feature work，優先修復 baseline／measurement。** 你要提供具體重現與阻礙，不為趕簡報填假資料。

## 9. 測試／驗收矩陣

| 測試 | 最低方法 | 成功證據 | 不足時的回報 |
|---|---|---|---|
| 環境重建 | 乾淨 checkout＋核准工具鏈跑 setup/build | 版本、完整命令、return code、logs | 缺少套件、編譯錯誤與完整位置 |
| 官方 OFDMA | 官方範例＋runtime TX／日誌 | DL MU、實際 STA、RU 與時間 | 僅有候選或吞吐量時標未驗證 |
| B1 重現 | PM/B 重跑 canonical command | 相同設定與可核對輸出、完整 metadata | 說明機器或亂數差異 |
| 分類 | 查 AP→STA UDP 與對照 | LL/BE 能連到 flow／packet／scheduler | 不明 ID／port 顯示 unavailable |
| 封包量測 | 挑真實封包手算與 aggregate 比對 | 相同單位／窗口下數值一致 | 差額與誤差來源 |
| stop/drain | 檢查 app stop、RX、simulation stop | 未解決封包可追蹤，無假 RX | drain 敏感性與限制 |
| 整合回歸 | 安裝 B 改動後重跑 `rr` | RR 路徑與資料管線仍正常 | 哪個 commit 引入問題 |
| 可分享性 | PM／D 取到 evidence 並重跑 | raw data、checksum、設定、命令 | 權限或檔案遺漏 |

初期至少三組獨立重複是計畫要求；單次 sanity run 可以用於除錯，但只能標 preliminary，不能宣稱最終改善。

## 10. 提交給 B、PM、Report Lead 的清單

### 給 B

- [ ] 固定版本與可重建環境。
- [ ] 單一場景入口、config 與有效值列表。
- [ ] 邏輯 STA／AID／MAC／IP／flow／LL-BE 對照。
- [ ] 相同 AC 的實際設定、時間窗與 deadline 語意。
- [ ] B1 canonical command、trace、metadata 與 scheduler 接入方式。
- [ ] 一組能觀察到 scheduling contention 的真實場景，或目前無競爭的證據。

### 給 PM

- [ ] Issue #1/#5/#9 對應的 PR、驗收勾選與 evidence。
- [ ] 已完成／已測試／規劃／阻礙清單，避免以「大致完成」代替狀態。
- [ ] 環境、schema、流量／時間／AC/RU 等需要決策的提案與代價。
- [ ] 一份其他人可照做的重現步驟；尚未通過處明確 TODO。

### 給 Report Lead

- [ ] 真實 raw CSV、manifest、欄位與 metric 定義。
- [ ] seed/run、project/upstream SHA、配置與資料 checksum。
- [ ] 哪些 run 是 sanity／preliminary，哪些是計畫中的 replicated experiments。
- [ ] 已知 limitations、未量得欄位、loss／deadline 分母與 drain 影響。
- [ ] 不把缺失數據當 0，也不提供示意曲線當真實結果。

## 11. PR 與日常回報格式

分開提交環境／場景骨架、量測、執行自動化與整合；避免一次混入 B 的 scheduler 改動。每個 PR 連到 Issue，列出改動、測試命令、實際結果、證據與限制，交 PM 審查。不要自行合併設計變更。

可直接複製下列回報格式；所有尚無證據的欄位填 TODO：

```text
日期／Owner：
Issue／PR：
project SHA／upstream SHA／dirty state：
Implemented（已實作）：
Tested（實際執行與結果）：
Planned（下一步）：
Blocked（原因、影響、已嘗試方式）：
完整命令／config／seed/run：
evidence 路徑或 URL／checksum：
需要 B 提供：
需要 PM 決策：
```

## 12. 常見阻礙處理與升級

| 現象 | 優先調查 | 回報 PM 的資料 |
|---|---|---|
| 缺 CMake／編譯器 | 目前 shell 的 PATH、版本、環境差異 | 完整錯誤、工具路徑、建議處理方式 |
| setup 拒絕未知變更 | `.local/ns-3` diff、untracked、patch state | 保存差異、來源、如何版本化 |
| 只有 SU 或沒有 DL MU | scheduler 設定、pending data、association／BA、限制 | runtime trace，請 B 協助判讀 |
| LL/BE 全部對錯 flow | STA/AID/IP/port 對照及建立順序 | 可重現的最小 run 與映射 |
| 結束時 loss 異常 | app stop、sink lifetime、drain、queue | 分層事件與延長 drain 的觀察 |
| P95 很好但大量未收到 | 只統計 received 的偏差、負載與丟棄 | delay＋miss＋loss／unresolved 一起呈現 |
| B1 仍不穩定 | 回到最小共同場景，縮小問題 | 11/14 fallback 所需風險與阻礙 |

## 13. Checkpoint 後的工作，現在先列 TODO

依 PM 後續排程支援：

1. M2：在共同入口接入已測試的 P1，保留 B1，配合 B 做 controlled behavior test。
2. M3：接入 P2，提供具有 BE pending／服務等待的情境與各站服務紀錄。
3. M4：執行 E1–E4；一次主要變動一個因子，跨方案使用成對 seed/run。
4. M5：支援 E5 參數敏感度與所有圖表的資料重現，不盲跑全參數笛卡兒積。
5. M6：整理可重建來源、依賴、manifest、raw data 與限制，支援期末英文簡報／報告。

目前不得把上述工作勾為完成。P2、動態 RU、混合 AC、UL、完整 LOMAS 重現都不是這次初始化／最低 checkpoint 必做項。

## 14. 最後自查：你的交付是否可以被驗收

- [ ] 另一位組員可以照文件重建環境，而不是只在你的電腦可跑。
- [ ] 官方範例與專案 B1 已清楚區分。
- [ ] 所有「OFDMA 有運作」的敘述都有真正 DL MU／STA／RU 證據。
- [ ] 真實 packet／flow 資料可追溯到命令、版本、設定與亂數。
- [ ] B 能使用你的身分／時間／輸出契約整合 scheduler。
- [ ] D 能使用 raw data 與定義重現圖表，不需手動抄數字。
- [ ] 未決與未實作事項清楚標 TODO，PM 的科學與驗收決策有記錄。

對照閱讀：[Engineer B 工作交接書](ENGINEER_B_TASKS.zh-TW.md)、[DESIGN](DESIGN.md)、[EXPERIMENTS](EXPERIMENTS.md)、[結果格式](../results/README.md)、[Issue 索引](ISSUES.md)。
