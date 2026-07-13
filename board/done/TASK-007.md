---
id: TASK-007
title: 需求訪談與 PRD 定義 — v2 雲端化擴充（歷史紀錄／多格式匯出／登入／成本儀表板）
type: Story
priority: High
assignee: unassigned
status: done
created: 2026-07-13
updated: 2026-07-13T18:31:00
epic: EPIC-002
---

## 描述

延續 MVP（poc-sdlc-copilot2，AssemblyAI + 可切換 LLM 引擎）之上，針對「正式上線於 AWS Lambda 雲端環境、小團隊低成本使用」的目標，定義 v2 版 PRD。

範圍涵蓋：會議紀錄歷史保存與到期清理、多格式匯出（Word/PDF/純文字）、Google 第三方登入、管理者成本/用量儀表板，以及支撐這些功能的 AWS Serverless 架構（Lambda + API Gateway + DynamoDB + S3 + Cognito）。

## Acceptance Criteria

- [x] 完成需求訪談（涵蓋：歷史紀錄保存規則、匯出格式與產生位置、登入機制、角色權限、雲端部署架構限制）
- [x] 產出 PRD 文件（docs/requirements/TASK-007-prd.md）
- [x] PRD 包含：背景與目標、目標用戶（含管理者角色）、核心功能需求（FR）、非功能需求（NFR，含 AWS 架構選型）、資料模型雛形、MVP 範圍界定、開放問題

## 備注

**BA Agent 訪談摘要（2026-07-13T18:15:00）：**
- 訪談涵蓋 7 輪對話：歷史紀錄規則、匯出方案比較（前端 vs 後端）、登入與角色、AWS Lambda 部署限制、資料庫選型（DynamoDB vs SQLite on S3/EFS）
- 產出 PRD v1.0（本專案 AIMOM 首版）：4 大功能方向 + AWS Serverless 架構決策
- 關鍵決策：
  - 歷史紀錄僅保留使用者選擇「保留」的項目，最長 14 天（DynamoDB TTL 自動清理），音檔一律處理完即刪
  - 匯出：純文字前端產生；Word/PDF 後端產生（python-docx + reportlab）
  - 全站強制 Google OAuth 登入（Amazon Cognito + Google IdP），角色以白名單 email 認定管理者
  - 使用者僅能查看自己的歷史紀錄；管理者可看 LLM 成本/用量儀表板
  - 不做 Zoom/Teams 整合、不做批次上傳
  - 部署架構：Lambda（Mangum 包裝現有 FastAPI）+ API Gateway + DynamoDB + S3（音檔 Presigned Upload + Lifecycle）+ Cognito + AssemblyAI Webhook（取代輪詢）+ S3/CloudFront 前端
- PRD 文件：`docs/requirements/TASK-007-prd.md`

## 歷程

| 時間 | 代理 | 動作 |
|------|------|------|
| 2026-07-13T18:15:00 | orchestrator | 建立工單，放入 backlog |
| 2026-07-13T18:15:30 | ba-agent | 接單，開始需求訪談 |
| 2026-07-13T18:30:00 | ba-agent | 訪談完成，PRD 產出，工單移至 design |
| 2026-07-13T18:31:00 | orchestrator | PRD 定義型工單（比照 TASK-001），拆解為 TASK-008~012 實作工單後移至 done |
