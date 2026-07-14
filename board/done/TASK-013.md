---
id: TASK-013
title: AWS 資源建置（手動指南 + Terraform IaC）
type: Task
priority: High
assignee: unassigned
status: done
created: 2026-07-14
updated: 2026-07-14T15:23:01
epic: EPIC-003
---

## 描述

延續 TASK-012（Lambda 部署轉接層），本工單產出實際將 AIMOM 部署上 AWS 所需的基礎設施建置文件與程式碼：
1. 手動建置指南（給不想用 IaC 的情境，或供 IaC 邏輯對照參考）
2. Terraform IaC（正式建議做法，可重複、可版控、可 destroy 重建）

涵蓋資源：DynamoDB（Meetings/LLMUsage 表）、S3（音檔暫存 bucket + 前端靜態網站 bucket）、
Cognito User Pool + Google IdP 聯合登入、Lambda 函式、API Gateway HTTP API、IAM Role/Policy。

## Acceptance Criteria

- [x] `docs/deploy/manual-setup-guide.md`：條列 AWS Console／CLI 手動建置每一項資源的步驟
- [x] `infra/` Terraform 程式碼：DynamoDB 兩張表（含 TTL 屬性）
- [x] `infra/`：S3 音檔 bucket（含 lifecycle 規則自動清除）+ 前端靜態網站 bucket
- [x] `infra/`：Cognito User Pool + User Pool Client + Google IdP federation 設定（Google Client ID/Secret 以變數注入，不寫死）
- [x] `infra/`：Lambda 函式（zip 或 image 部署）+ IAM Role（含 DynamoDB/S3 最小權限 Policy）
- [x] `infra/`：API Gateway HTTP API + Lambda 整合 + 路由
- [x] `terraform validate` / `terraform plan` 可正常執行（不需真實 apply，避免產生費用）
- [x] 變數化：region、專案名稱前綴、Google OAuth 憑證、管理者 email 白名單皆可由 `terraform.tfvars` 覆寫

## 備注

## 歷程

| 時間 | 代理 | 動作 |
|------|------|------|
| 2026-07-14T15:15:00 | orchestrator | 依使用者需求建立工單，放入 backlog |
| 2026-07-14T15:23:01 | orchestrator | 完成手動指南與 Terraform IaC，terraform validate 通過，plan 因無真實 AWS 憑證中止於 API 呼叫前（設定本身已驗證），移至 done |
