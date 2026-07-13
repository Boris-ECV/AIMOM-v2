---
id: TASK-010
title: 多格式匯出（FR-10）— Word/PDF 後端產生、純文字前端產生
type: Story
priority: Medium
assignee: unassigned
status: done
created: 2026-07-13
updated: 2026-07-13T18:47:31
epic: EPIC-002
---

## 描述

依 `docs/requirements/TASK-007-prd.md` FR-10，新增 Word（.docx）與 PDF 匯出（後端產生），純文字匯出於前端直接產生。

## Acceptance Criteria

- [x] `export.py`：`GET /api/export/{job_id}?format=docx` 使用 `python-docx` 產生會議紀錄 Word 檔並回傳
- [x] `GET /api/export/{job_id}?format=pdf` 使用 `reportlab` 產生 PDF 並回傳，中文字型正確顯示（不出現方框字）
- [x] 匯出內容涵蓋：標題、摘要、待辦事項、決定事項、討論重點（與現有 Markdown 匯出內容一致）
- [x] 前端新增「純文字」匯出按鈕，使用 Blob 直接下載，不呼叫後端
- [x] 若 `job_id` 不存在或無會議紀錄資料 → 回傳 404
- [x] 單元測試：docx/pdf 產生成功（驗證回傳 content-type 與檔案非空）、找不到資料回 404

## 備注

## 歷程

| 時間 | 代理 | 動作 |
|------|------|------|
| 2026-07-13T18:31:00 | orchestrator | 由 TASK-007 PRD 拆解建立工單，放入 backlog |
| 2026-07-13T18:47:31 | orchestrator | 完成 SA/Dev/Review/QA/DevOps 全流程，31/31 測試通過，移至 done |
