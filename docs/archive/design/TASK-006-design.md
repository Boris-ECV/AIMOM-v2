# TASK-006 系統設計

## 架構說明

隱私刪除邏輯分為兩段，皆已於 TASK-004 開發階段實作：

1. **儲存階段**（`src/transcribe.py`）：AssemblyAI 轉錄完成後，將 `transcript.id`
   寫入 `tmp/{job_id}/meta.json` 的 `assemblyai_transcript_id` 欄位。
2. **刪除階段**（`src/progress.py` `cleanup()`）：清除本地暫存前，讀取 `meta.json`
   取得 `assemblyai_transcript_id`，呼叫 `aai.Transcript.delete(transcript_id)`；
   整段包在 `try/except Exception: pass` 中，確保遠端刪除失敗不影響本地清除。

## 模組清單

| 模組 | 檔案 | 職責 |
|------|------|------|
| 轉錄 | `src/transcribe.py` | 呼叫 AssemblyAI，儲存 `transcript_id` 至 meta.json |
| 清理 | `src/progress.py` | cleanup 端點：本地暫存清除 + 遠端 transcript 刪除 |

## DB Schema

不適用（以 `tmp/{job_id}/meta.json` 檔案作為 job 中繼資料儲存，非關聯式資料庫）。

`meta.json` 新增欄位：
```json
{
  "assemblyai_transcript_id": "string"
}
```

## 注意事項

- 刪除呼叫失敗（網路錯誤、逐字稿已被刪除等）一律吞掉例外，優先保證本地清理成功。
- `ASSEMBLYAI_API_KEY` 未設定時略過遠端刪除（僅本地清除），避免因設定缺漏造成清理流程中斷。
