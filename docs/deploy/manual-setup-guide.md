# AWS 手動建置指南（TASK-013）

本文件提供不使用 IaC 時，透過 AWS Console／CLI 手動建置 AIMOM 所需資源的完整步驟。
正式環境建議改用 `infra/`（Terraform），本文件同時可作為 Terraform 邏輯的對照參考。

以下假設 region 為 `ap-northeast-1`（東京），專案前綴為 `aimom`，請依實際需求調整。

---

## 1. DynamoDB — Meetings 表

**Console：** DynamoDB → Tables → Create table

| 設定項 | 值 |
|--------|-----|
| Table name | `aimom-meetings` |
| Partition key | `user_id` (String) |
| Sort key | `meeting_id` (String) |
| Table settings | Customize（On-demand capacity，符合小團隊低成本用量） |

建立完成後：
1. 進入該表 → **Additional settings** → **Time to Live (TTL)**
2. 啟用 TTL，Attribute name 填 `expires_at`

**CLI 等效指令：**
```powershell
aws dynamodb create-table `
  --table-name aimom-meetings `
  --attribute-definitions AttributeName=user_id,AttributeType=S AttributeName=meeting_id,AttributeType=S `
  --key-schema AttributeName=user_id,KeyType=HASH AttributeName=meeting_id,KeyType=RANGE `
  --billing-mode PAY_PER_REQUEST `
  --region ap-northeast-1

aws dynamodb update-time-to-live `
  --table-name aimom-meetings `
  --time-to-live-specification "Enabled=true, AttributeName=expires_at" `
  --region ap-northeast-1
```

## 2. DynamoDB — LLMUsage 表

| 設定項 | 值 |
|--------|-----|
| Table name | `aimom-llm-usage` |
| Partition key | `date` (String) |
| Sort key | `usage_id` (String) |
| Billing | On-demand |

```powershell
aws dynamodb create-table `
  --table-name aimom-llm-usage `
  --attribute-definitions AttributeName=date,AttributeType=S AttributeName=usage_id,AttributeType=S `
  --key-schema AttributeName=date,KeyType=HASH AttributeName=usage_id,KeyType=RANGE `
  --billing-mode PAY_PER_REQUEST `
  --region ap-northeast-1
```

## 3. S3 — 音檔暫存 Bucket

**Console：** S3 → Create bucket

| 設定項 | 值 |
|--------|-----|
| Bucket name | `aimom-audio-<你的帳號代號>`（bucket 名稱全域唯一，需自行加後綴） |
| Block Public Access | 全部勾選（維持私有，透過 presigned URL 存取） |
| Versioning | 停用（音檔為暫存性質，不需版本） |

建立後設定 **Lifecycle rule**（自動清除）：
1. Bucket → Management → Create lifecycle rule
2. Scope：整個 bucket
3. Actions：Expire current versions of objects → **1 天**後刪除（音檔處理完即應刪除，1 天是保守緩衝）

CORS 設定（供前端 presigned PUT 上傳）：
```json
[
  {
    "AllowedHeaders": ["*"],
    "AllowedMethods": ["PUT", "GET"],
    "AllowedOrigins": ["*"],
    "ExposeHeaders": ["ETag"]
  }
]
```

## 4. S3 — 前端靜態網站 Bucket

| 設定項 | 值 |
|--------|-----|
| Bucket name | `aimom-frontend-<你的帳號代號>` |
| Static website hosting | 啟用，Index document: `index.html` |
| Block Public Access | 建議搭配 CloudFront + OAC（Origin Access Control），bucket 本身仍設為私有 |

之後建立 **CloudFront Distribution**，Origin 指向此 bucket（使用 OAC，不直接公開 bucket）。

## 5. Cognito User Pool + Google 登入

**Console：** Cognito → User pools → Create user pool

1. **Sign-in options**：勾選 Email（供非 Google 帳號備援，或可只用聯合登入）
2. **Configure Federated Identity Providers**：
   - 新增 Google 作為身分提供者
   - 需先在 [Google Cloud Console](https://console.cloud.google.com/) 建立 OAuth 2.0 Client ID，取得 Client ID / Client Secret
   - Authorized redirect URI 填入 Cognito 提供的網域：`https://<your-domain>.auth.ap-northeast-1.amazoncognito.com/oauth2/idpresponse`
3. **App integration** → 建立 **App client**：
   - 不需要 client secret（前端 SPA 使用 PKCE flow）
   - Allowed callback URLs：前端網址（CloudFront domain）
   - OAuth flows：Authorization code grant
   - OAuth scopes：`openid email profile`
4. 建立完成後記錄：
   - User Pool ID（`COGNITO_USER_POOL_ID`）
   - App Client ID（`COGNITO_APP_CLIENT_ID`）
   - Region（`COGNITO_REGION`）

## 6. Lambda 函式

1. **打包**：在 `src/` 目錄安裝相依套件並打包成 zip（或建置容器映像，若套件含原生二進位建議用容器映像）
   ```powershell
   cd src
   pip install -r requirements.txt -t package/
   Copy-Item *.py package/
   Compress-Archive -Path package/* -DestinationPath aimom-lambda.zip
   ```
2. **Console：** Lambda → Create function → Author from scratch
   - Runtime：Python 3.12
   - Handler：`lambda_handler.handler`
   - Memory：512–1024 MB（參考 `docs/deploy/lambda-deploy-notes.md`）
   - Timeout：30 秒
3. 上傳 `aimom-lambda.zip`
4. **環境變數**：依 `docs/deploy/lambda-deploy-notes.md` 的清單逐一填入
5. **執行角色（IAM Role）**：附加以下權限（最小權限原則）：
   - DynamoDB：對 `aimom-meetings`、`aimom-llm-usage` 的 `GetItem`/`PutItem`/`Query`/`DeleteItem`/`Scan`/`UpdateTimeToLive`
   - S3：對音檔 bucket 的 `GetObject`/`PutObject`/`DeleteObject`

## 7. API Gateway HTTP API

1. **Console：** API Gateway → Create API → HTTP API
2. Integration：Lambda，選擇上述建立的函式，Payload format version 選 `2.0`
3. Routes：新增 `ANY /{proxy+}`（讓 FastAPI 內部路由處理所有路徑）
4. CORS：在 API Gateway 層設定，或維持 FastAPI 內建 `CORSMiddleware`（**擇一**，避免重複表頭）
5. Deploy → 記錄 Invoke URL，作為前端 `API` base URL

## 8. 驗證

1. 呼叫 `GET <Invoke URL>/api/health` 應回傳 `{"status": "ok"}`
2. 用瀏覽器開啟前端網址，測試 Google 登入 → 上傳音檔 → 轉譯 → 摘要 → 保留/匯出 全流程
