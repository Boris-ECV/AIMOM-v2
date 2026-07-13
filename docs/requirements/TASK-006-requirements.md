# TASK-006 需求文件

## 背景

PRD v2.0 NFR-01 要求：處理完成後須呼叫 `AssemblyAI DELETE /transcript/{id}`，
確保錄音與逐字稿不留存於第三方服務。AssemblyAI 預設 72 小時後自動刪除，
但為符合嚴格隱私需求，系統應在本地清除暫存時主動觸發遠端刪除。

## 功能需求

- FR-01：`/api/transcribe` 完成後，將 AssemblyAI 回傳的 `transcript.id` 儲存於 `tmp/{job_id}/meta.json` 的 `assemblyai_transcript_id` 欄位。
- FR-02：`DELETE /api/cleanup/{job_id}` 執行時，若 `meta.json` 存在 `assemblyai_transcript_id` 且已設定 `ASSEMBLYAI_API_KEY`，呼叫 `aai.Transcript.delete(transcript_id)` 刪除遠端逐字稿。
- FR-03：AssemblyAI 遠端刪除失敗（例外）不得影響本地暫存目錄清除流程。

## 非功能需求

- NFR-01（隱私）：處理完成後，遠端不得保留逐字稿與音檔（透過主動刪除 + AssemblyAI 72 小時自動刪除雙重保障）。
- NFR-02（穩定性）：遠端刪除呼叫需以 try/except 包裹，避免第三方服務錯誤影響本地清理。

## 使用者故事

作為系統管理者，我想要在使用者結束會議紀錄處理後，系統能自動清除第三方服務上的錄音與逐字稿，
以便符合公司隱私政策，避免資料外洩風險。

## 流程說明

1. `/api/transcribe` 呼叫 AssemblyAI 完成轉錄，取得 `transcript.id`
2. 將 `transcript.id` 寫入 `tmp/{job_id}/meta.json` 的 `assemblyai_transcript_id`
3. 使用者結束使用或系統排程觸發 `DELETE /api/cleanup/{job_id}`
4. 讀取 `meta.json`，若存在 `assemblyai_transcript_id`，呼叫 AssemblyAI SDK 刪除該筆逐字稿
5. 不論遠端刪除成功與否，皆刪除本地 `tmp/{job_id}/` 暫存目錄

## 資料需求

- 輸入：`meta.json` 內的 `assemblyai_transcript_id` 欄位
- 輸出：AssemblyAI 遠端刪除呼叫結果（不回傳給使用者，僅記錄於伺服器端行為）

## 邊界條件

- `meta.json` 不存在 `assemblyai_transcript_id`（例如轉錄尚未執行過）時，跳過遠端刪除，僅清除本地目錄。
- `ASSEMBLYAI_API_KEY` 未設定時，跳過遠端刪除呼叫。
- AssemblyAI API 呼叫拋出例外時，捕捉並忽略，確保本地清除仍執行完成。

## 歷程

| 時間 | 代理 | 動作 |
|------|------|------|
| 2026-07-09T18:10:00 | orchestrator | 建立工單，放入 backlog（depends_on TASK-004） |
| 2026-07-13T12:00:00 | ba-agent | 需求分析完成，撰寫需求文件；移動工單至 design/ |
