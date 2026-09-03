# 設計文件 — SDLCAIP2-12 CD 部署將 Cognito callback/logout URL 覆蓋回 localhost，導致正式環境登入失敗

## 對應需求規格
G1 已核准的需求規格（本 ticket 描述）：SDLCAIP2-10 建立的 `.github/workflows/ci.yml`
`backend` job 執行 `terraform apply` 時，未注入 `infra/variables.tf` 中
`frontend_callback_urls`/`frontend_logout_urls` 兩個變數，導致這兩個
`list(string)` 變數持續套用 default 值 `["http://localhost:5500"]`；
這兩個變數同時餵給 `infra/cognito.tf` 的 `aws_cognito_user_pool_client.app`
（`callback_urls`/`logout_urls`）、`infra/apigateway.tf` 的 API Gateway
CORS `allow_origins`、以及 `infra/s3.tf` 音檔 bucket CORS
`allowed_origins`，使得每次 CD 執行 `terraform apply` 都會把正式環境
CloudFront 網址覆蓋回 localhost，導致正式環境使用者登入 Cognito 後無法
正確導回（callback/logout URL 不符）。核准的修復方式：新增兩個 GitHub
Actions **repository Variables**（非 Secrets，因非機密）
`FRONTEND_CALLBACK_URLS`／`FRONTEND_LOGOUT_URLS`（JSON array 字串，例如
`["https://d11d8l4nxw1bow.cloudfront.net"]`），並在 `backend` job 的
`terraform apply` step env 區塊新增：
```
TF_VAR_frontend_callback_urls: ${{ vars.FRONTEND_CALLBACK_URLS }}
TF_VAR_frontend_logout_urls: ${{ vars.FRONTEND_LOGOUT_URLS }}
```
人類已確認這兩個 GitHub repository variables 已建立完成。範圍外：
`infra/variables.tf`/`cognito.tf`/`apigateway.tf`/`s3.tf` 本身的程式碼
不變（這些檔案的變數/資源定義已經正確，問題只在 CI 沒有注入值）；
SDLCAIP2-13（CORS 被擋）與本 ticket 共用同一組根因與同一個修復（見下方
決策 3 與 `docs/design/SDLCAIP2-13.md`）。

## 介面/API 契約
本 Story 不新增/變更任何對外 API（純 CI/CD 設定修復，無 HTTP 端點、無
request/response 格式變動）。以下是 `.github/workflows/ci.yml` 的
`backend` job 中 `terraform apply` step 需要追加的內容（developer 據此
實作，不需自己發明格式）：

```yaml
      - name: terraform apply
        working-directory: infra
        run: terraform apply -auto-approve -input=false
        env:
          TF_VAR_google_client_id: ${{ secrets.TF_VAR_google_client_id }}
          TF_VAR_google_client_secret: ${{ secrets.TF_VAR_google_client_secret }}
          TF_VAR_admin_emails: ${{ secrets.TF_VAR_admin_emails }}
          TF_VAR_github_token: ${{ secrets.TF_VAR_github_token }}
          TF_VAR_openai_api_key: ${{ secrets.TF_VAR_openai_api_key }}
          TF_VAR_groq_api_key: ${{ secrets.TF_VAR_groq_api_key }}
          TF_VAR_gemini_api_key: ${{ secrets.TF_VAR_gemini_api_key }}
          TF_VAR_bedrock_proxy_base_url: ${{ secrets.TF_VAR_bedrock_proxy_base_url }}
          TF_VAR_bedrock_proxy_api_key: ${{ secrets.TF_VAR_bedrock_proxy_api_key }}
          TF_VAR_assemblyai_api_key: ${{ secrets.TF_VAR_assemblyai_api_key }}
          TF_VAR_frontend_callback_urls: ${{ vars.FRONTEND_CALLBACK_URLS }}
          TF_VAR_frontend_logout_urls: ${{ vars.FRONTEND_LOGOUT_URLS }}
```

這是對 SDLCAIP2-10 已核准 `backend` job 定義（`docs/design/SDLCAIP2-10.md`）
的 env 區塊追加兩行，其餘 10 個既有 `TF_VAR_*`（皆對應
`sensitive = true` 變數，經 `secrets.*` 注入）與 job 的 `needs`/`if`/其他
steps 全部不變。`vars.FRONTEND_CALLBACK_URLS`/`vars.FRONTEND_LOGOUT_URLS`
是 GitHub Actions 的 repository **Variables**（`Settings → Secrets and
variables → Actions → Variables` 分頁），語法上與 `secrets.*` 平行但
渲染在 log 中不會被遮罩（因為本來就非機密，見決策 1）；值必須是
Terraform `list(string)` 可解析的 JSON array 字串（例如
`["https://d11d8l4nxw1bow.cloudfront.net"]`），因為 `terraform apply`
對 `TF_VAR_<name>` 環境變數的解析規則是：若變數宣告型別非
`string`（此處是 `list(string)`），值必須是合法 HCL/JSON 字面值，純
逗號分隔字串（例如 `a,b`）不會被接受。人類已確認此兩個 repository
variables 已依此格式建立完成。

## 資料模型
無新增資料模型。本 Story 不新增/變更任何資料表、欄位或索引——
`infra/cognito.tf`/`apigateway.tf`/`s3.tf` 既有資源定義本身不變，
只是修正 CI 未注入既有變數值的缺陷，讓這些資源在 `terraform apply`
時採用正式環境的實際網址而非 default 的 localhost。

## 關鍵技術決策

1. **兩個新值採用 GitHub Actions repository **Variables**
   （`vars.FRONTEND_CALLBACK_URLS`/`vars.FRONTEND_LOGOUT_URLS`），不使用
   Secrets。**
   理由：CloudFront 網址是前端公開可見的網址（使用者瀏覽器網址列、
   Cognito Hosted UI redirect 都會直接曝露），不具機密性；GitHub
   Variables 與 Secrets 在 workflow log 中的行為差異是 Secrets 值會被
   自動遮罩為 `***`，若除錯時需要在 log 中確認實際注入的網址是否正確，
   Variables 不會遮罩、除錯更直接。用 Secrets 存放非機密值只會徒增
   「這是不是機密」的認知負擔，且與 SDLCAIP2-10 決策 8 建立的既有慣例
   （`sensitive = true` 才用 Secrets／`TF_VAR_*`）保持一致，此二變數在
   `infra/variables.tf` 中本來就未標記 `sensitive = true`。

2. **`frontend_callback_urls`/`frontend_logout_urls` 各自維持獨立的
   GitHub Variable，不合併成單一變數（例如一個
   `FRONTEND_URLS` 同時餵給兩者）。**
   理由：延續 SDLCAIP2-10 決策 8/建立的「一個 Terraform 變數對應一個
   注入來源」慣例（該決策原文即針對 sensitive 變數逐一對應 Secret）；
   雖然目前兩者的值通常相同（callback 與 logout 都導回同一個
   CloudFront 網址），但 `infra/cognito.tf` 將其宣告為兩個獨立變數，
   語意上允許未來登入後導回頁與登出後導回頁不同（例如導向不同的
   前端路由），合併成一個變數會在該情境出現時需要重新拆分 CI 設定與
   Terraform 變數宣告，維持現有 1:1 對應成本更低、風險更小。

3. **不新增一個「只給 CORS 用」的獨立變數，CORS（`apigateway.tf`/
   `s3.tf`）與 Cognito callback（`cognito.tf`）三處全部共用同一組
   `frontend_callback_urls`。**
   理由：三處消費的語意本質相同——「哪些前端網域被允許存取這個環境的
   後端/資源」，且 `infra/apigateway.tf:7`、`infra/s3.tf:27` 目前的
   Terraform 程式碼已經是直接引用 `var.frontend_callback_urls`（非本
   Story 新增的程式碼決策，是既有事實），這也是為什麼 SDLCAIP2-13
   （CORS 被擋）與本 ticket 是同一個根因、同一個修復——修這裡的 CI
   注入缺陷會同時修正 Cognito 登入與 CORS 兩個問題，拆成兩個獨立變數
   對現有程式碼結構沒有實益，反而需要修改 `apigateway.tf`/`s3.tf` 去
   引用新變數，擴大本 bug 修復的變更範圍到需求之外。

4. **本 Story 不修改 `infra/variables.tf`/`cognito.tf`/`apigateway.tf`/
   `s3.tf` 任一行程式碼，只修改 `.github/workflows/ci.yml`。**
   理由：這四個檔案的變數宣告、資源引用本身完全正確（`list(string)`
   型別、default 值合理、`callback_urls`/`allow_origins`/
   `allowed_origins` 都正確引用對應變數）；缺陷純粹是 CI 的
   `terraform apply` env 區塊少了兩行注入，修復範圍應精準對應根因，
   不擴大變更面。

## 開放設計問題（定稿時必須為空）
無。
