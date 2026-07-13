---
id: TASK-005
title: 前端進度顯示調整 — 對應 AssemblyAI 非同步流程
type: Story
priority: Medium
assignee: dev-agent
status: design
created: 2026-07-09
updated: 2026-07-13T11:52:00
epic: EPIC-001
depends_on: TASK-004
prd: docs/requirements/TASK-001-prd.md (v2.0)
---

## BA 分析摘要

需求文件已完成：`docs/requirements/TASK-005-requirements.md`。
核心問題確認：`doUpload()` 主流程已符合 v2.0（僅呼叫 transcribe→summarize），
但 `loadResults()` 仍殘留呼叫 `/api/diarize`，需由 Dev Agent 修正為使用
transcribe 階段已取得的 segments，不再重複呼叫。

## 背景

TASK-004 將後端改為 AssemblyAI 後，處理流程從：
- `上傳 → 轉錄 → 識別 → 整理`（4 個獨立 API）

改為：
- `上傳 → [AssemblyAI：轉錄+識別同步進行] → 整理`（3 個階段）

前端需對應調整進度顯示與 API 呼叫順序。

## 範圍

### 需修改的檔案

| 檔案 | 改動 |
|------|------|
| `src/frontend/index.html` | 調整進度階段顯示（3 階段）、更新 callStep 流程 |

### 進度階段變更

| v1.0（舊） | v2.0（新） |
|-----------|-----------|
| 上傳完成（10%） | 上傳完成（10%） |
| 語音轉文字（40%） | AssemblyAI 處理中（轉錄+識別）（25%→75%） |
| 發言人識別（65%） | ← 合併至上方 |
| AI 整理（100%） | AI 整理（100%） |

### 前端呼叫流程調整

```js
// v1.0
await callStep('/api/transcribe');
await callStep('/api/diarize');      // ← 移除此步驟
await callStep('/api/summarize');

// v2.0
await callStep('/api/transcribe');   // 內含說話者識別
await callStep('/api/summarize');
```

### AssemblyAI 進度輪詢

AssemblyAI 處理時間較長（非同步），後端 /api/status 需回傳 AssemblyAI 的 `status`：
- `queued` → 25%
- `processing` → 50%
- `completed` → 75%

前端輪詢邏輯不需改動（已有 setInterval），只需調整進度顯示文字與百分比對應。

## Acceptance Criteria

- [x] 進度頁面顯示 3 個階段（移除獨立的「發言人識別」階段）
- [x] 第 2 階段顯示 AssemblyAI 處理進度（queued/processing/completed）
- [x] callStep 不再呼叫 /api/diarize
- [x] 進度百分比對應更新：上傳10% → AssemblyAI處理25-75% → AI整理100%
- [x] 所有現有功能（重命名、編輯、匯出）不受影響

## Review 備注

✅ PASS - `loadResults()` 已改用 `state.segments`（於 `doUpload()` 呼叫 `/api/transcribe` 時存入），
不再呼叫 `/api/diarize`；3 階段進度顯示與百分比對應已於前次變更完成並經確認；
發言人重命名/Inline 編輯/匯出等既有功能程式碼未受影響。

## QA 測試案例

| # | 案例 | 類型 | 結果 |
|---|------|------|------|
| 1 | 上傳後依序呼叫 transcribe → summarize，不呼叫 diarize | 正向 | ✅ Pass（程式碼追蹤確認 doUpload 僅 2 次 callStep） |
| 2 | transcribe 回傳 segments 存入 state.segments | 正向 | ✅ Pass |
| 3 | loadResults() 未含任何 `/api/diarize` fetch 呼叫 | 正向 | ✅ Pass（grep 確認全檔僅剩註解提及） |
| 4 | segments 為空陣列時逐字稿頁面不報錯 | 邊界 | ✅ Pass（`state.segments || []` 防呆） |
| 5 | 發言人重命名/Inline 編輯/匯出既有邏輯未變動 | 回歸 | ✅ Pass（diff 確認未觸及相關函式） |

**註：** 本執行環境未安裝 Python/pytest，本工單僅涉及前端 HTML/JS（專案慣例無前端自動化測試框架，
與 TASK-003 一致），故以程式碼靜態追蹤與人工邏輯驗證取代自動化測試執行。

## 歷程

| 時間 | 代理 | 動作 |
|------|------|------|
| 2026-07-09T18:10:00 | orchestrator | 建立工單，放入 backlog（depends_on TASK-004） |
| 2026-07-13T11:52:00 | ba-agent | 需求分析完成，撰寫 docs/requirements/TASK-005-requirements.md；移動工單至 design/ |
| 2026-07-13T11:53:00 | sa-agent | 設計完成，撰寫 docs/design/TASK-005-design.md（純前端修正）；移動工單至 development/ |
| 2026-07-13T11:55:00 | dev-agent | 修正 `doUpload()` 保存 transcribe segments 至 state；`loadResults()` 改用 state.segments，移除 `/api/diarize` 呼叫；移動工單至 review/ |
| 2026-07-13T11:56:00 | review-agent | ✅ PASS - 全部 5 項 AC 通過；移動工單至 testing/ |
| 2026-07-13T11:57:00 | qa-agent | ✅ QA PASS - 靜態程式碼驗證通過（本環境未安裝 python，改以人工邏輯追蹤驗證 doUpload/loadResults 呼叫流程）；移動工單至 done/ |
| 2026-07-13T11:58:00 | devops-agent | 🚀 已部署 - 交付報告 docs/TASK-005-delivery.md 建立完成 |
