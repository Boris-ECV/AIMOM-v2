# 設計文件 — SDLCAIP2-61 ALLOWED_EMAILS 白名單設定可透過 Terraform 部署且不被 CD 覆蓋

## 對應需求規格
G1 定稿版（見工單 SDLCAIP2-61 描述）：補齊 SDLCAIP2-23 遺漏的 infra 層設定，讓
`infra/variables.tf`、`infra/lambda.tf`、`infra/terraform.tfvars.example`、
`.github/workflows/ci.yml` 對稱於既有 `admin_emails` 的寫法新增
`allowed_emails`，使 `ALLOWED_EMAILS` 環境變數能實際注入 Lambda 且不被 CD
自動部署清除。應用層（`src/auth.py`、`src/config.py`，已讀取
`ALLOWED_EMAILS` 環境變數）不變動。

## 介面/API 契約
無新增對外 API。本 Story 是純 infra 設定串接，對外行為沿用 `src/auth.py`
既有的 403 邏輯（當 token 驗證通過但 email 不在白名單內時回傳 403，且
`ALLOWED_EMAILS` 為空字串時視為不限制，此行為已由 SDLCAIP2-23 實作與測試
覆蓋，本 Story 不重複設計）。

以下列出 4 個檔案各自要新增的確切內容，比照 `admin_emails` 現有寫法：

### 1. `infra/variables.tf`
在 `variable "admin_emails"`區塊之後新增（型別、default、sensitive 與
`admin_emails` 完全對稱）：

```hcl
variable "allowed_emails" {
  description = "登入白名單 email，逗號分隔，非空時強制僅允許清單內 email 登入"
  type        = string
  default     = ""
  sensitive   = true
}
```

### 2. `infra/lambda.tf`
在 `environment.variables`區塊內，緊接 `ADMIN_EMAILS = var.admin_emails`
之後新增一行：

```hcl
      ADMIN_EMAILS              = var.admin_emails
      ALLOWED_EMAILS            = var.allowed_emails
```

（對齊既有區塊的等號對齊風格，不需額外調整其他行的空格數。）

### 3. `infra/terraform.tfvars.example`
在 `admin_emails` 那一行之後新增範例值：

```
meeting_retention_days = 14
admin_emails           = "you@example.com,teammate@example.com"
allowed_emails         = "you@example.com,teammate@example.com"
```

### 4. `.github/workflows/ci.yml`
在 `terraform apply` step 的 `env` 區塊中，緊接
`TF_VAR_admin_emails: ${{ secrets.TF_VAR_admin_emails }}` 之後新增一行：

```yaml
          TF_VAR_admin_emails: ${{ secrets.TF_VAR_admin_emails }}
          TF_VAR_allowed_emails: ${{ secrets.TF_VAR_allowed_emails }}
```

此外，開發者需在 GitHub repo settings → Secrets 新增
`TF_VAR_allowed_emails`（人工操作，不在程式碼變更範圍內，但 AC2 的驗收
前提）；設計文件僅記錄此相依，不代為執行。

## 資料模型
無新增資料模型。

## 關鍵技術決策
- **完全比照 `admin_emails` 的型別/預設值/sensitive 設定**：`type = string`
  （非 `list(string)`）、`default = ""`、`sensitive = true`。理由：
  `src/config.py` 以逗號分隔字串解析（`os.getenv("ALLOWED_EMAILS", "")`），
  與 `admin_emails`→`ADMIN_EMAILS` 的既有資料流完全相同，維持同一種解析
  慣例可讓兩個白名單設定的行為一致、降低開發者誤用 Terraform list 型別
  導致字串格式不符的風險。
- **插入位置緊鄰 `admin_emails`／`ADMIN_EMAILS`／`TF_VAR_admin_emails`
  之後，而非檔案末端**：理由是維持兩個白名單變數在各檔案中物理相鄰、
  風格一致，未來讀者一眼就能看出兩者是同類設定、同時維護。
- **不建立新的 tfvars/CI 條件分支（例如依環境切換是否啟用白名單）**：
  理由是 spec 範圍外明確排除「多環境部署」，`ALLOWED_EMAILS` 為空字串時
  `src/auth.py` 既有邏輯即視為不限制登入，不需要額外的 Terraform
  條件邏輯即可滿足「非空時才生效」的需求。
- **不新增/修改 `src/auth.py`、`src/config.py` 或其測試**：spec 範圍外
  明確排除，且 SDLCAIP2-23 已完整實作並測試此段邏輯，本 Story 僅補 infra
  串接。

## UI 原型
無，本 Story 不涉及前端 UI（純 infra 設定變更，不涉及任何前端元件、版面
或樣式）。

## 開放設計問題（定稿時必須為空）
無。經讀取 `infra/variables.tf`、`infra/lambda.tf`、
`infra/terraform.tfvars.example`、`.github/workflows/ci.yml` 中
`admin_emails`/`ADMIN_EMAILS`/`TF_VAR_admin_emails` 的現有寫法後，確認
`allowed_emails` 可完全對稱套用，無任何需要額外產品決策或與既有模式衝突
之處。
