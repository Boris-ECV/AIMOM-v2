---
id: TASK-015
title: 音檔上傳改用 S3 Presigned URL 直傳，解決大檔案 413 限制
type: Bug
priority: High
assignee: qa-agent
claimed_by: qa-agent
status: testing
created: 2026-07-16
updated: 2026-07-16T11:35:00
epic: EPIC-003
---

## 描述

TASK-014 手動驗證上線流程時發現：上傳 7.91MB 音檔會回傳 `413 Content Too Large`，
3MB 以下小檔案則正常。

追查原因：目前 `src/upload.py` 的 `/api/upload` 端點，是讓瀏覽器把整份音檔以
`multipart/form-data` 直接 POST 給 API Gateway → Lambda（TASK-012 導入 Mangum
Lambda 部署時沿用了原本假設本機/EC2 伺服器的寫法，把檔案內容整包塞進 request
body 裡寫入 `/tmp`），這會撞到兩個 AWS 平台硬性限制（皆無法用設定調高）：

- **API Gateway（HTTP API）payload 上限**：10MB
- **Lambda 同步呼叫 payload 上限**：6MB
- 且 API Gateway 收到二進位 body 時會先整包 **base64 編碼**才轉給 Lambda，
  多墊高約 33% 大小，因此實際可用的音檔上限遠低於 6MB／10MB（大約只到
  4-5MB 原始檔案大小），對於真實會議錄音（幾十分鐘、數十 MB）完全不可行。

## Acceptance Criteria

- [x] 後端新增簽發 S3 Presigned PUT URL 的端點（`POST /api/upload/presign`），
      回傳一個限時有效（預設 600 秒，可用 `AUDIO_PRESIGN_EXPIRES_SEC` 調整）的 URL，
      讓瀏覽器直接 PUT 音檔到 `audio_bucket_name`（`AUDIO_BUCKET_NAME` 環境變數，
      由 Terraform 自動帶入），完全繞過 API Gateway/Lambda 的 payload 限制
- [x] 前端 `index.html` 上傳流程改為：先呼叫 `/api/upload/presign` → 瀏覽器直接
      `fetch(presignedUrl, { method: 'PUT', body: file })` 上傳到 S3 → 上傳完成後
      呼叫新增的 `POST /api/upload/complete`（帶 `job_id` + `s3_key`）建立 job，
      再依序呼叫既有的 `/api/transcribe`、`/api/summarize`（沿用原本流程不變）
- [x] 設計決策：不修改 `src/transcribe.py`。改在新的 `POST /api/upload/complete`
      端點內，由後端用 `boto3` 的 `download_file()` 把 S3 物件下載到 `/tmp`、
      驗證音檔長度、寫入既有的 `meta.json`（含 `audio_path` 本機路徑），下載完成後
      即刪除 S3 暫存物件（bucket 本身仍保留 1 天 lifecycle 保底）。
      如此 `transcribe.py` 完全不需變動，仍讀取本機 `/tmp` 音檔，風險最小
- [x] IAM 角色（`infra/iam.tf` 的 `lambda_exec`）：確認既有的
      `s3:GetObject` / `s3:PutObject` / `s3:DeleteObject`（`S3AudioAccess` statement）
      已足夠涵蓋 `generate_presigned_url`（僅用呼叫端憑證簽名，不需額外 IAM action）
      與 `/upload/complete` 的下載/刪除操作，**無需修改 IAM**
- [x] `infra/s3.tf` 的 audio bucket：確認既有 CORS 設定
      （`allowed_methods = ["PUT", "GET"]`、`allowed_origins = var.frontend_callback_urls`）
      已涵蓋前端網域直接 PUT 的需求，**無需修改**
- [x] 新增單元測試涵蓋 presign / complete 端點邏輯（mock `boto3` 的
      `generate_presigned_url` / `download_file` / `delete_object`），
      `src/tests/test_upload.py` 新增 7 個測試（含安全性驗證），全部套件 46/46 pass
- [ ] 手動驗證：上傳一個 20MB+ 的真實錄音檔案，確認完整跑完
      上傳 → 轉錄 → 摘要 → 匯出流程（待重新部署後於瀏覽器實測）

## 備注

- 此問題是在 TASK-014（前端 Cognito OAuth 登入整合）手動驗證階段發現，
  與登入整合本身無關，屬於 TASK-012（Lambda 部署）遺留的架構缺口，
  因此另開此工單追蹤，不影響 TASK-014 驗收。
- 已確認：3MB 以下小檔案上傳可正常運作（TASK-014 驗證時使用），
  問題只發生在檔案較大時。
- 相關真實錯誤：`POST /api/upload` → `413 (Content Too Large)`。

## 歷程

| 時間 | 代理 | 動作 |
|------|------|------|
| 2026-07-16T10:35:00 | orchestrator | 於 TASK-014 手動驗證過程中發現大檔案上傳 413 問題，建立此工單追蹤，放入 backlog |
| 2026-07-16T11:05:00 | dev-agent | 需求與設計已於建立工單時完整釐清（AC 已包含端點/前端流程/IAM/CORS/測試/驗證項目），略過獨立 BA/SA 文件產出，直接進入開發，backlog → development |
| 2026-07-16T11:20:00 | dev-agent | 完成開發：新增 `/api/upload/presign`、`/api/upload/complete` 端點（`src/upload.py`、`src/models.py`、`src/config.py`），前端 `index.html` 改走 presigned URL 直傳流程，`infra/lambda.tf` 新增 `AUDIO_BUCKET_NAME` 環境變數；確認既有 IAM/CORS 已足夠，無需修改。新增 5 個單元測試，套件 44/44 pass，`terraform validate` 通過 |
| 2026-07-16T11:35:00 | review-agent | Code review 發現高風險問題：`/api/upload/complete` 未驗證 `s3_key` 是否確實屬於該 `job_id`，且 `job_id` 未做格式驗證即用於組出檔案路徑，理論上可被用來讀取/覆寫非預期路徑或存取他人 job 的音檔。已修正：`job_id` 需為合法 UUID、且 `s3_key` 必須等於伺服器依 `job_id` 重新計算出的既定命名，不符即回 400。新增 2 個回歸測試，套件 46/46 pass。development → review → development（修正後）→ testing |
