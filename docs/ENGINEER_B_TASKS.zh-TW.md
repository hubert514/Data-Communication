# Engineer B 工作交接書：排程器可行性、P1/P2、決策追蹤與測試

文件修訂：r2。更新日期：2026-11-07。時程使用 Asia/Taipei。

**負責人：Engineer B。實際姓名／GitHub 帳號與正式指派：由使用者自行處理，尚未代填。**

需求與驗收依據為根目錄 [README](../README.md)。本文將任務拆成可交接工作包；其中的測試設計與工程建議不是新的科學規格。版本、演算法語意、優先序、介面、整合與驗收由 PM 最終決定。

> 你的第一個目標：用固定版本的原始碼與小型可執行證據，回答「在哪裡改 STA 選擇順序、能否取得正確的 packet queue age、如何保留合法 MU/RU 與官方 RR」，再進入 P1/P2 實作。

## 0. 開工與版本規範

先讀 [共用版本／協作規範](DEVELOPMENT_WORKFLOW.zh-TW.md)。本文 r2 是工作指示修訂；它不表示 P1/P2 已實作，或任何科學 gate 已接受。

- 從最新 `origin/main` 建立 `feature/scheduler-*`，PR 記錄完整 base commit、上游 SHA 與依賴 A 的哪個 commit／PR。
- source references 必須對應 `configs/ns3-candidate.json` 的 exact SHA；ENVIRONMENT.md 另外記接受狀態。不可因換一個較容易修改的 release 就直接沿用原比較。
- 修改 `.local/ns-3` 後，交付追蹤的 patch／sources、series 順序、checksum 與乾淨安裝方式；本機 upstream dirty 狀態不是正式版本。
- B 協調 scheduler patches／series 與 decision logs；A 協調 setup/run/config，跨接點變更先對齊，不能另設不同場景／量測入口。
- CLI/schema／timestamp／AC/RU 變更要附 migration 或研究影響並交 PM；測試過的 SHA 若再變動，重跑受影響檢查。
- 每次 PR 提供實際證據，保留 RR 回歸；只經 PR 合併，不 force-push `main`。文件合併不會自動接受 #2/#6/#9。

本文工作包編號為 `B-FEAS`、`B-PROBE`、`B-INTEG`；研究方案 `B1` 專指官方 RR baseline，避免與「B 工程師第一階段」混淆。

第一輪交付依 [PM 決策清單／11/10 書面驗收](PM_DECISIONS.zh-TW.md)。基本 main 保護已啟用，使用者自行處理帳號與正式指派，且不安排評審會議或日曆活動。r2 僅更新啟動流程；source／runtime／P1/P2 的驗收要求未變。

### 工作包輸入／交付／驗收對照

| 工作包 | 目標窗口／相依 | 明確交付位置 | 完成所需證據與交接 |
|---|---|---|---|
| B-FEAS-01：DL source 路徑 | 11/7–10；固定 candidate SHA，可先於成功 build | `docs/DESIGN.md`、#2 | source 檔案/函式/行號、DL call path、eligibility/RR/RU 關係；交 A/PM |
| B-FEAS-02：queue-age 語意 | 11/7–10；pinned source，runtime probe 另需 A 的環境 | DESIGN 的可見性／時間語意表、#2 | enqueue 與 construction/last-service 的證據；未可執行處標 TODO，不冒充 runtime 查證 |
| B-FEAS-03：extension 提案 | 11/7–10；前兩包發現＋A 的介面需求 | DESIGN、#2/#3 | subclass/patch 選項、限制、維護/授權/回歸影響，PM 記錄選擇後可進入正式改動 |
| B-PROBE-01：instrumentation 路線 | 11/11–13；PM 核准路徑與可執行環境 | `scheduler/`／必要 `patches/`／focused tests、#6 | focused instrumentation 的真實觀察、RR 不受 logging 影響；交 A/PM |
| B-PROBE-02：最小排序路線 | 11/11–13；已核准 prototype 路徑 | 最小 diff、focused test、logs、#6 | 排序接點確實可作用或有精確限制；不能把 prototype 稱正式 P1 |
| B-INTEG-01：共同入口整合 | 11/14–15；A 的 B1＋B 已實作 probe | 整合 PR、#9、PM_STATUS | 乾淨安裝、RR 回歸、同 config/IDs/schema、限制清楚；交 A/PM/D |
| B-P1-01：完整 P1 | M2；checkpoint 前只有 PM 核准的 stretch | policy source/patch、C/L 測試、DESIGN | 真實 queue-age 或明確核准改名 fallback、合法決策、RR fill 與回歸證據 |
| B-P2-01：BE guard | M3；P1 穩定與 PM 核准 service 語意／閾值 | policy source/patch、C/F 測試、DESIGN | crafted overdue 情境有效介入，無 empty/duplicate/invalid allocation，事件可查核 |

表中產物尚未存在者皆為 TODO。Source inspection 可完成 source 類任務；runtime probe 必須真實執行，完整接受仍依 PM 與里程碑。Checkpoint 最低 gate 不強制完成完整 P1/P2。

`B-PROBE-01` 與 `B-PROBE-02` 是 README／Issue #6 所允許的兩條替代路線，由 PM 選擇採用的交付，並非兩包都必做。選 instrumentation 不能宣稱已證明可改排序；選排序 prototype 也不能取代整體 checkpoint 的官方 DL MU 證據。

## 1. 接手時的真實狀態

| 項目 | 已知狀態 | 你的起點 |
|---|---|---|
| bootstrap | [PR #13](https://github.com/hubert514/Data-Communication/pull/13) 已合併到 `main` | 從最新 `origin/main` 建分支，與 PM/A 記錄同一整合基點 |
| ns-3 候選 | tag `ns-3.49`；commit `418210e8914e9f6bcb5cddbcc94a2cecb7853b68` | 此 SHA 可作調查基點，尚未通過建置／runtime 驗收 |
| 本地 setup | bootstrap 主機下載與重複 setup 成功 | 不表示你的工具鏈或 scheduler 已可用 |
| 建置與官方範例 | bootstrap 主機缺少 PATH 中的 CMake，未編譯或執行 | A 排除環境時，你可先做 source inspection |
| `scheduler/`、`patches/` | 尚無 scheduler 實作／實際 patch | TODO / NOT IMPLEMENTED |
| `sim/` 與 project run CLI | 尚未實作 | focused probe 可先規劃，正式共同場景依賴 A |
| queue-age 可行性 | 尚未確認；找到時間戳記 API 不等於語意正確 | 必須核對時間來源與實際排程可存取性 |
| P1/P2 與實驗結果 | 尚未實作，沒有資料或改善證據 | 不先承諾結果 |

bootstrap 的六項安全測試與 GitHub CI 只驗證工具，不驗證 MU scheduling。詳見 [BOOTSTRAP](BOOTSTRAP.md) 與 [ENVIRONMENT](ENVIRONMENT.md)。接手時再核對 PR／Issue 是否更新。

## 2. 你的責任範圍與分工界線

| 工作 | 主要負責者 | 你需要交付／協作 |
|---|---|---|
| 上游 MU/RR API 與 source investigation | B | 精確 source location、資料語意、可行性與限制 |
| P1 latency-aware STA selection | B | queue-age urgency、決策規則、合法性與 focused tests |
| P2 BE fairness guard | B | overdue 規則、服務事件、狀態更新與測試 |
| scheduler patches／sources | B | 可重現安裝、版本固定、原始授權保留 |
| scheduler decision logs | B | run/time/STA/RU／urgency／fairness 語意 |
| OS/toolchain、共同拓樸、流量與 B1 入口 | A | 提出 scheduler 所需設定、身分與 trace 接點 |
| flow／application packet metrics | A | 與 A 對齊 queue/MAC 事件到 packet/flow 的對照 |
| 統計／圖表／英文簡報 | Report Lead | 交付能解釋行為的 logs、限制與政策版本 |
| 研究設計、替代方案、驗收與合併 | PM | 提案、證據與風險；不自行改科學主張 |

你主要維護 `scheduler/`、必要的 `patches/`、scheduler focused tests 與設計／trace 文件。不要另外建立一套不同拓樸或不同量測定義來宣稱 B1/P1 可直接比較。

## 3. 時程與工作包

| 時間 | 工作包 | 最低交付 | 對應 Issue |
|---|---|---|---|
| 11/7–11/10 | B-FEAS：source/API 與時間語意可行性 | 選擇接點、queue-age 可見性、擴充選項、限制 | [#2](https://github.com/hubert514/Data-Communication/issues/2) |
| 11/7–11/10 | A/B/PM 介面契約 | pinned 版本、場景／身分／時間／輸出契約 | [#3](https://github.com/hubert514/Data-Communication/issues/3) |
| 11/11–11/13 | B-PROBE：最小排序或 instrumentation 證據 | 小型 code diff、執行命令與 logs | [#6](https://github.com/hubert514/Data-Communication/issues/6) |
| 11/14–11/15 | B-INTEG：與 A 的共同場景整合 | 安裝方式、RR 回歸、probe 證據或阻礙 | [#9](https://github.com/hubert514/Data-Communication/issues/9) |
| 11/16–11/22 | Checkpoint，報告日期待定 | P1 明確規則與精確實作路徑、PM 已查核的可行性 | [#12](https://github.com/hubert514/Data-Communication/issues/12) |
| Checkpoint 後 M2 | 完成／測試／整合 P1 | 真正 queue-age 或 PM 核准的明確改名 fallback | 日期 TODO |
| Checkpoint 後 M3 | 完成 P2 | 可配置 BE guard、行為證據與合法分配 | 日期 TODO |
| M4–M6 | 實驗支援、敏感度、最終交付 | 追蹤、回歸、政策與限制說明 | PM 排定 |

**Checkpoint 最低要求是 P1 規則與精確 extension path；P1 可執行比較是 stretch，P2 不屬於最低 checkpoint gate。** 不因這份文件列出 P1/P2 詳細步驟，就把它們提早變成 11/15 前必做。

建議逐日拆分，供 PM 調整：

| 日期 | 建議完成事項 |
|---|---|
| 11/7 | 對齊 SHA；讀 MU/RR header 與 DL 路徑；列資料需求 |
| 11/8 | 追 candidate eligibility、RR credits、RU finalization 與 packet timestamp |
| 11/9 | 做最小 metadata／時間語意 probe，或記錄無法執行的阻礙 |
| 11/10 | 交調查包、擴充策略比較與 A/B 契約給 PM |
| 11/11 | 在已核准路徑建立最小 instrumentation／排序 prototype |
| 11/12 | 跑 focused cases，核對候選與最終傳送的差異 |
| 11/13 | 提 PR、限制、測試證據，保留可重現 RR |
| 11/14 | 與 A 整合；提供 PM baseline/fallback 判斷資料 |
| 11/15 | 完成整合交接與 checkpoint 技術說明 |

## 4. B-FEAS：原始碼調查，依順序回答問題

### B-FEAS-1. 固定調查版本

在 PM 尚未接受其他版本前，調查以目前候選固定 SHA 為基點。引用 source 時寫出完整 SHA、檔案、函式／行號；行號只對該 commit 有效。

```bash
git -C .local/ns-3 rev-parse HEAD
git -C .local/ns-3 status --short
```

若還沒有本地來源，可依既有工具下載：

```bash
./scripts/setup_ns3.sh
```

setup/build/smoke 入口可用不等於執行已通過。建置工具問題交由 A 主責，你保留自己的重現與觀察，不另換不同 release 後直接整合。

### B-FEAS-2. 調查入口與目前已觀察的線索

以下僅為 pinned source inspection 的起點，不是已驗收的 extension strategy：

| 來源／符號 | 調查目的 | 編寫本文時的 source-level 觀察 |
|---|---|---|
| `src/wifi/model/he/multi-user-scheduler.{h,cc}` | MU 基底介面、format selection 與狀態 | 仍需完整讀取並畫出實際呼叫路徑 |
| `rr-multi-user-scheduler.cc::SelectTxFormat()` | SU／DL MU／UL 路徑的選擇 | 不可把 scheduler 被呼叫等同實際送出 DL MU |
| `rr-multi-user-scheduler.cc::TrySendingDlMuPpdu()` | DL 候選走訪與初步 MPDU／時間約束 | 會依 STA/TID 查找可傳資料，含 BA 與傳送限制 |
| `rr-multi-user-scheduler.cc::ComputeDlMuInfo()` | 形成 DL MU 資料與後續處理 | 需要追到最後有效集合與傳送事件 |
| `rr-multi-user-scheduler.cc::FinalizeTxVector()` | 最後 RU／候選裁減 | 排序中的候選不一定留在最終 allocation |
| `rr-multi-user-scheduler.cc::UpdateCredits()` | 原 RR 公平優先序 | 看到依傳送時間、RU 頻寬份額更新 credits 並排序 |
| `rr-multi-user-scheduler.h` | 存取層級與可擴充性 | 多個選擇函式、candidate／credit state 位於 private 區域 |
| `src/wifi/model/wifi-mpdu.h::GetTimestamp()` | 封包時間來源 | 註解是 MPDU 建立時間，不能直接等同 enqueue time |
| `src/wifi/model/wifi-mac-queue.{h,cc}` 與實際 queue 路徑 | 真正入列、失效、重傳與 queue metadata | 需追資料寫入與生命週期 |
| `examples/wireless/wifi-he-network.cc` | 官方 scheduler 設定、NStations 與 OFDMA probe | 可與 A 的範例配置相互核對 |

若用命令搜尋，可從下面開始；搜尋結果是定位線索，不是完成證據：

```bash
rg -n 'SelectTxFormat|TrySendingDlMuPpdu|ComputeDlMuInfo|UpdateCredits|FinalizeTxVector' \
  .local/ns-3/src/wifi/model/he/rr-multi-user-scheduler.*
rg -n 'GetTimestamp|GetExpiryTime|Enqueue|PeekNextMpdu' \
  .local/ns-3/src/wifi/model
```

header 的 `private virtual` 並不自動代表 C++ 無法 override；但 derived class 不能因此直接使用 private state／helper。請分別驗證「可覆寫什麼」與「能否重用完整合法排程所需資料」，不要憑關鍵字下結論。

### B-FEAS-3. 畫出實際 DL 排程路徑

請交一份文字流程或小圖，回答：

1. 哪個事件或 MAC/TXOP 路徑呼叫 scheduler？
2. SU／DL MU／UL 決定在哪裡做？目前是否關閉 UL？
3. 目前 AC／TID 決定如何影響可見候選？
4. STA 列表何時建立／移除、何時排序，依據哪些 credits？
5. 對每個 STA 如何取得「現在可傳的 MPDU」？哪些 queue 被考慮？
6. BA agreement、link、available time、aggregation 與 PHY/MAC 限制在哪裡排除候選？
7. RU 選擇與 finalization 在哪裡做，會不會裁掉已選 STA？
8. 何時真正交給 frame exchange／PHY 傳送？能在哪裡證明最後 STA/RU？
9. RR credit 更新與「已服務」狀態更新各在哪個事件，能否對齊？

把 DL 與 UL 的函式分清楚。不要只因某段程式有 `GetHeMuUserInfoMap()` 就認定它是專案需要的 DL 選擇點。

### B-FEAS-4. 建立 metadata 可見性表

請以真實 source inspection／probe 填表；查不到就記「不可得」或 TODO，不能給推測值。

| 資料 | 精確來源／型別 | 決策當下可讀？ | 語意與限制 | 執行／source 證據 |
|---|---|---|---|---|
| 候選 STA MAC／AID | TODO | TODO | association／link／邏輯 ID 映射 | TODO |
| 對應 flow／LL-BE 分類 | TODO | TODO | 從 A 的 recipient／flow 契約取得 | TODO |
| TID／AC | TODO | TODO | phase 1 同 AC，不能單憑 AC 分 LL/BE | TODO |
| 有 pending 的 queue／MPDU | TODO | TODO | 非空是否也代表當下 eligible | TODO |
| 真正 enqueue timestamp | TODO | TODO | packet、MPDU、queue 層生命週期 | TODO |
| 最老「eligible LL packet」 | TODO | TODO | 多 TID、重傳、aggregate 時如何定義 | TODO |
| queue occupancy | TODO | TODO | packet／MPDU／bytes、範圍與排除條件 | TODO |
| 上次成功排程服務事件 | TODO | TODO | 不等同 RX/ACK，需另定事件 | TODO |
| 最終 RU／selected STA | TODO | TODO | finalization 後與真正 TX 的關係 | TODO |

### B-FEAS-5. 特別查核時間戳記語意

目前看到的 `WifiMpdu::GetTimestamp()` 註解是「此 MPDU 建立的時間」。它可以是線索，但還不是 actual queue enqueue timestamp 的證明。

請至少調查：

1. 時間欄位在哪裡寫入？是在 app TX、MPDU 建構、入 queue，或其他時刻？
2. 建構與 enqueue 是否總是同一事件？若不是，差異能否影響 urgency？
3. 重傳、重新入列、alias/copy、聚合／分片會保留還是更新時間？
4. 過期／已排程／不可傳封包是否被正確排除？
5. `PeekNextMpdu` 找到的是否等於政策要求的最老 eligible LL packet？跨 TID 時如何處理？
6. scheduler 路徑是否能在不破壞 queue ordering／生命週期下取得資料？
7. 能否加最小 trace，對照已知建構／入列事件與排程時讀到的時間？

提出一個小型可重現語意測試，使用已知事件時間並驗證 `now − enqueue_time`。若使用受控／合成流量，標成 **synthetic behavioral fixture／行為測試**，不是性能實驗資料。

不能把 application TX timestamp 自動當成 MAC enqueue time，也不能把 `now − last_served` 標成 queue age。

### B-FEAS-6. 擴充策略比較與 PM 決策

README 允許的主要方向為：新的 `MultiUserScheduler` subclass，或必要時維護 RR patch／derived implementation。請用證據比較：

| 比較項 | 新 subclass | RR patch／derived implementation |
|---|---|---|
| 可用 hooks／存取資料 | TODO 實際符號與可用範圍 | TODO 實際需改成員與 helper |
| 保留 RR-fill 的方式 | TODO | TODO |
| 保留 RU／PHY/MAC 合法性的方式 | TODO | TODO |
| 重用上游程式量／維護成本 | TODO | TODO |
| 對原 B1 的影響與回歸風險 | TODO | TODO |
| patch／overlay 安裝流程 | TODO | TODO |
| 授權／上游 notices | TODO | TODO |
| 最小 probe 的結果 | TODO，未執行不得填通過 | TODO，未執行不得填通過 |

交給 PM：推薦方向、來源證據、可執行 probe／阻礙、替代方案、對科學比較的影響。PM 核准後寫入 DESIGN.md；不要自行決定改成不同 RU policy、不同 AC 或 service-age claim。

## 5. 與 A 必須先對齊的介面契約

以下清單未經 A/B 對齊與 PM 核准前維持 TODO：

- [ ] 精確 upstream tag/SHA、工具鏈與 sources／patches 安裝方式。
- [ ] 一個共同 simulation entry point、一個 canonical config schema。
- [ ] selector：`rr`／`latency`／`fairness`，未實作的 selector 明確拒絕。
- [ ] LL／BE recipient／flow mapping；logical STA ID、Node ID、AID、MAC、IP 不混用。
- [ ] phase 1 同 AC；TID／eligible queue 範圍與 BA/link 條件。
- [ ] deadline、warm-up、active window、app stop、drain、sim stop。
- [ ] queue-age／service-age 的起算、讀取及更新事件。
- [ ] scheduler configuration 如何傳入，不從臨時硬編碼值偷改研究參數。
- [ ] 同一 run ID、時鐘、output directory 與 metadata 版本。
- [ ] CSV 缺失值、集合編碼、reason logs 與最終送出 evidence 如何保存。
- [ ] B1 保留路徑及有／無 instrumentation 時的回歸方法。

你對 A 的最小需求是「有 pending LL/BE 且真正發生選擇衝突的共同場景」。若全體都可同時被服務，就很難驗證 urgency 改排序是否有意義。

## 6. 11/11–11/13：最小 prototype／instrumentation 工作包

此階段優先取得小而可信的可行性證據，尚不要求完整 P1/P2。

建議順序：

1. 在 PM 核准的路徑加 instrumentation，先不改任何候選排序。
2. 紀錄原 RR 候選順序、eligibility、最終 selected／RU 與可取得時間欄位。
3. 用同一設定與 seed/run 重跑 B1，確認沒有因 logging 修改排程狀態或消耗亂數。
4. 在獨立可關閉的 probe 模式做最小排序變更，證明接點能影響候選與最終服務。
5. 對照原始 RR 與 probe，辨認哪個 STA 被換入／換出，是否仍有合法 DL MU。
6. 以 focused test／trace 支持結果；若無法改動，交出精確原因與替代路徑。
7. 保留 RR 預設與回歸命令；prototype 不得以正式 P1／latency 方案發表性能結論。

probe 若選擇臨時固定排序，必須明確命名「排序接點測試」，不可把它冒充 queue-age-aware P1。若要暴露臨時 CLI，與 A/PM 對齊名稱與狀態。

### 本階段最低交付

- [ ] source/API 調查表、DL call path、時間語意結論或待解問題。
- [ ] 最小 diff、安裝方法、完整執行命令與版本。
- [ ] 原 RR 與 probe／instrumentation 的真實 logs。
- [ ] 候選與最終傳送的關係可查核，並記錄 STA／RU。
- [ ] 不能完成的項目清楚標 Blocked／TODO，附重現與 PM 決策需求。

## 7. M2／Checkpoint stretch：P1 規則與實作工作包

**狀態：TODO / NOT IMPLEMENTED。完整 P1 為 M2；是否在 checkpoint 前推進，由 PM 依 B1 可靠性決定。**

### P1-1. 固定語意，再寫候選排序

README 規劃的 urgency：

```text
queue_age_i_ms = now_ms - enqueue_time_of_oldest_eligible_LL_packet_i_ms
urgency_i = queue_age_i_ms / deadline_i_ms
```

逐項實作／核對：

1. 從原合法排程路徑取得候選，保留 eligibility 與 nonempty 條件。
2. 以 A/B 契約的 recipient／flow 身分判斷 LL/BE；不要只用 AC。
3. 讀取正確最老 eligible LL packet 的 enqueue time；沒有資料就明確 unavailable。
4. deadline 必須為有效正值，時間單位一致；若 timestamp 在未來，當作錯誤查原因，不默默截成 0 掩蓋 bug。
5. 以 `urgency >= urgency_threshold` 判定 urgent。`0.5` 是初始 trial，尚未最佳化。
6. urgent LL 依 urgency 遞減，tie-break deterministic 並寫入 DESIGN。
7. 先放 urgent LL，再盡量依官方 RR priority/order 補其餘 slots。
8. 去除重複，不能選空 queue，不能越過 MU cap 與當下 PHY/MAC 限制。
9. 使用與 B1 相同 RU policy；最後選擇可能因合法性被裁減，必須紀錄。
10. 沒有 urgent LL 時，盡量回到 B1 原行為；偏離處需具體說明與測試。

這些是行為規格，不宣稱 ns-3 存在同名 helper。不要照 README pseudocode 直接生成未查證 API。

### P1-2. 必須文件化的邊界

| 情境 | 要確定的行為 |
|---|---|
| 候選為空 | 沿用合法 no-TX／SU fallback，不強做無效 MU |
| 全是 BE／沒有 urgent LL | 近似原 RR，說明允許差異 |
| urgent LL 多於 cap | 依 urgency 與 deterministic tie 規則選擇 |
| urgent LL 少於 cap | RR fill，排除已選 STA |
| 多 TID／多 queue | 最老 eligible LL 的範圍，與原可傳順序如何相容 |
| BA/link/TXOP 不允許 | 不因 LL urgency 繞過限制 |
| 候選在 allocation 被淘汰 | 區分曾被優先考慮與最終送出 |
| 重傳／alias／aggregate | 不重設或混淆原始 queue-age 語意 |
| 同時刻／相同 urgency | 可重現的 tie-break，不引入未記錄亂數 |
| 未知 LL/BE／missing timestamp | 明確拒絕配置、略過或核准 fallback，不能靜默捏造 |

最後一列的處置方式是 PM/介面決策，現在不預先定義成已接受行為。

### P1-3. 排程分數與 end-to-end 指標要分開

queue age 是政策使用的等待時間；Report Lead/A 的 application／IP delay 包含其他階段。queue-age/deadline 比例只是 urgency heuristic，不能因此保證端到端 deadline。把兩者的時間起點、層次與名稱寫清楚。

## 8. M3：P2 BE 公平保護工作包

**狀態：TODO / NOT IMPLEMENTED；不屬於最低 checkpoint gate。** 先完成 P1 與 B1 regression，再依 PM 優先序進入。

README 規劃：

```text
be_service_age_i_ms = now_ms - last_successfully_scheduled_service_i_ms
```

當 BE 有 pending 且 service age 超過可配置 `be_max_service_gap_ms`，為最 overdue 且 eligible 的 BE 保留一次合法 MU service opportunity，再由 P1 填其餘位置。這不保證封包送達或 hard deadline。

### P2-1. 先提交 PM 決策的未決細節

| 問題 | 為什麼不能略過 |
|---|---|
| 「成功排程服務」在哪個事件更新？ | 名列候選、最終 allocation、實際 TX、ACK 與 RX 都不同 |
| 首次服務的初始時間 | 無 last-service 值不能任意當 0 導致假 overdue |
| BE 原先 empty、後來有資料 | 閒置很久不一定等同一直受飢餓 |
| 多個 BE 同時 overdue | 需 deterministic 的排序與 tie 規則 |
| 閾值邊界 | README 是 exceeds；精確比較與浮點／Time 表示需固定 |
| MU cap 為 1 或合法 RU 不足 | protected BE 與 LL 的取捨與合法性 |
| 被保護 BE 最後無法傳送 | 是否更新服務狀態、如何保留等待、記錄原因 |
| retransmission／ACK loss | guard 的 service 定義與 delivery fairness 要分開 |
| association／disassociation | 狀態建立、清除與 ID 重用 |
| warm-up／run reset | 不可跨 run 污染狀態；window 是否影響 age 要明訂 |

`be_max_service_gap_ms` 的數值目前 TODO，不要擅填成「最佳值」。把提案、理由及測試情境交 PM 核准。

### P2-2. 實作順序

1. 建立每個 BE 的明確 service state，依核准事件更新。
2. 只對有 pending 且 eligible 的 BE 評估 overdue。
3. 依核准規則選最 overdue，確保與其他 selected STA 唯一。
4. 嘗試保留合法 opportunity，不能強行分配不存在的 RU 或超過 available time。
5. 剩餘 slots 走 P1 與 RR fill，保留共同分配規則。
6. 紀錄 guard 被考慮、有效介入與實際服務的差別。
7. 用 crafted starvation fixture 驗證觸發，再用真實共同場景評估 trade-off。
8. 和 A/Report Lead 分別觀察 scheduled service gap、TX、ACK/RX、BE goodput；不能用其中一個代替全部。

## 9. 決策追蹤與輸出契約

README 初始欄位：

```text
run_id,time_s,scheduler,eligible_sta_ids,selected_sta_ids,ru_allocation,urgent_sta_ids,fairness_override
```

| 欄位 | 需明確定義 |
|---|---|
| `run_id` | 與 A 的 flow／packet／metadata 完全一致 |
| `time_s` | 哪個 scheduling event；秒；與其他 trace 同一 simulation clock |
| `scheduler` | 實際啟用的 rr／latency／fairness；probe 不能冒充正式政策 |
| `eligible_sta_ids` | 真正符合當下條件的集合，不只是所有 associated STAs |
| `selected_sta_ids` | 在約定階段的最終有效集合；若非實際 TX，需有對應 trace |
| `ru_allocation` | 可解析的 STA→RU 對照，來自最後有效配置 |
| `urgent_sta_ids` | 實際達 threshold 的 LL，依當下可得真實資料 |
| `fairness_override` | 何時算真正介入；B1/P1 的不適用值依 schema 定義 |

queue age、deadline、urgency、service age、RR credits、decision ID、reason 等診斷欄位可能很有用，但目前為**提案**。若新增／修改正式 schema，交 PM 核准 migration；也可提議獨立診斷 log，清楚說明關聯方式與狀態。

寫入時注意：

- CSV 陣列／RU map 若含逗號，需合法 escaping；編碼格式與 parser 一起文件化。
- unavailable 不能填成看似量得的 0；不適用與缺失要區分。
- 記錄 policy 參數、patch/source SHA、trace schema 與 build profile 到 run metadata。
- log 開關不可改 candidate state 或消耗 RNG，不能為了列印而改變選擇。
- 若多次決策在同一 timestamp，提出能對回 final TX 的方法，不能只憑時間猜事件。
- 調試資訊若包含大量每-packet／per-opportunity 輸出，先控制範圍；正式比較各方案使用一致的 tracing 條件。

## 10. 測試計畫：先驗證行為，再討論效能

以下是待實作／待執行的案例清單，不代表已通過。crafted fixture 的數字是受控測試輸入；必須標 synthetic behavioral fixture，不能放進實驗圖表當測量結果。

### 10.1 共通 invariant 與 B1 回歸

| ID | 測試情境 | 需要檢查 |
|---|---|---|
| C01 | eligible 集合為空 | 無空 queue／無效 allocation，不 crash |
| C02 | cap 小於候選數 | 最終 selected 不超過 cap，沒有重複 |
| C03 | 部分 STA 無 pending | 不因高 urgency／service age 選到空 queue |
| C04 | 某候選不符 BA/link/time | 即使分數高也不得繞過 eligibility |
| C05 | RU finalization 裁減候選 | logs 區分 candidate、selected 與 actual TX |
| C06 | 同 config/seed/run 重跑 | 行為可重現或差異來源有說明 |
| C07 | tracing on/off | 方案與隨機事件不因 logging 改變 |
| C08 | 安裝 scheduler 變更後跑 `rr` | 官方 baseline 路徑與資料輸出仍可用 |
| C09 | 未實作 selector／非法參數 | 明確失敗，不靜默退回其他方案 |

### 10.2 P1 focused cases

| ID | 受控情境 | 預期驗證重點 |
|---|---|---|
| L01 | 全 BE 或無 LL urgent | 盡可能與原 RR 一致；偏差有理由 |
| L02 | LL urgency 略低於 threshold | 不當 urgent |
| L03 | LL urgency 恰等於 threshold | 依 `>=` 納入 urgent |
| L04 | urgent LL 數量超過 cap | 高 urgency 優先，tie deterministic |
| L05 | urgent LL 少於 cap | 剩餘由原 RR order 補，不能重複 |
| L06 | 年齡很高但該 queue 為空／不 eligible | 不可被選入 |
| L07 | timestamp 是建構時間而非 enqueue | 語意 probe 必須辨認差異，不能誤標 queue age |
| L08 | retransmission／alias／多 TID | 核對 oldest eligible 與時間生命週期 |
| L09 | 只有一個候選或所有候選都能服務 | 不誤宣稱出現 meaningful priority improvement |
| L10 | crafted contention，urgent LL 原本排在 cap 之外 | 證明 P1 讓其進入最終有效選擇；若未進入，解釋合法性原因 |

每個測試交：初始 queue／STA 條件、事件時間、政策參數、原 RR 結果、P1 結果、最後 RU／TX、assertion 與 raw log。L10 的意義是驗證決策有改變，不是證明整體延遲已改善。

### 10.3 P2 focused cases

| ID | 受控情境 | 預期驗證重點 |
|---|---|---|
| F01 | 無 overdue BE | P2 走與 P1 相容的路徑 |
| F02 | pending BE 剛低於／等於／高於閾值 | 依核准的邊界規則決定介入 |
| F03 | 一個 overdue eligible BE＋urgent LL | 合法保留 BE 機會，剩餘走 P1 |
| F04 | 多個 overdue／同 service age | 選擇與 tie-break deterministic |
| F05 | 很久未服務但 queue 為空 | 不保護空 queue |
| F06 | 第一次出現 BE pending／閒置後恢復 | 起算符合核准設計，不誤報飢餓 |
| F07 | 被保護後因 RU/time 失敗 | 不誤記成成功服務，logs 說明原因 |
| F08 | TX 已排程但 ACK/RX 失敗 | service state 與 delivery 狀態分開 |
| F09 | cap=1 或其他合法性極限 | 不產生重複／空／超限 allocation |
| F10 | controlled starvation case | guard 確實觸發並有最終服務證據，實際 BE gap 可檢查 |
| F11 | 新 run／重新 association | 狀態清除／建立正確，不受前次 run 污染 |

除 focused tests 外，與 A 重跑共同 B1/P1/P2 場景。平均延遲、P95、deadline misses、BE goodput、Jain index 與 service-gap 的正式比較由真實 paired-seed runs 支持；單個 fixture 或一次 run 不能證明性能優勢。

## 11. 版本化修改與安裝方式

你在 `.local/ns-3` 中的手動改動不會自動成為專案交付。每一個必要修改都要轉成 repo 追蹤的 patch／source overlay 與安裝步驟。

目前 setup 的實際行為：

1. 從 `configs/ns3-candidate.json` 讀取候選版本，確認 exact SHA。
2. 依 `patches/series` 順序套用列出的 `.patch`。
3. patch 以 `git apply --index` 管理，新增檔也會進本地 upstream index。
4. 保存 patch checksum 與 worktree fingerprint，允許相同 managed state 重複 setup。
5. 遇到未知 edits／untracked／patch input 改動或錯誤 SHA，拒絕並保存現場，不幫你 reset。

因此你的交付需包含：

- [ ] patch filename、順序、適用的 exact upstream SHA。
- [ ] 若使用 overlay，先與 A 定義並實作 installation manifest／流程；目前這部分 TODO。
- [ ] 修改檔案清單、目的與保留的原版 license/copyright notices。
- [ ] 不依賴只存在自己機器上的檔案、未追蹤 include 或絕對路徑。
- [ ] 在乾淨 upstream checkout 安裝、build、跑 RR 與 focused test 的證據。
- [ ] 更新 patch 時如何保留舊手動工作與遷移；不要刪同學變更後重跑。
- [ ] 可關閉／回到 B1 的明確方式，且不需要手動編輯程式碼切方案。

不要把全上游 repo、編譯輸出或大型 PCAP commit 到 project。不要為了快速 subclass 將大量 private 成員公開而不解釋風險；若需要修改可見性，提出最小 diff 與理由給 PM。

## 12. 11/14–11/15：整合與最低 checkpoint 驗收

與 A 一起執行：

1. 對齊 project commit、upstream SHA、patch/overlay 版本及安裝順序。
2. 使用同一 entry point、設定與身分／時間／schema 契約。
3. 從乾淨環境重新安裝，不依賴你手動留在 `.local` 的內容。
4. 先跑官方範例／共同 B1，保留實際 DL MU evidence 與 output 正確性。
5. 再跑已實作的 instrumentation／排序 probe 或 P1 focused test。
6. 比對候選、最終 selected、實際 TX／ACK/RX，說明其不同層次。
7. 交 code diff、完整命令、raw logs、限制與需要 PM 決策的項目。

**11/14 決策：如果可靠 B1 尚未完成，PM 應按 README freeze P1 feature work。** 你轉向協助 baseline、eligibility／DL MU tracing 與量測查錯；不要自行把研究改成「只有 scheduler 測試就算 checkpoint 完成」。

最低 checkpoint 中你的專責驗收：

- [ ] P1 決策規則寫清楚，queue age 可得／不可得有證據。
- [ ] exact code insertion／extension path 有 pinned source reference。
- [ ] PM 對 extension strategy 與必要 fallback 有記錄。
- [ ] 至少能交 source inspection；若有 runtime prototype，提供真實命令與 logs。
- [ ] 與 A 共同支持官方 DL MU、project B1 與分類／schema 檢查。
- [ ] 所有未實作／未執行的 P1/P2 項目保留 TODO。

Checkpoint 整體仍需要 A 的可重現 B1、真實結果與 D 的圖表，及 PM 審查。你的 prototype 不能代替其他 gate。

## 13. Queue-age 不可行時的 fallback 提案

先排除「只是還沒找對接點」與「真正無法安全取得資料」。若仍不可得，交給 PM 一份提案：

1. 哪個時間欄位／queue 語意不可得，在哪個 pinned source／probe 看見限制。
2. 能否以低風險 instrumentation／metadata 補足，需多少改動與維護成本。
3. 若採 service-age-aware，精確公式、服務更新事件、初始與 empty queue 規則。
4. 和原 queue-age P1 的研究主張差異、偏差與可回答的問題。
5. config、selector、metadata、logs、文件與報告要如何明確改名／遷移。
6. 對時程、B1 重現及測試的影響。

PM 核准前不把 fallback 當正式 P1 結果；也不把 MPDU 建構時間或 last-served age 靜默標成 enqueue queue age。

## 14. 交付清單與溝通方式

### 給 A

- [ ] accepted extension strategy、sources／patches 安裝方式。
- [ ] scheduler factory／selector 接點與已實作狀態。
- [ ] 需要的流量／STA mapping、時間與參數，缺少時清楚報錯。
- [ ] 輸出 trace schema、run metadata 欄位提案與關聯方式。
- [ ] RR 回歸命令、focused cases、已知不支援情境。

### 給 PM

- [ ] Issue #2/#6/#9 對應的 source／PR／測試證據。
- [ ] queue-age 語意表與可得性結論，不能只寫「有 timestamp API」。
- [ ] extension options、推薦理由、科學比較影響與維護風險。
- [ ] 合法性、RR 保留、同 AC／同 RU、fallback 變更的核准需求。
- [ ] Implemented／Tested／Planned／Blocked 明確狀態與下一步。

### 給 Report Lead

- [ ] B1/P1/P2 規則與參數、試驗值與已接受值的區別。
- [ ] 真實 trace 解讀方式，候選／已選／TX／ACK／RX 不同層次。
- [ ] 一個可查核的行為案例；synthetic fixture 清楚標註用途。
- [ ] 沒有硬 deadline 或普遍公平保證的限制說明。
- [ ] 所有性能敘述只連到真實 controlled／replicated data；尚無結果就保留 TODO。

建議使用短期 `feature/scheduler-*` 分支，將 source investigation／instrumentation、P1、P2 與整合分成可審查 PR。附 Issue、具體改動、完整命令、實際輸出、證據、限制；A 在可行時交叉審查，PM 決定接受與合併。

回報格式可直接使用：

```text
日期／Owner／Issue／PR：
project SHA／upstream SHA／patch 指紋：
本次調查的 source symbol／時間語意：
Implemented（已實作）：
Tested（命令、情境、實際結果）：
Planned（下一步）：
Blocked（精確原因、影響、已嘗試方式）：
候選／最終選擇／TX 證據 URL 或路徑：
已知限制：
需要 A 提供：
需要 PM 決策：
```

## 15. 常見誤區與處理

| 誤區／問題 | 正確處理 |
|---|---|
| 把 RR 想成簡單 cyclic 順序 | 保留上游 airtime/credit 行為，引用 pinned code |
| 改 `RrWifiQueueScheduler` 當作完成 OFDMA | 回到 `RrMultiUserScheduler`／MU 選擇路徑 |
| 見 `GetTimestamp()` 就宣稱有 enqueue age | 追寫入／生命週期，做受控事件對照 |
| 用不同 AC 讓 LL 先傳，當作 P1 效果 | phase 1 同 AC；mixed AC 是另立實驗 |
| 高 urgency 就跳過 BA/RU/time 限制 | eligibility 與合法配置仍必須滿足 |
| print candidate 就說 STA 被服務 | 補 final allocation 與 actual TX 證據 |
| 更新 last-service 太早 | 依 PM 核准事件更新，傳送／ACK/RX 分開 |
| 空 queue 也算最 overdue | pending／eligible 過濾；明確 first-service／idle 規則 |
| 多個 STAs 同分時依容器偶然順序 | 將 deterministic tie-break 文件化並測試 |
| 為方便改 RU sizing 或 rate control | 先交 PM 研究設計提案，維持 controlled comparison |
| 只看一次 fixture 的 latency | fixture 用於 correctness；效能需真正 paired replications |
| 保證 hard deadline／不飢餓 | 描述機制與實測結果、條件及限制，不作未證明保證 |

## 16. 最後自查：你的交付是否足以驗收

- [ ] A 可以依你留下的方式乾淨安裝與切換已實作政策。
- [ ] 原始官方 RR 仍能使用相同場景與量測管線。
- [ ] 每個 queue／service timestamp 都有明確來源與語意。
- [ ] P1 只改 STA 選擇優先性，保留同 AC／同 RU 等比較條件。
- [ ] P2 只在有 pending／eligible 的 BE 上依核准規則介入。
- [ ] focused tests 有真實執行輸出；未執行全部標 TODO。
- [ ] logs 能區分候選、有效配置與實際傳送，不把排程當成送達。
- [ ] 不可行項目、fallback、schema 或科學主張變更都有 PM 決策記錄。
- [ ] Report Lead 能以正確名稱解釋機制，不需要猜程式做了什麼。

對照閱讀：[Engineer A 工作交接書](ENGINEER_A_TASKS.zh-TW.md)、[DESIGN](DESIGN.md)、[ENVIRONMENT](ENVIRONMENT.md)、[EXPERIMENTS](EXPERIMENTS.md)、[結果格式](../results/README.md)、[Issue 索引](ISSUES.md)。
