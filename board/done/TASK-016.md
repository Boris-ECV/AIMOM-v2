---
id: TASK-016
title: /api/transcribe 改為非同步，解決 Lambda/API Gateway 30 秒逾時限制
type: Bug
priority: High
assignee: dev-agent
claimed_by: qa-agent
status: done
created: 2026-07-16
updated: 2026-07-16T18:30:00
epic: EPIC-003
---

## 描述

TASK-015 部署後以 20MB+ 真實錄音檔手動驗證上傳流程時發現：上傳本身完全正常
（無 413），但緊接著呼叫 `POST /api/transcribe` 卻回傳 `503 Service Unavailable`，
之後 `GET /api/status/{job_id}` 回傳 `404`。

追查 CloudWatch log（`/aws/lambda/aimom-dev-api`）確認：

```
REPORT RequestId: 9c96d8af-... Duration: 30000.00 ms Billed Duration: 30000 ms
Memory Size: 1024 MB Max Memory Used: 237 MB Status: timeout
```

根本原因：`src/transcribe.py` 的 `/transcribe` 端點是**同步**呼叫，在同一次
HTTP request/response 生命週期內，於 `run_in_executor` 中完整執行
`transcriber.transcribe(audio_path, aai_config)`（把音檔上傳給 AssemblyAI 並
輪詢等待轉錄完成）才回傳結果。這個做法受到兩層都是 30 秒的限制：

- `infra/variables.tf` 的 `lambda_timeout` 預設 30 秒
- API Gateway **HTTP API**（`aws_apigatewayv2_integration`）對 Lambda `AWS_PROXY`
  整合的逾時上限**本身也是 30 秒**（AWS 平台硬性限制，即使把 `lambda_timeout`
  調高到 Lambda 支援的 900 秒，客戶端仍然無法在原本那次 HTTP 請求內拿到結果，
  Lambda 若沒有在 30 秒內回應，API Gateway 會直接對客戶端回應逾時/錯誤）

真實會議錄音（幾十分鐘）送給 AssemblyAI 轉錄，就算 AssemblyAI 本身處理速度快，
「上傳音檔給 AssemblyAI + 排隊等待 + 輪詢直到完成」整體耗時通常遠超過 30 秒，
因此這個問題幾乎必定會在正式的長錄音上發生（TASK-014 驗證用的 3MB 短音檔之所以
沒踩到，是因為那個測試音檔夠短，轉錄在 30 秒內就完成了）。

`/api/summarize`（LLM 摘要）若呼叫大型 LLM 且逾時，理論上也可能有類似風險，
需要一併檢視（雖然 LLM 摘要一般比語音轉錄快很多，優先度較低）。

## 設計決策（development 階段補充）

盤點後確認：光是把 `/api/transcribe` 改成非同步觸發（例如自呼叫 Lambda 或
webhook）並不足夠 —— 因為 Lambda 執行環境（container）不保證同一個 job_id
的後續請求（`/api/status` 輪詢）會落在同一個 container 上，而目前整個專案
的 job 狀態（`meta.json`/`status.json`/`transcript.json`/`minutes.json`）
都只存在本機 `/tmp`，換到不同 container 就讀不到。

因此改採用以下方案（採用 AssemblyAI SDK 原生的「非阻塞送出 + 輪詢查狀態」
API，不需要自行實作 Lambda 自呼叫或 webhook 接收端）：

1. **`POST /api/transcribe`**：改用 `Transcriber.submit(audio_url, config)`
   （AssemblyAI SDK 提供的非阻塞版本，內部 `poll=False`，送出後立即回傳，
   不等待轉錄完成）取代原本會阻塞到轉錄完成的 `transcribe()`。
   S3 直傳的音檔改用 **presigned GET URL** 直接讓 AssemblyAI 去 S3 抓取，
   Lambda 不需要自己下載/上傳音檔位元組，送出速度極快（遠低於 30 秒）。
   送出後立即把 `assemblyai_transcript_id` 存起來、`stage` 設為
   `transcribing`，回應即完成
2. **`GET /api/status/{job_id}`**：當 `stage == "transcribing"` 時，改為
   呼叫 `Transcript.get_by_id(transcript_id)`（單次查詢、非阻塞）確認
   AssemblyAI 是否已完成；完成的話才在這裡把逐字稿 segments 組好、寫回
   job 狀態、把 `stage` 更新為 `transcribed`。每次輪詢都只做一次快速的
   狀態查詢，不會再有任何一次 HTTP 請求需要等待整段轉錄跑完
3. **Job 狀態儲存層改用 DynamoDB**（新增 `aimom-{env}-jobs` 表，
   `job_id` 為 hash key，其餘欄位打包成一個 JSON 字串存放，並設定
   TTL 自動過期，避免長期累積）取代本機 `/tmp` 的四個 JSON 檔案，
   確保任何 Lambda container 都能讀到最新進度。新增 `src/jobstore.py`
   作為統一的存取層；`progress.py` 的對外函式簽名保持不變
   （`update_progress()`/`read_status()`），內部改呼叫 jobstore，
   讓 `upload.py`/`transcribe.py`/`summarize.py` 既有呼叫端幾乎不用改
4. S3 暫存音檔物件**不再於 `/upload/complete` 時就立刻刪除**
   （AssemblyAI 送出後才會非同步去抓取，過早刪除有競態風險），
   改為依賴既有的 1 天 lifecycle 規則自動清除，`/api/cleanup/{job_id}`
   手動清除時也會一併嘗試刪除

## Acceptance Criteria

- [x] 盤點並確認確切的非同步架構做法：採用 AssemblyAI SDK 原生的
      `Transcriber.submit()`（非阻塞送出）+ `Transcript.get_by_id()`
      （單次查詢）搭配 DynamoDB 共用 job 狀態層，取代 Lambda 自呼叫/webhook
      方案（不需要額外的 IAM 自呼叫權限或 webhook 接收端點，複雜度更低）
- [x] 前端 `index.html` 的 `startPoll()`/`pollStatus()` 已調整：偵測到
      `stage=='transcribed'` 時才呼叫新增的 `GET /api/transcript/{job_id}`
      取得逐字稿、接著觸發 `/api/summarize`；`doUpload()` 不再等待轉錄完成，
      只送出 `/api/transcribe` 後即進入輪詢畫面
- [x] `src/summarize.py` 已檢視：目前 LLM 摘要呼叫本身耗時遠低於 30 秒
      （單次 chat completion），暫不需要套用相同的非同步模式；已改為從
      jobstore 讀取 segments、寫回 minutes（配合 job 狀態遷移）
- [x] 本次方案不需要新增 `lambda:InvokeFunction` 自呼叫權限；改為在
      `infra/iam.tf` 的 `DynamoDBAccess` 加入新的 `aimom-{env}-jobs` 表 ARN
- [x] 新增/更新單元測試：`test_transcribe.py`（非阻塞送出、presigned URL、
      新端點 `/api/transcript/{job_id}`）、`test_progress.py`（輪詢時自動
      向 AssemblyAI 查詢並完成收尾）、`test_upload.py`（改用 jobstore、
      不再提前刪除 S3 物件）、`test_summarize.py`/`test_diarize.py`/
      `test_export.py`/`test_history.py`（皆改用 jobstore + moto 模擬
      DynamoDB），全數 50 個測試通過
- [x] 手動驗證：用一個真實轉錄耗時明顯超過 30 秒的錄音檔，確認完整跑完
      上傳 → 轉錄（非同步）→ 摘要 → 匯出流程，過程中 `/api/status` 輪詢能
      正確反映進度直到完成 —— 已於 2026-07-16 由使用者在正式環境（CloudShell
      部署後）以較長音檔驗證通過，全流程無 503/逾時，處理成功並完成後續匯出

## 備注

- 此問題是在 TASK-015（S3 presigned URL 直傳）部署後、以 20MB+ 真實錄音檔手動
  驗證時發現，與 TASK-015 的上傳修正本身無關（上傳階段已確認無 413），
  屬於 TASK-012（Lambda 部署）遺留的另一個架構缺口，因此另開此工單追蹤。
- 相關真實錯誤：`POST /api/transcribe` → `503 (Service Unavailable)`，
  CloudWatch log 顯示 `Status: timeout`（30000ms）。
- **部署過程中額外發現並修復兩個問題**（皆屬本工單範圍內的架構變更直接造成，
  非既有缺陷）：
  1. Lambda 執行角色僅授予 DynamoDB 資料層級權限（GetItem/PutItem/...），
     但 `jobstore.py`/`db.py`/`usage.py` 的 `ensure_*_table_exists()` 一律
     呼叫 `dynamodb:ListTables`，導致正式環境所有相關端點回傳
     `AccessDeniedException` 500。修法：捕捉 AccessDeniedException 並視為
     「已由 Terraform 建好」直接略過，只在本機/測試環境真正建表。
  2. AssemblyAI Python SDK 的 `Transcript.get_by_id()` 名稱看似單次查詢，
     實際內部是阻塞輪詢迴圈（`while True` + `time.sleep`），會等到轉錄
     completed/error 才回傳 —— 在 `/api/status` 誤用它等於把 30 秒逾時
     問題原封不動搬到這個端點，導致真實長錄音測試時 `/api/status` 503。
     修法：改用 SDK 底層真正單次查詢、不阻塞的 `api.get_transcript()`，
     並加上例外保護避免查詢失敗連帶讓整個請求 500。

## 歷程

| 時間 | 代理 | 動作 |
|------|------|------|
| 2026-07-16T16:30:00 | orchestrator | 於 TASK-015 部署後手動驗證過程中發現 /api/transcribe 503（Lambda 30 秒逾時）問題，建立此工單追蹤，放入 backlog |
| 2026-07-16T17:30:00 | dev-agent | 完成實作：新增 src/jobstore.py（DynamoDB 共用 job 狀態層）、src/transcript_utils.py；改寫 src/transcribe.py（非同步送出 + 新增 GET /api/transcript/{job_id}）、src/progress.py（輪詢時自動向 AssemblyAI 查詢並收尾）、src/upload.py（改用 jobstore、不再提前刪除 S3 物件）、src/summarize.py/src/diarize.py/src/export.py/src/history.py（改用 jobstore）；新增 infra/dynamodb.tf 的 aimom-{env}-jobs 表、infra/iam.tf 授權、infra/lambda.tf 環境變數；更新 src/frontend/index.html 前端輪詢邏輯；更新全部相關單元測試改用 jobstore + moto 模擬 DynamoDB，50 個測試全數通過；terraform validate 通過。待使用者於 CloudShell 部署後進行真實長錄音手動驗證 |
| 2026-07-16T17:45:00 | dev-agent | 部署後第一次真實驗證發現 AccessDeniedException（Lambda 角色缺 dynamodb:ListTables），修正 jobstore.py/db.py/usage.py 的 ensure_*_table_exists() 遇權限不足即略過，新增 test_jobstore.py 迴歸測試（52 個測試通過），重新產生 task016-update.zip |
| 2026-07-16T18:20:00 | dev-agent | 部署後第二次真實驗證發現長錄音時 /api/status 503，追查發現 AssemblyAI SDK 的 Transcript.get_by_id() 內部為阻塞輪詢，改用底層非阻塞的 api.get_transcript()，加上查詢失敗的例外保護，更新 test_progress.py（53 個測試通過），重新產生 task016-update.zip |
| 2026-07-16T18:30:00 | qa-agent | 使用者於正式環境以真實長錄音完整驗證：上傳 → 轉錄（非同步）→ 摘要成功，無 503/逾時，全流程通過。移至 done |
| 2026-08-03T00:00:00 | dev-agent | LLM engine 由 Groq / GitHub Models 切換測試，實測 Groq `llama-3.3-70b-versatile` 因 TPM 12000 限制易在長逐字稿上失敗；改接 Bedrock proxy（OpenAI 相容端點）並以 `mistral.mistral-large-3-675b-instruct` 作為預設模型，同時修正 Lambda 環境變數前後空白造成的 404/401 問題 |
| 2026-08-04T00:00:00 | dev-agent | 補強 `src/config.py` / `src/summarize.py` 的錯誤訊息與 env trim，讓 Bedrock proxy 404/401 可直接回傳詳細 response body，並完成 `lambda-code.zip` 重新打包與部署驗證，最終摘要流程恢復正常 |
