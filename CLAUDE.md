# POC-SDLC 專案

這是一個 AI 全自動 SDLC 概念驗證系統。
所有工具（Jira、GitHub、Confluence）均以本機文字檔模擬。

---

## 專案根目錄

`C:\Users\boris.lin\Claude\poc-sdlc-copilot`

---

## 執行模式

### 模式 A：Autopilot（單一 Session，順序處理）

本系統使用 **單一 Copilot 對話**自動扮演所有角色，適合單一工單或依序處理。

啟動指令：
```
請啟動 SDLC 流程，掃描 board/ 中所有待處理工單，
自動完成從需求分析到部署的完整流程，不需要我的介入。
```

### 模式 B：Parallel（多 Session，同時處理多工單）✨ 推薦

多個背景 Agent 同時各自處理一張工單，適合 backlog 有多張工單時。

啟動指令：
```
請啟動 Parallel SDLC 流程，掃描 board/backlog/ 中所有未認領工單，
為每張工單各自啟動一個背景 Agent，並行完成完整流程。
```

### 執行流程（Parallel 模式）

```
[掃描 board/backlog/，找出所有未認領工單]
          ↓
[為每張工單寫入 claimed_by + 建立 lock file]
          ↓
[用 task 工具 parallel 啟動多個背景 Agent]
    ↙         ↓         ↘
Agent-A    Agent-B    Agent-C
TASK-001  TASK-002   TASK-003
(完整SDLC) (完整SDLC) (完整SDLC)
    ↘         ↓         ↙
[等待所有 Agent 完成，輸出整體摘要]
```

---

## 資料夾結構說明

```
poc-sdlc/
├── board/              ← 工單看板（Jira 模擬）
│   ├── backlog/        ← 待處理
│   ├── analysis/       ← 需求分析中
│   ├── design/         ← 系統設計中
│   ├── development/    ← 開發中
│   ├── review/         ← Code Review 中
│   ├── testing/        ← 測試中
│   ├── done/           ← 完成
│   └── blocked/        ← 封鎖中
├── docs/               ← 文件（Confluence 模擬）
│   ├── requirements/   ← 需求文件
│   ├── design/         ← 設計文件
│   └── api/            ← API 規格
├── src/                ← 程式碼
├── versions/           ← 版本快照（Git 模擬）
│   └── TASK-XXX/
│       ├── before/     ← 任務開始前快照
│       └── after/      ← 任務完成後快照
├── status/             ← 各代理目前狀態
└── logs/               ← 各代理執行記錄
```

---

## 工單格式規範

每張工單是一個 `.md` 檔，檔名格式：`TASK-{三位數}.md`

### YAML frontmatter 欄位

```yaml
---
id: TASK-001
title: 任務標題
type: Story | Task | Bug | Epic
priority: High | Medium | Low
assignee: 代理名稱 | unassigned
status: backlog | analysis | design | development | review | testing | done | blocked
created: YYYY-MM-DD
updated: YYYY-MM-DD
epic: EPIC-XXX
---
```

### 工單狀態變更規則

**狀態變更 = 移動檔案到對應資料夾 + 更新 frontmatter status 欄位 + 新增歷程記錄**

```
backlog → analysis    (BA Agent 接單)
analysis → design     (BA Agent 完成後)
design → development  (SA Agent 完成後)
development → review  (Dev Agent 完成後)
review → testing      (Review Agent 通過後)
review → development  (Review Agent 退回後)
testing → done        (QA Agent 全過後)
testing → blocked     (發現嚴重 Bug 後)
任何狀態 → blocked    (遭遇阻礙時)
```

---

## 版本快照規範

每當代理開始執行一個任務，必須：

1. **開始前**：將 `src/` 相關檔案複製到 `versions/TASK-XXX/before/`
2. **完成後**：將 `src/` 相關檔案複製到 `versions/TASK-XXX/after/`

資料夾命名：`versions/TASK-{id}/before/` 和 `versions/TASK-{id}/after/`

---

## Log 格式規範

所有代理必須將執行步驟記錄到 `logs/{agent-name}.log`

格式：
```
[YYYY-MM-DDTHH:mm:ss] [代理名稱] [工單ID] 動作類型  說明
```

動作類型：
- `START`   — 開始執行任務
- `READ`    — 讀取檔案
- `WRITE`   — 寫入/建立檔案
- `MOVE`    — 移動工單（狀態變更）
- `VERSION` — 建立版本快照
- `ASSIGN`  — 指派任務給代理
- `DONE`    — 任務完成
- `ERROR`   — 發生錯誤
- `BLOCKED` — 任務被封鎖
- `NOTE`    — 一般備注

範例：
```
[2026-07-08T10:30:00] [dev-agent] [TASK-001] START   接取任務：實作使用者登入功能
[2026-07-08T10:30:05] [dev-agent] [TASK-001] READ    docs/requirements/login.md
[2026-07-08T10:30:10] [dev-agent] [TASK-001] VERSION 建立 before 快照 → versions/TASK-001/before/
[2026-07-08T10:30:15] [dev-agent] [TASK-001] WRITE   src/auth.js
[2026-07-08T10:30:30] [dev-agent] [TASK-001] MOVE    board/development/ → board/review/
[2026-07-08T10:30:31] [dev-agent] [TASK-001] VERSION 建立 after 快照 → versions/TASK-001/after/
[2026-07-08T10:30:32] [dev-agent] [TASK-001] DONE    任務完成，等待 Review
```

---

## Status 檔案規範

每個代理在 `status/` 下有一個 `.status` 檔案，格式：

```
status: idle | busy
updated: YYYY-MM-DDTHH:mm:ss
current_task: TASK-XXX | none
```

**規則：**
- 代理接任務前：更新 `status: busy`、`current_task: TASK-XXX`
- 代理完成任務後：更新 `status: idle`、`current_task: none`

---

## 代理職責說明

| 代理 | 職責 | 接單條件 |
|------|------|----------|
| **orchestrator** | 拆解需求、建立工單、分派任務、監控進度 | 收到人工需求輸入 |
| **ba-agent** | 需求分析、使用者故事、建立需求文件 | `board/backlog/` 有未指派 Story |
| **sa-agent** | 系統分析、DB Schema、API 設計 | `board/analysis/` 有工單 |
| **dev-agent** | 功能開發、撰寫測試 | `board/design/` 有工單 |
| **review-agent** | Code Review、品質檢查 | `board/review/` 有工單 |
| **qa-agent** | 測試執行、Bug 回報 | `board/testing/` 有工單 |
| **devops-agent** | 部署、交付報告 | `board/done/` 所有測試通過 |

---

## Orchestrator 分派流程

```
1. 掃描 board/backlog/ 取得待處理工單
2. 讀取 status/ 確認哪些代理 idle
3. 將工單指派給 idle 的對應代理
4. 更新工單 assignee 欄位
5. 通知代理開始執行
6. 持續監控 status/ 與 board/ 狀態
```

---

## ⚡ 並行執行規則（Parallel Execution Rules）

### 工單認領機制（Claim）

為避免多個 Agent Session 同時搶佔同一張工單，Orchestrator 分派工單時須：

**1. 立即在工單 frontmatter 寫入 claimed_by**
```yaml
---
claimed_by: session-{timestamp}   ← 新增此欄
claimed_at: YYYY-MM-DDTHH:mm:ss   ← 新增此欄
---
```

**2. 在 status/locks/ 建立 lock file**
```
status/locks/TASK-XXX.lock
```
內容格式：
```
session: session-{timestamp}
task: TASK-XXX
locked_at: YYYY-MM-DDTHH:mm:ss
agent: ba-agent
```

**3. Lock 釋放時機**：工單進入 `done/` 或 `blocked/` 時，刪除（改為標記 released）對應 lock file

### Agent 接單前的檢查

每個 Agent 接單前必須確認：
1. 工單 `claimed_by` 欄位是否是自己的 session
2. `status/locks/TASK-XXX.lock` 是否存在且匹配
3. 若工單已被他人認領 → 跳過，繼續掃描其他工單

### Status 檔案擴充格式

並行模式下，status 檔案加入 session 欄位：
```
status: idle | busy
updated: YYYY-MM-DDTHH:mm:ss
current_task: TASK-XXX | none
session: session-{timestamp} | none    ← 新增
```

### 並行啟動方式（task 工具）

Orchestrator 掃描 backlog 後，為每張未認領工單啟動獨立 background agent：

```
認領 TASK-001 → task(background) → "以 Autopilot 模式完整處理 TASK-001"
認領 TASK-002 → task(background) → "以 Autopilot 模式完整處理 TASK-002"
認領 TASK-003 → task(background) → "以 Autopilot 模式完整處理 TASK-003"
（同時啟動，各自獨立執行）
```

### Log 格式：加入 session 標識

並行模式下，log 格式加入 session 欄位以區分不同執行緒：
```
[timestamp] [agent-name] [TASK-XXX] [session-xxx] 動作類型  說明
```

### 衝突預防規則

| 資源 | 衝突類型 | 解決方式 |
|------|---------|---------|
| `board/backlog/TASK-XXX.md` | 雙重認領 | 認領後立即寫入 `claimed_by` |
| `status/{agent}.status` | 同代理角色雙佔 | 檢查 status=idle 後才接單 |
| `logs/{agent}.log` | 多 session 寫入 | 每行加 session ID，append 模式安全 |
| `docs/requirements/` | 路徑衝突 | 各 TASK 使用獨立子路徑 |

---

## 代碼規範

- 函式最長 50 行
- 每個模組必須有對應測試
- 測試檔命名：`{模組名}.test.js`
- 文件放在 `docs/` 對應子資料夾

---

## 工單 ID 規則

- Epic：`EPIC-{三位數}`，如 `EPIC-001`
- 任務：`TASK-{三位數}`，如 `TASK-001`
- Bug：`BUG-{三位數}`，如 `BUG-001`
- 編號由 Orchestrator 統一分配，遞增不重複
