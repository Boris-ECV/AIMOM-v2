---
id: TASK-011
title: 管理者成本/用量儀表板（FR-11）— LLM 用量追蹤 + 管理者專屬 API
type: Story
priority: Medium
assignee: unassigned
status: backlog
created: 2026-07-13
updated: 2026-07-13T18:31:00
epic: EPIC-002
---

## 描述

依 `docs/requirements/TASK-007-prd.md` FR-11，記錄每次 LLM 摘要呼叫的 token 用量與估算成本，並提供僅管理者可存取的彙總 API/儀表板頁面。

## Acceptance Criteria

- [ ] `usage.py`：`record_llm_usage()` 於 `summarize.py` 呼叫 LLM 後寫入 DynamoDB `LLMUsage` 表（PK=`date`，SK=`usage_id`），欄位含 engine/model/input_tokens/output_tokens/estimated_cost/user_id/meeting_id
- [ ] 成本估算：依各引擎 token 單價換算（GitHub Models/OpenAI $2.50-$10 / M tokens、Groq、Gemini 依各自定價），寫死於設定表方便未來調整
- [ ] `GET /api/admin/usage`：僅 `role=admin` 可存取（依賴 TASK-008 的驗證），回傳依日期/使用者彙總的用量與成本
- [ ] 非管理者呼叫此 API → 403
- [ ] 前端新增「管理者儀表板」頁籤（僅登入為管理者時顯示/可存取）
- [ ] 單元測試：用量寫入正確、彙總計算正確、非管理者 403

## 備注

## 歷程

| 時間 | 代理 | 動作 |
|------|------|------|
| 2026-07-13T18:31:00 | orchestrator | 由 TASK-007 PRD 拆解建立工單，放入 backlog |
