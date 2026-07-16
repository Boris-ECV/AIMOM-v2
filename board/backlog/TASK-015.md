---
id: TASK-015
title: 音檔上傳改用 S3 Presigned URL 直傳，解決大檔案 413 限制
type: Bug
priority: High
assignee: unassigned
status: backlog
created: 2026-07-16
updated: 2026-07-16T10:35:00
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

- [ ] 後端新增簽發 S3 Presigned PUT URL 的端點（例如 `POST /api/upload/presign`），
      回傳一個限時有效的 URL，讓瀏覽器直接 PUT 音檔到 `audio_bucket_name`
      （`aimom-dev-audio-402742377991`），完全繞過 API Gateway/Lambda 的 payload 限制
- [ ] 前端 `index.html` 上傳流程改為：先呼叫 presign 端點 → 瀏覽器直接
      `fetch(presignedUrl, { method: 'PUT', body: file })` 上傳到 S3 → 上傳完成後
      再呼叫既有的 `/api/transcribe` 之類端點（帶 S3 object key），觸發後續轉錄流程
      （後續轉錄/摘要邏輯不需要大改，只是音檔來源從「Lambda 收到的 bytes」改成
      「S3 上已存在的物件」）
- [ ] `src/transcribe.py`（或對應模組）需要能接受「S3 object key」作為輸入，從
      S3 下載音檔到 `/tmp` 後再送給 AssemblyAI（或改成直接讓 AssemblyAI 讀 S3
      URL，視既有轉錄實作方式決定）
- [ ] IAM 角色（`infra/iam.tf` 的 `lambda_exec`）需要新增產生 presigned URL 所需的
      權限（`s3:PutObject` 已存在，需確認簽發 presigned URL 本身用的是呼叫端憑證
      即可，不需額外 IAM action，但要確認 bucket CORS 設定允許瀏覽器直接 PUT）
- [ ] `infra/s3.tf` 的 audio bucket 需要新增/確認 CORS 設定，允許前端網域
      （`frontend_cloudfront_domain`）直接對 bucket 發送 PUT 請求
- [ ] 更新單元測試涵蓋 presign 端點邏輯（mock S3 generate_presigned_url）
- [ ] 手動驗證：上傳一個 20MB+ 的真實錄音檔案，確認完整跑完
      上傳 → 轉錄 → 摘要 → 匯出流程

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
