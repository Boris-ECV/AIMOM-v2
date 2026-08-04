# TASK-002 系統設計 — 後端核心服務
**建立者：** sa-agent | **時間：** 2026-07-09T12:58:00

---

## 架構說明

採用 **FastAPI + AWS Lambda + API Gateway HTTP API**，各功能拆成獨立模組，透過
`job_id`（UUID）隔離每次處理。音檔暫存於 S3，進度與中繼狀態改存 DynamoDB
jobstore，避免 Lambda container 間狀態遺失。

```
src/
├── app.py          ← FastAPI 主程式，掛載所有 router
├── config.py       ← .env 讀取、引擎工廠函式
├── upload.py       ← S3 presign / complete / 驗證
├── transcribe.py   ← AssemblyAI 非同步送出與輪詢
├── diarize.py      ← AssemblyAI speaker diarization 對齊
├── summarize.py    ← LLM Prompt 組合與呼叫
├── progress.py     ← 進度狀態讀寫（jobstore）
├── jobstore.py     ← DynamoDB job 狀態存取
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
- `get_transcription_client()` → 依語音引擎設定回傳對應 client
- `get_llm_client()` → 依 `LLM_ENGINE` 回傳對應 client
- 支援引擎：
  - 語音：`assemblyai`
  - LLM：`bedrock-proxy`（預設）、`github-models`、`openai-gpt4o`、`groq`、`gemini`

### upload.py
- 產生 `job_id = uuid4()`
- 建立 S3 presigned URL，讓前端直接上傳音檔
- 完成後寫入 jobstore 的 meta 資料（filename, duration, size, created_at）
- 驗證副檔名（.mp3 / .wav / .m4a）與時長

### transcribe.py
- 讀取 S3 音檔位址
- 呼叫 AssemblyAI submit / get_by_id
- 輸出格式：
  ```json
  [{ "start": 0.0, "end": 5.2, "text": "...", "speaker": null }]
  ```
- 儲存至 jobstore transcript

### diarize.py
- 讀取 jobstore transcript
- 使用 AssemblyAI 的 speaker 標記
- 將 transcript segments 與說話人時間對齊（最大重疊原則）
- 更新 transcript 中每個 segment 的 `speaker` 欄位
- 降級：speaker 資訊不足時以單一 speaker 繼續主流程

### summarize.py
- 讀取 jobstore transcript，組合成逐字稿文字
- System Prompt（繁體中文回應）：
  ```
  你是會議記錄助手。根據以下逐字稿，輸出 JSON 格式的會議紀錄，
  包含：summary（摘要）、action_items（待辦，含 owner/task/due）、
  decisions（決定事項陣列）、topics（討論議題，含 title/content）。
  使用繁體中文回應。
  ```
- 呼叫 LLM（OpenAI 相容端點，可由 Bedrock proxy / Groq / GitHub Models / Gemini 切換），解析 JSON 回應
- 儲存至 jobstore minutes

### progress.py
- 讀/寫 DynamoDB jobstore
- 格式：`{ stage, progress, message, updated_at }`
- `update_progress(job_id, stage, progress, message)` 工具函式

---

## API 規格

詳見 `docs/api/TASK-002-api.md`

---

## 資料流

```
POST /upload/complete
  → S3 音檔
  → jobstore meta
  → status: { stage: "uploaded", progress: 10 }

POST /transcribe
  → AssemblyAI submit / get_by_id
  → jobstore transcript
  → status: { stage: "transcribed", progress: 40 }

POST /diarize
  → AssemblyAI speaker 對齊
  → transcript 更新 speaker 欄位
  → status: { stage: "diarized", progress: 65 }

POST /summarize
  → Bedrock proxy / LLM provider
  → jobstore minutes
  → status: { stage: "done", progress: 100 }
```

---

## 依賴套件

```
fastapi>=0.110
uvicorn
python-dotenv
openai>=1.0
boto3
pytest
httpx          ← FastAPI 測試用
```

---

## 注意事項

1. AssemblyAI 與 Bedrock proxy 都是外部服務，需保留可切換設定
2. jobstore 必須能跨 Lambda container 讀寫
3. LLM 回應可能無法嚴格回傳 JSON，需 try/except 解析並 fallback 純文字
4. 暫存音檔透過 S3 lifecycle / cleanup 刪除，不依賴本機 `tmp/`
