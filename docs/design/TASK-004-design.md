# TASK-004 系統設計 — 後端改用 AssemblyAI
**建立者：** sa-agent | **時間：** 2026-07-09T18:15:00

---

## 變更摘要

| 檔案 | 動作 | 說明 |
|------|------|------|
| `config.py` | 重寫 | 移除 Whisper/pyannote 設定，加入 AssemblyAI |
| `transcribe.py` | 重寫 | assemblyai SDK，同步阻塞式呼叫 |
| `diarize.py` | 簡化 | 僅讀 transcript.json（AssemblyAI 已含 speaker） |
| `progress.py` | 修改 | cleanup 加入 AssemblyAI transcript 刪除 |
| `requirements.txt` | 更新 | 移除 pydub/pyannote，加入 assemblyai |
| `.env.example` | 更新 | 新設定欄位 |
| `tests/` | 更新 | Mock AssemblyAI SDK |

---

## AssemblyAI SDK 流程設計

```
POST /api/transcribe（前端呼叫）
  ↓
aai.settings.api_key = ASSEMBLYAI_API_KEY
TranscriptionConfig(language_code="zh", speaker_labels=True)
  ↓
aai.Transcriber().transcribe(audio_path, config)
  ← 阻塞，直到 AssemblyAI 完成（30分鐘音訊約 1-2 分鐘）
  ↓
transcript.utterances → [{speaker, text, start_ms, end_ms}]
transcript.id          → 儲存至 meta.json（用於後續刪除）
  ↓
儲存 transcript.json（含 speaker 欄位）
progress → 75%
```

---

## 關鍵設計決策

### 同步 vs 非同步
- 選擇：**同步阻塞**（`transcriber.transcribe()` 內部輪詢）
- 理由：架構改動最小；FastAPI 的 async endpoint 中用 `run_in_executor` 包裝
- AssemblyAI SDK 會自動輪詢直到完成，通常 30 分鐘音訊 < 2 分鐘

### Speaker 標籤格式
- AssemblyAI 回傳：`"A"`, `"B"`, `"C"` 
- 轉換為：`"SPEAKER_A"`, `"SPEAKER_B"` 以維持前端相容性

### utterances vs words
- 優先用 `transcript.utterances`（已依發言人分段）
- 若 `speaker_labels=False` fallback 用 `transcript.words` 合併

---

## 移除的依賴

```
- pyannote.audio  ← 移除（授權問題 + 1GB 模型）
- pydub           ← 移除（分段邏輯不再需要）
- mutagen         ← 保留（仍用於時長驗證）
```
