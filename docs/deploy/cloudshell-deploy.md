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

### 4. 執行 Terraform
```bash
terraform init
terraform plan
terraform apply
```
輸入 `yes` 確認後開始建立資源。完成後：
```bash
terraform output
```
記錄 `api_invoke_url`、`cognito_hosted_ui_domain`、`frontend_cloudfront_domain` 等輸出值。

### 5. 回頭補上 Google OAuth Redirect URI
1. 用 `terraform output cognito_hosted_ui_domain` 取得實際網域
2. 回 Google Cloud Console → Credentials → 編輯 OAuth Client
3. Authorized redirect URIs 補上：`https://<實際網域>/oauth2/idpresponse`

### 6. 清理（重要）
CloudShell 的家目錄有 1GB 持久化儲存空間，操作完成後：
```bash
rm -f ~/infra-package.zip
```
避免機密的 `terraform.tfvars` 長期留在 CloudShell 儲存空間中。
`terraform.tfstate` 也會留在 CloudShell 裡（含資源 ID 等資訊，非機密但建議之後改用 S3 backend 集中管理狀態檔，見下方備註）。

## 備註：state 檔案管理

目前 `infra/` 未設定 remote backend，`terraform.tfstate` 只會留在執行 `apply` 的那個環境（此例為 CloudShell 家目錄）。
若之後需要多人協作或重新從別的環境 `apply`／`destroy`，建議加上 S3 backend（見 `providers.tf` 可擴充 `backend "s3" {}` 區塊）。
小團隊 POC 階段可先接受單一 CloudShell session 管理 state 的作法，但**切勿刪除 CloudShell 家目錄裡的 `terraform.tfstate`**，
否則 Terraform 會失去對已建立資源的追蹤紀錄。
