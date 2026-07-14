# AIMOM 基礎設施（Terraform）

本目錄使用 Terraform 建置 AIMOM v2 所需的 AWS 資源：DynamoDB、S3（音檔暫存 + 前端網站）、
CloudFront、Cognito User Pool（Google 聯合登入）、Lambda、API Gateway HTTP API。

對應手動建置步驟請參考：`../docs/deploy/manual-setup-guide.md`
Lambda 環境變數/設定值說明請參考：`../docs/deploy/lambda-deploy-notes.md`
無 AWS access key（僅 Console 帳密登入）情境請參考：`../docs/deploy/cloudshell-deploy.md`

## 前置需求

- Terraform >= 1.5.0
- 已設定好 AWS 憑證（`aws configure` 或環境變數 `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`，或 CloudShell）
- 已在 Google Cloud Console 建立 OAuth 2.0 Client（取得 Client ID/Secret，用於 Cognito 聯合登入）

## Remote State（S3 backend）— 只需執行一次

主要 `infra/` 設定使用 S3 儲存 Terraform state（而非只留在本機/單一 CloudShell session），
但 state bucket 本身無法由使用它的同一份設定建立（雞生蛋問題），因此拆成 `infra/bootstrap/` 先建置：

```powershell
cd infra/bootstrap
terraform init
terraform apply
terraform output state_bucket_name   # 記下這個值
```

`infra/bootstrap` 使用**本機 state**（不能用還沒建立出來的 bucket 當自己的 backend），
執行過一次後，`bootstrap/terraform.tfstate` 請自行備份保管好（例如放入你的密碼管理工具或私有加密儲存），
之後很少需要再變動這個模組。

## 使用方式（主要 infra/）

```powershell
cd infra
cp backend.hcl.example backend.hcl
# 編輯 backend.hcl，填入上一步 bootstrap 的 state_bucket_name

cp terraform.tfvars.example terraform.tfvars
# 編輯 terraform.tfvars，填入實際的 Google OAuth 憑證、API keys、管理者 email 等

terraform init -backend-config=backend.hcl
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
（`infra/bootstrap` 的 state bucket 設有 `prevent_destroy`，需要手動移除該保護才能刪除，避免不小心刪掉 state）

## 注意事項

- `terraform.tfvars`、`backend.hcl` 含機密/環境資訊，已列於 `.gitignore`，**不可提交到版控**
- State locking 使用 Terraform 1.10+ 原生的 S3 lockfile 機制（`use_lockfile = true`），不需要額外的 DynamoDB lock table
- Lambda 打包目前直接壓縮 `src/` 原始碼；正式環境建議將相依套件（`boto3`/`reportlab`/`python-docx` 等）改用 **Lambda Layer** 管理，避免打包過大或每次重複安裝
- 音檔 bucket 設定 1 天 lifecycle 自動清除，符合「音檔處理完即刪除」的設計
- DynamoDB 皆採 on-demand 計費模式，符合小團隊低流量、低成本的需求
