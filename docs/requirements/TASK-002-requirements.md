# TASK-002 需求文件 — 後端核心服務
**建立者：** ba-agent
**建立時間：** 2026-07-09T12:56:00
**PRD 來源：** docs/requirements/TASK-001-prd.md

---

## 功能需求

### FR-01：錄音上傳端點
- `POST /api/upload`
- 接受 multipart/form-data，欄位 `file`
- 驗證格式（MP3/WAV/M4A）與時長（≤ 2 小時）
- 儲存至 `tmp/{job_id}/audio.{ext}`
- 回傳 `{ job_id, filename, duration_sec, size_bytes }`
- 錯誤：格式不符（400）、超出長度（400）、伺服器錯誤（500）

### FR-02：語音轉文字端點
- `POST /api/transcribe`，Body: `{ job_id }`
- 呼叫 Whisper API（`openai.audio.transcriptions.create`）
- 語言設定：`zh`（支援中英混合）
- 長音訊（>25MB）自動分段（每段 ≤ 24MB），轉錄後合併時間戳
- 結果儲存至 `tmp/{job_id}/transcript.json`
- 格式：`[{ start, end, text, speaker: null }]`
- 回傳逐字稿片段陣列 + 全文合併字串

### FR-03：發言人識別端點
- `POST /api/diarize`，Body: `{ job_id }`
- 呼叫 pyannote.audio pipeline（`pyannote/speaker-diarization-3.1`）
- 將逐字稿片段與說話人區段對齊，標注 `speaker: "SPEAKER_00"` 等
- 結果覆寫更新 `tmp/{job_id}/transcript.json`
- **降級策略**：pyannote 不可用時，回傳 `speaker: "SPEAKER_00"` 全部同一人，不擋主流程

### FR-04：AI 整理端點
- `POST /api/summarize`，Body: `{ job_id }`
- 讀取 `tmp/{job_id}/transcript.json`
- 組合 Prompt，呼叫 LLM（預設 GPT-4o）
- Prompt 要求輸出 JSON 格式：
  ```json
  {
    "summary": "...",
    "action_items": [{ "owner": "...", "task": "...", "due": "..." }],
    "decisions": ["..."],
    "topics": [{ "title": "...", "content": "..." }]
  }
  ```
- 結果儲存至 `tmp/{job_id}/minutes.json`
- 回傳結構化 JSON

### FR-05：進度查詢端點
- `GET /api/status/{job_id}`
- 回傳 `{ job_id, stage, progress, message }`
- stage: `idle | uploading | transcribing | diarizing | summarizing | done | error`
- progress: 0–100

### FR-06：清理端點
- `DELETE /api/cleanup/{job_id}`
- 刪除 `tmp/{job_id}/` 整個目錄
- 回傳 `{ deleted: true }`

### FR-07：設定管理
- `.env` 設定檔（不進版控）
- 欄位：
  - `OPENAI_API_KEY`
  - `WHISPER_ENGINE=openai-whisper`（可改 `whisper-local`）
  - `LLM_ENGINE=openai-gpt4o`（可改 `google-gemini` / `anthropic-claude`）
  - `HUGGINGFACE_TOKEN`（pyannote 需要）
  - `TMP_DIR=./tmp`
  - `MAX_AUDIO_HOURS=2`

---

## 非功能需求

- Python 3.10+，框架 FastAPI（比 Flask 更易於非同步與型別提示）
- 每個端點對應單元測試（pytest）
- 進度狀態更新：各階段開始/結束時寫入 `tmp/{job_id}/status.json`
- 錯誤處理：所有外部 API 呼叫包 try/except，回傳統一格式 `{ error: "...", code: XXX }`
- 暫存隔離：每次上傳產生 UUID job_id，避免路徑衝突

---

## 使用者故事

作為**後端使用者（前端呼叫）**，我想要呼叫 `/api/upload` → `/api/transcribe` → `/api/diarize` → `/api/summarize`，以便取得完整會議紀錄。

---

## 模組規劃

| 模組 | 檔案 | 職責 |
|------|------|------|
| 主應用 | `src/app.py` | FastAPI app 初始化、路由掛載 |
| 上傳模組 | `src/upload.py` | 接收檔案、驗證、存暫存 |
| 轉錄模組 | `src/transcribe.py` | Whisper API 呼叫、分段合併 |
| 識別模組 | `src/diarize.py` | pyannote pipeline、對齊逐字稿 |
| 整理模組 | `src/summarize.py` | LLM 呼叫、Prompt 組合、結果解析 |
| 設定模組 | `src/config.py` | .env 讀取、引擎切換邏輯 |
| 進度模組 | `src/progress.py` | 狀態讀寫（status.json） |
| 測試 | `src/tests/` | pytest 各模組測試 |
