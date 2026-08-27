# TASK-011 交付報告 — 管理者成本/用量儀表板

## 完成內容

- `src/usage.py`：`record_llm_usage()` 寫入 DynamoDB `LLMUsage` 表（含 Decimal 轉換以符合 DynamoDB 型別限制）、`estimate_cost()` 依定價表估算成本、`summarize_usage()` 依日期/使用者彙總
- `src/summarize.py`：每次 LLM 呼叫後記錄用量（`try/except` 保護，記錄失敗不影響摘要功能主流程）
- `src/admin.py`：`GET /api/admin/usage`，僅 `role=admin`（`require_admin` 依賴）可存取，回傳彙總資料，非管理者 403
- `app.py`：掛載 `admin_router`
- `frontend/index.html`：新增「管理者儀表板」按鈕（僅登入為管理者時顯示，透過 `/api/me` 判斷），彈出頁面顯示依日期/使用者彙總表格
- `tests/test_usage_admin.py`：6 項測試，涵蓋成本估算、彙總計算、非管理者 403、管理者 200

## 測試結果

```
36 passed（全專案，含既有 31 項）
```

## 驗收對應（PRD FR-11）

| AC | 狀態 |
|----|------|
| 記錄每次呼叫的 token 用量/成本 | ✅ `record_llm_usage` |
| 成本估算依各引擎定價 | ✅ 定價表寫死於 `usage.py`，可調整 |
| `GET /api/admin/usage` 僅管理者可存取 | ✅ `require_admin` |
| 非管理者 403 | ✅ 測試覆蓋 |
| 前端管理者儀表板頁籤 | ✅ 僅管理者可見/可存取 |
| 單元測試 | ✅ 6 項通過 |

## 已知限制

- DynamoDB 不支援原生 float，成本欄位以 `Decimal` 儲存，讀出時轉回 `float` 供彙總運算
- 定價表為靜態常數，若供應商調整定價需手動更新程式碼（未接外部定價 API）
