# AIMOM

AI 會議轉錄與摘要系統。後端為 Python（AWS Lambda handler），前端為靜態 HTML/JS，
資料儲存於 DynamoDB，認證採 AWS Cognito，基礎設施以 Terraform 管理。

> 本 repo 是從既有專案 `AIMOM`（`Boris-ECV/AIMOM`）延續而來，套用了
> sdlc-agent-framework 多代理 SDLC 框架繼續開發。舊 repo 已標記為
> deprecated，往後開發統一在此 repo 進行。

## 系統架構

```
src/
├── app.py                   ← 主要 API 進入點（路由/中介層）
├── lambda_handler.py         ← AWS Lambda 進入點（mangum）
├── auth.py                    ← Cognito JWT 認證
├── config.py                   ← 環境變數集中管理
├── db.py                         ← DynamoDB 存取
├── transcribe.py / diarize.py / summarize.py / export.py / progress.py
│                                  ← 轉錄、講者分離、摘要、匯出、進度追蹤等功能模組
├── admin.py / history.py / jobstore.py / usage.py / upload.py
│                                  ← 管理、歷史紀錄、任務儲存、用量、上傳相關功能
├── frontend/                    ← 靜態 HTML/JS（無 build 流程）
└── tests/                         ← pytest 測試（12 個檔案）

infra/                          ← Terraform（AWS 基礎設施）
docs/                             ← 框架文件（見下方「開發流程」）
docs/archive/                      ← 舊 POC-SDLC 系統遺留的 TASK 交付紀錄，僅供歷史參考，非現行設計文件
```

## 本地開發

```powershell
# 安裝依賴
pip install -r src/requirements.txt

# 執行測試（含覆蓋率）
pytest src/tests --cov=src --cov-report=term-missing

# Lint（目前為既有技術債，CI 尚未硬性阻擋，見 project-profile.yaml quality.lint_zero_tolerance）
ruff check .
```

實際指令、品質門檻與已知技術債，以 [project-profile.yaml](project-profile.yaml) 為唯一依據。

## 部署

AWS 基礎設施透過 Terraform（`infra/`）管理。`infra/backend.hcl` 與
`infra/terraform.tfvars` 為機密設定，未納入版控（僅提供 `.example` 範本），
實際部署前需向現有維運者取得 S3 state bucket 等資訊。

## 開發流程（sdlc-agent-framework）

本專案套用 sdlc-agent-framework 多代理 SDLC 框架進行後續功能開發：

- **需求追蹤**：Jira 專案 `SDLCAIP2` 為唯一事實來源，所有工單狀態、gate 決策皆記錄在 Jira 上。
- **開發流程**：每張 Story 依序走過 `Backlog → Refining → G1(需求核准) → Designing →
  G1b(設計核准) → Ready → In Progress → Testing → In Review → G2(合併) → Done`，
  由 orchestrator（Claude Code CLI）依 `.claude/CLAUDE.md` 規則驅動各 agent 完成。
- **啟動方式**：在此資料夾開啟 Claude Code CLI，執行 `/sdlc:start` 讓 orchestrator
  接手處理 Jira 上待處理的工單。
- **CI/CD**：GitHub Actions（`.github/workflows/ci.yml`）跑 lint + test + coverage 門檻，
  `main` 分支已設定 branch protection，需 PR 且 CI（`quality` job）綠燈才可合併。
- **工程原則**：見 [CONSTITUTION.md](CONSTITUTION.md)（失敗處理哲學、安全預設、測試哲學、
  範圍紀律、程式碼風格等，依既有程式碼慣例歸納，非憑空制定）。
- **既有專案（brownfield）補充**：本專案承接自既有程式碼，非綠地起始，舊系統既有功能
  沒有 `docs/design/<KEY>.md` 設計文件屬正常現象，不代表「無先例」，詳見
  `docs/04-project-instantiation.md` 既有專案套用補充章節。

框架本體文件（`.claude/`、`config/`、`templates/`、`docs/00-08*.md`）皆疊加自
sdlc-agent-framework 上游，若需修改框架行為，應回饋修改上游框架而非在此 repo 分叉。
