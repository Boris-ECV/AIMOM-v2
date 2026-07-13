---
id: TASK-003
title: 前端 Web 介面 — 上傳、進度、結果編輯與匯出
type: Story
priority: High
assignee: ba-agent
status: backlog
created: 2026-07-09
updated: 2026-07-09T12:55:00
epic: EPIC-001
prd: docs/requirements/TASK-001-prd.md
depends_on: TASK-002
---

## 描述

實作 Web 前端介面，提供錄音上傳、處理進度顯示、
會議紀錄結果瀏覽與 inline 編輯、Markdown 匯出功能。
前端直接呼叫 TASK-002 後端 API。

## 相關 PRD 章節

- FR-01：錄音上傳 UI（拖拽 + 點選）
- FR-05：結果瀏覽與編輯（inline edit，紀錄/逐字稿切換）
- FR-06：匯出 Markdown（下載按鈕）
- FR-03：發言人名稱手動修改
- NFR-02：進度條顯示
- NFR-04：支援現代瀏覽器

## Acceptance Criteria

- [ ] 上傳頁面：支援拖拽 + 點選，顯示檔名與大小，限制 2 小時
- [ ] 進度頁面：顯示當前處理階段（上傳/轉錄/識別/整理）與百分比
- [ ] 結果頁面：顯示摘要/Action Items/決定事項/討論重點（4 區塊）
- [ ] 逐字稿頁面：顯示帶時間戳的發言人分段逐字稿
- [ ] 發言人重命名：點擊 Speaker A/B/C 可修改為真實姓名（即時更新全部）
- [ ] Inline 編輯：會議紀錄各區塊可直接點擊編輯
- [ ] 匯出 Markdown：下載 `YYYYMMDD-meeting-notes.md`
- [ ] 響應式設計：支援桌面寬度（≥1024px）
- [ ] 錯誤處理：顯示友善錯誤訊息（上傳失敗/API 失敗等）

## 歷程

| 時間 | 代理 | 動作 |
|------|------|------|
| 2026-07-09T12:55:00 | orchestrator | 建立工單，放入 backlog |
