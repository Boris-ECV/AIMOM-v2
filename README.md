# POC-SDLC 快速開始指南（GitHub Copilot 版）

## 系統現況

```
poc-sdlc-copilot/
├── .github/
│   ├── copilot-instructions.md  ← ✅ Copilot 全局指令
│   └── instructions/agents/     ← ✅ 7 個代理 Copilot 指令檔
├── .claude/agents/              ← ✅ 7 個代理 Claude Code 備用格式
├── board/
│   ├── backlog/        ← ✅ TASK-001.md（等待處理）
│   ├── analysis/
│   ├── design/
│   ├── development/
│   ├── review/
│   ├── testing/
│   ├── done/
│   └── blocked/
├── docs/
│   ├── requirements/
│   ├── design/
│   └── api/
├── src/
├── versions/
├── status/             ← ✅ 7 個代理，全部 idle
├── logs/               ← ✅ 7 個代理，初始 log
├── AGENTS.md           ← ✅ Copilot 代理索引
└── CLAUDE.md           ← ✅ 系統規範文件（Copilot & Claude Code 共用）
```

---

## 啟動方式

在 `poc-sdlc-copilot/` 資料夾中開啟 **GitHub Copilot CLI**，輸入：

```
/autopilot
請啟動 SDLC 流程，掃描 board/ 中所有待處理工單，
自動完成從需求分析到部署的完整流程，不需要我的介入。
```

Copilot 將自動依序執行：
`BA Agent → SA Agent → Dev Agent → Review Agent → QA Agent → DevOps Agent`

### 手動模式（逐步控制）

```
/agent ba-agent      → 只執行需求分析
/agent sa-agent      → 只執行系統設計
/agent dev-agent     → 只執行開發
/agent review-agent  → 只執行 Code Review
/agent qa-agent      → 只執行測試
/agent devops-agent  → 只執行部署
```

---

## 目前工單

| ID | 標題 | 狀態 | 位置 |
|----|------|------|------|
| TASK-001 | 實作使用者登入功能 | backlog | board/backlog/ |

---

## 代理清單

| `/agent` 指令 | 代理 | 職責 | 接單條件 |
|--------------|------|------|----------|
| `/agent orchestrator` | Orchestrator | 分派工單、監控進度 | 人工需求輸入 |
| `/agent ba-agent` | BA Agent | 需求分析、文件撰寫 | board/backlog/ 有工單 |
| `/agent sa-agent` | SA Agent | 系統設計、API 規格 | board/design/ 有工單 |
| `/agent dev-agent` | Dev Agent | 功能開發、撰寫測試 | board/development/ 有工單 |
| `/agent review-agent` | Review Agent | Code Review | board/review/ 有工單 |
| `/agent qa-agent` | QA Agent | 測試執行、Bug 回報 | board/testing/ 有工單 |
| `/agent devops-agent` | DevOps Agent | 部署、交付報告 | board/done/ 有工單 |

---

## 預期執行流程（TASK-001）

```
orchestrator    讀取 backlog → 分派 TASK-001 給 ba-agent
ba-agent        分析需求 → 建立 docs/requirements/TASK-001-requirements.md
                移動工單：backlog → analysis → design
sa-agent        設計系統 → 建立 docs/design/TASK-001-design.md
                移動工單：design → development
dev-agent       建立 before 快照 → 開發 src/auth.js + src/auth.test.js
                建立 after 快照 → 移動工單：development → review
review-agent    Code Review → PASS → 移動工單：review → testing
qa-agent        執行測試 → 全過 → 移動工單：testing → done
devops-agent    模擬部署 → 建立交付報告 docs/TASK-001-delivery.md
```

---

## 指令檔說明

| 檔案 | 用途 |
|------|------|
| `CLAUDE.md` | 系統總規範，Copilot 與 Claude Code 皆讀取 |
| `AGENTS.md` | 代理索引，Copilot 讀取 |
| `.github/copilot-instructions.md` | Copilot 專用全局指令 |
| `.github/instructions/agents/*.instructions.md` | Copilot 代理定義（主要）|
| `.claude/agents/*.md` | Claude Code 代理定義（備用）|

---

## 常用操作指令

```powershell
# 查看所有工單
Get-ChildItem board -Recurse -Filter "*.md" | Where {$_.Name -ne "_TEMPLATE.md"}

# 查看所有代理狀態
Get-Content status\*.status

# 手動移動工單
Move-Item board\backlog\TASK-001.md board\analysis\TASK-001.md

# 查看 log
Get-Content logs\ba-agent.log
```
