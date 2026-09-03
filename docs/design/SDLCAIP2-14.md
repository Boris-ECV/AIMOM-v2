# 設計文件 — SDLCAIP2-14 [INCIDENT] 正式環境登入後呼叫後端 API 出現 Failed to fetch

## 對應需求規格
G1 已核准的 ticket 描述（SDLCAIP2-14）。根因與修法已在 G1 完全定案，非本文件範圍：
CloudWatch Logs 證實 Lambda 每次 cold start 皆因
`cannot import name 'api' from 'assemblyai.transcriber'` 而 crash。
`src/requirements-lambda.txt` 第 5 行 `assemblyai>=0.30.0` 缺少上限，導致
`scripts/build_lambda_layer.sh` 重建 Layer 時解析到會移除
`assemblyai.transcriber.api`（`src/progress.py` 有 import）的 0.65.0+ 版本。
`src/requirements.txt` 第 6 行已在前次事故修正為
`assemblyai>=0.30.0,<0.65.0  # 0.65.0+ removed assemblyai.transcriber.api, used by src/progress.py`，
本次修法就是把 `requirements-lambda.txt` 第 5 行改成與之完全一致的內容。

## 介面/API 契約
無——純依賴版本鎖定，不涉及對外介面變更。

## 資料模型
無新增資料模型。

## 關鍵技術決策
G1 spec 已決定 WHAT（把 `requirements-lambda.txt` 的 assemblyai 版本鎖定改成
與 `requirements.txt` 一致）。本設計文件唯一要補的是 HOW 驗證
Gherkin 情境「依 requirements-lambda.txt 實際安裝版本 import lambda_handler
不會失敗」——因為這是一個「兩個 requirements 檔案必須同步鎖版」的靜態一致性
問題，而非執行期行為，仿照本專案既有慣例（`src/tests/test_ci_backend_job.py`：
以正規表示式解析設定檔文字、斷言結構/內容一致，不實際跑 terraform/AWS），
新增測試採同一風格的靜態文字比對，而非真的在測試環境安裝套件跑 import
（成本高、且會受測試環境套件快取影響，不穩定）：

- 新增 `src/tests/test_lambda_layer_requirements_pin.py`：
  1. 讀取 `src/requirements-lambda.txt` 與 `src/requirements.txt` 全文。
  2. 各自用正規表示式 `r"^assemblyai\s*(.+)$"`（逐行掃描，忽略前後空白）
     擷取 assemblyai 那一行的版本限制字串（含 comment 前的部分）。
  3. 斷言兩邊都找到 assemblyai 行（找不到就是檔案格式跑掉，直接 fail 並給
     清楚訊息）。
  4. 斷言兩邊解析出的版本限制字串（去除 inline comment 後）完全相等，且
     必須包含 `<0.65.0` 上限（直接寫死斷言 `"<0.65.0" in constraint`，
     不用泛用 semver 邏輯——這是本次事故的確切邊界，寫死比通用解析更不會
     漏掉這個 regression）。
  5. 額外斷言 `requirements-lambda.txt` 的 assemblyai 行含有解釋性 comment
     （`assert "#" in line and "assemblyai.transcriber.api" in line`），
     確保未來有人手動改版本時，理由不會被無聲丟失。

  這個測試會在本次修法「之前」對 `requirements-lambda.txt` 直接 fail
  （因為目前該行沒有 `<0.65.0` 也沒有 comment），修法「之後」通過——
  精確對應 regression 的起因與修復，且不需要真的安裝 assemblyai 或呼叫
  `lambda_handler`，執行速度快、不受套件源版本波動影響。

  之所以不寫「真的 import lambda_handler」的測試：CI 的 `backend` job
  已經會用 `requirements-lambda.txt` 建 Layer 並部署，是更貼近正式環境的
  端到端驗證；這裡的單元測試目的是在本地/PR 階段就攔住「兩份 requirements
  又不同步」這個具體錯誤模式，兩者互補，不重複造輪子。

## 開放設計問題(定稿時必須為空)
無。
