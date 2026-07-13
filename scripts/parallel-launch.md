# Parallel SDLC 啟動指南

## 概述

Parallel 模式讓 Orchestrator 為 backlog 中的每張工單啟動獨立的 background agent，
多張工單同時並行處理，大幅縮短整體完成時間。

---

## 架構示意

```
使用者輸入：「啟動 Parallel SDLC 流程」
              ↓
         Orchestrator
         （掃描 backlog）
         ↙    ↓    ↘
  Agent-A  Agent-B  Agent-C   ← 各自獨立 context window
  TASK-001 TASK-002 TASK-003
    ↓         ↓        ↓
  done/    done/    done/     ← 各自完成，互不干擾
```

---

## 啟動指令

### 方式一：處理所有 backlog 工單（推薦）

```
請啟動 Parallel SDLC 流程，掃描 board/backlog/ 中所有未認領工單，
為每張工單各自啟動一個背景 Agent，並行完成完整流程。
```

### 方式二：只處理指定工單

```
請啟動 Parallel SDLC 流程，並行處理 TASK-003、TASK-004、TASK-005。
```

### 方式三：Autopilot（單一順序，保持原本行為）

```
請啟動 SDLC 流程，掃描 board/ 中所有待處理工單，
自動完成從需求分析到部署的完整流程，不需要我的介入。
```

---

## Parallel 模式執行流程

### Orchestrator 執行步驟

```
1. 掃描 board/backlog/，列出所有無 claimed_by 的工單
2. 為每張工單建立 session ID（session-{timestamp}-{index}）
3. 對每張工單執行認領：
   a. 在工單 frontmatter 加入 claimed_by + claimed_at
   b. 建立 status/locks/TASK-XXX.lock
4. 用 task 工具為每張工單啟動 background agent
5. 等待所有 agent 完成（通知自動到達）
6. 輸出整體完成摘要
```

### 每個 Background Agent 執行步驟

```
1. 確認工單 claimed_by 是自己的 session（防衝突）
2. 依序執行 BA → SA → Dev → Review → QA → DevOps
3. 每步驟的 log 加入 [session-xxx] 標識
4. 完成後標記 lock released
```

---

## Lock File 說明

**位置：** `status/locks/TASK-XXX.lock`

**格式：**
```
session: session-20260709105800
task: TASK-003
locked_at: 2026-07-09T10:58:00
agent: ba-agent
released: false
```

**生命週期：**
- `Orchestrator 認領` → 建立，`released: false`
- `DevOps Agent 完成` → 更新，`released: true`
- `下次啟動前` → 可手動清除所有 `released: true` 的 lock files

---

## 衝突防護機制

| 場景 | 處理方式 |
|------|---------|
| 兩個 session 同時掃描 backlog | 第一個寫入 claimed_by 者獲得工單，後者讀到 claimed_by 後跳過 |
| Agent 崩潰後重啟 | 讀取 lock file，確認 session 一致，從上次斷點繼續 |
| Lock file 存在但 released=false 且 session 不符 | 視為他人持有，跳過 |
| 同名 agent（如兩個 ba-agent）衝突 | session ID 不同，status 欄位包含 session，可區分 |

---

## 並行執行範例

假設 backlog 有 3 張工單：

```bash
# Orchestrator 輸出：
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ Parallel SDLC 啟動
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
掃描結果：3 張工單待處理
  📋 TASK-003：實作使用者註冊功能
  📋 TASK-004：實作商品列表 API
  📋 TASK-005：實作購物車功能

認領完成 → 啟動 3 個背景 Agent：
  🚀 sdlc-TASK-003（session-20260709105800）已啟動
  🚀 sdlc-TASK-004（session-20260709105801）已啟動
  🚀 sdlc-TASK-005（session-20260709105802）已啟動

等待所有 Agent 完成...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# 三個 Agent 同時在各自的 context window 中執行
# 完成後各自輸出：
✅ sdlc-TASK-003 完成（BA→SA→Dev→Review→QA→DevOps）
✅ sdlc-TASK-004 完成
✅ sdlc-TASK-005 完成
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 注意事項

1. **Context Window 限制**：每個 background agent 有獨立的 context window，不共享對話記憶
2. **檔案系統是唯一共享層**：agent 之間只透過 `board/`、`status/`、`logs/` 協調
3. **不要並行修改同一個 src/ 檔案**：設計工單時確保不同工單操作不同模組
4. **Log 追蹤**：用 `grep "session-xxx"` 過濾特定 agent 的 log
5. **最大並行數建議**：≤ 5 張工單同時並行（避免資源競爭）
