# TASK-008 交付報告

**交付時間：** 2026-07-13T18:55:00
**功能：** 登入與角色驗證（FR-08）— Google OAuth / Cognito JWT + 白名單管理者

## 完成功能摘要

- 新增 `src/auth.py`：`verify_token()` 驗證 Cognito 簽發的 JWT（透過 JWKS 公鑰驗簽、檢查 `iss`/`aud`/`exp`），`get_current_user` / `require_admin` 兩個 FastAPI dependency
- 白名單角色判定：email 存在於環境變數 `ADMIN_EMAILS`（逗號分隔，不分大小寫）→ `role=admin`
- `src/config.py` 新增 `COGNITO_REGION`/`COGNITO_USER_POOL_ID`/`COGNITO_APP_CLIENT_ID`/`ADMIN_EMAILS`
- `src/app.py`：新增 `GET /api/me`；既有 5 個 router（upload/transcribe/diarize/summarize/progress）全部加上 `Depends(get_current_user)`
- `src/tests/conftest.py`：提供 autouse fixture 覆寫驗證，既有測試不需自組 JWT 即可運作

## 版本資訊
- Before：`versions/TASK-008/before/`（config.py, app.py）
- After：`versions/TASK-008/after/`（config.py, app.py, auth.py）
- 新增檔案：`src/auth.py`、`src/tests/test_auth.py`、`src/tests/conftest.py`

## 模擬部署步驟
1. ✅ 程式碼驗證（pytest 全數通過）
2. ✅ 單元測試執行：20/20 通過（含 5 個新增 auth 測試）
3. ✅ 模擬部署完成（實際 Lambda 部署待 TASK-012）

## QA 結果
✅ 所有 Acceptance Criteria 通過

## 已知限制／後續事項
- 白名單目前僅支援環境變數管理，PRD 已記錄未來可遷移至 DynamoDB 表由管理者自行維護
- 本機/CI 測試以自簽 RSA 金鑰模擬 Cognito JWKS，尚未串接真實 AWS Cognito（需 TASK-012 實際部署後驗證）
