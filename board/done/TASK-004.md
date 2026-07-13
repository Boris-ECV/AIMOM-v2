---
id: TASK-004
title: 後端改用 AssemblyAI — 轉錄 + 說話者識別整合
type: Story
priority: High
assignee: sa-agent
status: backlog
created: 2026-07-09
updated: 2026-07-09T18:10:00
epic: EPIC-001
depends_on: none
prd: docs/requirements/TASK-001-prd.md (v2.0)
---

## 背景

PRD v2.0 決定改用 AssemblyAI 取代 OpenAI Whisper + pyannote.audio，
理由：說話者識別原生支援、無 25MB 分段限制、費用較低（$0.085/場 30 分鐘）。

## 目標

將 `src/transcribe.py` + `src/diarize.py` 重構為 AssemblyAI SDK，
轉錄與說話者識別合併為單一 API 呼叫。

## 範圍

### 需修改的檔案

| 檔案 | 改動 |
|------|------|
| `src/transcribe.py` | 完整重寫：改用 assemblyai SDK 非同步流程 |
| `src/diarize.py` | 移除 pyannote 邏輯，改由 transcribe 步驟一次完成 |
| `src/config.py` | 移除 WHISPER_ENGINE / PYANNOTE_ENABLED / HUGGINGFACE_TOKEN；加入 ASSEMBLYAI_API_KEY / ASSEMBLYAI_MODEL |
| `src/app.py` | 合併 /transcribe + /diarize 流程，或保留端點但後者直接讀暫存結果 |
| `src/requirements.txt` | 移除 `pyannote.audio`、`pydub`、`mutagen`；加入 `assemblyai` |
| `src/.env.example` | 更新設定欄位 |

### AssemblyAI API 流程（需實作）

```python
import assemblyai as aai

aai.settings.api_key = ASSEMBLYAI_API_KEY
config = aai.TranscriptionConfig(
    language_code="zh",
    speaker_labels=True,       # 說話者識別
    speakers_expected=None,    # 自動偵測
)
transcript = aai.Transcriber().transcribe(audio_file_path, config)
# transcript.utterances → [{speaker, text, start, end}]
# transcript.id         → 用於後續 DELETE
```

### 新增：AssemblyAI transcript 刪除（隱私需求）

```python
# 處理完成後刪除 AssemblyAI 上的音檔與逐字稿
aai.Transcript.delete(transcript_id)
```

## Acceptance Criteria

- [ ] POST /api/transcribe 改用 AssemblyAI，回傳格式與原有相同（segments 陣列）
- [ ] 逐字稿結果包含 speaker 欄位（SPEAKER_A / SPEAKER_B...）
- [ ] POST /api/diarize 仍可呼叫（向下相容），直接讀取 transcript.json 的 speaker 欄位
- [ ] 移除 pyannote.audio / pydub / mutagen 依賴
- [ ] DELETE /api/cleanup 額外呼叫 AssemblyAI 刪除 transcript
- [ ] 更新 config.py、requirements.txt、.env.example
- [ ] 更新對應測試檔案（mock AssemblyAI SDK）

## 歷程

| 時間 | 代理 | 動作 |
|------|------|------|
| 2026-07-09T18:10:00 | orchestrator | 建立工單，放入 backlog |
