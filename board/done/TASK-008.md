---
id: TASK-008
title: 登入與角色驗證（FR-08）— Google OAuth / Cognito JWT + 白名單管理者
type: Story
priority: High
assignee: dev-agent
status: done
created: 2026-07-13
updated: 2026-07-13T18:45:00
epic: EPIC-002
---

## 描述

依 `docs/requirements/TASK-007-prd.md` FR-08，實作全站登入驗證機制：後端驗證 Amazon Cognito 簽發的 JWT（Google 聯合登入後取得），解析出使用者 email，並依白名單（環境變數 `ADMIN_EMAILS`）判定一般使用者 / 管理者角色。所有 API（除健康檢查外）皆須經過此驗證。

## Acceptance Criteria

- [x] 提供 get_current_user FastAPI dependency：解析 Authorization header、驗證 JWT 簽章（透過 Cognito JWKS 公鑰）、iss/aud/過期時間，取得 email
- [x] 白名單判定：email 存在於 `ADMIN_EMAILS`（逗號分隔環境變數）→ `role=admin`，否則 `role=user`
- [x] 缺少/無效 token → 回傳 401
- [x] 現有 API（`/api/upload`、`/api/transcribe`、`/api/summarize`、`/api/status/*`）加上此驗證依賴
- [x] 單元測試涵蓋：合法 token 通過、過期 token 拒絕、白名單/非白名單角色判定、缺少 token 401

## 備注

✅ PASS - Dev 已實作 auth.py（JWT 驗證+白名單角色判定），app.py 全 API 加上驗證依賴，20/20 測試通過（含 5 個新增 auth 測試）。Review：邏輯正確、錯誤處理完整、無安全疑慮，通過。

✅ QA PASS - 20/20 單元測試通過，涵蓋合法/過期/未知kid token、白名單管理者判定、缺少 token 401、既有 API 加驗證後不受影響。

## 歷程

| 時間 | 代理 | 動作 |
|------|------|------|
| 2026-07-13T18:31:00 | orchestrator | 由 TASK-007 PRD 拆解建立工單，放入 backlog |
| 2026-07-13T18:32:00 | sa-agent | 完成設計，工單移至 development |
| 2026-07-13T18:40:00 | dev-agent | 實作 auth.py/config.py/app.py，撰寫測試，工單移至 review |
| 2026-07-13T18:45:00 | review-agent | Code Review 通過，工單移至 testing |
| 2026-07-13T18:50:00 | qa-agent | 測試全數通過，工單移至 done |
| 2026-07-13T18:55:00 | devops-agent | 交付報告完成，模擬部署完成 |
