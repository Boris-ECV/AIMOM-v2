# 設計文件 — SDLCAIP2-13 正式環境呼叫後端 API 被 CORS 政策阻擋

## 對應需求規格
G1 已核准的需求規格（本 ticket 描述）：正式環境前端（CloudFront 網址）
呼叫後端 API Gateway 時被 CORS 政策阻擋。根因與 SDLCAIP2-12 完全相同——
`.github/workflows/ci.yml` 的 `backend` job 執行 `terraform apply` 時未
注入 `infra/variables.tf` 的 `frontend_callback_urls` 變數，導致該變數
持續套用 default 值 `["http://localhost:5500"]`；此變數同時餵給
`infra/apigateway.tf:7`（API Gateway CORS `cors_configuration.
allow_origins`）與 `infra/s3.tf:27`（音檔 S3 bucket CORS
`allowed_origins`），使正式環境的 CloudFront 網址不在允許清單內、瀏覽器
CORS 預檢請求被拒。**本 ticket 的修復完全包含在
`docs/design/SDLCAIP2-12.md` 的設計與同一顆 PR/commit 內**——修好
SDLCAIP2-12（在 `backend` job 的 `terraform apply` env 區塊新增
`TF_VAR_frontend_callback_urls`/`TF_VAR_frontend_logout_urls`）即同時
修正本 ticket 描述的 CORS 問題，本 Story 不需要任何額外的 CI 或
Terraform 變更。

## 介面/API 契約
無。本 Story 不新增/變更任何對外 API、CI job 定義或 Terraform 資源——
修復內容與 SDLCAIP2-12 完全相同的一段 diff（見
`docs/design/SDLCAIP2-12.md`「介面/API 契約」章節的完整 `terraform
apply` step 內容），不在此重複貼一次；developer 實作時應與 SDLCAIP2-12
合併為同一顆 PR/commit（同一個修復，兩張票對應同一組驗收）。

## 資料模型
無新增資料模型。理由與 SDLCAIP2-12 相同：`infra/apigateway.tf`/
`s3.tf` 既有 CORS 資源定義本身不變，只是修正 CI 未注入既有變數值的
缺陷。

## 關鍵技術決策
本 Story 的技術決策與 SDLCAIP2-12 完全相同，詳見
`docs/design/SDLCAIP2-12.md`「關鍵技術決策」1-4（GitHub Variables 而非
Secrets、callback/logout 兩變數不合併、CORS 不另拆獨立變數、不修改
`infra/*.tf` 只修 CI），此處不重複展開，僅補充一點本 Story 特有的
驗收角度：

1. **驗證方式以 API Gateway/S3 CORS 回應標頭為準，而非只驗證 Cognito
   登入流程。**
   理由：SDLCAIP2-12 的驗收聚焦在 Cognito callback/logout 導回是否
   正確，本 ticket的驗收聚焦在瀏覽器對 API Gateway 端點與 S3
   presigned URL 的請求是否通過 CORS 預檢（`Access-Control-Allow-
   Origin` 標頭是否含正式環境 CloudFront 網址）——兩者是同一組
   `TF_VAR_frontend_callback_urls` 注入後的兩個不同下游效果，developer
   實作後應在 G2 分別對兩個驗收角度各驗證一次，而非只驗證其中一項就
   視為兩張票皆通過。

## 開放設計問題（定稿時必須為空）
無。
