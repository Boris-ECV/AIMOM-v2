---
id: TASK-014
title: 前端 Cognito OAuth 登入整合與部署
type: Task
priority: High
assignee: unassigned
status: done
created: 2026-07-14
updated: 2026-07-16T10:35:00
epic: EPIC-003
---

## 描述

TASK-013 已完成 AWS 資源建置並實際部署（Cognito User Pool + Google IdP、Lambda、API Gateway、
DynamoDB、S3、CloudFront 皆已在 `ap-northeast-1` 建立完成）。但 `src/frontend/index.html`
目前完全沒有登入流程：API 網址寫死 `http://localhost:8000`，所有 API 呼叫都沒有帶
`Authorization` header，後端 `auth.py` 已實作的 Cognito JWT 驗證因此無法被前端觸發。

本工單要讓前端能真正走 Cognito Hosted UI 的 OAuth 2.0 Authorization Code + PKCE 流程登入，
取得 ID Token 後帶在所有 API 請求上，並完成部署到已建立的 `frontend` S3 bucket + CloudFront。

已部署的實際環境資訊（供實作與部署參考）：
- `api_invoke_url`: https://0e4wrwqj2g.execute-api.ap-northeast-1.amazonaws.com/
- `cognito_hosted_ui_domain`: aimom-dev-auth.auth.ap-northeast-1.amazoncognito.com
- `cognito_app_client_id`: 3c1p876tadpdrd71uu2d982ei
- `frontend_cloudfront_domain`: d11d8l4nxw1bow.cloudfront.net
- `frontend_bucket_name`: aimom-dev-frontend-402742377991
- region: ap-northeast-1

## Acceptance Criteria

- [x] 新增 `src/frontend/config.js`（不寫死在 index.html 內），定義 API base URL、Cognito
      Hosted UI domain、App Client ID、redirect URI、region，方便未來換環境時只改這一個檔案
- [x] 未登入時顯示登入畫面／按鈕，導向 Cognito Hosted UI（`/oauth2/authorize`），
      使用 Authorization Code + PKCE（`code_challenge_method=S256`），不使用 implicit flow
- [x] 登入完成導回後，於前端交換 authorization code 為 token（`/oauth2/token`），
      取得 ID Token 並安全保存（`sessionStorage`），不可外洩於 URL 或 console log
- [x] 所有既有 API 呼叫（`/api/me`, `/api/upload`, `/api/transcribe`, `/api/summarize`,
      `/api/status`, `/api/export`, `/api/admin/usage`, `/api/cleanup` 等）改為統一的
      `apiFetch()` 封裝，自動帶上 `Authorization: Bearer <id_token>`
- [x] 收到 401 回應時，清除本機 token 並導回登入畫面（不需自動 refresh token，屬已知限制，
      於備注中說明並記錄為後續優化項目）
- [x] 登出功能：呼叫 Cognito `/logout` endpoint 並清除本機 token
- [x] 新增 `docs/deploy/frontend-deploy.md`，
      說明如何將 `src/frontend/` 上傳至 `frontend_bucket_name` 並執行 CloudFront invalidation
- [x] 本地或 CloudShell 手動驗證：完整跑過登入 → 上傳錄音 → 產出會議紀錄 → 匯出 → 登出流程
      （已於 2026-07-16 由使用者在 CloudFront 網域上用 3MB 以下短音檔實際驗證通過）

## 備注

- 開發階段以「inline JS 括號/大括號計數平衡檢查」取代自動化測試（前端無既有測試框架，
  且此開發環境無法安裝需要系統管理員權限的 node/npm）。
- **手動驗證尚未執行**：需要使用者將 `src/frontend/` 上傳到 S3
  (`aimom-dev-frontend-402742377991`) 並建立 CloudFront invalidation 後，於瀏覽器開啟
  `https://d11d8l4nxw1bow.cloudfront.net` 實際測試登入/上傳/匯出/登出全流程，
  詳見 `docs/deploy/frontend-deploy.md`。
- ID Token 過期後不會自動 refresh，使用者需重新登入；已知限制，非本工單範圍。
- **測試中發現並修正的重大問題**：實際部署後 CORS 預檢請求（OPTIONS）與所有 API 呼叫
  皆回傳 500。追查後發現 `infra/lambda.tf` 先前只打包 `src/` 原始碼，完全沒有包含
  `fastapi`/`mangum` 等相依套件，Lambda 執行時直接 `ImportModuleError`。改用獨立的
  **Lambda Layer**（`infra/layer/`，由 `scripts/build_lambda_layer.ps1`/`.sh` 建置，
  對應 `src/requirements-lambda.txt`）解決，`infra/lambda.tf` 新增
  `aws_lambda_layer_version.deps` 並掛載至 function，已重新 `terraform apply` 生效，
  `curl /api/health` 已驗證回傳 200。
- **手動驗證中發現第二個 bug（已修正）**：Layer 問題解決後，登入流程本身可正常走完
  Cognito Hosted UI + PKCE 換到 ID Token，但所有帶 Authorization header 的 API
  （如 `/api/me`）仍一律回傳 401。用瀏覽器 Network 分頁攔截實際 token 內容，
  逐項核對 `aud`/`iss`/`exp`/JWKS `kid` 皆正確，判斷問題在後端驗證邏輯本身：
  真實 Cognito ID Token（透過 authorization_code flow 換發）一定帶有 `at_hash`
  claim，但 `src/auth.py` 的 `verify_token()` 呼叫 `jwt.decode()` 時沒有傳入
  `access_token` 可供比對，`python-jose` 因此對每個合法 token 都拋出
  `JWTClaimsError: No access_token provided to compare against at_hash claim.`，
  被 `except Exception` 吃掉轉成籠統的 401。修正：在 `jwt.decode()` 的 `options`
  加上 `"verify_at_hash": False`（前端只帶 ID Token，本來就不需要驗 at_hash）。
  已於 `src/tests/test_auth.py` 補上
  `test_verify_token_with_at_hash_claim_accepted` 回歸測試，套件測試 40/40 pass。
  此 bug 未被先前 review/QA 的既有測試發現，因為假 token fixture 沒有帶 `at_hash`
  claim，只有真實 Cognito 核發的 token 才會踩到，屬於既有測試覆蓋不足，已補強。
- ✅ **QA PASS - 2026-07-16**：使用者以 3MB 以下短音檔在
  `https://d11d8l4nxw1bow.cloudfront.net` 實際完整跑過「Google 登入 → 上傳錄音 →
  轉錄 → 摘要 → 匯出 → 登出」全流程，皆成功。
- ⚠️ **驗證過程中另發現一個超出本工單範圍的架構限制（已另開 TASK-015 追蹤）**：
  上傳 7.91MB 音檔時 `/api/upload` 回傳 `413 Content Too Large`。原因是目前上傳
  流程把整份音檔內容當作 HTTP request body 直接送進 API Gateway → Lambda，撞到
  AWS 平台硬性限制（API Gateway payload 上限 10MB；Lambda 同步呼叫 payload 上限
  6MB；且 API Gateway 對二進位 body 會先 base64 編碼再轉給 Lambda，多出約 33%
  大小，實際可上傳的音檔上限遠低於使用情境需求）。這是 TASK-012（Lambda 部署）
  遺留的設計缺口，與本工單（前端登入整合）無關，不影響本工單驗收，另建
  TASK-015 處理（建議改用 S3 Presigned URL 直傳）。

## 歷程

| 時間 | 代理 | 動作 |
|------|------|------|
| 2026-07-14T18:30:00 | orchestrator | 依使用者需求建立工單，放入 backlog（TASK-013 部署後發現前端登入整合缺口） |
| 2026-07-14T18:42:00 | dev-agent | 完成 config.js 外部化設定、Cognito PKCE 登入流程、apiFetch 封裝與 8 處呼叫套用、登出功能、frontend-deploy.md，移至 testing 等待使用者實際部署驗證 |
| 2026-07-15 | orchestrator | 使用者於 CloudShell terraform apply Lambda Layer 修正後，手動驗證登入流程時發現 `/api/me` 等所有 API 呼叫皆回傳 401；追查為 `src/auth.py` 的 `verify_token()` 未處理 ID Token 的 `at_hash` claim 導致 python-jose 誤判驗證失敗，修正 `jwt.decode()` options 並補上回歸測試，套件測試 40/40 pass |
| 2026-07-15 | orchestrator | CloudShell 1GB 磁碟配額不足以同時容納 aws provider（~675MB）與 archive_file 動態壓縮 layer 所需的暫存空間；改為本機預先建置 `infra/build/aimom-lambda-layer.zip`，`infra/lambda.tf` 改用 `filebase64sha256` 直接讀取該 zip，不再用 `archive_file` 對 `infra/layer/` 動態壓縮 |
| 2026-07-16 | qa-agent | 使用者以 3MB 以下短音檔完整驗證登入→上傳→轉錄→摘要→匯出→登出全流程成功，✅ QA PASS，移動 board/testing/ → board/done/；驗證過程中另發現大檔案（7.91MB）上傳觸發 413（API Gateway/Lambda payload 上限），與本工單無關，另建 TASK-015 追蹤 |
