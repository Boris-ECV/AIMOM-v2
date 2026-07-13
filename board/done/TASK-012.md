---
id: TASK-012
title: Lambda 部署轉接層（NFR-05）— Mangum Handler + 部署設定
type: Task
priority: Medium
assignee: unassigned
status: done
created: 2026-07-13
updated: 2026-07-13T18:54:59
epic: EPIC-002
---

## 描述

依 `docs/requirements/TASK-007-prd.md` NFR-05，讓現有 FastAPI app 可在 AWS Lambda 上執行，透過 `Mangum` 包裝既有 `app.py`，不需重寫框架。

## Acceptance Criteria

- [x] 新增 `src/lambda_handler.py`：`from mangum import Mangum; from app import app; handler = Mangum(app)`
- [x] `requirements.txt` 新增 `mangum`、`boto3`、`python-docx`、`reportlab`、`python-jose[cryptography]`（JWT 驗證用）
- [x] 新增部署設定文件（`docs/deploy/lambda-deploy-notes.md`）：記錄環境變數清單（DynamoDB 表名、Cognito User Pool 資訊、ADMIN_EMAILS 等）、Lambda timeout/memory 建議值、API Gateway 整合注意事項
- [x] 單元測試：驗證 `lambda_handler.handler` 可正確處理一個模擬的 API Gateway event（呼叫 `/docs` 或健康檢查路由）並回傳 200

## 備注

## 歷程

| 時間 | 代理 | 動作 |
|------|------|------|
| 2026-07-13T18:31:00 | orchestrator | 由 TASK-007 PRD 拆解建立工單，放入 backlog |
| 2026-07-13T18:54:59 | orchestrator | 完成 SA/Dev/Review/QA/DevOps 全流程，38/38 測試通過，移至 done。EPIC-002 全部 5 項工單完成 |
