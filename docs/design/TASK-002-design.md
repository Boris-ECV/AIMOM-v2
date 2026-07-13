# TASK-002 系統設計 — 後端核心服務
**建立者：** sa-agent | **時間：** 2026-07-09T12:58:00

---

## 架構說明

採用 **FastAPI** 非同步框架，各功能拆成獨立模組，透過 `job_id`（UUID）隔離每次處理。
暫存資料存於 `tmp/{job_id}/`，處理完畢後由前端呼叫 `/api/cleanup` 刪除。

```
src/
├── app.py          ← FastAPI 主程式，掛載所有 router
├── config.py       ← .env 讀取、引擎工廠函式
├── upload.py       ← 上傳驗證與暫存管理
├── transcribe.py   ← Whisper 呼叫、分段合併
├── diarize.py      ← pyannote 發言人識別
├── summarize.py    ← LLM Prompt 組合與呼叫
├── progress.py     ← 進度狀態讀寫
├── models.py       ← Pydantic request/response models
└── tests/
    ├── test_upload.py
    ├── test_transcribe.py
    ├── test_diarize.py
    ├── test_summarize.py
    └── test_progress.py
```

---

## 模組設計

### app.py
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
# 掛載 router：upload / transcribe / diarize / summarize / status / cleanup
```

### config.py
- 讀取 `.env`（python-dotenv）
- `get_whisper_client()` → 依 `WHISPER_ENGINE` 回傳對應 client
- `get_llm_client()` → 依 `LLM_ENGINE` 回傳對應 client
- 支援引擎：
  - Whisper：`openai-whisper`（預設）、`whisper-local`
  - LLM：`openai-gpt4o`（預設）、`google-gemini`、`anthropic-claude`

### upload.py
- 驗證副檔名（.mp3 / .wav / .m4a）
- 驗證時長（用 `mutagen` 或 `ffprobe` 讀取 metadata）
- 產生 `job_id = uuid4()`
- 建立 `tmp/{job_id}/` 目錄
- 寫入 `tmp/{job_id}/meta.json`（filename, duration, size, created_at）
- 儲存音訊至 `tmp/{job_id}/audio.{ext}`

### transcribe.py
- 讀取 `tmp/{job_id}/audio.{ext}`
- 若檔案 > 24MB → 用 `pydub` 切成 10 分鐘一段
- 逐段呼叫 `openai.audio.transcriptions.create(model="whisper-1", language="zh")`
- 合併所有 segment，修正時間偏移
- 輸出格式：
  ```json
  [{ "start": 0.0, "end": 5.2, "text": "...", "speaker": null }]
  ```
- 儲存至 `tmp/{job_id}/transcript.json`

### diarize.py
- 讀取 `tmp/{job_id}/audio.{ext}`
- 呼叫 `pyannote.audio` Pipeline（需 HuggingFace token）
- 輸出說話人時間區間：`[(start, end, "SPEAKER_00"), ...]`
- 將 transcript segments 與說話人時間對齊（最大重疊原則）
- 更新 transcript.json 中每個 segment 的 `speaker` 欄位
- 降級：`PYANNOTE_ENABLED=false` 時跳過，所有 speaker 設為 `"SPEAKER_00"`

### summarize.py
- 讀取 transcript.json，組合成逐字稿文字
- System Prompt（繁體中文回應）：
  ```
  你是會議記錄助手。根據以下逐字稿，輸出 JSON 格式的會議紀錄，
  包含：summary（摘要）、action_items（待辦，含 owner/task/due）、
  decisions（決定事項陣列）、topics（討論議題，含 title/content）。
  使用繁體中文回應。
  ```
- 呼叫 LLM，解析 JSON 回應
- 儲存至 `tmp/{job_id}/minutes.json`

### progress.py
- 讀/寫 `tmp/{job_id}/status.json`
- 格式：`{ stage, progress, message, updated_at }`
- `update_progress(job_id, stage, progress, message)` 工具函式

---

## API 規格

詳見 `docs/api/TASK-002-api.md`

---

## 資料流

```
POST /upload
  → tmp/{job_id}/audio.mp3
  → tmp/{job_id}/meta.json
  → status: { stage: "uploaded", progress: 10 }

POST /transcribe
  → [分段] → Whisper API × N
  → tmp/{job_id}/transcript.json
  → status: { stage: "transcribed", progress: 40 }

POST /diarize
  → pyannote → 對齊
  → transcript.json 更新 speaker 欄位
  → status: { stage: "diarized", progress: 65 }

POST /summarize
  → GPT-4o
  → tmp/{job_id}/minutes.json
  → status: { stage: "done", progress: 100 }
```

---

## 依賴套件

```
fastapi>=0.110
uvicorn
python-dotenv
openai>=1.0
pydub          ← 音訊分段
mutagen        ← 讀取音訊 metadata
pyannote.audio ← 發言人識別
pytest
httpx          ← FastAPI 測試用
```

---

## 注意事項

1. pyannote.audio 需 HuggingFace token，須接受 model 授權條款
2. 長音訊分段後，時間戳偏移需累加，確保合併後連貫
3. GPT-4o 可能無法嚴格回傳 JSON，需 try/except 解析並 fallback 純文字
4. `tmp/` 目錄不進版控（加入 .gitignore）
