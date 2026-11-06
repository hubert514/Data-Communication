# PM 決策清單與 A/B 啟動驗收

文件修訂：r1。日期：2026-11-07。時區：Asia/Taipei。最終決策者：Technical PM。

依據 [README](../README.md)、[A 工作交接書](ENGINEER_A_TASKS.zh-TW.md)、[B 工作交接書](ENGINEER_B_TASKS.zh-TW.md) 與 [版本協作規範](DEVELOPMENT_WORKFLOW.zh-TW.md)。本文將未決事項、輸入、決策與阻擋範圍列清楚，不代表任何科學選項已核准。

使用者已指定：A/B 帳號與正式指派由使用者處理；不安排評審會議或日曆活動。以下 11/10 是既有可行性工作窗口的書面檢查點，不是已建立的會議。

## 1. 現在可以開始的工作

| 角色 | 可立即進行 | 第一次回報 | 不需要等待 |
|---|---|---|---|
| A | 確認工具鏈／CMake，依候選 lock 執行 setup/build，調查官方 HE 範例 | SHA、工具版本、命令、實際輸出、DL MU 證據或 blocker | B 的完整 P1/P2 實作 |
| B | 在候選 SHA 上讀 MU/RR source，追 eligibility、queue metadata、timestamp 語意與 extension 選項 | pinned source references、可見性表、限制與推薦路線 | A 的 build 成功；但 runtime probe 要等可執行環境 |
| PM | 維護下列決策表與 #3，確認證據、影響範圍和下一步 | 哪些已查證、待補證據、待核准，以及對應 owner | 不必先猜完所有實驗參數 |

正式身分與權限由使用者處理，不把 repo owner 自動指定為 A 或 B。Issue 已備好角色任務，不表示同學已接受／開始工作。

## 2. 決策登錄表

狀態以「待輸入／待決策／已決策」為主；只有附決策者、日期與 evidence／PR 才能標已決策。下表的技術結論目前皆未接受；README 已定的限制不重新當成任選項。

| ID | 決策／確認事項 | 必要輸入與提出者 | 誰決定／目標窗口 | 目前狀態 | 尚未決定時影響 |
|---|---|---|---|---|---|
| D01 | A/B 實際帳號、存取與 Issue 指派 | 使用者提供並完成帳號／權限設定 | 使用者／PM；啟動時 | 使用者自行處理 | 不影響閱讀公開 repo；不宣稱已正式指派 |
| D02 | 接受的 ns-3 tag/SHA、OS／工具鏈 | A 的乾淨 build＋官方範例證據；B 的相容性觀察 | PM；11/7–10 | 待輸入；目前只有候選固定 SHA | 可做 candidate source investigation；正式版本驗收未完成 |
| D03 | enqueue time／oldest eligible LL 可否安全讀取 | B 的欄位寫入與生命週期追蹤、source 與 runtime probe | PM；11/7–10 | 待輸入 | 阻擋 queue-age P1 正式主張；不阻擋 B1 場景建構 |
| D04 | subclass 或 maintained RR patch／derived implementation | B 的 hook/private-state/RR-fill/RU 合法性與維護分析 | PM；11/7–10 | 待決策 | 正式 scheduler 修改待核准；可先唯讀調查 |
| D05 | 單一 simulation 入口、config 讀取、selector 與安裝流程 | A 提入口/config/run；B 提 scheduler 註冊與 patch/overlay 需求 | PM；11/7–10 | 待決策 | 阻擋獨立而互不相容的正式實作；不阻擋環境排錯 |
| D06 | logical STA／Node／AID／MAC／IP／flow／ports 與 LL-BE 對照 | A 提 mapping，B 證明 scheduler 使用方式 | PM；11/7–10 契約 | 待輸入；config 僅草案 | 阻擋分類與端到端 logs 交接；不可依數字恰巧相同猜映射 |
| D07 | warm-up、active window、app/sink stop、drain、simulation stop | A 提時間表、drain 觀察；B 說明 age 更新；D 核對分析 | PM；契約／正式資料前 | 待決策；20–30 s＋drain 僅初始規劃 | 可做短 probe；正式結果必須先明訂窗口與邊界 |
| D08 | latency 層、P95 convention、deadline 分母、loss/unresolved、bytes | A 提原始 trace 與一致性方法，D 提統計需求，B 解釋 MAC 事件 | PM；契約／正式資料前 | 待決策 | 可以開發 instrumentation；未定義前不接受性能結論 |
| D09 | BE offered load 與低／中／高負載代表值 | A 的真實負載校準、queue／eligible／服務觀察 | PM；11/11–13 | 待輸入；不能先填最佳值 | 阻擋有意義的效能比較；不阻擋基準連通性與量測除錯 |
| D10 | phase 1 同 AC、同 RU policy／ACK／rate-control 等控制值 | README 同 AC／保留 RU 原則；A/B 記錄實際配置 | PM；契約／比較前 | 原則已由 README 固定；精確配置待查證 | 不得私自改為 mixed AC／adaptive RU 後沿用同一主張 |
| D11 | main 分支保護及後續審查者 | 實際 checks、協作者／權限、下面的 baseline/team 設定 | repo 管理者／PM；啟動時 | baseline 已於 2026-11-07 套用並讀回；team review 待使用者完成成員設定 | 基本 PR/CI 已啟用；一人核准規則尚未啟用 |
| D12 | project license 與 copied/modified upstream notices | PM 選擇；A/B 列依賴與要分發的來源 | PM；相關來源分發前 | 待決策；LICENSE 尚無授權授予 | 不擅自套用 license；始終保留上游 notices |

P2 的 service 更新事件、first-service／idle 規則、`be_max_service_gap_ms` 等，列為 M3 的 PM 決策；它們不是啟動 B1 或最低 checkpoint 的先決條件。

## 3. PM 決策記錄格式

每個 ID 以新記錄保留歷史，不覆寫成看似一直如此：

```text
Decision ID／關聯 Issue／PR：
狀態：待輸入／待決策／已決策
提出者／最終決策者／日期：
輸入版本：project SHA、upstream SHA、patch 指紋
source／命令／實際輸出／evidence URL：
選項與推薦理由：
決定採用的行為與精確值：TODO
科學比較／介面／資料遷移影響：
需同步的 config／docs／producer／consumer：
重測／重跑範圍：
下一位 owner／交付窗口：
```

未填的決策保留 TODO。`GetTimestamp()` 存在、CI 綠燈、probe exit 0 都不能單獨接受 queue-age 語意或 DL MU。

## 4. A/B 第一次交付包

### A：#1，11/7–11/10

- [ ] 以最新 `origin/main` 開 `feature/simulation-*`，記錄 base SHA。
- [ ] 記錄 Python/Git/CMake/compiler/Make 或 Ninja 版本與 OS；缺少項目寫清楚。
- [ ] 執行既有 setup/build/smoke，保存 metadata／return code／logs；失敗也保存。
- [ ] 成功執行時附真正的 DL MU、served STA 與 RU；不足就標缺口，不用 throughput 表代替。
- [ ] 更新 ENVIRONMENT.md，將候選 pin 與 PM accepted 狀態分開。
- [ ] 給 B 可重現環境／命令；給 PM 可存取的日誌，不只本機 `.local/` 路徑。

### B：#2，11/7–11/10

- [ ] 記錄相同 candidate SHA，列 MU→DL candidate→RU/final TX 的 source 路徑。
- [ ] 補 source/visibility 表：STA、queue occupancy、receiver、TID/AC、LL-BE 對照、timestamp。
- [ ] 追 `GetTimestamp()` 的建構／入列／重傳／alias 語意；不能直接認定是 enqueue。
- [ ] 比較 subclass 與 RR patch／derived 路線，包括 private state 與 RR/RU 保留方式。
- [ ] 有可執行環境時再做最小 runtime probe；未跑就明確 TODO／Blocked。
- [ ] 將限制／fallback 提案與需要 A 提供的資料交到 DESIGN／#2/#3。

兩位回報都必須包含 Implemented／Tested／Planned／Blocked；文件就緒不代表工程任務完成。

## 5. 11/10 書面可行性審查

不建立活動、不寄邀請；由 PM 在既有窗口檢查下列證據。未指定當日時刻，不額外加上午／下午的硬性 deadline。

| 檢查序 | PM 要查核 | 證據 owner | 可接受的輸出 |
|---|---|---|---|
| 1 | 工具鏈、candidate/accepted SHA、乾淨建置 | A | 接受環境或列精確 blocker；未 build 不填通過 |
| 2 | 官方範例及實際 DL MU／STA／RU | A/B | 真正 runtime 證據或待補 trace 的清單 |
| 3 | queue-age 語意與可存取性 | B | 可得／不可得／待查，附 source/probe，而非臆測 |
| 4 | extension 路線、合法性與 RR 保留 | B，A 檢查安裝 | PM 選擇與理由，或限縮下一個 probe |
| 5 | D05–D08 共同入口、身分、時間與輸出契約 | A/B，D 提分析需求 | DESIGN 記錄核准定義或明確待補項 |
| 6 | 11/11–13 B1/probe 的可執行範圍 | PM | 哪些包可開始，哪些因哪個輸入等待 |

書面結論用以下三類，不能拿一類冒充另一類：

- **可接受該 gate**：列已符合的 acceptance criteria、命令／來源證據、PM 決策。
- **可繼續局部工作**：說明已確認與未確認的界線，例如 source inspection 可繼續，但 runtime gate 尚未過。
- **需要先排除阻礙**：列 owner、精確問題、下一個嘗試及影響的工作包，不宣稱可行性完成。

11/14 若 B1 仍不可靠，按 README 由 PM 凍結 P1 feature work，先修 baseline／measurement。P1 完整比較是 checkpoint stretch，P2 不屬最低 gate。

## 6. 分支保護的兩階段設定

設定 payload 是 repo 中的可審查檔案；GitHub 不會自動套用此資料夾。只有管理者透過 API/UI 實際套用並讀回，才算已啟用。

| 階段 | 檔案 | 設定與狀態 |
|---|---|---|
| 基本保護 | [main.json](../.github/branch-protection/main.json) | **已套用並讀回核對**：PR、最新分支的 `tooling` check、包含 admin、解決對話、禁 force-push／刪除 |
| 團隊審查提案 | [main-team.proposed.json](../.github/branch-protection/main-team.proposed.json) | 與 baseline 相同但至少 1 位核准；**未啟用**，等使用者完成不同帳號的 write collaborator 與 PM 流程 |

基本階段的 approving review count 為 0，避免只有一位擁有者時無法核准自己提交的 PR；這不等於科學／設計不需 PM 審查。team 規則的 1 位核准也不會自動指定 PM 身分；PM 最終技術決策仍要留下記錄。

真實已存在的 check 名稱為 `tooling`，由 `github-actions` 產生；它目前只驗證 bootstrap tooling，不能表示 ns-3 build／OFDMA 已通過。若改 workflow job 名稱，保護設定與 docs 必須同步，避免永遠等待不存在的 check。

2026-11-07 的 API 讀回為：`strict=true`、`contexts=["tooling"]`、`enforce_admins=true`、`required_approving_review_count=0`、`required_conversation_resolution=true`、`allow_force_pushes=false`、`allow_deletions=false`。啟用前確認原先 main 未受保護，沒有覆寫既有規則。之後再查實際設定，不能只憑 payload 檔案推測狀態。

設定依據：[GitHub 分支保護說明](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)、[REST 設定 API](https://docs.github.com/en/rest/branches/branch-protection#update-branch-protection)。

## 7. 本次啟動的完成範圍

PM 清單、A/B 開工指引與基本保護的完成，不關閉 #1/#2/#3 或其他 checkpoint Issues。尚待工程師提供的建置、queue-age、DL MU、真實 baseline 資料與 PM 科學決策，維持 TODO。

帳號／邀請／Issues 正式指派由使用者處理；不代填其他人的身分，也不建立日曆活動。專案 license 未選擇，config 中未決值維持原狀。
