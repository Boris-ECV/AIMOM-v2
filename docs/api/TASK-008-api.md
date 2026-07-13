# TASK-008 API 規格

## 驗證方式（適用於全部受保護端點）

- Header: `Authorization: Bearer <Cognito JWT>`
- 缺少或驗證失敗 → `401 { "detail": "未授權，請重新登入" }`

## GET /api/me

- 說明：回傳目前登入使用者資訊（供前端判斷是否顯示管理者頁籤）
- Response 200: `{ "email": "user@example.com", "role": "user" }`
- Response 401: `{ "detail": "未授權，請重新登入" }`
