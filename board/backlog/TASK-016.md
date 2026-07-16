---
id: TASK-016
title: /api/transcribe 改為非同步，解決 Lambda/API Gateway 30 秒逾時限制
type: Bug
priority: High
assignee: unassigned
status: backlog
created: 2026-07-16
updated: 2026-07-16T16:30:00
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

## Acceptance Criteria

- [ ] 盤點並確認確切的非同步架構做法（建議方向，設計時再確認取捨）：
      例如讓 `/api/transcribe` 收到請求後，先把狀態寫成 `transcribing`、
      立即回應 202/200，然後透過 `boto3` 以 **非同步（Event）方式**
      重新呼叫同一個 Lambda function（或另一支 worker function）執行實際的
      AssemblyAI 轉錄；也可評估改用 AssemblyAI 官方的 **webhook callback**
      機制（轉錄完成後由 AssemblyAI 主動呼叫後端一個 callback 端點），
      避免自行輪詢等待
- [ ] 前端 `index.html` 已有的 `startPoll()` / `/api/status` 輪詢機制需確認
      能正確反映非同步轉錄的進度與完成狀態，不需要大改
- [ ] `src/summarize.py` 一併檢視是否有相同的同步逾時風險，若耗時較長也需要
      套用相同的非同步模式
- [ ] Lambda 執行角色（IAM）如需新增 `lambda:InvokeFunction`（自呼叫或呼叫
      worker function）權限，需一併於 `infra/iam.tf` 補上
- [ ] 更新/新增單元測試涵蓋非同步觸發邏輯（mock 非同步呼叫、webhook callback 等）
- [ ] 手動驗證：用一個真實的 20-30 分鐘會議錄音（或至少轉錄耗時明顯超過 30 秒的
      音檔），確認完整跑完 上傳 → 轉錄（非同步）→ 摘要 → 匯出流程，過程中
      `/api/status` 輪詢能正確反映進度直到完成

## 備注

- 此問題是在 TASK-015（S3 presigned URL 直傳）部署後、以 20MB+ 真實錄音檔手動
  驗證時發現，與 TASK-015 的上傳修正本身無關（上傳階段已確認無 413），
  屬於 TASK-012（Lambda 部署）遺留的另一個架構缺口，因此另開此工單追蹤。
- 相關真實錯誤：`POST /api/transcribe` → `503 (Service Unavailable)`，
  CloudWatch log 顯示 `Status: timeout`（30000ms）。

## 歷程

| 時間 | 代理 | 動作 |
|------|------|------|
| 2026-07-16T16:30:00 | orchestrator | 於 TASK-015 部署後手動驗證過程中發現 /api/transcribe 503（Lambda 30 秒逾時）問題，建立此工單追蹤，放入 backlog |
