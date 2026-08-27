# 前端部署指南（TASK-014）

`src/frontend/` 是純靜態網站（`index.html` + `config.js`），部署到 TASK-013 已建立的
`frontend` S3 bucket，由 CloudFront 提供對外存取。

## 1. 確認 `config.js` 內容正確

`src/frontend/config.js` 定義了目前環境的實際值，換環境（例如 prod）時只需要改這一個檔案：

```js
window.APP_CONFIG = {
  apiBaseUrl: '<api_invoke_url，來自 terraform output>',
  cognitoDomain: '<cognito_hosted_ui_domain>',
  cognitoClientId: '<cognito_app_client_id>',
  redirectUri: '<https://frontend_cloudfront_domain>',
  logoutUri: '<https://frontend_cloudfront_domain>',
  region: '<aws_region>',
};
```

`redirectUri`/`logoutUri` 必須與 `infra/terraform.tfvars` 的
`frontend_callback_urls`/`frontend_logout_urls` 完全一致（含結尾有無斜線），
否則 Cognito Hosted UI 會回傳 `redirect_uri mismatch` 錯誤。

## 2. 上傳到 S3（在 CloudShell 或本機有 AWS 憑證的環境執行）

```bash
aws s3 sync src/frontend/ s3://<frontend_bucket_name>/ \
  --exclude ".DS_Store" \
  --cache-control "no-cache, must-revalidate"
```

`no-cache` 是因為目前規模小、更新頻率低，先求「每次都拿到最新版本」而非做版本化快取，
之後流量變大再考慮改用 hash 檔名 + 長快取。

## 3. 建立 CloudFront Invalidation（讓變更立即生效）

```bash
aws cloudfront create-invalidation \
  --distribution-id <cloudfront_distribution_id> \
  --paths "/*"
```

`<cloudfront_distribution_id>` 可從 AWS Console → CloudFront，或
`terraform state show <cloudfront resource>` 取得（目前 `outputs.tf` 只輸出網域，
未輸出 distribution id，如常態需要可自行在 `infra/outputs.tf` 新增一個 output）。

## 4. 驗證流程

1. 瀏覽器開啟 `https://<frontend_cloudfront_domain>`（記得是 https，不是 http）
2. 應看到登入畫面 → 點擊「使用 Google 帳號登入」
3. 導向 Google 帳號選擇 → 導回 Cognito → 導回前端網域並自動完成 token 交換
4. 登入後應看到會議上傳主畫面；若帳號在 `admin_emails` 白名單內，右上角應看到
   「📊 管理者儀表板」按鈕
5. 實際上傳一段錄音，確認完整跑完 上傳 → 轉錄 → 摘要 → 匯出 流程
6. 點擊「登出」，確認回到登入畫面且 `sessionStorage` 已清空

## 已知限制

- ID Token 過期（Cognito 預設 1 小時）後，前端目前**不會自動用 refresh token 換新**，
  使用者會在下一次 API 呼叫收到 401 並被導回登入畫面，需要重新登入。
  對小團隊低頻使用場景可接受，如需改善可後續加上 silent refresh（用 refresh_token
  呼叫 `/oauth2/token` 換新 id_token）。
- `config.js` 目前是手動維護的靜態檔案，未來若環境變多，可考慮改為部署流程中
  自動產生（例如從 `terraform output -json` 產生），現階段单一 dev 環境足夠簡單維護。
