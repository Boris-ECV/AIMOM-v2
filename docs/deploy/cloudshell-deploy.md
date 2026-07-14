# 使用 AWS CloudShell 部署（無 access key 情境）

適用情境：IAM 使用者透過帳密登入 AWS Console，但政策不允許建立 access key/secret。
AWS CloudShell 直接沿用你目前 Console 登入 session 的臨時憑證，完全不需要 access key。

## 步驟

### 1. 開啟 CloudShell
1. 登入 AWS Console（帳密登入）
2. 畫面右上角工具列，點擊 CloudShell 圖示（終端機圖案），或直接搜尋 "CloudShell"
3. 等待環境初始化（約 30–60 秒）

### 2. 安裝 Terraform
CloudShell 是 Amazon Linux 2，預設沒有 Terraform，執行：
```bash
sudo yum install -y yum-utils shadow-utils
sudo yum-config-manager --add-repo https://rpm.releases.hashicorp.com/AmazonLinux/hashicorp.repo
sudo yum -y install terraform
terraform -version
```

### 3. 上傳 infra 程式碼
1. CloudShell 右上角 **Actions** → **Upload file**
2. 選擇本機的 `infra-package.zip`（已包含 `terraform.tfvars`，內有你的 Google OAuth 憑證等機密資訊）
3. 上傳完成後在 CloudShell 執行：
   ```bash
   mkdir -p ~/aimom-infra
   unzip infra-package.zip -d ~/aimom-infra
   cd ~/aimom-infra
   ls
   ```

### 4. 先建立 remote state bucket（bootstrap，僅需執行一次）
```bash
cd bootstrap
terraform init
terraform apply
terraform output state_bucket_name   # 記下這個值，下一步要用
cd ..
```

### 5. 設定 backend 並執行主要 Terraform
```bash
cp backend.hcl.example backend.hcl
nano backend.hcl   # 把 bucket 改成上一步的 state_bucket_name

terraform init -backend-config=backend.hcl
terraform plan
terraform apply
```
輸入 `yes` 確認後開始建立資源。完成後：
```bash
terraform output
```
記錄 `api_invoke_url`、`cognito_hosted_ui_domain`、`frontend_cloudfront_domain` 等輸出值。

### 6. 回頭補上 Google OAuth Redirect URI
1. 用 `terraform output cognito_hosted_ui_domain` 取得實際網域
2. 回 Google Cloud Console → Credentials → 編輯 OAuth Client
3. Authorized redirect URIs 補上：`https://<實際網域>/oauth2/idpresponse`

### 7. 清理（重要）
CloudShell 的家目錄有 1GB 持久化儲存空間，操作完成後：
```bash
rm -f ~/infra-package.zip
```
避免機密的 `terraform.tfvars` 長期留在 CloudShell 儲存空間中。
由於已改用 **S3 remote backend**，`terraform.tfstate` 實際存放在 S3（有版本控制、加密），
CloudShell 本機只留一份工作副本（`.terraform/` 快取），不是唯一副本，可放心之後在其他環境
用同一組 `backend.hcl` 重新 `terraform init` 接續操作，不會遺失狀態。

## 備註：state 檔案管理

`infra/` 已設定 **S3 remote backend**（見 `infra/bootstrap/` 與 `backend.hcl`），
`terraform.tfstate` 集中存放在 S3，具備版本控制與加密，可從任何已設定好 `backend.hcl` 的環境
（本機、CloudShell、CI/CD）接續 `terraform plan`/`apply`，不再綁定單一 session。
State locking 使用 Terraform 1.10+ 原生的 S3 lockfile 機制，避免多人同時 apply 造成衝突。
若之後需要多人協作或重新從別的環境 `apply`／`destroy`，建議加上 S3 backend（見 `providers.tf` 可擴充 `backend "s3" {}` 區塊）。
小團隊 POC 階段可先接受單一 CloudShell session 管理 state 的作法，但**切勿刪除 CloudShell 家目錄裡的 `terraform.tfstate`**，
否則 Terraform 會失去對已建立資源的追蹤紀錄。
