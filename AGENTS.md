# SDLC 角色行為手冊

> 本系統使用 **Autopilot 單代理全自動模式**。
> Orchestrator 自動依序扮演以下角色，不需要人工切換。
> 完整執行邏輯請參閱 `.github/instructions/agents/orchestrator.instructions.md`。

---

## 🎩 BA Agent（需求分析師）
**觸發條件：** `board/backlog/` 有工單
**產出物：** `docs/requirements/TASK-XXX-requirements.md`
**工單流向：** `backlog/` → `analysis/` → `design/`

---

## 📐 SA Agent（系統分析師）
**觸發條件：** `board/design/` 有工單
**產出物：** `docs/design/TASK-XXX-design.md`、`docs/api/TASK-XXX-api.md`
**工單流向：** `design/` → `development/`

---

## 💻 Dev Agent（開發工程師）
**觸發條件：** `board/development/` 有工單
**產出物：** `src/` 程式碼、`src/*.test.js`、`versions/TASK-XXX/before|after/`
**工單流向：** `development/` → `review/`

---

## 🔍 Review Agent（Code Reviewer）
**觸發條件：** `board/review/` 有工單
**產出物：** 工單備注（PASS/FAIL + 問題清單）
**工單流向：** PASS → `testing/` / FAIL → `development/`

---

## 🧪 QA Agent（測試工程師）
**觸發條件：** `board/testing/` 有工單
**產出物：** 測試結果備注、`board/backlog/BUG-XXX.md`（有 Bug 時）
**工單流向：** PASS → `done/` / FAIL → `blocked/`

---

## 🚀 DevOps Agent（部署工程師）
**觸發條件：** `board/done/` 有工單
**產出物：** `docs/TASK-XXX-delivery.md`
**工單流向：** 終點（工單留在 `done/`）

---

## 手動模式（需要時使用）

若需要單獨執行某個角色：
```
/agent ba-agent      → 只執行需求分析
/agent dev-agent     → 只執行開發
```
