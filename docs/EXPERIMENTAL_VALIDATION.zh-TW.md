# RR／Queue-Age 實驗驗證結果

## 結論與範圍

本次在既有 1 AP／8 STA（4 LL／4 BE）場景完成 18 次真實 ns-3.49
模擬：BE 每 flow 為 4、8、12 Mbit/s，各使用 RngRun 1、2、3，並對每個
RngRun 配對執行官方 RR 與 class-agnostic Queue-Age。LL 固定為每 flow
160 kbit/s，應用流量 5 秒，另有 200 ms drain；沒有改動 PHY、MAC priority、
封包大小或 RU 規則。

18/18 runs 均通過 AID／class mapping、封包帳務、非負 delay、HE-MU、合法
20 MHz RU、最多四位 MU users、scheduler final allocation 與 PHY sequence
逐批一致等檢查。所有 raw checksum 與 run metadata 相符，且每個 run 都保存
完整重現命令。大型 trace 位於 `.local/experimental-validation/`，沒有納入 Git。

測試結果支持：8 Mbit/s 時原先看到的 LL latency degradation 可以在三個
matched RngRun 重現；12 Mbit/s 已進入壅塞區，Queue-Age 變成以大幅增加 LL
delay 換取較高 BE delivery／throughput，不能再稱為「吞吐不變」。這些結果
只適用於目前 class-agnostic prototype 與測試設定，不代表一般 OFDMA 結論。

## 實驗矩陣與方法

| BE load / flow | RngRun | RR runs | Queue-Age runs | 結果 |
|---:|---|---:|---:|---|
| 4 Mbit/s | 1, 2, 3 | 3 | 3 | 6/6 PASSED |
| 8 Mbit/s | 1, 2, 3 | 3 | 3 | 6/6 PASSED |
| 12 Mbit/s | 1, 2, 3 | 3 | 3 | 6/6 PASSED |

統計單位是每個獨立 RngRun，不是 packet。報告列出平均、sample SD，以及
`n=3` 時的雙尾 95% Student-t interval。三次重複的 interval 很寬且對分布
假設敏感，只用來呈現不確定性，不宣稱 statistical significance。吞吐量在
4／8 Mbit/s 的不同 RngRun 完全相同；delay 與 8／12 Mbit/s 的 HE-MU 數量
仍有變化，因此 scenario 不是完全 deterministic，但相同吞吐值不能假裝成
額外隨機資訊。

## 各 RngRun 的 LL 結果

下表為 `RR -> Queue-Age`，單位為 ms；完整 LL／BE throughput、PDR、Jain、
queue age 與 STA distribution 在 machine-readable CSV。

| BE load | RngRun | LL mean delay | LL P95 delay | aggregate throughput (Mbit/s) |
|---:|---:|---:|---:|---:|
| 4 | 1 | 0.583528 → 0.600984 | 1.452950 → 1.455800 | 16.63616 → 16.63616 |
| 4 | 2 | 0.584718 → 0.602391 | 1.455700 → 1.479200 | 16.63616 → 16.63616 |
| 4 | 3 | 0.581977 → 0.599812 | 1.445750 → 1.465550 | 16.63616 → 16.63616 |
| 8 | 1 | 0.913537 → 2.047962 | 1.542850 → 3.043950 | 32.63360 → 32.63360 |
| 8 | 2 | 0.889721 → 2.026714 | 1.471950 → 2.963650 | 32.63360 → 32.63360 |
| 8 | 3 | 0.884518 → 2.010544 | 1.453450 → 2.705500 | 32.63360 → 32.63360 |
| 12 | 1 | 3.114885 → 36.891899 | 5.699950 → 87.390224 | 46.52672 → 48.50240 |
| 12 | 2 | 3.245852 → 37.301507 | 5.693200 → 88.250024 | 46.50176 → 48.44480 |
| 12 | 3 | 3.046681 → 37.215478 | 5.389200 → 88.151224 | 46.54016 → 48.45440 |

## 負載結果與 paired differences

| BE load | Policy | LL mean / P95 (ms) | BE mean / P95 (ms) | Total throughput (Mbit/s) | LL / BE PDR |
|---:|---|---|---|---:|---|
| 4 | RR | 0.583408 / 1.451467 | 0.806078 / 1.003117 | 16.63616 | 1.000000 / 1.000000 |
| 4 | Queue-Age | 0.601062 / 1.466850 | 0.803768 / 0.791150 | 16.63616 | 1.000000 / 1.000000 |
| 8 | RR | 0.895925 / 1.489417 | 1.906768 / 2.498266 | 32.63360 | 1.000000 / 1.000000 |
| 8 | Queue-Age | 2.028407 / 2.904367 | 1.903494 / 2.482558 | 32.63360 | 1.000000 / 1.000000 |
| 12 | RR | 3.135806 / 5.594117 | 114.435606 / 160.761272 | 46.52288 | 1.000000 / 0.956073 |
| 12 | Queue-Age | 37.136295 / 87.930491 | 70.356101 / 129.335369 | 48.46720 | 1.000000 / 0.996586 |

主要 `Queue-Age - RR` paired 統計如下：

| BE load | Metric | Mean difference | SD | 95% t interval |
|---:|---|---:|---:|---|
| 4 | LL mean delay (ms) | +0.017655 | 0.000190 | [0.017182, 0.018127] |
| 4 | LL P95 delay (ms) | +0.015383 | 0.011011 | [-0.011971, 0.042738] |
| 8 | LL mean delay (ms) | +1.132481 | 0.005736 | [1.118231, 1.146732] |
| 8 | LL P95 delay (ms) | +1.414950 | 0.141154 | [1.064276, 1.765624] |
| 12 | LL mean delay (ms) | +34.000489 | 0.201633 | [33.499563, 34.501414] |
| 12 | LL P95 delay (ms) | +82.336374 | 0.568868 | [80.923114, 83.749634] |
| 12 | aggregate throughput (Mbit/s) | +1.944320 | 0.030740 | [1.867951, 2.020689] |
| 12 | BE PDR | +0.040513 | 0.000641 | [0.038922, 0.042104] |

4／8 Mbit/s 的 per-class throughput 與 PDR 均未改變。12 Mbit/s 的 BE
offered load 合計為 48 Mbit/s，RR 在 200 ms drain 截止仍有約 4.4% BE
packets 未收完；Queue-Age 將 BE PDR 提高至約 0.9966，但 LL mean/P95 delay
分別增加約 34／82 ms。LL PDR 在所有 runs 都是 1.0。每 class 的 Jain
throughput fairness 皆為 1 或非常接近 1；這只表示同 class 四個 flows 均衡，
不能抵銷 class 間的 latency trade-off。

## LL latency degradation 證據

| 假說 | 4 Mbit/s | 8 Mbit/s | 12 Mbit/s | 判讀 |
|---|---|---|---|---|
| H1：BE queue head 比 LL 更老 | 不支持 | 不支持 | 支持 | 8 Mbit/s Queue-Age 下平均 LL／BE age 為 1.817／1.165 ms，排序後反而是 LL head 較老；12 Mbit/s 為 50.122／65.138 ms |
| H2：final service share 移向 BE | 不支持 | 不支持 | 支持 | 8 Mbit/s 的 BE allocation share 在兩 policy 完全相同（約 0.8621）；12 Mbit/s 由 0.6327 升至 0.9072 |
| H3：LL service gap 增加 | 不支持 | 證據不足 | 支持 | 8 Mbit/s mean gap 差只有 0.000863 ms 且 interval 包含 0；12 Mbit/s 由約 10.006 增至 48.585 ms |
| H4：與 airtime credit 交互作用 | 證據不足 | 證據不足 | 證據不足 | trace 未記 credit 值，不能由結果反推 |
| H5：只改等待時間、不改吞吐 | 支持 | 支持 | 不支持 | 4／8 Mbit/s throughput、PDR 不變而 LL delay 上升；12 Mbit/s throughput、PDR 也改變 |
| H6：backlog／aggregation 決定 final selection | 證據不足 | 證據不足 | 證據不足 | trace 沒有 queue depth 與 A-MPDU membership |

針對每個 run 的 LL P95 tail packets，分析其 `Tx -> Rx` 等待區間內的 final
allocations。8 Mbit/s RR 的三個 runs 在 tail windows 內 BE allocation share
皆為 0；Queue-Age 皆為 0.5。12 Mbit/s Queue-Age 則約為 0.944--0.945，且
tail windows 中 LL／BE candidate age 都約 94--95 ms。這支持「Queue-Age
改變 LL 封包等待期間的服務時序」的關聯，但 windows 是事後依 delay 選出，
不能單獨證明因果。8 Mbit/s 的全程 BE allocation share 不變，也顯示整體
allocation 次數不足以解釋 degradation，時序與 aggregation 仍需更細 trace。

## 技術限制與下一步

- 目前只有三個 RngRun；95% interval 只作描述。正式研究應擴至至少 10--30
  個 matched runs，再預先定義檢定與 effect size。
- `packet-summary.csv` 的 `lost_by_sim_stop` 是 200 ms drain 截止的觀察結果，
  不等同 PHY drop cause。12 Mbit/s 應另外做 drain-time sensitivity test。
- 現有 scheduler trace 應最小幅度增加 observation-only airtime credit、queue
  depth、final A-MPDU MPDU count／bytes；不得改 selection 或 RU allocation。
- 下一個 policy 研究方向是 LL-aware age/deadline 或受約束的 class-aware
  ordering，但應在完成上述 observability 與更多 matched runs 後再實作。
- No-OFDMA baseline 為 optional，本輪沒有執行，以避免稀釋 mandatory load
  sweep 與 degradation diagnosis。
- 本機沒有 `clang-format` 17--22 或無版本命令；依限制未安裝額外 formatter。
  Python 語法、單元測試與 `git diff --check` 均有執行，但 C++ style check 的
  這項環境限制仍存在。

## 重現

```bash
python3 scripts/experimental_validation.py run-matrix \
  --loads 4,8,12 --rng-runs 1,2,3
python3 scripts/experimental_validation.py aggregate
```

逐 run 精確命令、輸出路徑與 HE-MU 數量見
`docs/evidence/b-experimental-validation-01/experiment-matrix.csv`。
