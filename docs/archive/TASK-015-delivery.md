# TASK-015 交付報告：音檔上傳改用 S3 Presigned URL 直傳

## 摘要

修正 TASK-014 手動驗證階段發現的 `413 Content Too Large` 問題：大於約 4-5MB 的
音檔上傳會撞到 API Gateway（10MB）與 Lambda 同步呼叫（6MB，實際因 base64 編碼
再打折）的 payload 硬性上限。改為前端直接以 S3 Presigned PUT URL 上傳，完全繞過
API Gateway/Lambda 傳輸音檔本體。

## 變更內容

- **新增** `POST /api/upload/presign`：簽發限時有效（預設 600 秒）的 S3 PUT
  presigned URL
- **新增** `POST /api/upload/complete`：確認 S3 物件已上傳後，由後端下載到
  `/tmp`、驗證音檔長度、寫入既有的 `meta.json`，下載完成即刪除 S3 暫存物件
- **保留** 舊版 `POST /api/upload`（multipart 直傳），供本機開發/小檔案使用
- `src/frontend/index.html`：`doUpload()` 改為 presign → `fetch(PUT)` 直傳 S3 →
  complete → 既有轉錄/摘要流程
- `infra/lambda.tf`：新增 `AUDIO_BUCKET_NAME` 環境變數
- 確認既有 IAM（`s3:GetObject/PutObject/DeleteObject`）與 S3 CORS 設定已足夠，
  **無需修改**
- 新增 7 個單元測試（含安全性回歸測試），套件 46/46 pass

## 過程中發現並修正的安全性問題

Code review 發現 `/api/upload/complete` 未驗證 `s3_key` 是否確實屬於呼叫端聲稱的
`job_id`，且 `job_id` 未經格式驗證即用於組出檔案路徑，理論上可能被用來存取其他
job 的音檔或造成路徑跳脫。已修正為：`job_id` 必須是合法 UUID，且 `s3_key` 必須
等於伺服器依 `job_id` 重新計算出的既定命名（`{job_id}/audio{suffix}`），不符即
回 400。

## 部署

- CloudShell 上以增量 zip（僅 5 個變動檔案）更新既有的 `aimom-infra-v4` 工作目錄
- `terraform apply`：僅 `aws_lambda_function.api` in-place 更新（新程式碼 +
  `AUDIO_BUCKET_NAME`），Lambda Layer 未變動
- 前端：`aws s3 sync` + CloudFront invalidation

## 手動驗證結果

使用 20MB+ 真實錄音檔測試：

- ✅ **上傳階段**（presign → S3 PUT → complete）完全正常，網路紀錄確認**無 413**
  —— 本工單目標（解決大檔案上傳 413）達成
- ⚠️ 緊接著的 `/api/transcribe` 回傳 `503`，CloudWatch log 確認為
  `Status: timeout`（Lambda 於 30000ms 被砍斷）。這是**下游全新問題**，與本工單
  無關（詳見「已知限制」），另開 **TASK-016** 追蹤

## 已知限制（已開立後續工單）

**TASK-016**：`/api/transcribe` 目前同步等待 AssemblyAI 轉錄完成才回應，
受 Lambda（`lambda_timeout`，預設 30 秒）與 API Gateway HTTP API 對 Lambda
整合逾時上限（同為 30 秒，無法調高）雙重限制。真實會議錄音的轉錄耗時通常遠超
過 30 秒，需改為非同步架構（前端既有的 `/api/status` 輪詢機制可沿用）。
