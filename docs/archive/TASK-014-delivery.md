# TASK-014 交付報告

**交付時間：** 2026-07-16T10:35:00
**功能：** 前端 Cognito OAuth 登入整合與部署

## 完成功能摘要

- 新增 `src/frontend/config.js`，將 API base URL、Cognito Hosted UI domain、
  App Client ID、redirect/logout URI、region 從程式碼中抽出，換環境只需改這一個檔案
- 前端導入 Cognito Hosted UI 的 OAuth 2.0 Authorization Code + PKCE 登入流程
  （`code_challenge_method=S256`，不使用 implicit flow）
- 登入完成後於前端交換 authorization code 為 ID Token，安全保存於 `sessionStorage`
- 統一的 `apiFetch()` 封裝，自動帶上 `Authorization: Bearer <id_token>`，套用至全部
  8 處既有 API 呼叫；收到 401 時清除本機 token 並導回登入畫面
- 登出功能：呼叫 Cognito `/logout` 並清空本機 token
- 新增 `docs/deploy/frontend-deploy.md` 說明部署步驟

## 版本資訊

- 相關程式碼：`src/frontend/index.html`、`src/frontend/config.js`、`src/auth.py`
- 修改檔案：見 git commit 歷程（`cc2ec9b`、`73e33ea`、`0ae7059`、`0b8453c`）

## 部署過程中發現並修正的問題（非原始 AC，但屬完整交付必要修正）

1. **Lambda 500（相依套件未打包）**：`infra/lambda.tf` 原本只打包 `src/` 原始碼，
   缺少 `fastapi`/`mangum` 等相依套件。改用獨立 Lambda Layer
   （`aws_lambda_layer_version.deps`）解決，已 `terraform apply` 生效，
   `curl /api/health` 驗證回傳 200。
2. **CloudShell 磁碟空間不足**：CloudShell 家目錄僅 1GB 配額，`aws` provider
   解壓縮即佔 675MB+，無法同時容納 Lambda Layer 原始檔（~80MB）與
   `archive_file` 動態產生的 zip。改為本機預先建置
   `infra/build/aimom-lambda-layer.zip`，`infra/lambda.tf` 改用
   `filebase64sha256` 直接讀取該 zip，只需上傳壓縮檔（~28MB）即可。
3. **所有登入後 API 呼叫回傳 401**：`src/auth.py` 的 `verify_token()` 未處理
   真實 Cognito ID Token 必帶的 `at_hash` claim，`python-jose` 因缺少
   `access_token` 可比對而對每個合法 token 拋出 `JWTClaimsError`，被籠統轉成
   401。修正：`jwt.decode()` 加上 `options={"verify_at_hash": False}`。
   新增回歸測試 `test_verify_token_with_at_hash_claim_accepted`，
   套件測試 40/40 pass。此問題未被既有測試發現的原因：假 token fixture
   沒有帶 `at_hash` claim，只有真實 Cognito 核發的 token 才會踩到。

## 模擬/實際部署步驟

1. ✅ 程式碼修正（auth.py、lambda.tf、build 腳本）
2. ✅ 單元測試執行（`pytest tests/` 40/40 pass）
3. ✅ `terraform apply` 建立 Lambda Layer v2 並更新 Lambda function
4. ✅ 前端 `src/frontend/` 同步到 `aimom-dev-frontend-402742377991` S3 bucket
5. ✅ CloudFront invalidation 執行完成
6. ✅ 實際瀏覽器手動驗證：登入 → 上傳 → 轉錄 → 摘要 → 匯出 → 登出，全部通過

## QA 結果

✅ 所有 Acceptance Criteria 通過（含手動驗證項目，2026-07-16 使用者於
`https://d11d8l4nxw1bow.cloudfront.net` 實際測試完成）。

## 已知限制 / 後續追蹤

- ID Token 過期（1 小時）後不會自動 refresh，需重新登入，已知限制、非本工單範圍。
- **大檔案（約 5MB 以上）上傳會回傳 413**：API Gateway/Lambda payload 硬性限制
  （10MB/6MB），與二進位 body 的 base64 編碼開銷有關，屬 TASK-012 遺留的架構缺口，
  已另建 **TASK-015**（改用 S3 Presigned URL 直傳）追蹤，不影響本工單驗收。
