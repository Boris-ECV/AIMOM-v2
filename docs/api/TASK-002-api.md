# TASK-002 API 規格
**建立者：** sa-agent | **時間：** 2026-07-09T12:58:30

Base URL: `http://localhost:8000`

---

## POST /api/upload

上傳錄音檔，建立處理任務。

**Request:** `multipart/form-data`
- `file`: 音訊檔案（MP3/WAV/M4A）

**Response 200:**
```json
{ "job_id": "uuid", "filename": "meeting.mp3", "duration_sec": 3600, "size_bytes": 102400 }
```
**Response 400:** `{ "error": "不支援的格式" }` / `{ "error": "錄音超過 2 小時上限" }`

---

## POST /api/transcribe

執行語音轉文字。

**Request:** `{ "job_id": "uuid" }`

**Response 200:**
```json
{
  "job_id": "uuid",
  "segments": [{ "start": 0.0, "end": 5.2, "text": "大家好", "speaker": null }],
  "full_text": "大家好..."
}
```

---

## POST /api/diarize

執行發言人識別，更新逐字稿 speaker 欄位。

**Request:** `{ "job_id": "uuid" }`

**Response 200:**
```json
{
  "job_id": "uuid",
  "speakers": ["SPEAKER_00", "SPEAKER_01"],
  "segments": [{ "start": 0.0, "end": 5.2, "text": "大家好", "speaker": "SPEAKER_00" }]
}
```

---

## POST /api/summarize

執行 AI 會議紀錄整理。

**Request:** `{ "job_id": "uuid" }`

**Response 200:**
```json
{
  "job_id": "uuid",
  "summary": "本次會議討論了...",
  "action_items": [
    { "owner": "王小明", "task": "完成前端設計稿", "due": "下週五" }
  ],
  "decisions": ["決定採用 FastAPI 框架", "MVP 不包含歷史記錄功能"],
  "topics": [
    { "title": "技術選型", "content": "討論了 Flask vs FastAPI..." }
  ]
}
```

---

## GET /api/status/{job_id}

查詢處理進度。

**Response 200:**
```json
{
  "job_id": "uuid",
  "stage": "transcribing",
  "progress": 35,
  "message": "正在轉錄第 2/4 段..."
}
```
stage 值：`idle | uploaded | transcribing | transcribed | diarizing | diarized | summarizing | done | error`

---

## DELETE /api/cleanup/{job_id}

刪除暫存資料。

**Response 200:** `{ "deleted": true, "job_id": "uuid" }`
**Response 404:** `{ "error": "job_id 不存在" }`

---

## 通用錯誤格式

```json
{ "error": "錯誤說明", "code": 400 }
```
