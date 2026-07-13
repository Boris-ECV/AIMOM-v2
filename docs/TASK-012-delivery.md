# TASK-012 交付報告 — Lambda 部署轉接層

## 完成內容

- `src/lambda_handler.py`：`Mangum(app)` 包裝既有 FastAPI app，作為 Lambda 進入點
- `app.py`：新增 `GET /api/health` 無需登入的健康檢查端點，供 Lambda/API Gateway 探測使用
- `docs/deploy/lambda-deploy-notes.md`：完整部署設定筆記，涵蓋環境變數清單、Memory/Timeout 建議值、API Gateway HTTP API 整合注意事項、IAM 權限需求
- `tests/test_lambda_handler.py`：2 項測試，使用模擬的 API Gateway HTTP API v2 event 驗證 handler 正確路由（健康檢查 200、未知路由 404）
- `requirements.txt`：`mangum`/`boto3`/`python-docx`/`reportlab`/`python-jose[cryptography]` 已於環境建置階段加入，本工單確認齊全

## 測試結果

```
38 passed（全專案，含既有 36 項）
```

## 驗收對應（PRD NFR-05）

| AC | 狀態 |
|----|------|
| `lambda_handler.py`（Mangum 包裝） | ✅ |
| `requirements.txt` 新增部署相依套件 | ✅（已於前期環境建置階段完成） |
| 部署設定文件 | ✅ `docs/deploy/lambda-deploy-notes.md` |
| 單元測試驗證模擬 API Gateway event | ✅ 2 項通過 |

## 已知限制 / 後續事項

- 尚未撰寫實際 IaC（Terraform/CDK/SAM）樣板，僅提供設定筆記，供後續基礎設施建置參考
- 尚未實作 S3 presigned URL 直傳、AssemblyAI webhook 回呼、DynamoDB 正式建表（IaC 管理）——這些屬於實際上雲部署階段的工作，超出本次程式碼交付範圍，已於部署筆記中列出注意事項
- 前端目前仍以 `localhost:8000` 作為 API base URL，正式部署後需改為 API Gateway 端點（環境變數化）

## EPIC-002 總結

TASK-007（PRD）～ TASK-012（Lambda 轉接層）五項實作工單已全數完成並通過測試（38/38），
涵蓋 v2 版四大功能：登入（Google OAuth via Cognito）、歷史紀錄（DynamoDB + TTL + 使用者隔離）、
多格式匯出（Word/PDF/純文字）、管理者成本儀表板，並完成 AWS Lambda 部署轉接層與設定文件。
本版程式碼與文件已提交至 `Boris-ECV/AIMOM`（GitHub，private）。
