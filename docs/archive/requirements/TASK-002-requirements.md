# TASK-002 需求文件 — 後端核心服務
**建立者：** ba-agent
**建立時間：** 2026-07-09T12:56:00
**PRD 來源：** docs/requirements/TASK-001-prd.md

---

## 功能需求

### FR-01：錄音上傳端點
- `POST /api/upload/presign`、`POST /api/upload/complete`
- 前端先取得 S3 presigned URL，再直傳音檔到 S3
- 後端完成檔案驗證、建立 job、回傳 `{ job_id, filename, duration_sec, size_bytes }`
- 錯誤：格式不符（400）、超出長度（400）、伺服器錯誤（500）

### FR-02：語音轉文字端點
- `POST /api/transcribe`，Body: `{ job_id }`
- 呼叫 AssemblyAI 非同步送出與輪詢 API
- 語言設定：中英混合（繁中 + 英文）
- 結果儲存至 jobstore，回傳逐字稿片段陣列 + 全文合併字串
- 格式：`[{ start, end, text, speaker: null }]`

### FR-03：發言人識別端點
- `POST /api/diarize`，Body: `{ job_id }`
- 改由 AssemblyAI 原生 speaker diarization 完成，無需額外 pyannote
- 將逐字稿片段與說話人區段對齊，標注 `speaker: "SPEAKER_A"` 等
- 結果寫回 jobstore / transcript 資料
- **降級策略**：speaker 資訊不足時，以單一 speaker 繼續流程，不擋主流程

### FR-04：AI 整理端點
- `POST /api/summarize`，Body: `{ job_id }`
- 讀取 jobstore 中的 transcript
- 組合 Prompt，呼叫 LLM（v2.2 預設 `bedrock-proxy`，可切換 `github-models` / `openai-gpt4o` / `groq` / `gemini`）
- Prompt 要求輸出 JSON 格式：
  ```json
  {
    "meeting_info": { "date": "...", "time": "...", "location": "...", "participants": ["..."] },
    "summary": "...",
    "action_items": [{ "owner": "...", "task": "...", "due": "..." }],
    "decisions": ["..."],
    "topics": [{ "title": "...", "content": "..." }]
  }
  ```
- `meeting_info` 各欄位、`action_items` 的 `owner`/`due`：逐字稿未明確提及一律留空
  （participants 為空陣列），AI 不可自行臆測；結果頁面提供對應欄位供使用者手動填寫/修正
- `summary` 長度依會議長短彈性調整，短會議約 100-200 字，長會議可放寬至 300-500 字
- 結果儲存至 jobstore / minutes
- 回傳結構化 JSON

### FR-05：進度查詢端點
- `GET /api/status/{job_id}`
- 回傳 `{ job_id, stage, progress, message }`
- stage: `idle | uploading | transcribing | diarizing | summarizing | done | error`
- progress: 0–100

### FR-06：清理端點
- `DELETE /api/cleanup/{job_id}`
- 刪除 jobstore 資料與暫存 S3 物件
- 回傳 `{ deleted: true }`

### FR-07：設定管理
- `.env` 設定檔（不進版控）
- 欄位：
  - `ASSEMBLYAI_API_KEY`
  - `LLM_ENGINE=bedrock-proxy`（可改 `github-models` / `openai-gpt4o` / `groq` / `gemini`）
  - `LLM_MODEL=mistral.mistral-large-3-675b-instruct`
  - `BEDROCK_PROXY_BASE_URL`
  - `BEDROCK_PROXY_API_KEY`
  - `ADMIN_EMAILS`
  - `DYNAMODB_MEETINGS_TABLE`
  - `DYNAMODB_LLM_USAGE_TABLE`
  - `AUDIO_BUCKET_NAME`
  - `TMP_DIR=/tmp`

---

## 非功能需求

- Python 3.10+，框架 FastAPI（比 Flask 更易於非同步與型別提示）
- 每個端點對應單元測試（pytest）
- 進度狀態更新：各階段開始/結束時寫入 jobstore 狀態
- 錯誤處理：所有外部 API 呼叫包 try/except，回傳統一格式 `{ error: "...", code: XXX }`
- 暫存隔離：每次上傳產生 UUID job_id，避免路徑衝突

---

## 使用者故事

作為**後端使用者（前端呼叫）**，我想要呼叫 `/api/upload/presign` → `/api/upload/complete` → `/api/transcribe` → `/api/diarize` → `/api/summarize`，以便取得完整會議紀錄。

---

## 模組規劃

| 模組 | 檔案 | 職責 |
|------|------|------|
| 主應用 | `src/app.py` | FastAPI app 初始化、路由掛載 |
| 上傳模組 | `src/upload.py` | presigned URL、驗證、S3 complete |
| 轉錄模組 | `src/transcribe.py` | AssemblyAI 送出與輪詢 |
| 識別模組 | `src/diarize.py` | AssemblyAI speaker 對齊 |
| 整理模組 | `src/summarize.py` | LLM 呼叫、Prompt 組合、結果解析 |
| 設定模組 | `src/config.py` | .env 讀取、引擎切換邏輯 |
| 進度模組 | `src/progress.py` | 狀態讀寫（jobstore） |
| 狀態儲存 | `src/jobstore.py` | DynamoDB job 狀態存取 |
| 測試 | `src/tests/` | pytest 各模組測試 |
