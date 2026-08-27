# TASK-013 交付報告 — AWS 資源建置（手動指南 + Terraform IaC）

## 完成內容

### 1. 手動建置指南
- `docs/deploy/manual-setup-guide.md`：完整條列 DynamoDB、S3（音檔 + 前端）、Cognito+Google、Lambda、
  API Gateway 的 Console/CLI 手動建置步驟，含 CORS/Lifecycle/IAM 設定細節

### 2. Terraform IaC（`infra/`）
| 檔案 | 內容 |
|------|------|
| `providers.tf` | AWS provider、archive provider 版本鎖定 |
| `variables.tf` | 所有可調參數（region、專案前綴、Google OAuth、LLM 各引擎金鑰、Lambda 規格等） |
| `dynamodb.tf` | `aimom-<env>-meetings`（含 TTL）、`aimom-<env>-llm-usage` 兩張表 |
| `s3.tf` | 音檔 bucket（CORS + 1天 lifecycle 自動清除）、前端網站 bucket（私有，透過 CloudFront 存取） |
| `cloudfront.tf` | CloudFront Distribution + OAC，讓前端 bucket 維持私有仍可對外提供 |
| `cognito.tf` | User Pool + Hosted UI Domain + Google Identity Provider + App Client（PKCE flow） |
| `iam.tf` | Lambda 執行角色，最小權限（DynamoDB 兩表 CRUD + S3 音檔 bucket 讀寫刪） |
| `lambda.tf` | `archive_file` 打包 `src/`（排除 venv/tests/tmp）、Lambda 函式、環境變數注入 |
| `apigateway.tf` | HTTP API + Lambda Proxy 整合（payload v2.0）+ `ANY /{proxy+}` 路由 |
| `outputs.tf` | API URL、Cognito 設定值、CloudFront 網址等輸出 |
| `terraform.tfvars.example` | 範例變數檔（機密欄位不含真實值） |
| `README.md` | 使用說明 |

## 驗證結果

- `terraform init`：成功下載 provider（aws ~5.100.0, archive ~2.8.0）
- `terraform validate`：**Success! The configuration is valid.**
- `terraform plan`（帶入測試用假變數值）：`archive_file` 資料源成功打包 `src/` 原始碼；
  執行到呼叫 AWS API 階段因本機沙箱環境無真實 AWS 憑證而中止（預期行為，非設定錯誤）
- 未執行 `terraform apply`，未在 AWS 建立任何真實資源，避免產生費用或誤動作

## 驗收對應

| AC | 狀態 |
|----|------|
| 手動建置指南 | ✅ |
| DynamoDB 兩張表（含 TTL） | ✅ |
| S3 音檔 bucket（lifecycle）+ 前端網站 bucket | ✅ |
| Cognito User Pool + Google IdP | ✅ |
| Lambda 函式 + IAM Role（最小權限） | ✅ |
| API Gateway HTTP API + Lambda 整合 | ✅ |
| `terraform validate`/`plan` 可執行 | ✅（plan 因無真實 AWS 憑證中止於 API 呼叫前，設定本身已驗證正確） |
| 變數化 | ✅ `variables.tf` + `terraform.tfvars.example` |

## 已知限制 / 後續事項

- 尚未實際 `terraform apply` 到真實 AWS 帳號（需使用者提供 AWS 憑證與 Google OAuth 憑證後執行）
- Lambda 打包目前直接壓縮原始碼，正式環境建議改用 Lambda Layer 管理相依套件（見 `infra/README.md`）
- 當時未包含 S3 presigned URL 上傳邏輯與 AssemblyAI 非同步整合；後續已由程式碼工單補上並同步部署
- 未設定自訂網域（Route53 + ACM 憑證），CloudFront 目前使用預設網域
