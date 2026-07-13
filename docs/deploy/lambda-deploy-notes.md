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

## API Gateway 整合注意事項

- 使用 **HTTP API**（非 REST API）搭配 Lambda Proxy 整合，`payloadFormatVersion` 建議設為 `2.0`
- CORS 設定可直接在 API Gateway 層設定，或維持目前 FastAPI `CORSMiddleware`（擇一，避免重複设定造成表頭衝突）
- 大型音檔上傳應改走 **S3 presigned URL** 直傳（詳見 PRD NFR-05），不應透過 API Gateway/Lambda 傳輸二進位音檔（payload 上限 10MB）
- Lambda 執行角色（IAM Role）需授權：
  - DynamoDB：`Meetings`、`LLMUsage` 表的 `GetItem`/`PutItem`/`Query`/`DeleteItem`/`Scan`
  - S3：音檔 bucket 的 `GetObject`/`PutObject`/`DeleteObject`（若採用 presigned URL 上傳）
  - Cognito：僅需公開 JWKS 端點驗證簽章，不需額外 IAM 權限（JWKS 透過 HTTPS 快取取得）

## 本機/CI 測試

- `tests/test_lambda_handler.py` 使用 `mangum` 直接以模擬的 API Gateway HTTP API v2 event 呼叫 `/api/health`，
  驗證 handler 可正確路由並回傳 200，不需真實部署到 AWS 即可驗證整合正確性。
