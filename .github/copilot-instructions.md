# POC-SDLC 系統（GitHub Copilot 版）

這是 AI 全自動 SDLC 概念驗證系統，專為 GitHub Copilot CLI 優化。
完整系統規範請參閱 `CLAUDE.md`，並行執行說明請參閱 `scripts/parallel-launch.md`。

## 快速啟動

### ⚡ Parallel 模式（推薦 — backlog 有多張工單時）

```
/autopilot
請啟動 Parallel SDLC 流程，掃描 board/backlog/ 中所有未認領工單，
為每張工單各自啟動一個背景 Agent，並行完成完整流程。
```

Orchestrator 將：
1. 掃描 backlog，找出所有未認領工單
2. 立即認領（寫入 `claimed_by` + 建立 lock file）
3. 用 `task` 工具為每張工單啟動獨立 background agent
4. 等待所有 agent 完成，輸出整體摘要

### 🚀 Autopilot 模式（單一 Session，順序處理）

```
/autopilot
請啟動 SDLC 流程，掃描 board/ 中所有待處理工單，
自動完成從需求分析到部署的完整流程，不需要我的介入。
```

### 🔧 手動模式（需人工切換）

若需要逐步控制，可手動指定階段：
```
/agent orchestrator   → 分派工單
/agent ba-agent       → 只執行需求分析
/agent sa-agent       → 只執行系統設計
/agent dev-agent      → 只執行開發
/agent review-agent   → 只執行 Code Review
/agent qa-agent       → 只執行測試
/agent devops-agent   → 只執行部署
```

## 模式比較

| 模式 | 適合場景 | 工單處理 | 速度 |
|------|---------|---------|------|
| Parallel | backlog 多張工單 | 同時並行 | ⚡ 最快 |
| Autopilot | 單一工單 / 順序偏好 | 依序處理 | 正常 |
| 手動 | 逐步控制 / 偵錯 | 人工觸發 | 最慢 |

## Lock 狀態查詢

```bash
# 查看目前所有 lock files
ls status/locks/

# 查看特定工單的 lock 狀態
cat status/locks/TASK-XXX.lock

# 過濾特定 session 的 log
grep "session-20260709" logs/ba-agent.log
```

## 代理指令檔位置

- `.github/instructions/agents/` — Copilot 原生格式（角色行為手冊）
- `.claude/agents/` — Claude Code 備用格式
- `scripts/parallel-launch.md` — Parallel 模式詳細說明

## MCP 設定（未來擴充）

```
/mcp
```
