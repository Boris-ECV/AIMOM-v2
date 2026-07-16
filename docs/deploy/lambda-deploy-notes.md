# Lambda 部署設定筆記（TASK-012）

## 部署方式概要

- 執行環境：AWS Lambda（Python 3.12 runtime）
- 進入點：`src/lambda_handler.handler`（`Mangum(app)`）
- API：Amazon API Gateway **HTTP API**（比 REST API 便宜、延遲較低，符合小團隊低成本考量）
- 打包：建議使用 Lambda **容器映像**或 **Lambda Layer** 封裝 `reportlab`/`python-docx`/`boto3` 等相依套件（避免單一 zip 超過 250MB 解壓限制）

## Lambda 設定建議值

| 項目 | 建議值 | 說明 |
|------|--------|------|
| Memory | 512–1024 MB | reportlab/docx 產生檔案、JWT 驗證需要一定運算資源；可依實際冷啟動/執行時間調整 |
| Timeout | 30 秒 | 一般 API 請求；若日後仍需同步等待轉譯完成的端點，需另外評估（目前設計已改用 AssemblyAI webhook，避免長時間等待） |
| 並行數（Reserved concurrency） | 依團隊規模設定，如 10 | 小團隊使用，避免意外高流量產生費用 |
| 環境變數 | 見下方清單 | 一律透過 Lambda 環境變數或 Secrets Manager 注入，不寫死於程式碼 |

## 必要環境變數清單

| 變數 | 說明 |
|------|------|
| `LLM_ENGINE` | `github-models` / `openai-gpt4o` / `groq` / `gemini` |
| `LLM_MODEL` | 覆寫預設模型（可留空） |
| `GITHUB_TOKEN` / `OPENAI_API_KEY` / `GROQ_API_KEY` / `GEMINI_API_KEY` | 依 `LLM_ENGINE` 擇一設定 |
| `ASSEMBLYAI_API_KEY` | 轉譯服務金鑰 |
| `COGNITO_REGION` | Cognito User Pool 所在 region |
| `COGNITO_USER_POOL_ID` | Cognito User Pool ID |
| `COGNITO_APP_CLIENT_ID` | Cognito App Client ID（JWT audience 驗證用） |
| `ADMIN_EMAILS` | 管理者 email 白名單，逗號分隔 |
| `DYNAMODB_MEETINGS_TABLE` | 預設 `aimom-meetings` |
| `DYNAMODB_LLM_USAGE_TABLE` | 預設 `aimom-llm-usage` |
| `MEETING_RETENTION_DAYS` | 預設 `14` |
| `TMP_DIR` | Lambda 上應設為 `/tmp`（唯一可寫入目錄，且有 512MB–10GB 限制） |
| `AUDIO_BUCKET_NAME` | 音檔暫存 S3 bucket 名稱，由 `infra/lambda.tf` 自動帶入 `aws_s3_bucket.audio.bucket`（TASK-015 presigned URL 直傳用） |

## API Gateway 整合注意事項

- 使用 **HTTP API**（非 REST API）搭配 Lambda Proxy 整合，`payloadFormatVersion` 建議設為 `2.0`
- CORS 設定可直接在 API Gateway 層設定，或維持目前 FastAPI `CORSMiddleware`（擇一，避免重複设定造成表頭衝突）
- 音檔上傳採 **S3 presigned URL** 直傳（TASK-015，詳見 PRD NFR-05）：前端呼叫
  `POST /api/upload/presign` 取得簽名 URL 後直接 PUT 到 S3，再呼叫
  `POST /api/upload/complete` 觸發後端下載/驗證，不透過 API Gateway/Lambda 傳輸
  二進位音檔本體（該路徑仍受 payload 上限 10MB / Lambda 同步呼叫 6MB 限制）。
  舊版 `POST /api/upload`（multipart 直傳）仍保留供本機開發/小檔案測試使用
- Lambda 執行角色（IAM Role）需授權：
  - DynamoDB：`Meetings`、`LLMUsage` 表的 `GetItem`/`PutItem`/`Query`/`DeleteItem`/`Scan`
  - S3：音檔 bucket 的 `GetObject`/`PutObject`/`DeleteObject`（若採用 presigned URL 上傳）
  - Cognito：僅需公開 JWKS 端點驗證簽章，不需額外 IAM 權限（JWKS 透過 HTTPS 快取取得）

## Lambda 相依套件打包（TASK-014 修正）

**重要修正**：先前版本的 Lambda 只打包 `src/` 原始碼本身，完全沒有包含
`fastapi`/`mangum`/`boto3` 等第三方套件，導致部署後每次呼叫（包含 CORS 的
OPTIONS 預檢請求）都會因為 `ImportModuleError` 回傳 500。

現在改用 **Lambda Layer** 管理相依套件（`infra/lambda.tf` 的
`aws_lambda_layer_version.deps`），與應用程式碼（`data.archive_file.lambda_package`）
分開打包：

```powershell
# Windows（會優先使用 src/venv 內的 Python）
powershell -File scripts/build_lambda_layer.ps1
```
```bash
# CloudShell / Linux / macOS
bash scripts/build_lambda_layer.sh
```

會產生 `infra/layer/python/`（不進版控，屬建置產物）與 `infra/build/aimom-lambda-layer.zip`，
內容依 `src/requirements-lambda.txt`（正式環境實際需要的套件，排除 `uvicorn`
本機開發用 server、`pytest`/`moto`/`httpx` 測試用套件、`boto3`——後者由
Lambda Python runtime 內建提供不需重複打包）安裝，並指定
`--platform manylinux2014_x86_64 --python-version 3.12` 確保跟 Lambda
runtime 相容（即使建置環境不是 Linux/3.12 也能正確下載對應的 wheel）。

`infra/lambda.tf` 的 `aws_lambda_layer_version.deps` 直接讀取建置好的
`infra/build/aimom-lambda-layer.zip`（用 `filebase64sha256` 算 hash），
**不再**用 `archive_file` 動態壓縮 `infra/layer/`。這是因為在磁碟空間有限的
環境（例如 AWS CloudShell 僅 1GB 家目錄配額，`aws` provider 本身解壓縮就要
600MB+），同時存放未壓縮原始檔（~80MB）與 `archive_file` 另外產生的 zip
會直接把空間塞爆。改為在本機（或 CI）先跑建置腳本產生好 zip，只上傳這個
zip 檔到部署環境即可，`infra/layer/python/` 原始目錄不需要一併上傳。



- `tests/test_lambda_handler.py` 使用 `mangum` 直接以模擬的 API Gateway HTTP API v2 event 呼叫 `/api/health`，
  驗證 handler 可正確路由並回傳 200，不需真實部署到 AWS 即可驗證整合正確性。
