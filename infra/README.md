# AIMOM 基礎設施（Terraform）

本目錄使用 Terraform 建置 AIMOM v2 所需的 AWS 資源：DynamoDB、S3（音檔暫存 + 前端網站）、
CloudFront、Cognito User Pool（Google 聯合登入）、Lambda、API Gateway HTTP API。

對應手動建置步驟請參考：`../docs/deploy/manual-setup-guide.md`
Lambda 環境變數/設定值說明請參考：`../docs/deploy/lambda-deploy-notes.md`

## 前置需求

- Terraform >= 1.5.0
- 已設定好 AWS 憑證（`aws configure` 或環境變數 `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`）
- 已在 Google Cloud Console 建立 OAuth 2.0 Client（取得 Client ID/Secret，用於 Cognito 聯合登入）

## 使用方式

```powershell
cd infra
cp terraform.tfvars.example terraform.tfvars
# 編輯 terraform.tfvars，填入實際的 Google OAuth 憑證、API keys、管理者 email 等

terraform init
terraform plan
terraform apply
```

套用完成後，`terraform output` 會列出：
- `api_invoke_url`：前端 API base URL
- `cognito_user_pool_id` / `cognito_app_client_id` / `cognito_hosted_ui_domain`：登入設定
- `frontend_cloudfront_domain`：前端網址
- `audio_bucket_name`：音檔暫存 bucket

## 銷毀資源（避免產生費用）

```powershell
terraform destroy
```

## 注意事項

- `terraform.tfvars` 含機密資訊（Google Client Secret、API Keys），已列於 `.gitignore`，**不可提交到版控**
- Lambda 打包目前直接壓縮 `src/` 原始碼；正式環境建議將相依套件（`boto3`/`reportlab`/`python-docx` 等）改用 **Lambda Layer** 管理，避免打包過大或每次重複安裝
- 音檔 bucket 設定 1 天 lifecycle 自動清除，符合「音檔處理完即刪除」的設計
- DynamoDB 皆採 on-demand 計費模式，符合小團隊低流量、低成本的需求
