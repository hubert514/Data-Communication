# 版本管理、協作與交付規範

文件修訂：r2。更新日期：2026-11-07。維護與技術決策：Technical PM。

適用對象：Engineer A、Engineer B、Technical PM、Report Lead。
本文件具體化 [README 第 7–10 節](../README.md) 的工作流程，未變更研究問題、實驗設定或 checkpoint 驗收標準。

## 1. 版本的單一來源

| 版本／內容 | 記錄位置 | 規則 |
|---|---|---|
| 科學規格、分工與里程碑 | `README.md` | 需求變更需 PM 決策與 PR；交接文件不能覆蓋規格 |
| 開發中的 project 版本 | Git commit SHA＋分支／PR | 分支名會移動，證據必須另外寫完整 SHA |
| ns-3 候選來源 | `configs/ns3-candidate.json` | 固定 upstream URL、tag、完整 commit；不得改用浮動 master |
| 接受的環境與版本證據 | `docs/ENVIRONMENT.md` | 「候選身分固定」與「建置／DL MU 已驗收」分開 |
| A/B 介面與研究決策 | `docs/DESIGN.md` | 記錄參數、身分、時間、schema、核准 PR／決策日期 |
| 場景設定 | `configs/` 中核准的設定 | 草案目前是 `0-proposed`；每次 run 保存實際有效值 |
| patch／overlay | `patches/series`、追蹤的 patch／sources 與安裝方式 | exact upstream SHA、檔案順序與 checksum 可追溯 |
| 輸出 schema | README／`results/README.md`＋核准 migration | 不可同名欄位偷換層次、單位、分母或缺失值 |
| 執行證據 | run metadata、原始資料、logs、checksums | 不以「最新版本」或檔名代替精確版本 |
| 工作指示 | A/B 交接書＋Issues | 文件 r1 為指示修訂號，不是軟體 release 或實驗完成標記 |

目前 ns-3 候選為 `ns-3.49`、`418210e8914e9f6bcb5cddbcc94a2cecb7853b68`。這仍不代表 simulator build／DL MU 驗收通過。日後若換版本，A 同步候選 lock、ENVIRONMENT 與重建證據，B 更新 patch／source references 與回歸結果，PM 在同一 PR 或相連的整合 PR 核准。

不得為尚未完成的功能建立「已完成版本」描述。目前未建立 project release tag 的規則；需要 checkpoint／期末 release tag 時，由 PM 決定名稱及對應已接受的 `main` commit。不要拿 ns-3 tag 當成 project 版本。

## 2. 分支、同步與提交

| 分支 | 用途 | 主要負責者 |
|---|---|---|
| `main` | 已審查的共同整合基點 | PM 管理合併；現階段仍為 pre-implementation，不宣稱 simulator 已可建置 |
| `feature/simulation-*` | 環境、場景、流量、量測、run 工具 | A |
| `feature/scheduler-*` | source probe、P1/P2、scheduler tracing/tests | B |
| `docs/*` | 文件、工作規範、報告來源等 | 依文件 owner |

每個分支處理一個可審查工作包，起點及依賴寫進 PR。除已知且有記錄的 stacked PR 依賴外，從最新 `origin/main` 開始。bootstrap 分支已完成初始化用途，工程實作請另開短期分支。

乾淨工作目錄的開工範例：

```bash
git status --short --branch
git fetch origin
git switch main
git pull --ff-only origin main
git rev-parse HEAD
# A 的分支範例；B 改用 feature/scheduler-feasibility
git switch -c feature/simulation-baseline
```

若已存在同名分支，先核對它的內容與 owner，不要用會覆寫分支的指令重建。若有未提交工作，先保存／提交自己的內容；不要 reset 或刪掉同學工作來取得「乾淨」。

建議提交方式：

```bash
git diff --check
git diff --stat
git add sim/README.md
git diff --cached
git commit -m "docs: clarify baseline handoff (refs #5)"
```

以上只示範流程；`git add` 要換成此次實際修改的明確路徑。提交前檢查 staged diff，不用 `git add .` 把不相關內容一起帶入。commit message 可用 `docs:`、`build:`、`feat:`、`fix:`、`test:`，並帶 Issue 關聯；前綴不代表功能已驗收。

- 不直接將日常工程變更推上 `main`；經 PR、檢查與 PM 所需審查後合併。
- 不 force-push `main`，也不改寫別人正在使用的共用分支歷史。
- `main` 更新後，先 `git fetch origin`，在自己的分支整合 `origin/main` 並重跑受影響檢查；共用分支優先採不改寫歷史的 merge。衝突由相關 owner 協作處理。
- 不為了讓 CI 綠燈而刪除測試、假造資料或關掉應執行的檢查。
- GitHub 基本 branch protection 已啟用：PR、最新分支的 `tooling` CI、包含 admin、對話需解決、禁強推／刪除；目前 required approvals=0。至少 1 位其他審查者的 team 規則仍是提案，等使用者完成成員設定後再啟用；不能把基本保護稱為已強制 PM 審查。

## 3. 共用檔案的協作 owner

| 檔案／區域 | 協調主責 | 另一位工程師需參與的情境 |
|---|---|---|
| `sim/`、場景／流量、flow/packet writer | A | B 需要接入 selector、身分或時間事件 |
| `scheduler/`、scheduler focused tests、decision writer | B | A 需要接入共同場景、metadata、run 目錄 |
| setup/build/run 入口 | A | B 變更 patch／overlay 安裝或 scheduler 註冊 |
| scheduler patches 與 `patches/series` | B | A 驗證可乾淨安裝與 baseline 回歸 |
| `configs/` | A 協調、B 提供政策欄位 | 參數與比較條件由 PM 核准；不各建衝突版本 |
| DESIGN／schema／ENVIRONMENT | 依內容由 A/B 提案，PM 核准 | 跨版本、語意、介面或科學比較變更 |
| 正式 aggregate／plot 與報告來源 | Report Lead | A 提供資料契約，B 解釋 scheduler 事件 |

owner 表用於避免衝突，不是 GitHub 權限設定。實際帳號、存取與正式指派由使用者自行處理。改共用檔案前，在 Issue／PR 寫清修改範圍與依賴；不要同時維護兩份互不相容的 canonical config／entry point。

## 4. 介面與 schema 變更程序

以下變更都要列出舊／新定義、受影響 producer／consumer、遷移與重跑範圍：

1. ns-3 tag/SHA、工具鏈或 patch 安裝方式。
2. selector／CLI／設定鍵、預設值與 config/CLI 優先序。
3. logical STA／AID／MAC／flow／LL-BE mapping。
4. enqueue／service timestamp、measurement window、drain、deadline 分母。
5. CSV 欄位、單位、集合編碼、status／null、metadata 定義。
6. AC、RU、ACK、rate control 等會影響科學比較的設定。

步驟為「Issue 提案 → A/B 列影響 → PM 核准 → producer/consumer 與文件同步 → 相應測試 → PR 合併」。不要自行給 schema 指定已核准的新版本號；目前草案可持續討論，但正式採用與 migration 必須有 PM 決策。

舊資料保留原版本與 raw files；轉換時產出新檔案並記錄來源／轉換命令，不覆寫成看似同一次原始 run。

## 5. 每個工作包的開始與完成標準

| 狀態 | 最低記錄 | 能否宣稱驗收 |
|---|---|---|
| Planned／TODO | owner、Issue、目標窗口、輸入與相依 | 否 |
| Implemented | 程式／文件 diff、project SHA、仍缺哪些測試 | 否 |
| Tested | 實際命令、環境、SHA、config、seed/run、結果與 evidence | 僅代表列出的檢查已執行 |
| Blocked | 阻礙、影響、已試方法、需要誰提供什麼 | 否；有 blocker report 不等於 gate 通過 |
| PM accepted | 對應 acceptance criteria、證據與 PM 決策記錄 | 僅限 PM 接受的該項範圍 |

source inspection 可以完成「找到 source／確認 access level」這類任務，不能完成「已編譯」「實際 DL MU」「性能改善」。CLI exit 0、unit tests、CI 成功各自只代表該檢查的範圍。

工作包完成時，一併交付輸入版本、修改範圍、產物位置、命令／實際輸出、限制及下一位接收者。若有必要輸入仍 TODO，可先做不依賴它的調查，不能把未決假設硬編碼成正式比較。

## 6. PR 合併與實驗證據

每個 PR 應包含：

- Issue／工作包 ID、owner、目標里程碑、base commit 與依賴 PR。
- 問題與完成後行為、修改檔案、已實作與未實作範圍。
- 實際測試命令與結果；沒有執行的項目填 TODO／Blocked。
- upstream/project SHA、patch 指紋、有效設定與 seed/run（不適用則說明）。
- evidence URL／可共享路徑、checksum、已知限制。
- 是否改科學比較／介面／schema；需要的 PM 決策。

合併前確認 HEAD 沒有在檢查後偷偷變動；若新增修改，重跑受影響檢查。PR 關聯任務不表示關閉它；只在對應驗收真的通過時使用 `Closes`。這次文件合併不關閉 #1–#12，也不表示 checkpoint 驗收。

A/B 關鍵 C++ 改動盡可能交叉審查，PM 處理設計、整合與接受。使用者明確授權代理完成某次檢查與合併時，代理應記錄授權範圍；文件審查／推送授權不會自動接受尚未執行的科學驗收。

實驗證據以乾淨、已提交的 project source 為優先；若除錯 run 有 dirty code，明確標 preliminary，保存 diff／指紋，不把它混入正式比較。run metadata 不應用來取代原始 trace／packet data。

`.local/`、build、二進位、大型 raw PCAP 維持 gitignored。小型真實證據／fixture 要標示性質，必要時明確選取檔案提交；大量結果保留 manifest、checksum 與所有接收者可存取的位置。不得以缺失值、假 receive time 或預期曲線代替資料。

## 7. 文件修訂與交接入口

文件若改 owner、時程、版本、驗收或工作範圍，更新文件修訂號／日期並在 PR 說明變更原因；Git 歷史保留完整差異。單純檢查清單尚未執行時不打勾。

- [Engineer A：環境、基準、流量與量測](ENGINEER_A_TASKS.zh-TW.md)
- [Engineer B：排程器、tracing 與測試](ENGINEER_B_TASKS.zh-TW.md)
- [PM 進度與未決事項](PM_STATUS.md)
- [Issues 與里程碑](ISSUES.md)
- [PM 決策與書面可行性驗收、分支保護設定](PM_DECISIONS.zh-TW.md)

目前尚待處理：使用者完成實際帳號／正式指派；PM 確認 project license、accepted toolchain／ns-3 runtime、完整 A/B 契約與 schema 正式版本；團隊加入後啟用一位核准人規則。文件／骨架已合併不會使這些 TODO 自動完成。

修訂紀錄：r1 定義協作規範；r2 記錄基本保護的實際啟用、使用者自行處理成員設定，並連到 PM 決策清單。技術／科學驗收狀態未變。
