# TASK-009 API 規格

所有端點皆需登入（見 TASK-008），`user_id` 一律取自驗證後的 email。

## POST /api/meetings/{job_id}/keep

- 說明：使用者選擇保留本次會議紀錄，寫入 DynamoDB 並設定 14 天 TTL
- Response 200: `{ "meeting_id": "...", "expires_at": "2026-07-27T18:30:00" }`
- Response 404: 找不到該 job 的 minutes 資料

## POST /api/meetings/{job_id}/discard

- 說明：使用者選擇不保留，僅回應成功，不寫入歷史紀錄
- Response 200: `{ "status": "discarded" }`

## GET /api/meetings

- 說明：列出目前登入使用者自己的歷史紀錄（未過期項目）
- Response 200: `{ "meetings": [ { "meeting_id", "title", "created_at", "expires_at" }, ... ] }`

## GET /api/meetings/{meeting_id}

- 說明：取得單筆會議紀錄完整內容（含逐字稿與會議紀錄 JSON）
- Response 200: `{ "meeting_id", "title", "transcript_text", "minutes", "expires_at" }`
- Response 404: 不存在或不屬於目前使用者

## DELETE /api/meetings/{meeting_id}

- 說明：使用者手動提前刪除自己的歷史紀錄
- Response 200: `{ "status": "deleted" }`
- Response 404: 不存在或不屬於目前使用者
