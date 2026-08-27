# TASK-009 系統設計 — 會議紀錄歷史（DynamoDB）

## 架構說明

新增 `db.py` 封裝 DynamoDB `Meetings` 表存取（透過 `boto3.resource("dynamodb")`）。
Table 名稱、region 皆讀取 `config.py`；本機/CI 測試使用 `moto` 模擬 DynamoDB，不需真實 AWS 帳號。

保留 14 天採 **DynamoDB 原生 TTL**：寫入時計算 `expires_at`（epoch seconds = 現在 + `MEETING_RETENTION_DAYS` 天），
並在建表時將該屬性設為 TTL attribute（本機測試建表時同步設定）。

使用者隔離：PK 為 `user_id`（來自 TASK-008 驗證後的 email），查詢/刪除皆先過濾 `user_id`，
確保使用者 A 無法動到使用者 B 的資料（找不到就回 404，不透露資料是否存在）。

## 模組清單

| 模組 | 檔案 | 職責 |
|------|------|------|
| DynamoDB 存取層 | `src/db.py` | 建表（測試用）、`put_meeting`、`list_meetings`、`get_meeting`、`delete_meeting` |
| API 路由 | `src/history.py` | `/api/meetings` 系列端點（保留/查詢/刪除） |

## DB Schema

```
Table: Meetings (config.DYNAMODB_MEETINGS_TABLE)
  PK: user_id (S)
  SK: meeting_id (S)
  屬性:
    title (S)
    created_at (S, ISO8601)
    transcript_text (S)
    minutes_json (S, JSON 字串)
    expires_at (N, epoch seconds)  ← TTL 屬性
```

## 注意事項

- 音檔刪除沿用 TASK-006 既有邏輯（AssemblyAI transcript 刪除 + 本地暫存刪除），本工單只處理「文字紀錄」的保存
- `discard`（不保留）不寫入 DynamoDB，前端顯示完當下結果後即結束，不留痕跡
- `MEETING_RETENTION_DAYS` 可設定，預設 14
