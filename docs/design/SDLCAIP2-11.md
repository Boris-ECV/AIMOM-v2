# 設計文件 — SDLCAIP2-11 建立前端 CD 自動部署（S3 sync + CloudFront invalidation）

## 對應需求規格
G1 已核准的需求規格（本 ticket 描述）：PR 合併到 `main` 後，deploy workflow 的
`frontend` job 應將 `src/frontend/` 內容同步到前端 S3 bucket（套用
`--cache-control "no-cache, must-revalidate"`，排除 `.DS_Store`），並對
CloudFront distribution 發出一次 `--paths "/*"` 的 invalidation；`frontend`
job 必須依賴 SDLCAIP2-10 的 `backend` job 成功完成才會觸發（不會單獨搶跑）；
`infra/outputs.tf` 需新增 `cloudfront_distribution_id` output（對應
`aws_cloudfront_distribution.frontend.id`）供部署步驟使用；任一步驟失敗時
GitHub Actions 需清楚顯示該 job 失敗並保留完整 log。範圍外：
terraform apply/後端基礎設施部署（SDLCAIP2-10 範圍，本故事直接消費其輸出）、
Slack/email 通知機制、多環境部署、前端改用 Terraform `aws_s3_object` 管理、
`config.js` 自動產生（沿用手動維護現況）。

## 介面/API 契約
本 Story 不新增/變更任何對外 API（純 CI/CD 自動化，無 HTTP 端點、無
request/response 格式變動）。以下是 `.github/workflows/ci.yml` 新增的
`frontend` job 完整內容，與既有 `quality`/`e2e`/`backend`（SDLCAIP2-10）
平行加入同一份 `jobs:`：

```yaml
  frontend:
    name: Deploy frontend (S3 sync + CloudFront invalidation)
    needs: [backend]
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    timeout-minutes: 10
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

      - name: Sync frontend to S3
        run: |
          aws s3 sync src/frontend/ s3://${{ needs.backend.outputs.frontend_bucket_name }}/ \
            --exclude ".DS_Store" \
            --cache-control "no-cache, must-revalidate"

      - name: Invalidate CloudFront cache
        run: |
          aws cloudfront create-invalidation \
            --distribution-id ${{ needs.backend.outputs.cloudfront_distribution_id }} \
            --paths "/*"
```

`aws s3 sync`/`aws cloudfront create-invalidation` 的旗標與參數逐字沿用
`docs/archive/deploy/frontend-deploy.md` 現行手動部署指令（見決策 5），僅將
`<frontend_bucket_name>`/`<cloudfront_distribution_id>` 換成 CI 內可取得的
job output 參照。`needs: [backend]` 搭配與 `backend` job 相同的
`if: github.event_name == 'push' && github.ref == 'refs/heads/main'` 條件，
直接滿足 AC Scenario 3（backend 失敗或尚未完成時 frontend 不會被觸發——這是
GitHub Actions `needs` 的預設語意：上游 job 未成功，下游 job 直接被跳過，
不需要額外撰寫條件判斷）。

**`infra/outputs.tf` 新增（本 Story 程式碼範圍）：**

```hcl
output "cloudfront_distribution_id" {
  description = "前端 CloudFront distribution ID，供部署流程建立 invalidation 使用"
  value       = aws_cloudfront_distribution.frontend.id
}
```

加在既有 `frontend_cloudfront_domain` output 之後，對應
`infra/cloudfront.tf` 的 `aws_cloudfront_distribution.frontend` 資源（已確認
資源名稱與 spec 描述一致）。

**`.github/workflows/ci.yml` 的 `backend` job 需追加 outputs（本 Story 的
整合點，見決策 1 ——影響 SDLCAIP2-10 已合併的 job 定義，非本 Story 自建新
job）：**

```yaml
  backend:
    # …SDLCAIP2-10 既有內容不變，新增以下 1 個 step + 1 個 outputs: 區塊…
    outputs:
      frontend_bucket_name: ${{ steps.tf-outputs.outputs.frontend_bucket_name }}
      cloudfront_distribution_id: ${{ steps.tf-outputs.outputs.cloudfront_distribution_id }}
    steps:
      # …checkout / configure-aws-credentials / setup-terraform / setup-python /
      #    build lambda layer / reconstruct backend.hcl / terraform init /
      #    terraform apply（以上皆為 SDLCAIP2-10 既有 steps，不變）…

      - name: Export terraform outputs for frontend job
        id: tf-outputs
        working-directory: infra
        run: |
          echo "frontend_bucket_name=$(terraform output -raw frontend_bucket_name)" >> "$GITHUB_OUTPUT"
          echo "cloudfront_distribution_id=$(terraform output -raw cloudfront_distribution_id)" >> "$GITHUB_OUTPUT"
```

## 資料模型
無新增資料模型。`infra/outputs.tf` 新增的 `cloudfront_distribution_id` 是
Terraform infra 層級的輸出值（暴露既有資源的一個屬性），不是應用程式的資料
表/欄位/索引——不屬於本節「資料模型」的範疇，故仍列「無新增資料模型」。

## 關鍵技術決策

1. **`backend`（SDLCAIP2-10）job 需追加 `outputs:` 區塊 + 一個
   `terraform output -raw` 步驟，才能把 `frontend_bucket_name`/
   `cloudfront_distribution_id` 傳給 `frontend` job；這是本 Story 對
   SDLCAIP2-10 job 定義的必要追加，不是重新設計 SDLCAIP2-10。**
   理由：GitHub Actions 的 `needs.<job>.outputs.<name>` 是唯一內建的
   跨 job 傳值機制，前提是上游 job 必須在 `outputs:` 宣告從某個 step
   output 映射而來的值；`terraform apply` 本身不會自動把 apply 結果寫進
   `$GITHUB_OUTPUT`，需要額外一個 `terraform output -raw <name>` 呼叫。
   取捨：這代表 `frontend` job 無法在不修改 `backend` job 的情況下獨立
   取得這兩個值——曾考慮讓 `frontend` job 自己重新 `terraform init` +
   `terraform output`（不依賴 `backend` 的 outputs），但那需要重複一次
   `backend.hcl` 重建 + `terraform init` 的 remote state 讀取，且會在
   `frontend` job 內再暴露一次同樣的 state bucket 存取面，複雜度與風險都
   高於在 `backend` job 內多加 4 行 step；因此選擇追加 `backend` 的
   outputs，而非讓 `frontend` job 自己讀 state。**是否需要為此走
   SDLCAIP2-10 的正式設計文件修訂/重新過 G1b，見文件末「對 SDLCAIP2-10 的
   影響」一節。**

2. **`frontend` job 用 `needs: [backend]`（而非 `needs: [quality, e2e,
   backend]` 或平行於 `backend` 各自 `needs: [quality, e2e]`）表達
   「必須等 backend 成功」。**
   理由：AC Scenario 3 明確要求「backend job 失敗或尚未完成時 frontend
   不應被觸發」；GitHub Actions 的 `needs` 是遞移的觸發前提（`backend`
   本身已 `needs: [quality, e2e]`，`frontend` 只需再宣告對 `backend` 的
   直接依賴，不需重複列出 `quality`/`e2e`），且 `frontend` 需要消費
   `backend` 的 job outputs（見決策 1），`needs: [backend]` 同時滿足
   「依賴語意」與「取值語意」兩個需求，是唯一必要的宣告。

3. **`frontend` job 沿用與 `backend` 完全相同的 `if:` 條件
   （`github.event_name == 'push' && github.ref == 'refs/heads/main'`）
   而非只依賴 `needs:` 隱含的觸發條件。**
   理由：`needs:` 只保證「若此 job 因其他條件被排入才會等待上游」，本身
   不會限制觸發事件；沿用與 `backend` 相同的顯式 `if:` 條件，讓
   `frontend` 在語意上與 `backend`（SDLCAIP2-10 決策 3）保持一致、易讀，
   且雙重保險：即使 `needs:` 語意被誤解，`if:` 仍能防止 `frontend` 在
   PR 事件（`pull_request`）下被觸發。

4. **`frontend` job 加進既有 `.github/workflows/ci.yml`，與
   `quality`/`e2e`/`backend` 平行，不另開新 workflow 檔案。**
   理由：延續 SDLCAIP2-5（e2e）與 SDLCAIP2-10（backend）已建立的慣例，
   單一 workflow 檔案下 `needs:` 可直接表達 job 間依賴，避免跨 workflow
   `workflow_run` trigger 的額外複雜度（同 SDLCAIP2-10 決策 3 理由）。

5. **`aws s3 sync`/`aws cloudfront create-invalidation` 指令與旗標逐字
   沿用 `docs/archive/deploy/frontend-deploy.md` 現行手動部署步驟，不在
   CI 內另外設計新的快取策略或 invalidation 範圍。**
   理由：本 Story 範圍是「把既有手動指令自動化」，非重新設計部署策略；
   `--cache-control "no-cache, must-revalidate"` 與 `--paths "/*"` 的
   選型理由已記錄在該文件（小規模、低更新頻率，求「每次都拿到最新版本」），
   本 Story 不重新評估，維持現況。

6. **`frontend` job 的 `permissions:` 只在 job 層級宣告
   `id-token: write` + `contents: read`（與 `backend` job 相同模式），
   不改動 workflow 頂層 `permissions`。**
   理由：與 SDLCAIP2-10 決策 6 相同考量——`id-token: write` 是 OIDC
   assume-role 的硬性需求，限制在會實際觸碰 AWS 的 job，`quality`/`e2e`
   維持現有預設權限不變。

7. **AWS 憑證沿用 SDLCAIP2-10 已設定的同一個 OIDC role
   （`secrets.AWS_DEPLOY_ROLE_ARN`），不建立新的 IAM role 或新 Secret。**
   理由：spec「外部依賴」明確「無新增，沿用 SDLCAIP2-10 已設定的 AWS OIDC
   憑證與 GitHub Secrets」；`AWS_DEPLOY_ROLE_ARN` 對應的 IAM role 權限
   （SDLCAIP2-10 外部依賴清單第 3 點）已涵蓋 S3（含前端 bucket）與
   CloudFront，`s3:PutObject`/`cloudfront:CreateInvalidation` 等動作屬於
   該 role 既有 policy 範圍內的資源操作，不需要額外授權。

8. **部署失敗的可見性完全依賴 GitHub Actions 原生 job 失敗狀態 + 完整
   step log，不加 `continue-on-error`、不加自訂通知步驟。**
   理由：與 SDLCAIP2-10 決策 9 相同——AC Scenario 4 與範圍外條款都明確
   只要求原生失敗顯示與完整 log，`aws s3 sync`/`aws cloudfront
   create-invalidation` 失敗時的 shell exit code 非 0 已自然滿足此要求。

## 開放設計問題（定稿時必須為空）
無。

## 對 SDLCAIP2-10 的影響（供 orchestrator 判斷是否需要重開 G1b）

SDLCAIP2-10 的設計文件（`docs/design/SDLCAIP2-10.md`）與其 G1b 已核准的
`backend` job 定義**不包含** `outputs:` 區塊與 `terraform output -raw`
匯出步驟——這是因為 SDLCAIP2-10 撰寫時，跨 job 傳值的需求方
（本 Story 的 `frontend` job）尚未設計。本 Story 的實作需要在 `backend`
job 追加：
1. 一個新 step（`Export terraform outputs for frontend job`，見上方
   「介面/API 契約」）
2. job 層級的 `outputs:` 宣告

這個追加**不改變 SDLCAIP2-10 已核准的任何行為**（不改動 `needs`/`if`/
既有 steps 的執行內容或順序，`terraform output -raw` 是唯讀操作、不影響
`terraform apply` 已完成的部署結果），純粹是新增兩個唯讀輸出值的暴露
管道。屬於「發現既有設計需要一個小的、不改變其行為的擴充點」，而非推翻
SDLCAIP2-10 的技術決策——建議**不需要**因此重開 SDLCAIP2-10 的 G1b，
可由本 Story 的 developer 在實作 `frontend` job 時一併對 `backend` job
補上這個 diff（同一顆 PR 或緊接的 PR 皆可，但建議同一顆 PR，因為
`frontend` job 若無此 outputs 會直接執行失敗，兩者是同一個可運作單元）。
若 orchestrator 認為「修改一份已通過 G1b 的設計對應的既有程式碼」本身
需要走正式流程，才需要另外處理；本設計文件已把追加內容完整寫清楚
（見上方 backend job outputs 區塊），developer 據此實作即可，不需要
额外的設計澄清。
