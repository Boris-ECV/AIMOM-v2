# Google OAuth Client 設定指南（供 Cognito 聯合登入使用）

本文件說明如何在 Google Cloud Console 建立 OAuth 2.0 Client，取得 `google_client_id` /
`google_client_secret`，供 `infra/terraform.tfvars` 的 Cognito Google Identity Provider 設定使用。

---

## 前置準備

你需要有一個 Google 帳號可以存取 [Google Cloud Console](https://console.cloud.google.com/)。
若你的 Google 帳號屬於某個 Google Workspace 組織，且該組織限制建立專案，需請管理者協助或改用個人 Gmail 帳號。

---

## 步驟 1：建立（或選擇）一個 GCP 專案

1. 開啟 https://console.cloud.google.com/
2. 左上角專案選單 → **新增專案**
3. 專案名稱建議：`aimom` 或 `aimom-auth`
4. 建立完成後，確認畫面上方已切換到該專案

---

## 步驟 2：設定 OAuth 同意畫面（OAuth consent screen）

1. 左側選單 → **APIs & Services** → **OAuth consent screen**
2. User Type 選擇：
   - **External**（一般情況，允許任何 Google 帳號登入 — AIMOM 用這個）
   - Internal 僅限 Google Workspace 組織內部帳號使用（若你的團隊都在同一個 Workspace 網域可考慮，但要注意這需要組織帳號）
3. 填寫必要欄位：
   - App name：`AIMOM 會議紀錄系統`
   - User support email：你的 email
   - Developer contact information：你的 email
4. **Scopes** 頁面：可先略過（預設 `openid`/`email`/`profile` 已足夠，Cognito 側會另外指定）
5. **Test users**（若 Publishing status 停留在 Testing 階段）：
   - 加入所有需要登入 AIMOM 的使用者 email（未發布到 Production 前，只有加入的 test user 才能登入）
   - 若之後想開放給白名單以外的人，需要將 App 狀態改為 **Production**（Google 可能要求額外驗證，一般內部小工具維持 Testing + Test users 名單即可）

---

## 步驟 3：建立 OAuth Client ID

1. 左側選單 → **APIs & Services** → **Credentials**
2. **+ Create Credentials** → **OAuth client ID**
3. Application type：**Web application**
4. Name：`aimom-cognito`
5. **Authorized JavaScript origins**：可先留空（Cognito 走 server-side redirect，非必要）
6. **Authorized redirect URIs**：這裡最重要，必須填入 **Cognito Hosted UI 的回呼網址**，格式為：
   ```
   https://<你的-cognito-domain-prefix>.auth.<region>.amazoncognito.com/oauth2/idpresponse
   ```
   - 若使用 `infra/` Terraform，`cognito.tf` 中 domain prefix 設定為 `${local.name_prefix}-auth`，
     例如 `project_name=aimom`、`environment=dev` → domain 為 `aimom-dev-auth`
   - 假設 region 為 `ap-northeast-1`，完整網址即為：
     ```
     https://aimom-dev-auth.auth.ap-northeast-1.amazoncognito.com/oauth2/idpresponse
     ```
   - **注意**：這個網域必須等 Terraform 先建立好 `aws_cognito_user_pool_domain` 資源後才能確定是否可用
     （domain prefix 全域唯一，若被別人占用需改名），建議流程：
     1. 先想好 `project_name`/`environment`，或先 `terraform apply` 建立 Cognito 資源
     2. 用 `terraform output cognito_hosted_ui_domain` 取得實際網域
     3. 回來 Google Console 把這個網址填入 Authorized redirect URIs
     4. 由於 Google Client ID/Secret 需要先給 Terraform 建立 Cognito Identity Provider，實務上會是「先建立 Google Client（redirect URI 隨便填一個佔位）→ apply Terraform 拿到 Cognito domain → 回 Google Console 補上正確的 redirect URI」的兩階段流程
7. 建立完成後，Google 會顯示：
   - **Client ID**（格式類似 `xxxxx-yyyyy.apps.googleusercontent.com`）
   - **Client Secret**
   - 請兩者都先妥善保存（Client Secret 只會顯示一次，若遺失需重新產生）

---

## 步驟 4：填入 Terraform 變數

打開 `infra/terraform.tfvars`（若還沒建立，先從 `terraform.tfvars.example` 複製），填入：

```hcl
google_client_id     = "xxxxx-yyyyy.apps.googleusercontent.com"
google_client_secret = "your-client-secret"
```

**注意：`terraform.tfvars` 已列在 `.gitignore`，不會被提交到 GitHub，請勿手動移除該規則。**

---

## 步驟 5：（若之前用佔位 redirect URI）回頭補上正確網址

1. `cd infra && terraform apply` 建立 Cognito 資源
2. `terraform output cognito_hosted_ui_domain` 取得實際網域
3. 回 Google Cloud Console → Credentials → 編輯剛才建立的 OAuth Client
4. Authorized redirect URIs 補上：`https://<實際網域>/oauth2/idpresponse`
5. 儲存

---

## 常見問題

**Q: 一定要用 External User Type 嗎？**
A: 若所有使用者都在同一個 Google Workspace 網域內，可用 Internal（設定更簡單，不需要 Test users 名單，但僅限該網域帳號登入）。若團隊成員用一般 Gmail，必須用 External。

**Q: Testing 階段的 Refresh Token 只有 7 天效期，會影響使用嗎？**
A: 會。若長期使用建議申請將 App 狀態改為 **Production**（走 Google 驗證流程，需準備隱私權政策頁面等），否則使用者每 7 天需重新登入一次。小團隊 POC 階段可先接受此限制。

**Q: Client Secret 忘記存怎麼辦？**
A: 回 Credentials 頁面該 Client → **Reset secret**，重新產生後同步更新 `terraform.tfvars` 並重新 `terraform apply`。
