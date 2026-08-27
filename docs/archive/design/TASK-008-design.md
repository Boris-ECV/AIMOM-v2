# TASK-008 系統設計 — 登入與角色驗證

## 架構說明

FastAPI 以 dependency injection 方式在每個受保護路由前驗證 `Authorization: Bearer <JWT>`。
JWT 由 Amazon Cognito User Pool（聯合 Google IdP）簽發，後端透過 Cognito 的 JWKS 端點取得公鑰驗證簽章。
為降低外部相依，JWKS 的取得與快取封裝在 `auth.py` 的 `_get_jwks()`，測試時可 mock 掉。

角色判定：解析 JWT payload 拿到 `email` claim，比對環境變數 `ADMIN_EMAILS`（逗號分隔）決定 `role`。

## 模組清單

| 模組 | 檔案 | 職責 |
|------|------|------|
| 驗證 | `src/auth.py` | JWT 驗證、白名單角色判定、`get_current_user` FastAPI dependency、`require_admin` dependency |
| 設定 | `src/config.py` | 新增 `COGNITO_REGION` / `COGNITO_USER_POOL_ID` / `COGNITO_APP_CLIENT_ID` / `ADMIN_EMAILS` |
| 路由保護 | `src/app.py` | 現有 router 加上 `Depends(get_current_user)` |

## 資料結構

```python
class CurrentUser(BaseModel):
    email: str
    role: Literal["user", "admin"]
```

## 驗證流程

1. 從 Header 取出 Bearer token，缺少 → 401
2. 解析 JWT header 取得 `kid`，向 JWKS 找對應公鑰
3. 用 `python-jose` 驗證簽章、`exp`、`iss`（需符合 Cognito issuer URL）
4. 取出 `email` claim，比對 `ADMIN_EMAILS` 決定角色
5. 任一步驟失敗 → 401 Unauthorized

## 測試策略

`_get_jwks()` 與 JWT 驗證邏輯分離，測試以自簽 RSA 金鑰模擬 Cognito 簽發流程，
避免真的呼叫 AWS，符合本機/CI 可測試性。

## 注意事項

- 本機開發/測試沒有真正的 Cognito 服務，`auth.py` 需保留可注入測試用金鑰的介面（`jwks_provider` 參數，預設呼叫真實 Cognito JWKS URL）
- 白名單管理目前用環境變數（PRD 開放問題已記錄，未來可遷移至 DynamoDB 表）
