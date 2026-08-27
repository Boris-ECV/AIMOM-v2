# TASK-009 交付報告 — 會議紀錄歷史（DynamoDB）

## 完成內容

- `src/db.py`：DynamoDB `Meetings` 表存取層（boto3），提供 `put_meeting` / `list_meetings` / `get_meeting` / `delete_meeting`，含 14 天 TTL 計算與自動建表（本機/測試用）
- `src/history.py`：5 個新端點，皆需登入
  - `POST /api/meetings/{job_id}/keep` — 保留本次會議紀錄
  - `POST /api/meetings/{job_id}/discard` — 不保留
  - `GET /api/meetings` — 列出自己的（未過期）歷史紀錄
  - `GET /api/meetings/{meeting_id}` — 取得單筆完整內容
  - `DELETE /api/meetings/{meeting_id}` — 手動提前刪除
- `app.py`：掛載 `history_router`
- `tests/test_history.py`：7 項測試，使用 `moto` 模擬 DynamoDB，涵蓋保留/捨棄/查詢/刪除/跨使用者隔離

## 測試結果

```
27 passed (全專案，含既有 20 項)
```

## 驗收對應（PRD FR-09）

| AC | 狀態 |
|----|------|
| 每次轉譯完成可選擇保留或刪除 | ✅ keep/discard 端點 |
| 僅保留的留在歷史紀錄 | ✅ discard 不寫入 DB |
| 最多保存 14 天 | ✅ DynamoDB TTL (`MEETING_RETENTION_DAYS`) |
| 使用者只能看到自己的 | ✅ user_id=email 隔離，測試覆蓋 |
| 尚未到期也可手動刪除 | ✅ DELETE 端點 |

## 已知限制 / 後續事項

- 音檔本身刪除沿用既有暫存清理邏輯，本工單僅處理文字紀錄的保存；後續 TASK-012（Lambda）會將暫存改為 S3 生命週期規則
- 正式環境 DynamoDB 表由 IaC（如 CDK/Terraform，於 TASK-012 決定）建立，`ensure_meetings_table_exists()` 僅供本機/測試使用
