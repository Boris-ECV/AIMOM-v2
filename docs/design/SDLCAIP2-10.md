# 設計文件 — SDLCAIP2-10 建立後端 CD 自動部署（Terraform apply 自動化）

## 對應需求規格
G1 已核准的需求規格（本 ticket 描述）：PR 合併到 `main` 後，deploy workflow 的
`backend` job 應在非互動模式下重建 `infra/backend.hcl`（沿用既有 S3 remote
state bucket/key/region）並執行 `terraform init` + `apply`，使後端基礎設施
（Lambda 與其依賴的 `infra/` 資源）自動完成部署；Lambda `source_code_hash`
需反映最新 `src/` 內容；`infra/variables.tf` 中 10 個 `sensitive = true`
變數需各自透過獨立 GitHub Secret 以 `TF_VAR_<name>` 注入，workflow yaml
本身不得含任何機密明文；任一步驟失敗時 GitHub Actions 需清楚顯示該 job
失敗並保留完整 log。範圍外：前端 S3 sync/CloudFront invalidation
（SDLCAIP2-11）、Slack/email 通知、Lambda Layer 重建自動化以外的最佳化、
多環境部署、前端改用 Terraform 管理。AWS 憑證注入機制的選型留給本設計文件
決定（見下方決策 1）。

## 介面/API 契約
本 Story 不新增/變更任何對外 API（純 CI/CD 自動化，無 HTTP 端點、無
request/response 格式變動）。以下是 `.github/workflows/ci.yml` 新增的
`backend` job 完整內容（developer 據此實作，不需自己發明格式）：

```yaml
  backend:
    name: Deploy backend (terraform apply)
    needs: [quality, e2e]
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    timeout-minutes: 20
    permissions:
      id-token: write
      contents: read
    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials (OIDC)
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_DEPLOY_ROLE_ARN }}
          aws-region: ${{ secrets.TF_STATE_REGION }}

      - uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: "1.10.5"
          terraform_wrapper: false

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Build Lambda layer
        run: bash scripts/build_lambda_layer.sh

      - name: Reconstruct infra/backend.hcl
        run: |
          cat > infra/backend.hcl <<EOF
          bucket = "${{ secrets.TF_STATE_BUCKET }}"
          key    = "${{ secrets.TF_STATE_KEY }}"
          region = "${{ secrets.TF_STATE_REGION }}"
          encrypt = true
          use_lockfile = true
          EOF

      - name: terraform init
        working-directory: infra
        run: terraform init -backend-config=backend.hcl -input=false

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
```

完整 job 加入既有 `jobs:` 底下，與 `quality:`/`e2e:` 平行（同一層級縮排），
`on:` 沿用既有頂層設定（不需另開 workflow 檔案，見決策 3）。`needs: [quality,
e2e]` 搭配 GitHub Actions 預設語意（`needs` 依賴的 job 須全部成功才會執行）
直接滿足 AC Scenario 1 的 Given 子句「一個 PR 已通過 quality 與 e2e job 並
合併到 main」；`if:` 條件把此 job 限制在「push 事件且分支為 main」，PR 觸發
的 `pull_request` event 不會執行此 job（避免每個 PR 都跑一次昂貴且有副作用
的 `terraform apply`）。

## 資料模型
無新增資料模型。本 Story 不新增/變更任何資料表、欄位或索引——`infra/`
既有的 DynamoDB/S3/Lambda/Cognito 資源定義本身不變，只是把「誰來執行
`terraform apply`」從人工改成 CI。

## 關鍵技術決策

1. **AWS 憑證注入採用 GitHub OIDC + `aws-actions/configure-aws-credentials`
   assume-role，不使用靜態 access key/secret GitHub Secrets。**
   理由：OIDC 讓每次 job 執行取得的是短效期臨時憑證（job 結束即失效），
   不需要長期存活、需要人工輪替的 AWS access key 存在 GitHub Secrets 裡；
   是 AWS 與 GitHub 官方目前對 CI/CD 場景的建議做法，安全風險面顯著低於
   靜態金鑰外洩。取捨：需要人類事先在 AWS 手動建立一次性資源（OIDC
   identity provider + IAM role 信任策略），這與 `infra/bootstrap/`
   建立 state bucket 的雞生蛋問題性質相同（無法用還沒有憑證的 CI 自己
   建立自己要用的憑證來源），因此比照現行慣例列為「人類手動一次性設定」
   （見下方「外部依賴」）而非新增 Terraform 資源。

2. **`infra/backend.hcl` 由三個獨立 Secret（`TF_STATE_BUCKET` /
   `TF_STATE_KEY` / `TF_STATE_REGION`）在 CI 內用 heredoc 組回檔案，而非
   單一個「整份 backend.hcl 內容」的大 Secret。**
   理由：與 AC Scenario 2「每個變數應對應一個獨立的 GitHub Secret」的
   精神一致，套用到 state backend 設定同樣granular／可個別更新／可個別
   稽核（例如未來換 bucket 只需改一個 Secret，不需要重貼整份檔案內容）；
   `encrypt = true`／`use_lockfile = true` 兩個值在既有
   `backend.hcl.example` 中固定不變（非環境相依），直接寫死在 heredoc
   內，不需要額外 Secret。

3. **`backend` job 加進既有 `.github/workflows/ci.yml`，作為與
   `quality`/`e2e` 平行的第三個 job，不另開新的 workflow 檔案。**
   理由：延續 SDLCAIP2-5 已建立的慣例（`docs/design/SDLCAIP2-5.md` 決策：
   e2e job 直接加入同一份 `ci.yml`，不另開檔案）；單一 workflow 檔案下
   `needs:` 可直接表達「等 quality/e2e 成功才跑 backend」的依賴語意，
   避免使用跨 workflow 的 `workflow_run` trigger（需要額外處理
   `workflow_run` 事件本身沒有原始 push 的完整 context、且需要另外查詢
   上游 workflow 執行結果，複雜度與失敗模式都高於同檔案 `needs:`）。

4. **Terraform 版本用 `hashicorp/setup-terraform@v3` 明確 pin 為
   `1.10.5`（而非只依賴 runner 預裝版本或只寫 `>= 1.5.0`）。**
   理由：`infra/backend.hcl.example` 與 `infra/README.md` 明確依賴
   Terraform 1.10+ 原生 S3 state locking（`use_lockfile = true`，取代
   DynamoDB lock table）；`providers.tf` 的 `required_version >= 1.5.0`
   只是下限，不保證 CI runner 剛好裝到 >=1.10 的版本。明確 pin 一個
   已知支援 `use_lockfile` 的版本號，避免 CI 環境版本漂移導致
   `terraform init` 對 lockfile 語法解讀失敗。

5. **Lambda Layer 打包直接呼叫既有 `scripts/build_lambda_layer.sh`
   （非 `.ps1`，因 runner 是 `ubuntu-latest`），不在 workflow yaml 內
   重新用逐行指令實作打包邏輯。**
   理由：範圍外條款明確排除「Lambda Layer 重建自動化以外的最佳化，沿用
   現有 scripts/build_lambda_layer.ps1/.sh」；CI 只是這支既有腳本的一個
   新呼叫端，避免同一份打包邏輯在 shell script 與 workflow yaml 兩處
   重複維護（違反 CONSTITUTION「避免不必要的抽象層」／單一事實來源）。
   腳本本身已將輸出固定寫到 `infra/build/aimom-lambda-layer.zip`，與
   `infra/lambda.tf` 的 `aws_lambda_layer_version.filename` 路徑一致，
   不需額外接線。

6. **`backend` job 的 `permissions:` 只在 job 層級宣告
   `id-token: write` + `contents: read`，不改動 workflow 頂層
   `permissions`。**
   理由：`id-token: write` 是 OIDC assume-role 的硬性需求，但 GitHub
   Actions 的 `permissions` 支援 job 層級覆寫；把最小權限限制在
   `backend` 這個會實際觸碰 AWS 的 job，`quality`/`e2e` 兩個既有 job
   維持目前隱含的預設權限不變，避免範圍外地放寬整個 workflow 的 token
   權限面。

7. **`terraform apply -auto-approve -input=false`（而非互動輸入
   `yes`）達成 AC Scenario 1 的非互動模式要求；`terraform init` 同樣加
   `-input=false`。**
   理由：AC 明文要求「非互動模式（無需人工輸入 yes）」，`-auto-approve`
   是 Terraform 官方對應此需求的標準旗標；`-input=false`
   同時防止任何變數缺漏時 Terraform 停下來互動式提示輸入（而是直接以
   錯誤結束，讓失敗立即可見，呼應 Scenario 3）。

8. **只有 `infra/variables.tf` 中 `sensitive = true` 的 10 個變數透過
   `TF_VAR_<name>` Secret 注入；其餘非機密變數（如
   `frontend_callback_urls`/`frontend_logout_urls`/`llm_engine` 等）
   沿用 `variables.tf` 現有 default 值，不在本 Story 額外注入。**
   理由：AC Scenario 2 明確只針對「標記 sensitive = true 的每個變數」；
   非機密變數已有 default（`frontend_callback_urls` 預設
   `http://localhost:5500` 等），套用 default 足以讓 `terraform apply`
   成功（滿足 Scenario 1「不因缺少機密變數而失敗」——這句話本身也隱含
   「非機密變數缺漏不在此 Story 的失敗防範範圍內」），若之後需要 CI
   部署帶入正式 CloudFront 網址等非機密環境值，屬於獨立故事（可能與
   SDLCAIP2-11 前端 CloudFront 網址產生後才有值可填），不在本 Story
   範圍內處理。

9. **部署失敗的可見性完全依賴 GitHub Actions 原生 job 失敗狀態 +
   完整 step log，不加 `continue-on-error`、不加自訂通知步驟。**
   理由：AC Scenario 3 與範圍外條款都明確只要求「GitHub Actions 顯示
   該 job 為失敗狀態，並保留完整錯誤 log（不需額外通知機制）」；
   `terraform apply` 失敗時的 shell exit code 非 0 會讓 step 直接標記
   失敗、job 顯示紅色，GitHub Actions 預設保留每個 step 的完整 stdout/
   stderr log，不需要任何額外程式碼即可滿足此 Scenario。

## 開放設計問題（定稿時必須為空）
無。

## 外部依賴（需要人類手動設定，非本 Story 程式碼範圍）

**一次性 AWS 設定（OIDC，比照 `infra/bootstrap/` 雞生蛋問題的既有慣例，
由人類手動建立，不透過本 Story 的 Terraform 程式碼建立）：**
1. 在 AWS IAM 建立 OIDC identity provider：
   `https://token.actions.githubusercontent.com`（audience
   `sts.amazonaws.com`），若帳號內已有其他專案建立過則可重用。
2. 建立一個部署用 IAM role（例如 `aimom-gha-deploy-role`），信任政策
   限定 `token.actions.githubusercontent.com` 且
   `sub` 條件限制為 `repo:Boris-ECV/AIMOM-v2:ref:refs/heads/main`
   （只有 main 分支的 push 觸發能 assume 這個 role，PR 分支不行）。
3. 該 role 需要涵蓋 `infra/*.tf` 會用到的權限：DynamoDB、S3（state
   bucket + 音檔/前端 bucket）、Lambda（含 Layer）、API Gateway v2、
   CloudFront、Cognito、以及 IAM（`iam:CreateRole`/`PutRolePolicy`/
   `AttachRolePolicy`/`PassRole` 等，因為 `infra/iam.tf` 本身會建立/
   修改 IAM role），建議先比照 `terraform plan` 涉及的資源清單收斂為
   自訂 policy，範圍限制在 `${project_name}-*` 資源命名前綴。

**GitHub Secrets（需要人類在 repo Settings → Secrets and variables →
Actions 逐一設定，共 14 個）：**

AWS 憑證（1 個）：
- `AWS_DEPLOY_ROLE_ARN` — 上述 IAM role 的 ARN

State backend 設定（3 個，取自既有 `infra/bootstrap` 輸出/現行手動部署
使用的 `backend.hcl` 實際值）：
- `TF_STATE_BUCKET`
- `TF_STATE_KEY`
- `TF_STATE_REGION`

`infra/variables.tf` 的 10 個 `sensitive = true` 變數（取自現行手動部署
使用的 `terraform.tfvars` 實際值）：
- `TF_VAR_google_client_id`
- `TF_VAR_google_client_secret`
- `TF_VAR_admin_emails`
- `TF_VAR_github_token`
- `TF_VAR_openai_api_key`
- `TF_VAR_groq_api_key`
- `TF_VAR_gemini_api_key`
- `TF_VAR_bedrock_proxy_base_url`
- `TF_VAR_bedrock_proxy_api_key`
- `TF_VAR_assemblyai_api_key`
