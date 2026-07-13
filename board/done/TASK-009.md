---
id: TASK-009
title: 會議紀錄歷史（FR-09）— DynamoDB 保留/刪除、14天TTL、使用者隔離
type: Story
priority: High
assignee: unassigned
status: done
created: 2026-07-13
updated: 2026-07-13T18:44:03
epic: EPIC-002
---

## 描述

依 `docs/requirements/TASK-007-prd.md` FR-09，實作會議紀錄歷史功能：處理完成後使用者可選擇保留或刪除；保留者寫入 DynamoDB `Meetings` 表並設定 14 天 TTL；使用者僅能查詢/刪除自己的紀錄；音檔一律於處理完成後刪除（前端提示）。

## Acceptance Criteria

- [x] `db.py`：封裝 DynamoDB `Meetings` 表存取（boto3 resource，PK=`user_id`，SK=`meeting_id`）
- [x] `POST /api/meetings/{job_id}/keep`：使用者選擇保留 → 寫入 DynamoDB，`expires_at` = 建立時間 + 14 天（epoch seconds，設為 TTL 屬性）
- [x] `POST /api/meetings/{job_id}/discard`：使用者選擇刪除 → 不寫入歷史紀錄（或已寫入者標記/直接刪除）
- [x] `GET /api/meetings`：列出目前登入使用者（`user_id` 來自 FR-08 驗證後的 email）自己的歷史紀錄，僅回傳未過期項目
- [x] `DELETE /api/meetings/{meeting_id}`：使用者可手動提前刪除自己的歷史紀錄
- [x] 資料隔離驗證：使用者 A 無法查詢/刪除使用者 B 的紀錄（回傳 404，不洩漏存在與否）
- [x] 音檔刪除：轉錄完成後，暫存音檔立即刪除（沿用 TASK-006 邏輯），前端顯示提示文字
- [x] 單元測試（使用 `moto` 模擬 DynamoDB）：保留寫入、查詢僅回自己的、手動刪除、跨使用者隔離、TTL 屬性正確設定

## 備注

## 歷程

| 時間 | 代理 | 動作 |
|------|------|------|
| 2026-07-13T18:31:00 | orchestrator | 由 TASK-007 PRD 拆解建立工單，放入 backlog |
| 2026-07-13T18:44:03 | orchestrator | 完成 SA/Dev/Review/QA/DevOps 全流程，27/27 測試通過，移至 done |
